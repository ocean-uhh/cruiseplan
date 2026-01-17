"""
Cruise configuration serialization functions.

This module contains high-level business logic for serializing CruiseInstance objects back to
dictionary and YAML formats with proper field ordering and comment preservation.

**I/O Module Architecture:**
- **cruiseplan.utils.io**: File system validation, path handling, directory creation
- **cruiseplan.schema.yaml_io**: YAML file format reading/writing with comment preservation (used by this module)
- **cruiseplan.core.serialization** (this module): High-level CruiseInstance object serialization to YAML
- **cruiseplan.output.*_generator**: Specialized output format generators (HTML, LaTeX, CSV, etc.)

**Dependencies**: Uses `cruiseplan.schema.yaml_io` for YAML operations and `cruiseplan.utils.io` for file handling.

**See Also**:
- For file system operations: `cruiseplan.utils.io`
- For YAML file operations: `cruiseplan.schema.yaml_io`
- For generating specific output formats: `cruiseplan.output.html_generator`, `cruiseplan.output.latex_generator`, etc.
- For the enrichment process that uses these functions: `cruiseplan.core.enrichment`
"""

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

from cruiseplan.schema.activities import (
    AreaDefinition,
    LineDefinition,
    PointDefinition,
)
from cruiseplan.schema.cruise_config import ClusterDefinition, LegDefinition
from cruiseplan.schema.fields import (
    ACTIVITIES_FIELD,
    AREA_ALLOWED_FIELDS,
    AREA_VERTEX_FIELD,
    ARRIVAL_PORT_FIELD,
    CLUSTER_ALLOWED_FIELDS,
    DEPARTURE_PORT_FIELD,
    FIRST_ACTIVITY_FIELD,
    LAST_ACTIVITY_FIELD,
    LATITUDE_FIELD,
    LEG_ALLOWED_FIELDS,
    LINE_ALLOWED_FIELDS,
    LINE_VERTEX_FIELD,
    LONGITUDE_FIELD,
    POINT_ALLOWED_FIELDS,
)
from cruiseplan.schema.yaml_io import save_yaml

if TYPE_CHECKING:
    from cruiseplan.core.cruise import CruiseInstance

logger = logging.getLogger(__name__)


def deserialize_inline_definition(
    definition_dict: dict,
) -> Union[PointDefinition, LineDefinition, AreaDefinition]:
    """
    Convert an inline dictionary definition to the appropriate definition object.

    Determines the type of definition based on the presence of key fields
    and creates the corresponding Pydantic object.

    Parameters
    ----------
    definition_dict : dict
        Dictionary containing the inline definition fields.

    Returns
    -------
    Union[PointDefinition, LineDefinition, AreaDefinition]
        The appropriate definition object created from the dictionary.

    Raises
    ------
    ValueError
        If the definition type cannot be determined or validation fails.
    """
    # Determine definition type based on key fields (check most specific first)
    if LINE_VERTEX_FIELD in definition_dict:  # "route"
        return LineDefinition(**definition_dict)
    elif AREA_VERTEX_FIELD in definition_dict:
        return AreaDefinition(**definition_dict)
    # Fallback: assume it's a station if it has common station fields
    elif any(field in definition_dict for field in ["latitude", "longitude"]):
        # Add default operation_type if missing
        if "operation_type" not in definition_dict:
            definition_dict = definition_dict.copy()
            definition_dict["operation_type"] = (
                "CTD"  # Default operation type - TODO this doesn't seem right, do we have a default operation defined in defaults.py?
            )
        return PointDefinition(**definition_dict)
    else:
        raise ValueError(
            f"Cannot determine definition type for inline definition: {definition_dict}"
        )


def serialize_definition(
    obj: Union[
        PointDefinition,
        LineDefinition,
        AreaDefinition,
        ClusterDefinition,
        LegDefinition,
    ],
    allowed_fields: Union[list[str], set[str]],
) -> dict[str, Any]:
    """
    Convert a Pydantic definition object to a dictionary with field filtering.

    This function extracts only the allowed fields from the object, filtering out
    internal fields and maintaining canonical field ordering from YAML_FIELD_ORDER.

    Parameters
    ----------
    obj : Union[PointDefinition, LineDefinition, AreaDefinition, ClusterDefinition, LegDefinition]
        The Pydantic object to serialize
    allowed_fields : Union[list[str], set[str]]
        Collection of field names that should be included in the output.
        Field ordering is determined by YAML_FIELD_ORDER, not by this parameter.

    Returns
    -------
    dict[str, Any]
        Dictionary containing only the allowed fields with their values in canonical order
    """
    from cruiseplan.schema.fields import YAML_FIELD_ORDER

    output = {}

    # Serialize fields in canonical order using YAML_FIELD_ORDER
    # Only include fields that are in allowed_fields
    for _, pydantic_field in YAML_FIELD_ORDER:
        if pydantic_field in allowed_fields and hasattr(obj, pydantic_field):
            value = getattr(obj, pydantic_field)
            if value is not None:  # Skip None values to keep YAML clean
                # Convert enum values to strings for YAML serialization
                if isinstance(value, Enum):
                    output[pydantic_field] = value.value
                # Convert GeoPoint objects to coordinate dictionaries
                elif hasattr(value, "__iter__") and not isinstance(value, str):
                    # Handle lists of GeoPoint objects (e.g., route, corners)
                    converted_list = []
                    for item in value:
                        if hasattr(item, "latitude") and hasattr(item, "longitude"):
                            # This is a GeoPoint object
                            converted_list.append(
                                {
                                    LATITUDE_FIELD: item.latitude,
                                    LONGITUDE_FIELD: item.longitude,
                                }
                            )
                        else:
                            converted_list.append(item)
                    output[pydantic_field] = converted_list
                else:
                    output[pydantic_field] = value

    return output


