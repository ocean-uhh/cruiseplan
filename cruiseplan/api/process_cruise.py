"""
Cruise processing workflow API.

This module provides the complete processing workflow including enrich(), validate(),
and process() functions that coordinate the full data processing pipeline.
"""

import logging
import warnings as python_warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import ValidationError

from cruiseplan.core.validation import (
    check_complete_duplicates,
    check_cruise_metadata,
    check_duplicate_names,
    check_unexpanded_ctd_sections,
    format_validation_warnings,
    validate_depth_accuracy,
)
from cruiseplan.data.bathymetry import BathymetryManager
from cruiseplan.exceptions import BathymetryError, FileError
from cruiseplan.exceptions import ValidationError as CruisePlanValidationError
from cruiseplan.schema.fields import (
    ACTION_FIELD,
    ARRIVAL_PORT_FIELD,
    DEPARTURE_PORT_FIELD,
    LINES_FIELD,
    OP_TYPE_FIELD,
    START_DATE_FIELD,
)
from cruiseplan.schema.values import (
    DEFAULT_ARRIVAL_PORT,
    DEFAULT_DEPARTURE_PORT,
    DEFAULT_LEG_NAME,
    DEFAULT_START_DATE,
    DEFAULT_UPDATE_PREFIX,
)
from cruiseplan.schema.yaml_io import load_yaml, load_yaml_safe, save_yaml
from cruiseplan.types import EnrichResult, ProcessResult, ValidationResult
from cruiseplan.utils.logging import configure_logging

logger = logging.getLogger(__name__)


# --- Shared Warning Handling Utilities ---


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


# --- Enrichment Functions ---


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
        configure_logging(verbose)
        if verbose:
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
            raise CruisePlanValidationError(f"Invalid YAML configuration: {e}")

        # Setup and validate output paths
        try:
            from cruiseplan.utils.io import setup_output_paths

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
                raise CruisePlanValidationError(f"Configuration validation failed: {e}")
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
            output_file=output_path,
            files_created=[output_path],
            summary=extended_summary,
        )

    except (CruisePlanValidationError, FileError, BathymetryError):
        # Re-raise our custom exceptions as-is
        raise
    except KeyboardInterrupt:
        raise  # Let CLI handle this
    except Exception as e:
        # Wrap unexpected errors
        raise FileError(f"Unexpected error during enrichment: {e}") from e


# --- Validation Functions ---


