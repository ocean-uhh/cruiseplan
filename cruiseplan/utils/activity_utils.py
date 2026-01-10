"""
Activity and scheduling utility functions.

Shared utilities for processing cruise activities across different output generators.
"""

from typing import Any


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


# Note: Coordinate conversion functions are available in cruiseplan.utils.coordinates
# Use CoordConverter.decimal_degrees_to_ddm() for coordinate conversions
