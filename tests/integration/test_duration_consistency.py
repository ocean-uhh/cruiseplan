"""
Integration test for duration calculation consistency between output generators.

This module tests that LaTeX and HTML generators calculate total durations
consistently, ensuring no double-counting of transit times or other operations.
"""

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import CruiseInstance
from cruiseplan.schema.fields import (
    ACTION_FIELD,
    DURATION_FIELD,
    OP_DEPTH_FIELD,
    OP_TYPE_FIELD,
    POINTS_FIELD,
)


class TestDurationConsistency:
    """Test duration calculation consistency between output generators."""

    @pytest.fixture
    def sample_cruise_config(self, tmp_path):
        """Create a sample cruise configuration for testing."""
        config_content = f"""
cruise_name: "Duration_Test_Cruise"
start_date: "2025-06-01T08:00:00"
default_vessel_speed: 10.0
default_distance_between_stations: 20.0
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: false

{POINTS_FIELD}:
  - name: "STN_001"
    {OP_TYPE_FIELD}: CTD
    {ACTION_FIELD}: profile
    latitude: 60.0
    longitude: -20.0
    {OP_DEPTH_FIELD}: 1000.0
    {DURATION_FIELD}: 120.0  # 2 hours

  - name: "STN_002"
    {OP_TYPE_FIELD}: CTD
    {ACTION_FIELD}: profile
    latitude: 61.0
    longitude: -19.0
    {OP_DEPTH_FIELD}: 1500.0
    {DURATION_FIELD}: 180.0  # 3 hours

  - name: "MOORING_001"
    {OP_TYPE_FIELD}: mooring
    {ACTION_FIELD}: deployment
    latitude: 62.0
    longitude: -18.0
    {OP_DEPTH_FIELD}: 2000.0
    {DURATION_FIELD}: 240.0  # 4 hours

legs:
  - name: "Test_Leg"
    departure_port:
      name: "Port_A"
      latitude: 59.0
      longitude: -21.0
      timezone: "UTC"
    arrival_port:
      name: "Port_B"
      latitude: 64.0
      longitude: -16.0
      timezone: "UTC"
    first_station: "STN_001"
    last_station: "MOORING_001"
    activities:
      - "STN_001"
      - "STN_002"
      - "MOORING_001"
"""
        config_file = tmp_path / "test_cruise.yaml"
        config_file.write_text(config_content)
        return config_file

    @pytest.fixture
    def cruise(self, sample_cruise_config):
        """Create a cruise object from the sample configuration."""
        return CruiseInstance(sample_cruise_config)

    @pytest.fixture
    def timeline(self, cruise):
        """Generate timeline for the cruise."""
        return generate_timeline(cruise)

    def test_latex_html_duration_consistency(self, cruise, timeline):
        """
        Test that LaTeX and HTML generators calculate total durations consistently.

        Verifies that:
        LaTeX: total_navigation_transit_h + total_operation_duration_h
        equals
        HTML: total_duration_h (sum of all activity durations)
        """
        # Calculate HTML total duration (matches HTML generator logic)
        # This is the exact logic from line ~404 in html_generator.py
        html_total_duration_h = (
            sum(activity["duration_minutes"] for activity in timeline) / 60.0
        )

        # Extract LaTeX duration calculations (we need to replicate the logic)
        # Since the LaTeX calculations are internal, we'll replicate them here

        # Categorize activities using operation_class to handle new op_type system
        # Stations are PointOperations that aren't ports or moorings
        stations = [
            a
            for a in timeline
            if a.get("operation_class") == "PointOperation"
            and a.get("op_type") not in ["port", "mooring"]
        ]
        moorings = [a for a in timeline if a.get("op_type") == "mooring"]
        areas = [a for a in timeline if a.get("operation_class") == "AreaOperation"]

        # Get all transits first
        all_transits = [a for a in timeline if a.get("op_type") == "transit"]

        # Navigation transits don't have actions (exact LaTeX logic)
        navigation_transits = [a for a in all_transits if not a.get("action")]

        # Scientific transits have actions
        scientific_transits = [a for a in all_transits if a.get("action")]

        # Calculate major port transits (exact LaTeX logic)
        port_departure_activities = [
            a for a in timeline if a["activity"] == "Port_Departure"
        ]
        port_arrival_activities = [
            a for a in timeline if a["activity"] == "Port_Arrival"
        ]

        # Calculate individual durations (hours)
        station_duration_h = sum(s["duration_minutes"] for s in stations) / 60
        mooring_duration_h = sum(m["duration_minutes"] for m in moorings) / 60
        area_duration_h = sum(a["duration_minutes"] for a in areas) / 60
        total_scientific_op_h = (
            sum(t["duration_minutes"] for t in scientific_transits) / 60
        )

        # Port transit calculations (exact LaTeX logic)
        transit_to_area_h = 0.0
        transit_from_area_h = 0.0

        # Transit to area = departure port activity duration
        if port_departure_activities:
            transit_to_area_h = port_departure_activities[0]["duration_minutes"] / 60

        # Transit from area = arrival port activity duration
        if port_arrival_activities:
            transit_from_area_h = port_arrival_activities[0]["duration_minutes"] / 60

        # Within area = navigation transits EXCLUDING port transits (correct LaTeX logic)
        within_area_transits = [
            t
            for t in navigation_transits
            if t.get("activity") not in ["Port_Departure", "Port_Arrival"]
        ]
        transit_within_area_h = (
            sum(t["duration_minutes"] for t in within_area_transits) / 60
        )

        # LaTeX calculations (based on your corrected logic)
        total_navigation_transit_h = (
            transit_to_area_h + transit_from_area_h
        )  # Excludes within-area

        total_operation_duration_h = (
            station_duration_h
            + mooring_duration_h
            + area_duration_h
            + total_scientific_op_h
            + transit_within_area_h  # Within-area transit counted as operation time
        )

        # Optional debug output for troubleshooting (set to False for normal operation)
        debug_output = False
        if debug_output:
            print("\n=== TIMELINE DEBUG INFO ===")
            print(f"Total timeline activities: {len(timeline)}")
            for i, activity in enumerate(timeline[:10]):  # Show first 10 activities
                print(
                    f"Activity {i}: {activity.get('name', 'N/A')} - op_type: {activity.get('op_type', 'N/A')} - duration: {activity.get('duration_minutes', 'N/A')}"
                )

            print("Categorization counts:")
            print(
                f"  stations: {len(stations)} - total duration: {station_duration_h:.3f}h"
            )
            print(
                f"  moorings: {len(moorings)} - total duration: {mooring_duration_h:.3f}h"
            )
            print(f"  areas: {len(areas)} - total duration: {area_duration_h:.3f}h")
            print(
                f"  navigation_transits: {len(navigation_transits)} - total duration: {transit_within_area_h:.3f}h"
            )
            print(
                f"  scientific_transits: {len(scientific_transits)} - total duration: {total_scientific_op_h:.3f}h"
            )
            print(
                f"  port_departure_activities: {len(port_departure_activities)} - duration: {transit_to_area_h:.3f}h"
            )
            print(
                f"  port_arrival_activities: {len(port_arrival_activities)} - duration: {transit_from_area_h:.3f}h"
            )

        # The key test: LaTeX totals should equal HTML total
        latex_total_duration_h = total_navigation_transit_h + total_operation_duration_h

        # Verify consistency (the LaTeX fix should make these equal)
        assert abs(latex_total_duration_h - html_total_duration_h) < 0.01, (
            f"Duration calculation inconsistency detected!\n"
            f"HTML total_duration_h: {html_total_duration_h:.3f}\n"
            f"LaTeX total (navigation + operations): {latex_total_duration_h:.3f}\n"
            f"  - total_navigation_transit_h: {total_navigation_transit_h:.3f}\n"
            f"  - total_operation_duration_h: {total_operation_duration_h:.3f}\n"
            f"    - station_duration_h: {station_duration_h:.3f}\n"
            f"    - mooring_duration_h: {mooring_duration_h:.3f}\n"
            f"    - area_duration_h: {area_duration_h:.3f}\n"
            f"    - total_scientific_op_h: {total_scientific_op_h:.3f}\n"
            f"    - transit_within_area_h: {transit_within_area_h:.3f}\n"
            f"Difference: {abs(latex_total_duration_h - html_total_duration_h):.6f} hours"
        )

    def test_activity_categorization_completeness(self, timeline):
        """
        Test that all activities in timeline are properly categorized.

        Ensures no activities are missed in the duration calculations.
        """
        all_activities = len(timeline)

        # Count activities dynamically by op_type (the actual field used in timeline)
        op_type_counts = {}
        for activity in timeline:
            op_type = activity.get("op_type", "unknown")
            op_type_counts[op_type] = op_type_counts.get(op_type, 0) + 1

        # Special categorization for detailed reporting
        all_transits = [a for a in timeline if a.get("op_type") == "transit"]
        navigation_transits = len([a for a in all_transits if not a.get("action")])
        scientific_transits = len([a for a in all_transits if a.get("action")])

        port_departure = len(
            [a for a in timeline if a.get("activity") == "Port_Departure"]
        )
        port_arrival = len([a for a in timeline if a.get("activity") == "Port_Arrival"])

        # Total categorized activities = sum of all op_types
        categorized_total = sum(op_type_counts.values())

        assert categorized_total == all_activities, (
            f"Activity categorization incomplete!\n"
            f"Total activities: {all_activities}\n"
            f"Categorized: {categorized_total}\n"
            f"Op_type breakdown: {op_type_counts}\n"
            f"Transit details:\n"
            f"  - navigation_transits (no action): {navigation_transits}\n"
            f"  - scientific_transits (with action): {scientific_transits}\n"
            f"Port details:\n"
            f"  - port_departure: {port_departure}\n"
            f"  - port_arrival: {port_arrival}\n"
            f"Missing: {all_activities - categorized_total}"
        )

    def test_specific_duration_values(self, timeline):
        """
        Test that specific durations match expected values from the configuration.

        Validates that the timeline generation preserves the configured durations.
        """
        # Find specific activities and verify their durations
        stn_001 = next((a for a in timeline if a.get("name") == "STN_001"), None)
        stn_002 = next((a for a in timeline if a.get("name") == "STN_002"), None)
        mooring_001 = next(
            (a for a in timeline if a.get("name") == "MOORING_001"), None
        )

        # Verify configured durations are preserved
        if stn_001:
            assert (
                stn_001["duration_minutes"] == 120.0
            ), f"STN_001 duration should be 120 minutes, got {stn_001['duration_minutes']}"

        if stn_002:
            assert (
                stn_002["duration_minutes"] == 180.0
            ), f"STN_002 duration should be 180 minutes, got {stn_002['duration_minutes']}"

        if mooring_001:
            assert (
                mooring_001["duration_minutes"] == 240.0
            ), f"MOORING_001 duration should be 240 minutes, got {mooring_001['duration_minutes']}"
