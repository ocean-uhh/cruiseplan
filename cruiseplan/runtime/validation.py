"""
Cruise Configuration Validation Functions.

This module provides comprehensive validation for cruise configurations, organized into
distinct validation categories:

1. **Duplicate Detection**: Find naming conflicts and identical entries with proper scoping
   - check_duplicate_names() - Enforce uniqueness scopes: global catalog (points/lines/areas), legs, and per-leg clusters
   - check_complete_duplicates() - Find true duplicates (same name + same attributes) - likely copy-paste errors

2. **Scientific Data Validation**: Verify oceanographic accuracy
   - validate_depth_accuracy() - Compare stated depths with bathymetry data

3. **Configuration Completeness**: Check for missing/incomplete configuration
   - check_unexpanded_ctd_sections() - Find CTD sections needing expansion
   - check_cruise_metadata() - Verify cruise metadata completeness

4. **Pydantic Warning Processing**: Convert technical validation errors to user-friendly messages
   - format_validation_warnings() - Main entry point for processing Pydantic warnings
   - Helper functions for text matching and message cleanup

All validation functions operate on CruiseInstance objects and return structured
error/warning information suitable for display to users.
"""

import logging
from typing import TYPE_CHECKING, Union

from cruiseplan.config.activities import AreaDefinition, LineDefinition, PointDefinition
from cruiseplan.config.fields import (
    AREA_REGISTRY,
    CRUISE_NAME_FIELD,
    INSTITUTION_FIELD,
    LINE_REGISTRY,
    POINT_REGISTRY,
    PRINCIPAL_INVESTIGATOR_FIELD,
    VESSEL_FIELD,
)
from cruiseplan.config.values import (
    DEFAULT_ARRIVAL_PORT,
    DEFAULT_CRUISE_NAME,
    DEFAULT_DEPARTURE_PORT,
    DEFAULT_UPDATE_PREFIX,
)
from cruiseplan.data.bathymetry import BathymetryManager

if TYPE_CHECKING:
    from cruiseplan.runtime.cruise import CruiseInstance

logger = logging.getLogger(__name__)


# =============================================================================
# DUPLICATE DETECTION
# =============================================================================


def _get_all_entities(cruise_instance: "CruiseInstance"):
    """
    Yield all entity collections with their metadata.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        Loaded cruise configuration object.

    Yields
    ------
    tuple
        (entity_type, display_name, entities, comparison_fields) where:
        - entity_type: String identifier (e.g., "points", "lines")
        - display_name: Human-readable name for error messages
        - entities: List of actual entity objects
        - comparison_fields: List of field names to compare for complete duplicates
    """
    entity_definitions = [
        ("points", "point", ["latitude", "longitude", "operation_type", "action"]),
        ("lines", "line", ["operation_type", "action", "route"]),
        ("areas", "area", ["operation_type", "action", "corners"]),
        (
            "legs",
            "leg",
            [],
        ),  # Legs only checked for name duplicates, no field comparison needed
    ]

    for entity_type, display_name, comparison_fields in entity_definitions:
        entities = getattr(cruise_instance.config, entity_type, None) or []
        if entities:
            yield entity_type, display_name, entities, comparison_fields


