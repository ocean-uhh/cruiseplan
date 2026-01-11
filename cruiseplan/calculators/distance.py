"""
Geographic distance calculations for cruise planning.

This module provides functions for calculating distances between geographic points
using the Haversine formula, which gives Great Circle distances on a spherical Earth.
Includes utilities for route distance calculation and unit conversions between
kilometers and nautical miles.
"""

import math
from typing import Union

from cruiseplan.schema import GeoPoint

# Earth radius in kilometers (WGS84 approximate) - used for haversine distance calculation
R_EARTH_KM = 6371.0


def to_coords(point: Union[GeoPoint, tuple[float, float]]) -> tuple[float, float]:
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
    start: Union[GeoPoint, tuple[float, float]],
    end: Union[GeoPoint, tuple[float, float]],
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
    lat1, lon1 = to_coords(start)
    lat2, lon2 = to_coords(end)

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R_EARTH_KM * c


def route_distance(points: list[Union[GeoPoint, tuple[float, float]]]) -> float:
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
