"""
Test suite for cruiseplan.cli.pandoi module.

This module tests the PANGAEA search CLI functionality, including latitude/longitude
validation, dataset searching, DOI list saving, and main CLI entry point.
"""

from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import pytest

from cruiseplan.cli.pandoi import (
    main,
    save_doi_list,
    search_pangaea_datasets,
    validate_lat_lon_bounds,
)
from cruiseplan.cli.utils import CLIError


class TestValidateLatLonBounds:
    """Test suite for validate_lat_lon_bounds function."""

    def test_valid_standard_format(self):
        """Test valid -180 to 180 format."""
        result = validate_lat_lon_bounds([50, 60], [-90, -30])
        assert result == (-90, 50, -30, 60)

    def test_valid_360_format(self):
        """Test valid 0 to 360 format."""
        result = validate_lat_lon_bounds([50, 60], [270, 330])
        assert result == (270, 50, 330, 60)

    def test_valid_360_crossing_meridian(self):
        """Test valid 0-360 format crossing 0° meridian."""
        result = validate_lat_lon_bounds([50, 60], [350, 10])
        assert result == (350, 50, 10, 60)

    def test_mixed_format_error(self):
        """Test mixed longitude formats are rejected."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [-90, 240])

        assert "Cannot mix formats" in str(excinfo.value)
        assert "-180 to 180 format" in str(excinfo.value)
        assert "0 to 360 format" in str(excinfo.value)

    def test_invalid_latitude_range(self):
        """Test invalid latitude values."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([-100, 50], [-90, -30])
        assert "Latitude must be between -90 and 90" in str(excinfo.value)

        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 100], [-90, -30])
        assert "Latitude must be between -90 and 90" in str(excinfo.value)

    def test_invalid_latitude_ordering(self):
        """Test invalid latitude ordering (min >= max)."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([60, 50], [-90, -30])
        assert "min_lat must be less than max_lat" in str(excinfo.value)

    def test_invalid_longitude_standard_format(self):
        """Test invalid longitude values in standard format."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [-200, -30])
        assert "Cannot mix formats" in str(excinfo.value)

        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [-90, 200])
        assert "Cannot mix formats" in str(excinfo.value)

    def test_invalid_longitude_360_format(self):
        """Test invalid longitude values in 360 format."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [-10, 330])
        assert "Cannot mix formats" in str(excinfo.value)

        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [270, 380])
        assert "Cannot mix formats" in str(excinfo.value)

    def test_invalid_longitude_ordering_standard(self):
        """Test invalid longitude ordering in standard format."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [-30, -90])
        assert "min_lon must be less than max_lon" in str(excinfo.value)

    def test_invalid_longitude_ordering_360_normal(self):
        """Test invalid longitude ordering in 360 format (normal case)."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [330, 270])
        assert "min_lon must be less than max_lon" in str(excinfo.value)

    def test_edge_cases_latitude(self):
        """Test edge cases for latitude bounds."""
        # Exact bounds should work
        result = validate_lat_lon_bounds([-90, 90], [0, 360])
        assert result == (0, -90, 360, 90)

        # Single degree range should work
        result = validate_lat_lon_bounds([50, 51], [0, 1])
        assert result == (0, 50, 1, 51)

    def test_edge_cases_longitude(self):
        """Test edge cases for longitude bounds."""
        # Exact 180 format bounds
        result = validate_lat_lon_bounds([50, 60], [-180, 180])
        assert result == (-180, 50, 180, 60)

        # Exact 360 format bounds
        result = validate_lat_lon_bounds([50, 60], [0, 360])
        assert result == (0, 50, 360, 60)

    def test_index_error_handling(self):
        """Test handling of insufficient lat/lon values."""
        with pytest.raises(CLIError):
            validate_lat_lon_bounds([50], [-90, -30])

        with pytest.raises(CLIError):
            validate_lat_lon_bounds([50, 60], [-90])

        with pytest.raises(CLIError):
            validate_lat_lon_bounds([], [-90, -30])


class TestSearchPangaeaDatasets:
    """Test suite for search_pangaea_datasets function."""

    @patch("cruiseplan.cli.pandoi.PangaeaManager")
    def test_successful_search_with_bbox(self, mock_manager_class):
        """Test successful search with bounding box."""
        # Mock the manager instance and its search method
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = [
            {"doi": "10.1594/PANGAEA.123456"},
            {"doi": "10.1594/PANGAEA.789012"},
        ]

        result = search_pangaea_datasets(query="CTD", bbox=(-90, 50, -30, 60), limit=10)

        assert result == ["10.1594/PANGAEA.123456", "10.1594/PANGAEA.789012"]
        mock_manager.search.assert_called_once_with(
            query="CTD", bbox=(-90, 50, -30, 60), limit=10
        )

    @patch("cruiseplan.cli.pandoi.PangaeaManager")
    def test_successful_search_without_bbox(self, mock_manager_class):
        """Test successful search without bounding box."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = [{"doi": "10.1594/PANGAEA.123456"}]

        result = search_pangaea_datasets(query="temperature", limit=5)

        assert result == ["10.1594/PANGAEA.123456"]
        mock_manager.search.assert_called_once_with(
            query="temperature", bbox=None, limit=5
        )

    @patch("cruiseplan.cli.pandoi.PangaeaManager")
    def test_search_no_results(self, mock_manager_class):
        """Test search with no results."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = []

        result = search_pangaea_datasets(query="nonexistent", limit=10)

        assert result == []

    @patch("cruiseplan.cli.pandoi.PangaeaManager")
    def test_search_results_without_doi(self, mock_manager_class):
        """Test search results that don't have DOI field."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.return_value = [
            {"doi": "10.1594/PANGAEA.123456"},
            {"title": "Dataset without DOI"},  # No DOI field
            {"doi": None},  # DOI is None
            {"doi": "10.1594/PANGAEA.789012"},
        ]

        result = search_pangaea_datasets(query="CTD", limit=10)

        # Should only return datasets with valid DOIs
        assert result == ["10.1594/PANGAEA.123456", "10.1594/PANGAEA.789012"]

    @patch("cruiseplan.cli.pandoi.PangaeaManager")
    def test_search_manager_exception(self, mock_manager_class):
        """Test handling of PangaeaManager exceptions."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.search.side_effect = Exception("API error")

        with pytest.raises(CLIError) as excinfo:
            search_pangaea_datasets(query="CTD", limit=10)

        assert "Search failed: API error" in str(excinfo.value)

    @patch("cruiseplan.cli.pandoi.PangaeaManager")
    def test_search_manager_instantiation_exception(self, mock_manager_class):
        """Test handling of PangaeaManager instantiation exceptions."""
        mock_manager_class.side_effect = Exception("Manager init failed")

        with pytest.raises(CLIError) as excinfo:
            search_pangaea_datasets(query="CTD", limit=10)

        assert "Search failed: Manager init failed" in str(excinfo.value)


class TestSaveDoiList:
    """Test suite for save_doi_list function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_save_doi_list_success(self, mock_mkdir, mock_file):
        """Test successful DOI list saving."""
        dois = ["10.1594/PANGAEA.123456", "10.1594/PANGAEA.789012"]
        output_path = Path("/tmp/test_dois.txt")

        save_doi_list(dois, output_path)

        # Check that parent directory creation was attempted
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Check file operations
        mock_file.assert_called_once_with(output_path, "w")
        handle = mock_file()
        expected_calls = [
            call("10.1594/PANGAEA.123456\n"),
            call("10.1594/PANGAEA.789012\n"),
        ]
        handle.write.assert_has_calls(expected_calls)

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_save_empty_doi_list(self, mock_mkdir, mock_file):
        """Test saving empty DOI list."""
        dois = []
        output_path = Path("/tmp/empty_dois.txt")

        save_doi_list(dois, output_path)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once_with(output_path, "w")
        # File should be opened but no writes should happen
        mock_file().write.assert_not_called()

    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    @patch("pathlib.Path.mkdir")
    def test_save_doi_list_permission_error(self, mock_mkdir, mock_file):
        """Test handling of permission errors during file save."""
        dois = ["10.1594/PANGAEA.123456"]
        output_path = Path("/restricted/test_dois.txt")

        with pytest.raises(CLIError) as excinfo:
            save_doi_list(dois, output_path)

        assert "Failed to save DOI list: Permission denied" in str(excinfo.value)

    @patch("pathlib.Path.mkdir", side_effect=OSError("Cannot create directory"))
    def test_save_doi_list_mkdir_error(self, mock_mkdir):
        """Test handling of directory creation errors."""
        dois = ["10.1594/PANGAEA.123456"]
        output_path = Path("/tmp/test_dois.txt")

        with pytest.raises(CLIError) as excinfo:
            save_doi_list(dois, output_path)

        assert "Failed to save DOI list: Cannot create directory" in str(excinfo.value)


