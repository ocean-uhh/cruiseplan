"""
Coordinate formatting utilities for scientific and maritime applications.

This module provides functions to format coordinates in various standard formats
used in oceanographic and maritime contexts, including decimal degrees, degrees
and decimal minutes (DMM), and LaTeX-formatted output. Also includes utilities
for extracting coordinates from cruise configurations and calculating map bounds.

Notes
-----
All coordinate functions expect input in decimal degrees and handle both
northern/eastern (positive) and southern/western (negative) coordinates.
The UnitConverter class provides static methods for coordinate conversions.
"""

import math
import re
from typing import List, Optional, Tuple


class UnitConverter:
    """
    Utility class for coordinate unit conversions.

    This class provides static methods for converting between different
    coordinate representations commonly used in maritime and scientific contexts.
    """

    @staticmethod
    def decimal_degrees_to_dmm(decimal_degrees: float) -> Tuple[float, float]:
        """
        Convert decimal degrees to degrees and decimal minutes.

        Parameters
        ----------
        decimal_degrees : float
            Coordinate in decimal degrees format.

        Returns
        -------
        tuple of float
            Tuple of (degrees, decimal_minutes).

        Examples
        --------
        >>> UnitConverter.decimal_degrees_to_dmm(65.7458)
        (65.0, 44.75)
        """
        degrees = int(abs(decimal_degrees))
        minutes = (abs(decimal_degrees) - degrees) * 60
        return float(degrees), minutes


def format_dmm_comment(lat: float, lon: float) -> str:
    """
    Format coordinates as degrees/decimal minutes comment for validator compliance.

    This function generates DMM format that passes the strict validator requirements:
    - DD MM.MM'N, DDD MM.MM'W format (degrees and decimal minutes)
    - No degree symbols (°)
    - 2-digit latitude degrees, 3-digit longitude degrees with leading zeros
    - Exactly 2 decimal places for minutes

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.

    Returns
    -------
    str
        DMM comment like "65 44.75'N, 024 28.75'W".

    Examples
    --------
    >>> format_dmm_comment(65.7458, -24.4792)
    "65 44.75'N, 024 28.75'W"
    """
    # Convert to degrees and decimal minutes
    lat_deg, lat_min = UnitConverter.decimal_degrees_to_dmm(lat)
    lon_deg, lon_min = UnitConverter.decimal_degrees_to_dmm(lon)

    # Determine directions
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"

    # Format with required precision: DD MM.MM'N, DDD MM.MM'W
    lat_str = f"{abs(int(lat_deg)):02d} {lat_min:05.2f}'{lat_dir}"
    lon_str = f"{abs(int(lon_deg)):03d} {lon_min:05.2f}'{lon_dir}"

    return f"{lat_str}, {lon_str}"


def format_position_string(lat: float, lon: float, format_type: str = "dmm") -> str:
    """
    Format coordinate pair as a position string.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.
    format_type : str, optional
        Format type - 'dmm' for degrees/decimal minutes, 'decimal' for decimal degrees.
        Default is 'dmm'.

    Returns
    -------
    str
        Formatted position string.

    Examples
    --------
    >>> format_position_string(65.7458, -24.4792, "dmm")
    "65 44.75'N, 024 28.75'W"
    >>> format_position_string(65.7458, -24.4792, "decimal")
    "65.7458°N, 24.4792°W"
    """
    if format_type == "dmm":
        return format_dmm_comment(lat, lon)
    elif format_type == "decimal":
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        return f"{abs(lat):.4f}°{lat_dir}, {abs(lon):.4f}°{lon_dir}"
    else:
        raise ValueError(f"Unsupported format_type: {format_type}")


