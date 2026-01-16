"""Tests for cruiseplan.utils.constants module."""

import pytest

from cruiseplan.utils.units import (
    KM_PER_NM,
    MINUTES_PER_HOUR,
    NM_PER_KM,
    hours_to_minutes,
    minutes_to_hours,
    seconds_to_minutes,
)


class TestConstants:
    """Test constants and conversion functions."""

    def test_constants_values(self):
        """Test that constants have expected values."""
        assert pytest.approx(0.539957, abs=0.001) == NM_PER_KM
        assert pytest.approx(1.852, abs=0.001) == KM_PER_NM
        assert MINUTES_PER_HOUR == 60.0

    def test_minutes_to_hours(self):
        """Test minutes to hours conversion."""
        assert minutes_to_hours(60.0) == 1.0
        assert minutes_to_hours(120.0) == 2.0
        assert minutes_to_hours(30.0) == 0.5
        assert minutes_to_hours(0.0) == 0.0

    def test_hours_to_minutes(self):
        """Test hours to minutes conversion."""
        assert hours_to_minutes(1.0) == 60.0
        assert hours_to_minutes(2.0) == 120.0
        assert hours_to_minutes(0.5) == 30.0
        assert hours_to_minutes(0.0) == 0.0

    def test_seconds_to_minutes(self):
        """Test seconds to minutes conversion."""
        assert seconds_to_minutes(60.0) == 1.0
        assert seconds_to_minutes(120.0) == 2.0
        assert seconds_to_minutes(30.0) == 0.5
        assert seconds_to_minutes(0.0) == 0.0

    def test_conversion_consistency(self):
        """Test that conversions are consistent with each other."""
        # hours -> minutes -> hours should be identity
        hours = 2.5
        assert minutes_to_hours(hours_to_minutes(hours)) == pytest.approx(hours)

        # Test relationship between NM_PER_KM and KM_PER_NM
        assert pytest.approx(1.0, abs=0.001) == NM_PER_KM * KM_PER_NM

    def test_edge_cases(self):
        """Test edge cases for conversion functions."""
        # Very large numbers
        large_val = 1e6
        assert hours_to_minutes(large_val) == large_val * MINUTES_PER_HOUR
        assert minutes_to_hours(large_val) == large_val / MINUTES_PER_HOUR

        # Very small numbers
        small_val = 1e-6
        assert hours_to_minutes(small_val) == small_val * MINUTES_PER_HOUR
        assert seconds_to_minutes(small_val) == small_val / 60.0
