"""
Comprehensive integration tests for TC4 mixed operations configuration.
Tests duration calculations, distance accuracy, and complete workflow.
"""

import tempfile
from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation import enrich_configuration
from cruiseplan.utils.config import ConfigLoader


class TestTC4MixedOpsComprehensive:
    """Comprehensive tests for TC4 mixed operations scenario."""

    def test_tc4_comprehensive_duration_breakdown(self):
        """Test comprehensive duration breakdown for TC4 mixed operations."""
        yaml_path = "tests/fixtures/tc4_mixed_ops.yaml"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        # Use enrichment for metadata only (no depths to avoid CI variability)
        import tempfile

        temp_dir = Path(tempfile.gettempdir())
        enriched_path = temp_dir / f"tc4_test_enriched_{hash(yaml_path) % 10000}.yaml"

        try:
            # Ensure the file doesn't exist before we start
            if enriched_path.exists():
                enriched_path.unlink()

            # Enrich only for defaults and coords, skip depths to avoid CI bathymetry variability
            enrich_configuration(
                yaml_path, output_path=enriched_path, add_depths=False, add_coords=True
            )

            # Verify the enriched file exists and is readable
            if not enriched_path.exists():
                pytest.fail(f"Enriched file was not created at {enriched_path}")

            # Load enriched configuration
            loader = ConfigLoader(str(enriched_path))
            config = loader.load()
        finally:
            # Clean up temporary enriched file
            if enriched_path.exists():
                enriched_path.unlink()

        timeline = generate_timeline(config)

        # Expected duration breakdown (hours) - now with separate transit activities
        expected_durations = {
            1: 57.8,  # Port_Departure: Halifax to Operations (577.8nm @ 10kt)
            2: 0.5,  # STN_001: CTD operation (may vary based on depth calculation)
            3: 6.0,  # Transit to ADCP_Survey: 60nm @ 10kt
            4: 12.0,  # ADCP_Survey: Scientific transit (60nm @ 5kt)
            5: 6.0,  # Transit to Area_01: 60nm @ 10kt
            6: 2.0,  # Area_01: Survey area (120 min)
            7: 202.9,  # Port_Arrival: Operations to Cadiz (2029nm @ 10kt)
        }

        # Expected transit distances (nm) - separate transit activities have the distances
        expected_transit_distances = {
            1: 577.8,  # Port_Departure: Halifax to operations
            2: 0.0,  # STN_001: no transit (already at location)
            3: 60.0,  # Transit to ADCP_Survey: STN_001 to ADCP start
            4: 0.0,  # ADCP_Survey: no transit (separate activity handles it)
            5: 60.0,  # Transit to Area_01: ADCP end to Area_01
            6: 0.0,  # Area_01: no transit (separate activity handles it)
            7: 2029.1,  # Port_Arrival: Area_01 to Cadiz
        }

        # Expected activity types
        expected_activity_types = {
            1: "Port_Departure",
            2: "Station",
            3: "Transit",
            4: "Transit",
            5: "Transit",
            6: "Area",
            7: "Port_Arrival",
        }

        print("\n🔍 TC4 Mixed Operations Duration Analysis:")
        print(f"Total activities: {len(timeline)}")

        total_duration_h = 0.0
        for i, activity in enumerate(timeline, 1):
            duration_h = activity["duration_minutes"] / 60
            transit_dist = activity.get("transit_dist_nm", 0)
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

        # Calculate expected total with separate transit activities
        expected_total = (
            57.8  # 1. Port_Departure: Halifax to Operations
            + 0.5  # 2. STN_001: CTD operation
            + 6.0  # 3. Transit to ADCP_Survey: 60nm @ 10kt
            + 12.0  # 4. ADCP_Survey: Scientific transit operation (60nm @ 5kt)
            + 6.0  # 5. Transit to Area_01: 60nm @ 10kt
            + 2.0  # 6. Area_01: Survey area operation (120 min)
            + 202.9  # 7. Port_Arrival: Operations to Cadiz
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
            loader = ConfigLoader(str(enriched_path))
            config = loader.load()
        finally:
            if enriched_path.exists():
                enriched_path.unlink()

        timeline = generate_timeline(config)

        # Verify operation sequencing with separate transit activities
        operation_names = [activity["label"] for activity in timeline]
        expected_sequence = [
            "Departure: Halifax to Operations",
            "STN_001",
            "Transit to ADCP_Survey",
            "ADCP_Survey",
            "Transit to Area_01",
            "Area_01",
            "Arrival: Operations to Cadiz",
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
