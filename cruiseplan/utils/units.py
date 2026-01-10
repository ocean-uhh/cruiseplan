"""
Unit conversion constants and functions.

This module provides immutable physical constants and unit conversion functions
for time, distance, and other measurements. These are mathematical constants
that do not change based on cruise configuration.
"""

# --- Time Conversion Factors ---
SECONDS_PER_MINUTE = 60.0
MINUTES_PER_HOUR = 60.0
HOURS_PER_DAY = 24.0

# --- Distance Conversion Constants ---
NM_PER_KM = 0.539957  # Nautical miles per kilometer
KM_PER_NM = 1.852  # Kilometers per nautical mile


# --- Time Conversion Functions ---


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


# --- Distance Conversion Functions ---


def km_to_nm(km: float) -> float:
    """
    Convert kilometers to nautical miles.

    Parameters
    ----------
    km : float
        Distance in kilometers.

    Returns
    -------
    float
        Distance in nautical miles.
    """
    return km * NM_PER_KM


def nm_to_km(nm: float) -> float:
    """
    Convert nautical miles to kilometers.

    Parameters
    ----------
    nm : float
        Distance in nautical miles.

    Returns
    -------
    float
        Distance in kilometers.
    """
    return nm * KM_PER_NM
