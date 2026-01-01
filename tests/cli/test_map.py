"""
Test suite for cruiseplan.cli.map command - API-First Architecture.

This module implements streamlined tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

from cruiseplan.cli.map import main


class TestMapCommand:
    """Streamlined test suite for CLI map functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("output"),
            output_file=None,
            format="png",
            bathy_source="gebco2025",
            bathy_dir=Path("data"),
            bathy_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        with (
            patch("cruiseplan.map") as mock_api,
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch("cruiseplan.cli.cli_utils._handle_deprecated_params"),
            patch(
                "cruiseplan.cli.map._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.map._validate_directory_writable",
                return_value=Path("output"),
            ),
            patch("cruiseplan.cli.map._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.map._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.map._format_progress_header"),
            patch(
                "cruiseplan.cli.map._collect_generated_files",
                return_value=[Path("output/test_map.png")],
            ),
            patch("cruiseplan.cli.map._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = [Path("output/test_map.png")]

            result = main(args)

            # Should return 0 for success
            assert result == 0

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("output"),
            verbose=False,
        )

        with (
            patch("cruiseplan.map") as mock_api,
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch(
                "cruiseplan.cli.map._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.map._validate_directory_writable",
                return_value=Path("output"),
            ),
        ):
            mock_api.side_effect = Exception("API error")

            result = main(args)

            # Should return 1 for error
            assert result == 1

    def test_main_file_not_found_handling(self):
        """Test graceful handling of file not found."""
        args = argparse.Namespace(
            config_file=Path("nonexistent.yaml"),
            output_dir=Path("output"),
            verbose=False,
        )

        with (
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch("cruiseplan.cli.map._validate_config_file") as mock_validate,
        ):
            mock_validate.side_effect = FileNotFoundError()

            result = main(args)

            # Should return 1 for error
            assert result == 1

    def test_deprecated_output_file_parameter(self):
        """Test handling of deprecated --output-file parameter."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("output"),
            output_file=Path("custom_map.png"),  # Deprecated parameter
            format="png",
            verbose=False,
        )

        with (
            patch("cruiseplan.map") as mock_api,
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch("cruiseplan.cli.cli_utils._handle_deprecated_params"),
            patch(
                "cruiseplan.cli.map._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.map._validate_directory_writable",
                return_value=Path("output"),
            ),
            patch("cruiseplan.cli.map._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.map._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.map._format_progress_header"),
            patch(
                "cruiseplan.cli.map._collect_generated_files",
                return_value=[Path("custom_map.png")],
            ),
            patch("cruiseplan.cli.map._format_success_message"),
            patch("cruiseplan.cli.map.logger") as mock_logger,
        ):

            # Mock successful API response
            mock_api.return_value = [Path("custom_map.png")]

            result = main(args)

            # Should succeed
            assert result == 0

            # Verify deprecation warning was logged
            mock_logger.warning.assert_called_with(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )

    def test_map_generation_with_all_formats(self):
        """Test map generation with all output formats."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("output"),
            output_file=None,
            format="all",  # PNG + KML
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            bathy_stride=10,
            show_plot=False,
            figsize=[15, 12],
            verbose=True,
        )

        with (
            patch("cruiseplan.map") as mock_api,
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch("cruiseplan.cli.cli_utils._handle_deprecated_params"),
            patch(
                "cruiseplan.cli.map._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.map._validate_directory_writable",
                return_value=Path("output"),
            ),
            patch("cruiseplan.cli.map._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.map._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.map._format_progress_header"),
            patch(
                "cruiseplan.cli.map._collect_generated_files",
                return_value=[
                    Path("output/test_map.png"),
                    Path("output/test_catalog.kml"),
                ],
            ),
            patch("cruiseplan.cli.map._format_success_message"),
        ):

            # Mock successful API response with multiple files
            mock_api.return_value = [
                Path("output/test_map.png"),
                Path("output/test_catalog.kml"),
            ]

            result = main(args)

            # Should succeed
            assert result == 0

            # Verify API was called
            mock_api.assert_called_once()

    def test_map_generation_failure_handling(self):
        """Test handling when map generation fails."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("output"),
            verbose=False,
        )

        with (
            patch("cruiseplan.map") as mock_api,
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch("cruiseplan.cli.cli_utils._handle_deprecated_params"),
            patch(
                "cruiseplan.cli.map._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.map._validate_directory_writable",
                return_value=Path("output"),
            ),
            patch("cruiseplan.cli.map._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.map._convert_api_response_to_cli",
                return_value={"success": False, "errors": ["Map generation failed"]},
            ),
            patch("cruiseplan.cli.map._format_progress_header"),
            patch("cruiseplan.cli.map._collect_generated_files", return_value=[]),
        ):

            # Mock failed API response
            mock_api.return_value = []

            result = main(args)

            # Should return 1 for failure
            assert result == 1

    def test_verbose_exception_handling(self):
        """Test verbose exception handling with traceback."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("output"),
            verbose=True,
        )

        with (
            patch("cruiseplan.map") as mock_api,
            patch("cruiseplan.cli.map._setup_cli_logging"),
            patch(
                "cruiseplan.cli.map._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch(
                "cruiseplan.cli.map._validate_directory_writable",
                return_value=Path("output"),
            ),
            patch("traceback.print_exc") as mock_traceback,
        ):
            mock_api.side_effect = RuntimeError("Unexpected error")

            result = main(args)

            # Should return 1 for error
            assert result == 1

            # Should print traceback in verbose mode
            mock_traceback.assert_called_once()


class TestMapCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import map as map_module

        assert hasattr(map_module, "main")
        assert callable(map_module.main)
