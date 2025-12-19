"""
Debug tests for scheduler timeline generation.
These tests provide detailed output for understanding and debugging scheduler behavior.
"""

import tempfile
from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation import enrich_configuration
from cruiseplan.utils.config import ConfigLoader


class TestSchedulerDebug:
    """Debug tests that provide detailed timeline analysis."""

    @pytest.mark.parametrize("fixture_name", ["tc4_mixed_ops.yaml"])
    def test_scheduler_debug_output(self, fixture_name, capsys):
        """Generate detailed debug output for scheduler timeline generation."""
        yaml_path = f"tests/fixtures/{fixture_name}"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        print(f"\n{'='*60}")
        print(f"Debugging Scheduler: {fixture_name}")
        print(f"{'='*60}")

        try:
            # Create temporary enriched file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as tmp_file:
                enriched_path = Path(tmp_file.name)

            try:
                # Enrich the fixture file to add missing global fields
                enrich_configuration(yaml_path, output_path=enriched_path)

                # Load enriched configuration
                loader = ConfigLoader(str(enriched_path))
                config = loader.load()
            finally:
                # Clean up temporary enriched file
                if enriched_path.exists():
                    enriched_path.unlink()

            print("✅ Config loaded:")
            print(f"   Cruise: {config.cruise_name}")
            print(f"   Start date: {config.start_date}")
            print(f"   Start time: {getattr(config, 'start_time', 'not set')}")
            print(f"   Legs: {len(config.legs)}")
            for leg in config.legs:
                print(
                    f"     {leg.name}: {getattr(leg, 'first_station', 'no first')} -> {getattr(leg, 'last_station', 'no last')}"
                )
            print(f"   Default vessel speed: {config.default_vessel_speed} knots")

            print(f"\n   Stations: {len(config.stations or [])}")
            if config.stations:
                for i, stn in enumerate(config.stations):
                    if hasattr(stn, "position") and stn.position:
                        print(
                            f"     {i+1}. {stn.name} at {stn.position.latitude}, {stn.position.longitude}"
                        )
                    else:
                        print(f"     {i+1}. {stn.name} - NO POSITION!")

            # Count mooring operations from stations list
            mooring_operations = [
                s
                for s in (config.stations or [])
                if hasattr(s, "operation_type") and s.operation_type.value == "mooring"
            ]
            print(f"\n   Mooring operations: {len(mooring_operations)}")
            if mooring_operations:
                for i, mooring in enumerate(mooring_operations):
                    if hasattr(mooring, "position") and mooring.position:
                        duration = getattr(mooring, "duration", "not set")
                        print(
                            f"     {i+1}. {mooring.name} at {mooring.position.latitude}, {mooring.position.longitude} ({duration} min)"
                        )
                    else:
                        print(f"     {i+1}. {mooring.name} - NO POSITION!")

            print(f"\n   Transits: {len(config.transits or [])}")
            if config.transits:
                for i, transit in enumerate(config.transits):
                    vessel_speed = getattr(transit, "vessel_speed", None)
                    speed_str = (
                        f" at {vessel_speed} knots"
                        if vessel_speed
                        else " (default speed)"
                    )
                    print(f"     {i+1}. {transit.name}{speed_str}")
                    for j, point in enumerate(transit.route):
                        print(f"        {j+1}. {point.latitude}, {point.longitude}")

            print(f"\n   Legs: {len(config.legs or [])}")
            if config.legs:
                for i, leg in enumerate(config.legs):
                    stations = getattr(leg, "stations", [])
                    sequence = getattr(leg, "sequence", [])
                    print(
                        f"     {i+1}. {leg.name}: stations={stations}, sequence={sequence}"
                    )

            print("\n   Port information (leg-level):")
            for leg in config.legs:
                print(f"     {leg.name}: {leg.departure_port} -> {leg.arrival_port}")

            # Generate timeline with debug info
            print("\n🔍 Generating timeline...")
            timeline = generate_timeline(config)

            print(f"📊 Timeline result: {len(timeline)} activities")
            if timeline:
                for i, activity in enumerate(timeline):
                    transit_dist = activity.get("transit_dist_nm", 0)
                    lat, lon = activity["lat"], activity["lon"]
                    print(
                        f"   {i+1}. {activity['activity']}: {activity['label']} at ({lat:.3f}, {lon:.3f})"
                    )
                    print(
                        f"      Duration: {activity['duration_minutes']:.1f} min, Transit to here: {transit_dist:.2f} nm"
                    )
                    if transit_dist > 0:
                        # Use vessel speed from activity if available, otherwise default
                        vessel_speed = activity.get(
                            "vessel_speed_kt", config.default_vessel_speed
                        )
                        expected_time_h = transit_dist / vessel_speed
                        actual_time_h = activity["duration_minutes"] / 60
                        print(
                            f"      Expected transit time: {expected_time_h:.2f}h, Actual op time: {actual_time_h:.2f}h"
                        )

                # Summary statistics
                total_duration_h = sum(a["duration_minutes"] for a in timeline) / 60
                total_transit_nm = sum(a.get("transit_dist_nm", 0) for a in timeline)
                total_days = total_duration_h / 24

                print("\n📈 Summary:")
                print(
                    f"   Total timeline duration: {total_duration_h:.1f} hours ({total_days:.1f} days)"
                )
                print(f"   Total transit distance: {total_transit_nm:.1f} nm")

                # Activity type breakdown
                activities_by_type = {}
                for activity in timeline:
                    activity_type = activity["activity"]
                    if activity_type not in activities_by_type:
                        activities_by_type[activity_type] = {
                            "count": 0,
                            "duration_h": 0,
                        }
                    activities_by_type[activity_type]["count"] += 1
                    activities_by_type[activity_type]["duration_h"] += (
                        activity["duration_minutes"] / 60
                    )

                print("   Activity breakdown:")
                for activity_type, stats in activities_by_type.items():
                    print(
                        f"     {activity_type}: {stats['count']} activities, {stats['duration_h']:.1f}h"
                    )
            else:
                print("   ❌ Empty timeline!")

            # Test passes if timeline is generated successfully
            assert len(timeline) > 0, f"Timeline should not be empty for {fixture_name}"

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()
            raise

    def test_scheduler_debug_mixed_operations_details(self, capsys):
        """Detailed debug output specifically for mixed operations to verify transit calculations."""
        yaml_path = "tests/fixtures/tc4_mixed_ops.yaml"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        print(f"\n{'='*60}")
        print("Mixed Operations Transit Calculation Debug")
        print(f"{'='*60}")

        # Create temporary enriched file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp_file:
            enriched_path = Path(tmp_file.name)

        try:
            # Enrich the fixture file to add missing global fields
            enrich_configuration(yaml_path, output_path=enriched_path)

            # Load enriched configuration
            loader = ConfigLoader(str(enriched_path))
            config = loader.load()
        finally:
            # Clean up temporary enriched file
            if enriched_path.exists():
                enriched_path.unlink()

        timeline = generate_timeline(config)

        # Debug: Print all activities in the timeline
        print(f"\n📋 Generated timeline with {len(timeline)} activities:")
        for i, activity in enumerate(timeline, 1):
            print(
                f"   Activity {i}: {activity.get('label', 'Unknown')} ({activity.get('activity', 'Unknown')})"
            )
            print(f"     - transit_dist_nm: {activity.get('transit_dist_nm', 0):.2f}")
            print(
                f"     - operation_dist_nm: {activity.get('operation_dist_nm', 0):.2f}"
            )

        # Verify specific distance calculations
        print("\n🔍 Verifying transit distance calculations:")

        # Expected inter-operation distances (transit_dist_nm) for tc4_mixed_ops.yaml
        # Updated for new timeline structure with separate transit activities
        expected_transit_distances = {
            1: (
                577.81,
                "Halifax to operations area",
            ),  # Port departure to first operation
            2: (0.00, "STN_001 (no additional transit)"),  # Already at location
            3: (60.04, "STN_001 to ADCP_Survey start"),  # CTD to ADCP survey start
            4: (0.00, "ADCP_Survey operation (no transit)"),  # Scientific operation
            5: (60.04, "ADCP_Survey end to Area_01"),  # ADCP end to survey area
            6: (0.00, "Area_01 operation (no transit)"),  # Area operation
            7: (2029.12, "Area_01 to arrival port"),  # Operations to Cadiz
        }

        # Expected operation distances (operation_dist_nm) - only for scientific transits
        expected_operation_distances = {
            4: (
                60.04,
                "ADCP_Survey route distance",
            ),  # ADCP survey route length (46°N to 47°N)
        }

        for i, activity in enumerate(timeline, 1):
            # Check transit distances (inter-operation) for transit records
            if i in expected_transit_distances:
                expected_dist, description = expected_transit_distances[i]
                actual_dist = activity.get("transit_dist_nm", 0)
                print(f"   Activity {i}: {description}")
                print(
                    f"     Expected transit_dist_nm: {expected_dist:.2f} nm, Actual: {actual_dist:.2f} nm"
                )

                assert (
                    abs(actual_dist - expected_dist) < 0.1
                ), f"Transit distance mismatch for activity {i}: expected {expected_dist:.2f}, got {actual_dist:.2f}"

            # Check operation distances (route lengths for scientific operations)
            if i in expected_operation_distances:
                expected_op_dist, description = expected_operation_distances[i]
                actual_op_dist = activity.get("operation_dist_nm", 0)
                print(f"   Activity {i}: {description}")
                print(
                    f"     Expected operation_dist_nm: {expected_op_dist:.2f} nm, Actual: {actual_op_dist:.2f} nm"
                )

                assert (
                    abs(actual_op_dist - expected_op_dist) < 0.1
                ), f"Operation distance mismatch for activity {i}: expected {expected_op_dist:.2f}, got {actual_op_dist:.2f}"

        # Verify custom vessel speed is applied for ADCP_Survey
        adcp_activity = timeline[
            3
        ]  # ADCP_Survey is at index 3 (4th activity) in new structure
        assert adcp_activity["label"] == "ADCP_Survey"

        # At 5 knots, the ADCP route should take longer than at default speed
        adcp_duration_h = adcp_activity["duration_minutes"] / 60
        print(f"\n   ADCP survey operation duration: {adcp_duration_h:.2f}h at 5 knots")
        assert (
            adcp_duration_h > 10
        ), f"ADCP survey should take >10h at 5 knots, got {adcp_duration_h:.2f}h"

        print("\n✅ All distance calculations verified!")
