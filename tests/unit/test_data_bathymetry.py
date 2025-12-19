# Note: You need to mock the Path object used inside the Manager constructor
from pathlib import Path
from unittest.mock import MagicMock, patch

import netCDF4 as nc
import numpy as np
import pytest
import requests

from cruiseplan.data.bathymetry import BathymetryManager, download_bathymetry
from cruiseplan.utils.constants import FALLBACK_DEPTH


@pytest.fixture
def mock_netcdf_data():
    """
    Returns mock coordinate data and a mock netCDF4.Dataset object.
    Grid: Lats 40-44 (5 points), Lons -50 to -46 (5 points). 1-degree spacing.
    Depth formula (Mock): Z = -(lat * 10 + lon * 1)
    """
    lats = np.linspace(40.0, 44.0, 5)  # [40, 41, 42, 43, 44]
    lons = np.linspace(-50.0, -46.0, 5)  # [-50, -49, -48, -47, -46]

    # Define a robust mock for the 'z' variable slicing
    def mock_z_access(indices):
        if isinstance(indices, tuple) and len(indices) == 2:
            y_indices = indices[0]
            x_indices = indices[1]

            # Handle both list indexing and slice indexing
            if isinstance(y_indices, list) and isinstance(x_indices, list):
                # New style: [[y0, y1], [x0, x1]] - Advanced indexing for 2x2 grid
                depths = np.zeros((len(y_indices), len(x_indices)))
                for i, y_idx in enumerate(y_indices):
                    for j, x_idx in enumerate(x_indices):
                        depths[i, j] = -(lats[y_idx] * 10 + lons[x_idx] * 1)
                return depths
            elif isinstance(y_indices, slice) and isinstance(x_indices, slice):
                # Slice indexing for grid subsets
                y_start, y_stop, y_step = y_indices.indices(len(lats))
                x_start, x_stop, x_step = x_indices.indices(len(lons))

                y_range = range(y_start, y_stop, y_step or 1)
                x_range = range(x_start, x_stop, x_step or 1)

                depths = np.zeros((len(y_range), len(x_range)))
                for i, y_idx in enumerate(y_range):
                    for j, x_idx in enumerate(x_range):
                        depths[i, j] = -(lats[y_idx] * 10 + lons[x_idx] * 1)
                return depths

        # Fallback for unexpected indexing patterns
        return np.array([[0]])

    mock_z_var = MagicMock()
    # The lambda function handles the complex tuple indexing from netCDF4 slicing
    mock_z_var.__getitem__.side_effect = lambda indices: mock_z_access(indices)

    mock_ds = MagicMock(spec=nc.Dataset)
    mock_ds.variables = {"lat": lats, "lon": lons, "z": mock_z_var}
    mock_ds.isopen.return_value = True
    return mock_ds


@pytest.fixture
def real_mode_manager(mock_netcdf_data):
    """Returns a BathymetryManager forced into REAL mode."""
    # 1. Patch Path.exists() to return True
    with patch.object(Path, "exists", return_value=True):
        # 2. Mock file size check to return a valid size
        mock_stat = MagicMock()
        mock_stat.st_size = 500 * 1024 * 1024  # 500 MB (valid ETOPO size)
        with patch.object(Path, "stat", return_value=mock_stat):
            # 3. Patch nc.Dataset to return our mock data
            with patch(
                "cruiseplan.data.bathymetry.nc.Dataset", return_value=mock_netcdf_data
            ):
                manager = BathymetryManager()
                # 4. Manually set the internal state to the mock's arrays (since __init__ does this)
                manager._lats = mock_netcdf_data.variables["lat"]
                manager._lons = mock_netcdf_data.variables["lon"]
                manager._is_mock = False
                yield manager
                manager.close()


@pytest.fixture
def mock_bathymetry():
    """Returns a BathymetryManager forced into Mock Mode."""
    # We pass a non-existent path to force mock mode
    bm = BathymetryManager(source="non_existent_file")
    return bm


def test_mock_depth_determinism(mock_bathymetry):
    """Ensure mock data returns consistent values for the same coordinates."""
    d1 = mock_bathymetry.get_depth_at_point(47.5, -52.0)
    d2 = mock_bathymetry.get_depth_at_point(47.5, -52.0)
    assert d1 == d2
    assert isinstance(d1, float)
    assert d1 < 0  # Should be underwater


