"""
Test suite for cruiseplan.cli.pangaea command - API-First Architecture.

This module implements comprehensive tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

import argparse
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.pangaea import (
    determine_workflow_mode,
    fetch_pangaea_data,
    main,
    save_doi_list,
    save_pangaea_pickle,
    search_pangaea_datasets,
    validate_dois,
    validate_lat_lon_bounds,
)


class TestDoiValidation:
    """Test DOI validation functionality."""

    def test_validate_dois_basic(self):
        """Test basic DOI validation."""
        dois = [
            "10.1594/PANGAEA.12345",
            "doi:10.1594/PANGAEA.67890",
            "https://doi.org/10.1594/PANGAEA.11111",
        ]

        result = validate_dois(dois)
        expected = [
            "10.1594/PANGAEA.12345",
            "10.1594/PANGAEA.67890",
            "10.1594/PANGAEA.11111",
        ]
        assert result == expected

    def test_validate_dois_invalid(self):
        """Test validation filters invalid DOIs."""
        dois = [
            "10.1594/PANGAEA.12345",
            "invalid-doi",
            "not-a-doi-at-all",
            "10.1594/PANGAEA.67890",
        ]

        result = validate_dois(dois)
        expected = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
        assert result == expected

    def test_validate_dois_whitespace_handling(self):
        """Test validation handles whitespace correctly."""
        dois = [
            "  10.1594/PANGAEA.12345  ",
            "\t10.1594/PANGAEA.67890\n",
        ]

        result = validate_dois(dois)
        expected = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
        assert result == expected


class TestPangaeaDataFetching:
    """Test PANGAEA data fetching functionality."""

    def test_fetch_pangaea_data_function_exists(self):
        """Test that fetch_pangaea_data function exists and is callable."""
        # This is a utility function so we just verify it exists
        assert callable(fetch_pangaea_data)

        # Test with empty DOI list (safe call that doesn't require mocking)
        result = fetch_pangaea_data([], merge_campaigns=False)
        assert result == []


class TestPangaeaPickleSaving:
    """Test PANGAEA pickle file saving functionality."""

    def test_save_pangaea_pickle_success(self, tmp_path):
        """Test successful pickle file saving."""
        data = [
            {"Campaign": "Test_Campaign", "Stations": [{"lat": 60.0, "lon": -5.0}]},
        ]
        output_file = tmp_path / "test_stations.pkl"

        save_pangaea_pickle(data, output_file)

        # Verify file was created and contains correct data
        assert output_file.exists()

        with open(output_file, "rb") as f:
            loaded_data = pickle.load(f)

        assert loaded_data == data

    def test_save_pangaea_pickle_creates_directory(self, tmp_path):
        """Test that saving creates parent directories."""
        data = [{"Campaign": "Test"}]
        output_dir = tmp_path / "nested" / "directory"
        output_file = output_dir / "test_stations.pkl"

        save_pangaea_pickle(data, output_file)

        # Verify directory was created
        assert output_dir.exists()
        assert output_file.exists()


class TestPangaeaCommand:
    """Comprehensive test suite for CLI pangaea functionality."""

    def test_main_calls_api_with_correct_params_search_mode(self):
        """Test that CLI correctly calls API layer with search parameters."""
        args = argparse.Namespace(
            query_or_file="CTD profiles",
            lat=[50.0, 60.0],
            lon=[-10.0, 0.0],
            limit=10,
            output_file=None,
            output_dir=Path("data"),
            output="pangaea_stations",
            verbose=False,
        )

        mock_stations = [{"Campaign": "Test", "Stations": [{"lat": 55.0, "lon": -5.0}]}]

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
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch(
                "cruiseplan.cli.pangaea._collect_generated_files",
                return_value=[Path("pangaea_stations.pkl")],
            ),
            patch("cruiseplan.cli.pangaea._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (mock_stations, [Path("pangaea_stations.pkl")])

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

    def test_validate_lat_lon_bounds_360_crossing_meridian(self):
        """Test coordinate bounds validation crossing 0° meridian in 360 format."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [350.0, 10.0]

        # This should be valid - crossing the 0° meridian
        result = validate_lat_lon_bounds(lat_bounds, lon_bounds)
        expected = (350.0, 50.0, 10.0, 60.0)

        assert result == expected

    def test_validate_lat_lon_bounds_mixed_format_error(self):
        """Test validation fails with mixed longitude formats."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [-10.0, 240.0]  # Mixed formats

        with pytest.raises(Exception, match="Longitude coordinates must be either"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)

    def test_validate_lat_lon_bounds_invalid_latitude_range(self):
        """Test validation fails with invalid latitude range."""
        lat_bounds = [-100.0, 60.0]  # Invalid min_lat
        lon_bounds = [-10.0, 5.0]

        with pytest.raises(Exception, match="Latitude must be between -90 and 90"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)

    def test_validate_lat_lon_bounds_invalid_latitude_ordering(self):
        """Test validation fails when min_lat >= max_lat."""
        lat_bounds = [60.0, 50.0]  # Wrong ordering
        lon_bounds = [-10.0, 5.0]

        with pytest.raises(Exception, match="min_lat must be less than max_lat"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)


class TestPangaeaDataSearch:
    """Test PANGAEA data search functionality."""

    def test_search_pangaea_datasets_success(self):
        """Test successful PANGAEA dataset search."""
        mock_manager = MagicMock()
        mock_manager.search.return_value = [
            {"doi": "10.1594/PANGAEA.12345", "Title": "Test Dataset"}
        ]

        with (
            patch("cruiseplan.cli.pangaea.PangaeaManager", return_value=mock_manager),
            patch(
                "cruiseplan.cli.pangaea.format_geographic_bounds",
                return_value="Geographic bounds: test",
            ),
            patch("cruiseplan.cli.pangaea.logger"),
        ):
            result = search_pangaea_datasets(
                "CTD profiles", (50.0, -10.0, 60.0, 5.0), 10
            )

            assert len(result) == 1
            assert result[0] == "10.1594/PANGAEA.12345"
            mock_manager.search.assert_called_once()

    def test_search_pangaea_datasets_no_results(self):
        """Test PANGAEA search with no results."""
        mock_manager = MagicMock()
        mock_manager.search.return_value = []

        with (
            patch("cruiseplan.cli.pangaea.PangaeaManager", return_value=mock_manager),
            patch(
                "cruiseplan.cli.pangaea.format_geographic_bounds",
                return_value="Geographic bounds: test",
            ),
            patch("cruiseplan.cli.pangaea.logger"),
        ):
            result = search_pangaea_datasets(
                "nonexistent query", (50.0, -10.0, 60.0, 5.0), 10
            )

            assert result == []

    def test_search_pangaea_datasets_exception(self):
        """Test PANGAEA search with manager exception."""
        mock_manager = MagicMock()
        mock_manager.search.side_effect = Exception("Search failed")

        with (
            patch("cruiseplan.cli.pangaea.PangaeaManager", return_value=mock_manager),
            patch(
                "cruiseplan.cli.pangaea.format_geographic_bounds",
                return_value="Geographic bounds: test",
            ),
            patch("cruiseplan.cli.pangaea.logger"),
        ):
            from cruiseplan.cli.cli_utils import CLIError

            with pytest.raises(CLIError, match="Search failed"):
                search_pangaea_datasets("CTD profiles", (50.0, -10.0, 60.0, 5.0), 10)


class TestDoiListSaving:
    """Test DOI list saving functionality."""

    def test_save_doi_list_success(self, tmp_path):
        """Test successful DOI list saving."""
        dois = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
        output_file = tmp_path / "dois.txt"

        save_doi_list(dois, output_file)

        assert output_file.exists()
        content = output_file.read_text()
        assert "10.1594/PANGAEA.12345" in content
        assert "10.1594/PANGAEA.67890" in content

    def test_save_empty_doi_list(self, tmp_path):
        """Test saving empty DOI list."""
        dois = []
        output_file = tmp_path / "empty_dois.txt"

        save_doi_list(dois, output_file)

        assert output_file.exists()
        content = output_file.read_text().strip()
        assert content == ""


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


class TestPangaeaUtilities:
    """Test other PANGAEA utility functions."""

    def test_module_has_required_functions(self):
        """Test that the module has all required utility functions."""
        from cruiseplan.cli import pangaea

        # These functions should exist and be callable
        assert hasattr(pangaea, "validate_dois")
        assert callable(pangaea.validate_dois)

        assert hasattr(pangaea, "fetch_pangaea_data")
        assert callable(pangaea.fetch_pangaea_data)

        assert hasattr(pangaea, "save_pangaea_pickle")
        assert callable(pangaea.save_pangaea_pickle)

        assert hasattr(pangaea, "main")
        assert callable(pangaea.main)
