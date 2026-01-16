"""
Test suite for cruiseplan.cli.schedule command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.schedule import main


class TestScheduleThinCLI:
    """Test suite for thin CLI schedule functionality."""

    def test_minimal_schedule_command(self):
        """Test minimal schedule command with required arguments."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            format="all",
            leg=None,
            derive_netcdf=False,
            verbose=False,
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            # Mock successful schedule response
            mock_schedule.return_value = cruiseplan.ScheduleResult(
                timeline=[
                    {"activity": "Transit", "duration_minutes": 120},
                    {"activity": "Station CTD_001", "duration_minutes": 60},
                ],
                files_created=[
                    Path("data/test_schedule.html"),
                    Path("data/test_schedule.csv"),
                ],
                summary={
                    "activities": 2,
                    "files_generated": 2,
                    "formats": ["html", "csv"],
                    "leg": None,
                },
            )

            main(args)

            # Verify API was called with correct arguments
            mock_schedule.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",
                output=None,
                format="all",
                leg=None,
                derive_netcdf=False,
                bathy_source="etopo2022",
                bathy_dir="data/bathymetry",
                bathy_stride=10,
                figsize=None,
                verbose=False,
            )

    def test_schedule_with_custom_options(self):
        """Test schedule command with custom options."""
        args = argparse.Namespace(
            config_file=Path("cruise.yaml"),
            output_dir="/custom/output",
            output="my_schedule",
            format="netcdf",  # Use NetCDF format to allow derive_netcdf=True
            leg="leg1",
            derive_netcdf=True,
            bathy_source="gebco2025",
            bathy_dir="/custom/bathy",
            verbose=True,
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.return_value = cruiseplan.ScheduleResult(
                timeline=[{"activity": "Custom", "duration_minutes": 90}],
                files_created=[Path("/custom/output/my_schedule.html")],
                summary={
                    "activities": 1,
                    "files_generated": 1,
                    "formats": ["html"],
                    "leg": "leg1",
                },
            )

            main(args)

            mock_schedule.assert_called_once_with(
                config_file=Path("cruise.yaml"),
                output_dir="/custom/output",
                output="my_schedule",
                format="netcdf",
                leg="leg1",
                derive_netcdf=True,
                bathy_source="gebco2025",
                bathy_dir="/custom/bathy",
                bathy_stride=10,
                figsize=None,
                verbose=True,
            )

    def test_schedule_derive_netcdf_compatibility_warning(self):
        """Test --derive-netcdf flag compatibility warning for non-NetCDF formats."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            format="html",  # Non-NetCDF format
            derive_netcdf=True,  # Should trigger warning
            verbose=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_schedule,
            patch("builtins.print") as mock_print,
        ):
            mock_schedule.return_value = cruiseplan.ScheduleResult(
                timeline=[{"activity": "Test", "duration_minutes": 60}],
                files_created=[Path("test_schedule.html")],
                summary={
                    "activities": 1,
                    "files_generated": 1,
                    "formats": ["html"],
                    "leg": None,
                },
            )

            main(args)

            # Verify warning was printed
            warning_calls = [
                call for call in mock_print.call_args_list if call[0][0].startswith("⚠️")
            ]
            assert len(warning_calls) > 0

            # Verify derive_netcdf was set to False in API call
            mock_schedule.assert_called_once()
            call_args = mock_schedule.call_args
            assert call_args[1]["derive_netcdf"] is False

    def test_schedule_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"), format="all", verbose=False
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.side_effect = cruiseplan.ValidationError(
                "Invalid YAML configuration"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_schedule_file_error_handling(self):
        """Test handling of FileError from API."""
        args = argparse.Namespace(
            config_file=Path("missing.yaml"), format="all", verbose=False
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.side_effect = cruiseplan.FileError(
                "Configuration file not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_schedule_runtime_error_handling(self):
        """Test handling of RuntimeError from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), format="all", verbose=False
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.side_effect = RuntimeError("Failed to generate timeline")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_schedule_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), format="all", verbose=False
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_schedule_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), format="all", verbose=False
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.side_effect = Exception("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_schedule_unexpected_error_with_verbose(self):
        """Test handling of unexpected errors with verbose traceback."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            format="all",
            verbose=True,  # Should trigger traceback printing
        )

        with (
            patch("cruiseplan.schedule") as mock_schedule,
            patch("traceback.print_exc") as mock_traceback,
        ):
            mock_schedule.side_effect = Exception("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should print traceback when verbose=True
            mock_traceback.assert_called_once()
            assert exc_info.value.code == 1

    def test_default_argument_handling(self):
        """Test that missing arguments get proper defaults."""
        # Minimal args - missing optional attributes
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            format="csv",
            # Missing: output_dir, output, leg, derive_netcdf, etc.
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            mock_schedule.return_value = cruiseplan.ScheduleResult(
                timeline=[{"activity": "Test", "duration_minutes": 30}],
                files_created=[Path("data/test_schedule.csv")],
                summary={"activities": 1, "files_generated": 1},
            )

            main(args)

            # Should use defaults for missing arguments
            mock_schedule.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",  # default
                output=None,  # default
                format="csv",
                leg=None,  # default
                derive_netcdf=False,  # default
                bathy_source="etopo2022",  # default
                bathy_dir="data/bathymetry",  # default
                bathy_stride=10,  # default
                figsize=None,  # default
                verbose=False,  # default
            )

    def test_schedule_empty_timeline_handling(self):
        """Test handling of empty timeline result."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"), format="all", verbose=False
        )

        with patch("cruiseplan.schedule") as mock_schedule:
            # Return result with empty timeline
            mock_schedule.return_value = cruiseplan.ScheduleResult(
                timeline=[],  # Empty timeline
                files_created=[],
                summary={"activities": 0, "files_generated": 0},
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with failure code for empty timeline
            assert exc_info.value.code == 1


class TestScheduleResultType:
    """Test the ScheduleResult type for completeness."""

    def test_schedule_result_success(self):
        """Test ScheduleResult with successful schedule generation."""
        timeline = [
            {"activity": "Transit", "duration_minutes": 120},
            {"activity": "Station", "duration_minutes": 90},
        ]
        result = cruiseplan.ScheduleResult(
            timeline=timeline,
            files_created=[Path("schedule.html"), Path("schedule.csv")],
            summary={"activities": 2, "files_generated": 2},
        )

        assert result.timeline == timeline
        assert bool(result) is True
        assert len(result.files_created) == 2
        assert "✅ Schedule (2 activities) complete" in str(result)
        assert "(2 files)" in str(result)

    def test_schedule_result_failure(self):
        """Test ScheduleResult with failed schedule generation."""
        result = cruiseplan.ScheduleResult(
            timeline=None,
            files_created=[],
            summary={"activities": 0, "files_generated": 0},
        )

        assert result.timeline is None
        assert bool(result) is False
        assert len(result.files_created) == 0
        assert "❌ Schedule failed" in str(result)

    def test_schedule_result_empty_timeline(self):
        """Test ScheduleResult with empty timeline."""
        result = cruiseplan.ScheduleResult(
            timeline=[],  # Empty but not None
            files_created=[],
            summary={"activities": 0, "files_generated": 0},
        )

        assert result.timeline == []
        assert bool(result) is False  # Empty timeline evaluates to False
        assert "❌ Schedule failed" in str(result)
