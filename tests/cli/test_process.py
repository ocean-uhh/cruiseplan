"""
Test suite for cruiseplan.cli.process command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.process import main
from cruiseplan.schema import POINTS_FIELD


class TestProcessThinCLI:
    """Test suite for thin CLI process functionality."""

    def test_minimal_process_command(self):
        """Test minimal process command with required arguments."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            output=None,
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            run_validation=True,
            run_map_generation=True,
            depth_check=True,
            tolerance=10.0,
            format="all",
            bathy_stride=10,
            figsize=None,
            no_port_map=False,
            verbose=False,
        )

        with patch("cruiseplan.process") as mock_process:
            # Mock successful process response
            mock_process.return_value = cruiseplan.ProcessResult(
                config={
                    "cruise_name": "test_cruise",
                    POINTS_FIELD: [{"name": "station1"}],
                },
                files_created=[
                    Path("data/test_enriched.yaml"),
                    Path("data/test_schedule.html"),
                    Path("data/test_map.png"),
                ],
                summary={
                    "config_file": "test.yaml",
                    "files_generated": 3,
                    "enrichment_run": True,
                    "validation_run": True,
                    "map_generation_run": True,
                },
            )

            main(args)

            # Verify API was called with correct arguments
            mock_process.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",
                output=None,
                bathy_source="etopo2022",
                bathy_dir="data/bathymetry",
                add_depths=True,
                add_coords=True,
                expand_sections=True,
                run_validation=True,
                run_map_generation=True,
                depth_check=True,
                tolerance=10.0,
                format="all",
                bathy_stride=10,
                figsize=None,
                no_port_map=False,
                verbose=False,
            )

    def test_process_with_custom_options(self):
        """Test process command with custom options."""
        args = argparse.Namespace(
            config_file=Path("custom.yaml"),
            output_dir="/custom/output",
            output="custom_cruise",
            bathy_source="gebco2025",
            bathy_dir="/custom/bathy",
            add_depths=False,
            add_coords=False,
            expand_sections=False,
            run_validation=False,
            run_map_generation=False,
            depth_check=False,
            tolerance=5.0,
            format="html",
            bathy_stride=20,
            figsize=[12, 8],
            no_port_map=True,
            verbose=True,
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.return_value = cruiseplan.ProcessResult(
                config={"cruise_name": "custom_cruise"},
                files_created=[Path("/custom/output/custom_cruise_enriched.yaml")],
                summary={
                    "config_file": "custom.yaml",
                    "files_generated": 1,
                    "enrichment_run": False,
                    "validation_run": False,
                    "map_generation_run": False,
                },
            )

            main(args)

            mock_process.assert_called_once_with(
                config_file=Path("custom.yaml"),
                output_dir="/custom/output",
                output="custom_cruise",
                bathy_source="gebco2025",
                bathy_dir="/custom/bathy",
                add_depths=False,
                add_coords=False,
                expand_sections=False,
                run_validation=False,
                run_map_generation=False,
                depth_check=False,
                tolerance=5.0,
                format="html",
                bathy_stride=20,
                figsize=[12, 8],
                no_port_map=True,
                verbose=True,
            )

    def test_process_failure(self):
        """Test process command when processing fails."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.return_value = cruiseplan.ProcessResult(
                config=None,
                files_created=[],
                summary={"config_file": "invalid.yaml", "files_generated": 0},
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_process_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.side_effect = cruiseplan.ValidationError(
                "Invalid YAML configuration: syntax error"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_process_file_error_handling(self):
        """Test handling of FileError from API."""
        args = argparse.Namespace(
            config_file=Path("missing.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.side_effect = cruiseplan.FileError(
                "Configuration file not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_process_bathymetry_error_handling(self):
        """Test handling of BathymetryError from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            bathy_source="invalid_source",
            verbose=False,
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.side_effect = cruiseplan.BathymetryError(
                "Bathymetry data not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_process_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_process_runtime_error_handling(self):
        """Test handling of RuntimeError from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.side_effect = RuntimeError("Processing failed unexpectedly")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_process_unexpected_error_with_verbose(self):
        """Test handling of unexpected errors with verbose traceback."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), output_dir="data", verbose=True
        )

        with (
            patch("cruiseplan.process") as mock_process,
            patch("traceback.print_exc") as mock_traceback,
        ):
            # Use an exception type that will fall through to general handler
            mock_process.side_effect = ValueError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should print traceback when verbose=True
            mock_traceback.assert_called_once()
            assert exc_info.value.code == 1

    def test_default_argument_handling(self):
        """Test that missing arguments get proper defaults."""
        # Minimal args - missing optional attributes
        args = argparse.Namespace(
            config_file=Path("test.yaml")
            # Missing: output_dir, bathy_source, add_depths, etc.
        )

        with patch("cruiseplan.process") as mock_process:
            mock_process.return_value = cruiseplan.ProcessResult(
                config={"cruise_name": "test"},
                files_created=[Path("data/test_enriched.yaml")],
                summary={"config_file": "test.yaml", "files_generated": 1},
            )

            main(args)

            # Should use defaults for missing arguments
            mock_process.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",  # default
                output=None,  # default
                bathy_source="etopo2022",  # default
                bathy_dir="data/bathymetry",  # default
                add_depths=True,  # default
                add_coords=True,  # default
                expand_sections=True,  # default
                run_validation=True,  # default
                run_map_generation=True,  # default
                depth_check=True,  # default
                tolerance=10.0,  # default
                format="all",  # default
                bathy_stride=10,  # default
                figsize=None,  # default
                no_port_map=False,  # default
                verbose=False,  # default
            )


class TestProcessResultType:
    """Test the ProcessResult type for completeness."""

    def test_process_result_success(self):
        """Test ProcessResult with successful processing."""
        config = {"cruise_name": "test_cruise", POINTS_FIELD: [{"name": "station1"}]}
        files = [Path("enriched.yaml"), Path("schedule.html"), Path("map.png")]
        summary = {"files_generated": 3, "enrichment_run": True}

        result = cruiseplan.ProcessResult(
            config=config, files_created=files, summary=summary
        )

        assert result.config == config
        assert bool(result) is True
        assert len(result.files_created) == 3
        assert "✅ Processing complete" in str(result)
        assert "(3 files)" in str(result)

    def test_process_result_failure(self):
        """Test ProcessResult with failed processing."""
        result = cruiseplan.ProcessResult(
            config=None, files_created=[], summary={"files_generated": 0}
        )

        assert result.config is None
        assert bool(result) is False
        assert len(result.files_created) == 0
        assert "❌ Processing failed" in str(result)
