"""
Shared utility functions for output generators.

This module contains common utility functions used across different output
format generators (CSV, HTML, LaTeX, etc.) to ensure consistency and reduce
code duplication.
"""

from datetime import datetime
from typing import Any


def get_activity_depth(activity: dict) -> float:
    """
    Get depth for an activity using the same logic as Operation.get_depth().

    Prioritizes operation_depth over water_depth, with backward compatibility
    for the legacy 'depth' field.

    Parameters
    ----------
    activity : dict
        Activity record with depth information

    Returns
    -------
    float
        Depth value as float, or 0.0 if no depth available
    """
    operation_depth = activity.get("operation_depth")
    if operation_depth is not None:
        return abs(float(operation_depth))

    water_depth = activity.get("water_depth")
    if water_depth is not None:
        return abs(float(water_depth))

    legacy_depth = activity.get("depth")  # Backward compatibility
    if legacy_depth is not None:
        return abs(float(legacy_depth))

    return 0.0


def get_activity_position(activity: dict) -> tuple[float, float]:
    """
    Get latitude and longitude for an activity using modern field names with legacy fallback.

    Parameters
    ----------
    activity : dict
        Activity record with position information

    Returns
    -------
    tuple[float, float]
        (latitude, longitude) as floats, or (0.0, 0.0) if no position available
    """
    # Use modern field names with fallback to legacy
    lat = activity.get("entry_lat", activity.get("lat", 0.0))
    lon = activity.get("entry_lon", activity.get("lon", 0.0))
    return float(lat), float(lon)


def format_activity_type(activity: dict) -> str:
    """
    Format activity type using op_type and action fields.

    Creates formatted strings like "CTD profile", "Port mob", "Transit", etc.

    Parameters
    ----------
    activity : dict
        Activity record with op_type and action information

    Returns
    -------
    str
        Formatted activity type string
    """
    op_type = activity.get("op_type", "Unknown")
    action = activity.get("action")

    # Preserve case for known acronyms
    if op_type.upper() in ["CTD", "ADCP", "CTD", "GPS", "USBL"]:
        formatted_op_type = op_type.upper()
    else:
        formatted_op_type = op_type.title()

    if action:
        # Format as "op_type action" (e.g. "CTD profile", "Port mob")
        return f"{formatted_op_type} {action}"
    else:
        # Just use op_type for things like "Transit" without action
        return formatted_op_type


def round_time_to_minute(dt: datetime) -> datetime:
    """
    Round datetime to nearest minute for clean output timestamps.

    Utility function for standardizing time formatting by removing
    seconds and microseconds components for clean output display.

    Parameters
    ----------
    dt : datetime
        Input datetime

    Returns
    -------
    datetime
        Datetime rounded to nearest minute

    Examples
    --------
    >>> from datetime import datetime
    >>> round_time_to_minute(datetime(2023, 1, 1, 12, 30, 45))
    datetime(2023, 1, 1, 12, 30)
    """
    return dt.replace(second=0, microsecond=0)


def is_scientific_operation(activity: dict[str, Any]) -> bool:
    """
    Determine if an activity should be included as a scientific operation.

    Include: PointOperation, LineOperation, AreaOperation.
    Exclude: PortOperation and NavigationalTransit.

    Parameters
    ----------
    activity : Dict[str, Any]
        Activity record from timeline

    Returns
    -------
    bool
        True if this is a scientific operation
    """
    operation_class = activity.get("operation_class", "")
    if operation_class:
        return operation_class in ["PointOperation", "LineOperation", "AreaOperation"]

    # Backward compatibility: check activity type for legacy test data
    activity_type = activity.get("activity", "")
    return activity_type in ["Station", "Mooring", "Area", "Line"]


def is_line_operation(activity: dict[str, Any]) -> bool:
    """
    Check if activity is a line operation (scientific transit with start/end coordinates).

    Parameters
    ----------
    activity : Dict[str, Any]
        Activity record from timeline

    Returns
    -------
    bool
        True if this is a line operation
    """
    return (
        activity["activity"] == "Transit"
        and activity.get("action") is not None
        and activity.get("start_lat") is not None
        and activity.get("start_lon") is not None
    )


def format_operation_action(operation_type: str, action: str) -> str:
    """
    Format operation type and action into combined description.

    Parameters
    ----------
    operation_type : str
        Type of operation (e.g., "ctd", "mooring", "transit")
    action : str
        Action being performed (e.g., "profile", "deployment", "recovery")

    Returns
    -------
    str
        Formatted operation description
    """
    if not operation_type:
        return ""

    operation_type = str(operation_type).lower()
    action_str = str(action) if action else ""

    # Handle different operation types
    if operation_type == "ctd" and action_str.lower() == "profile":
        return "CTD profile"
    elif operation_type == "mooring" and action_str.lower() == "deployment":
        return "Mooring deployment"
    elif operation_type == "mooring" and action_str.lower() == "recovery":
        return "Mooring recovery"
    elif operation_type == "transit":
        if action_str:
            return f"Transit ({action_str})"
        else:
            return "Transit"
    elif operation_type and action_str:
        return f"{operation_type.title()} {action_str}"
    elif operation_type:
        return operation_type.title()
    else:
        return ""