def check_duplicate_names(
    cruise_instance: "CruiseInstance",
) -> tuple[list[str], list[str]]:
    """
    Check for duplicate names across different configuration scopes.

    Enforces three uniqueness scopes:
    1. Global catalog: points, lines, areas must all have unique names (cross-type)
    2. Leg scope: legs must have unique names within legs
    3. Cluster scope: clusters must have unique names within clusters

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

    # 1. Check global catalog scope: points, lines, areas must be unique across types
    catalog_entities = []

    for entity_type, display_name, entities, _ in _get_all_entities(cruise_instance):
        # Skip legs - they have their own scope
        if entity_type != "legs":
            for entity in entities:
                if hasattr(entity, "name"):
                    catalog_entities.append((entity.name, display_name))

    # Check for cross-type duplicates in catalog
    if catalog_entities:
        catalog_errors = _check_cross_type_duplicates(catalog_entities)
        errors.extend(catalog_errors)

    # 2. Check leg scope: legs must be unique within legs
    if hasattr(cruise_instance.config, "legs") and cruise_instance.config.legs:
        leg_errors = _check_entity_duplicates(cruise_instance.config.legs, "leg")
        errors.extend(leg_errors)

    # 3. Check cluster scope: clusters must be unique within each leg
    if hasattr(cruise_instance.config, "legs") and cruise_instance.config.legs:
        for leg in cruise_instance.config.legs:
            if hasattr(leg, "clusters") and leg.clusters:
                cluster_errors = _check_entity_duplicates(
                    leg.clusters, f"cluster (in leg '{leg.name}')"
                )
                errors.extend(cluster_errors)

    return errors, warnings


def _check_cross_type_duplicates(catalog_entities: list[tuple[str, str]]) -> list[str]:
    """
    Check for name duplicates across different entity types in the catalog.

    Parameters
    ----------
    catalog_entities : list[tuple[str, str]]
        List of (entity_name, entity_type) tuples

    Returns
    -------
    list[str]
        List of error messages for cross-type duplicates
    """
    errors = []
    name_to_types = {}

    # Group entities by name
    for name, entity_type in catalog_entities:
        if name not in name_to_types:
            name_to_types[name] = []
        name_to_types[name].append(entity_type)

    # Check for conflicts
    for name, types in name_to_types.items():
        if len(types) > 1:
            type_counts = {}
            for t in types:
                type_counts[t] = type_counts.get(t, 0) + 1

            # Format error message
            type_descriptions = []
            for entity_type, count in type_counts.items():
                if count == 1:
                    type_descriptions.append(f"1 {entity_type}")
                else:
                    type_descriptions.append(f"{count} {entity_type}s")

            errors.append(
                f"Name conflict: '{name}' is used by {', '.join(type_descriptions)} - "
                f"all catalog entities (points, lines, areas) must have unique names"
            )

    return errors


def _check_entity_duplicates(entities: list, entity_display_name: str) -> list[str]:
    """
    Check for duplicate names in a list of entities.

    Parameters
    ----------
    entities : list
        List of entities with 'name' attributes
    entity_display_name : str
        Display name for error messages (e.g., "point", "leg")

    Returns
    -------
    list[str]
        List of error messages for duplicates found
    """
    errors = []
    entity_names = [entity.name for entity in entities if hasattr(entity, "name")]

    if len(entity_names) != len(set(entity_names)):
        # Find duplicates efficiently
        name_counts = {}
        for name in entity_names:
            name_counts[name] = name_counts.get(name, 0) + 1

        # Report duplicates
        for name, count in name_counts.items():
            if count > 1:
                errors.append(
                    f"Duplicate {entity_display_name} name '{name}' found {count} times - "
                    f"{entity_display_name} names must be unique"
                )

    return errors


def check_complete_duplicates(
    cruise_instance: "CruiseInstance",
) -> tuple[list[str], list[str]]:
    """
    Check for completely identical entries across all entity types.

    This catches true duplicates where everything is identical - likely copy-paste errors
    or accidental duplicates. This is a subset of entities that would also be caught by
    check_duplicate_names(), but indicates a more serious duplication issue.

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

    # Check each entity type for complete duplicates using shared iterator
    for _, display_name, entities, comparison_fields in _get_all_entities(
        cruise_instance
    ):
        # Skip entities that don't have comparison fields (like legs)
        if comparison_fields:
            entity_errors = _check_complete_entity_duplicates(
                entities, display_name, comparison_fields
            )
            errors.extend(entity_errors)

    return errors, warnings


def _check_complete_entity_duplicates(
    entities: list, entity_display_name: str, comparison_fields: list[str]
) -> list[str]:
    """
    Check for complete duplicates in a list of entities.

    Parameters
    ----------
    entities : list
        List of entities with attributes to compare
    entity_display_name : str
        Display name for error messages (e.g., "point", "line")
    comparison_fields : list[str]
        List of attribute names to compare for duplicates

    Returns
    -------
    list[str]
        List of error messages for complete duplicates found
    """
    errors = []
    warned_pairs = set()  # Track warned pairs to avoid duplicates

    for ii, entity1 in enumerate(entities):
        for entity2 in entities[ii + 1 :]:
            # First check if names are the same (required for complete duplicate)
            if not (
                hasattr(entity1, "name")
                and hasattr(entity2, "name")
                and entity1.name == entity2.name
            ):
                continue

            # Check if all comparison fields are identical
            all_fields_match = True
            for field in comparison_fields:
                val1 = getattr(entity1, field, None)
                val2 = getattr(entity2, field, None)
                if val1 != val2:
                    all_fields_match = False
                    break

            if all_fields_match:
                # Create a sorted pair to avoid duplicate warnings for same entities
                pair = tuple(sorted([entity1.name, entity2.name]))
                if pair not in warned_pairs:
                    warned_pairs.add(pair)
                    errors.append(
                        f"Complete duplicate found: {entity_display_name} '{entity1.name}' appears multiple times "
                        f"with identical attributes - likely a copy-paste error"
                    )

    return errors


