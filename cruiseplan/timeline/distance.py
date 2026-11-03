"""
Geographic distance calculations for cruise planning.

This module provides functions for calculating distances between geographic points
using the Haversine formula, which gives Great Circle distances on a spherical Earth.
Includes utilities for route distance calculation and unit conversions between
kilometers and nautical miles.
"""

from cruiseplan.config.activities import GeoPoint
from cruiseplan.utils.coordinates import distance_nm
from cruiseplan.utils.units import NM_PER_KM


def to_coords(point: GeoPoint | tuple[float, float]) -> tuple[float, float]:
    """
    Extract (latitude, longitude) coordinates from various input types.

    Parameters
    ----------
    point : GeoPoint or tuple of float
        Input point as either a GeoPoint object or (lat, lon) tuple.

    Returns
    -------
    tuple of float
        (latitude, longitude) coordinates in decimal degrees.
    """
    if isinstance(point, GeoPoint):
        return (point.latitude, point.longitude)
    if isinstance(point, dict) and "latitude" in point and "longitude" in point:
        return (point["latitude"], point["longitude"])
    return point


def haversine_distance(
    start: GeoPoint | tuple[float, float],
    end: GeoPoint | tuple[float, float],
) -> float:
    """
    Calculate Great Circle distance between two points using Haversine formula.

    Parameters
    ----------
    start : GeoPoint or tuple of float
        Starting point coordinates.
    end : GeoPoint or tuple of float
        Ending point coordinates.

    Returns
    -------
    float
        Distance in kilometers.
    """
    return distance_nm(to_coords(start), to_coords(end)) / NM_PER_KM


def route_distance(points: list[GeoPoint | tuple[float, float]]) -> float:
    """
    Calculate total distance of a path connecting multiple points.

    Parameters
    ----------
    points : list of GeoPoint or tuple of float
        Ordered list of points defining the route.

    Returns
    -------
    float
        Total route distance in kilometers.
    """
    if not points or len(points) < 2:
        return 0.0

    total = 0.0
    for i in range(len(points) - 1):
        total += haversine_distance(points[i], points[i + 1])
    return total
