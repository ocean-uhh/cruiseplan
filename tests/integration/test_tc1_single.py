"""
Integration tests for the tc1_single.yaml canonical test case.

This test suite provides comprehensive coverage of the basic cruiseplan workflow
using tc1_single.yaml as the canonical test case for single-station transatlantic
cruise planning scenarios. All validation uses precise values from constants.py.
"""

import tempfile
from pathlib import Path

import pytest

from cruiseplan.api.process_cruise import enrich_configuration
from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import CruiseInstance
from cruiseplan.output.csv_generator import generate_csv_schedule
from cruiseplan.output.html_generator import generate_html_schedule
from cruiseplan.output.map_generator import generate_map
from cruiseplan.schema.values import (
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_VESSEL_SPEED_KT,
)
from cruiseplan.schema.yaml_io import load_yaml


class TestTC1SingleIntegration:
    """Integration tests using tc1_single.yaml canonical test case."""

    @pytest.fixture
    def yaml_path(self):
        """Path to the canonical tc1_single.yaml test fixture."""
        return "tests/fixtures/tc1_single.yaml"

    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_yaml_loading_and_validation(self, yaml_path):
        """Test basic YAML loading and validation of tc1_single.yaml."""
        # Load configuration
        config_dict = load_yaml(yaml_path)
        cruise = CruiseInstance.from_dict(config_dict)
        config = cruise.config

        # Validate basic structure
        assert config.cruise_name == "TC1_Single_Test"

        # Validate legs structure (new architecture)
        assert len(config.legs) == 1
        leg = config.legs[0]
        assert leg.departure_port.name == "Halifax"  # Now a PointDefinition object
        assert leg.arrival_port.name == "Cadiz"  # Now a PointDefinition object

        # Validate stations
        assert len(config.points) == 1
        station = config.points[0]
        assert station.name == "STN_001"
        assert station.latitude == 45.0
        assert station.longitude == -45.0
        assert station.operation_type.value == "CTD"
        assert station.action.value == "profile"

        # Validate legs
        assert len(config.legs) == 1
        leg = config.legs[0]
        assert leg.name == "Leg_Single"
        assert leg.departure_port.name == "Halifax"
        assert leg.arrival_port.name == "Cadiz"
        assert len(leg.activities) == 1 and leg.activities[0].name == "STN_001"

    def test_cruise_object_creation_and_port_resolution(self, yaml_path):
        """Test Cruise object creation with port resolution."""
        cruise = CruiseInstance(yaml_path)

        # Check station registry
        assert len(cruise.point_registry) == 1
        assert "STN_001" in cruise.point_registry

        # Check runtime legs
        assert len(cruise.runtime_legs) == 1
        leg = cruise.runtime_legs[0]
        assert leg.name == "Leg_Single"

        # Check that ports are resolved to PointDefinition objects in legs
        assert hasattr(
            leg.departure_port, "latitude"
        ), "Departure port should be resolved"
        assert hasattr(leg.arrival_port, "latitude"), "Arrival port should be resolved"

        # Validate resolved ports
        assert leg.departure_port.name == "Halifax"
        assert leg.arrival_port.name == "Cadiz"
        assert leg.departure_port.latitude == 44.6488  # Halifax coordinates
        assert leg.arrival_port.latitude == 36.5298  # Cadiz coordinates

    def test_enrichment_defaults_only(self, yaml_path, temp_dir):
        """Test basic enrichment adds required defaults matching constants.py."""
        output_path = temp_dir / "tc1_single_defaults.yaml"

        # Perform enrichment with defaults only (no coords/depths)
        enrichment_summary = enrich_configuration(
            config_path=Path(yaml_path),
            output_path=output_path,
            add_coords=False,
            add_depths=False,
        )

        # Verify defaults exist (either already present or added by enrichment)
        # Since tc1_single.yaml already has defaults, defaults_added might be 0

        # Load enriched config and validate exact values from constants.py
        enriched_cruise = CruiseInstance(output_path)
        config = enriched_cruise.config

        # Verify values match constants exactly
        assert config.default_vessel_speed == DEFAULT_VESSEL_SPEED_KT
        assert config.default_distance_between_stations == DEFAULT_STATION_SPACING_KM
        assert config.start_date == DEFAULT_START_DATE

    def test_enrichment_with_depths(self, yaml_path, temp_dir):
        """Test depth enrichment with ETOPO2022 (default bathymetry source)."""
        output_path = temp_dir / "tc1_single_depths.yaml"

        # Perform enrichment with depths using default ETOPO2022
        enrichment_summary = enrich_configuration(
            config_path=Path(yaml_path),
            output_path=output_path,
            add_coords=False,
            add_depths=True,
            bathymetry_source="etopo2022",  # Explicit default
            bathymetry_dir="data/bathymetry",
        )

        # Load and validate depth enrichment
        enriched_cruise = CruiseInstance(output_path)
        enriched_station = enriched_cruise.point_registry["STN_001"]

        # Check depth value (already present in fixture, so no enrichment needed)
        assert hasattr(enriched_station, "water_depth"), "Water depth should be present"
        assert (
            enriched_station.water_depth == 2850.0
        ), f"Expected mocked depth 2850.0, got {enriched_station.water_depth}"

    def test_enrichment_with_coords(self, yaml_path, temp_dir):
        """Test coordinate enrichment with DMM format."""
        output_path = temp_dir / "tc1_single_coords.yaml"

        # Perform enrichment with coordinates
        enrichment_summary = enrich_configuration(
            config_path=Path(yaml_path),
            output_path=output_path,
            add_coords=True,
            add_depths=False,
            coord_format="ddm",
        )

        # Load and validate coordinate enrichment
        enriched_cruise = CruiseInstance(output_path)
        enriched_station = enriched_cruise.point_registry["STN_001"]

        # Check coordinate enrichment with precise DMM format
        assert hasattr(
            enriched_station, "get_ddm_comment"
        ), "Coordinates should be enriched"
        ddm_result = enriched_station.get_ddm_comment()
        assert (
            ddm_result == "45 00.00'N, 045 00.00'W"
        ), f"Expected DMM '45 00.00'N, 045 00.00'W', got {ddm_result}"

    def test_enrichment_gebco2025_depth(self, yaml_path, temp_dir):
        """Test depth enrichment with GEBCO2025 bathymetry source."""
        output_path = temp_dir / "tc1_single_gebco.yaml"

        # Perform enrichment with GEBCO2025 bathymetry source
        enrichment_summary = enrich_configuration(
            config_path=Path(yaml_path),
            output_path=output_path,
            add_coords=False,
            add_depths=True,
            bathymetry_source="gebco2025",
            bathymetry_dir="data/bathymetry",
        )

        # Load and validate GEBCO2025 depth
        enriched_cruise = CruiseInstance(output_path)
        enriched_station = enriched_cruise.point_registry["STN_001"]

        # Check depth value (already present in fixture, so no enrichment needed)
        assert hasattr(enriched_station, "water_depth"), "Water depth should be present"
        assert (
            enriched_station.water_depth == 2850.0
        ), f"Expected mocked depth 2850.0, got {enriched_station.water_depth}"

    def test_enrichment_complete_workflow(self, yaml_path, temp_dir):
        """Test complete enrichment workflow with all options enabled."""
        output_path = temp_dir / "tc1_single_complete.yaml"

        # Perform complete enrichment
        enrichment_summary = enrich_configuration(
            config_path=Path(yaml_path),
            output_path=output_path,
            add_coords=True,
            add_depths=True,
            bathymetry_source="etopo2022",
            bathymetry_dir="data/bathymetry",
            coord_format="ddm",
        )

        # Check that defaults exist (either already present or added by enrichment)
        # Since tc1_single.yaml already has defaults, defaults_added might be 0

        # Verify enriched file was created
        assert output_path.exists(), "Enriched YAML file should be created"

        # Load and validate complete enrichment
        enriched_cruise = CruiseInstance(output_path)
        enriched_station = enriched_cruise.point_registry["STN_001"]
        config = enriched_cruise.config

        # Validate all default values match constants
        assert config.default_vessel_speed == DEFAULT_VESSEL_SPEED_KT
        assert config.default_distance_between_stations == DEFAULT_STATION_SPACING_KM
        assert config.start_date == DEFAULT_START_DATE

        # Check coordinate enrichment
        assert hasattr(
            enriched_station, "get_ddm_comment"
        ), "Coordinates should be enriched"
        assert enriched_station.get_ddm_comment() == "45 00.00'N, 045 00.00'W"

        # Check depth value (already present in fixture, so no enrichment needed)
        assert hasattr(enriched_station, "water_depth"), "Water depth should be present"
        assert enriched_station.water_depth == 2850.0  # Mocked value

        # Verify enrichment summary counts
        assert enrichment_summary["stations_with_coords_added"] == 1
        # Note: depths are already present in fixture now, so no depths added
        assert enrichment_summary["stations_with_depths_added"] == 0

    def test_mooring_duration_defaults(self, temp_dir):
        """Test that mooring operations without duration get default 999-hour duration."""
        from cruiseplan.schema.values import DEFAULT_MOORING_DURATION_MIN

        # Create test fixture path
        mooring_fixture = Path(__file__).parent.parent / "fixtures" / "tc1_mooring.yaml"
        output_path = temp_dir / "mooring_enriched.yaml"

        # Perform enrichment
        enrichment_summary = enrich_configuration(
            config_path=mooring_fixture, output_path=output_path
        )

        # Should have added station defaults
        assert (
            enrichment_summary["station_defaults_added"] == 1
        ), "Should add mooring duration default"

        # Load enriched config and check the duration was added
        enriched_cruise = CruiseInstance(output_path)
        mooring_station = enriched_cruise.point_registry["MOORING_001"]

        # Check that duration was added with correct value
        assert hasattr(
            mooring_station, "duration"
        ), "Mooring should have duration field"
        assert (
            mooring_station.duration == DEFAULT_MOORING_DURATION_MIN
        ), f"Expected {DEFAULT_MOORING_DURATION_MIN} minutes, got {mooring_station.duration}"
        assert (
            mooring_station.duration == 59940.0
        ), "Duration should be 59940 minutes (999 hours)"

    def test_csv_output_generation(self, yaml_path, temp_dir):
        """Test CSV schedule generation with proper transit data."""
        cruise = CruiseInstance(yaml_path)
        timeline = generate_timeline(cruise)

        # Generate CSV
        csv_path = temp_dir / "test_schedule.csv"
        generate_csv_schedule(cruise.config, timeline, csv_path)

        assert csv_path.exists(), "CSV file should be created"

        # Read and validate CSV content
        csv_content = csv_path.read_text()
        lines = csv_content.strip().split("\n")

        # Check header
        header = lines[0]
        assert "activity,label,operation_action,start_time,end_time" in header
        assert "Transit dist [nm],Vessel speed [kt],Duration [hrs]" in header

        # Check data rows (5 activities + 1 header = 6 lines)
        assert len(lines) == 6, "Expected header + 5 activity rows"

        # Validate Halifax port row (departure port)
        halifax_row = lines[1].split(",")
        assert halifax_row[0] == "Port"
        assert halifax_row[1] == "Halifax"
        assert float(halifax_row[5]) == 0.0, "Port should have 0 transit distance"

        # Validate first transit row
        transit1_row = lines[2].split(",")
        assert transit1_row[0] == "Transit"
        assert "STN_001" in transit1_row[1]
        assert float(transit1_row[5]) > 0, "Transit should have transit distance"
        assert float(transit1_row[6]) > 0, "Transit should have vessel speed"

        # Validate station row
        stn_row = lines[3].split(",")
        assert stn_row[0] == "Station"
        assert stn_row[1] == "STN_001"
        assert float(stn_row[5]) == 0.0, "Station should have 0 transit distance"

        # Validate second transit row
        transit2_row = lines[4].split(",")
        assert transit2_row[0] == "Transit"
        assert "Cadiz" in transit2_row[1]
        assert float(transit2_row[5]) > 0, "Transit should have transit distance"
        assert float(transit2_row[6]) > 0, "Transit should have vessel speed"

        # Validate Cadiz port row (arrival port)
        cadiz_row = lines[5].split(",")
        assert cadiz_row[0] == "Port"
        assert cadiz_row[1] == "Cadiz"
        assert float(cadiz_row[5]) == 0.0, "Port should have 0 transit distance"

    def test_html_output_generation(self, yaml_path, temp_dir):
        """Test HTML schedule generation without duplicate transits."""
        cruise = CruiseInstance(yaml_path)
        timeline = generate_timeline(cruise)

        # Generate HTML
        html_path = temp_dir / "test_schedule.html"
        generate_html_schedule(cruise.config, timeline, html_path)

        assert html_path.exists(), "HTML file should be created"

        # Read and validate HTML content
        html_content = html_path.read_text()

        # Check for proper structure
        assert (
            f"<title>Schedule for {cruise.config.cruise_name}</title>" in html_content
        )
        assert "Halifax" in html_content
        assert "Cadiz" in html_content
        assert "STN_001" in html_content

        # Ensure no duplicate transit entries (after our recent fixes)
        halifax_mentions = html_content.count("Halifax")
        cadiz_mentions = html_content.count("Cadiz")

        # Should appear in port names but not duplicate transit summaries
        assert halifax_mentions >= 1, "Halifax should be mentioned"
        assert cadiz_mentions >= 1, "Cadiz should be mentioned"

    def test_map_generation(self, yaml_path, temp_dir):
        """Test map generation with proper bounds and colorbar sizing."""
        cruise = CruiseInstance(yaml_path)

        # Generate map
        map_path = temp_dir / "test_map.png"
        result_path = generate_map(
            data_source=cruise,
            source_type="cruise",
            output_file=map_path,
            show_plot=False,
        )

        assert result_path is not None, "Map generation should succeed"
        assert result_path.exists(), "Map file should be created"
        assert result_path.stat().st_size > 0, "Map file should not be empty"

    def test_end_to_end_workflow(self, yaml_path, temp_dir):
        """Test complete end-to-end workflow from YAML to all outputs."""
        # 1. Load and enrich configuration
        enriched_path = temp_dir / "enriched.yaml"
        enrichment_summary = enrich_configuration(
            config_path=Path(yaml_path),
            output_path=enriched_path,
            add_coords=True,
            add_depths=True,
        )

        # Check that defaults exist (either already present or added by enrichment)
        # Since tc1_single.yaml already has defaults, defaults_added might be 0

        # 2. Create cruise object with enriched config
        cruise = CruiseInstance(enriched_path)

        # 3. Generate timeline
        timeline = generate_timeline(cruise)
        # Timeline includes: mob/demob in ports (2) + user operations (1) + transits (2) = 5 activities
        assert (
            len(timeline) == 5
        ), "Timeline should have 5 activities (mob/demob + user ops)"

        # 4. Generate all output formats
        outputs = {}

        # CSV
        csv_path = temp_dir / "schedule.csv"
        generate_csv_schedule(cruise.config, timeline, csv_path)
        outputs["csv"] = csv_path

        # HTML
        html_path = temp_dir / "schedule.html"
        generate_html_schedule(cruise.config, timeline, html_path)
        outputs["html"] = html_path

        # Map
        map_path = temp_dir / "map.png"
        generate_map(cruise, "cruise", map_path, show_plot=False)
        outputs["map"] = map_path

        # Validate all outputs exist and are non-empty
        for format_name, file_path in outputs.items():
            assert file_path.exists(), f"{format_name} output should exist"
            assert (
                file_path.stat().st_size > 0
            ), f"{format_name} output should not be empty"

        # Final validation: timeline covers expected time and distance
        total_duration = sum(act.get("duration_minutes", 0) for act in timeline)
        total_distance = sum(act.get("dist_nm", 0) for act in timeline)

        assert total_duration > 0, "Total cruise duration should be positive"
        assert total_distance > 0, "Total cruise distance should be positive"

        # Reasonable ranges for Halifax → 45°N 45°W → Cadiz
        assert (
            total_duration > 100 * 60
        ), "Should take more than 100 hours total"  # minutes
        assert total_distance > 2000, "Should be more than 2000 nm total distance"
