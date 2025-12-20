"""
Constants and default values for cruise planning.

This module defines default parameters, conversion factors, and sentinel values
used throughout the cruiseplan system. These constants provide fallback values
for configuration parameters and standard conversion utilities.

Notes
-----
All constants are defined at the module level for easy importing and use.
Unit conversion functions are provided for common time conversions.
"""

# cruiseplan/utils/constants.py
from datetime import datetime, timezone

# --- Time Conversion Factors ---
SECONDS_PER_MINUTE = 60.0
MINUTES_PER_HOUR = 60.0
HOURS_PER_DAY = 24.0

# --- Geographic and Distance Constants ---

# Earth radius in kilometers (WGS84 approximate)
R_EARTH_KM = 6371.0

# Distance conversion factors
NM_PER_KM = 0.539957  # Nautical miles per kilometer
KM_PER_NM = 1.852  # Kilometers per nautical mile

# --- Depth/Bathymetry Constants ---

# Sentinel value indicating that depth data is missing, the station is outside
# the bathymetry grid boundaries, or a calculation failed.
# This value is defined in the specs as the fallback depth if ETOPO data is not found.
FALLBACK_DEPTH = -9999.0

# --- Default Cruise Parameters ---
# These are used as code-level fallbacks if a configuration parameter is
# required before the CruiseConfig object is fully initialized or if a
# required field is missing (though the YAML schema should prevent the latter).

# Default vessel transit speed in knots (kt)
DEFAULT_VESSEL_SPEED_KT = 10.0

# Default profile turnaround time in minutes (minutes)
# Corresponds to CruiseConfig.turnaround_time default.
DEFAULT_TURNAROUND_TIME_MIN = 30.0

# Default CTD descent/ascent rate in meters per second (m/s)
# Corresponds to CruiseConfig.ctd_descent_rate/ascent_rate default.
DEFAULT_CTD_RATE_M_S = 1.0

# Default distance between stations in kilometers (km)
# Corresponds to CruiseConfig.default_distance_between_stations default.
DEFAULT_STATION_SPACING_KM = 15.0

# Default calculation flags - typically True for automated processing
# Whether to calculate transit times between section waypoints
DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS = True

# Whether to automatically look up depth values from bathymetry data
DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY = True

# Default mooring operation duration in minutes (999 hours = 59940 minutes)
# Used as a highly visible placeholder for mooring operations without specified duration
DEFAULT_MOORING_DURATION_MIN = 59940.0

DEFAULT_START_DATE_NUM = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
# Make this an ISO8601 string
DEFAULT_START_DATE = DEFAULT_START_DATE_NUM.isoformat()

# --- Unit Conversion Functions ---


def minutes_to_hours(minutes: float) -> float:
    """
    Convert minutes to hours.

    Parameters
    ----------
    minutes : float
        Time duration in minutes.

    Returns
    -------
    float
        Time duration in hours.
    """
    return minutes / MINUTES_PER_HOUR


def hours_to_minutes(hours: float) -> float:
    """
    Convert hours to minutes.

    Parameters
    ----------
    hours : float
        Time duration in hours.

    Returns
    -------
    float
        Time duration in minutes.
    """
    return hours * MINUTES_PER_HOUR


def seconds_to_minutes(seconds: float) -> float:
    """
    Convert seconds to minutes.

    Parameters
    ----------
    seconds : float
        Time duration in seconds.

    Returns
    -------
    float
        Time duration in minutes.
    """
    return seconds / SECONDS_PER_MINUTE


def rate_per_second_to_rate_per_minute(rate_per_sec: float) -> float:
    """
    Convert rate per second to rate per minute.

    For example: meters per second → meters per minute

    Parameters
    ----------
    rate_per_sec : float
        Rate value per second (e.g., m/s).

    Returns
    -------
    float
        Rate value per minute (e.g., m/min).
    """
    return rate_per_sec * SECONDS_PER_MINUTE


def hours_to_days(hours: float) -> float:
    """
    Convert hours to days.

    Parameters
    ----------
    hours : float
        Time duration in hours.

    Returns
    -------
    float
        Time duration in days.
    """
    return hours / HOURS_PER_DAY


def minutes_to_days(minutes: float) -> float:
    """
    Convert minutes to days.

    Parameters
    ----------
    minutes : float
        Time duration in minutes.

    Returns
    -------
    float
        Time duration in days.
    """
    return minutes / (MINUTES_PER_HOUR * HOURS_PER_DAY)