def format_position_latex(lat: float, lon: float) -> str:
    """
    Format coordinates for LaTeX output with proper symbols.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.

    Returns
    -------
    str
        LaTeX-formatted position string.

    Examples
    --------
    >>> format_position_latex(65.7458, -24.4792)
    "65$^\\circ$44.75'N, 024$^\\circ$28.75'W"
    """
    # Convert to degrees and decimal minutes
    lat_deg, lat_min = UnitConverter.decimal_degrees_to_dmm(lat)
    lon_deg, lon_min = UnitConverter.decimal_degrees_to_dmm(lon)

    # Determine directions
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"

    # Format with LaTeX degree symbols
    lat_str = f"{abs(int(lat_deg)):02d}$^\\circ${lat_min:05.2f}'{lat_dir}"
    lon_str = f"{abs(int(lon_deg)):03d}$^\\circ${lon_min:05.2f}'{lon_dir}"

    return f"{lat_str}, {lon_str}"


def parse_dmm_format(coords_str: str) -> Tuple[float, float]:
    """
    Parse degrees/decimal minutes format with direction indicators.

    A simpler version that handles common coordinate string formats.

    Parameters
    ----------
    coords_str : str
        Coordinate string in DMM format.

    Returns
    -------
    tuple of float
        Tuple of (latitude, longitude) in decimal degrees.

    Examples
    --------
    >>> parse_dmm_format("52° 49.99' N, 51° 32.81' W")
    (52.83316666666667, -51.54683333333333)
    >>> parse_dmm_format("52°49.99'N,51°32.81'W")
    (52.83316666666667, -51.54683333333333)
    >>> parse_dmm_format("56° 34,50' N, 52° 40,33' W")  # European comma
    (56.575, -52.6721666666667)
    """
    # Handle different quote characters and European decimal comma
    coords_str = coords_str.replace("′", "'").replace('"', "'").replace('"', "'")

    # Replace European decimal comma with dot in decimal numbers
    coords_str = re.sub(r"(\d+),(\d+)", r"\1.\2", coords_str)

    # Pattern for degrees and decimal minutes with direction
    pattern = r"(\d+)°\s*(\d+(?:\.\d+)?)[\'′]?\s*([NS]),?\s*(\d+)°\s*(\d+(?:\.\d+)?)[\'′]?\s*([EW])"

    match = re.search(pattern, coords_str)
    if not match:
        raise ValueError(f"DMM format not recognized: '{coords_str}'")

    lat_deg = int(match.group(1))
    lat_min = float(match.group(2))
    lat_dir = match.group(3)
    lon_deg = int(match.group(4))
    lon_min = float(match.group(5))
    lon_dir = match.group(6)

    # Convert to decimal degrees
    lat = lat_deg + lat_min / 60.0
    if lat_dir == "S":
        lat = -lat

    lon = lon_deg + lon_min / 60.0
    if lon_dir == "W":
        lon = -lon

    return lat, lon


def format_geographic_bounds(
    min_lon: float, min_lat: float, max_lon: float, max_lat: float
) -> str:
    """
    Format geographic bounding box coordinates with proper hemisphere indicators.

    Uses hemisphere indicators for non-zero coordinates:
    - W for negative longitude, E for positive longitude (nothing for 0° or 180°)
    - S for negative latitude, N for positive latitude (nothing for 0°)

    Parameters
    ----------
    min_lon : float
        Minimum longitude in decimal degrees
    min_lat : float
        Minimum latitude in decimal degrees
    max_lon : float
        Maximum longitude in decimal degrees
    max_lat : float
        Maximum latitude in decimal degrees

    Returns
    -------
    str
        Formatted bounds string with hemisphere indicators

    Examples
    --------
    >>> format_geographic_bounds(-90, 50, -30, 60)
    "50.00°N to 60.00°N, 90.00°W to 30.00°W"
    >>> format_geographic_bounds(270, 50, 330, 60)
    "50.00°N to 60.00°N, 270.00°E to 330.00°E"
    >>> format_geographic_bounds(-180, -45, 180, 45)
    "45.00°S to 45.00°N, 180.00° to 180.00°"
    """

    def format_coord(value: float, coord_type: str) -> str:
        """Format single coordinate with hemisphere indicator."""
        abs_val = abs(value)

        if coord_type == "lat":
            if value > 0:
                return f"{abs_val:.2f}°N"
            elif value < 0:
                return f"{abs_val:.2f}°S"
            else:  # value == 0
                return f"{abs_val:.2f}°"
        elif value > 0 and value != 180:
            return f"{abs_val:.2f}°E"
        elif value < 0 and value != -180:
            return f"{abs_val:.2f}°W"
        else:  # value == 0, 180, or -180
            return f"{abs_val:.2f}°"

    lat_bounds = f"{format_coord(min_lat, 'lat')} to {format_coord(max_lat, 'lat')}"
    lon_bounds = f"{format_coord(min_lon, 'lon')} to {format_coord(max_lon, 'lon')}"

    return f"{lat_bounds}, {lon_bounds}"


