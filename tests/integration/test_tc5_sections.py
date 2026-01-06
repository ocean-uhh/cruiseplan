"""
Integration tests for TC5 sections configuration.

Includes automated verification of manual testing steps from 
docs/source/manual_testing.rst for TC5 Sections test case (checks 1-3).
"""

import re
import tempfile
from pathlib import Path
from typing import Dict

import pytest
import yaml
from bs4 import BeautifulSoup

from cruiseplan.cli.main import main as cli_main


class TestTC5SectionsIntegration:
    """Integration tests for TC5 sections configuration."""

    @pytest.fixture
    def cli_outputs(self):
        """
        Generate TC5 outputs using CLI commands for manual verification tests.
        
        This fixture runs the complete cruiseplan process + schedule workflow
        for tc5_sections.yaml and returns paths to all output files.
        Matches the verification steps in docs/source/manual_testing.rst.
        """
        yaml_path = "tests/fixtures/tc5_sections.yaml"
        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")
            
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup paths
            fixture_file = Path(yaml_path)
            bathy_dir = Path("data/bathymetry")
            output_dir = Path(temp_dir) / "cli_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Process (enrichment) - sections are expanded automatically
            args_process = [
                "cruiseplan", "process", 
                "-c", str(fixture_file),
                "--bathy-dir", str(bathy_dir),
                "--output-dir", str(output_dir),
                "--no-port-map"
            ]
            
            import sys
            old_argv = sys.argv
            try:
                sys.argv = args_process
                cli_main()
            finally:
                sys.argv = old_argv
            
            # Find enriched file
            with open(fixture_file) as f:
                config = yaml.safe_load(f)
                cruise_name = config.get("cruise_name", "TC5_Sections_Test")
            
            enriched_file = output_dir / f"{cruise_name}_enriched.yaml"
            assert enriched_file.exists(), f"Enriched file not found: {enriched_file}"
            
            # Step 2: Schedule
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
            yield {
                "enriched_yaml": enriched_file,
                "schedule_html": output_dir / f"{cruise_name}_schedule.html"
            }

    # Manual Verification Tests from docs/source/manual_testing.rst
    # ============================================================

    def test_manual_check_1_enriched_yaml_individual_stations(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 1: Verify enriched.yaml contains individual stations instead of sections.
        
        Should have expanded stations like SEC_001_Stn001 with specific format.
        From docs/source/manual_testing.rst line 249-264
        """
        with open(cli_outputs["enriched_yaml"]) as f:
            enriched = yaml.safe_load(f)
        
        # Look for expanded station name pattern
        stations = enriched.get("stations", [])
        expanded_stations = [s for s in stations if "SEC_001_Stn" in s.get("name", "")]
        
        assert len(expanded_stations) > 0, "No expanded section stations found (SEC_001_Stn***)"
        
        # Check first expanded station has expected format
        first_station = expanded_stations[0]
        expected_name = "SEC_001_Stn001"
        
        assert first_station.get("name") == expected_name, \
            f"Expected first station name {expected_name}, got {first_station.get('name')}"
        
        # Check for expected fields from the documentation
        assert first_station.get("coordinates_ddm") == "45 00.00'N, 050 00.00'W", \
            f"Expected coordinates_ddm, got {first_station.get('coordinates_ddm')}"
        assert first_station.get("water_depth") == 58.0, \
            f"Expected water_depth 58.0, got {first_station.get('water_depth')}"
        assert first_station.get("operation_type") == "CTD", \
            f"Expected operation_type CTD, got {first_station.get('operation_type')}"
        assert first_station.get("action") == "profile", \
            f"Expected action profile, got {first_station.get('action')}"
        assert first_station.get("duration") == 120.0, \
            f"Expected duration 120.0, got {first_station.get('duration')}"
        
        # Check comment contains section reference
        comment = first_station.get("comment", "")
        assert "Station 1/14 on SEC_001 section" in comment, \
            f"Expected comment about section, got '{comment}'"

    def test_manual_check_3_schedule_html_station_spacing(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 3: Verify HTML shows station spacing of 11.2 nm.
        
        From docs/source/manual_testing.rst line 267
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for station spacing - should appear somewhere in the HTML
        assert "11.2" in html_text, f"Expected station spacing 11.2 nm not found in HTML"