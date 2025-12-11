"""
Activity and scheduling utility functions.
Shared utilities for processing cruise activities across different output generators.
"""

from datetime import datetime
from typing import Any, Dict


def is_scientific_operation(activity: Dict[str, Any]) -> bool:
    """
    Determine if an activity should be included as a scientific operation.

    Include: Stations, Moorings, and Scientific Transits (with action field).
    Exclude: Pure Navigation Transits (without action field).

    Parameters
    ----------
    activity : Dict[str, Any]
        Activity record from timeline

    Returns
    -------
    bool
        True if this is a scientific operation
    """
    if activity["activity"] in ["Station", "Mooring", "Area"]:
        return True
    elif activity["activity"] == "Transit":
        # Scientific transit if it has an action field
        return activity.get("action") is not None
    return False


def is_scientific_transit(transit: Dict[str, Any]) -> bool:
    """
    Distinguish a Transit activity as scientific based on the presence of the
    'action' field, as per the schema change description.

    Scientific Transits: Have 'action' field (ADCP, bathymetry, etc.)
    Pure Navigation Transits: Lack the 'action' field.

    Parameters
    ----------
    transit : Dict[str, Any]
        Transit activity record from timeline

    Returns
    -------
    bool
        True if this is a scientific transit
    """
    return transit.get("activity") == "Transit" and transit.get("action") is not None


def is_line_operation(activity: Dict[str, Any]) -> bool:
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


def round_time_to_minute(dt: datetime) -> datetime:
    """
    Round datetime to nearest minute.

    Parameters
    ----------
    dt : datetime
        Input datetime

    Returns
    -------
    datetime
        Datetime rounded to nearest minute
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
# Use UnitConverter.decimal_degrees_to_dmm() for coordinate conversions
