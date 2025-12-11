"""
Integration tests for LaTeX generator with scheduler timeline output.
"""

from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.output.latex_generator import generate_latex_tables
from cruiseplan.utils.config import ConfigLoader


class TestLatexGeneratorIntegration:
    """Integration tests for LaTeX generator with scheduler output."""

    def test_latex_generation_simple_cruise(self):
        """Test LaTeX generation with simple 2-station cruise."""
        yaml_path = "tests/fixtures/cruise_simple.yaml"

        # Load configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        # Generate timeline
        timeline = generate_timeline(config)
        assert len(timeline) > 0, "Timeline should not be empty"
        assert (
            len(timeline) == 5
        ), "Expected 5 activities for simple cruise (2 x CTD, 3 x Transit)"

        # Generate LaTeX tables
        output_dir = Path("tests_output")
        files_created = generate_latex_tables(config, timeline, output_dir)

        # Verify files were created
        assert len(files_created) == 2, "Should create 2 LaTeX files"

        stations_file = output_dir / f"{config.cruise_name}_stations.tex"
        work_days_file = output_dir / f"{config.cruise_name}_work_days.tex"

        assert stations_file in files_created
        assert work_days_file in files_created
        assert stations_file.exists()
        assert work_days_file.exists()

        # Check file content is not empty
        assert stations_file.stat().st_size > 100, "Stations file should have content"
        assert work_days_file.stat().st_size > 100, "Work days file should have content"

        # Verify stations table contains expected elements
        stations_content = stations_file.read_text()
        assert "STN-001" in stations_content  # Replace underscore with dash
        assert "STN-002" in stations_content  # Replace underscore with dash
        assert "Working area, stations and profiles" in stations_content

        # Verify work days table contains expected elements and values
        work_days_content = work_days_file.read_text()
        assert "Transit to area" in work_days_content
        assert "CTD/Station Operations" in work_days_content
        assert "Transit within area" in work_days_content
        assert "Transit from area" in work_days_content

        # Check specific numeric values match expected calculations
        assert "& Transit to area &  & 52.2 \\\\" in work_days_content
        assert "& CTD/Station Operations & 2.1 &  \\\\" in work_days_content
        assert "Transit within area & 6.0 " in work_days_content
        assert "& Transit from area &  & 97.3 \\\\" in work_days_content

    def test_latex_generation_mixed_operations(self):
        """Test LaTeX generation with mixed operations (stations, moorings, transits)."""
        yaml_path = "tests/fixtures/cruise_mixed_ops.yaml"

        # Load configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        # Generate timeline
        timeline = generate_timeline(config)
        assert len(timeline) > 0, "Timeline should not be empty"

        # Should have mix of operations
        activities = [activity["activity"] for activity in timeline]
        assert "Transit" in activities, "Should include transit operations"
        assert "Station" in activities, "Should include station operations"
        assert "Mooring" in activities, "Should include mooring operations"

        # Generate LaTeX tables
        output_dir = Path("tests_output")
        files_created = generate_latex_tables(config, timeline, output_dir)

        # Verify files were created
        assert len(files_created) == 2, "Should create 2 LaTeX files"

        work_days_file = output_dir / f"{config.cruise_name}_work_days.tex"
        work_days_content = work_days_file.read_text()

        # Check that mixed operations are represented
        assert "CTD/Station Operations" in work_days_content
        assert "Mooring Operations" in work_days_content
        assert "ADCP Survey" in work_days_content
        assert "Transit within area" in work_days_content

    @pytest.mark.parametrize(
        "fixture_name", ["cruise_simple.yaml", "cruise_mixed_ops.yaml"]
    )
    def test_all_fixtures_generate_valid_latex(self, fixture_name):
        """Test that all fixtures generate valid, non-empty LaTeX files."""
        yaml_path = f"tests/fixtures/{fixture_name}"

        if not Path(yaml_path).exists():
            pytest.skip(f"Fixture {yaml_path} not found")

        # Load and generate
        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        output_dir = Path("tests_output/latex_reports")
        files_created = generate_latex_tables(config, timeline, output_dir)

        # Basic validations for all fixtures
        assert len(files_created) > 0, f"No files created for {fixture_name}"

        for file_path in files_created:
            assert file_path.exists(), f"File {file_path} was not created"
            assert file_path.stat().st_size > 50, f"File {file_path} is too small"

            # Check basic LaTeX structure
            content = file_path.read_text()
            assert "\\begin{table}" in content, f"Missing table start in {file_path}"
            assert "\\end{table}" in content, f"Missing table end in {file_path}"
            assert "\\caption{" in content, f"Missing caption in {file_path}"