def serialize_point_definition(point: PointDefinition) -> dict[str, Any]:
    """
    Serialize a PointDefinition to dictionary format.

    Parameters
    ----------
    point : PointDefinition
        The point definition to serialize

    Returns
    -------
    dict[str, Any]
        Serialized point definition dictionary
    """
    return serialize_definition(point, POINT_ALLOWED_FIELDS)


def serialize_line_definition(line: LineDefinition) -> dict[str, Any]:
    """
    Serialize a LineDefinition to dictionary format.

    Parameters
    ----------
    line : LineDefinition
        The line definition to serialize

    Returns
    -------
    dict[str, Any]
        Serialized line definition dictionary
    """
    return serialize_definition(line, LINE_ALLOWED_FIELDS)


def serialize_area_definition(area: AreaDefinition) -> dict[str, Any]:
    """
    Serialize an AreaDefinition to dictionary format.

    Parameters
    ----------
    area : AreaDefinition
        The area definition to serialize

    Returns
    -------
    dict[str, Any]
        Serialized area definition dictionary
    """
    return serialize_definition(area, AREA_ALLOWED_FIELDS)


def serialize_cluster_definition(cluster: ClusterDefinition) -> dict[str, Any]:
    """
    Serialize a ClusterDefinition to dictionary format.

    Parameters
    ----------
    cluster : ClusterDefinition
        The cluster definition to serialize

    Returns
    -------
    dict[str, Any]
        Serialized cluster definition dictionary
    """
    # Handle activities separately BEFORE calling serialize_definition
    # to avoid PointDefinition objects being converted to coordinate dictionaries
    activities_backup = None
    if hasattr(cluster, "activities") and cluster.activities:
        activities_backup = cluster.activities
        # Convert PointDefinition objects to string references
        activities_list = []
        for activity in cluster.activities:
            if hasattr(activity, "name"):
                # This is a PointDefinition object, use its name
                activities_list.append(activity.name)
            else:
                # This is already a string reference
                activities_list.append(activity)
        # Temporarily replace activities for serialization
        cluster.activities = activities_list

    # Now serialize with the string references
    output = serialize_definition(cluster, CLUSTER_ALLOWED_FIELDS)

    # Restore original activities
    if activities_backup is not None:
        cluster.activities = activities_backup

    return output


def _serialize_port_object(port_obj) -> dict[str, Any]:
    """Helper to serialize port objects for leg definitions."""
    if hasattr(port_obj, "name") and hasattr(port_obj, "latitude"):
        # This is a full PortDefinition object, serialize it
        return serialize_definition(port_obj, POINT_ALLOWED_FIELDS)
    return port_obj


def _convert_activity_to_name(activity) -> str:
    """Helper to convert activity object to string name reference."""
    if hasattr(activity, "name"):
        # This is a PointDefinition object, use its name
        return activity.name
    else:
        # This is already a string reference
        return activity


def serialize_leg_definition(leg: LegDefinition) -> dict[str, Any]:
    """
    Serialize a LegDefinition to dictionary format.

    Parameters
    ----------
    leg : LegDefinition
        The leg definition to serialize

    Returns
    -------
    dict[str, Any]
        Serialized leg definition dictionary
    """
    output = serialize_definition(leg, LEG_ALLOWED_FIELDS)

    # Handle special serialization for nested port objects
    if hasattr(leg, DEPARTURE_PORT_FIELD) and leg.departure_port:
        output[DEPARTURE_PORT_FIELD] = _serialize_port_object(leg.departure_port)

    if hasattr(leg, ARRIVAL_PORT_FIELD) and leg.arrival_port:
        output[ARRIVAL_PORT_FIELD] = _serialize_port_object(leg.arrival_port)

    # Handle clusters within legs
    if hasattr(leg, "clusters") and leg.clusters:
        output["clusters"] = [
            serialize_cluster_definition(cluster) for cluster in leg.clusters
        ]

    # Handle activities - convert PointDefinition objects back to string references
    if hasattr(leg, ACTIVITIES_FIELD) and leg.activities:
        output[ACTIVITIES_FIELD] = [
            _convert_activity_to_name(activity) for activity in leg.activities
        ]

    # Handle first_activity - convert PointDefinition object back to string reference
    if hasattr(leg, FIRST_ACTIVITY_FIELD) and leg.first_activity:
        output[FIRST_ACTIVITY_FIELD] = _convert_activity_to_name(leg.first_activity)

    # Handle last_activity - convert PointDefinition object back to string reference
    if hasattr(leg, LAST_ACTIVITY_FIELD) and leg.last_activity:
        output[LAST_ACTIVITY_FIELD] = _convert_activity_to_name(leg.last_activity)

    return output


