"""
Coordinate formatting utilities for scientific and maritime applications.

This module provides functions to format coordinates in various standard formats
used in oceanographic and maritime contexts, including decimal degrees, degrees
and decimal minutes (DDM), and LaTeX-formatted output. Also includes utilities
for extracting coordinates from cruise configurations and calculating map bounds.

Notes
-----
All coordinate functions expect input in decimal degrees and handle both
northern/eastern (positive) and southern/western (negative) coordinates.
The CoordConverter class provides static methods for coordinate conversions.
"""

import math
from typing import Any, Optional


class CoordConverter:
    """
    Utility class for coordinate unit conversions.

    This class provides static methods for converting between different
    coordinate representations commonly used in maritime and scientific contexts.
    """

    @staticmethod
    def decimal_degrees_to_ddm(decimal_degrees: float) -> tuple[float, float]:
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
        >>> CoordConverter.decimal_degrees_to_ddm(65.7458)
        (65.0, 44.75)
        """
        degrees = int(abs(decimal_degrees))
        minutes = (abs(decimal_degrees) - degrees) * 60
        return float(degrees), minutes


def format_ddm_comment(lat: float, lon: float) -> str:
    """
    Format coordinates as degrees/decimal minutes comment for validator compliance.

    This function generates ddm format that passes the strict validator requirements:
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
        ddm comment like "65 44.75'N, 024 28.75'W".

    Examples
    --------
    >>> format_ddm_comment(65.7458, -24.4792)
    "65 44.75'N, 024 28.75'W"
    """
    # Convert to degrees and decimal minutes
    lat_deg, lat_min = CoordConverter.decimal_degrees_to_ddm(lat)
    lon_deg, lon_min = CoordConverter.decimal_degrees_to_ddm(lon)

    # Determine directions
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"

    # Format with required precision: DD MM.MM'N, DDD MM.MM'W
    lat_str = f"{abs(int(lat_deg)):02d} {lat_min:05.2f}'{lat_dir}"
    lon_str = f"{abs(int(lon_deg)):03d} {lon_min:05.2f}'{lon_dir}"

    return f"{lat_str}, {lon_str}"


def format_position_latex(lat: float, lon: float) -> str:
    r"""
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
    lat_deg, lat_min = CoordConverter.decimal_degrees_to_ddm(lat)
    lon_deg, lon_min = CoordConverter.decimal_degrees_to_ddm(lon)

    # Determine directions
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"

    # Format with LaTeX degree symbols
    lat_str = f"{abs(int(lat_deg)):02d}$^\\circ${lat_min:05.2f}'{lat_dir}"
    lon_str = f"{abs(int(lon_deg)):03d}$^\\circ${lon_min:05.2f}'{lon_dir}"

    return f"{lat_str}, {lon_str}"


def _extract_port_info(port: Any) -> Optional[tuple[float, float, str]]:
    """
    Extract port information from a port object.

    Parameters
    ----------
    port : Any
        Port object (PortDefinition or string reference)

    Returns
    -------
    Optional[Tuple[float, float, str]]
        (latitude, longitude, name) tuple or None if port is invalid
    """
    if port is None:
        return None

    # Check if it's a resolved PortDefinition object
    if hasattr(port, "latitude") and hasattr(port, "longitude"):
        return (port.latitude, port.longitude, port.name)

    # String reference or invalid - return None
    return None


def extract_coordinates_from_cruise(
    cruise: Any,
) -> tuple[list[float], list[float], list[str], Optional[tuple], Optional[tuple]]:
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
    for station_name, station in cruise.point_registry.items():
        lat = station.latitude
        lon = station.longitude
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
        else:
            # String reference - skip for now
            arr_lat = None
            arr_lon = None
            arr_name = None

        if arr_lat is not None and arr_lon is not None:
            arrival_port = (arr_lat, arr_lon, arr_name)

    return all_lats, all_lons, station_names, departure_port, arrival_port


def calculate_map_bounds(
    all_lats: list[float],
    all_lons: list[float],
    padding_percent: float = 0.05,
    padding_degrees: Optional[float] = None,
    apply_aspect_ratio: bool = True,
    round_to_degrees: bool = True,
) -> tuple[float, float, float, float]:
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
        min_lat: float = math.floor(min_lat_padded)
        max_lat: float = math.ceil(max_lat_padded)
        min_lon: float = math.floor(min_lon_padded)
        max_lon: float = math.ceil(max_lon_padded)
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
) -> tuple[float, float, float, float]:
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