def extract_coordinates_from_cruise(
    cruise,
) -> Tuple[List[float], List[float], List[str], Optional[Tuple], Optional[Tuple]]:
    """
    Extract coordinates from cruise configuration.

    Parameters
    ----------
    cruise : Cruise
        Cruise object with station registry and configuration

    Returns
    -------
    tuple
        (all_lats, all_lons, station_names, departure_port, arrival_port)
        departure_port and arrival_port are tuples of (lat, lon, name) or None
    """
    all_lats = []
    all_lons = []
    station_names = []

    # Extract coordinates from all stations
    for station_name, station in cruise.station_registry.items():
        lat = (
            station.latitude
            if hasattr(station, "latitude")
            else station.position.latitude
        )
        lon = (
            station.longitude
            if hasattr(station, "longitude")
            else station.position.longitude
        )
        all_lats.append(lat)
        all_lons.append(lon)
        station_names.append(station_name)

    # Add departure and arrival ports if they exist
    departure_port = None
    arrival_port = None

    if hasattr(cruise.config, "departure_port") and cruise.config.departure_port:
        # Handle both resolved PortDefinition objects and string references
        if hasattr(cruise.config.departure_port, "latitude"):
            # Resolved PortDefinition object
            dep_lat = cruise.config.departure_port.latitude
            dep_lon = cruise.config.departure_port.longitude
            dep_name = cruise.config.departure_port.name
        elif hasattr(cruise.config.departure_port, "position"):
            # Legacy format with nested position object
            dep_lat = cruise.config.departure_port.position.latitude
            dep_lon = cruise.config.departure_port.position.longitude
            dep_name = cruise.config.departure_port.name
        else:
            # String reference - skip for now
            dep_lat = None
            dep_lon = None
            dep_name = None

        if dep_lat is not None and dep_lon is not None:
            departure_port = (dep_lat, dep_lon, dep_name)

    if hasattr(cruise.config, "arrival_port") and cruise.config.arrival_port:
        # Handle both resolved PortDefinition objects and string references
        if hasattr(cruise.config.arrival_port, "latitude"):
            # Resolved PortDefinition object
            arr_lat = cruise.config.arrival_port.latitude
            arr_lon = cruise.config.arrival_port.longitude
            arr_name = cruise.config.arrival_port.name
        elif hasattr(cruise.config.arrival_port, "position"):
            # Legacy format with nested position object
            arr_lat = cruise.config.arrival_port.position.latitude
            arr_lon = cruise.config.arrival_port.position.longitude
            arr_name = cruise.config.arrival_port.name
        else:
            # String reference - skip for now
            arr_lat = None
            arr_lon = None
            arr_name = None

        if arr_lat is not None and arr_lon is not None:
            arrival_port = (arr_lat, arr_lon, arr_name)

    return all_lats, all_lons, station_names, departure_port, arrival_port


