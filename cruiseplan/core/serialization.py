"""
Cruise configuration serialization functions.

This module contains functions for serializing CruiseInstance objects back to
dictionary and YAML formats with proper field ordering and comment preservation.
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
from cruiseplan.schema.vocabulary import (
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
from cruiseplan.utils.yaml_io import save_yaml

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
    allowed_fields: list[str],
) -> dict[str, Any]:
    """
    Convert a Pydantic definition object to a dictionary with field filtering.

    This function extracts only the allowed fields from the object, filtering out
    internal fields and maintaining canonical field ordering.

    Parameters
    ----------
    obj : Union[PointDefinition, LineDefinition, AreaDefinition, ClusterDefinition, LegDefinition]
        The Pydantic object to serialize
    allowed_fields : list[str]
        List of field names that should be included in the output

    Returns
    -------
    dict[str, Any]
        Dictionary containing only the allowed fields with their values
    """
    output = {}

    # Serialize only the allowed fields in canonical order
    for field_name in allowed_fields:
        if hasattr(obj, field_name):
            value = getattr(obj, field_name)
            if value is not None:  # Skip None values to keep YAML clean
                # Convert enum values to strings for YAML serialization
                if isinstance(value, Enum):
                    output[field_name] = value.value
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
                    output[field_name] = converted_list
                else:
                    output[field_name] = value

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
    return serialize_definition(cluster, CLUSTER_ALLOWED_FIELDS)


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
        port_obj = leg.departure_port
        if hasattr(port_obj, "name") and hasattr(port_obj, "latitude"):
            # This is a full PortDefinition object, serialize it
            output[DEPARTURE_PORT_FIELD] = serialize_definition(
                port_obj, POINT_ALLOWED_FIELDS
            )

    if hasattr(leg, ARRIVAL_PORT_FIELD) and leg.arrival_port:
        port_obj = leg.arrival_port
        if hasattr(port_obj, "name") and hasattr(port_obj, "latitude"):
            # This is a full PortDefinition object, serialize it
            output[ARRIVAL_PORT_FIELD] = serialize_definition(
                port_obj, POINT_ALLOWED_FIELDS
            )

    # Handle clusters within legs
    if hasattr(leg, "clusters") and leg.clusters:
        output["clusters"] = [
            serialize_definition(cluster, CLUSTER_ALLOWED_FIELDS)
            for cluster in leg.clusters
        ]

    # Handle activities - convert PointDefinition objects back to string references
    if hasattr(leg, ACTIVITIES_FIELD) and leg.activities:
        activities_list = []
        for activity in leg.activities:
            if hasattr(activity, "name"):
                # This is a PointDefinition object, use its name
                activities_list.append(activity.name)
            else:
                # This is already a string reference
                activities_list.append(activity)
        output[ACTIVITIES_FIELD] = activities_list

    # Handle first_activity - convert PointDefinition object back to string reference
    if hasattr(leg, FIRST_ACTIVITY_FIELD) and leg.first_activity:
        if hasattr(leg.first_activity, "name"):
            # This is a PointDefinition object, use its name
            output[FIRST_ACTIVITY_FIELD] = leg.first_activity.name
        else:
            # This is already a string reference
            output[FIRST_ACTIVITY_FIELD] = leg.first_activity

    # Handle last_activity - convert PointDefinition object back to string reference
    if hasattr(leg, LAST_ACTIVITY_FIELD) and leg.last_activity:
        if hasattr(leg.last_activity, "name"):
            # This is a PointDefinition object, use its name
            output[LAST_ACTIVITY_FIELD] = leg.last_activity.name
        else:
            # This is already a string reference
            output[LAST_ACTIVITY_FIELD] = leg.last_activity

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
    from cruiseplan.schema.vocabulary import (
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
            serialize_line_definition(l) for l in cruise_instance.line_registry.values()
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
        save_yaml(output_dict, output_path, backup=backup, add_comments=add_comments)
        logger.info(f"Saved cruise configuration to {output_path}")
        return None
    else:
        # Return as string
        from cruiseplan.utils.yaml_io import dict_to_yaml_string

        return dict_to_yaml_string(output_dict, add_comments=add_comments)