# =============================================================================
# SCIENTIFIC DATA VALIDATION
# =============================================================================


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

    def _calc_percent_diff(depth1: float, depth2: float) -> float:
        """Calculate percentage difference between two depth values."""
        return abs(depth1 - depth2) / depth2 * 100

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
                    diff_percent = _calc_percent_diff(stated_depth, expected_depth)

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
                diff_percent = _calc_percent_diff(operation_depth, water_depth)

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


# =============================================================================
# CONFIGURATION COMPLETENESS
# =============================================================================


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
    for line_name, line in cruise_instance.line_registry.items():
        if (
            hasattr(line, "operation_type")
            and line.operation_type == "CTD"
            and hasattr(line, "action")
            and line.action == "section"
        ):
            warnings.append(
                f"CTD section '{line_name}' should be expanded using "
                f"'cruiseplan enrich --expand-sections' before scheduling"
            )

    return warnings


def check_cruise_metadata(cruise_instance: "CruiseInstance") -> list[str]:
    """
    Check cruise metadata for placeholder values and default coordinates.

    Uses specific placeholder patterns defined in cruiseplan.config.values:
    - UPDATE- prefix for placeholder values
    - port_update_ prefix for port placeholders
    - Default cruise name placeholder

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

    # Check cruise name for placeholder
    if hasattr(cruise_instance.config, CRUISE_NAME_FIELD):
        cruise_name = getattr(cruise_instance.config, CRUISE_NAME_FIELD)
        if cruise_name == DEFAULT_CRUISE_NAME or (
            cruise_name and cruise_name.startswith(DEFAULT_UPDATE_PREFIX)
        ):
            warnings.append(f"Cruise name contains placeholder value: {cruise_name}")

    # Check standard metadata fields for UPDATE- prefix
    metadata_fields = [
        (
            "Principal Investigator",
            cruise_instance.config,
            PRINCIPAL_INVESTIGATOR_FIELD,
        ),
        ("Institution", cruise_instance.config, INSTITUTION_FIELD),
        ("Vessel", cruise_instance.config, VESSEL_FIELD),
    ]

    for description, obj, field_name in metadata_fields:
        if hasattr(obj, field_name):
            value = getattr(obj, field_name)
            if (
                value
                and isinstance(value, str)
                and value.startswith(DEFAULT_UPDATE_PREFIX)
            ):
                warnings.append(f"{description} contains placeholder value: {value}")

    # Check port names for placeholder patterns
    for leg in cruise_instance.config.legs:
        if hasattr(leg, "departure_port") and leg.departure_port:
            if leg.departure_port.name == DEFAULT_DEPARTURE_PORT:
                warnings.append(
                    f"Departure port contains placeholder value: {leg.departure_port.name}"
                )

        if hasattr(leg, "arrival_port") and leg.arrival_port:
            if leg.arrival_port.name == DEFAULT_ARRIVAL_PORT:
                warnings.append(
                    f"Arrival port contains placeholder value: {leg.arrival_port.name}"
                )

    return warnings


# =============================================================================
# PYDANTIC WARNING PROCESSING
# =============================================================================


def format_validation_warnings(
    captured_warnings: list[str], cruise_instance: "CruiseInstance"
) -> list[str]:
    """
    Format captured Pydantic warnings into user-friendly grouped messages.

    This is the main entry point for converting technical Pydantic validation
    errors into readable warnings grouped by entity type (Points/Lines/Areas).

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

    # Categorize warnings using helper function
    warning_groups = _categorize_warnings(captured_warnings, cruise_instance)

    # Format output using helper function
    return _format_warning_groups(warning_groups)