def calculate_map_bounds(
    all_lats: List[float],
    all_lons: List[float],
    padding_percent: float = 0.05,
    padding_degrees: Optional[float] = None,
    apply_aspect_ratio: bool = True,
    round_to_degrees: bool = True,
) -> Tuple[float, float, float, float]:
    """
    Calculate map bounds with flexible padding and aspect ratio correction.

    Parameters
    ----------
    all_lats : list of float
        All latitude values to include
    all_lons : list of float
        All longitude values to include
    padding_percent : float, optional
        Padding as fraction of range (default 0.05 = 5%). Ignored if padding_degrees is set.
    padding_degrees : float, optional
        Fixed padding in degrees. If set, overrides padding_percent.
    apply_aspect_ratio : bool, optional
        Whether to apply geographic aspect ratio correction (default True)
    round_to_degrees : bool, optional
        Whether to round bounds outward to whole degrees (default True)

    Returns
    -------
    tuple
        (final_min_lon, final_max_lon, final_min_lat, final_max_lat)
    """
    if not all_lats or not all_lons:
        raise ValueError("No coordinates provided")

    # Calculate padding
    if padding_degrees is not None:
        padding = padding_degrees
    else:
        lat_range = max(all_lats) - min(all_lats)
        lon_range = max(all_lons) - min(all_lons)
        padding = max(lat_range, lon_range) * padding_percent

    # Apply padding
    min_lat_padded = min(all_lats) - padding
    max_lat_padded = max(all_lats) + padding
    min_lon_padded = min(all_lons) - padding
    max_lon_padded = max(all_lons) + padding

    # Round outwards to whole degrees (optional)
    if round_to_degrees:
        min_lat = math.floor(min_lat_padded)
        max_lat = math.ceil(max_lat_padded)
        min_lon = math.floor(min_lon_padded)
        max_lon = math.ceil(max_lon_padded)
    else:
        min_lat = min_lat_padded
        max_lat = max_lat_padded
        min_lon = min_lon_padded
        max_lon = max_lon_padded

    # Apply aspect ratio correction (optional)
    if apply_aspect_ratio:
        final_min_lon, final_max_lon, final_min_lat, final_max_lat = (
            compute_final_limits(min_lon, max_lon, min_lat, max_lat)
        )
    else:
        final_min_lon, final_max_lon, final_min_lat, final_max_lat = (
            min_lon,
            max_lon,
            min_lat,
            max_lat,
        )

    return final_min_lon, final_max_lon, final_min_lat, final_max_lat


def compute_final_limits(
    lon_min: float, lon_max: float, lat_min: float, lat_max: float
) -> Tuple[float, float, float, float]:
    """
    Compute final map limits accounting for geographic aspect ratio.

    Parameters
    ----------
    lon_min, lon_max : float
        Initial longitude bounds
    lat_min, lat_max : float
        Initial latitude bounds

    Returns
    -------
    tuple
        (final_lon_min, final_lon_max, final_lat_min, final_lat_max)
    """
    mid_lat_deg = (lat_min + lat_max) / 2
    mid_lat_deg = max(-85.0, min(85.0, mid_lat_deg))
    mid_lat_rad = math.radians(mid_lat_deg)

    try:
        aspect = 1.0 / math.cos(mid_lat_rad)
    except ZeroDivisionError:
        aspect = 1.0
    aspect = max(1.0, min(aspect, 10.0))

    # Current ranges
    lat_range = lat_max - lat_min
    lon_range = lon_max - lon_min

    # Required ranges for proper aspect ratio
    required_lon_range = lat_range * aspect
    required_lat_range = lon_range / aspect

    # Expand whichever dimension needs it
    if required_lon_range > lon_range:
        # Need to expand longitude
        lon_center = (lon_min + lon_max) / 2
        final_lon_min = lon_center - required_lon_range / 2
        final_lon_max = lon_center + required_lon_range / 2
        final_lat_min = lat_min
        final_lat_max = lat_max
    else:
        # Need to expand latitude
        lat_center = (lat_min + lat_max) / 2
        final_lat_min = lat_center - required_lat_range / 2
        final_lat_max = lat_center + required_lat_range / 2
        final_lon_min = lon_min
        final_lon_max = lon_max

    return final_lon_min, final_lon_max, final_lat_min, final_lat_max
