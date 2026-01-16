"""
Test suite for cruiseplan.cli.bathymetry command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.bathymetry import main


class TestBathymetryThinCLI:
    """Test suite for thin CLI bathymetry functionality."""

    def test_minimal_bathymetry_command(self):
        """Test minimal bathymetry command with default arguments."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            # Mock successful bathymetry response
            mock_bathymetry.return_value = cruiseplan.BathymetryResult(
                data_file=Path("data/bathymetry/etopo2022.nc"),
                source="etopo2022",
                summary={
                    "source": "etopo2022",
                    "output_dir": "data/bathymetry",
                    "file_size_mb": 850.5,
                    "citation_shown": False,
                },
            )

            main(args)

            # Verify API was called with correct arguments
            mock_bathymetry.assert_called_once_with(
                bathy_source="etopo2022", output_dir=None, citation=False
            )

    def test_bathymetry_with_custom_options(self):
        """Test bathymetry command with custom options."""
        args = argparse.Namespace(
            bathy_source="gebco2025",
            output_dir=Path("/custom/bathy"),
            citation=True,
            verbose=True,
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.return_value = cruiseplan.BathymetryResult(
                data_file=Path("/custom/bathy/gebco2025.nc"),
                source="gebco2025",
                summary={
                    "source": "gebco2025",
                    "output_dir": "/custom/bathy",
                    "file_size_mb": 1200.0,
                    "citation_shown": True,
                },
            )

            main(args)

            mock_bathymetry.assert_called_once_with(
                bathy_source="gebco2025",
                output_dir=str(Path("/custom/bathy")),
                citation=True,
            )

    def test_bathymetry_failure(self):
        """Test bathymetry command when download fails."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.return_value = cruiseplan.BathymetryResult(
                data_file=None,
                source="etopo2022",
                summary={
                    "source": "etopo2022",
                    "output_dir": "data/bathymetry",
                    "file_size_mb": None,
                    "error": "Download failed",
                },
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            bathy_source="invalid_source",
            output_dir=None,
            citation=False,
            verbose=False,
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.side_effect = cruiseplan.ValidationError(
                "Invalid bathymetry source"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_file_error_handling(self):
        """Test handling of FileError from API."""
        args = argparse.Namespace(
            bathy_source="etopo2022",
            output_dir="/invalid/path",
            citation=False,
            verbose=False,
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.side_effect = cruiseplan.FileError(
                "Cannot create output directory"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_bathymetry_error_handling(self):
        """Test handling of BathymetryError from API."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.side_effect = cruiseplan.BathymetryError(
                "Bathymetry download server unavailable"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_file_not_found_handling(self):
        """Test handling of FileNotFoundError from API."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.side_effect = FileNotFoundError("Bathymetry data not found")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_runtime_error_handling(self):
        """Test handling of RuntimeError from API."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.side_effect = RuntimeError("Download failed unexpectedly")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_bathymetry_unexpected_error_with_verbose(self):
        """Test handling of unexpected errors with verbose traceback."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=False, verbose=True
        )

        with (
            patch("cruiseplan.bathymetry") as mock_bathymetry,
            patch("traceback.print_exc") as mock_traceback,
        ):
            # Use an exception type that will fall through to general handler
            mock_bathymetry.side_effect = ValueError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should print traceback when verbose=True
            mock_traceback.assert_called_once()
            assert exc_info.value.code == 1

    def test_default_argument_handling(self):
        """Test that missing arguments get proper defaults."""
        # Minimal args - missing optional attributes
        args = argparse.Namespace(
            # Missing: bathy_source, output_dir, citation, verbose
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.return_value = cruiseplan.BathymetryResult(
                data_file=Path("data/bathymetry/etopo2022.nc"),
                source="etopo2022",
                summary={"source": "etopo2022", "file_size_mb": 850.5},
            )

            main(args)

            # Should use defaults for missing arguments
            mock_bathymetry.assert_called_once_with(
                bathy_source="etopo2022",  # default
                output_dir=None,  # default
                citation=False,  # default
            )

    def test_bathymetry_with_citation(self):
        """Test bathymetry command with citation display."""
        args = argparse.Namespace(
            bathy_source="etopo2022", output_dir=None, citation=True, verbose=False
        )

        with patch("cruiseplan.bathymetry") as mock_bathymetry:
            mock_bathymetry.return_value = cruiseplan.BathymetryResult(
                data_file=Path("data/bathymetry/etopo2022.nc"),
                source="etopo2022",
                summary={
                    "source": "etopo2022",
                    "output_dir": "data/bathymetry",
                    "file_size_mb": 850.5,
                    "citation_shown": True,
                },
            )

            main(args)

            mock_bathymetry.assert_called_once_with(
                bathy_source="etopo2022", output_dir=None, citation=True
            )


class TestBathymetryResultType:
    """Test the BathymetryResult type for completeness."""

    def test_bathymetry_result_success(self):
        """Test BathymetryResult with successful download."""
        data_file = Path("etopo2022.nc")

        # Mock the file existence check
        with patch("pathlib.Path.exists", return_value=True):
            result = cruiseplan.BathymetryResult(
                data_file=data_file,
                source="etopo2022",
                summary={"file_size_mb": 850.5, "source": "etopo2022"},
            )

            assert result.data_file == data_file
            assert bool(result) is True
            assert result.source == "etopo2022"
            assert "✅ Bathymetry download (etopo2022) complete" in str(result)
            assert "(1 files)" in str(result)

    def test_bathymetry_result_failure(self):
        """Test BathymetryResult with failed download."""
        result = cruiseplan.BathymetryResult(
            data_file=None,
            source="etopo2022",
            summary={"file_size_mb": None, "error": "Download failed"},
        )

        assert result.data_file is None
        assert bool(result) is False
        assert "❌ Bathymetry download (etopo2022) failed" in str(result)
