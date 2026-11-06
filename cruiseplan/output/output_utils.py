"""
Shared utility functions for output generators.

This module contains common utility functions used across different output
format generators (CSV, HTML, LaTeX, etc.) to ensure consistency and reduce
code duplication.
"""

from datetime import datetime

from cruiseplan.config.values import DEFAULT_DEPTH
from cruiseplan.timeline.record import ActivityRecord


def _positive_depth(value: float) -> float:
    """Return ``abs(value)``, or the fill value unchanged so it stays visible."""
    value = float(value)
    return value if value == DEFAULT_DEPTH else abs(value)


def _duration_hours(activity: ActivityRecord) -> tuple[str, bool]:
    """Return the duration in hours to one decimal and whether it is the fill value."""
    return f"{activity.duration_minutes / 60:.1f}", activity.duration_is_fill


def get_activity_depth(activity: ActivityRecord) -> float:
    """
    Return the depth of a record: operation depth, else water depth, else 0.

    Parameters
    ----------
    activity : ActivityRecord
        Timeline record.

    Returns
    -------
    float
        Positive depth in meters (``DEFAULT_DEPTH`` kept as is), or 0.0 when
        the record has no depth.
    """
    depth = activity.depth_m
    return 0.0 if depth is None else _positive_depth(depth)


def get_activity_position(activity: ActivityRecord) -> tuple[float, float]:
    """
    Return the entry position of a record.

    Parameters
    ----------
    activity : ActivityRecord
        Timeline record.

    Returns
    -------
    tuple of float
        (latitude, longitude) in decimal degrees.
    """
    return float(activity.entry_lat), float(activity.entry_lon)


def format_activity_type(activity: ActivityRecord) -> str:
    """
    Format the operation type and action of a record, e.g. "CTD profile".

    Parameters
    ----------
    activity : ActivityRecord
        Timeline record.

    Returns
    -------
    str
        Formatted activity type.
    """
    op_type = activity.op_type
    if op_type.upper() in ["CTD", "ADCP", "GPS", "USBL"]:
        formatted_op_type = op_type.upper()
    else:
        formatted_op_type = op_type.title()
    if activity.action:
        return f"{formatted_op_type} {activity.action}"
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
    if operation_type == "mooring" and action_str.lower() == "deployment":
        return "Mooring deployment"
    if operation_type == "mooring" and action_str.lower() == "recovery":
        return "Mooring recovery"
    if operation_type == "transit":
        if action_str:
            return f"Transit ({action_str})"
        return "Transit"
    if operation_type and action_str:
        return f"{operation_type.title()} {action_str}"
    if operation_type:
        return operation_type.title()
    return ""
