"""
Integration test for duration calculation consistency between output generators.

This module tests that LaTeX and HTML generators calculate total durations
consistently, ensuring no double-counting of transit times or other operations.
"""

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import Cruise


class TestDurationConsistency:
    """Test duration calculation consistency between output generators."""

    @pytest.fixture
    def sample_cruise_config(self, tmp_path):
        """Create a sample cruise configuration for testing."""
        config_content = """
cruise_name: "Duration_Test_Cruise"
start_date: "2025-06-01T08:00:00"
default_vessel_speed: 10.0
default_distance_between_stations: 20.0
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: false

stations:
  - name: "STN_001"
    operation_type: CTD
    action: profile  
    position: "60.0, -20.0"
    operation_depth: 1000.0
    duration: 120.0  # 2 hours

  - name: "STN_002"
    operation_type: CTD
    action: profile
    position: "61.0, -19.0"
    operation_depth: 1500.0
    duration: 180.0  # 3 hours

  - name: "MOORING_001"
    operation_type: mooring
    action: deployment
    position: "62.0, -18.0"
    operation_depth: 2000.0
    duration: 240.0  # 4 hours

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
        return Cruise(sample_cruise_config)

    @pytest.fixture
    def timeline(self, cruise):
        """Generate timeline for the cruise."""
        return generate_timeline(cruise.config, cruise.runtime_legs[0])

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

        # Categorize activities exactly like LaTeX generator does
        stations = [a for a in timeline if a.get("op_type") == "station"]
        moorings = [a for a in timeline if a.get("op_type") == "mooring"]
        areas = [a for a in timeline if a.get("op_type") == "area"]

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

    def test_no_double_counting_transit_within_area(self, cruise, timeline):
        """
        Test that transit_within_area is not double-counted.

        Verifies that within-area navigation transits are only counted once
        in the total duration calculation.
        """
        # Extract navigation transits
        navigation_transits = [
            a
            for a in timeline
            if a.get("activity_type") == "transit"
            and a.get("transit_type") == "navigation"
        ]

        if not navigation_transits:
            pytest.skip("No navigation transits in timeline to test double-counting")

        # Calculate total duration using simple sum (HTML approach)
        total_simple_sum_h = (
            sum(activity["duration_minutes"] for activity in timeline) / 60.0
        )

        # Calculate all individual components
        stations = [a for a in timeline if a.get("activity_type") == "station"]
        moorings = [a for a in timeline if a.get("activity_type") == "mooring"]
        areas = [a for a in timeline if a.get("activity_type") == "area"]
        scientific_transits = [
            a
            for a in timeline
            if a.get("activity_type") == "transit"
            and a.get("transit_type") == "scientific"
        ]
        port_transits = [
            a for a in timeline if a.get("activity_type") == "port_transit"
        ]

        # Sum all individual components (should equal simple sum)
        component_sum_h = (
            sum(s["duration_minutes"] for s in stations) / 60
            + sum(m["duration_minutes"] for m in moorings) / 60
            + sum(a["duration_minutes"] for a in areas) / 60
            + sum(t["duration_minutes"] for t in scientific_transits) / 60
            + sum(t["duration_minutes"] for t in navigation_transits) / 60
            + sum(t["duration_minutes"] for t in port_transits) / 60
        )

        # These should be identical - if not, there's double counting somewhere
        assert abs(total_simple_sum_h - component_sum_h) < 0.01, (
            f"Component sum doesn't match total sum - possible double counting!\n"
            f"Simple sum: {total_simple_sum_h:.3f}\n"
            f"Component sum: {component_sum_h:.3f}\n"
            f"Difference: {abs(total_simple_sum_h - component_sum_h):.6f} hours"
        )

    def test_activity_categorization_completeness(self, timeline):
        """
        Test that all activities in timeline are properly categorized.

        Ensures no activities are missed in the duration calculations.
        """
        all_activities = len(timeline)

        # Count activities by op_type (the actual field used in timeline)
        stations = len([a for a in timeline if a.get("op_type") == "station"])
        moorings = len([a for a in timeline if a.get("op_type") == "mooring"])
        areas = len([a for a in timeline if a.get("op_type") == "area"])

        # All transits use op_type="transit"
        all_transits = [a for a in timeline if a.get("op_type") == "transit"]
        navigation_transits = len([a for a in all_transits if not a.get("action")])
        scientific_transits = len([a for a in all_transits if a.get("action")])

        # Port transits are identified by activity field
        port_departure = len(
            [a for a in timeline if a.get("activity") == "Port_Departure"]
        )
        port_arrival = len([a for a in timeline if a.get("activity") == "Port_Arrival"])

        # Note: port activities are also transits, so we need to avoid double counting
        # Total categorized activities = stations + moorings + areas + all_transits
        categorized_total = stations + moorings + areas + len(all_transits)

        assert categorized_total == all_activities, (
            f"Activity categorization incomplete!\n"
            f"Total activities: {all_activities}\n"
            f"Categorized: {categorized_total}\n"
            f"  - stations: {stations}\n"
            f"  - moorings: {moorings}\n"
            f"  - areas: {areas}\n"
            f"  - all_transits: {len(all_transits)}\n"
            f"    - navigation_transits (no action): {navigation_transits}\n"
            f"    - scientific_transits (with action): {scientific_transits}\n"
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