def test_grid_subset_shape(mock_bathymetry):
    """Verify 2D grid generation works and respects bounds."""
    lat_min, lat_max = 40, 50
    lon_min, lon_max = -60, -50

    # 1. Fetch grid
    xx, yy, zz = mock_bathymetry.get_grid_subset(lat_min, lat_max, lon_min, lon_max)

    # 2. Check dimensions (Mock generates 100x100 by default)
    assert xx.shape == (100, 100)
    assert yy.shape == (100, 100)
    assert zz.shape == (100, 100)

    # 3. Check value ranges
    assert np.min(xx) >= lon_min
    assert np.max(xx) <= lon_max
    assert np.min(yy) >= lat_min
    assert np.max(yy) <= lat_max


def test_out_of_bounds_handling(mock_bathymetry):
    """Ensure the system handles weird coordinates gracefully."""
    # Note: Mock mode calculates math on anything, but real mode returns -9999.
    # We test that it returns a float and doesn't crash.
    depth = mock_bathymetry.get_depth_at_point(91.0, 0.0)
    assert isinstance(depth, float)


def test_real_mode_initialization(real_mode_manager):
    """Verify REAL mode is engaged and coordinates are loaded."""
    assert real_mode_manager._is_mock is False
    assert real_mode_manager._dataset is not None
    assert real_mode_manager._lats.shape == (5,)


def test_interpolation_success(real_mode_manager):
    """Test core bilinear interpolation near a known point."""
    # Grid coordinates: Lat: 40, 41, 42, 43, 44. Lon: -50, -49, -48, -47, -46
    # We test a point in the center of the 40-41 Lat, -50 to -49 Lon cell: (40.5, -49.5)

    # Expected Z at corners:
    # Z(40, -50) = -(40*10 + -50*1) = -350
    # Z(41, -50) = -(41*10 + -50*1) = -360
    # Z(40, -49) = -(40*10 + -49*1) = -351
    # Z(41, -49) = -(41*10 + -49*1) = -361
    # Interpolated Z(40.5, -49.5) should be the average: -355.5

    depth = real_mode_manager.get_depth_at_point(40.5, -49.5)
    assert depth == pytest.approx(-355.5)


def test_interpolation_bounds_check(real_mode_manager):
    """Ensure real mode bounds checking returns FALLBACK_DEPTH."""
    # Test point outside latitude bounds
    assert real_mode_manager.get_depth_at_point(50.0, -49.0) == FALLBACK_DEPTH
    # Test point outside longitude bounds
    assert real_mode_manager.get_depth_at_point(41.0, 0.0) == FALLBACK_DEPTH


def test_get_grid_subset_real_mode(real_mode_manager):
    """
    Verify real data subsetting works and respects stride.
    The bounds are extended slightly (e.g., to 44.0001) to ensure the
    searchsorted index includes the final grid point (index 4) when slicing.
    """
    lat_min = 40.0
    lon_min = -50.0

    # FIX: Increase the max bounds by a small epsilon to force searchsorted to
    # return the exclusive index (index 5) needed for the slice [0:5:2]
    lat_max_exclusive = 44.0001
    lon_max_exclusive = (
        -45.9999
    )  # Must be > -46.0 since we're dealing with negative numbers

    # Test with stride=2. Expected indices: 0, 2, 4 -> 3 points.
    xx, yy, zz = real_mode_manager.get_grid_subset(
        lat_min, lat_max_exclusive, lon_min, lon_max_exclusive, stride=2
    )

    # Assert 3x3 shape (Success)
    assert xx.shape == (3, 3)
    assert yy.shape == (3, 3)
    assert zz.shape == (3, 3)

    # Test bounds of the returned slice (index 0 and 4)
    assert xx[0, 0] == -50.0  # First longitude
    assert yy[2, 2] == 44.0  # Last latitude (at index 4 in original array)


def test_close_method(real_mode_manager, mock_netcdf_data):
    """Ensure the close method is called on the NetCDF dataset."""
    real_mode_manager.close()
    mock_netcdf_data.close.assert_called_once()


# Patch global objects used by download_bathymetry
@patch("cruiseplan.data.bathymetry.Path.exists")
@patch("cruiseplan.data.bathymetry.Path.mkdir")
@patch("cruiseplan.data.bathymetry.Path.unlink")
@patch("cruiseplan.data.bathymetry.requests.get")
@patch("cruiseplan.data.bathymetry.tqdm")
@patch("builtins.open", new_callable=MagicMock)
def test_download_bathymetry_success_path(
    mock_open, mock_tqdm, mock_requests_get, mock_unlink, mock_mkdir, mock_exists
):
    """Tests successful download with progress bar update."""
    mock_exists.return_value = False

    # Mock response object for success
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"Content-Length": "1000"}
    # Simulate content chunks
    mock_response.iter_content.return_value = [b"a" * 100] * 10
    mock_requests_get.return_value = mock_response

    # Need to mock the Path object that gets passed to open
    mock_path_instance = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_path_instance

    download_bathymetry(target_dir="test_data")

    # Assert successful calls
    mock_requests_get.assert_called_once()
    mock_tqdm.assert_called_once()
    mock_path_instance.write.call_count == 10
    mock_unlink.assert_not_called()  # No failure, no cleanup


