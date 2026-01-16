"""
Core validation functions for cruise configurations.

This module contains validation business logic that operates on CruiseInstance objects.
These functions perform the actual validation checks without file I/O or API concerns.
"""

import logging
from typing import TYPE_CHECKING, Union

from cruiseplan.data.bathymetry import BathymetryManager
from cruiseplan.schema.activities import AreaDefinition, LineDefinition, PointDefinition
from cruiseplan.schema.fields import (
    AREA_REGISTRY,
    LINE_REGISTRY,
    POINT_REGISTRY,
)

if TYPE_CHECKING:
    from cruiseplan.core.cruise import CruiseInstance

logger = logging.getLogger(__name__)


def check_duplicate_names(
    cruise_instance: "CruiseInstance",
) -> tuple[list[str], list[str]]:
    """
    Check for duplicate names across different configuration sections.

    Parameters
    ----------
    cruise_instance : CruiseInstance
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
    if hasattr(cruise_instance.config, "points") and cruise_instance.config.points:
        station_names = [station.name for station in cruise_instance.config.points]
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
    if hasattr(cruise_instance.config, "legs") and cruise_instance.config.legs:
        leg_names = [leg.name for leg in cruise_instance.config.legs]
        if len(leg_names) != len(set(leg_names)):
            duplicates = [name for name in leg_names if leg_names.count(name) > 1]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = leg_names.count(dup_name)
                errors.append(
                    f"Duplicate leg name '{dup_name}' found {count} times - leg names must be unique"
                )

    # Check for duplicate section names (if cruise has sections)
    if hasattr(cruise_instance.config, "sections") and cruise_instance.config.sections:
        section_names = [section.name for section in cruise_instance.config.sections]
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


def check_complete_duplicates(
    cruise_instance: "CruiseInstance",
) -> tuple[list[str], list[str]]:
    """
    Check for completely identical entries (same name, coordinates, operation, etc.).

    Parameters
    ----------
    cruise_instance : CruiseInstance
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
    if hasattr(cruise_instance.config, "points") and cruise_instance.config.points:
        stations = cruise_instance.config.points
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


def validate_depth_accuracy(
    cruise_instance: "CruiseInstance",
    bathymetry_manager: BathymetryManager,
    tolerance: float,
) -> tuple[int, list[str]]:
    """
    Compare station water depths with bathymetry data.

    Validates that stated water depths are reasonably close to bathymetric depths.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        Loaded cruise configuration object.
    bathymetry_manager : BathymetryManager
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

    for station_name, station in cruise_instance.point_registry.items():
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


def check_unexpanded_ctd_sections(cruise_instance: "CruiseInstance") -> list[str]:
    """
    Check for CTD sections that haven't been expanded yet.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        Cruise instance to check.

    Returns
    -------
    List[str]
        List of warnings about unexpanded CTD sections.
    """
    warnings = []

    # TODO: update to use sections instead of transits
    for transit_name, transit in cruise_instance.line_registry.items():
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


def check_cruise_metadata(cruise_instance: "CruiseInstance") -> list[str]:
    """
    Check cruise metadata for placeholder values and default coordinates.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        Cruise instance to check.

    Returns
    -------
    List[str]
        List of warnings about metadata issues.
    """
    warnings = []

    if hasattr(cruise_instance.config, "cruise_name"):
        cruise_name = cruise_instance.config.cruise_name
        if cruise_name and "placeholder" in str(cruise_name).lower():
            warnings.append(f"Cruise name contains placeholder value: {cruise_name}")

    placeholders = [
        ("Principal Investigator", cruise_instance.config, "principal_investigator"),
        ("Institution", cruise_instance.config, "institution"),
        ("Vessel", cruise_instance.config, "vessel"),
    ]

    for description, obj, field_name in placeholders:
        if hasattr(obj, field_name):
            value = getattr(obj, field_name)
            if value and isinstance(value, str) and "placeholder" in str(value).lower():
                warnings.append(f"{description} contains placeholder value: {value}")

    return warnings


def format_validation_warnings(
    captured_warnings: list[str], cruise_instance: "CruiseInstance"
) -> list[str]:
    """
    Format captured Pydantic warnings into user-friendly grouped messages.

    Parameters
    ----------
    captured_warnings : List[str]
        List of captured warning messages from Pydantic validators.
    cruise_instance : CruiseInstance
        Cruise instance to map warnings to specific entities.

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
        if hasattr(cruise_instance, POINT_REGISTRY):
            for station_name, station in getattr(
                cruise_instance, POINT_REGISTRY
            ).items():
                if warning_relates_to_entity(warning_msg, station):
                    if station_name not in warning_groups["Points"]:
                        warning_groups["Points"][station_name] = []
                    warning_groups["Points"][station_name].append(
                        clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # Check lines
        if not entity_found and hasattr(cruise_instance, LINE_REGISTRY):
            for transit_name, transit in getattr(
                cruise_instance, LINE_REGISTRY
            ).items():
                if warning_relates_to_entity(warning_msg, transit):
                    if transit_name not in warning_groups["Lines"]:
                        warning_groups["Lines"][transit_name] = []
                    warning_groups["Lines"][transit_name].append(
                        clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # Check areas
        if not entity_found and hasattr(cruise_instance, AREA_REGISTRY):
            for area_name, area in getattr(cruise_instance, AREA_REGISTRY).items():
                if warning_relates_to_entity(warning_msg, area):
                    if area_name not in warning_groups["Areas"]:
                        warning_groups["Areas"][area_name] = []
                    warning_groups["Areas"][area_name].append(
                        clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # If not found, add to general configuration warnings
        if not entity_found:
            warning_groups["Configuration"].append(clean_warning_message(warning_msg))

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


def warning_relates_to_entity(
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


def clean_warning_message(warning_msg: str) -> str:
    """Clean up warning message for user display."""
    cleaned = warning_msg.replace(
        "Duration is set to placeholder value ", "Duration is set to placeholder "
    )
    cleaned = cleaned.replace("Input should be ", "")
    cleaned = cleaned.replace(" (type=", " - expected ")

    return cleaned
