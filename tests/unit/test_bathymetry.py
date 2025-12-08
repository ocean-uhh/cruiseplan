import numpy as np
import pytest

from cruiseplan.data.bathymetry import BathymetryManager


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
