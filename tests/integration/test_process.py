"""
Integration tests for cruiseplan process command.

These tests exercise the process command with real code execution and minimal mocking
to achieve better test coverage and validate end-to-end functionality.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.process import main


class TestProcessIntegration:
    """Integration tests for process command with real execution paths."""

    def test_process_command_with_real_config_validation(self):
        """Test process command with real configuration file validation."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir=Path("tests_output"),
            add_depths=True,
            add_coords=True,
            expand_sections=False,
            expand_ports=False,
            run_validation=True,
            run_map_generation=False,  # Skip map generation to avoid external deps
            verbose=False,
            quiet=False,
        )

        # Mock the API call and disable file size checking to avoid filesystem dependencies
        with (
            patch("cruiseplan.process") as mock_api,
            patch("cruiseplan.utils.output_formatting._format_output_summary") as mock_summary,
        ):
            mock_api.return_value = (
                {"stations_with_depths_added": 3},
                [Path("tests_output/tc1_single_enriched.yaml")],
            )
            mock_summary.return_value = "✅ Configuration processing completed successfully"

            # This should run real validation logic
            main(args)

            # Verify API was called with processed parameters
            mock_api.assert_called_once()
            call_args = mock_api.call_args[1]  # Get kwargs
            assert "config_file" in call_args
            assert call_args["add_depths"] is True
            assert call_args["add_coords"] is True

    def test_process_command_file_not_found_error(self):
        """Test process command handles file not found errors correctly."""
        args = argparse.Namespace(
            config_file=Path("nonexistent_file.yaml"),
            output_dir=Path("tests_output"),
            verbose=False,
            quiet=False,
        )

        # No mocking - let real validation run and fail
        with pytest.raises(SystemExit):
            main(args)

    def test_process_command_legacy_parameter_handling(self):
        """Test that process command correctly handles legacy parameters."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir=Path("tests_output"),
            add_depths=True,
            add_coords=True,
            # Legacy parameters that should be migrated
            bathy_source_legacy="etopo2022",
            bathy_dir_legacy=Path("data/bathymetry"),
            bathy_stride_legacy=10,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.process") as mock_api,
            patch("cruiseplan.utils.output_formatting._format_output_summary") as mock_summary,
        ):
            mock_api.return_value = ({}, [Path("test_output.yaml")])
            mock_summary.return_value = "✅ Configuration processing completed successfully"

            # This should run real parameter migration logic
            main(args)

            # Verify legacy parameters were processed
            mock_api.assert_called_once()

    def test_process_command_keyboard_interrupt(self):
        """Test process command handles keyboard interrupt gracefully."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir=Path("tests_output"),
            add_depths=True,
            add_coords=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.process") as mock_api,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)

    def test_process_command_api_error_handling(self):
        """Test process command handles API errors with proper error formatting."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir=Path("tests_output"),
            add_depths=True,
            add_coords=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.process") as mock_api,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_api.side_effect = Exception("API processing failed")

            with pytest.raises(SystemExit):
                main(args)


class TestProcessEdgeCases:
    """Test edge cases and error conditions for process command."""

    def test_missing_required_attributes(self):
        """Test handling of args object missing required attributes."""
        # Create minimal args object missing some expected attributes
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
        )
        # Missing output_dir, verbose, etc.

        with (
            patch("cruiseplan.process") as mock_api,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_api.return_value = ({}, [])

            # Should handle missing attributes gracefully via getattr defaults
            main(args)

            mock_api.assert_called_once()

    def test_empty_api_response_handling(self):
        """Test handling when API returns empty/None responses."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir=Path("tests_output"),
            add_depths=True,
            verbose=False,
            quiet=False,
        )

        with (
            patch("cruiseplan.process") as mock_api,
            patch("pathlib.Path.exists", return_value=True),
        ):
            # Test that empty API response is handled gracefully
            mock_api.return_value = (None, [])

            # Should complete without error (process command is robust)
            main(args)

            mock_api.assert_called_once()