def _validate_configuration(
    config_path: Path,
    check_depths: bool = False,
    tolerance: float = 10.0,
    bathymetry_source: str = "etopo2022",
    bathymetry_dir: str = "data",
    strict: bool = False,
) -> tuple[bool, list[str], list[str]]:
    """
    Comprehensive validation of YAML configuration file.

    Performs schema validation, logical consistency checks, and optional
    depth verification against bathymetry data.

    Parameters
    ----------
    config_path : Path
        Path to input YAML configuration.
    check_depths : bool, optional
        Whether to validate depths against bathymetry (default: False).
    tolerance : float, optional
        Depth difference tolerance percentage (default: 10.0).
    bathymetry_source : str, optional
        Bathymetry dataset to use (default: "etopo2022").
    strict : bool, optional
        Whether to use strict validation mode (default: False).

    Returns
    -------
    Tuple[bool, List[str], List[str]]
        Tuple of (success, errors, warnings) where:
        - success: True if validation passed
        - errors: List of error messages
        - warnings: List of warning messages
    """
    errors = []
    warnings = []

    # Capture Python warnings for better formatting
    captured_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    # Set up warning capture
    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    try:
        # Import here to avoid circular dependencies
        from cruiseplan.core.cruise import CruiseInstance

        # Load and validate configuration
        cruise = CruiseInstance(config_path)

        # Basic validation passed if we get here
        logger.debug("✓ YAML structure and schema validation passed")

        # Duplicate detection (always run)
        duplicate_errors, duplicate_warnings = check_duplicate_names(cruise)
        errors.extend(duplicate_errors)
        warnings.extend(duplicate_warnings)

        complete_dup_errors, complete_dup_warnings = check_complete_duplicates(cruise)
        errors.extend(complete_dup_errors)
        warnings.extend(complete_dup_warnings)

        if duplicate_errors or complete_dup_errors:
            logger.debug(
                f"Found {len(duplicate_errors + complete_dup_errors)} duplicate-related errors"
            )
        if duplicate_warnings or complete_dup_warnings:
            logger.debug(
                f"Found {len(duplicate_warnings + complete_dup_warnings)} duplicate-related warnings"
            )

        # Depth validation if requested
        if check_depths:
            bathymetry = BathymetryManager(
                source=bathymetry_source, data_dir=bathymetry_dir
            )
            stations_checked, depth_warnings = validate_depth_accuracy(
                cruise, bathymetry, tolerance
            )
            warnings.extend(depth_warnings)
            logger.debug(f"Checked {stations_checked} stations for depth accuracy")

        # Additional validations can be added here

        # Check for unexpanded CTD sections (raw YAML and cruise object)
        ctd_section_warnings = check_unexpanded_ctd_sections(cruise)
        warnings.extend(ctd_section_warnings)

        # Check for cruise metadata issues
        metadata_warnings = check_cruise_metadata(cruise)
        warnings.extend(metadata_warnings)

        # Process captured warnings and format them nicely
        formatted_warnings = format_validation_warnings(captured_warnings, cruise)
        warnings.extend(formatted_warnings)

        success = len(errors) == 0
        return success, errors, warnings

    except ValidationError as e:
        # Load raw config first to help with error formatting
        raw_config = None
        try:
            raw_config = load_yaml_safe(config_path)
        except Exception:
            # Best-effort: if we cannot load raw YAML, continue with basic error reporting
            pass

        for error in e.errors():
            # Enhanced location formatting with station names when possible
            location = _format_error_location(error["loc"], raw_config)
            message = error["msg"]
            errors.append(f"Schema error at {location}: {message}")

        # Still try to collect warnings even when validation fails
        try:

            # Check cruise metadata from raw YAML
            if raw_config:
                metadata_warnings = _check_cruise_metadata_raw(raw_config)
                warnings.extend(metadata_warnings)

                # Check for unexpanded CTD sections from raw YAML
                ctd_warnings = _check_unexpanded_ctd_sections_raw(raw_config)
                warnings.extend(ctd_warnings)
        except Exception:
            # If we can't load raw YAML, just continue
            pass

        # Process captured Pydantic warnings even on validation failure
        formatted_warnings = _format_validation_warnings(captured_warnings, None)
        warnings.extend(formatted_warnings)

        return False, errors, warnings

    except Exception as e:
        errors.append(f"Configuration loading error: {e}")
        return False, errors, warnings

    finally:
        # Restore original warning handler
        python_warnings.showwarning = old_showwarning


# --- Business Logic Functions (moved to core modules) ---
# All validation business logic has been moved to cruiseplan.core.validation


def _check_unexpanded_ctd_sections_raw(config_dict: dict[str, Any]) -> list[str]:
    """
    Check for CTD sections that haven't been expanded yet from raw YAML.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Raw configuration dictionary.

    Returns
    -------
    List[str]
        List of warnings about unexpanded CTD sections.
    """
    warnings = []

    if LINES_FIELD in config_dict:
        for line in config_dict[LINES_FIELD]:
            if line.get(OP_TYPE_FIELD) == "CTD" and line.get(ACTION_FIELD) == "section":
                warnings.append(
                    f"CTD section '{line.get('name', 'unnamed')}' should be expanded "
                    f"using 'cruiseplan enrich --expand-sections' before scheduling"
                )

    return warnings


