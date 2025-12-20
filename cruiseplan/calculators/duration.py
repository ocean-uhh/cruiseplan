"""
Duration calculations for cruise operations and activities.

This module provides time duration calculations for various cruise operations
including CTD profiling, vessel transit, and operational constraints based on
day/night windows. Uses configuration parameters for vessel speeds and CTD rates.
"""

from datetime import datetime, timedelta
from typing import Literal

from cruiseplan.calculators.distance import km_to_nm
from cruiseplan.core.validation import CruiseConfig
from cruiseplan.utils.constants import (
    hours_to_minutes,
    rate_per_second_to_rate_per_minute,
)


class DurationCalculator:
    """
    Calculates time durations for cruise operations and activities.

    This class provides methods to calculate operation durations based on
    cruise configuration parameters including vessel speeds, CTD rates,
    and operational time windows.

    Attributes
    ----------
    config : CruiseConfig
        Cruise configuration object containing operational parameters.
    day_start_hour : int
        Hour when daytime operations begin (0-23).
    day_end_hour : int
        Hour when daytime operations end (0-23).
    """

    def __init__(self, config: CruiseConfig):
        self.config = config
        # Pull from config (defaulting to 8/20 via Pydantic if not set)
        self.day_start_hour = config.day_start_hour
        self.day_end_hour = config.day_end_hour

    def calculate_ctd_time(self, depth: float) -> float:
        """
        Calculate CTD profiling duration including descent, ascent, and turnaround.

        Parameters
        ----------
        depth : float
            Water depth in meters.

        Returns
        -------
        float
            Total duration in minutes.

        Notes
        -----
        Formula: (Depth / Descent) + (Depth / Ascent) + Turnaround
        """
        if depth <= 0:
            return 0.0

        descent_m_sec = self.config.ctd_descent_rate
        ascent_m_sec = self.config.ctd_ascent_rate
        # Convert rates (m/s) to m/min
        descent_m_min = rate_per_second_to_rate_per_minute(descent_m_sec)
        ascent_m_min = rate_per_second_to_rate_per_minute(ascent_m_sec)

        # Avoid division by zero
        if descent_m_min <= 0 or ascent_m_min <= 0:
            return 0.0

        profile_time = (depth / descent_m_min) + (depth / ascent_m_min)
        return profile_time + self.config.turnaround_time

    def calculate_transit_time(
        self, distance_km: float, speed_knots: float = None
    ) -> float:
        """
        Calculate vessel transit duration based on distance and speed.

        Parameters
        ----------
        distance_km : float
            Distance to travel in kilometers.
        speed_knots : float, optional
            Vessel speed in knots. If None, uses config default.

        Returns
        -------
        float
            Transit duration in minutes.
        """
        speed = (
            speed_knots if speed_knots is not None else self.config.default_vessel_speed
        )
        if speed <= 0:
            return 0.0

        distance_nm = km_to_nm(distance_km)
        duration_hours = distance_nm / speed
        return hours_to_minutes(duration_hours)

    def calculate_wait_time(
        self,
        arrival_dt: datetime,
        duration_minutes: float,
        required_window: Literal["day", "night"] = None,
    ) -> float:
        """
        Calculate wait time to align operations with day/night windows.

        Parameters
        ----------
        arrival_dt : datetime
            Arrival time at the operation location.
        duration_minutes : float
            Duration of the operation in minutes.
        required_window : {"day", "night"}, optional
            Required time window for the operation.

        Returns
        -------
        float
            Wait time in minutes before operation can begin.
        """
        if not required_window:
            return 0.0

        current_dt = arrival_dt

        # Define window boundaries relative to current_dt
        day_start = current_dt.replace(
            hour=self.day_start_hour, minute=0, second=0, microsecond=0
        )
        day_end = current_dt.replace(
            hour=self.day_end_hour, minute=0, second=0, microsecond=0
        )

        is_daytime_arrival = self.day_start_hour <= current_dt.hour < self.day_end_hour

        if required_window == "day":
            # A: Too Early (Night before)
            if current_dt.hour < self.day_start_hour:
                return (day_start - current_dt).total_seconds() / 60.0

            # B: Too Late (Night after)
            if current_dt.hour >= self.day_end_hour:
                next_start = day_start + timedelta(days=1)
                return (next_start - current_dt).total_seconds() / 60.0

            # C: Day Arrival -> Check if finish fits
            if is_daytime_arrival:
                finish_time = current_dt + timedelta(minutes=duration_minutes)
                if finish_time <= day_end:
                    return 0.0
                else:
                    next_start = day_start + timedelta(days=1)
                    return (next_start - current_dt).total_seconds() / 60.0

        elif required_window == "night":
            # Simplified: If at night, start. If at day, wait for night.
            if not is_daytime_arrival:
                return 0.0

            # Wait for sunset
            return (day_end - current_dt).total_seconds() / 60.0

        return 0.0