def _categorize_warnings(
    captured_warnings: list[str], cruise_instance: "CruiseInstance"
) -> dict[str, dict]:
    """
    Categorize warnings by entity type and specific entities.

    Returns
    -------
    dict
        Warning groups with Points/Lines/Areas containing entity-specific warnings,
        and Configuration containing uncategorized warnings.
    """
    warning_groups = {
        "Points": {},
        "Lines": {},
        "Areas": {},
        "Configuration": [],
    }

    # Process warnings for each entity type
    warning_groups["Points"] = _process_warnings_for_entity_type(
        captured_warnings, cruise_instance, POINT_REGISTRY
    )
    warning_groups["Lines"] = _process_warnings_for_entity_type(
        captured_warnings, cruise_instance, LINE_REGISTRY
    )
    warning_groups["Areas"] = _process_warnings_for_entity_type(
        captured_warnings, cruise_instance, AREA_REGISTRY
    )

    # Find warnings that weren't categorized to any entity
    all_categorized_warnings = set()
    for entity_group in [
        warning_groups["Points"],
        warning_groups["Lines"],
        warning_groups["Areas"],
    ]:
        for entity_warnings in entity_group.values():
            all_categorized_warnings.update(entity_warnings)

    # Add uncategorized warnings to Configuration
    for warning_msg in captured_warnings:
        cleaned_warning = clean_warning_message(warning_msg)
        if cleaned_warning not in all_categorized_warnings:
            warning_groups["Configuration"].append(cleaned_warning)

    return warning_groups


def _process_warnings_for_entity_type(
    warnings: list[str], cruise_instance: "CruiseInstance", registry_name: str
) -> dict[str, list[str]]:
    """Process warnings for a specific entity type (points, lines, areas)."""
    entity_warnings = {}
    registry = _get_entity_registry(cruise_instance, registry_name)

    for warning_msg in warnings:
        for entity_name, entity in registry.items():
            if warning_relates_to_entity(warning_msg, entity):
                if entity_name not in entity_warnings:
                    entity_warnings[entity_name] = []
                entity_warnings[entity_name].append(clean_warning_message(warning_msg))

    return entity_warnings


def _get_entity_registry(cruise_instance: "CruiseInstance", registry_name: str) -> dict:
    """Get entity registry by name, returns empty dict if not found."""
    if hasattr(cruise_instance, registry_name):
        return getattr(cruise_instance, registry_name)
    return {}


def _format_warning_groups(warning_groups: dict) -> list[str]:
    """Format categorized warning groups into user-friendly output sections."""
    formatted_sections = []

    # Format entity-specific warnings
    for group_name in ["Points", "Lines", "Areas"]:
        if warning_groups[group_name]:
            formatted_section = _format_entity_warnings(
                group_name, warning_groups[group_name]
            )
            formatted_sections.append(formatted_section)

    # Add configuration warnings
    if warning_groups["Configuration"]:
        lines = ["Configuration:"]
        for warning in warning_groups["Configuration"]:
            lines.append(f"  - {warning}")
        formatted_sections.append("\n".join(lines))

    return formatted_sections


def _format_entity_warnings(
    group_name: str, entity_warnings: dict[str, list[str]]
) -> str:
    """Format warnings for a specific entity group (Points/Lines/Areas)."""
    lines = [f"{group_name}:"]
    # Sort entity names alphabetically
    for entity_name in sorted(entity_warnings.keys()):
        warnings_for_entity = entity_warnings[entity_name]
        for warning in warnings_for_entity:
            lines.append(f"  - {entity_name}: {warning}")
    return "\n".join(lines)


def warning_relates_to_entity(
    warning_msg: str, entity: Union[PointDefinition, LineDefinition, AreaDefinition]
) -> bool:
    """
    Check if a Pydantic warning message relates to a specific entity.

    Uses text pattern matching to determine which station/line/area a validation
    error belongs to by checking if entity field values appear in the warning text.

    Parameters
    ----------
    warning_msg : str
        Raw Pydantic validation warning message
    entity : Union[PointDefinition, LineDefinition, AreaDefinition]
        Entity to check against the warning message

    Returns
    -------
    bool
        True if the warning appears to relate to this entity
    """
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
    """
    Clean up Pydantic validation warnings for user display.

    Removes technical Pydantic-specific text and formats warnings in a more
    user-friendly way.

    Parameters
    ----------
    warning_msg : str
        Raw Pydantic validation warning message

    Returns
    -------
    str
        Cleaned warning message suitable for display to users
    """
    cleaned = warning_msg.replace(
        "Duration is set to placeholder value ", "Duration is set to placeholder "
    )
    cleaned = cleaned.replace("Input should be ", "")
    cleaned = cleaned.replace(" (type=", " - expected ")

    return cleaned
