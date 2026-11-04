"""
Bathymetry grid orientation and the land (elevation >= 0) fill path.

The tests read a real GEBCO 2025 subset near Halifax
(``tests/fixtures/bathymetry/gebco2025_halifax_subset.nc``: 44.3-44.8 N,
64.0-63.3 W, ``elevation`` in m as int16, about half land and ocean to -143 m).
"""

import logging
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pytest
import yaml

import cruiseplan
import cruiseplan.data.bathymetry as bathy_module
from cruiseplan.config.values import DEFAULT_DEPTH

FIXTURES = Path(__file__).parent.parent / "fixtures"
BATHY_DIR = FIXTURES / "bathymetry"
HALIFAX_FILE = "gebco2025_halifax_subset.nc"

# Ocean point south of the Halifax approaches, at the center of a grid cell
# (cell spacing 1/240 deg), so the bilinear value is the mean of the four
# corner elevations read from the file: (-90 - 82 - 105 - 97) / 4 = -93.5 m.
OCEAN_POINT = (44.40, -63.50)
OCEAN_ELEVATION = -93.5

# Land point on the Halifax peninsula; corner elevations read from the file
# are 60, 59, 67 and 63 m, so the interpolated elevation is 62.25 m.
LAND_POINT = (44.65, -63.60)
LAND_ELEVATION = 62.25


@pytest.fixture
def halifax_source(monkeypatch):
    """Point the ``gebco2025`` source at the Halifax subset file name."""
    monkeypatch.setattr(bathy_module, "source_file", lambda source: (HALIFAX_FILE, 0.0))
    return "gebco2025"


def _write_lat_flipped_copy(path: Path) -> None:
    """Write the Halifax subset with latitude stored north to south."""
    with nc.Dataset(BATHY_DIR / HALIFAX_FILE) as src, nc.Dataset(path, "w") as dst:
        dst.createDimension("lat", src.dimensions["lat"].size)
        dst.createDimension("lon", src.dimensions["lon"].size)
        dst.createVariable("lat", "f8", ("lat",))[:] = src["lat"][::-1]
        dst.createVariable("lon", "f8", ("lon",))[:] = src["lon"][:]
        dst.createVariable("elevation", "i2", ("lat", "lon"))[:] = src["elevation"][
            ::-1, :
        ]


def test_real_subset_point_values(halifax_source):
    """The chosen ocean and land points interpolate to the values read from the file."""
    mgr = bathy_module.BathymetryManager(source=halifax_source, data_dir=str(BATHY_DIR))
    assert mgr.available and not mgr._lat_flipped
    assert mgr.get_depth_at_point(*OCEAN_POINT) == pytest.approx(OCEAN_ELEVATION)
    assert mgr.get_depth_at_point(*LAND_POINT) == pytest.approx(LAND_ELEVATION)


def test_descending_latitude_matches_ascending(halifax_source, tmp_path):
    """A north-to-south copy of the real grid returns the same depth as the original."""
    _write_lat_flipped_copy(tmp_path / HALIFAX_FILE)
    asc = bathy_module.BathymetryManager(source=halifax_source, data_dir=str(BATHY_DIR))
    desc = bathy_module.BathymetryManager(source=halifax_source, data_dir=str(tmp_path))

    assert asc.available and desc.available
    assert desc._lat_flipped and not asc._lat_flipped

    for point in (OCEAN_POINT, LAND_POINT):
        assert desc.get_depth_at_point(*point) == pytest.approx(
            asc.get_depth_at_point(*point)
        )
    assert desc.get_depth_at_point(*OCEAN_POINT) == pytest.approx(OCEAN_ELEVATION)


def test_grid_subset_descending_latitude(halifax_source, tmp_path):
    """get_grid_subset returns ascending latitudes and the original depths when flipped."""
    _write_lat_flipped_copy(tmp_path / HALIFAX_FILE)
    asc = bathy_module.BathymetryManager(source=halifax_source, data_dir=str(BATHY_DIR))
    desc = bathy_module.BathymetryManager(source=halifax_source, data_dir=str(tmp_path))

    bounds = (44.35, 44.70, -63.80, -63.40)
    xx_a, yy_a, zz_a = asc.get_grid_subset(*bounds, stride=3)
    xx_d, yy_d, zz_d = desc.get_grid_subset(*bounds, stride=3)

    assert np.all(np.diff(yy_d[:, 0]) > 0)  # latitudes returned ascending
    np.testing.assert_allclose(xx_d, xx_a)
    np.testing.assert_allclose(yy_d, yy_a)
    np.testing.assert_array_equal(np.asarray(zz_d), np.asarray(zz_a))


def _enrich_station_at(tmp_path, source: str, lat: float, lon: float) -> dict:
    """Enrich tc4 with STN_001 moved to (lat, lon) against the Halifax subset."""
    config = yaml.safe_load((FIXTURES / "tc4_mixed_ops.yaml").read_text())
    stn = next(p for p in config["points"] if p["name"] == "STN_001")
    stn["latitude"], stn["longitude"] = lat, lon
    config_file = tmp_path / "tc4_halifax.yaml"
    config_file.write_text(yaml.safe_dump(config, sort_keys=False))

    result = cruiseplan.enrich(
        config_file=config_file,
        output_dir=str(tmp_path / "out"),
        add_depths=True,
        bathy_source=source,
        bathy_dir=str(BATHY_DIR),
    )
    enriched = yaml.safe_load(Path(result.output_file).read_text())
    return next(p for p in enriched["points"] if p["name"] == "STN_001")


def test_land_point_gets_fill_depth(tmp_path, halifax_source, caplog):
    """A station over land (elevation >= 0) is set to the fill value, not abs(elevation)."""
    with caplog.at_level(logging.WARNING, logger="cruiseplan.runtime.enrichment"):
        stn = _enrich_station_at(tmp_path, halifax_source, *LAND_POINT)
    assert stn["water_depth"] == DEFAULT_DEPTH
    assert "bathymetry_source" not in stn
    assert any(
        "on land" in rec.getMessage() and "STN_001" in rec.getMessage()
        for rec in caplog.records
        if rec.levelno == logging.WARNING
    )


def test_ocean_point_gets_positive_depth(tmp_path, halifax_source):
    """A station over ocean (negative elevation) is stored as depth = -elevation."""
    stn = _enrich_station_at(tmp_path, halifax_source, *OCEAN_POINT)
    assert stn["water_depth"] == pytest.approx(-OCEAN_ELEVATION)
    assert stn["bathymetry_source"] == halifax_source
