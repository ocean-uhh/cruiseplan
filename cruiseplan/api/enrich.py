"""
Cruise configuration enrichment API.

This module provides the main enrich() function that handles all validation, 
file operations, and error handling for enriching cruise configurations.
"""

import logging
import warnings as python_warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional, Union

from cruiseplan.exceptions import BathymetryError, FileError, ValidationError
from cruiseplan.schema.vocabulary import (
    ARRIVAL_PORT_FIELD,
    DEPARTURE_PORT_FIELD,
)
from cruiseplan.types import EnrichResult
from cruiseplan.utils.defaults import (
    DEFAULT_ARRIVAL_PORT,
    DEFAULT_DEPARTURE_PORT,
    DEFAULT_LEG_NAME,
)
from cruiseplan.utils.yaml_io import load_yaml, save_yaml

logger = logging.getLogger(__name__)


# --- Warning Handling Utilities ---


@contextmanager
def _validation_warning_capture():
    """
    Context manager for capturing and formatting validation warnings.

    Yields
    ------
    List[str]
        List that will be populated with captured warning messages.
    """
    captured_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    try:
        yield captured_warnings
    finally:
        python_warnings.showwarning = old_showwarning


# --- Configuration Field Processing ---


def _minimal_preprocess_config(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Minimal preprocessing to ensure config_dict can pass Pydantic validation.

    Only adds the absolute minimum required for Cruise.from_dict() to succeed.
    All intelligent defaults and business logic moved to Cruise object methods.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Raw configuration dictionary from YAML.

    Returns
    -------
    dict[str, Any]
        Minimally processed config dictionary ready for Cruise.from_dict().
    """
    # Create a copy to avoid modifying original
    processed_config = config_dict.copy()

    # Only add what's absolutely required for Pydantic validation to pass
    # Most defaults will be handled by Cruise object methods

    # Ensure legs list exists (required by schema)
    if "legs" not in processed_config:
        processed_config["legs"] = []

    # If no legs and no ports, add minimal default leg for validation
    if not processed_config["legs"]:
        departure_port = processed_config.get(
            DEPARTURE_PORT_FIELD, DEFAULT_DEPARTURE_PORT
        )
        arrival_port = processed_config.get(ARRIVAL_PORT_FIELD, DEFAULT_ARRIVAL_PORT)

        processed_config["legs"] = [
            {
                "name": DEFAULT_LEG_NAME,
                DEPARTURE_PORT_FIELD: departure_port,
                ARRIVAL_PORT_FIELD: arrival_port,
            }
        ]

        # Remove global ports since they're now in the leg
        processed_config.pop(DEPARTURE_PORT_FIELD, None)
        processed_config.pop(ARRIVAL_PORT_FIELD, None)

    return processed_config


def _save_config(
    config_dict: dict[str, Any],
    output_path: Optional[Path],
) -> None:
    """
    Save configuration to file.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to save.
    output_path : Optional[Path]
        Path for output file (if None, no save).
    """
    if output_path:
        save_yaml(config_dict, output_path, backup=False)


def _process_warnings(captured_warnings: list[str]) -> None:
    """
    Process and display captured warnings in user-friendly format.

    Parameters
    ----------
    captured_warnings : list[str]
        List of captured warning messages.
    """
    if captured_warnings:
        logger.warning("⚠️ Configuration Warnings:")
        for warning in captured_warnings:
            for line in warning.split("\n"):
                if line.strip():
                    logger.warning(f"  {line}")
        logger.warning("")  # Add spacing between warning groups


def _enrich_configuration(
    config_path: Path,
    add_depths: bool = False,
    add_coords: bool = False,
    expand_sections: bool = False,
    bathymetry_source: str = "etopo2022",
    bathymetry_dir: str = "data",
    coord_format: str = "ddm",
    output_path: Optional[Path] = None,
) -> dict[str, Any]:
    """
    Add missing data to cruise configuration.

    Enriches the cruise configuration by adding bathymetric depths and
    formatted coordinates where missing. Port references are automatically
    resolved to full PortDefinition objects during loading.

    Parameters
    ----------
    config_path : Path
        Path to input YAML configuration.
    add_depths : bool, optional
        Whether to add missing depth values (default: False).
    add_coords : bool, optional
        Whether to add formatted coordinate fields (default: False).
    expand_sections : bool, optional
        Whether to expand CTD sections into individual stations (default: False).
    bathymetry_source : str, optional
        Bathymetry dataset to use (default: "etopo2022").
    coord_format : str, optional
        Coordinate format ("ddm" or "dms", default: "ddm").
    output_path : Optional[Path], optional
        Path for output file (if None, modifies in place).

    Returns
    -------
    Dict[str, Any]
        Dictionary with enrichment summary containing:
        - stations_with_depths_added: Number of depths added
        - stations_with_coords_added: Number of coordinates added
        - sections_expanded: Number of CTD sections expanded
        - stations_from_expansion: Number of stations generated from expansion
        - total_stations_processed: Total stations processed
    """
    # === Clean Architecture: Minimal preprocessing → Cruise enhancement phase ===

    # 1. Load raw YAML
    config_dict = load_yaml(config_path)

    # 2. Minimal preprocessing (only what's required for Pydantic validation)
    processed_config = _minimal_preprocess_config(config_dict)

    # 3. Create Cruise object
    from cruiseplan.core.cruise import CruiseInstance

    with _validation_warning_capture() as captured_warnings:
        cruise = CruiseInstance.from_dict(processed_config)

    # 4. Cruise enhancement phase - all business logic in Cruise object methods
    sections_expanded = 0
    stations_from_expansion = 0
    if expand_sections:
        section_summary = cruise.expand_sections()
        sections_expanded = section_summary["sections_expanded"]
        stations_from_expansion = section_summary["stations_from_expansion"]

    # Add station defaults (like mooring durations)
    station_defaults_added = cruise.add_station_defaults()

    stations_with_depths_added = set()
    if add_depths:
        stations_with_depths_added = cruise.enrich_depths(
            bathymetry_source, bathymetry_dir
        )

    # Ports are automatically resolved during Cruise object creation
    # No need for explicit expand_ports flag anymore

    # 5. Add coordinate displays if requested (Cruise object enhancement)
    coord_changes_made = 0
    if add_coords:
        coord_changes_made = cruise.add_coordinate_displays(coord_format)

    # 6. Generate final YAML output with all enhancements
    output_config = cruise.to_commented_dict()

    # 7. Build summary and save
    final_summary = {
        "sections_expanded": sections_expanded,
        "stations_from_expansion": stations_from_expansion,
        "stations_with_depths_added": len(stations_with_depths_added),
        "stations_with_coords_added": coord_changes_made,
        "station_defaults_added": station_defaults_added,
        "total_stations_processed": len(cruise.point_registry),
    }

    # Process warnings and save configuration
    _process_warnings(captured_warnings)
    _save_config(output_config, output_path)

    return final_summary


def enrich(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    add_depths: bool = True,
    add_coords: bool = True,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    coord_format: str = "ddm",
    expand_sections: bool = True,
    verbose: bool = False,
) -> EnrichResult:
    """
    Enrich a cruise configuration file (mirrors: cruiseplan enrich).

    This function now handles all validation, file operations, and error handling
    that was previously in the CLI layer.

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    output_dir : str
        Output directory for enriched file (default: "data")
    output : str, optional
        Base filename for output (default: use input filename)
    add_depths : bool
        Add missing depth values to stations using bathymetry data (default: True)
    add_coords : bool
        Add formatted coordinate fields (default: True)
    expand_sections : bool
        Expand CTD sections into individual station definitions (default: True)
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    coord_format : str
        Coordinate format (default: "ddm")
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    EnrichResult
        Structured result with output file, files created, and summary

    Raises
    ------
    ValidationError
        If configuration validation fails
    FileError
        If file operations fail (reading, writing, permissions)
    BathymetryError
        If bathymetry operations fail

    Examples
    --------
    >>> import cruiseplan
    >>> result = cruiseplan.enrich(config_file="cruise.yaml", add_depths=True)
    >>> print(f"Enriched file: {result.output_file}")
    >>> print(f"Summary: {result.summary}")
    """
    try:
        # Setup verbose logging if requested
        if verbose:
            logging.basicConfig(level=logging.DEBUG)
            logger.debug("Verbose logging enabled")

        # Validate input file path using centralized utility
        from cruiseplan.utils.io import validate_input_file

        try:
            config_path = validate_input_file(config_file)
        except ValueError as e:
            raise FileError(str(e))

        # Validate config file format
        try:
            config_data = load_yaml(config_path)
            cruise_name = config_data.get("cruise_name")
        except Exception as e:
            raise ValidationError(f"Invalid YAML configuration: {e}")

        # Setup and validate output paths
        try:
            from cruiseplan.utils.config import setup_output_paths

            output_dir_path, base_name = setup_output_paths(
                config_file, output_dir, output
            )

            # Create output directory if needed
            output_dir_path.mkdir(parents=True, exist_ok=True)

            # Test directory writability
            test_file = output_dir_path / ".tmp_write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except Exception:
                raise FileError(f"Output directory is not writable: {output_dir_path}")

        except Exception as e:
            if isinstance(e, FileError):
                raise
            raise FileError(f"Output directory setup failed: {e}")

        # Determine final output file path
        output_path = output_dir_path / f"{base_name}_enriched.yaml"

        logger.info(f"🔧 Enriching {config_path}")
        if verbose:
            logger.info(f"📁 Output directory: {output_dir_path}")
            logger.info(f"📄 Output file: {output_path}")
            logger.info(
                f"⚙️  Operations: depths={add_depths}, coords={add_coords}, sections={expand_sections}"
            )

        # Perform the actual enrichment
        try:
            summary = _enrich_configuration(
                config_path,
                output_path=output_path,
                add_depths=add_depths,
                add_coords=add_coords,
                expand_sections=expand_sections,
                bathymetry_source=bathy_source,
                bathymetry_dir=bathy_dir,
                coord_format=coord_format,
            )

        except Exception as e:
            # Convert low-level errors to appropriate high-level exceptions
            error_msg = str(e).lower()
            if (
                "validation" in error_msg
                or "invalid" in error_msg
                or "missing" in error_msg
            ):
                raise ValidationError(f"Configuration validation failed: {e}")
            elif (
                "bathymetry" in error_msg
                or "etopo" in error_msg
                or "gebco" in error_msg
            ):
                raise BathymetryError(f"Bathymetry processing failed: {e}")
            elif (
                "file" in error_msg
                or "directory" in error_msg
                or "permission" in error_msg
            ):
                raise FileError(f"File operation failed: {e}")
            else:
                # Re-raise as generic error for now
                raise

        # Verify output was created successfully
        if not output_path.exists():
            raise FileError(
                f"Enrichment completed but output file was not created: {output_path}"
            )

        # Generate extended summary information
        extended_summary = {
            "config_file": str(config_path),
            "cruise_name": cruise_name,
            "operations_performed": {
                "add_depths": add_depths,
                "add_coords": add_coords,
                "expand_sections": expand_sections,
            },
            "output_size_bytes": output_path.stat().st_size,
            **summary,  # Include detailed summary from _enrich_configuration
        }

        logger.info(f"✅ Configuration enriched successfully: {output_path}")

        return EnrichResult(
            output_file=output_path, files_created=[output_path], summary=extended_summary
        )

    except (ValidationError, FileError, BathymetryError):
        # Re-raise our custom exceptions as-is
        raise
    except KeyboardInterrupt:
        raise  # Let CLI handle this
    except Exception as e:
        # Wrap unexpected errors
        raise FileError(f"Unexpected error during enrichment: {e}") from e


# For backward compatibility, expose the internal function with the old name
enrich_configuration = _enrich_configuration