import math
from typing import List, Tuple, Union

from cruiseplan.core.validation import GeoPoint

# Earth radius in kilometers (approximate)
R_EARTH_KM = 6371.0
NM_PER_KM = 0.539957
KM_PER_NM = 1.852


def to_coords(point: Union[GeoPoint, Tuple[float, float]]) -> Tuple[float, float]:
    """Helper to extract (lat, lon) from various input types."""
    if isinstance(point, GeoPoint):
        return (point.latitude, point.longitude)
    if isinstance(point, dict) and "latitude" in point and "longitude" in point:
        return (point["latitude"], point["longitude"])
    return point


def haversine_distance(
    start: Union[GeoPoint, Tuple[float, float]],
    end: Union[GeoPoint, Tuple[float, float]],
) -> float:
    """Calculate Great Circle distance in Kilometers between two points."""
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


def route_distance(points: List[Union[GeoPoint, Tuple[float, float]]]) -> float:
    """Calculate total distance of a path in Kilometers."""
    if not points or len(points) < 2:
        return 0.0

    total = 0.0
    for i in range(len(points) - 1):
        total += haversine_distance(points[i], points[i + 1])
    return total


def km_to_nm(km: float) -> float:
    return km * NM_PER_KM


def nm_to_km(nm: float) -> float:
    return nm * KM_PER_NM