def _check_cruise_metadata_raw(raw_config: dict) -> list[str]:
    """
    Check cruise metadata for placeholder values and default coordinates from raw YAML.

    Parameters
    ----------
    raw_config : dict
        Raw YAML configuration dictionary.

    Returns
    -------
    List[str]
        List of cruise metadata warning messages.
    """
    metadata_warnings = []

    # Check for UPDATE- placeholders in cruise-level fields

    # Check start_date
    if START_DATE_FIELD in raw_config:
        start_date = str(raw_config[START_DATE_FIELD])
        if start_date.startswith(DEFAULT_UPDATE_PREFIX):
            metadata_warnings.append(
                f"Start date is set to placeholder '{DEFAULT_UPDATE_PREFIX}YYYY-MM-DDTHH:MM:SSZ'. Please update with actual cruise start date."
            )
        elif start_date == DEFAULT_START_DATE:
            metadata_warnings.append(
                "Start date is set to default '1970-01-01T00:00:00Z'. Please update with actual cruise start date."
            )

    # Check departure port
    if DEPARTURE_PORT_FIELD in raw_config:
        port = raw_config[DEPARTURE_PORT_FIELD]
        if "name" in port and str(port["name"]) == DEFAULT_DEPARTURE_PORT:
            metadata_warnings.append(
                f"Departure port name is set to placeholder '{DEFAULT_DEPARTURE_PORT}'. Please update with actual port name."
            )

        if "latitude" in port and "longitude" in port:
            if port.get("latitude") == 0.0 and port.get("longitude") == 0.0:
                metadata_warnings.append(
                    "Departure port coordinates are set to default (0.0, 0.0). Please update with actual port coordinates."
                )

        if port.get("timezone") == "GMT+0":
            metadata_warnings.append(
                "Departure port timezone is set to default 'GMT+0'. Please update with actual port timezone."
            )

    # Check arrival port
    if ARRIVAL_PORT_FIELD in raw_config:
        port = raw_config[ARRIVAL_PORT_FIELD]
        if "name" in port and str(port["name"]) == DEFAULT_ARRIVAL_PORT:
            metadata_warnings.append(
                f"Arrival port name is set to placeholder '{DEFAULT_ARRIVAL_PORT}'. Please update with actual port name."
            )

        if "latitude" in port and "longitude" in port:
            if port.get("latitude") == 0.0 and port.get("longitude") == 0.0:
                metadata_warnings.append(
                    "Arrival port coordinates are set to default (0.0, 0.0). Please update with actual port coordinates."
                )

        if port.get("timezone") == "GMT+0":
            metadata_warnings.append(
                "Arrival port timezone is set to default 'GMT+0'. Please update with actual port timezone."
            )

    # Format warnings if any found
    if metadata_warnings:
        lines = ["Cruise Metadata:"]
        for warning in metadata_warnings:
            lines.append(f"  - {warning}")
        return ["\n".join(lines)]

    return []


# --- Error Location Formatting ---


def _format_error_location(location_path: tuple, raw_config: dict) -> str:
    """
    Format error location path to be more user-friendly.

    Converts array indices to meaningful names when possible.
    E.g., "stations -> 0 -> latitude" becomes
    "stations -> Station_001 (index 0) -> latitude"

    Parameters
    ----------
    location_path : tuple
        Path tuple from Pydantic validation error.
    raw_config : dict
        Raw configuration dictionary for name lookup.

    Returns
    -------
    str
        Formatted location string.
    """
    if not location_path:
        return "root"

    formatted_parts = []
    current_config = raw_config

    for i, part in enumerate(location_path):
        if isinstance(part, int) and i > 0:
            # This is an array index

            try:
                if isinstance(current_config, list) and part < len(current_config):
                    item = current_config[part]
                    if isinstance(item, dict) and "name" in item:
                        formatted_parts.append(f"{item['name']} (index {part})")
                    else:
                        formatted_parts.append(f"index {part}")
                else:
                    formatted_parts.append(f"index {part}")
            except (KeyError, IndexError, TypeError):
                formatted_parts.append(f"index {part}")

            # Update current_config for next iteration
            try:
                if isinstance(current_config, list) and part < len(current_config):
                    current_config = current_config[part]
                else:
                    current_config = None
            except (IndexError, TypeError):
                current_config = None

        else:
            # This is a regular key
            formatted_parts.append(str(part))

            # Update current_config for next iteration
            try:
                if isinstance(current_config, dict) and part in current_config:
                    current_config = current_config[part]
                else:
                    current_config = None
            except (KeyError, TypeError):
                current_config = None

    return " -> ".join(formatted_parts)


