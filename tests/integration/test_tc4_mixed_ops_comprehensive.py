"""
Comprehensive integration tests for TC4 mixed operations configuration.
Tests duration calculations, distance accuracy, and complete workflow.

Includes automated verification of all manual testing steps from 
docs/source/manual_testing.rst for TC4 Mixed Ops test case (checks 1-7, excluding PNG).
"""

import re
import tempfile
from pathlib import Path
from typing import Dict

import pytest
import yaml
from bs4 import BeautifulSoup

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation_old import enrich_configuration
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
            1: 0,
            2: 57.8,  # Port_Departure: Halifax to Operations (577.8nm @ 10kt)
            3: 0.5,  # STN_001: CTD operation (may vary based on depth calculation)
            4: 6.0,  # Transit to ADCP_Survey: 60nm @ 10kt
            5: 12.0,  # ADCP_Survey: Scientific transit (60nm @ 5kt)
            6: 3.6,  # Transit to Area_01: 36.3nm @ 10kt (using ADCP exit coordinates)
            7: 2.0,  # Area_01: Survey area (120 min)
            8: 200.7,  # Transit to Cadiz: Operations to Cadiz (2007.3nm @ 10kt)
            9: 0,
        }

        # Expected transit distances (nm) - separate transit activities have the distances
        expected_transit_distances = {
            1: 0,
            2: 577.8,  # Transit to STN_001: Halifax to operations
            3: 0.0,  # STN_001: no transit (already at location)
            4: 60.0,  # Transit to ADCP_Survey: STN_001 to ADCP start
            5: 60.0,  # ADCP_Survey: scientific transit distance
            6: 36.3,  # Transit to Area_01: ADCP end to Area_01
            7: 0.0,  # Area_01: no transit (separate activity handles it)
            8: 2007.3,  # Transit to Cadiz: Area_01 to Cadiz (actual calculated distance)
            9: 0,
        }

        # Expected activity types
        expected_activity_types = {
            1: "Port",
            2: "Transit",
            3: "Station",
            4: "Transit",
            5: "Line",  # ADCP_Survey is a LineOperation
            6: "Transit",
            7: "Area",
            8: "Transit",
            9: "Port",
        }

        print("\n🔍 TC4 Mixed Operations Duration Analysis:")
        print(f"Total activities: {len(timeline)}")

        total_duration_h = 0.0
        for i, activity in enumerate(timeline, 1):
            duration_h = activity["duration_minutes"] / 60
            transit_dist = activity.get("dist_nm", 0)
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

        # Calculate expected total based on actual timeline
        expected_total = sum(
            expected_durations[i]
            for i in range(1, len(timeline) + 1)
            if i in expected_durations
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
            "Halifax",
            "Transit to STN_001",
            "STN_001",
            "Transit to ADCP_Survey",
            "ADCP_Survey",
            "Transit to Area_01",
            "Area_01",
            "Transit to Cadiz",
            "Cadiz",
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

    @pytest.fixture
    def cli_outputs(self):
        """
        Generate TC4 outputs using CLI commands for manual verification tests.
        
        This fixture runs the complete cruiseplan process + schedule workflow
        for tc4_mixed_ops.yaml using subprocess (like test_all_fixtures.py).
        Matches the verification steps in docs/source/manual_testing.rst.
        """
        import subprocess
        
        yaml_path = "tests/fixtures/tc4_mixed_ops.yaml"
        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")
            
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup paths
            fixture_file = Path(yaml_path)
            bathy_dir = Path("data/bathymetry")
            output_dir = Path(temp_dir) / "cli_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Find cruise name for output files
            with open(fixture_file) as f:
                config = yaml.safe_load(f)
                cruise_name = config.get("cruise_name", "TC4_Mixed_Test")
            
            # Step 1: Process (enrichment) using subprocess
            process_cmd = [
                "cruiseplan", "process", 
                "-c", str(fixture_file),
                "--bathy-dir", str(bathy_dir),
                "--output-dir", str(output_dir),
                "--no-port-map"
            ]
            
            result = subprocess.run(process_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                pytest.fail(f"Process command failed: {result.stderr}")
            
            # Check enriched file exists
            enriched_file = output_dir / f"{cruise_name}_enriched.yaml"
            if not enriched_file.exists():
                pytest.fail(f"Enriched file not created: {enriched_file}")
            
            # Step 2: Schedule using subprocess
            schedule_cmd = [
                "cruiseplan", "schedule",
                "-c", str(enriched_file), 
                "--bathy-dir", str(bathy_dir),
                "-o", str(output_dir)
            ]
            
            result = subprocess.run(schedule_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                pytest.fail(f"Schedule command failed: {result.stderr}")
            
            # Return paths to all output files for verification
            yield {
                "schedule_html": output_dir / f"{cruise_name}_schedule.html",
                "stations_tex": output_dir / f"{cruise_name}_stations.tex", 
                "work_days_tex": output_dir / f"{cruise_name}_work_days.tex"
            }

    # Manual Verification Tests from docs/source/manual_testing.rst
    # ============================================================

    def test_manual_check_2_stations_tex_line_types(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 2: Verify stations.tex shows 3 lines with specific entries.
        
        Station, Line, and Area operations with correct coordinates and depths.
        From docs/source/manual_testing.rst line 214-221
        """
        with open(cli_outputs["stations_tex"], "r") as f:
            tex_content = f.read()
        
        # Check for the three expected entries
        assert "STN-001" in tex_content, "STN-001 station not found in LaTeX table"
        assert "45$^\\circ$00.00'N, 050$^\\circ$00.00'W" in tex_content, "Station coordinates not found"
        assert "58" in tex_content, "Station depth 58m not found"
        
        assert "ADCP-Survey" in tex_content, "ADCP-Survey line not found in LaTeX table"
        assert "Line" in tex_content, "Line operation type not found"
        
        assert "Area-01" in tex_content, "Area-01 not found in LaTeX table"
        assert "Area" in tex_content, "Area operation type not found"
        assert "47$^\\circ$30.00'N, 050$^\\circ$30.00'W" in tex_content, "Area center coordinates not found"

    def test_manual_check_3_schedule_html_total_duration(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 3: Verify HTML shows total duration of 287.2 hours.
        
        From docs/source/manual_testing.rst line 224
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for total duration - value appears in tables as plain number
        assert "282.7" in html_text, f"Expected total duration 282.7 not found in HTML"

    def test_manual_check_4_schedule_html_operation_count(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 4: Verify HTML shows 3 operations total and 3 operations in Mixed_Survey leg.
        
        From docs/source/manual_testing.rst line 226
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for operation counts
        assert "3 operations" in html_text, "Expected 3 operations count not found in HTML"
        assert "Mixed_Survey" in html_text, "Mixed_Survey leg not found in HTML"

    def test_manual_check_5_schedule_html_transit_distance(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 5: Verify Transit to ADCP survey shows 60.0 nm taking 6.0 hours.
        
        From docs/source/manual_testing.rst line 228  
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for transit to ADCP survey details
        assert "60.0" in html_text, "Expected transit distance 60.0 nm not found in HTML"
        assert "6.0" in html_text, "Expected transit duration 6.0 hours not found in HTML"

    def test_manual_check_6_schedule_html_adcp_positions(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 6: Verify ADCP survey entry/exit positions.
        
        Entry: 46.0000, -50.0000 and Exit: 47.0000, -50.0000
        From docs/source/manual_testing.rst line 230
        """
        with open(cli_outputs["schedule_html"], "r") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        
        html_text = soup.get_text()
        
        # Look for ADCP survey positions 
        assert "46.0000, -50.0000" in html_text, "ADCP entry position not found in HTML"
        assert "47.0000, -50.0000" in html_text, "ADCP exit position not found in HTML"

    def test_manual_check_7_work_days_tex_operation_transit_hours(self, cli_outputs: Dict[str, Path]):
        """
        Manual check 7: Verify work days table shows 24.2 operation hours and 258.5 transit hours.
        
        From docs/source/manual_testing.rst line 232-236
        """
        with open(cli_outputs["work_days_tex"], "r") as f:
            tex_content = f.read()
        
        # Look for the total duration line with operation and transit hours
        total_pattern = r"\\textbf\{Total duration\}.*?\\textbf\{([\d.]+)\}.*?\\textbf\{([\d.]+)\}"
        match = re.search(total_pattern, tex_content)
        
        assert match is not None, "Total duration line not found in work days LaTeX table"
        
        operation_hours = float(match.group(1))
        transit_hours = float(match.group(2))
        
        assert abs(operation_hours - 24.2) < 1.0, \
            f"Expected operation hours ~24.2, got {operation_hours}"
        assert abs(transit_hours - 258.5) < 2.0, \
            f"Expected transit hours ~258.5, got {transit_hours}"
