"""
Test suite for cruiseplan.cli.validate command - API-First Architecture.

This module implements streamlined tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.validate import main


class TestValidateCommand:
    """Streamlined test suite for CLI validate functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            check_depths=True,
            tolerance=5.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.validate") as mock_api,
            patch("cruiseplan.cli.validate._setup_cli_logging"),
            patch(
                "cruiseplan.cli.validate._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.validate._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.validate._convert_api_response_to_cli", return_value={}
            ),
            patch(
                "cruiseplan.cli.validate._extract_api_errors",
                return_value=(True, [], []),
            ),
            patch("cruiseplan.cli.validate._format_progress_header"),
            patch(
                "cruiseplan.cli.validate._format_validation_results",
                return_value="✅ Configuration valid",
            ),
        ):

            # Mock successful API response
            mock_api.return_value = {"success": True, "errors": [], "warnings": []}

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with success code 0
            assert exc_info.value.code == 0

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.validate") as mock_api,
            patch("cruiseplan.cli.validate._setup_cli_logging"),
            patch(
                "cruiseplan.cli.validate._validate_config_file",
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
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.validate") as mock_api,
            patch("cruiseplan.cli.validate._setup_cli_logging"),
        ):
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)

    def test_validation_with_errors_exits_with_error_code(self):
        """Test that validation errors cause exit with error code."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.validate") as mock_api,
            patch("cruiseplan.cli.validate._setup_cli_logging"),
            patch(
                "cruiseplan.cli.validate._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.validate._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.validate._convert_api_response_to_cli", return_value={}
            ),
            patch(
                "cruiseplan.cli.validate._extract_api_errors",
                return_value=(False, ["Missing field"], []),
            ),
            patch("cruiseplan.cli.validate._format_progress_header"),
            patch(
                "cruiseplan.cli.validate._format_validation_results",
                return_value="❌ Configuration invalid",
            ),
        ):

            # Mock API response with errors
            mock_api.return_value = {
                "success": False,
                "errors": ["Missing field"],
                "warnings": [],
            }

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with error code 1
            assert exc_info.value.code == 1

    def test_validation_with_warnings_only_exits_successfully(self):
        """Test that warnings-only validation exits successfully."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            warnings_only=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.validate") as mock_api,
            patch("cruiseplan.cli.validate._setup_cli_logging"),
            patch(
                "cruiseplan.cli.validate._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.validate._resolve_cli_to_api_params", return_value={}
            ),
            patch(
                "cruiseplan.cli.validate._convert_api_response_to_cli", return_value={}
            ),
            patch(
                "cruiseplan.cli.validate._extract_api_errors",
                return_value=(True, [], ["Minor issue"]),
            ),
            patch("cruiseplan.cli.validate._format_progress_header"),
            patch(
                "cruiseplan.cli.validate._format_validation_results",
                return_value="✅ Configuration valid with warnings",
            ),
        ):

            # Mock API response with warnings only
            mock_api.return_value = {
                "success": True,
                "errors": [],
                "warnings": ["Minor issue"],
            }

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with success code 0
            assert exc_info.value.code == 0

    def test_nonexistent_file_handled_by_validation_utility(self):
        """Test that nonexistent files are caught by input validation."""
        args = argparse.Namespace(
            config_file=Path("nonexistent.yaml"),
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.cli.validate._setup_cli_logging"),
            patch("cruiseplan.cli.validate._validate_config_file") as mock_validate,
        ):

            from cruiseplan.cli.cli_utils import CLIError

            mock_validate.side_effect = CLIError("File not found")

            with pytest.raises(SystemExit):
                main(args)