@patch("cruiseplan.data.bathymetry.Path.exists")
@patch("cruiseplan.data.bathymetry.Path.unlink")
@patch("cruiseplan.data.bathymetry.requests.get")
def test_download_bathymetry_failure_cleanup_and_fallback(
    mock_requests_get, mock_unlink, mock_exists
):
    """Tests failure of all URLs, cleanup, and printing manual instructions."""
    mock_exists.return_value = False

    # Mock the existence of a partial download before cleanup
    mock_unlink.side_effect = lambda: print("Cleanup attempted")

    # Set both URLs to fail with an exception
    mock_requests_get.side_effect = [
        requests.exceptions.RequestException("URL 1 failed"),
        requests.exceptions.RequestException("URL 2 failed"),
    ]

    # We must patch Path.exists inside the function call logic.
    with patch("builtins.print") as mock_print:
        download_bathymetry(target_dir="test_data")

    # Assert requests were made to both URLs
    assert mock_requests_get.call_count == 2

    # Assert cleanup (unlink) was attempted for both failures
    # Since unlink is patched, we check its calls (or the side effect if you used print)

    # Assert final fallback instructions are printed (this will be complex to test precisely
    # due to multiple print calls, so check the final, critical message)
    mock_print.assert_any_call("⛔ AUTOMATIC DOWNLOAD FAILED")


"""
Simplified additional tests to improve bathymetry.py coverage.

This test suite targets the missing coverage areas with simpler, more reliable tests.
"""

from unittest.mock import MagicMock, patch

import pytest

import cruiseplan.data.bathymetry as bathy_module
from cruiseplan.data.bathymetry import (
    ETOPO_FILENAME,
    get_bathymetry_singleton,
)


