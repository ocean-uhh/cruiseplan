"""
Test suite for cruiseplan.cli.map command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.map import main


class TestMapThinCLI:
    """Test suite for thin CLI map functionality."""

    def test_minimal_map_command(self):
        """Test minimal map command with required arguments."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            output=None,
            format="all",
            bathy_source="etopo2022",
            bathy_dir="data",
            bathy_stride=5,
            figsize=None,
            show_plot=False,
            no_ports=False,
            verbose=False,
        )

        with patch("cruiseplan.map") as mock_map:
            # Mock successful map response
            mock_map.return_value = cruiseplan.MapResult(
                map_files=[Path("data/test_map.png"), Path("data/test_catalog.kml")],
                format="all",
                summary={
                    "config_file": "test.yaml",
                    "format": "all",
                    "files_generated": 2,
                    "output_dir": "data",
                },
            )

            main(args)

            # Verify API was called with correct arguments
            mock_map.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",
                output=None,
                format="all",
                bathy_source="etopo2022",
                bathy_dir="data",
                bathy_stride=5,
                figsize=None,
                show_plot=False,
                no_ports=False,
                verbose=False,
            )

    def test_map_with_custom_options(self):
        """Test map command with custom options."""
        args = argparse.Namespace(
            config_file=Path("custom.yaml"),
            output_dir="/custom/output",
            output="custom_map",
            format="png",
            bathy_source="gebco2025",
            bathy_dir="/custom/bathy",
            bathy_stride=10,
            figsize=[12.0, 8.0],
            show_plot=True,
            no_ports=True,
            verbose=True,
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.return_value = cruiseplan.MapResult(
                map_files=[Path("/custom/output/custom_map_map.png")],
                format="png",
                summary={
                    "config_file": "custom.yaml",
                    "format": "png",
                    "files_generated": 1,
                    "output_dir": "/custom/output",
                },
            )

            main(args)

            mock_map.assert_called_once_with(
                config_file=Path("custom.yaml"),
                output_dir="/custom/output",
                output="custom_map",
                format="png",
                bathy_source="gebco2025",
                bathy_dir="/custom/bathy",
                bathy_stride=10,
                figsize=[12.0, 8.0],
                show_plot=True,
                no_ports=True,
                verbose=True,
            )

    def test_map_failure(self):
        """Test map command when generation fails."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.return_value = cruiseplan.MapResult(
                map_files=[],
                format="all",
                summary={
                    "config_file": "invalid.yaml",
                    "format": "all",
                    "files_generated": 0,
                    "error": "Configuration invalid",
                },
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.side_effect = cruiseplan.ValidationError(
                "Invalid YAML configuration: syntax error"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_file_error_handling(self):
        """Test handling of FileError from API."""
        args = argparse.Namespace(
            config_file=Path("missing.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.side_effect = cruiseplan.FileError("Configuration file not found")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_bathymetry_error_handling(self):
        """Test handling of BathymetryError from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            bathy_source="invalid_source",
            verbose=False,
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.side_effect = cruiseplan.BathymetryError(
                "Bathymetry data not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_file_not_found_handling(self):
        """Test handling of FileNotFoundError from API."""
        args = argparse.Namespace(
            config_file=Path("missing.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.side_effect = FileNotFoundError("Configuration file not found")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_runtime_error_handling(self):
        """Test handling of RuntimeError from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.side_effect = RuntimeError("Map generation failed unexpectedly")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), output_dir="data", verbose=False
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_map_unexpected_error_with_verbose(self):
        """Test handling of unexpected errors with verbose traceback."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), output_dir="data", verbose=True
        )

        with (
            patch("cruiseplan.map") as mock_map,
            patch("traceback.print_exc") as mock_traceback,
        ):
            # Use an exception type that will fall through to general handler
            mock_map.side_effect = ValueError("Unexpected error")

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
            # Missing: output_dir, format, bathy_source, etc.
        )

        with patch("cruiseplan.map") as mock_map:
            mock_map.return_value = cruiseplan.MapResult(
                map_files=[Path("data/test_map.png")],
                format="all",
                summary={"config_file": "test.yaml", "files_generated": 1},
            )

            main(args)

            # Should use defaults for missing arguments
            mock_map.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",  # default
                output=None,  # default
                format="all",  # default
                bathy_source="etopo2022",  # default
                bathy_dir="data",  # default
                bathy_stride=5,  # default
                figsize=None,  # default
                show_plot=False,  # default
                no_ports=False,  # default
                verbose=False,  # default
            )


class TestMapResultType:
    """Test the MapResult type for completeness."""

    def test_map_result_success(self):
        """Test MapResult with successful map generation."""
        map_files = [Path("map.png"), Path("catalog.kml")]
        result = cruiseplan.MapResult(
            map_files=map_files,
            format="all",
            summary={"files_generated": 2, "config_file": "test.yaml"},
        )

        assert result.map_files == map_files
        assert bool(result) is True
        assert len(result.map_files) == 2
        assert "✅ Map generation (all) complete" in str(result)
        assert "(2 files)" in str(result)

    def test_map_result_failure(self):
        """Test MapResult with failed map generation."""
        result = cruiseplan.MapResult(
            map_files=[],
            format="all",
            summary={"files_generated": 0, "error": "Generation failed"},
        )

        assert result.map_files == []
        assert bool(result) is False
        assert len(result.map_files) == 0
        assert "❌ Map generation (all) failed" in str(result)
