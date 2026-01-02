"""
Test suite for cruiseplan process command.

Streamlined tests focused on CLI layer functionality after API-first refactoring.
Tests verify CLI argument handling and API integration, not underlying business logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.process import main


class TestProcessCommand:
    """Streamlined test suite for CLI process functionality."""

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        mock_args = MagicMock()
        mock_args.config_file = Path("test_config.yaml")
        mock_args.output_dir = Path("data")
        mock_args.add_depths = True
        mock_args.add_coords = True
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.process") as mock_api,
            patch("cruiseplan.cli.process._setup_cli_logging"),
            patch("cruiseplan.cli.process._handle_deprecated_cli_params"),
            patch("cruiseplan.cli.process._apply_cli_defaults"),
            patch(
                "cruiseplan.cli.process._initialize_cli_command",
                return_value=Path("test_config.yaml"),
            ),
            patch("cruiseplan.cli.process._format_progress_header"),
            patch(
                "cruiseplan.cli.process._standardize_output_setup",
                return_value=(Path("data"), "test", {}),
            ),
            patch("cruiseplan.cli.process._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.process._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.process._collect_generated_files") as mock_collect,
            patch("cruiseplan.cli.process._format_output_summary"),
        ):

            mock_api.return_value = ([], [Path("data/test_enriched.yaml")])
            mock_collect.return_value = [Path("data/test_enriched.yaml")]

            main(mock_args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        mock_args = MagicMock()
        mock_args.config_file = Path("test_config.yaml")
        mock_args.output_dir = Path("data")
        mock_args.verbose = False

        with patch("cruiseplan.process") as mock_api:
            mock_api.side_effect = Exception("API error")

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_main_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        mock_args = MagicMock()
        mock_args.config_file = Path("test_config.yaml")
        mock_args.output_dir = Path("data")
        mock_args.verbose = False

        with patch("cruiseplan.process") as mock_api:
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_main_handles_processing_failure(self):
        """Test handling of processing failure from API."""
        mock_args = MagicMock()
        mock_args.config_file = Path("test_config.yaml")
        mock_args.output_dir = Path("data")
        mock_args.add_depths = True
        mock_args.add_coords = True
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.process") as mock_api,
            patch("cruiseplan.cli.process._setup_cli_logging"),
            patch("cruiseplan.cli.cli_utils._handle_deprecated_params"),
            patch(
                "cruiseplan.cli.process._validate_config_file",
                return_value=Path("test_config.yaml"),
            ),
            patch("cruiseplan.cli.process._format_progress_header"),
            patch("cruiseplan.cli.process._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.process._convert_api_response_to_cli",
                return_value={
                    "success": False,
                    "errors": ["Processing failed", "Missing data"],
                },
            ),
            patch("cruiseplan.cli.process._collect_generated_files", return_value=[]),
        ):

            # Mock API response with failure
            mock_api.return_value = ([], [])

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_main_handles_cli_error(self):
        """Test handling of CLIError exceptions."""
        mock_args = MagicMock()
        mock_args.config_file = Path("test_config.yaml")
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.cli.process._initialize_cli_command") as mock_init,
            patch("cruiseplan.cli.process.logger") as mock_logger,
        ):

            from cruiseplan.cli.cli_utils import CLIError

            mock_init.side_effect = CLIError("Invalid config file")

            with pytest.raises(SystemExit):
                main(mock_args)

            # Should log the error
            mock_logger.error.assert_called_once()
            # Error message should contain the CLIError content
            error_call = mock_logger.error.call_args[0][0]
            assert "Configuration processing failed" in error_call
            assert "Invalid config file" in error_call

    def test_main_handles_general_exception(self):
        """Test handling of unexpected exceptions."""
        mock_args = MagicMock()
        mock_args.config_file = Path("test_config.yaml")
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.process") as mock_api,
            patch("cruiseplan.cli.process._setup_cli_logging"),
            patch("cruiseplan.cli.process._handle_deprecated_cli_params"),
            patch("cruiseplan.cli.process._apply_cli_defaults"),
            patch(
                "cruiseplan.cli.process._initialize_cli_command",
                return_value=Path("test_config.yaml"),
            ),
            patch("cruiseplan.cli.process._standardize_output_setup",
                return_value=(Path("data"), "test", {})),
            patch("cruiseplan.cli.process.logger") as mock_logger,
        ):

            mock_api.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit):
                main(mock_args)

            # Should log the error
            mock_logger.error.assert_called_once()
            # Error message should contain the exception content
            error_call = mock_logger.error.call_args[0][0]
            assert "Configuration processing failed" in error_call
            assert "Unexpected error" in error_call
