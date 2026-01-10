"""
Shared utility functions for output generators.

This module contains common utility functions used across different output
format generators (CSV, HTML, LaTeX, etc.) to ensure consistency and reduce
code duplication.
"""

from datetime import datetime


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
