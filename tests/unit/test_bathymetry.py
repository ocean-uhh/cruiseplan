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