class TestPandoiMain:
    """Test suite for main CLI function."""

    def _create_mock_args(
        self,
        query="CTD",
        lat=None,
        lon=None,
        limit=10,
        output_file=None,
        output_dir=Path("data"),
        verbose=False,
    ):
        """Create mock arguments for testing."""
        mock_args = MagicMock()
        mock_args.query = query
        mock_args.lat = lat
        mock_args.lon = lon
        mock_args.limit = limit
        mock_args.output_file = output_file
        mock_args.output_dir = output_dir
        mock_args.verbose = verbose
        return mock_args

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_successful_search_with_bbox(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test successful main execution with bounding box."""
        mock_args = self._create_mock_args(
            query="CTD", lat=[50, 60], lon=[-90, -30], limit=20
        )
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        main(mock_args)

        mock_setup_logging.assert_called_once_with(verbose=False)
        mock_search.assert_called_once_with(
            query="CTD", bbox=(-90, 50, -30, 60), limit=20
        )
        expected_path = Path("data") / "CTD_dois.txt"
        mock_save.assert_called_once_with(["10.1594/PANGAEA.123456"], expected_path)

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_successful_search_without_bbox(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test successful main execution without bounding box."""
        mock_args = self._create_mock_args(query="temperature")
        mock_search.return_value = ["10.1594/PANGAEA.789012"]

        main(mock_args)

        mock_search.assert_called_once_with(query="temperature", bbox=None, limit=10)
        expected_path = Path("data") / "temperature_dois.txt"
        mock_save.assert_called_once_with(["10.1594/PANGAEA.789012"], expected_path)

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("pathlib.Path.mkdir")
    def test_main_no_results_found(self, mock_mkdir, mock_search, mock_setup_logging):
        """Test main execution when no results are found."""
        mock_args = self._create_mock_args(query="nonexistent")
        mock_search.return_value = []

        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)

        assert excinfo.value.code == 1
        mock_search.assert_called_once_with(query="nonexistent", bbox=None, limit=10)

    @patch("cruiseplan.cli.pandoi.setup_logging")
    def test_main_invalid_limit_zero(self, mock_setup_logging):
        """Test main with invalid limit (zero)."""
        mock_args = self._create_mock_args(limit=0)

        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)

        assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    def test_main_invalid_limit_negative(self, mock_setup_logging):
        """Test main with invalid limit (negative)."""
        mock_args = self._create_mock_args(limit=-5)

        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)

        assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_large_limit_warning(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging, caplog
    ):
        """Test main with large limit shows warning."""
        mock_args = self._create_mock_args(limit=150)
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        with caplog.at_level("WARNING"):
            main(mock_args)

        # Check that warning about large limit was logged
        assert any(
            "Large limit values may result in slow searches" in record.message
            for record in caplog.records
        )

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_with_custom_output_file(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test main execution with custom output file."""
        custom_path = Path("/tmp/custom_dois.txt")
        mock_args = self._create_mock_args(output_file=custom_path)
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        main(mock_args)

        mock_save.assert_called_once_with(["10.1594/PANGAEA.123456"], custom_path)

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_query_filename_sanitization(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test that query strings are properly sanitized for filenames."""
        mock_args = self._create_mock_args(query="CTD temperature & salinity!")
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        main(mock_args)

        # Special characters should be replaced with single underscores (collapsed)
        expected_path = Path("data") / "CTD_temperature_salinity_dois.txt"
        mock_save.assert_called_once_with(["10.1594/PANGAEA.123456"], expected_path)

    @patch("cruiseplan.cli.pandoi.setup_logging")
    def test_main_invalid_lat_lon_bounds(self, mock_setup_logging):
        """Test main with invalid lat/lon bounds."""
        mock_args = self._create_mock_args(lat=[50, 60], lon=[-90, 240])  # Mixed format

        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)

        assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    def test_main_incomplete_lat_lon_bounds(self, mock_setup_logging):
        """Test main with only lat or only lon provided."""
        # Test with only lat provided
        mock_args = self._create_mock_args(lat=[50, 60], lon=None)
        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)
        assert excinfo.value.code == 1

        # Test with only lon provided
        mock_args = self._create_mock_args(lat=None, lon=[-90, -30])
        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)
        assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    def test_main_search_exception(self, mock_search, mock_setup_logging):
        """Test main handling of search exceptions."""
        mock_args = self._create_mock_args()
        mock_search.side_effect = CLIError("Search failed")

        with pytest.raises(SystemExit) as excinfo:
            main(mock_args)

        assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    def test_main_keyboard_interrupt(self, mock_setup_logging):
        """Test main handling of keyboard interrupt."""
        mock_args = self._create_mock_args()

        with patch("cruiseplan.cli.pandoi.search_pangaea_datasets") as mock_search:
            mock_search.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    def test_main_unexpected_exception(self, mock_setup_logging):
        """Test main handling of unexpected exceptions."""
        mock_args = self._create_mock_args()

        with patch("cruiseplan.cli.pandoi.search_pangaea_datasets") as mock_search:
            mock_search.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            assert excinfo.value.code == 1

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_verbose_logging(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test main with verbose logging enabled."""
        mock_args = self._create_mock_args(verbose=True)
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        main(mock_args)

        mock_setup_logging.assert_called_once_with(verbose=True)

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_with_360_longitude_format(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test main with 0-360 longitude format."""
        mock_args = self._create_mock_args(lat=[50, 60], lon=[270, 330])
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        main(mock_args)

        mock_search.assert_called_once_with(
            query="CTD", bbox=(270, 50, 330, 60), limit=10
        )

    @patch("cruiseplan.cli.pandoi.setup_logging")
    @patch("cruiseplan.cli.pandoi.search_pangaea_datasets")
    @patch("cruiseplan.cli.pandoi.save_doi_list")
    @patch("pathlib.Path.mkdir")
    def test_main_crossing_meridian_360_format(
        self, mock_mkdir, mock_save, mock_search, mock_setup_logging
    ):
        """Test main with 0-360 format crossing 0° meridian."""
        mock_args = self._create_mock_args(lat=[50, 60], lon=[350, 10])
        mock_search.return_value = ["10.1594/PANGAEA.123456"]

        main(mock_args)

        mock_search.assert_called_once_with(
            query="CTD", bbox=(350, 50, 10, 60), limit=10
        )
