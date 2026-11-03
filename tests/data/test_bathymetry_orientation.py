"""Bathymetry grid orientation and the land (elevation >= 0) fill path."""

from pathlib import Path

import netCDF4 as nc
import numpy as np
import pytest
import yaml

import cruiseplan
import cruiseplan.data.bathymetry as bathy_module
from cruiseplan.config.values import DEFAULT_DEPTH

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _write_grid(
    path: Path, lats: np.ndarray, lons: np.ndarray, elevation: np.ndarray
) -> None:
    """Write a minimal bathymetry netCDF with lat, lon and a ``z`` elevation grid."""
    ds = nc.Dataset(path, "w")
    try:
        ds.createDimension("lat", len(lats))
        ds.createDimension("lon", len(lons))
        ds.createVariable("lat", "f8", ("lat",))[:] = lats
        ds.createVariable("lon", "f8", ("lon",))[:] = lons
        ds.createVariable("z", "f4", ("lat", "lon"))[:] = elevation
    finally:
        ds.close()


def _elevation(lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    """Return a linear ocean elevation (negative) so bilinear interpolation is exact."""
    return -(lats[:, None] * 10 + lons[None, :])


@pytest.fixture
def grid_manager(tmp_path, monkeypatch):
    """Return a factory building a BathymetryManager over a real synthetic grid."""
    data_dir = tmp_path / "bathy"
    data_dir.mkdir(exist_ok=True)
    monkeypatch.setattr(
        bathy_module, "source_file", lambda source: (f"{source}.nc", 0.0)
    )

    def _make(lats, lons, elevation, name):
        _write_grid(data_dir / f"{name}.nc", lats, lons, elevation)
        return bathy_module.BathymetryManager(source=name, data_dir=str(data_dir))

    return _make


def test_descending_latitude_matches_ascending(grid_manager):
    """A north-to-south grid returns the same depth as its ascending equivalent."""
    lons = np.array([-50.0, -49.0, -48.0])
    lats_asc = np.array([40.0, 41.0, 42.0, 43.0])
    asc = grid_manager(lats_asc, lons, _elevation(lats_asc, lons), name="asc")

    lats_desc = lats_asc[::-1]
    desc = grid_manager(lats_desc, lons, _elevation(lats_desc, lons), name="desc")

    assert asc.available and desc.available
    assert desc._lat_flipped and not asc._lat_flipped

    point = (41.5, -49.5)
    expected = -(41.5 * 10 + -49.5)  # linear field, interpolation is exact
    assert asc.get_depth_at_point(*point) == pytest.approx(expected)
    assert desc.get_depth_at_point(*point) == pytest.approx(expected)


def test_grid_subset_descending_latitude(grid_manager):
    """get_grid_subset returns ascending coordinates and matching depths when flipped."""
    lons = np.array([-50.0, -49.0, -48.0])
    lats_desc = np.array([43.0, 42.0, 41.0, 40.0])
    mgr = grid_manager(lats_desc, lons, _elevation(lats_desc, lons), name="descsub")

    xx, yy, zz = mgr.get_grid_subset(40.0, 43.0001, -50.0, -47.9999, stride=1)
    assert np.all(np.diff(yy[:, 0]) > 0)  # latitudes returned ascending
    # z matches the analytic elevation at each returned coordinate
    np.testing.assert_allclose(np.asarray(zz), -(np.asarray(yy) * 10 + np.asarray(xx)))


def _enrich_with_grid(tmp_path, monkeypatch, elevation_fill: float, name: str) -> dict:
    """Enrich tc4 against an all-``elevation_fill`` grid covering STN_001 (45, -50)."""
    data_dir = tmp_path / "bathy"
    data_dir.mkdir(exist_ok=True)
    lats = np.array([43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0])
    lons = np.array([-52.0, -51.0, -50.0, -49.0, -48.0])
    elevation = np.full((len(lats), len(lons)), elevation_fill, dtype="f4")
    _write_grid(data_dir / f"{name}.nc", lats, lons, elevation)
    monkeypatch.setattr(
        bathy_module, "source_file", lambda source: (f"{source}.nc", 0.0)
    )
    result = cruiseplan.enrich(
        config_file=FIXTURES / "tc4_mixed_ops.yaml",
        output_dir=str(tmp_path / "out"),
        add_depths=True,
        bathy_source=name,
        bathy_dir=str(data_dir),
    )
    return yaml.safe_load(Path(result.output_file).read_text())


def test_land_point_gets_fill_depth(tmp_path, monkeypatch):
    """A station over land (elevation >= 0) is set to the fill value, not abs(elevation)."""
    enriched = _enrich_with_grid(tmp_path, monkeypatch, 50.0, name="land")
    stn = next(p for p in enriched["points"] if p["name"] == "STN_001")
    assert stn["water_depth"] == DEFAULT_DEPTH
    assert "bathymetry_source" not in stn


def test_ocean_point_gets_positive_depth(tmp_path, monkeypatch):
    """A station over ocean (negative elevation) is stored as a positive depth."""
    enriched = _enrich_with_grid(tmp_path, monkeypatch, -3000.0, name="ocean")
    stn = next(p for p in enriched["points"] if p["name"] == "STN_001")
    assert stn["water_depth"] == pytest.approx(3000.0)
    assert stn["bathymetry_source"] == "ocean"
