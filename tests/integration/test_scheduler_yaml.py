"""
Integration tests for the scheduler against real YAML fixture files.
"""

from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation import CruiseConfigurationError
from cruiseplan.utils.config import ConfigLoader


class TestSchedulerWithYAMLFixtures:
    """Integration tests for scheduler with actual YAML configurations."""

    def test_scheduler_with_simple_cruise(self):
        """Test scheduler with simple 2-station cruise."""
        yaml_path = "tests/fixtures/cruise_simple.yaml"

        # Load and validate configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        assert config.cruise_name == "Simple_Test_Cruise_2028"
        assert len(config.stations) == 2
        assert len(config.legs) == 1

        # Generate timeline
        timeline = generate_timeline(config)

        # Basic validations
        assert len(timeline) > 0, "Timeline should not be empty"
        assert (
            len(timeline) == 5
        ), "Expected: transit to area + station + inter-operation transit + station + transit from area"

        # Check timeline structure
        activities = [activity["activity"] for activity in timeline]
        assert (
            activities[0] == "Transit"
        ), "First activity should be transit to working area"
        assert activities[1] == "Station", "Second activity should be first station"
        assert (
            activities[2] == "Transit"
        ), "Third activity should be inter-operation transit"
        assert activities[3] == "Station", "Fourth activity should be second station"
        assert (
            activities[4] == "Transit"
        ), "Fifth activity should be transit from working area"

        # Check timing is sequential
        for i in range(len(timeline) - 1):
            assert (
                timeline[i]["end_time"] <= timeline[i + 1]["start_time"]
            ), f"Activity {i} should end before activity {i+1} starts"

        # Check total duration is reasonable (transatlantic crossing can be long)
        total_duration_hours = (
            timeline[-1]["end_time"] - timeline[0]["start_time"]
        ).total_seconds() / 3600
        assert (
            10 <= total_duration_hours <= 200
        ), f"Total duration {total_duration_hours:.1f}h seems unrealistic"

    def test_scheduler_with_mixed_operations(self):
        """Test scheduler with mixed operations (stations, moorings, transits)."""
        yaml_path = "tests/fixtures/cruise_mixed_ops.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()

        assert config.cruise_name == "Mixed_Operations_Test_2028"
        assert len(config.stations) == 2  # CTD station + mooring operation

        # Verify we have both operation types in stations
        operation_types = [s.operation_type.value for s in config.stations]
        assert "CTD" in operation_types
        assert "mooring" in operation_types

        # Generate timeline
        timeline = generate_timeline(config)

        # Should have activities for the mixed operations
        assert len(timeline) > 0

        # Check that station and mooring operations are both present
        operation_types = [activity["operation_type"] for activity in timeline]
        assert "station" in operation_types, "Should include station operation"
        assert "mooring" in operation_types, "Should include mooring operation"

        # Verify timing continuity
        for i in range(len(timeline) - 1):
            assert timeline[i]["end_time"] <= timeline[i + 1]["start_time"]

    def test_scheduler_with_multi_leg_cruise(self):
        """Test scheduler with multi-leg cruise configuration."""
        yaml_path = "tests/fixtures/cruise_multi_leg.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()

        assert config.cruise_name == "Multi_Leg_Expedition_2028"
        assert len(config.stations) == 6  # 3 stations per leg × 2 legs
        assert len(config.legs) == 2

        # Generate timeline
        timeline = generate_timeline(config)

        # Should handle all stations across multiple legs
        assert len(timeline) > 0

        # Should have more activities due to multiple stations
        station_activities = [a for a in timeline if a["activity"] == "Station"]
        assert len(station_activities) == 6, "Should process all 6 stations"

        # Check reasonable duration for multi-leg expedition
        total_duration_hours = (
            timeline[-1]["end_time"] - timeline[0]["start_time"]
        ).total_seconds() / 3600
        assert (
            total_duration_hours > 20
        ), "Multi-leg cruise should take substantial time"

    def test_scheduler_handles_missing_fixtures_gracefully(self):
        """Test that scheduler handles missing files appropriately."""
        with pytest.raises(CruiseConfigurationError):
            loader = ConfigLoader("tests/fixtures/nonexistent.yaml")
            loader.load()

    def test_all_fixtures_generate_valid_timelines(self):
        """Comprehensive test that all fixtures produce valid, non-empty timelines."""
        fixtures = [
            "tests/fixtures/cruise_simple.yaml",
            "tests/fixtures/cruise_mixed_ops.yaml",
            "tests/fixtures/cruise_multi_leg.yaml",
        ]

        for fixture_path in fixtures:
            if not Path(fixture_path).exists():
                pytest.skip(f"Fixture {fixture_path} not found")

            # Load config
            loader = ConfigLoader(fixture_path)
            config = loader.load()

            # Generate timeline
            timeline = generate_timeline(config)

            # Basic validations for all fixtures
            assert len(timeline) > 0, f"Timeline empty for {fixture_path}"

            # All activities should have required fields
            for activity in timeline:
                assert "activity" in activity
                assert "start_time" in activity
                assert "end_time" in activity
                assert "duration_minutes" in activity
                assert activity["duration_minutes"] > 0

            # Timeline should be temporally ordered
            for i in range(len(timeline) - 1):
                assert (
                    timeline[i]["end_time"] <= timeline[i + 1]["start_time"]
                ), f"Timeline ordering error in {fixture_path}"