def _validate_coordinate_bounds(
    lat_bounds: list[float], lon_bounds: list[float]
) -> tuple[float, float, float, float]:
    """
    Validate and normalize coordinate bounds with sophisticated longitude format checking.

    # NOTE: This sophisticated validation is now used by validation/base_models.py
    # and core/validation_old.py for consistent coordinate validation across the codebase.
    # It handles format consistency and meridian crossing properly.

    This function enforces that longitude coordinates use consistent formats and handles
    meridian crossing correctly. It supports both -180/180 and 0/360 longitude formats
    but prevents mixing of formats which can cause confusion.

    Parameters
    ----------
    lat_bounds : list[float]
        Latitude bounds [min_lat, max_lat]
    lon_bounds : list[float]
        Longitude bounds [min_lon, max_lon]

    Returns
    -------
    tuple[float, float, float, float]
        Normalized bounds (min_lon, min_lat, max_lon, max_lat) in bbox format

    Raises
    ------
    ValueError
        If coordinate bounds are invalid or use inconsistent longitude formats

    Examples
    --------
    >>> _validate_coordinate_bounds([50.0, 60.0], [-10.0, 10.0])
    (-10.0, 50.0, 10.0, 60.0)
    >>> _validate_coordinate_bounds([50.0, 60.0], [350.0, 360.0])
    (350.0, 50.0, 360.0, 60.0)
    """
    # Validate input format
    if not isinstance(lat_bounds, list) or len(lat_bounds) != 2:
        raise ValueError(
            "lat_bounds must be a list of exactly 2 values [min_lat, max_lat]"
        )

    if not isinstance(lon_bounds, list) or len(lon_bounds) != 2:
        raise ValueError(
            "lon_bounds must be a list of exactly 2 values [min_lon, max_lon]"
        )

    # Validate coordinate ranges
    min_lat, max_lat = lat_bounds
    min_lon, max_lon = lon_bounds

    # Validate latitude (always -90 to 90)
    if not (-90 <= min_lat <= 90):
        raise ValueError(
            f"Invalid minimum latitude: {min_lat}. Must be between -90 and 90."
        )

    if not (-90 <= max_lat <= 90):
        raise ValueError(
            f"Invalid maximum latitude: {max_lat}. Must be between -90 and 90."
        )

    if min_lat >= max_lat:
        raise ValueError(
            f"Minimum latitude ({min_lat}) must be less than maximum latitude ({max_lat})"
        )

    # Validate longitude ranges first - check for completely out-of-range values
    if not (-180 <= min_lon <= 360):
        raise ValueError(
            f"Invalid minimum longitude: {min_lon}. Must be between -180 and 360."
        )

    if not (-180 <= max_lon <= 360):
        raise ValueError(
            f"Invalid maximum longitude: {max_lon}. Must be between -180 and 360."
        )

    # Validate longitude format and ranges
    # Support both -180/180 and 0/360 formats, but not mixed
    if -180 <= min_lon <= 180 and -180 <= max_lon <= 180:
        # -180/180 format - allows meridian crossing
        if min_lon >= max_lon:
            raise ValueError(
                f"Minimum longitude ({min_lon}) must be less than maximum longitude ({max_lon})"
            )
    elif 0 <= min_lon <= 360 and 0 <= max_lon <= 360:
        # 0/360 format - NO meridian crossing allowed
        if min_lon >= max_lon:
            raise ValueError(
                f"Minimum longitude ({min_lon}) must be less than maximum longitude ({max_lon}). "
                f"For meridian crossing, use -180/180 format instead."
            )
    else:
        # Mixed format (e.g., -90 and 240)
        raise ValueError(
            "Longitude coordinates must use the same format:\n"
            "  - Both in -180 to 180 format (e.g., --lon -90 -30)\n"
            "  - Both in 0 to 360 format (e.g., --lon 270 330)\n"
            "  - Cannot mix formats (e.g., --lon -90 240 is invalid)\n"
            "  - Use -180/180 format for meridian crossing ranges"
        )

    # Return in bbox format (min_lon, min_lat, max_lon, max_lat)
    return (min_lon, min_lat, max_lon, max_lat)


def _validate_latitude(value: float) -> float:
    """
    Validate a single latitude coordinate.

    Parameters
    ----------
    value : float
        Latitude value in decimal degrees

    Returns
    -------
    float
        Validated latitude value

    Raises
    ------
    ValueError
        If latitude is outside the valid range of -90 to 90 degrees

    Examples
    --------
    >>> _validate_latitude(45.0)
    45.0
    >>> _validate_latitude(-91.0)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: Latitude -91.0 must be between -90 and 90
    """
    if not (-90 <= value <= 90):
        raise ValueError(f"Latitude {value} must be between -90 and 90")
    return value


def _validate_longitude(value: float) -> float:
    """
    Validate a single longitude coordinate.

    Accepts both -180/180 and 0/360 longitude formats for individual coordinates.
    For coordinate bounds validation with format consistency checking, use
    _validate_coordinate_bounds() instead.

    Parameters
    ----------
    value : float
        Longitude value in decimal degrees

    Returns
    -------
    float
        Validated longitude value

    Raises
    ------
    ValueError
        If longitude is outside the valid range of -180 to 360 degrees

    Examples
    --------
    >>> _validate_longitude(45.0)
    45.0
    >>> _validate_longitude(-180.0)
    -180.0
    >>> _validate_longitude(360.0)
    360.0
    >>> _validate_longitude(400.0)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: Longitude 400.0 must be between -180 and 360
    """
    # Individual point check: Must be valid in at least one system (-180..360 covers both)
    if not (-180 <= value <= 360):
        raise ValueError(f"Longitude {value} must be between -180 and 360")
    return value
