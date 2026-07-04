"""
Integration tests for the delay_start leg field.
"""

import pytest

from cruiseplan.runtime.cruise import CruiseInstance
from cruiseplan.timeline.scheduler import generate_timeline

_BASE_YAML = """
cruise_name: "Delay_Start_Test"
start_date: "2025-01-01T08:00:00"
default_vessel_speed: 10.0
default_distance_between_stations: 15.0

points:
  - name: STN_001
    latitude: 60.0
    longitude: -20.0
    operation_type: CTD
    action: profile
    water_depth: 1000.0
    duration: 60.0

legs:
  - name: Test_Leg
    departure_port:
      name: Port_A
      latitude: 58.0
      longitude: -22.0
      timezone: UTC
    arrival_port:
      name: Port_B
      latitude: 62.0
      longitude: -18.0
      timezone: UTC
    first_activity: STN_001
    last_activity: STN_001
    activities: [STN_001]
"""

_DELAYED_YAML = """
cruise_name: "Delay_Start_Test"
start_date: "2025-01-01T08:00:00"
default_vessel_speed: 10.0
default_distance_between_stations: 15.0

points:
  - name: STN_001
    latitude: 60.0
    longitude: -20.0
    operation_type: CTD
    action: profile
    water_depth: 1000.0
    duration: 60.0

legs:
  - name: Test_Leg
    delay_start: 120
    departure_port:
      name: Port_A
      latitude: 58.0
      longitude: -22.0
      timezone: UTC
    arrival_port:
      name: Port_B
      latitude: 62.0
      longitude: -18.0
      timezone: UTC
    first_activity: STN_001
    last_activity: STN_001
    activities: [STN_001]
"""


class TestDelayStart:
    """Test that delay_start on a leg shifts the schedule end time forward."""

    def test_delay_start_shifts_end_time(self, tmp_path):
        """delay_start: 120 should shift the entire schedule end time by 120 minutes."""
        base_file = tmp_path / "base.yaml"
        base_file.write_text(_BASE_YAML)
        base_timeline = generate_timeline(CruiseInstance(base_file))
        base_end = base_timeline[-1]["end_time"]

        delayed_file = tmp_path / "delayed.yaml"
        delayed_file.write_text(_DELAYED_YAML)
        delayed_timeline = generate_timeline(CruiseInstance(delayed_file))
        delayed_end = delayed_timeline[-1]["end_time"]

        diff_minutes = (delayed_end - base_end).total_seconds() / 60
        assert diff_minutes == pytest.approx(120.0), (
            f"Expected schedule to end 120 min later with delay_start=120, "
            f"got {diff_minutes:.1f} min difference"
        )

    def test_no_delay_start_unchanged(self, tmp_path):
        """Without delay_start, two identical configs produce the same end time."""
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        file_a.write_text(_BASE_YAML)
        file_b.write_text(_BASE_YAML)

        end_a = generate_timeline(CruiseInstance(file_a))[-1]["end_time"]
        end_b = generate_timeline(CruiseInstance(file_b))[-1]["end_time"]

        assert end_a == end_b
