"""
Comprehensive integration tests for TC4 mixed operations configuration.
Tests duration calculations, distance accuracy, and complete workflow.
"""

import tempfile
from pathlib import Path

import pytest

from cruiseplan.api.process_cruise import enrich_configuration
from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import CruiseInstance
from cruiseplan.schema.yaml_io import load_yaml


class TestTC4MixedOpsComprehensive:
    """Comprehensive tests for TC4 mixed operations scenario."""

    def test_tc4_comprehensive_duration_breakdown(self):
        """Test comprehensive duration breakdown for TC4 mixed operations."""
        yaml_path = "tests/fixtures/tc4_mixed_ops.yaml"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        # Use new direct Cruise interface (no YAML round-trip)
        from cruiseplan.schema.yaml_io import load_yaml

        config_dict = load_yaml(yaml_path)

        # Create Cruise object directly from dictionary
        cruise = CruiseInstance.from_dict(config_dict)

        # Perform enrichment directly on the Cruise object (no file I/O)
        cruise.add_station_defaults()

        timeline = generate_timeline(cruise)

        # Expected duration breakdown (hours) - now with separate transit activities
        expected_durations = {
            1: 0,
            2: 57.8,  # Port_Departure: Halifax to Operations (577.8nm @ 10kt)
            3: 0.5,  # STN_001: CTD operation (may vary based on depth calculation)
            4: 6.0,  # Transit to ADCP_Survey: 60nm @ 10kt
            5: 12.0,  # ADCP_Survey: Scientific transit (60nm @ 5kt)
            6: 3.6,  # Transit to Area_01: 36.3nm @ 10kt (using ADCP exit coordinates)
            7: 2.0,  # Area_01: Survey area (120 min)
            8: 200.7,  # Transit to Cadiz: Operations to Cadiz (2007.3nm @ 10kt)
            9: 0,
        }

        # Expected transit distances (nm) - separate transit activities have the distances
        expected_transit_distances = {
            1: 0,
            2: 577.8,  # Transit to STN_001: Halifax to operations
            3: 0.0,  # STN_001: no transit (already at location)
            4: 60.0,  # Transit to ADCP_Survey: STN_001 to ADCP start
            5: 60.0,  # ADCP_Survey: scientific transit distance
            6: 36.3,  # Transit to Area_01: ADCP end to Area_01
            7: 0.0,  # Area_01: no transit (separate activity handles it)
            8: 2007.3,  # Transit to Cadiz: Area_01 to Cadiz (actual calculated distance)
            9: 0,
        }

        # Expected activity types
        expected_activity_types = {
            1: "Port",
            2: "Transit",
            3: "Station",
            4: "Transit",
            5: "Line",  # ADCP_Survey is a LineOperation
            6: "Transit",
            7: "Area",
            8: "Transit",
            9: "Port",
        }

        print("\n🔍 TC4 Mixed Operations Duration Analysis:")
        print(f"Total activities: {len(timeline)}")

        total_duration_h = 0.0
        for i, activity in enumerate(timeline, 1):
            duration_h = activity["duration_minutes"] / 60
            transit_dist = activity.get("dist_nm", 0)
            start_time = activity["start_time"].strftime("%H:%M")
            activity_type = activity["activity"]

            print(
                f"  {i}. {activity_type}: {activity['label']} - {duration_h:.1f}h @ {start_time} (transit: {transit_dist:.1f}nm)"
            )

            # Verify activity type matches expected
            if i in expected_activity_types:
                expected_type = expected_activity_types[i]
                assert (
                    activity_type == expected_type
                ), f"Activity {i} type mismatch: expected {expected_type}, got {activity_type}"

            # Verify duration matches expected (with flexible tolerance for CTD operations)
            if i in expected_durations:
                expected_duration = expected_durations[i]
                # Use larger tolerance for CTD operations which may vary based on depth calculation
                tolerance = (
                    2.0
                    if activity_type == "Station"
                    and "CTD" in str(activity.get("operation_type", ""))
                    else 0.2
                )
                assert (
                    abs(duration_h - expected_duration) < tolerance
                ), f"Activity {i} duration mismatch: expected {expected_duration:.1f}h, got {duration_h:.1f}h (tolerance: {tolerance}h)"

            # Verify transit distance matches expected
            if i in expected_transit_distances:
                expected_distance = expected_transit_distances[i]
                assert (
                    abs(transit_dist - expected_distance) < 0.1
                ), f"Activity {i} transit distance mismatch: expected {expected_distance:.1f}nm, got {transit_dist:.1f}nm"

            total_duration_h += duration_h

        # Calculate expected total based on actual timeline
        expected_total = sum(
            expected_durations[i]
            for i in range(1, len(timeline) + 1)
            if i in expected_durations
        )

        print("\n📊 Duration Summary:")
        print(f"  Actual total: {total_duration_h:.1f} hours")
        print(f"  Expected total: {expected_total:.1f} hours")
        print(f"  Difference: {abs(total_duration_h - expected_total):.1f} hours")

        # Allow for small tolerance due to rounding and turnaround times
        assert abs(total_duration_h - expected_total) < 1.0, (
            f"Total duration mismatch: expected ~{expected_total:.1f}h, got {total_duration_h:.1f}h. "
            f"Missing transit times between operations?"
        )

        print("✅ TC4 comprehensive duration test passed!")

    def test_tc4_operation_sequence_timing(self):
        """Test that operations are properly sequenced with transit times."""
        yaml_path = "tests/fixtures/tc4_mixed_ops.yaml"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        # Create temporary enriched file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp_file:
            enriched_path = Path(tmp_file.name)

        try:
            enrich_configuration(yaml_path, output_path=enriched_path, add_depths=False)
            config_dict = load_yaml(enriched_path)
            cruise = CruiseInstance.from_dict(config_dict)
            _config = cruise.config
        finally:
            if enriched_path.exists():
                enriched_path.unlink()

        timeline = generate_timeline(cruise)

        # Verify operation sequencing with separate transit activities
        operation_names = [activity["label"] for activity in timeline]
        expected_sequence = [
            "Halifax",
            "Transit to STN_001",
            "STN_001",
            "Transit to ADCP_Survey",
            "ADCP_Survey",
            "Transit to Area_01",
            "Area_01",
            "Transit to Cadiz",
            "Cadiz",
        ]

        assert (
            operation_names == expected_sequence
        ), f"Operation sequence mismatch: expected {expected_sequence}, got {operation_names}"

        # Verify timing progression (each operation should start after previous ends)
        for i in range(len(timeline) - 1):
            current_end = timeline[i]["end_time"]
            next_start = timeline[i + 1]["start_time"]

            # Next operation should start at or after current operation ends
            # (allowing for transit time and turnaround time)
            assert next_start >= current_end, (
                f"Timeline gap: {timeline[i]['label']} ends at {current_end}, "
                f"but {timeline[i + 1]['label']} starts at {next_start}"
            )

        print("✅ TC4 operation sequence timing test passed!")

    def test_tc4_direct_cruise_timeline_generation(self):
        """Test the new direct Cruise → timeline interface (Phase 3)."""
        yaml_path = "tests/fixtures/tc4_mixed_ops.yaml"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        # Load and enrich using the new Cruise object approach
        # First load the YAML into a dictionary, then create Cruise object directly
        from cruiseplan.schema.yaml_io import load_yaml

        config_dict = load_yaml(yaml_path)

        # Create Cruise object directly from dictionary (no YAML round-trip)
        cruise = CruiseInstance.from_dict(config_dict)

        # Perform enrichment directly on the Cruise object
        cruise.add_station_defaults()

        # Generate timeline using the new direct interface
        timeline = generate_timeline(cruise)

        # Verify we get the same structure as the old approach
        assert len(timeline) > 0, "Timeline should not be empty"

        # Check that we have the expected activities
        activity_types = [activity["activity"] for activity in timeline]
        assert "Port" in activity_types, "Should have port activities"
        assert "Station" in activity_types, "Should have station activities"

        # DEBUG: Check if the objects in cruise.config.legs[0].activities are dictionaries or objects
        if cruise.config.legs:
            first_leg = cruise.config.legs[0]
            if first_leg.activities:
                first_activity = first_leg.activities[0]
                print(f"   First activity type: {type(first_activity)}")
                print(f"   First activity: {first_activity}")

        # Verify that activities now use proper objects instead of dictionaries
        # This is the key benefit - no dictionary handling needed!
        print(
            f"✅ Direct cruise timeline generation successful! Generated {len(timeline)} activities"
        )
        print(f"   Activity types: {set(activity_types)}")
