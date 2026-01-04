"""
Common utilities for operation handling across the cruiseplan system.

This module provides shared functions for operation calculations and
coordinate handling to reduce code duplication.
"""

from typing import Any, Optional

from cruiseplan.calculators import duration as calc


def calculate_common_duration(
    operation_depth: Optional[float], op_type: str, rules: Any
) -> float:
    """
    Calculate duration for operations based on type and depth.

    Centralizes the logic for CTD-style operations that require depth-based
    duration calculations.

    Parameters
    ----------
    operation_depth : Optional[float]
        Depth of operation in meters, or None for non-depth operations
    op_type : str
        Operation type identifier (e.g., "CTD", "station", "ADCP")
    rules : Any
        Duration calculation rules and parameters

    Returns
    -------
    float
        Duration in minutes
    """
    # Check if this is a depth-based operation
    depth_based_types = ["station", "CTD", "ADCP", "XBT", "XCTD"]

    if op_type in depth_based_types or (
        operation_depth is not None and operation_depth > 0
    ):
        depth = operation_depth or 0.0
        return calc.calculate_ctd_time(depth)

    # Default to zero for operations without depth
    return 0.0


def get_operation_distance_nm(waypoints: list) -> float:
    """
    Calculate total distance for multi-waypoint operations.

    Parameters
    ----------
    waypoints : list
        List of coordinate tuples [(lat1, lon1), (lat2, lon2), ...]

    Returns
    -------
    float
        Total distance in nautical miles
    """
    if len(waypoints) < 2:
        return 0.0

    from cruiseplan.calculators.distance import km_to_nm, route_distance

    # Convert to the format expected by route_distance
    points = [(wp[0], wp[1]) for wp in waypoints]
    distance_km = route_distance(points)

    return km_to_nm(distance_km)


def get_standard_entry_point(
    operation_class: str, coordinates: Any
) -> tuple[float, float]:
    """
    Get entry point using standard logic for different operation types.

    Parameters
    ----------
    operation_class : str
        Class of operation (point, line, area)
    coordinates : Any
        Operation coordinates (varies by type)

    Returns
    -------
    tuple[float, float]
        (latitude, longitude) of entry point
    """
    if operation_class == "point":
        return (coordinates.latitude, coordinates.longitude)
    elif operation_class == "line":
        return (coordinates.start.latitude, coordinates.start.longitude)
    elif operation_class == "area":
        # For areas, use first waypoint as entry
        if hasattr(coordinates, "waypoints") and coordinates.waypoints:
            first_wp = coordinates.waypoints[0]
            return (first_wp.latitude, first_wp.longitude)
        # Fallback to centroid
        return (coordinates.latitude, coordinates.longitude)
    else:
        msg = f"Unknown operation class: {operation_class}"
        raise ValueError(msg)


def get_standard_exit_point(
    operation_class: str, coordinates: Any
) -> tuple[float, float]:
    """
    Get exit point using standard logic for different operation types.

    Parameters
    ----------
    operation_class : str
        Class of operation (point, line, area)
    coordinates : Any
        Operation coordinates (varies by type)

    Returns
    -------
    tuple[float, float]
        (latitude, longitude) of exit point
    """
    if operation_class == "point":
        return (coordinates.latitude, coordinates.longitude)
    elif operation_class == "line":
        return (coordinates.end.latitude, coordinates.end.longitude)
    elif operation_class == "area":
        # For areas, use last waypoint as exit
        if hasattr(coordinates, "waypoints") and coordinates.waypoints:
            last_wp = coordinates.waypoints[-1]
            return (last_wp.latitude, last_wp.longitude)
        # Fallback to centroid
        return (coordinates.latitude, coordinates.longitude)
    else:
        msg = f"Unknown operation class: {operation_class}"
        raise ValueError(msg)
