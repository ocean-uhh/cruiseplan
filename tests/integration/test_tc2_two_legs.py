"""
Integration tests for TC2_TwoLegs_Test configuration.

This module provides comprehensive testing of the two-leg cruise configuration,
including enrichment, scheduling, timeline generation, and output validation.
Tests verify specific expected values like transit distances, leg durations,
and mooring defaults.
"""

import sys
import tempfile
from pathlib import Path

import pytest

from cruiseplan.api.process_cruise import enrich_configuration
from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import CruiseInstance
from cruiseplan.output.html_generator import generate_html_schedule
from cruiseplan.output.netcdf_generator import NetCDFGenerator
from cruiseplan.schema import POINTS_FIELD
from cruiseplan.schema.values import DEFAULT_MOORING_DURATION_MIN
from cruiseplan.schema.yaml_io import load_yaml


class TestTC2TwoLegsIntegration:
    """Integration tests using TC2_TwoLegs_Test configuration."""

    @pytest.fixture
    def base_config_path(self):
        """Path to the base TC2 two legs configuration."""
        return Path(__file__).parent.parent / "fixtures" / "tc2_two_legs.yaml"

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def _get_enriched_cruise(self, base_config_path):
        """Helper to create a CruiseInstance object with temporary enrichment."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp_file:
            enriched_path = Path(tmp_file.name)

        try:
            enrich_configuration(str(base_config_path), output_path=enriched_path)
            return CruiseInstance(str(enriched_path))
        finally:
            if enriched_path.exists():
                enriched_path.unlink()

    def test_yaml_loading_and_validation(self, base_config_path):
        """Test basic YAML loading and validation of TC2 two-legs configuration."""
        # Create temporary enriched file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp_file:
            enriched_path = Path(tmp_file.name)

        try:
            # Enrich the fixture file to add missing global fields
            enrich_configuration(str(base_config_path), output_path=enriched_path)

            # Load enriched configuration
            config_dict = load_yaml(enriched_path)
            cruise = CruiseInstance.from_dict(config_dict)
            config = cruise.config
        finally:
            # Clean up temporary enriched file
            if enriched_path.exists():
                enriched_path.unlink()

        # Validate basic structure
        assert config.cruise_name == "TC2_TwoLegs_Test"

        # Validate legs structure (new architecture)
        assert len(config.legs) == 2

        # Validate first leg
        first_leg = config.legs[0]
        assert first_leg.name == "Leg_Atlantic"
        # Port references are automatically resolved to PointDefinition objects
        assert first_leg.departure_port.name == "Halifax"  # Resolved name
        assert first_leg.arrival_port.name == "Bremerhaven"  # Resolved name

        # Validate second leg
        second_leg = config.legs[1]
        assert second_leg.name == "Leg_North"
        assert second_leg.departure_port.name == "Bremerhaven"  # Resolved name
        assert second_leg.arrival_port.name == "Reykjavik"  # Resolved name

        # Validate stations
        assert len(config.points) == 2

        # STN_001 (CTD station)
        stn_001 = next(s for s in config.points if s.name == "STN_001")
        assert stn_001.latitude == 50.0
        assert stn_001.longitude == -50.0
        assert stn_001.operation_type.value == "CTD"
        assert stn_001.action.value == "profile"

        # STN_002 (Mooring station)
        stn_002 = next(s for s in config.points if s.name == "STN_002")
        assert stn_002.latitude == 60.0
        assert stn_002.longitude == -30.0
        assert stn_002.operation_type.value == "mooring"
        assert stn_002.action.value == "deployment"
        assert stn_002.duration == DEFAULT_MOORING_DURATION_MIN

        # Validate legs
        assert len(config.legs) == 2

        # Leg_Atlantic
        leg_atlantic = next(leg for leg in config.legs if leg.name == "Leg_Atlantic")
        assert leg_atlantic.departure_port.name == "Halifax"
        assert leg_atlantic.arrival_port.name == "Bremerhaven"
        assert len(leg_atlantic.activities) == 1
        assert leg_atlantic.activities[0].name == "STN_001"

        # Leg_North
        leg_north = next(leg for leg in config.legs if leg.name == "Leg_North")
        assert leg_north.departure_port.name == "Bremerhaven"
        assert leg_north.arrival_port.name == "Reykjavik"
        assert len(leg_north.activities) == 1
        assert leg_north.activities[0].name == "STN_002"

    def test_cruise_object_creation_and_port_resolution(self, base_config_path):
        """Test Cruise object creation with proper port resolution."""
        cruise = self._get_enriched_cruise(base_config_path)

        # Check station registry
        assert len(cruise.point_registry) == 2
        assert "STN_001" in cruise.point_registry
        assert "STN_002" in cruise.point_registry

        # Check runtime legs with port resolution
        assert len(cruise.runtime_legs) == 2

        # Validate first leg ports are resolved
        leg_atlantic = cruise.runtime_legs[0]
        assert leg_atlantic.name == "Leg_Atlantic"
        assert hasattr(
            leg_atlantic.departure_port, "latitude"
        ), "Departure port should be resolved"
        assert hasattr(
            leg_atlantic.arrival_port, "latitude"
        ), "Arrival port should be resolved"
        assert leg_atlantic.departure_port.name == "Halifax"
        assert leg_atlantic.arrival_port.name == "Bremerhaven"
        assert abs(leg_atlantic.departure_port.latitude - 44.6488) < 0.001

        # Validate second leg ports are resolved
        leg_north = cruise.runtime_legs[1]
        assert leg_north.name == "Leg_North"
        assert hasattr(
            leg_north.departure_port, "latitude"
        ), "Departure port should be resolved"
        assert hasattr(
            leg_north.arrival_port, "latitude"
        ), "Arrival port should be resolved"
        assert leg_north.departure_port.name == "Bremerhaven"
        assert leg_north.arrival_port.name == "Reykjavik"

    def test_mooring_duration_enrichment(self, temp_dir):
        """Test that mooring operations get default duration during enrichment."""
        # Create a minimal config without mooring duration to test enrichment
        minimal_config = {
            "cruise_name": "Test_Mooring_Enrichment",
            POINTS_FIELD: [
                {
                    "name": "STN_MOORING",
                    "latitude": 60.0,
                    "longitude": -30.0,
                    "operation_type": "mooring",
                    "action": "deployment",
                    # Note: deliberately omitting duration field
                }
            ],
            "legs": [
                {
                    "name": "Test_Leg",
                    "departure_port": "port_halifax",
                    "arrival_port": "port_reykjavik",
                    "first_activity": "STN_MOORING",
                    "last_activity": "STN_MOORING",
                    "activities": ["STN_MOORING"],
                }
            ],
        }

        # Write minimal config
        import yaml

        minimal_path = temp_dir / "minimal_mooring.yaml"
        with open(minimal_path, "w") as f:
            yaml.dump(minimal_config, f)

        # Perform enrichment
        enriched_path = temp_dir / "enriched_mooring.yaml"
        enrichment_summary = enrich_configuration(
            config_path=minimal_path, output_path=enriched_path
        )

        # Verify mooring duration was added
        assert enrichment_summary["station_defaults_added"] == 1

        # Load enriched config and verify duration
        enriched_cruise = CruiseInstance(enriched_path)
        mooring_station = enriched_cruise.point_registry["STN_MOORING"]
        assert hasattr(mooring_station, "duration")
        assert mooring_station.duration == DEFAULT_MOORING_DURATION_MIN
        assert mooring_station.duration == 59940.0  # 999 hours

    def test_timeline_generation_with_expected_structure(self, base_config_path):
        """Test timeline generation produces expected two-leg structure."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise)

        # Validate timeline structure for two-leg cruise: should have 10 activities
        # Leg1: Port_Departure (Halifax), Transit, Station (STN_001), Transit, Port_Arrival (Bremerhaven)
        # Leg2: Port_Departure (Bremerhaven), Transit, Mooring (STN_002), Transit, Port_Arrival (Reykjavik)
        assert (
            len(timeline) == 10
        ), "Expected 10 activities for two-leg cruise (ports + operations + transits)"

        # Check activity types and sequence
        activities = [
            (act["activity"], act.get("label", ""), act.get("leg_name", ""))
            for act in timeline
        ]

        # Leg_Atlantic activities (first 5)
        assert activities[0][0] == "Port"  # Halifax departure
        assert "Halifax" in activities[0][1]
        assert activities[0][2] == "Leg_Atlantic"

        assert activities[1][0] == "Transit"  # Transit to STN_001
        assert "STN_001" in activities[1][1]
        assert activities[1][2] == "Leg_Atlantic"

        assert activities[2][0] == "Station"  # STN_001
        assert "STN_001" in activities[2][1]
        assert activities[2][2] == "Leg_Atlantic"

        assert activities[3][0] == "Transit"  # Transit to Bremerhaven
        assert "Bremerhaven" in activities[3][1]
        assert activities[3][2] == "Leg_Atlantic"

        assert activities[4][0] == "Port"  # Bremerhaven arrival
        assert "Bremerhaven" in activities[4][1]
        assert activities[4][2] == "Leg_Atlantic"

        # Leg_North activities (last 5)
        assert activities[5][0] == "Port"  # Bremerhaven departure
        assert "Bremerhaven" in activities[5][1]
        assert activities[5][2] == "Leg_North"

        assert activities[6][0] == "Transit"  # Transit to STN_002
        assert "STN_002" in activities[6][1]
        assert activities[6][2] == "Leg_North"

        assert activities[7][0] == "Mooring"  # STN_002
        assert "STN_002" in activities[7][1]
        assert activities[7][2] == "Leg_North"

        assert activities[8][0] == "Transit"  # Transit to Reykjavik
        assert "Reykjavik" in activities[8][1]
        assert activities[8][2] == "Leg_North"

        assert activities[9][0] == "Port"  # Reykjavik arrival
        assert "Reykjavik" in activities[9][1]
        assert activities[9][2] == "Leg_North"

    def test_specific_transit_distances(self, base_config_path):
        """Test that specific expected transit distances are generated."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise)

        # Extract transit distances
        transit_activities = [act for act in timeline if act.get("dist_nm", 0) > 0]

        # Should have 4 transit activities (Port_Departure and Port_Arrival for each leg)
        assert (
            len(transit_activities) >= 4
        ), "Expected at least 4 activities with transit distances"

        # Test specific expected distances (within 1% tolerance)
        # Look for transit activities by their labels
        halifax_to_stn001_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Transit" and "STN_001" in act.get("label", "")
        )

        # Halifax to STN_001: 637.7 nm
        expected_distance_1 = 637.7
        actual_distance_1 = halifax_to_stn001_activity.get("dist_nm", 0)
        assert (
            abs(actual_distance_1 - expected_distance_1) / expected_distance_1 < 0.01
        ), f"Halifax to STN_001 distance should be ~{expected_distance_1} nm, got {actual_distance_1} nm"

        # STN_001 to Bremerhaven: 2124.8 nm
        stn001_to_bremerhaven_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Transit"
            and "Bremerhaven" in act.get("label", "")
        )

        expected_distance_2 = 2124.8
        actual_distance_2 = stn001_to_bremerhaven_activity.get("dist_nm", 0)
        assert (
            abs(actual_distance_2 - expected_distance_2) / expected_distance_2 < 0.01
        ), f"STN_001 to Bremerhaven distance should be ~{expected_distance_2} nm, got {actual_distance_2} nm"

        # Verify other transit distances are reasonable
        bremerhaven_to_stn002_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Transit"
            and "STN_002" in act.get("label", "")
            and act.get("leg_name") == "Leg_North"
        )

        stn002_to_reykjavik_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Transit" and "Reykjavik" in act.get("label", "")
        )

        # These should be > 0 and reasonable (rough bounds check)
        assert (
            bremerhaven_to_stn002_activity.get("dist_nm", 0) > 1000
        ), "Bremerhaven to STN_002 should be substantial distance"
        assert (
            stn002_to_reykjavik_activity.get("dist_nm", 0) > 200
        ), "STN_002 to Reykjavik should be reasonable distance"

    def test_html_output_leg_durations(self, base_config_path, temp_dir):
        """Test that HTML output shows expected leg durations: 11.5 days for Leg_Atlantic, 48.5 days for Leg_North."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise)

        # Generate HTML
        html_path = temp_dir / "tc2_schedule.html"
        generate_html_schedule(cruise.config, timeline, html_path)

        assert html_path.exists(), "HTML file should be created"

        # Read HTML content
        html_content = html_path.read_text()

        # Check for expected leg durations
        # Based on the actual calculation: 11.5 days for Leg_Atlantic, 48.5 days for Leg_North
        assert (
            "11.5 days" in html_content
        ), "Leg_Atlantic should show 11.5 days total duration."
        assert (
            "48.5 days" in html_content
        ), "Leg_North should show 48.5 days total duration"

        # Verify leg section headers
        assert "Leg_Atlantic" in html_content, "Should contain Leg_Atlantic section"
        assert "Leg_North" in html_content, "Should contain Leg_North section"

        # Verify port names appear correctly (using display names not port IDs)
        assert (
            "Halifax" in html_content
        ), "Should show Halifax port with proper display name"
        assert (
            "Transit to Bremerhaven" in html_content
        ), "Should show transit to Bremerhaven with proper display name"
        assert (
            "Bremerhaven" in html_content
        ), "Should show Bremerhaven port with proper display name"
        assert (
            "Transit to Reykjavik" in html_content
        ), "Should show transit to Reykjavik with proper display name"

    def test_netcdf_output_mooring_duration(self, base_config_path, temp_dir):
        """Test that NetCDF output contains the expected mooring duration value."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise)

        # Generate NetCDF
        netcdf_generator = NetCDFGenerator()
        point_ops_path = temp_dir / "tc2_points.nc"

        # Generate point operations NetCDF (contains moorings)
        netcdf_generator.generate_point_operations(
            cruise.config, timeline, point_ops_path
        )

        assert point_ops_path.exists(), "NetCDF point operations file should be created"

        # Read and validate NetCDF content
        import xarray as xr

        # Disable timedelta decoding to get raw values
        ds = xr.open_dataset(point_ops_path, decode_timedelta=False)

        # Check that mooring duration is present and matches expected value
        # Find mooring operations
        operation_types = ds["operation_type"].values
        durations = ds["duration"].values

        # Convert to strings for comparison (NetCDF stores as bytes)
        operation_type_strings = [
            op.decode("utf-8") if isinstance(op, bytes) else str(op)
            for op in operation_types
        ]

        # Find mooring indices
        mooring_indices = [
            i
            for i, op_type in enumerate(operation_type_strings)
            if "mooring" in op_type.lower()
        ]

        assert (
            len(mooring_indices) > 0
        ), "Should have at least one mooring operation in NetCDF"

        # Check that mooring duration matches DEFAULT_MOORING_DURATION_MIN (converted to hours)
        expected_duration_hours = (
            DEFAULT_MOORING_DURATION_MIN / 60.0
        )  # Convert minutes to hours
        for idx in mooring_indices:
            mooring_duration = durations[idx]
            # Handle different duration representations
            if hasattr(mooring_duration, "total_seconds"):
                # pandas Timedelta object
                mooring_duration_hours = mooring_duration.total_seconds() / 3600.0
            elif (
                isinstance(mooring_duration, (int, float)) and mooring_duration > 10000
            ):
                # Likely nanoseconds, convert to hours
                mooring_duration_hours = float(mooring_duration) / (
                    1e9 * 3600.0
                )  # ns to hours
            else:
                # Regular float/int value
                mooring_duration_hours = float(mooring_duration)

            assert (
                abs(mooring_duration_hours - expected_duration_hours) < 0.1
            ), f"Mooring duration in NetCDF should be {expected_duration_hours} hours, got {mooring_duration_hours}"

        # Cleanup
        ds.close()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Tkinter/GUI issues on Windows CI"
    )
    def test_complete_two_leg_workflow(self, base_config_path, temp_dir):
        """Test complete end-to-end workflow for two-leg cruise configuration."""
        # 1. Load and validate configuration
        cruise = self._get_enriched_cruise(base_config_path)

        # 2. Generate timeline
        timeline = generate_timeline(cruise)

        # Validate timeline has correct structure
        assert (
            len(timeline) == 10
        ), "Two-leg cruise should have 10 activities (ports + operations + transits)"

        # 3. Test all output formats can be generated
        from cruiseplan.output.csv_generator import generate_csv_schedule
        from cruiseplan.output.kml_generator import generate_kml_schedule
        from cruiseplan.output.map_generator import generate_map

        outputs = {}

        # CSV
        csv_path = temp_dir / "tc2_schedule.csv"
        generate_csv_schedule(cruise.config, timeline, csv_path)
        outputs["csv"] = csv_path

        # HTML
        html_path = temp_dir / "tc2_schedule.html"
        generate_html_schedule(cruise.config, timeline, html_path)
        outputs["html"] = html_path

        # KML
        kml_path = temp_dir / "tc2_schedule.kml"
        generate_kml_schedule(cruise.config, timeline, kml_path)
        outputs["kml"] = kml_path

        # LaTeX (skip due to output format complexity - focus on core functionality)
        # latex_path = temp_dir / "tc2_schedule.tex"
        # generate_latex_tables(cruise.config, timeline, latex_path)
        # outputs["latex"] = latex_path

        # Map (timeline-based)
        map_path = temp_dir / "tc2_map.png"
        generate_map({"timeline": timeline}, "timeline", map_path, show_plot=False)
        outputs["map"] = map_path

        # NetCDF
        netcdf_generator = NetCDFGenerator()
        point_ops_path = temp_dir / "tc2_points.nc"
        ship_schedule_path = temp_dir / "tc2_ship.nc"

        netcdf_generator.generate_point_operations(
            cruise.config, timeline, point_ops_path
        )
        netcdf_generator.generate_ship_schedule(
            timeline, cruise.config, ship_schedule_path
        )
        outputs["netcdf_points"] = point_ops_path
        outputs["netcdf_ship"] = ship_schedule_path

        # Validate all outputs exist and are non-empty
        for format_name, file_path in outputs.items():
            assert file_path.exists(), f"{format_name} output should exist"
            assert (
                file_path.stat().st_size > 0
            ), f"{format_name} output should not be empty"

        # 4. Validate key metrics
        total_duration = sum(act.get("duration_minutes", 0) for act in timeline)
        total_distance = sum(act.get("dist_nm", 0) for act in timeline)

        assert total_duration > 0, "Total cruise duration should be positive"
        assert total_distance > 0, "Total cruise distance should be positive"

        # Specific validation for two-leg cruise
        assert (
            total_duration > 1400 * 60
        ), "Two-leg cruise should take more than 1400 hours total"  # minutes
        assert (
            total_distance > 4000
        ), "Two-leg cruise should cover more than 4000 nm total"

        # Validate mooring duration is substantial part of total
        mooring_duration = sum(
            act.get("duration_minutes", 0)
            for act in timeline
            if act.get("activity") == "Mooring"
        )
        assert (
            mooring_duration >= DEFAULT_MOORING_DURATION_MIN
        ), "Should include full mooring duration"

        # Final check: ensure leg separation is maintained
        leg_atlantic_activities = [
            act for act in timeline if act.get("leg_name") == "Leg_Atlantic"
        ]
        leg_north_activities = [
            act for act in timeline if act.get("leg_name") == "Leg_North"
        ]

        assert (
            len(leg_atlantic_activities) == 5
        ), f"Leg_Atlantic should have exactly 5 activities. Got: {len(leg_atlantic_activities)}"
        assert (
            len(leg_north_activities) == 5
        ), f"Leg_North should have exactly 5 activities. Got: {len(leg_north_activities)}"
