from datetime import datetime

import pytest

from cruiseplan.calculators.distance import haversine_distance
from cruiseplan.calculators.duration import DurationCalculator
from cruiseplan.core.validation import CruiseConfig, PortDefinition


# Mock Config
@pytest.fixture
def mock_config():
    from cruiseplan.core.validation import LegDefinition

    return CruiseConfig(
        cruise_name="Test",
        start_date="2025-01-01T08:00:00",
        default_vessel_speed=10,
        default_distance_between_stations=20,
        calculate_transfer_between_sections=True,
        calculate_depth_via_bathymetry=False,
        legs=[
            LegDefinition(
                name="Test_Leg",
                departure_port=PortDefinition(name="A", latitude=0.0, longitude=0.0),
                arrival_port=PortDefinition(name="B", latitude=0.0, longitude=0.0),
                first_station="S1",
                last_station="S1",
                activities=[],
            )
        ],
        ctd_descent_rate=1.0,  # 60 m/min
        ctd_ascent_rate=1.0,  # 60 m/min
        turnaround_time=10,  # min
        # Day Window
        day_start_hour=8,
        day_end_hour=20,
    )


@pytest.fixture
def slow_winch_config(mock_config):
    """Custom Config: Slower rates (0.5 m/s) and longer turnaround"""
    # Create a copy with modified values
    config = mock_config.model_copy()
    config.ctd_descent_rate = 2  # 120 m/min
    config.ctd_ascent_rate = 0.5  # 30 m/min
    config.turnaround_time = 12.5
    return config


# --- DURATION TESTS ---


def test_ctd_duration_standard(mock_config):
    """Test with default 1.0 m/s rates."""
    calc = DurationCalculator(mock_config)
    # Depth 600m
    # Descent: 600 / 60 = 10 min
    # Ascent:  600 / 60 = 10 min
    # Turnaround: 10 min
    # Total: 30 min
    assert calc.calculate_ctd_time(600.0) == 30.0


def test_ctd_duration_custom_rates(slow_winch_config):
    """
    Test with 0.5 m/s rates (slower).
    Formula: (Depth/Rate_Down) + (Depth/Rate_Up) + Turnaround
    """
    calc = DurationCalculator(slow_winch_config)

    # Depth 600m
    # Rate: 0.5 m/s = 30 m/min
    # Descent: 600 / 120 = 5 min
    # Ascent:  600 / 30 = 20 min
    # Turnaround: 12.5 min
    # Total: 37.5 min
    assert calc.calculate_ctd_time(600.0) == 37.5


def test_custom_day_window_wait():
    """Verify wait time respects custom daylight hours (e.g., High Latitude Summer)."""
    # Create config with LONG days (04:00 to 22:00)
    from cruiseplan.core.validation import LegDefinition

    cfg = CruiseConfig(
        cruise_name="Summer Sun",
        start_date="2025-06-01T00:00:00",
        default_vessel_speed=10,
        default_distance_between_stations=10,
        calculate_transfer_between_sections=True,
        calculate_depth_via_bathymetry=False,
        legs=[
            LegDefinition(
                name="Summer_Leg",
                departure_port=PortDefinition(name="A", latitude=0, longitude=0),
                arrival_port=PortDefinition(name="B", latitude=0, longitude=0),
                first_station="S1",
                last_station="S1",
                activities=[],
            )
        ],
        day_start_hour=4,  # Sunrise 04:00
        day_end_hour=22,  # Sunset 22:00
    )

    calc = DurationCalculator(cfg)

    # Case: Arrive at 05:00. This IS valid day in this config (would be night in default).
    # Should be 0 wait.
    arrival = datetime(2025, 6, 1, 5, 0, 0)
    wait = calc.calculate_wait_time(arrival, 60, "day")
    assert wait == 0.0


def test_distance_accuracy():
    # 1 degree of latitude is approx 111.1 km
    p1 = (0, 0)
    p2 = (1, 0)
    dist = haversine_distance(p1, p2)
    assert 110 < dist < 112


def test_ctd_duration(mock_config):
    calc = DurationCalculator(mock_config)
    # Depth 600m.
    # Descent: 600m / 60m/min = 10 min
    # Ascent:  600m / 60m/min = 10 min
    # Turnaround: 10 min
    # Total: 30 min
    assert calc.calculate_ctd_time(600) == 30.0


def test_wait_time_day_ops(mock_config):
    calc = DurationCalculator(mock_config)

    # CASE 1: Arrive at 12:00 (Noon). Duration 2 hours. Fits in day.
    arrival = datetime(2025, 1, 1, 12, 0, 0)
    wait = calc.calculate_wait_time(arrival, 120, "day")
    assert wait == 0.0

    # CASE 2: Arrive at 19:00. Duration 2 hours.
    # Finishes at 21:00 (Night). Must wait for tomorrow 08:00.
    # Wait = 19:00 -> 08:00 (+1) = 13 hours = 780 minutes
    arrival = datetime(2025, 1, 1, 19, 0, 0)
    wait = calc.calculate_wait_time(arrival, 120, "day")
    assert wait == 780.0

    # CASE 3: Arrive at 04:00 (Night). Must wait for 08:00.
    # Wait = 4 hours = 240 minutes
    arrival = datetime(2025, 1, 1, 4, 0, 0)
    wait = calc.calculate_wait_time(arrival, 120, "day")
    assert wait == 240.0
