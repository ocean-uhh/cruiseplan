"""
Simple tests to boost duration calculator coverage.

This module provides targeted tests for uncovered edge cases and error paths
in the duration calculator that are not hit by the main test suite.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cruiseplan.calculators.duration import DurationCalculator


class TestDurationCoverageBoost:
    """Simple tests to boost duration calculator coverage."""

    def setup_method(self):
        """Setup test fixtures."""
        # Mock configuration with default values
        self.mock_config = MagicMock()
        self.mock_config.ctd_descent_rate = 1.0  # m/s
        self.mock_config.ctd_ascent_rate = 2.0  # m/s
        self.mock_config.turnaround_time = 5.0  # minutes
        self.mock_config.default_vessel_speed = 10.0  # knots

        self.calculator = DurationCalculator(self.mock_config)

    def test_calculate_ctd_time_zero_depth(self):
        """Test CTD time with zero or negative depth (line 59)."""
        # Test zero depth
        assert self.calculator.calculate_ctd_time(0.0) == 0.0

        # Test negative depth
        assert self.calculator.calculate_ctd_time(-100.0) == 0.0

    def test_calculate_ctd_time_zero_rates(self):
        """Test CTD time with zero descent/ascent rates (line 67)."""
        # Test zero descent rate
        self.mock_config.ctd_descent_rate = 0.0
        result = self.calculator.calculate_ctd_time(1000.0)
        assert result == 0.0

        # Test zero ascent rate
        self.mock_config.ctd_descent_rate = 1.0
        self.mock_config.ctd_ascent_rate = 0.0
        result = self.calculator.calculate_ctd_time(1000.0)
        assert result == 0.0

        # Test negative rates
        self.mock_config.ctd_descent_rate = -1.0
        self.mock_config.ctd_ascent_rate = 2.0
        result = self.calculator.calculate_ctd_time(1000.0)
        assert result == 0.0

    def test_calculate_transit_time_zero_speed(self):
        """Test transit time with zero speed (lines 90-98)."""
        # Test zero speed parameter
        result = self.calculator.calculate_transit_time(100.0, speed_knots=0.0)
        assert result == 0.0

        # Test zero default speed
        self.mock_config.default_vessel_speed = 0.0
        result = self.calculator.calculate_transit_time(100.0)
        assert result == 0.0

        # Test negative speed
        result = self.calculator.calculate_transit_time(100.0, speed_knots=-5.0)
        assert result == 0.0

    def test_calculate_transit_time_uses_default_speed(self):
        """Test transit time uses default speed when none provided (lines 90-92)."""
        # Ensure default speed is used when speed_knots is None
        self.mock_config.default_vessel_speed = 12.0

        # Mock km_to_nm conversion (assume 1 km = 0.539957 nm roughly)
        with pytest.MonkeyPatch.context() as m:
            m.setattr(
                "cruiseplan.calculators.duration.km_to_nm", lambda x: x * 0.539957
            )

            result = self.calculator.calculate_transit_time(100.0, speed_knots=None)

            # Should use default speed of 12.0 knots
            expected_nm = 100.0 * 0.539957
            expected_hours = expected_nm / 12.0
            expected_minutes = expected_hours * 60

            assert abs(result - expected_minutes) < 0.1

    def test_calculate_wait_time_no_window(self):
        """Test wait time with no required window (line 124)."""
        arrival_time = datetime(2025, 6, 1, 10, 0, 0)

        # Test None window
        result = self.calculator.calculate_wait_time(
            arrival_time, required_window=None, duration_minutes=120.0
        )
        assert result == 0.0

        # Test empty string window
        result = self.calculator.calculate_wait_time(
            arrival_time, required_window="", duration_minutes=120.0
        )
        assert result == 0.0

        # Test False window
        result = self.calculator.calculate_wait_time(
            arrival_time, required_window=False, duration_minutes=120.0
        )
        assert result == 0.0

    def test_calculate_wait_time_day_window_too_late(self):
        """Test daylight wait for day window when arriving too late (lines 145-146)."""
        # Arrive after day hours (assuming day_end_hour is 18)
        self.calculator.day_end_hour = 18
        self.calculator.day_start_hour = 6

        # Arrive at 20:00 (8 PM) - too late for day operations
        arrival_time = datetime(2025, 6, 1, 20, 0, 0)

        result = self.calculator.calculate_wait_time(
            arrival_time, required_window="day", duration_minutes=120.0
        )

        # Should wait until next day at 6 AM
        next_start = arrival_time.replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        expected_wait = (next_start - arrival_time).total_seconds() / 60.0

        assert abs(result - expected_wait) < 0.1

    def test_calculate_wait_time_night_window(self):
        """Test daylight wait for night window operations (lines 157-165)."""
        self.calculator.day_end_hour = 18
        self.calculator.day_start_hour = 6

        # Test night arrival (should start immediately)
        night_arrival = datetime(2025, 6, 1, 22, 0, 0)
        result = self.calculator.calculate_wait_time(
            night_arrival, required_window="night", duration_minutes=120.0
        )
        assert result == 0.0

        # Test day arrival (should wait for night)
        day_arrival = datetime(2025, 6, 1, 14, 0, 0)  # 2 PM
        result = self.calculator.calculate_wait_time(
            day_arrival, required_window="night", duration_minutes=120.0
        )

        # Should wait until 6 PM (day_end_hour)
        day_end = day_arrival.replace(hour=18, minute=0, second=0, microsecond=0)
        expected_wait = (day_end - day_arrival).total_seconds() / 60.0

        assert abs(result - expected_wait) < 0.1

    def test_calculate_wait_time_day_operation_finish_past_day_end(self):
        """Test day operation that would finish past day end time."""
        self.calculator.day_end_hour = 18
        self.calculator.day_start_hour = 6

        # Arrive at 4 PM with 5-hour operation (would finish at 9 PM, past day end)
        arrival_time = datetime(2025, 6, 1, 16, 0, 0)
        duration_minutes = 5 * 60  # 5 hours

        result = self.calculator.calculate_wait_time(
            arrival_time, required_window="day", duration_minutes=duration_minutes
        )

        # Should wait until next day
        next_start = arrival_time.replace(
            hour=6, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        expected_wait = (next_start - arrival_time).total_seconds() / 60.0

        assert abs(result - expected_wait) < 0.1


class TestDurationCalculatorEdgeCases:
    """Test edge cases for duration calculator."""

    def test_calculate_with_extreme_values(self):
        """Test calculator with extreme configuration values."""
        # Test with very high rates
        config = MagicMock()
        config.ctd_descent_rate = 1000.0  # Very fast descent
        config.ctd_ascent_rate = 1000.0  # Very fast ascent
        config.turnaround_time = 0.0  # No turnaround
        config.default_vessel_speed = 100.0  # Very fast vessel

        calculator = DurationCalculator(config)

        # Should handle extreme values gracefully
        profile_time = calculator.calculate_ctd_time(5000.0)
        assert profile_time >= 0.0

        transit_time = calculator.calculate_transit_time(1000.0)
        assert transit_time >= 0.0

    def test_daylight_calculator_boundary_hours(self):
        """Test daylight calculations at exact boundary hours."""
        config = MagicMock()
        calculator = DurationCalculator(config)
        calculator.day_start_hour = 6
        calculator.day_end_hour = 18

        # Test arrival exactly at day start
        exact_start = datetime(2025, 6, 1, 6, 0, 0)
        result = calculator.calculate_wait_time(
            exact_start, required_window="day", duration_minutes=60.0
        )
        assert result == 0.0  # Should start immediately

        # Test arrival exactly at day end
        exact_end = datetime(2025, 6, 1, 18, 0, 0)
        result = calculator.calculate_wait_time(
            exact_end, required_window="day", duration_minutes=60.0
        )
        # Should wait until next day since we're at the boundary
        assert result > 0.0
