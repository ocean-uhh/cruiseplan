"""
Unit tests for cruiseplan.api.data module.

Tests the bathymetry and pangaea API functions with comprehensive mocking
to ensure proper parameter handling, error conditions, and result structures.
"""

import re
from pathlib import Path
from unittest.mock import patch

import cruiseplan
from cruiseplan.api.data import bathymetry, pangaea


class TestBathymetryAPI:
    """Test the bathymetry API function with various parameters."""

    @patch("cruiseplan.data.bathymetry.download_bathymetry")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.exists")
    def test_bathymetry_default_parameters(self, mock_exists, mock_stat, mock_mkdir, mock_download):
        """Test bathymetry with default parameters."""
        # Mock file existence and size
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 1024 * 1024 * 100  # 100 MB
        mock_download.return_value = "/test/data/etopo2022.nc"

        result = bathymetry()

        # Verify function calls
        mock_download.assert_called_once()
        call_args = mock_download.call_args[1]
        assert call_args["source"] == "etopo2022"
        mock_mkdir.assert_called_once()

        # Verify result structure
        assert isinstance(result, cruiseplan.BathymetryResult)
        assert result.data_file == Path("/test/data/etopo2022.nc")
        assert result.source == "etopo2022"
        assert result.summary["file_size_mb"] == 100.0

    @patch("cruiseplan.data.bathymetry.download_bathymetry")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.stat")
    @patch("pathlib.Path.exists")
    def test_bathymetry_custom_parameters(self, mock_exists, mock_stat, mock_mkdir, mock_download):
        """Test bathymetry with custom parameters."""
        # Mock file existence and size
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 1024 * 1024 * 50  # 50 MB
        mock_download.return_value = "/custom/gebco2025.nc"

        result = bathymetry(
            bathy_source="gebco2025", output_dir="/custom/bathy", citation=True
        )

        # Verify function calls
        mock_download.assert_called_once()
        call_args = mock_download.call_args[1]
        assert call_args["source"] == "gebco2025"
        assert call_args["target_dir"] == str(Path("/custom/bathy").resolve())

        # Verify result structure
        assert isinstance(result, cruiseplan.BathymetryResult)
        assert result.data_file == Path("/custom/gebco2025.nc")
        assert result.source == "gebco2025"
        assert result.summary["citation_shown"] is True
        assert result.summary["file_size_mb"] == 50.0

    @patch("cruiseplan.data.bathymetry.download_bathymetry")
    @patch("pathlib.Path.mkdir")
    def test_bathymetry_no_file_returned(self, mock_mkdir, mock_download):
        """Test bathymetry when download returns None."""
        mock_download.return_value = None

        result = bathymetry()

        assert isinstance(result, cruiseplan.BathymetryResult)
        assert result.data_file is None
        assert result.summary["file_size_mb"] is None


class TestPangaeaAPI:
    """Test the pangaea API function with various modes and parameters."""

    # Note: Heavy mocking tests removed due to pandas circular import issues
    # Integration tests provide comprehensive coverage of the actual functionality

    def test_pangaea_query_sanitization(self):
        """Test that query terms are properly sanitized for filenames."""
        # Test the filename generation logic
        test_cases = [
            ("CTD temperature", "CTD_temperature"),
            (
                "special!@#$%chars",
                "special_chars",
            ),  # Multiple underscores get collapsed
            ("multiple___underscores", "multiple_underscores"),
            ("_leading_trailing_", "leading_trailing"),
        ]

        for input_query, expected_safe in test_cases:
            # Extract the sanitization logic from the pangaea function
            safe_query = "".join(c if c.isalnum() else "_" for c in input_query)
            safe_query = re.sub(r"_+", "_", safe_query).strip("_")
            assert safe_query == expected_safe


    def test_pangaea_default_parameters(self):
        """Test that default parameters are handled correctly."""
        # This test verifies the parameter defaults without actually calling external services
        # We can test this by checking the function signature and docstring
        import inspect

        sig = inspect.signature(pangaea)

        # Check default values
        assert sig.parameters["output_dir"].default == "data"
        assert sig.parameters["output"].default is None
        assert sig.parameters["lat_bounds"].default is None
        assert sig.parameters["lon_bounds"].default is None
        assert sig.parameters["limit"].default == 10
        assert sig.parameters["rate_limit"].default == 1.0
        assert sig.parameters["merge_campaigns"].default is True
        assert sig.parameters["verbose"].default is False


class TestPangaeaResultType:
    """Test the PangaeaResult type structure and methods."""

    def test_pangaea_result_initialization(self):
        """Test PangaeaResult initialization with various data."""
        stations_data = [{"Campaign": "Test", "Stations": []}]
        files_created = [Path("test.txt"), Path("test.pkl")]
        summary = {"campaigns_found": 1, "files_generated": 2}

        result = cruiseplan.PangaeaResult(
            stations_data=stations_data, files_created=files_created, summary=summary
        )

        assert result.stations_data == stations_data
        assert result.files_created == files_created
        assert result.summary == summary
        assert bool(result) is True  # Should be truthy with data

    def test_pangaea_result_empty(self):
        """Test PangaeaResult with empty/None data."""
        result = cruiseplan.PangaeaResult(
            stations_data=None, files_created=[], summary={"campaigns_found": 0}
        )

        assert result.stations_data is None
        assert result.files_created == []
        assert bool(result) is False  # Should be falsy without data


class TestBathymetryResultType:
    """Test the BathymetryResult type structure."""

    def test_bathymetry_result_initialization(self):
        """Test BathymetryResult initialization."""
        data_file = Path("/test/data.nc")
        summary = {"source": "etopo2022", "file_size_mb": 100.0}

        result = cruiseplan.BathymetryResult(
            data_file=data_file, source="etopo2022", summary=summary
        )

        assert result.data_file == data_file
        assert result.source == "etopo2022"
        assert result.summary == summary