def validate(
    config_file: Union[str, Path],
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    check_depths: bool = True,
    tolerance: float = 10.0,
    strict: bool = False,
    warnings_only: bool = False,
    verbose: bool = False,
) -> ValidationResult:
    """
    Validate a cruise configuration file (mirrors: cruiseplan validate).

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    check_depths : bool
        Compare existing depths with bathymetry data (default: True)
    tolerance : float
        Depth difference tolerance in percent (default: 10.0)
    strict : bool
        Enable strict validation mode (default: False)
    warnings_only : bool
        Show warnings without failing - warnings don't affect return value (default: False)
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    ValidationResult
        Structured validation result with success status, errors, warnings, and summary.

    Examples
    --------
    >>> import cruiseplan
    >>> # Validate cruise configuration with depth checking
    >>> is_valid = cruiseplan.validate(config_file="cruise.yaml", check_depths=True)
    >>> # Strict validation with custom tolerance
    >>> is_valid = cruiseplan.validate(config_file="cruise.yaml", strict=True, tolerance=5.0)
    >>> if is_valid:
    ...     print("✅ Configuration is valid")
    """
    configure_logging(verbose)

    # Validate input file path using centralized utility
    from cruiseplan.utils.io import validate_input_file

    try:
        config_path = validate_input_file(config_file)
    except ValueError as e:
        raise FileError(str(e))
    logger.info(f"🔍 Validating {config_path}")

    try:
        success, errors, warnings = _validate_configuration(
            config_path=config_path,
            check_depths=check_depths,
            tolerance=tolerance,
            bathymetry_source=bathy_source,
            bathymetry_dir=bathy_dir,
            strict=strict,
        )

        # Create summary information
        summary = {
            "config_file": str(config_path),
            "error_count": len(errors),
            "warning_count": len(warnings),
            "depth_checking_enabled": check_depths,
            "strict_mode": strict,
        }

        # Try to add cruise name to summary if available
        try:
            config_dict = load_yaml_safe(config_path)
            if "cruise_name" in config_dict:
                summary["cruise_name"] = config_dict["cruise_name"]
        except Exception:
            # Best-effort enrichment: failure to read cruise_name should not break validation
            pass

        # Report results (UI layer responsibility)
        if errors:
            logger.error("❌ Validation Errors:")
            for error in errors:
                logger.error(f"  • {error}")

        if warnings:
            logger.warning("⚠️ Validation Warnings:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

        # Handle warnings_only mode
        final_success = success if not warnings_only else (success or len(errors) == 0)

        if final_success:
            logger.info("✅ Validation passed")
        else:
            logger.error("❌ Validation failed")

        return ValidationResult(
            success=final_success,
            errors=errors,
            warnings=warnings,
            summary=summary,
        )

    except Exception as e:
        logger.exception("💥 Validation failed")
        return ValidationResult(
            success=False,
            errors=[f"Validation failed: {e}"],
            warnings=[],
            summary={
                "config_file": str(config_path),
                "error_count": 1,
                "warning_count": 0,
            },
        )


# --- Process Function ---


def process(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    add_depths: bool = True,
    add_coords: bool = True,
    expand_sections: bool = True,
    run_validation: bool = True,
    run_map_generation: bool = True,
    depth_check: bool = True,
    tolerance: float = 10.0,
    format: str = "all",
    bathy_stride: int = 10,
    figsize: Optional[list] = None,
    no_port_map: bool = False,
    verbose: bool = False,
) -> ProcessResult:
    """
    Process cruise configuration with unified workflow (mirrors: cruiseplan process).

    This function runs the complete processing workflow: enrichment -> validation -> map generation.

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    output_dir : str
        Output directory for generated files (default: "data")
    output : str, optional
        Base filename for outputs (default: use cruise name from config)
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data/bathymetry")
    add_depths : bool
        Add missing depth values to stations using bathymetry data (default: True)
    add_coords : bool
        Add formatted coordinate fields (default: True)
    expand_sections : bool
        Expand CTD sections into individual station definitions (default: True)
    run_validation : bool
        Run validation after enrichment (default: True)
    run_map_generation : bool
        Generate maps after validation (default: True)
    depth_check : bool
        Compare existing depths with bathymetry data during validation (default: True)
    tolerance : float
        Depth difference tolerance in percent for validation (default: 10.0)
    format : str
        Map output format(s): "png", "pdf", "all" (default: "all")
    bathy_stride : int
        Bathymetry contour stride for maps (default: 10)
    figsize : list, optional
        Figure size for maps [width, height] (default: auto)
    no_port_map : bool
        Skip port overview map generation (default: False)
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    ProcessResult
        Structured result with all files created, validation results, and summary

    Examples
    --------
    >>> import cruiseplan
    >>> # Process with all defaults
    >>> result = cruiseplan.process("cruise.yaml")
    >>> print(f"Files created: {len(result.files_created)}")
    >>> # Custom processing workflow
    >>> result = cruiseplan.process("cruise.yaml", run_map_generation=False, depth_check=False)
    """
    configure_logging(verbose)

    logger.info(f"🚀 Processing cruise configuration: {config_file}")

    from cruiseplan.utils.io import validate_input_file

    # Validate input file
    try:
        config_path = validate_input_file(config_file)
    except ValueError as e:
        raise FileError(str(e))

    generated_files = []
    validation_result = None

    try:
        # Step 1: Enrichment (always run)
        logger.info("🔧 Enriching cruise configuration...")
        try:
            enrich_result = enrich(
                config_file=config_file,
                output_dir=output_dir,
                output=output,
                add_depths=add_depths,
                add_coords=add_coords,
                expand_sections=expand_sections,
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                verbose=verbose,
            )
            enriched_config_path = enrich_result.output_file
            generated_files.append(enriched_config_path)
        except Exception:
            logger.exception("❌ Enrichment failed")
            logger.info("💡 Try running validation only on your original config:")
            logger.info(f"   cruiseplan.validate(config_file='{config_file}')")
            logger.info("   Or use the CLI: cruiseplan validate {config_file}")
            raise

        # Step 2: Validation (optional)
        if run_validation:
            logger.info("✅ Validating cruise configuration...")
            validation_result = validate(
                config_file=enriched_config_path,  # Use enriched config if available
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                check_depths=depth_check,
                tolerance=tolerance,
                verbose=verbose,
            )
            if not validation_result.success:
                logger.warning("⚠️ Validation completed with warnings/errors")

        # Step 3: Map generation (optional)
        if run_map_generation:
            logger.info("🗺️ Generating cruise maps...")

            # Import here to avoid circular import
            from cruiseplan.api.map_cruise import map

            map_result = map(
                config_file=enriched_config_path,  # Use enriched config if available
                output_dir=output_dir,
                output=output,
                format=format,
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                bathy_stride=bathy_stride,
                figsize=figsize,
                no_ports=no_port_map,
                verbose=verbose,
            )
            generated_files.extend(map_result.map_files)

        # Load config metadata for summary
        try:
            config_dict = load_yaml_safe(config_path)
            cruise_name = config_dict.get("cruise_name", "Unknown")
        except Exception:
            cruise_name = "Unknown"

        # Create comprehensive summary
        summary = {
            "config_file": str(config_path),
            "cruise_name": cruise_name,
            "enriched_config": str(enriched_config_path),
            "operations_performed": {
                "enrichment": True,
                "validation": run_validation,
                "map_generation": run_map_generation,
            },
            "total_files_created": len(generated_files),
            "files_generated": len(generated_files),  # Add for CLI compatibility
            "validation_summary": (
                validation_result.summary if validation_result else None
            ),
        }

        logger.info(f"✅ Processing complete! Generated {len(generated_files)} files")

        # Extract validation errors/warnings for cleaner API
        validation_errors = validation_result.errors if validation_result else []
        validation_warnings = validation_result.warnings if validation_result else []

        return ProcessResult(
            config=enriched_config_path,
            files_created=generated_files,
            summary=summary,
            errors=validation_errors,
            warnings=validation_warnings,
        )

    except Exception:
        logger.exception("💥 Processing failed")
        raise


# --- Backward Compatibility Exports ---

# For backward compatibility, expose the internal function with the old name
enrich_configuration = _enrich_configuration
validate_configuration = _validate_configuration

# Import core validation functions for backward compatibility

# Adding backward compatibility aliases for private functions used in tests
_format_validation_warnings = format_validation_warnings
