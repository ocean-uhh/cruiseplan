"""
Debug tests for scheduler timeline generation.
These tests provide detailed output for understanding and debugging scheduler behavior.
"""

from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.utils.config import ConfigLoader


class TestSchedulerDebug:
    """Debug tests that provide detailed timeline analysis."""

    @pytest.mark.parametrize(
        "fixture_name", ["cruise_simple.yaml", "cruise_mixed_ops.yaml"]
    )
    def test_scheduler_debug_output(self, fixture_name, capsys):
        """Generate detailed debug output for scheduler timeline generation."""
        yaml_path = f"tests/fixtures/{fixture_name}"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        print(f"\n{'='*60}")
        print(f"Debugging Scheduler: {fixture_name}")
        print(f"{'='*60}")

        try:
            # Load configuration
            loader = ConfigLoader(yaml_path)
            config = loader.load()

            print("✅ Config loaded:")
            print(f"   Cruise: {config.cruise_name}")
            print(f"   Start date: {config.start_date}")
            print(f"   Start time: {getattr(config, 'start_time', 'not set')}")
            print(f"   First station: {config.first_station}")
            print(f"   Last station: {config.last_station}")
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

            print(
                f"\n   Departure port: {config.departure_port.name} at {config.departure_port.position}"
            )
            print(
                f"   Arrival port: {config.arrival_port.name} at {config.arrival_port.position}"
            )

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
        yaml_path = "tests/fixtures/cruise_mixed_ops.yaml"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        print(f"\n{'='*60}")
        print("Mixed Operations Transit Calculation Debug")
        print(f"{'='*60}")

        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        # Verify specific distance calculations
        print("\n🔍 Verifying transit distance calculations:")

        # Expected inter-operation distances (transit_dist_nm) - only for transit records
        expected_transit_distances = {
            1: (372.67, "Departure port to CTD_Station_A"),
            3: (21.55, "CTD_Station_A to Survey_Line_Alpha start"),
            5: (219.12, "Survey_Line_Alpha end to Mooring_K7_Recovery"),
            9: (366.77, "Mooring_K7_Recovery to arrival port"),
        }

        # Expected operation distances (operation_dist_nm) - only for scientific transits
        expected_operation_distances = {
            4: (27.94, "Survey_Line_Alpha route distance"),
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

        # Verify custom vessel speed is applied
        survey_activity = timeline[
            3
        ]  # Survey_Line_Alpha (now at index 3 due to inter-operation transit)
        assert survey_activity["label"] == "Survey_Line_Alpha"

        # At 5 knots, the internal route should take longer than at 12 knots
        survey_duration_h = survey_activity["duration_minutes"] / 60
        print(f"\n   Survey operation duration: {survey_duration_h:.2f}h at 5 knots")
        assert (
            survey_duration_h > 4
        ), f"Survey should take >4h at 5 knots, got {survey_duration_h:.2f}h"

        print("\n✅ All distance calculations verified!")
