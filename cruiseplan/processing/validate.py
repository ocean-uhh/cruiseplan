"""
Cruise configuration validation operations.

This module implements cruiseplan.validate() business logic including:
- Schema validation integration
- Depth accuracy verification
- Configuration completeness checks
- Cross-reference validation

Pure validation logic that verifies cruise configuration correctness
without modifying the data (unlike enrichment operations).
"""

import logging
import warnings as python_warnings
from pathlib import Path
from typing import Any, Union

from pydantic import ValidationError

from cruiseplan.data.bathymetry import BathymetryManager
from cruiseplan.schema.activities import AreaDefinition, LineDefinition, PointDefinition
from cruiseplan.schema.vocabulary import (
    ACTION_FIELD,
    AREA_REGISTRY,
    ARRIVAL_PORT_FIELD,
    DEPARTURE_PORT_FIELD,
    LINE_REGISTRY,
    LINES_FIELD,
    OP_TYPE_FIELD,
    POINT_REGISTRY,
    START_DATE_FIELD,
)
from cruiseplan.utils.defaults import (
    DEFAULT_ARRIVAL_PORT,
    DEFAULT_DEPARTURE_PORT,
    DEFAULT_START_DATE,
    DEFAULT_UPDATE_PREFIX,
)
from cruiseplan.utils.yaml_io import load_yaml_safe

logger = logging.getLogger(__name__)


# --- Warning Handling Utilities ---


# --- Main Validation Function ---


