from datetime import datetime, timedelta
from typing import Literal

from cruiseplan.calculators.distance import km_to_nm
from cruiseplan.core.validation import CruiseConfig


class DurationCalculator:
    def __init__(self, config: CruiseConfig):
        self.config = config
        # Pull from config (defaulting to 8/20 via Pydantic if not set)
        self.day_start_hour = config.day_start_hour
        self.day_end_hour = config.day_end_hour

    def calculate_ctd_time(self, depth: float) -> float:
        """
        Returns duration in MINUTES.
        Formula: (Depth / Descent) + (Depth / Ascent) + Turnaround
        """
        if depth <= 0:
            return 0.0

        # Convert rates (m/s) to m/min
        descent_m_min = self.config.ctd_descent_rate * 60
        ascent_m_min = self.config.ctd_ascent_rate * 60

        # Avoid division by zero
        if descent_m_min <= 0 or ascent_m_min <= 0:
            return 0.0

        profile_time = (depth / descent_m_min) + (depth / ascent_m_min)
        return profile_time + self.config.turnaround_time

    def calculate_transit_time(
        self, distance_km: float, speed_knots: float = None
    ) -> float:
        """
        Returns duration in MINUTES based on distance and vessel speed.
        """
        speed = (
            speed_knots if speed_knots is not None else self.config.default_vessel_speed
        )
        if speed <= 0:
            return 0.0

        distance_nm = km_to_nm(distance_km)
        hours = distance_nm / speed
        return hours * 60

    def calculate_wait_time(
        self,
        arrival_dt: datetime,
        duration_minutes: float,
        required_window: Literal["day", "night"] = None,
    ) -> float:
        """
        Calculates MINUTES to wait if the operation cannot start/finish
        within the required window.
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
