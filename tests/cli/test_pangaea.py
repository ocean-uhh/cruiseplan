"""
Test suite for cruiseplan.cli.pangaea command - API-First Architecture.

This module implements streamlined tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.pangaea import (
    determine_workflow_mode,
    main,
    validate_lat_lon_bounds,
)


class TestCoordinateBoundsValidation:
    """Test coordinate bounds validation functionality."""

    def test_validate_lat_lon_bounds_standard_format(self):
        """Test coordinate bounds validation with standard -180/180 format."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [-10.0, 5.0]

        result = validate_lat_lon_bounds(lat_bounds, lon_bounds)
        expected = (-10.0, 50.0, 5.0, 60.0)  # min_lon, min_lat, max_lon, max_lat

        assert result == expected

    def test_validate_lat_lon_bounds_360_format(self):
        """Test coordinate bounds validation with 0/360 format."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [350.0, 360.0]

        result = validate_lat_lon_bounds(lat_bounds, lon_bounds)
        expected = (350.0, 50.0, 360.0, 60.0)

        assert result == expected

    def test_validate_lat_lon_bounds_360_crossing_meridian_fails(self):
        """Test coordinate bounds validation fails when crossing 0° meridian in 360 format."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [350.0, 10.0]

        from cruiseplan.cli.cli_utils import CLIError

        # This should fail - meridian crossing not allowed in 0/360 format
        with pytest.raises(
            CLIError, match="For meridian crossing, use -180/180 format"
        ):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)

    def test_validate_lat_lon_bounds_mixed_format_error(self):
        """Test validation fails with mixed longitude formats."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [-10.0, 240.0]  # Mixed formats

        from cruiseplan.cli.cli_utils import CLIError

        with pytest.raises(CLIError, match="Invalid lat/lon bounds"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)

    def test_validate_lat_lon_bounds_invalid_latitude_range(self):
        """Test validation fails with invalid latitude range."""
        lat_bounds = [-100.0, 60.0]  # Invalid min_lat
        lon_bounds = [-10.0, 5.0]

        from cruiseplan.cli.cli_utils import CLIError

        with pytest.raises(CLIError, match="Invalid lat/lon bounds"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)

    def test_validate_lat_lon_bounds_invalid_latitude_ordering(self):
        """Test validation fails when min_lat >= max_lat."""
        lat_bounds = [60.0, 50.0]  # Wrong ordering
        lon_bounds = [-10.0, 5.0]

        from cruiseplan.cli.cli_utils import CLIError

        with pytest.raises(CLIError, match="Invalid lat/lon bounds"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)


class TestWorkflowModeDetection:
    """Test workflow mode detection functionality."""

    def test_determine_workflow_mode_search(self):
        """Test detection of search mode."""
        args = argparse.Namespace(
            query_or_file="CTD profiles", lat=[50.0, 60.0], lon=[-10.0, 5.0]
        )

        mode = determine_workflow_mode(args)
        assert mode == "search"

    def test_determine_workflow_mode_doi_file(self, tmp_path):
        """Test detection of DOI file mode."""
        # Create a temporary .txt file
        doi_file = tmp_path / "dois.txt"
        doi_file.write_text("10.1594/PANGAEA.12345")

        args = argparse.Namespace(query_or_file=str(doi_file))

        mode = determine_workflow_mode(args)
        assert mode == "doi_file"

    def test_determine_workflow_mode_search_with_lat_lon(self):
        """Test that lat/lon presence forces search mode."""
        args = argparse.Namespace(
            query_or_file="some_ambiguous_query", lat=[50.0, 60.0], lon=[-10.0, 5.0]
        )

        mode = determine_workflow_mode(args)
        assert mode == "search"


class TestPangaeaCommand:
    """Streamlined test suite for CLI pangaea functionality."""

    def test_main_calls_api_with_search_params(self):
        """Test that CLI correctly calls API layer with search parameters."""
        args = argparse.Namespace(
            query_or_file="CTD temperature",
            lat=[50, 60],
            lon=[-50, -30],
            limit=10,
            output_dir=Path("data"),
            output="atlantic_study",
            rate_limit=1.0,
            merge_campaigns=True,
            output_file=None,
            verbose=False,
        )

        mock_stations = [{"Campaign": "Test", "Stations": [{"lat": 55.0, "lon": -5.0}]}]

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {"query": "CTD temperature"}),
            ),
            patch("cruiseplan.cli.pangaea._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.pangaea._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch(
                "cruiseplan.cli.pangaea._collect_generated_files",
                return_value=[Path("atlantic_study_stations.pkl")],
            ),
            patch("cruiseplan.cli.pangaea._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (
                mock_stations,
                [Path("atlantic_study_stations.pkl")],
            )

            main(args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_calls_api_with_doi_file_mode(self):
        """Test that CLI correctly calls API layer with DOI file parameters."""
        args = argparse.Namespace(
            query_or_file="dois.txt",
            output_file=None,
            output_dir=Path("data"),
            output="pangaea_from_dois",
            verbose=False,
        )

        mock_stations = [{"Campaign": "Test", "Stations": [{"lat": 55.0, "lon": -5.0}]}]

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("doi_file", {}),
            ),
            patch("cruiseplan.cli.pangaea._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.pangaea._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch(
                "cruiseplan.cli.pangaea._collect_generated_files",
                return_value=[Path("pangaea_from_dois.pkl")],
            ),
            patch("cruiseplan.cli.pangaea._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (mock_stations, [Path("pangaea_from_dois.pkl")])

            main(args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        args = argparse.Namespace(
            query_or_file="CTD profiles",
            lat=[50.0, 60.0],
            lon=[-10.0, 0.0],
            verbose=False,
        )

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {}),
            ),
        ):
            mock_api.side_effect = Exception("API error")

            with pytest.raises(SystemExit):
                main(args)

    def test_main_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            query_or_file="CTD profiles",
            lat=[50.0, 60.0],
            lon=[-10.0, 0.0],
            verbose=False,
        )

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {}),
            ),
        ):
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)

    def test_pangaea_processing_failure(self):
        """Test handling of processing failure from API."""
        args = argparse.Namespace(
            query_or_file="CTD profiles",
            lat=[50.0, 60.0],
            lon=[-10.0, 0.0],
            verbose=False,
        )

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {}),
            ),
            patch("cruiseplan.cli.pangaea._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.pangaea._convert_api_response_to_cli",
                return_value={"success": False, "errors": ["Processing failed"]},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch("cruiseplan.cli.pangaea._collect_generated_files", return_value=[]),
        ):

            # Mock API response with failure
            mock_api.return_value = ([], [])

            with pytest.raises(SystemExit):
                main(args)


class TestPangaeaCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import pangaea

        assert hasattr(pangaea, "main")
        assert callable(pangaea.main)

        # Check that utility functions exist
        assert hasattr(pangaea, "validate_lat_lon_bounds")
        assert callable(pangaea.validate_lat_lon_bounds)

        assert hasattr(pangaea, "determine_workflow_mode")
        assert callable(pangaea.determine_workflow_mode)