def validate_configuration(
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
        from cruiseplan.core.cruise import Cruise

        # Load and validate configuration
        cruise = Cruise(config_path)

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
        ctd_section_warnings = _check_unexpanded_ctd_sections(cruise)
        warnings.extend(ctd_section_warnings)

        # Check for cruise metadata issues
        metadata_warnings = _check_cruise_metadata(cruise)
        warnings.extend(metadata_warnings)

        # Process captured warnings and format them nicely
        formatted_warnings = _format_validation_warnings(captured_warnings, cruise)
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


# --- Duplicate Detection Functions ---


def check_duplicate_names(cruise) -> tuple[list[str], list[str]]:
    """
    Check for duplicate names across different configuration sections.

    Parameters
    ----------
    cruise : Any
        Loaded cruise configuration object.

    Returns
    -------
    Tuple[List[str], List[str]]
        Tuple of (errors, warnings) for duplicate detection.
    """
    errors = []
    warnings = []

    # Check for duplicate station names - use raw config to catch duplicates
    # that were silently overwritten during point_registry creation
    if hasattr(cruise.config, "points") and cruise.config.points:
        station_names = [station.name for station in cruise.config.points]
        if len(station_names) != len(set(station_names)):
            duplicates = [
                name for name in station_names if station_names.count(name) > 1
            ]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = station_names.count(dup_name)
                errors.append(
                    f"Duplicate station name '{dup_name}' found {count} times - station names must be unique"
                )

    # Check for duplicate leg names (if cruise has legs)
    if hasattr(cruise.config, "legs") and cruise.config.legs:
        leg_names = [leg.name for leg in cruise.config.legs]
        if len(leg_names) != len(set(leg_names)):
            duplicates = [name for name in leg_names if leg_names.count(name) > 1]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = leg_names.count(dup_name)
                errors.append(
                    f"Duplicate leg name '{dup_name}' found {count} times - leg names must be unique"
                )

    # Check for duplicate section names (if cruise has sections)
    if hasattr(cruise.config, "sections") and cruise.config.sections:
        section_names = [section.name for section in cruise.config.sections]
        if len(section_names) != len(set(section_names)):
            duplicates = [
                name for name in section_names if section_names.count(name) > 1
            ]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = section_names.count(dup_name)
                errors.append(
                    f"Duplicate section name '{dup_name}' found {count} times - section names must be unique"
                )

    # NOTE: Moorings are no longer a separate section - they are stations with operation_type="mooring"

    return errors, warnings


def check_complete_duplicates(cruise) -> tuple[list[str], list[str]]:
    """
    Check for completely identical entries (same name, coordinates, operation, etc.).

    Parameters
    ----------
    cruise : Any
        Loaded cruise configuration object.

    Returns
    -------
    Tuple[List[str], List[str]]
        Tuple of (errors, warnings) for complete duplicate detection.
    """
    errors = []
    warnings = []
    warned_pairs = set()  # Track warned pairs to avoid duplicates

    # Check for complete duplicate stations
    if hasattr(cruise.config, "points") and cruise.config.points:
        stations = cruise.config.points
        for ii, station1 in enumerate(stations):
            for _jj, station2 in enumerate(stations[ii + 1 :], ii + 1):
                # Check if all key attributes are identical
                if (
                    station1.name
                    != station2.name  # Don't compare same names (handled above)
                    and getattr(station1, "latitude", None)
                    == getattr(station2, "latitude", None)
                    and getattr(station1, "longitude", None)
                    == getattr(station2, "longitude", None)
                    and getattr(station1, "operation_type", None)
                    == getattr(station2, "operation_type", None)
                    and getattr(station1, "action", None)
                    == getattr(station2, "action", None)
                ):

                    # Create a sorted pair to avoid duplicate warnings for same stations
                    pair = tuple(sorted([station1.name, station2.name]))
                    if pair not in warned_pairs:
                        warned_pairs.add(pair)
                        warnings.append(
                            f"Potentially duplicate stations '{station1.name}' and '{station2.name}' "
                            f"have identical coordinates and operations"
                        )

    return errors, warnings


# --- Depth Validation Functions ---


def validate_depth_accuracy(
    cruise, bathymetry_manager, tolerance: float
) -> tuple[int, list[str]]:
    """
    Compare station water depths with bathymetry data.

    Validates that stated water depths are reasonably close to bathymetric depths.

    Parameters
    ----------
    cruise : Any
        Loaded cruise configuration object.
    bathymetry_manager : Any
        Bathymetry data manager instance.
    tolerance : float
        Tolerance percentage for depth differences.

    Returns
    -------
    Tuple[int, List[str]]
        Tuple of (stations_checked, warning_messages) where:
        - stations_checked: Number of stations with depth data
        - warning_messages: List of depth discrepancy warnings
    """
    stations_checked = 0
    warning_messages = []

    for station_name, station in cruise.point_registry.items():
        # Check water_depth field (preferred for bathymetry comparison)
        water_depth = getattr(station, "water_depth", None)
        if water_depth is not None:
            stations_checked += 1

            # Get depth from bathymetry
            bathymetry_depth = bathymetry_manager.get_depth_at_point(
                station.latitude, station.longitude
            )

            if bathymetry_depth is not None and bathymetry_depth != 0:
                # Convert to positive depth value
                expected_depth = abs(bathymetry_depth)
                stated_depth = water_depth

                # Calculate percentage difference
                if expected_depth > 0:
                    diff_percent = (
                        abs(stated_depth - expected_depth) / expected_depth * 100
                    )

                    if diff_percent > tolerance:
                        warning_msg = (
                            f"Station {station_name}: depth discrepancy of "
                            f"{diff_percent:.1f}% (stated: {stated_depth:.0f}m, "
                            f"bathymetry: {expected_depth:.0f}m)"
                        )
                        warning_messages.append(warning_msg)
            else:
                warning_msg = f"Station {station_name}: could not verify depth (no bathymetry data)"
                warning_messages.append(warning_msg)

        # Additional validation for moorings: operation_depth should match water_depth (both sit on seafloor)
        operation_type = getattr(station, "operation_type", None)
        if operation_type == "mooring":
            operation_depth = getattr(station, "operation_depth", None)
            water_depth = getattr(station, "water_depth", None) or getattr(
                station, "depth", None
            )

            if operation_depth is not None and water_depth is not None:
                # For moorings, operation_depth and water_depth should be very close
                diff_percent = abs(operation_depth - water_depth) / water_depth * 100

                if diff_percent > tolerance:
                    warning_msg = (
                        f"Station {station_name} (mooring): operation_depth and water_depth mismatch of "
                        f"{diff_percent:.1f}% (operation: {operation_depth:.0f}m, water: {water_depth:.0f}m). "
                        f"Moorings should sit on the seafloor - these depths should match closely."
                    )
                    warning_messages.append(warning_msg)
            elif operation_depth is not None and water_depth is None:
                warning_msg = (
                    f"Station {station_name} (mooring): has operation_depth ({operation_depth:.0f}m) "
                    f"but missing water_depth. Moorings need both depths to verify seafloor placement."
                )
                warning_messages.append(warning_msg)

    return stations_checked, warning_messages


# --- Metadata and Structure Validation Functions ---


def _check_unexpanded_ctd_sections(cruise) -> list[str]:
    """
    Check for CTD sections that haven't been expanded yet.

    Parameters
    ----------
    cruise
        Cruise object to check.

    Returns
    -------
    List[str]
        List of warnings about unexpanded CTD sections.
    """
    warnings = []

    # TODO: update to use sections instead of transits
    for transit_name, transit in cruise.line_registry.items():
        if (
            hasattr(transit, "operation_type")
            and transit.operation_type == "CTD"
            and hasattr(transit, "action")
            and transit.action == "section"
        ):
            warnings.append(
                f"CTD section '{transit_name}' should be expanded using "
                f"'cruiseplan enrich --expand-sections' before scheduling"
            )

    return warnings


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


def _check_cruise_metadata(cruise) -> list[str]:
    """
    Check cruise metadata for placeholder values and default coordinates.

    Parameters
    ----------
    cruise
        Cruise object to check.

    Returns
    -------
    List[str]
        List of warnings about metadata issues.
    """
    warnings = []

    if hasattr(cruise.config, "cruise_name"):
        cruise_name = cruise.config.cruise_name
        if cruise_name and "placeholder" in str(cruise_name).lower():
            warnings.append(f"Cruise name contains placeholder value: {cruise_name}")

    placeholders = [
        ("Principal Investigator", cruise.config, "principal_investigator"),
        ("Institution", cruise.config, "institution"),
        ("Vessel", cruise.config, "vessel"),
    ]

    for description, obj, field_name in placeholders:
        if hasattr(obj, field_name):
            value = getattr(obj, field_name)
            if value and isinstance(value, str) and "placeholder" in str(value).lower():
                warnings.append(f"{description} contains placeholder value: {value}")

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


# --- Warning Processing Functions ---


def _format_validation_warnings(captured_warnings: list[str], cruise) -> list[str]:
    """
    Format captured Pydantic warnings into user-friendly grouped messages.

    Parameters
    ----------
    captured_warnings : List[str]
        List of captured warning messages from Pydantic validators.
    cruise : Cruise
        Cruise object to map warnings to specific entities.

    Returns
    -------
    List[str]
        Formatted warning messages grouped by type and sorted alphabetically.
    """
    if not captured_warnings:
        return []

    # Group warnings by type and entity
    warning_groups = {
        "Cruise Metadata": [],
        "Points": {},
        "Lines": {},
        "Areas": {},
        "Configuration": [],
    }

    # Process each warning and try to associate it with specific entities
    for warning_msg in captured_warnings:
        # Try to identify which entity this warning belongs to
        entity_found = False

        # Check points
        if hasattr(cruise, POINT_REGISTRY):
            for station_name, station in getattr(cruise, POINT_REGISTRY).items():
                if _warning_relates_to_entity(warning_msg, station):
                    if station_name not in warning_groups["Points"]:
                        warning_groups["Points"][station_name] = []
                    warning_groups["Points"][station_name].append(
                        _clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # Check lines
        if not entity_found and hasattr(cruise, LINE_REGISTRY):
            for transit_name, transit in getattr(cruise, LINE_REGISTRY).items():
                if _warning_relates_to_entity(warning_msg, transit):
                    if transit_name not in warning_groups["Lines"]:
                        warning_groups["Lines"][transit_name] = []
                    warning_groups["Lines"][transit_name].append(
                        _clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # Check areas
        if not entity_found and hasattr(cruise, AREA_REGISTRY):
            for area_name, area in getattr(cruise, AREA_REGISTRY).items():
                if _warning_relates_to_entity(warning_msg, area):
                    if area_name not in warning_groups["Areas"]:
                        warning_groups["Areas"][area_name] = []
                    warning_groups["Areas"][area_name].append(
                        _clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # If not found, add to general configuration warnings
        if not entity_found:
            warning_groups["Configuration"].append(_clean_warning_message(warning_msg))

    # Format the grouped warnings
    formatted_sections = []

    for group_name in [
        "Points",
        "Lines",
        "Areas",
    ]:
        if warning_groups[group_name]:
            lines = [f"{group_name}:"]
            # Sort entity names alphabetically
            for entity_name in sorted(warning_groups[group_name].keys()):
                entity_warnings = warning_groups[group_name][entity_name]
                for warning in entity_warnings:
                    lines.append(f"  - {entity_name}: {warning}")
            formatted_sections.append("\n".join(lines))

    # Add configuration warnings
    if warning_groups["Configuration"]:
        lines = ["Configuration:"]
        for warning in warning_groups["Configuration"]:
            lines.append(f"  - {warning}")
        formatted_sections.append("\n".join(lines))

    return formatted_sections


def _warning_relates_to_entity(
    warning_msg: str, entity: Union[PointDefinition, LineDefinition, AreaDefinition]
) -> bool:
    """Check if a warning message relates to a specific entity by examining field values."""
    # Use literal strings for Python object attribute access (entity is a Pydantic model)
    # not vocabulary constants which are for YAML field access
    if hasattr(entity, "operation_type") and str(entity.operation_type) in warning_msg:
        if "placeholder" not in warning_msg:
            return True

    if hasattr(entity, "action") and str(entity.action) in warning_msg:
        return True

    if hasattr(entity, "duration") and "duration" in warning_msg.lower():
        duration_val = str(entity.duration)
        if duration_val in warning_msg or (
            "placeholder" in warning_msg and "placeholder" in duration_val.lower()
        ):
            return True

    return False


def _clean_warning_message(warning_msg: str) -> str:
    """Clean up warning message for user display."""
    cleaned = warning_msg.replace(
        "Duration is set to placeholder value ", "Duration is set to placeholder "
    )
    cleaned = cleaned.replace("Input should be ", "")
    cleaned = cleaned.replace(" (type=", " - expected ")

    return cleaned


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