class TestBathymetrySimpleCoverage:
    """Simplified tests to improve bathymetry coverage."""

    def test_initialization_with_small_file(self, tmp_path):
        """Test initialization when bathymetry file exists but is too small."""
        # Create a small file that will be detected as incomplete
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)
        etopo_file = bathymetry_dir / ETOPO_FILENAME
        etopo_file.write_bytes(b"small file content")  # Much smaller than 450 MB

        with patch("cruiseplan.data.bathymetry.logger") as mock_logger:
            # Override the data directory to use our test path
            manager = BathymetryManager(source="etopo2022")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode due to small file
            assert manager._is_mock is True

            # Should log warning about small file
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "too small" in warning_call

    def test_initialization_with_corrupted_netcdf_file(self, tmp_path):
        """Test initialization when NetCDF file exists but is corrupted."""
        # Create a large file that passes size check but fails NetCDF loading
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)
        etopo_file = bathymetry_dir / ETOPO_FILENAME
        # Create a file larger than 450 MB (simulate with just marking it)
        large_content = b"corrupted netcdf content" * 1000000  # ~25 MB
        etopo_file.write_bytes(large_content)

        with (
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
            patch("netCDF4.Dataset", side_effect=Exception("Corrupted NetCDF")),
            patch.object(Path, "stat") as mock_stat,
        ):

            # Mock file size to be large enough
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 500 * 1024 * 1024  # 500 MB
            mock_stat.return_value = mock_stat_obj

            manager = BathymetryManager(source="etopo2022")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode due to corrupted file
            assert manager._is_mock is True

            # Should log warning about failed load
            mock_logger.warning.assert_called()

    def test_interpolation_error_handling(self):
        """Test error handling during depth interpolation."""
        manager = BathymetryManager(source="etopo2022")

        # Set up manager to not be in mock mode
        manager._is_mock = False

        # Mock _interpolate_depth to raise an exception
        with (
            patch.object(
                manager,
                "_interpolate_depth",
                side_effect=Exception("Interpolation error"),
            ),
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
        ):

            result = manager.get_depth_at_point(45.0, -60.0)

            # Should return fallback depth
            from cruiseplan.utils.constants import FALLBACK_DEPTH

            assert result == FALLBACK_DEPTH

            # Should log error
            mock_logger.error.assert_called()

    def test_initialization_with_custom_source(self, tmp_path):
        """Test initialization with custom (non-standard) source."""
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)

        with patch("cruiseplan.data.bathymetry.logger") as mock_logger:
            manager = BathymetryManager(source="custom_source")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode since custom file doesn't exist
            assert manager._is_mock is True

    def test_grid_subset_edge_cases(self):
        """Test grid subset with edge cases."""
        manager = BathymetryManager(source="etopo2022")
        manager._is_mock = False

        # Mock the dataset and coordinates
        mock_dataset = MagicMock()
        manager._dataset = mock_dataset
        manager._lats = [40.0, 50.0, 60.0]
        manager._lons = [-70.0, -60.0, -50.0]

        # Mock invalid slice conditions
        with patch("numpy.searchsorted", return_value=0):
            result = manager.get_grid_subset(35.0, 38.0, -75.0, -72.0)  # Outside bounds
            # Should handle gracefully
            assert isinstance(result, tuple)

    def test_bilinear_interpolation_edge_cases(self):
        """Test bilinear interpolation edge cases."""
        manager = BathymetryManager(source="etopo2022")
        manager._is_mock = False

        # Set up minimal coordinates
        manager._lats = [40.0, 50.0]
        manager._lons = [-70.0, -60.0]

        # Mock dataset
        mock_dataset = MagicMock()
        manager._dataset = mock_dataset
        mock_variables = MagicMock()
        mock_dataset.variables = {"z": mock_variables}

        # Test zero spacing case
        with (
            patch.object(manager, "_lats", [50.0, 50.0]),
            patch.object(manager, "_lons", [-60.0, -60.0]),
        ):
            # Should handle zero spacing gracefully
            result = manager.get_depth_at_point(50.0, -60.0)
            assert isinstance(result, float)

    def test_get_bathymetry_singleton(self):
        """Test the singleton bathymetry instance getter."""
        # Clear any existing singleton
        bathy_module._bathymetry_instance = None

        # Get singleton twice
        instance1 = get_bathymetry_singleton()
        instance2 = get_bathymetry_singleton()

        # Should be the same instance
        assert instance1 is instance2
        assert isinstance(instance1, BathymetryManager)

    def test_module_getattr_bathymetry(self):
        """Test the module __getattr__ for backwards compatibility."""
        # Clear any existing singleton
        bathy_module._bathymetry_instance = None

        # Access via __getattr__
        bathymetry_instance = bathy_module.bathymetry

        # Should return a BathymetryManager instance
        assert isinstance(bathymetry_instance, BathymetryManager)

    def test_module_getattr_invalid_attribute(self):
        """Test the module __getattr__ with invalid attribute."""
        # Should raise AttributeError for invalid attributes
        with pytest.raises(AttributeError):
            bathy_module.invalid_attribute

    def test_interpolation_bounds_edge_cases(self):
        """Test interpolation boundary conditions that might cause errors."""
        manager = BathymetryManager(source="etopo2022")
        manager._is_mock = False

        # Mock the dataset and coordinates
        mock_dataset = MagicMock()
        manager._dataset = mock_dataset
        manager._lats = [40.0, 50.0, 60.0]
        manager._lons = [-70.0, -60.0, -50.0]

        # Mock the variables
        mock_variables = MagicMock()
        mock_dataset.variables = {"z": mock_variables}

        # Test point exactly on grid boundary
        with patch.object(manager, "_interpolate_depth", return_value=-100.0):
            result = manager.get_depth_at_point(50.0, -60.0)
            assert result == -100.0

    def test_initialization_download_context(self, tmp_path):
        """Test initialization in download context (should suppress logging)."""
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)

        # Mock the stack trace to simulate download context

        mock_frame = MagicMock()
        mock_frame.name = "download_bathymetry"

        with (
            patch("traceback.extract_stack", return_value=[mock_frame] * 5),
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
        ):

            manager = BathymetryManager(source="etopo2022")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode
            assert manager._is_mock is True

            # Should not log about mock mode (download context)
            # Check that no info calls were made about mock mode
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            mock_mode_logs = [call for call in info_calls if "MOCK mode" in call]
            assert len(mock_mode_logs) == 0


"""
Comprehensive pytest suite for BathymetryManager's GEBCO 2025 functionality.

This test suite focuses on the ensure_gebco_2025 method and covers all aspects
of downloading, extracting, and validating the GEBCO 2025 dataset without
performing actual network operations or creating large files.
"""

import zipfile
from unittest.mock import MagicMock, mock_open, patch

import pytest


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
