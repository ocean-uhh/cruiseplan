"""
Test suite for cruiseplan.cli.schedule command - API-First Architecture.

This module implements streamlined tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.schedule import main


class TestScheduleCommand:
    """Streamlined test suite for CLI schedule functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            format="all",
            leg=None,
            derive_netcdf=True,
            validate_depths=False,
            verbose=False,
            quiet=False,
        )

        mock_timeline = [
            {"activity": "Transit", "duration_minutes": 120},
            {"activity": "Station CTD_001", "duration_minutes": 60},
        ]

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.schedule._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.schedule._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.schedule._format_progress_header"),
            patch(
                "cruiseplan.cli.schedule._collect_generated_files",
                return_value=[Path("test_schedule.csv")],
            ),
            patch(
                "cruiseplan.cli.schedule._format_timeline_summary",
                return_value="Timeline: 3.0 hours",
            ),
            patch("cruiseplan.cli.schedule._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (mock_timeline, [Path("test_schedule.csv")])

            main(args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            format="csv",
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
        ):
            mock_api.side_effect = Exception("API error")

            with pytest.raises(SystemExit):
                main(args)

    def test_main_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            format="csv",
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
        ):
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)

    def test_schedule_generation_failure(self):
        """Test handling of schedule generation failure from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            format="csv",
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.schedule._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.schedule._convert_api_response_to_cli",
                return_value={
                    "success": False,
                    "errors": ["Schedule generation failed"],
                },
            ),
            patch("cruiseplan.cli.schedule._format_progress_header"),
            patch("cruiseplan.cli.schedule._collect_generated_files", return_value=[]),
        ):

            # Mock API response with failure
            mock_api.return_value = ([], [])

            with pytest.raises(SystemExit):
                main(args)

    def test_derive_netcdf_flag_compatibility_warning(self):
        """Test --derive-netcdf flag compatibility checking."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            format="csv",  # CSV format with derive_netcdf=True should trigger warning
            derive_netcdf=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.schedule._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.schedule._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.schedule._format_progress_header"),
            patch(
                "cruiseplan.cli.schedule._collect_generated_files",
                return_value=[Path("test_schedule.csv")],
            ),
            patch(
                "cruiseplan.cli.schedule._format_timeline_summary",
                return_value="Timeline: 1.0 hours",
            ),
            patch("cruiseplan.cli.schedule._format_success_message"),
            patch("cruiseplan.cli.schedule.logger") as mock_logger,
        ):

            # Mock successful API response
            timeline = [{"activity": "Test", "duration_minutes": 60}]
            mock_api.return_value = (timeline, [Path("test_schedule.csv")])

            main(args)

            # Verify compatibility warning was logged
            mock_logger.warning.assert_called()
            warning_calls = [call[0][0] for call in mock_logger.warning.call_args_list]
            assert any("derive-netcdf" in call for call in warning_calls)

    def test_specific_leg_scheduling(self):
        """Test scheduling for a specific leg."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            format="html",
            leg="leg1",
            derive_netcdf=False,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.schedule._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.schedule._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.schedule._format_progress_header"),
            patch(
                "cruiseplan.cli.schedule._collect_generated_files",
                return_value=[Path("test_schedule.html")],
            ),
            patch(
                "cruiseplan.cli.schedule._format_timeline_summary",
                return_value="Timeline: 2.0 hours",
            ),
            patch("cruiseplan.cli.schedule._format_success_message"),
        ):

            # Mock successful API response
            timeline = [
                {"activity": "Transit", "duration_minutes": 60},
                {"activity": "Station", "duration_minutes": 60},
            ]
            mock_api.return_value = (timeline, [Path("test_schedule.html")])

            main(args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_cli_error_handling(self):
        """Test handling of CLIError exceptions."""
        args = argparse.Namespace(
            config_file=Path("nonexistent.yaml"),
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch("cruiseplan.cli.schedule._validate_config_file") as mock_validate,
            patch("cruiseplan.cli.schedule._format_error_message") as mock_format_error,
        ):

            from cruiseplan.cli.cli_utils import CLIError

            mock_validate.side_effect = CLIError("File not found")

            with pytest.raises(SystemExit):
                main(args)

            # Should format the error
            mock_format_error.assert_called_once_with(
                "schedule", mock_validate.side_effect
            )

    def test_empty_timeline_handling(self):
        """Test handling of empty timeline from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            format="csv",
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.schedule._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.schedule._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.schedule._format_progress_header"),
            patch("cruiseplan.cli.schedule._collect_generated_files", return_value=[]),
        ):

            # Mock API response with empty timeline
            mock_api.return_value = ([], [])

            with pytest.raises(SystemExit):
                main(args)

    def test_all_formats_schedule_generation(self):
        """Test schedule generation with all formats."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            format="all",
            derive_netcdf=True,
            verbose=True,
            quiet=False,
        )

        timeline = [
            {"activity": "Start", "duration_minutes": 0},
            {"activity": "Transit", "duration_minutes": 180},
            {"activity": "Station_001", "duration_minutes": 90},
            {"activity": "End", "duration_minutes": 0},
        ]
        generated_files = [
            Path("test_schedule.csv"),
            Path("test_schedule.html"),
            Path("test_schedule.nc"),
        ]

        with (
            patch("cruiseplan.schedule") as mock_api,
            patch("cruiseplan.cli.schedule._setup_cli_logging"),
            patch(
                "cruiseplan.cli.schedule._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.schedule._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.schedule._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.schedule._format_progress_header"),
            patch(
                "cruiseplan.cli.schedule._collect_generated_files",
                return_value=generated_files,
            ),
            patch(
                "cruiseplan.cli.schedule._format_timeline_summary",
                return_value="Timeline: 4.5 hours total",
            ),
            patch("cruiseplan.cli.schedule._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (timeline, generated_files)

            main(args)

            # Verify API was called
            mock_api.assert_called_once()


class TestScheduleCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import schedule

        assert hasattr(schedule, "main")
        assert callable(schedule.main)
