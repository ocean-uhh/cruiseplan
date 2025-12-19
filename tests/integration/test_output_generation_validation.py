"""
Integration tests for output generation validation.

These tests ensure that all output formats (LaTeX, PNG, HTML, CSV, NetCDF)
generate successfully and produce the expected files. This catches issues
like the LaTeX 'first_station' error that could otherwise go unnoticed.
"""

import argparse
import tempfile
from pathlib import Path

import pytest

from cruiseplan.cli.schedule import main as schedule_main


class TestOutputGenerationValidation:
    """Test that all output formats generate without errors."""

    def create_schedule_args(self, config_path, output_dir, format_type):
        """Create argparse.Namespace object for schedule command."""
        args = argparse.Namespace()
        args.config_file = Path(config_path)
        args.output_dir = Path(output_dir)
        args.format = format_type
        args.leg = None
        args.derive_netcdf = False
        args.verbose = False
        args.quiet = True  # Reduce output during testing
        return args

    @pytest.fixture
    def sample_configs(self):
        """Provide various test configurations to validate against."""
        # Use absolute paths from project root to data directory
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        return [
            str(project_root / "data" / "tc1_single_enriched.yaml"),
            str(project_root / "data" / "tc2_two_legs_enriched.yaml"),
            str(project_root / "data" / "tc3_clusters_enriched.yaml"),
        ]

    def test_latex_output_generation(self, sample_configs):
        """Test that LaTeX tables generate successfully for all configurations."""
        for config_path in sample_configs:
            if not Path(config_path).exists():
                pytest.skip(f"Test fixture {config_path} not found")

            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir)

                # Test LaTeX generation
                try:
                    args = self.create_schedule_args(
                        config_path, str(output_path), "latex"
                    )
                    schedule_main(args)
                except SystemExit as e:
                    if e.code != 0:
                        pytest.fail(f"LaTeX generation failed for {config_path}")

                # Verify LaTeX files were created
                latex_files = list(output_path.glob("*.tex"))
                assert (
                    len(latex_files) > 0
                ), f"No LaTeX files generated for {config_path}"

                # Should have both stations and work_days tables
                stations_files = list(output_path.glob("*_stations.tex"))
                work_days_files = list(output_path.glob("*_work_days.tex"))
                assert (
                    len(stations_files) > 0
                ), f"No stations table generated for {config_path}"
                assert (
                    len(work_days_files) > 0
                ), f"No work days table generated for {config_path}"

                # Verify LaTeX file has content
                latex_file = latex_files[0]
                content = latex_file.read_text()
                assert (
                    len(content) > 100
                ), f"LaTeX file suspiciously small for {config_path}"
                assert (
                    "\\begin{tabular}" in content
                ), f"LaTeX file missing table content for {config_path}"

    def test_png_output_generation(self, sample_configs):
        """Test that PNG maps generate successfully for all configurations."""
        for config_path in sample_configs:
            if not Path(config_path).exists():
                pytest.skip(f"Test fixture {config_path} not found")

            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir)

                # Test PNG generation
                try:
                    args = self.create_schedule_args(
                        config_path, str(output_path), "png"
                    )
                    schedule_main(args)
                except SystemExit as e:
                    if e.code != 0:
                        pytest.fail(f"PNG generation failed for {config_path}")

                # Verify PNG file was created
                png_files = list(output_path.glob("*.png"))
                assert len(png_files) > 0, f"No PNG map generated for {config_path}"

                # Verify PNG file has reasonable size (not empty)
                png_file = png_files[0]
                file_size = png_file.stat().st_size
                assert (
                    file_size > 1000
                ), f"PNG file suspiciously small ({file_size} bytes) for {config_path}"

    def test_all_formats_generation(self):
        """Test that all output formats generate successfully together."""
        # Use absolute path from project root to data directory
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        config_path = str(project_root / "data" / "tc1_single_enriched.yaml")
        if not Path(config_path).exists():
            pytest.skip(f"Test fixture {config_path} not found")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)

            # Test all formats at once
            try:
                args = self.create_schedule_args(
                    config_path, str(output_path), "html,csv,latex,netcdf,png"
                )
                schedule_main(args)
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"Multi-format generation failed for {config_path}")

            # Verify all expected files were created
            expected_patterns = [
                "*_schedule.html",  # HTML output
                "*_schedule.csv",  # CSV output
                "*_stations.tex",  # LaTeX stations table
                "*_work_days.tex",  # LaTeX work days table
                "*_schedule.nc",  # NetCDF output
                "*.png",  # PNG map
            ]

            for pattern in expected_patterns:
                files = list(output_path.glob(pattern))
                assert (
                    len(files) > 0
                ), f"No files matching pattern '{pattern}' found in {list(output_path.iterdir())}"

    def test_output_failure_detection(self):
        """Test that output generation failures are properly detected."""
        # Test with a malformed config that should cause generation errors
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
cruise_name: "Broken Test"
# Missing required fields to trigger validation errors
"""
            )
            broken_config = f.name

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                output_path = Path(temp_dir)

                # This should fail and exit with non-zero code
                with pytest.raises(SystemExit) as exc_info:
                    args = self.create_schedule_args(
                        broken_config, str(output_path), "latex"
                    )
                    schedule_main(args)

                # Verify it failed (non-zero exit code)
                assert (
                    exc_info.value.code != 0
                ), "Expected generation to fail with broken config"

        finally:
            Path(broken_config).unlink()  # Clean up temp file


class TestSpecificOutputFormats:
    """Test specific requirements for individual output formats."""

    def create_schedule_args(self, config_path, output_dir, format_type):
        """Create argparse.Namespace object for schedule command."""
        args = argparse.Namespace()
        args.config_file = Path(config_path)
        args.output_dir = Path(output_dir)
        args.format = format_type
        args.leg = None
        args.derive_netcdf = False
        args.verbose = False
        args.quiet = True  # Reduce output during testing
        return args

    def test_latex_table_structure(self):
        """Test that LaTeX output has proper table structure."""
        # Use absolute path from project root to data directory
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        config_path = str(project_root / "data" / "tc1_single_enriched.yaml")
        if not Path(config_path).exists():
            pytest.skip(f"Test fixture {config_path} not found")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)

            try:
                args = self.create_schedule_args(config_path, str(output_path), "latex")
                schedule_main(args)
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"LaTeX generation failed for {config_path}")

            latex_files = list(output_path.glob("*.tex"))
            assert len(latex_files) > 0

            content = latex_files[0].read_text()

            # Check for essential LaTeX table elements
            assert "\\begin{tabular}" in content, "Missing table environment"
            assert "\\end{tabular}" in content, "Missing table environment end"
            # Check for table formatting (booktabs package uses these instead of \hline)
            assert (
                "\\hline" in content or "\\toprule" in content or "\\midrule" in content
            ), "Missing table formatting"
            assert (
                "Activity" in content or "Station" in content or "Operation" in content
            ), "Missing table headers"

    def test_png_map_properties(self):
        """Test that PNG maps have proper dimensions and content."""
        # Use absolute path from project root to data directory
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        config_path = str(project_root / "data" / "tc1_single_enriched.yaml")
        if not Path(config_path).exists():
            pytest.skip(f"Test fixture {config_path} not found")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)

            try:
                args = self.create_schedule_args(config_path, str(output_path), "png")
                schedule_main(args)
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"PNG generation failed for {config_path}")

            png_files = list(output_path.glob("*.png"))
            assert len(png_files) > 0

            # Basic file size check (should be substantial for a map)
            png_file = png_files[0]
            file_size = png_file.stat().st_size
            assert (
                file_size > 10000
            ), f"PNG map seems too small ({file_size} bytes)"  # Maps should be > 10KB

            # Check filename contains expected elements
            filename = png_file.name
            assert (
                "_map" in filename.lower() or "_schedule" in filename.lower()
            ), "PNG filename should indicate map content"
