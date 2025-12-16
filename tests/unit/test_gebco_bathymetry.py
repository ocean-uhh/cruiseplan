"""
Comprehensive pytest suite for BathymetryManager's GEBCO 2025 functionality.

This test suite focuses on the ensure_gebco_2025 method and covers all aspects
of downloading, extracting, and validating the GEBCO 2025 dataset without
performing actual network operations or creating large files.
"""

import zipfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from cruiseplan.data.bathymetry import (
    GEBCO_NC_FILENAME,
    BathymetryManager,
)


class TestGEBCO2025Functionality:
    """Test suite for GEBCO 2025 download and management functionality."""

    @pytest.fixture
    def test_bathymetry_dir(self, tmp_path):
        """Create a temporary test_data/bathymetry directory structure."""
        test_data_dir = tmp_path / "test_data" / "bathymetry"
        test_data_dir.mkdir(parents=True, exist_ok=True)
        return test_data_dir

    @pytest.fixture
    def bathymetry_manager(self, test_bathymetry_dir):
        """Create a BathymetryManager instance with test directory."""
        # Create manager with custom data directory to avoid using real data/bathymetry/
        manager = BathymetryManager(source="gebco2025", data_dir="test_data")
        # Override the data_dir to use our test directory
        manager.data_dir = test_bathymetry_dir
        return manager

    def test_download_skipped_if_valid(self, bathymetry_manager, test_bathymetry_dir):
        """
        Test that download is skipped if a valid GEBCO file already exists.

        Mock Path.exists() to return True and Path.stat().st_size to return 7.5 GB.
        Assert that requests.get is never called.
        """
        gebco_path = test_bathymetry_dir / GEBCO_NC_FILENAME

        # Mock file existence and valid size (7.5 GB)
        with (
            patch.object(Path, "exists") as mock_exists,
            patch.object(Path, "stat") as mock_stat,
            patch("requests.get") as mock_get,
        ):

            # Configure mocks
            mock_exists.return_value = True
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 7_500_000_000  # 7.5 GB
            mock_stat.return_value = mock_stat_obj

            # Test the method
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is True
            mock_exists.assert_called()
            mock_stat.assert_called()
            mock_get.assert_not_called()  # No download should occur

    def test_insufficient_disk_space(self, bathymetry_manager, test_bathymetry_dir):
        """Test that download is aborted when insufficient disk space is available."""
        with (
            patch.object(Path, "exists", return_value=False),
            patch("shutil.disk_usage") as mock_disk_usage,
        ):

            # Configure insufficient disk space
            mock_disk_usage_obj = MagicMock()
            mock_disk_usage_obj.free = 5_000_000_000  # Only 5 GB free (need 12 GB)
            mock_disk_usage.return_value = mock_disk_usage_obj

            # Test the method
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is False

    def test_user_cancels_download(self, bathymetry_manager, test_bathymetry_dir):
        """Test that download is aborted when user declines."""
        with (
            patch.object(Path, "exists", return_value=False),
            patch("shutil.disk_usage") as mock_disk_usage,
            patch("builtins.input", return_value="n"),
            patch("cruiseplan.data.bathymetry.tqdm") as mock_tqdm,
            patch("sys.modules") as mock_modules,
        ):

            # Remove pytest from modules to bypass test environment detection
            if "pytest" in mock_modules:
                del mock_modules["pytest"]
            if "unittest" in mock_modules:
                del mock_modules["unittest"]

            # Configure tqdm mock to return a simple context manager
            mock_tqdm_instance = MagicMock()
            mock_tqdm_instance.__enter__ = MagicMock(return_value=mock_tqdm_instance)
            mock_tqdm_instance.__exit__ = MagicMock(return_value=None)
            mock_tqdm_instance.update = MagicMock()
            mock_tqdm.return_value = mock_tqdm_instance

            # Configure sufficient disk space
            mock_disk_usage_obj = MagicMock()
            mock_disk_usage_obj.free = 15_000_000_000  # 15 GB free
            mock_disk_usage.return_value = mock_disk_usage_obj

            # Test the method
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is False

    def test_network_error_during_download(
        self, bathymetry_manager, test_bathymetry_dir
    ):
        """Test proper error handling when network download fails."""
        with (
            patch.object(Path, "exists", return_value=False),
            patch("shutil.disk_usage") as mock_disk_usage,
            patch("builtins.input", return_value="y"),
            patch("requests.get") as mock_get,
            patch.object(Path, "unlink") as mock_unlink,
            patch("cruiseplan.data.bathymetry.tqdm") as mock_tqdm,
            patch("sys.modules") as mock_modules,
        ):

            # Remove pytest from modules to bypass test environment detection
            if "pytest" in mock_modules:
                del mock_modules["pytest"]
            if "unittest" in mock_modules:
                del mock_modules["unittest"]

            # Configure tqdm mock to return a simple context manager
            mock_tqdm_instance = MagicMock()
            mock_tqdm_instance.__enter__ = MagicMock(return_value=mock_tqdm_instance)
            mock_tqdm_instance.__exit__ = MagicMock(return_value=None)
            mock_tqdm_instance.update = MagicMock()
            mock_tqdm.return_value = mock_tqdm_instance

            # Configure sufficient disk space
            mock_disk_usage_obj = MagicMock()
            mock_disk_usage_obj.free = 15_000_000_000  # 15 GB free
            mock_disk_usage.return_value = mock_disk_usage_obj

            # Configure network error
            mock_get.side_effect = requests.RequestException("Network error")

            # Test the method
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is False
            mock_get.assert_called_once()

    def test_invalid_zip_file(self, bathymetry_manager, test_bathymetry_dir):
        """Test proper error handling when zip file is corrupted."""
        with (
            patch.object(Path, "exists", return_value=False),
            patch("shutil.disk_usage") as mock_disk_usage,
            patch("builtins.input", return_value="y"),
            patch("requests.get") as mock_get,
            patch("zipfile.ZipFile") as mock_zipfile,
            patch.object(Path, "unlink") as mock_unlink,
            patch("builtins.open", mock_open()),
            patch("cruiseplan.data.bathymetry.tqdm") as mock_tqdm,
            patch("sys.modules") as mock_modules,
        ):

            # Remove pytest from modules to bypass test environment detection
            if "pytest" in mock_modules:
                del mock_modules["pytest"]
            if "unittest" in mock_modules:
                del mock_modules["unittest"]

            # Configure tqdm mock to return a simple context manager
            mock_tqdm_instance = MagicMock()
            mock_tqdm_instance.__enter__ = MagicMock(return_value=mock_tqdm_instance)
            mock_tqdm_instance.__exit__ = MagicMock(return_value=None)
            mock_tqdm_instance.update = MagicMock()
            mock_tqdm.return_value = mock_tqdm_instance

            # Configure sufficient disk space
            mock_disk_usage_obj = MagicMock()
            mock_disk_usage_obj.free = 15_000_000_000  # 15 GB free
            mock_disk_usage.return_value = mock_disk_usage_obj

            # Configure successful download
            mock_response = MagicMock()
            mock_response.headers = {"content-length": "4000000000"}
            mock_response.iter_content.return_value = [b"test"] * 100
            mock_get.return_value = mock_response
            mock_response.raise_for_status.return_value = None

            # Configure zip file error
            mock_zipfile.side_effect = zipfile.BadZipFile("Invalid zip")

            # Test the method
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is False
            # Note: unlink may not be called if zip creation fails before download completes

    def test_no_netcdf_in_zip(self, bathymetry_manager, test_bathymetry_dir):
        """Test error handling when zip doesn't contain expected NetCDF file."""
        with (
            patch.object(Path, "exists", return_value=False),
            patch("shutil.disk_usage") as mock_disk_usage,
            patch("builtins.input", return_value="y"),
            patch("requests.get") as mock_get,
            patch("zipfile.ZipFile") as mock_zipfile,
            patch("builtins.open", mock_open()),
            patch("cruiseplan.data.bathymetry.tqdm") as mock_tqdm,
            patch("sys.modules") as mock_modules,
        ):

            # Remove pytest from modules to bypass test environment detection
            if "pytest" in mock_modules:
                del mock_modules["pytest"]
            if "unittest" in mock_modules:
                del mock_modules["unittest"]

            # Configure tqdm mock to return a simple context manager
            mock_tqdm_instance = MagicMock()
            mock_tqdm_instance.__enter__ = MagicMock(return_value=mock_tqdm_instance)
            mock_tqdm_instance.__exit__ = MagicMock(return_value=None)
            mock_tqdm_instance.update = MagicMock()
            mock_tqdm.return_value = mock_tqdm_instance

            # Configure sufficient disk space
            mock_disk_usage_obj = MagicMock()
            mock_disk_usage_obj.free = 15_000_000_000  # 15 GB free
            mock_disk_usage.return_value = mock_disk_usage_obj

            # Configure successful download
            mock_response = MagicMock()
            mock_response.headers = {"content-length": "4000000000"}
            mock_response.iter_content.return_value = [b"test"] * 100
            mock_get.return_value = mock_response
            mock_response.raise_for_status.return_value = None

            # Configure zip file with no NetCDF files
            mock_zip_instance = MagicMock()
            mock_zip_instance.namelist.return_value = ["readme.txt", "metadata.xml"]
            mock_zip_instance.__enter__.return_value = mock_zip_instance
            mock_zip_instance.__exit__.return_value = None
            mock_zipfile.return_value = mock_zip_instance

            # Test the method
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is False

    def test_test_environment_detection(self, bathymetry_manager, test_bathymetry_dir):
        """Test that method returns False in test environment without prompting."""
        with patch.object(Path, "exists", return_value=False):

            # Test the method (pytest should be detected in sys.modules)
            result = bathymetry_manager.ensure_gebco_2025()

            # Assertions
            assert result is False

    def test_silent_if_exists_parameter(self, bathymetry_manager, test_bathymetry_dir):
        """Test the silent_if_exists parameter suppresses logging when file exists."""
        with (
            patch.object(Path, "exists", return_value=True),
            patch.object(Path, "stat") as mock_stat,
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
        ):

            # Configure valid file size
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 7_500_000_000  # 7.5 GB
            mock_stat.return_value = mock_stat_obj

            # Test with silent_if_exists=True
            result = bathymetry_manager.ensure_gebco_2025(silent_if_exists=True)

            # Assertions
            assert result is True
            mock_logger.info.assert_not_called()

    def test_bathymetry_manager_with_gebco_source_initialization(
        self, test_bathymetry_dir
    ):
        """Test BathymetryManager initialization with GEBCO source."""
        with patch.object(Path, "exists", return_value=False):
            # Create manager with GEBCO source
            manager = BathymetryManager(source="gebco2025", data_dir="test_data")
            manager.data_dir = test_bathymetry_dir

            # Assertions
            assert manager.source == "gebco2025"
            assert (
                manager._is_mock is True
            )  # Should be in mock mode since file doesn't exist
