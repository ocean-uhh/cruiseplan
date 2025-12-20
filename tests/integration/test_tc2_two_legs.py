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

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import Cruise
from cruiseplan.core.validation import enrich_configuration
from cruiseplan.output.html_generator import generate_html_schedule
from cruiseplan.output.netcdf_generator import NetCDFGenerator
from cruiseplan.utils.config import ConfigLoader
from cruiseplan.utils.constants import DEFAULT_MOORING_DURATION_MIN


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
        """Helper to create a Cruise object with temporary enrichment."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp_file:
            enriched_path = Path(tmp_file.name)

        try:
            enrich_configuration(str(base_config_path), output_path=enriched_path)
            return Cruise(str(enriched_path))
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
            loader = ConfigLoader(str(enriched_path))
            config = loader.load()
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
        assert first_leg.departure_port == "port_halifax"
        assert first_leg.arrival_port == "port_bremerhaven"

        # Validate second leg
        second_leg = config.legs[1]
        assert second_leg.name == "Leg_North"
        assert second_leg.departure_port == "port_bremerhaven"
        assert second_leg.arrival_port == "port_reykjavik"

        # Validate stations
        assert len(config.stations) == 2

        # STN_001 (CTD station)
        stn_001 = next(s for s in config.stations if s.name == "STN_001")
        assert stn_001.latitude == 50.0
        assert stn_001.longitude == -50.0
        assert stn_001.operation_type.value == "CTD"
        assert stn_001.action.value == "profile"

        # STN_002 (Mooring station)
        stn_002 = next(s for s in config.stations if s.name == "STN_002")
        assert stn_002.latitude == 60.0
        assert stn_002.longitude == -30.0
        assert stn_002.operation_type.value == "mooring"
        assert stn_002.action.value == "deployment"
        assert stn_002.duration == DEFAULT_MOORING_DURATION_MIN

        # Validate legs
        assert len(config.legs) == 2

        # Leg_Atlantic
        leg_atlantic = next(l for l in config.legs if l.name == "Leg_Atlantic")
        assert leg_atlantic.departure_port == "port_halifax"
        assert leg_atlantic.arrival_port == "port_bremerhaven"
        assert leg_atlantic.activities == ["STN_001"]

        # Leg_North
        leg_north = next(l for l in config.legs if l.name == "Leg_North")
        assert leg_north.departure_port == "port_bremerhaven"
        assert leg_north.arrival_port == "port_reykjavik"
        assert leg_north.activities == ["STN_002"]

    def test_cruise_object_creation_and_port_resolution(self, base_config_path):
        """Test Cruise object creation with proper port resolution."""
        cruise = self._get_enriched_cruise(base_config_path)

        # Check station registry
        assert len(cruise.station_registry) == 2
        assert "STN_001" in cruise.station_registry
        assert "STN_002" in cruise.station_registry

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
            "stations": [
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
                    "first_station": "STN_MOORING",
                    "last_station": "STN_MOORING",
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
        enriched_cruise = Cruise(enriched_path)
        mooring_station = enriched_cruise.station_registry["STN_MOORING"]
        assert hasattr(mooring_station, "duration")
        assert mooring_station.duration == DEFAULT_MOORING_DURATION_MIN
        assert mooring_station.duration == 59940.0  # 999 hours

    def test_timeline_generation_with_expected_structure(self, base_config_path):
        """Test timeline generation produces expected two-leg structure."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

        # Validate timeline structure for two-leg cruise: should have 6 activities
        # Leg1: Port_Departure, Station (STN_001), Port_Arrival (to Bremerhaven)
        # Leg2: Port_Departure (from Bremerhaven), Mooring (STN_002), Port_Arrival (to Reykjavik)
        assert len(timeline) == 6, "Expected 6 activities for two-leg cruise"

        # Check activity types and sequence
        activities = [
            (act["activity"], act.get("label", ""), act.get("leg_name", ""))
            for act in timeline
        ]

        # Leg_Atlantic activities (first 3)
        assert activities[0][0] == "Port_Departure"
        assert "Halifax" in activities[0][1]
        assert activities[0][2] == "Leg_Atlantic"

        assert activities[1][0] == "Station"
        assert "STN_001" in activities[1][1]
        assert activities[1][2] == "Leg_Atlantic"

        assert activities[2][0] == "Port_Arrival"
        assert "Bremerhaven" in activities[2][1]
        assert activities[2][2] == "Leg_Atlantic"

        # Leg_North activities (last 3)
        assert activities[3][0] == "Port_Departure"
        assert "Bremerhaven" in activities[3][1]
        assert activities[3][2] == "Leg_North"

        assert activities[4][0] == "Mooring"
        assert "STN_002" in activities[4][1]
        assert activities[4][2] == "Leg_North"

        assert activities[5][0] == "Port_Arrival"
        assert "Reykjavik" in activities[5][1]
        assert activities[5][2] == "Leg_North"

    def test_specific_transit_distances(self, base_config_path):
        """Test that specific expected transit distances are generated."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

        # Extract transit distances
        transit_activities = [
            act for act in timeline if act.get("transit_dist_nm", 0) > 0
        ]

        # Should have 4 transit activities (Port_Departure and Port_Arrival for each leg)
        assert (
            len(transit_activities) >= 4
        ), "Expected at least 4 activities with transit distances"

        # Test specific expected distances (within 1% tolerance)
        halifax_to_stn001_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Port_Departure"
            and "Halifax" in act.get("label", "")
        )

        # Halifax to STN_001: 637.7 nm
        expected_distance_1 = 637.7
        actual_distance_1 = halifax_to_stn001_activity.get("transit_dist_nm", 0)
        assert (
            abs(actual_distance_1 - expected_distance_1) / expected_distance_1 < 0.01
        ), f"Halifax to STN_001 distance should be ~{expected_distance_1} nm, got {actual_distance_1} nm"

        # STN_001 to Bremerhaven: 2124.8 nm
        stn001_to_bremerhaven_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Port_Arrival"
            and "Bremerhaven" in act.get("label", "")
        )

        expected_distance_2 = 2124.8
        actual_distance_2 = stn001_to_bremerhaven_activity.get("transit_dist_nm", 0)
        assert (
            abs(actual_distance_2 - expected_distance_2) / expected_distance_2 < 0.01
        ), f"STN_001 to Bremerhaven distance should be ~{expected_distance_2} nm, got {actual_distance_2} nm"

        # Verify other transit distances are reasonable
        bremerhaven_to_stn002_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Port_Departure"
            and "Bremerhaven" in act.get("label", "")
            and act.get("leg_name") == "Leg_North"
        )

        stn002_to_reykjavik_activity = next(
            act
            for act in timeline
            if act.get("activity") == "Port_Arrival"
            and "Reykjavik" in act.get("label", "")
        )

        # These should be > 0 and reasonable (rough bounds check)
        assert (
            bremerhaven_to_stn002_activity.get("transit_dist_nm", 0) > 1000
        ), "Bremerhaven to STN_002 should be substantial distance"
        assert (
            stn002_to_reykjavik_activity.get("transit_dist_nm", 0) > 200
        ), "STN_002 to Reykjavik should be reasonable distance"

    def test_html_output_leg_durations(self, base_config_path, temp_dir):
        """Test that HTML output shows expected leg durations: 11.5 days for Leg_Atlantic, 48.5 days for Leg_North."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

        # Generate HTML
        html_path = temp_dir / "tc2_schedule.html"
        generate_html_schedule(cruise.config, timeline, html_path)

        assert html_path.exists(), "HTML file should be created"

        # Read HTML content
        html_content = html_path.read_text()

        # Check for expected leg durations
        # Based on the specific expectation: 11.5 days for Leg_Atlantic, 48.5 days for Leg_North
        assert (
            "11.5 days" in html_content
        ), "Leg_Atlantic should show 11.5 days total duration"
        assert (
            "48.5 days" in html_content
        ), "Leg_North should show 48.5 days total duration"

        # Verify leg section headers
        assert "Leg_Atlantic" in html_content, "Should contain Leg_Atlantic section"
        assert "Leg_North" in html_content, "Should contain Leg_North section"

        # Verify port names appear correctly (with our " to " fix)
        assert (
            "Halifax to Operations" in html_content
        ), "Should show Halifax departure with ' to ' format"
        assert (
            "Operations to Bremerhaven" in html_content
        ), "Should show Bremerhaven arrival with ' to ' format"
        assert (
            "Bremerhaven to Operations" in html_content
        ), "Should show Bremerhaven departure with ' to ' format"
        assert (
            "Operations to Reykjavik" in html_content
        ), "Should show Reykjavik arrival with ' to ' format"

    def test_netcdf_output_mooring_duration(self, base_config_path, temp_dir):
        """Test that NetCDF output contains the expected mooring duration value."""
        cruise = self._get_enriched_cruise(base_config_path)
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

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
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

        # Validate timeline has correct structure
        assert len(timeline) == 6, "Two-leg cruise should have 6 activities"

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
        total_distance = sum(act.get("transit_dist_nm", 0) for act in timeline)

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
            len(leg_atlantic_activities) == 3
        ), "Leg_Atlantic should have exactly 3 activities"
        assert (
            len(leg_north_activities) == 3
        ), "Leg_North should have exactly 3 activities"