def to_commented_dict(cruise_instance: "CruiseInstance") -> dict[str, Any]:
    """
    Export CruiseInstance configuration to a structured dictionary with comment preservation.

    This method provides the foundation for YAML output with canonical field
    ordering and comment preservation capabilities. Returns a dictionary that
    can be processed by ruamel.yaml for structured output with comments.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to serialize

    Returns
    -------
    Dict[str, Any]
        Dictionary with canonical field ordering suitable for YAML export
        with comment preservation.

    Notes
    -----
    The output dictionary follows canonical ordering:
    1. Cruise Metadata (cruise_name, description, start_date, start_time)
    2. Vessel Parameters (default_vessel_speed, turnaround_time, etc.)
    3. Calculation Settings (calculate_*, day_start_hour, etc.)
    4. Catalog Definitions (points, lines, areas, ports)
    5. Schedule Organization (legs)

    Comment preservation is handled at the YAML layer using ruamel.yaml
    with end-of-line and section header comment support.
    """
    from cruiseplan.schema.fields import (
        AREAS_FIELD,
        LEGS_FIELD,
        LINES_FIELD,
        POINTS_FIELD,
        PORTS_FIELD,
        YAML_FIELD_ORDER,
    )

    # Start with canonical field ordering
    output = {}

    # Serialize cruise-level fields in canonical order using YAML_FIELD_ORDER
    for yaml_field, pydantic_field in YAML_FIELD_ORDER:
        if hasattr(cruise_instance.config, pydantic_field):
            value = getattr(cruise_instance.config, pydantic_field)
            if value is not None:
                output[yaml_field] = value

    # Handle special port serialization for global departure/arrival ports
    if (
        hasattr(cruise_instance.config, DEPARTURE_PORT_FIELD)
        and cruise_instance.config.departure_port
    ):
        output[DEPARTURE_PORT_FIELD] = serialize_point_definition(
            cruise_instance.config.departure_port
        )

    if (
        hasattr(cruise_instance.config, ARRIVAL_PORT_FIELD)
        and cruise_instance.config.arrival_port
    ):
        output[ARRIVAL_PORT_FIELD] = serialize_point_definition(
            cruise_instance.config.arrival_port
        )

    # Serialize catalog definitions
    if cruise_instance.point_registry:
        output[POINTS_FIELD] = [
            serialize_point_definition(p)
            for p in cruise_instance.point_registry.values()
        ]

    if cruise_instance.line_registry:
        output[LINES_FIELD] = [
            serialize_line_definition(line)
            for line in cruise_instance.line_registry.values()
        ]

    if cruise_instance.area_registry:
        output[AREAS_FIELD] = [
            serialize_area_definition(a) for a in cruise_instance.area_registry.values()
        ]

    # Serialize ports catalog if it exists (separate from global departure/arrival ports)
    if hasattr(cruise_instance.config, "ports") and cruise_instance.config.ports:
        output[PORTS_FIELD] = [
            serialize_point_definition(p) for p in cruise_instance.config.ports
        ]

    # Serialize legs with their hierarchical structure
    if hasattr(cruise_instance.config, "legs") and cruise_instance.config.legs:
        output[LEGS_FIELD] = [
            serialize_leg_definition(leg) for leg in cruise_instance.config.legs
        ]

    return output


def to_yaml(
    cruise_instance: "CruiseInstance",
    output_file: Optional[Union[str, Path]] = None,
    backup: bool = True,
    add_comments: bool = True,
) -> Optional[str]:
    """
    Export CruiseInstance configuration to YAML format with comment preservation.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to serialize
    output_file : Optional[Union[str, Path]], optional
        Path to write YAML file. If None, returns YAML string.
    backup : bool, optional
        Whether to create backup of existing file (default: True)
    add_comments : bool, optional
        Whether to add descriptive comments to YAML (default: True)

    Returns
    -------
    Optional[str]
        YAML string if output_file is None, otherwise None

    Examples
    --------
    >>> # Save to file
    >>> cruise.to_yaml("enhanced_cruise.yaml")
    >>> # Get YAML string
    >>> yaml_str = cruise.to_yaml()
    """
    # Generate the dictionary representation
    output_dict = to_commented_dict(cruise_instance)

    if output_file is not None:
        # Save to file
        output_path = Path(output_file)
        save_yaml(output_dict, output_path, backup=backup)
        logger.info(f"Saved cruise configuration to {output_path}")
        return None
    else:
        # Return as string
        from cruiseplan.schema.yaml_io import dict_to_yaml_string

        return dict_to_yaml_string(output_dict, add_comments=add_comments)
