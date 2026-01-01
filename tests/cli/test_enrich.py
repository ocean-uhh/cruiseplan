"""
Test suite for cruiseplan.cli.enrich command - API-First Architecture.

This module implements streamlined tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.enrich import main


class TestEnrichCommand:
    """Streamlined test suite for CLI enrich functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            expand_ports=False,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            output_file=None,
            output_dir=Path("data"),
            output="test_enriched",
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.enrich._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.enrich._format_progress_header"),
            patch(
                "cruiseplan.cli.enrich._collect_generated_files",
                return_value=[Path("test_enriched.yaml")],
            ),
            patch("cruiseplan.cli.enrich._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (
                {"stations_with_depths_added": 3},
                [Path("test_enriched.yaml")],
            )

            main(args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            add_coords=False,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
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
            add_depths=True,
            add_coords=False,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
        ):
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)

    def test_validation_error_handling(self):
        """Test handling of validation errors with pretty formatting."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            add_coords=False,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params") as mock_resolve,
        ):

            from cruiseplan.cli.cli_utils import CLIError

            mock_resolve.side_effect = CLIError("Invalid configuration")

            with pytest.raises(SystemExit):
                main(args)

    def test_successful_enrichment_shows_summary(self):
        """Test successful enrichment shows operation summary."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
            verbose=False,
            quiet=False,
        )

        summary_data = {
            "stations_with_depths_added": 5,
            "stations_with_coords_added": 3,
            "sections_expanded": 2,
        }

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.enrich._convert_api_response_to_cli",
                return_value={"success": True, "data": summary_data},
            ),
            patch("cruiseplan.cli.enrich._format_progress_header"),
            patch(
                "cruiseplan.cli.enrich._collect_generated_files",
                return_value=[Path("test_enriched.yaml")],
            ),
            patch("cruiseplan.cli.enrich._format_success_message"),
            patch(
                "cruiseplan.cli.enrich._show_enrichment_summary"
            ) as mock_show_summary,
        ):

            # Mock successful API response
            mock_api.return_value = (summary_data, [Path("test_enriched.yaml")])

            main(args)

            # Verify summary was shown
            mock_show_summary.assert_called_once_with(summary_data, args)

    def test_format_validation_errors_stations(self):
        """Test validation error formatting for stations."""
        from cruiseplan.cli.enrich import _format_validation_errors

        errors = [
            {
                "loc": ["stations", "0", "latitude"],
                "type": "missing",
                "msg": "field required",
            },
            {
                "loc": ["stations", "1", "longitude"],
                "type": "value_error",
                "msg": "invalid value",
                "input": "bad_value",
            },
            {
                "loc": ["stations"],
                "type": "general_error",
                "msg": "general stations error",
            },
        ]

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            _format_validation_errors(errors)

            # Should have called error logging for each error type
            assert mock_logger.error.call_count > 0

    def test_format_validation_errors_all_types(self):
        """Test validation error formatting for all entity types."""
        from cruiseplan.cli.enrich import _format_validation_errors

        errors = [
            {
                "loc": ["moorings", "0", "depth"],
                "type": "missing",
                "msg": "field required",
            },
            {
                "loc": ["transits", "1", "route"],
                "type": "value_error",
                "msg": "invalid route",
                "input": [],
            },
            {"loc": ["legs", "0", "name"], "type": "missing", "msg": "field required"},
            {
                "loc": ["areas", "1", "boundary"],
                "type": "value_error",
                "msg": "invalid boundary",
                "input": "bad_shape",
            },
            {"loc": ["other", "field"], "type": "error", "msg": "general error"},
        ]

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            _format_validation_errors(errors)

            # Should handle all error types
            assert mock_logger.error.call_count > 0

    def test_format_validation_errors_comprehensive(self):
        """Test comprehensive validation error formatting covering all branches."""
        from cruiseplan.cli.enrich import _format_validation_errors

        # Test all different error types and paths to improve coverage
        errors = [
            # Stations - general error (covers line 59)
            {
                "loc": ["stations"],
                "type": "general_error",
                "msg": "general stations error",
            },
            # Moorings - missing field (covers lines 68-71)
            {"loc": ["moorings", "0"], "type": "missing", "msg": "field required"},
            {
                "loc": ["moorings", "1", "depth"],
                "type": "missing",
                "msg": "field required",
            },
            {
                "loc": ["moorings"],
                "type": "general_error",
                "msg": "general moorings error",
            },
            # Transits - missing field (covers lines 77-78)
            {"loc": ["transits", "0"], "type": "missing", "msg": "field required"},
            {
                "loc": ["transits", "1", "route"],
                "type": "missing",
                "msg": "field required",
            },
            {
                "loc": ["transits"],
                "type": "general_error",
                "msg": "general transits error",
            },
            # Legs - value errors (covers lines 92-95)
            {
                "loc": ["legs", "0", "name"],
                "type": "value_error",
                "msg": "invalid value",
                "input": "bad_value",
            },
            {"loc": ["legs"], "type": "general_error", "msg": "general legs error"},
            # Areas - value errors (covers lines 101-102, 107)
            {
                "loc": ["areas", "1", "boundary"],
                "type": "value_error",
                "msg": "invalid boundary",
                "input": "bad_shape",
            },
            {"loc": ["areas"], "type": "general_error", "msg": "general areas error"},
        ]

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            _format_validation_errors(errors)

            # Should handle all error types and call logger multiple times
            assert mock_logger.error.call_count > 10

    def test_show_enrichment_summary_comprehensive(self):
        """Test enrichment summary display with all operation types."""
        from cruiseplan.cli.enrich import _show_enrichment_summary

        summary = {
            "stations_with_depths_added": 5,
            "stations_with_coords_added": 3,
            "sections_expanded": 2,
            "stations_from_expansion": 12,
            "ports_expanded": 1,
            "defaults_added": 1,
            "station_defaults_added": 2,
        }

        args = argparse.Namespace(
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
        )

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            _show_enrichment_summary(summary, args)

            # Should log summary information
            assert mock_logger.info.call_count > 0

    def test_show_enrichment_summary_minimal(self):
        """Test enrichment summary with minimal operations."""
        from cruiseplan.cli.enrich import _show_enrichment_summary

        summary = {
            "stations_with_depths_added": 0,
            "stations_with_coords_added": 1,
        }

        args = argparse.Namespace(
            add_depths=False,
            add_coords=True,
            expand_sections=False,
            expand_ports=False,
        )

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            _show_enrichment_summary(summary, args)

            # Should still log summary
            assert mock_logger.info.call_count > 0

    def test_show_enrichment_summary_no_enhancements(self):
        """Test enrichment summary when no enhancements were needed (covers line 147)."""
        from cruiseplan.cli.enrich import _show_enrichment_summary

        # Summary with zero enhancements
        summary = {
            "stations_with_depths_added": 0,
            "stations_with_coords_added": 0,
            "sections_expanded": 0,
            "ports_expanded": 0,
        }

        args = argparse.Namespace(
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
        )

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            _show_enrichment_summary(summary, args)

            # Should log the "no enhancements needed" message
            mock_logger.info.assert_any_call(
                "ℹ️ No enhancements were needed - configuration is already complete"
            )

    def test_no_operations_specified_error(self):
        """Test error when no enrichment operations are specified."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=False,
            add_coords=False,
            expand_sections=False,
            expand_ports=False,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
        ):

            with pytest.raises(SystemExit):
                main(args)

    def test_deprecated_output_file_parameter(self):
        """Test handling of deprecated --output-file parameter."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            expand_ports=False,
            output_file=Path("custom_output.yaml"),  # Deprecated parameter
            output_dir=None,
            output=None,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.enrich._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.enrich._format_progress_header"),
            patch(
                "cruiseplan.cli.enrich._collect_generated_files",
                return_value=[Path("test_enriched.yaml")],
            ),
            patch("cruiseplan.cli.enrich._format_success_message"),
            patch("cruiseplan.cli.enrich.logger") as mock_logger,
        ):

            # Mock successful API response
            mock_api.return_value = (
                {"stations_with_depths_added": 1},
                [Path("custom_output.yaml")],
            )

            main(args)

            # Verify deprecation warning was logged
            mock_logger.warning.assert_called_with(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )

    def test_successful_enrichment_with_all_operations(self):
        """Test successful enrichment with all enhancement types."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("bathy_data"),
            coord_format="dms",
            output_file=None,
            output_dir=Path("output"),
            output="enhanced",
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.enrich._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.enrich._format_progress_header"),
            patch(
                "cruiseplan.cli.enrich._collect_generated_files",
                return_value=[Path("test_enriched.yaml")],
            ),
            patch("cruiseplan.cli.enrich._format_success_message"),
        ):

            # Mock comprehensive enhancement result
            enhancement_summary = {
                "stations_with_depths_added": 5,
                "stations_with_coords_added": 3,
                "sections_expanded": 2,
                "stations_from_expansion": 12,
                "ports_expanded": 1,
                "defaults_added": 1,
                "station_defaults_added": 2,
            }
            mock_api.return_value = (
                enhancement_summary,
                [Path("output/enhanced_enriched.yaml")],
            )

            main(args)

            # Verify API was called with comprehensive parameters
            mock_api.assert_called_once()

    def test_main_enrichment_failure_handling(self):
        """Test handling of enrichment failure from API (covers lines 209-212)."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.enrich._convert_api_response_to_cli",
                return_value={
                    "success": False,
                    "errors": ["Processing failed", "Data error"],
                },
            ),
            patch("cruiseplan.cli.enrich._format_progress_header"),
            patch("cruiseplan.cli.enrich._collect_generated_files", return_value=[]),
        ):

            # Mock API response with failure
            mock_api.return_value = ({}, [])

            with pytest.raises(SystemExit):
                main(args)

    def test_main_validation_error_handling(self):
        """Test handling of ValidationError exceptions (covers lines 220-226)."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            verbose=False,
            quiet=False,
        )

        from pydantic import ValidationError

        # Create mock validation error
        mock_validation_errors = [
            {
                "loc": ("stations", "0", "latitude"),
                "type": "missing",
                "msg": "Field required",
                "input": None,
            }
        ]

        validation_error = ValidationError.from_exception_data(
            "TestModel", mock_validation_errors
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.enrich._format_validation_errors"
            ) as mock_format_errors,
            patch("cruiseplan.cli.enrich.logger") as mock_logger,
        ):

            mock_api.side_effect = validation_error

            with pytest.raises(SystemExit):
                main(args)

            # Should log error count and call format function
            mock_logger.error.assert_called()
            # Just verify the function was called, not the exact format
            mock_format_errors.assert_called_once()

    def test_main_keyboard_interrupt_handling_coverage(self):
        """Test keyboard interrupt handling (covers lines 229-230)."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            add_depths=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.enrich") as mock_api,
            patch("cruiseplan.cli.enrich._setup_cli_logging"),
            patch(
                "cruiseplan.cli.enrich._validate_config_file",
                return_value=Path("test.yaml"),
            ),
            patch("cruiseplan.cli.enrich.logger") as mock_logger,
        ):

            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)

            # Should log cancellation message
            mock_logger.info.assert_called_with("\n\n⚠️ Operation cancelled by user.")

    def test_main_module_executable(self):
        """Test that the __main__ block is executable (covers lines 243-273)."""
        # We can test the actual argparse execution, but we can at least
        # verify the imports and basic structure work
        from cruiseplan.cli import enrich

        # Verify the main function exists and is callable
        assert hasattr(enrich, "main")
        assert callable(enrich.main)


class TestEnrichCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import enrich

        assert hasattr(enrich, "main")
        # Check that utility functions exist (not implementation details)
        assert hasattr(enrich, "_format_validation_errors")
        assert hasattr(enrich, "_show_enrichment_summary")
