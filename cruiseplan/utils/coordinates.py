"""
Coordinate formatting utilities for scientific and maritime applications.

This module provides functions to format coordinates in various standard formats
used in oceanographic and maritime contexts, including decimal degrees, degrees
and decimal minutes (DMM), and LaTeX-formatted output.

Notes
-----
All coordinate functions expect input in decimal degrees and handle both
northern/eastern (positive) and southern/western (negative) coordinates.
The UnitConverter class provides static methods for coordinate conversions.
"""

import re
from typing import Tuple


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
    "65$^\\circ$44.75'$N$, 024$^\\circ$28.75'$W$"
    """
    # Convert to degrees and decimal minutes
    lat_deg, lat_min = UnitConverter.decimal_degrees_to_dmm(lat)
    lon_deg, lon_min = UnitConverter.decimal_degrees_to_dmm(lon)

    # Determine directions
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"

    # Format with LaTeX degree symbols
    lat_str = f"{abs(int(lat_deg)):02d}$^\\circ${lat_min:05.2f}'${lat_dir}$"
    lon_str = f"{abs(int(lon_deg)):03d}$^\\circ${lon_min:05.2f}'${lon_dir}$"

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
