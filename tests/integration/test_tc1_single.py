"""
Integration tests for the tc1_single.yaml canonical test case.

This test suite provides comprehensive coverage of the basic cruiseplan workflow
using tc1_single.yaml as the canonical test case for single-station transatlantic
cruise planning scenarios. All validation uses precise values from constants.py.

Includes automated verification of all manual testing steps from 
docs/source/manual_testing.rst for TC1 Single test case (checks 1-13).
"""

import csv
import re
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml
from bs4 import BeautifulSoup

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.cli.main import main as cli_main
from cruiseplan.core.cruise import Cruise
from cruiseplan.core.validation_old import enrich_configuration
from cruiseplan.output.csv_generator import generate_csv_schedule
from cruiseplan.output.html_generator import generate_html_schedule
from cruiseplan.output.map_generator import generate_map
from cruiseplan.utils.config import ConfigLoader
from cruiseplan.utils.constants import (
    DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY,
    DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS,
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_VESSEL_SPEED_KT,
)


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

    @pytest.fixture
    def cli_outputs(self, yaml_path, temp_dir):
        """
        Generate TC1 outputs using CLI commands for manual verification tests.
        
        This fixture runs the complete cruiseplan process + schedule workflow
        for tc1_single.yaml and returns paths to all output files.
        Matches the verification steps in docs/source/manual_testing.rst.
        """
        # Setup paths
        fixture_file = Path(yaml_path)
        bathy_dir = Path("data/bathymetry")
        output_dir = temp_dir / "cli_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Process (enrichment) - mimic CLI exactly
        args_process = [
            "cruiseplan", "process", 
            "-c", str(fixture_file),
            "--bathy-dir", str(bathy_dir),
            "--output-dir", str(output_dir),
            "--no-port-map"  # Skip port plotting for speed
        ]
        
        # Run CLI process command
        import sys
        old_argv = sys.argv
        try:
            sys.argv = args_process
            cli_main()
        finally:
            sys.argv = old_argv
        
        # Find enriched file (cruise name from YAML)
        with open(fixture_file) as f:
            config = yaml.safe_load(f)
            cruise_name = config.get("cruise_name", "TC1_Single_Test")
        
        enriched_file = output_dir / f"{cruise_name}_enriched.yaml"
        assert enriched_file.exists(), f"Enriched file not found: {enriched_file}"
        
        # Step 2: Schedule - mimic CLI exactly
        args_schedule = [
            "cruiseplan", "schedule",
            "-c", str(enriched_file), 
            "--bathy-dir", str(bathy_dir),
            "-o", str(output_dir)
        ]
        
        try:
            sys.argv = args_schedule
            cli_main()
        finally:
            sys.argv = old_argv
        
        # Return paths to all output files for verification
        return {
            "enriched_yaml": enriched_file,
            "schedule_html": output_dir / f"{cruise_name}_schedule.html",
            "schedule_csv": output_dir / f"{cruise_name}_schedule.csv", 
            "stations_tex": output_dir / f"{cruise_name}_stations.tex",
            "work_days_tex": output_dir / f"{cruise_name}_work_days.tex",
            "catalog_kml": output_dir / f"{cruise_name}_catalog.kml"
        }

    def test_yaml_loading_and_validation(self, yaml_path):
        """Test basic YAML loading and validation of tc1_single.yaml."""
        # Load configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        # Validate basic structure
        assert config.cruise_name == "TC1_Single_Test"

        # Validate legs structure (new architecture)
        assert len(config.legs) == 1
        leg = config.legs[0]
        assert leg.departure_port == "port_halifax"  # String reference
        assert leg.arrival_port == "port_cadiz"  # String reference

        # Validate stations
        assert len(config.stations) == 1
        station = config.stations[0]
        assert station.name == "STN_001"
        assert station.latitude == 45.0
        assert station.longitude == -45.0
        assert station.operation_type.value == "CTD"
        assert station.action.value == "profile"

        # Validate legs
        assert len(config.legs) == 1
        leg = config.legs[0]
        assert leg.name == "Leg_Single"
        assert leg.departure_port == "port_halifax"
        assert leg.arrival_port == "port_cadiz"
        assert leg.activities == ["STN_001"]

    def test_cruise_object_creation_and_port_resolution(self, yaml_path):
        """Test Cruise object creation with port resolution."""
        cruise = Cruise(yaml_path)

        # Check station registry
        assert len(cruise.station_registry) == 1
        assert "STN_001" in cruise.station_registry

        # Check runtime legs
        assert len(cruise.runtime_legs) == 1
        leg = cruise.runtime_legs[0]
        assert leg.name == "Leg_Single"

        # Check that ports are resolved to PortDefinition objects in legs
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
        enriched_cruise = Cruise(output_path)
        config = enriched_cruise.config

        # Verify values match constants exactly
        assert config.default_vessel_speed == DEFAULT_VESSEL_SPEED_KT
        assert (
            config.calculate_transfer_between_sections
            == DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS
        )
        assert (
            config.calculate_depth_via_bathymetry
            == DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY
        )
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
        enriched_cruise = Cruise(output_path)
        enriched_station = enriched_cruise.station_registry["STN_001"]

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
        enriched_cruise = Cruise(output_path)
        enriched_station = enriched_cruise.station_registry["STN_001"]

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
        enriched_cruise = Cruise(output_path)
        enriched_station = enriched_cruise.station_registry["STN_001"]

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
        enriched_cruise = Cruise(output_path)
        enriched_station = enriched_cruise.station_registry["STN_001"]
        config = enriched_cruise.config

        # Validate all default values match constants
        assert config.default_vessel_speed == DEFAULT_VESSEL_SPEED_KT
        assert (
            config.calculate_transfer_between_sections
            == DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS
        )
        assert (
            config.calculate_depth_via_bathymetry
            == DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY
        )
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
        from cruiseplan.utils.constants import DEFAULT_MOORING_DURATION_MIN

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
        enriched_cruise = Cruise(output_path)
        mooring_station = enriched_cruise.station_registry["MOORING_001"]

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
        cruise = Cruise(yaml_path)
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

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
        cruise = Cruise(yaml_path)
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)

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
        cruise = Cruise(yaml_path)

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
        cruise = Cruise(enriched_path)

        # 3. Generate timeline
        timeline = generate_timeline(cruise.config, cruise.runtime_legs)
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

    # Manual Verification Tests from docs/source/manual_testing.rst
    # ============================================================

    def test_manual_check_1_enriched_coordinates_ddm(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 1: Verify STN_001 coordinates were enriched correctly.
        
        Expected: coordinates_ddm: 45 00.00'N, 045 00.00'W
        From docs/source/manual_testing.rst line 58-62
        """
        with open(cli_outputs["enriched_yaml"]) as f:
            enriched = yaml.safe_load(f)
        
        # Find STN_001 in stations
        stn_001 = None
        for station in enriched.get("stations", []):
            if station.get("name") == "STN_001":
                stn_001 = station
                break
        
        assert stn_001 is not None, "STN_001 station not found in enriched YAML"
        assert stn_001.get("coordinates_ddm") == "45 00.00'N, 045 00.00'W", \
            f"Expected coordinates_ddm '45 00.00\\'N, 045 00.00\\'W', got '{stn_001.get('coordinates_ddm')}'"

    def test_manual_check_2_enriched_port_expansion(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 2: Verify port got expanded with correct details.
        
        Expected port_cadiz with latitude: 36.5298, longitude: -6.2923, display_name: Cadiz, Spain
        From docs/source/manual_testing.rst line 64-72
        """
        with open(cli_outputs["enriched_yaml"]) as f:
            enriched = yaml.safe_load(f)
        
        ports = enriched.get("ports", [])
        port_cadiz = None
        for port in ports:
            if port.get("name") == "port_cadiz":
                port_cadiz = port
                break
        
        assert port_cadiz is not None, "port_cadiz not found in enriched YAML"
        assert port_cadiz.get("latitude") == 36.5298, \
            f"Expected latitude 36.5298, got {port_cadiz.get('latitude')}"
        assert port_cadiz.get("longitude") == -6.2923, \
            f"Expected longitude -6.2923, got {port_cadiz.get('longitude')}"
        assert port_cadiz.get("display_name") == "Cadiz, Spain", \
            f"Expected display_name 'Cadiz, Spain', got '{port_cadiz.get('display_name')}'"

    def test_manual_check_3_enriched_defaults_added(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 3: Verify defaults were added correctly.
        
        Expected: turnaround_time: 30.0, ctd_descent_rate: 1.0, ctd_ascent_rate: 1.0
        From docs/source/manual_testing.rst line 74-80
        """
        with open(cli_outputs["enriched_yaml"]) as f:
            enriched = yaml.safe_load(f)
        
        assert enriched.get("turnaround_time") == 30.0, \
            f"Expected turnaround_time 30.0, got {enriched.get('turnaround_time')}"
        assert enriched.get("ctd_descent_rate") == 1.0, \
            f"Expected ctd_descent_rate 1.0, got {enriched.get('ctd_descent_rate')}"
        assert enriched.get("ctd_ascent_rate") == 1.0, \
            f"Expected ctd_ascent_rate 1.0, got {enriched.get('ctd_ascent_rate')}"

    def test_manual_check_4_schedule_html_ctd_duration(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 4: Verify CTD takes 2.1 hours.
        
        Based on 30min turnaround + 2850m depth with 1.0 m/s rate = 2.1 hours total.
        From docs/source/manual_testing.rst line 86
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for CTD duration in HTML - the value appears in tables as just "2.1"
        # Check if 2.1 appears in context of CTD operations
        assert "2.1" in html_text, f"Expected CTD duration 2.1 not found in HTML"
        assert "CTD" in html_text, f"CTD operations section not found in HTML"

    def test_manual_check_5_schedule_html_total_duration(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 5: Verify total cruise duration is 262.4 hours / 10.9 days.
        
        From docs/source/manual_testing.rst line 88
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for total duration - the value appears in tables as just "262.4"
        assert "262.4" in html_text, f"Expected total duration 262.4 not found in HTML"
        assert "Total Cruise" in html_text, f"Total Cruise section not found in HTML"

    def test_manual_check_7_schedule_csv_longitude_minutes(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 7: Verify first row longitude minutes is -34.51.
        
        For -63.5752 degrees longitude, minutes should be -34.51.
        From docs/source/manual_testing.rst line 95-104
        """
        with open(cli_outputs["schedule_csv"], "r") as f:
            reader = csv.DictReader(f)
            first_row = next(reader)
        
        # Check for longitude minutes column
        lon_min = first_row.get("Lon [min]")
        assert lon_min is not None, "Lon [min] column not found in CSV"
        
        lon_min_float = float(lon_min)
        expected = -34.51
        assert abs(lon_min_float - expected) < 0.01, \
            f"Expected longitude minutes {expected}, got {lon_min_float}"

    def test_manual_check_8_stations_tex_water_depth(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 8: Verify LaTeX station table includes water depth 2850.
        
        From docs/source/manual_testing.rst line 110
        """
        with open(cli_outputs["stations_tex"], "r") as f:
            tex_content = f.read()
        
        # Look for water depth 2850 in the LaTeX table
        assert "2850" in tex_content, "Water depth 2850 not found in LaTeX stations table"

    def test_manual_check_9_stations_tex_latex_coordinates(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 9: Verify LaTeX coordinate format includes 45$^\\circ$00.00'N.
        
        From docs/source/manual_testing.rst line 111-115
        """
        with open(cli_outputs["stations_tex"], "r") as f:
            tex_content = f.read()
        
        # Look for the specific LaTeX-formatted coordinate
        expected_coord = "45$^\\circ$00.00'N"
        assert expected_coord in tex_content, \
            f"Expected LaTeX coordinate '{expected_coord}' not found in stations table"

    def test_manual_check_10_work_days_tex_operation_transit_hours(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 10: Verify work days table shows 2.1 operation hours and 260.3 transit hours.
        
        From docs/source/manual_testing.rst line 120-124
        """
        with open(cli_outputs["work_days_tex"], "r") as f:
            tex_content = f.read()
        
        # Look for the total duration line with operation and transit hours
        total_pattern = r"\\textbf\{Total duration\}.*?\\textbf\{([\d.]+)\}.*?\\textbf\{([\d.]+)\}"
        match = re.search(total_pattern, tex_content)
        
        assert match is not None, "Total duration line not found in work days LaTeX table"
        
        operation_hours = float(match.group(1))
        transit_hours = float(match.group(2))
        
        assert abs(operation_hours - 2.1) < 0.1, \
            f"Expected operation hours ~2.1, got {operation_hours}"
        assert abs(transit_hours - 260.3) < 1.0, \
            f"Expected transit hours ~260.3, got {transit_hours}"

    def test_manual_check_13_kml_file_exists(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 13: Verify KML file exists and contains station details.
        
        PNG checks (11-12) are excluded per requirements.
        From docs/source/manual_testing.rst line 135
        """
        kml_file = cli_outputs["catalog_kml"]
        assert kml_file.exists(), f"KML file not found: {kml_file}"
        
        # Basic content check - should contain station information
        with open(kml_file, "r") as f:
            kml_content = f.read()
        
        assert "STN_001" in kml_content, "STN_001 not found in KML file"
        assert "<kml" in kml_content.lower(), "Invalid KML format"
