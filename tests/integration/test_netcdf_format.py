"""
NetCDF schedule layout: CF units on every numeric variable, minutes, distance.

Schedules are written from real configs; the 0.5.0 file is a schedule of
data/pycnmix-2026-v1.yaml written before durations moved to minutes.
"""

import logging
import warnings
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

import cruiseplan
from cruiseplan.forecast.generator import generate_forecast, list_activities
from cruiseplan.forecast.reader import (
    netcdf_to_activity_records,
    read_schedule,
    to_current_format,
)

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "tests" / "fixtures"
PYCNMIX = ROOT / "data" / "pycnmix-2026-v1.yaml"
OLD_FILE = FIXTURES / "schedules" / "pycnmix-2026-v1_schedule_0.5.0.nc"

# Unit strings the writers use, all valid UDUNITS-2 (checked with cf_units
# when it is installed)
ALLOWED_UNITS = {
    "minute",
    "nautical_mile",
    "knot",
    "m",
    "degrees_north",
    "degrees_east",
}
TIME_STEPS = {"seconds", "minutes", "hours", "days"}
# Numeric variables without a physical unit (flags, counters, indices)
EXEMPT = {"duration_fill_flag", "obs", "operations", "endpoints"}


def _valid_units(units: str) -> bool:
    """True when *units* is a UDUNITS-2 unit (or, without cf_units, allowed)."""
    try:
        import cf_units
    except ImportError:
        if " since " in units:
            # CF reference time, as written for time and end_time
            step, _, origin = units.partition(" since ")
            try:
                np.datetime64(origin)
            except ValueError:
                return False
            return step in TIME_STEPS
        return units in ALLOWED_UNITS
    try:
        cf_units.Unit(units)
    except ValueError:
        return False
    return True


def _write(tmp_path: Path, config: Path, derive: bool = False) -> list[Path]:
    """Write the NetCDF schedule (and the derived files) of a config."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            result = cruiseplan.schedule(
                config_file=config,
                output_dir=str(tmp_path),
                format="netcdf,netcdf_specialized" if derive else "netcdf",
                derive_netcdf=derive,
            )
        finally:
            logging.disable(logging.NOTSET)
    return [Path(f) for f in result.files_created if str(f).endswith(".nc")]


@pytest.mark.parametrize(
    "config",
    [
        PYCNMIX,
        FIXTURES / "mooring_sequence_greenland.yaml",
        FIXTURES / "tc4_mixed_ops.yaml",
    ],
    ids=["pycnmix", "mooring_sequence", "tc4"],
)
def test_every_numeric_variable_has_valid_units(tmp_path, config):
    """Schedule and derived files: numeric variables carry UDUNITS-2 units."""
    files = _write(tmp_path, config, derive=True)
    assert len(files) >= 2
    for path in files:
        with xr.open_dataset(path, decode_times=False) as ds:
            for name, var in ds.variables.items():
                if not np.issubdtype(var.dtype, np.number) or name in EXEMPT:
                    continue
                units = var.attrs.get("units")
                assert units, f"{path.name}:{name} has no units"
                assert _valid_units(units), f"{path.name}:{name} units {units!r}"


def test_schedule_variables_and_encoding(tmp_path):
    """pycnmix: minutes, nautical miles, knots; CF times in UTC seconds."""
    (path,) = _write(tmp_path, PYCNMIX)
    with xr.open_dataset(path, decode_times=False) as raw:
        assert raw.time.attrs["units"].startswith("seconds since 1970-01-01")
        assert raw.time.attrs["calendar"] == "standard"
        assert raw.end_time.attrs["units"] == raw.time.attrs["units"]
        assert raw.duration.attrs["units"] == "minute"
        assert raw.planned_duration.attrs["units"] == "minute"
        assert raw.distance.attrs["units"] == "nautical_mile"
        assert raw.distance_to_next.attrs["units"] == "nautical_mile"
        assert raw.vessel_speed.attrs["units"] == "knot"
        assert raw.delay_start.attrs["units"] == "minute"
        assert "dist_nm" not in raw.variables
        assert raw.attrs["schedule_format"] == "0.6.0"
        # 2026-02-24 12:00 UTC (start_date with start_time 12:00)
        assert float(raw.time[0]) == pytest.approx(1771934400.0)


def test_old_format_file_reads_and_forecasts_the_same(tmp_path):
    """The 0.5.0 file (hours, dist_nm) gives the records and forecast of a new file."""
    (path,) = _write(tmp_path, PYCNMIX)
    with xr.open_dataset(OLD_FILE) as raw:
        assert raw.duration.attrs["units"] == "hour"
        assert "dist_nm" in raw.variables
    old, new = read_schedule(OLD_FILE), read_schedule(path)
    try:
        assert old.duration.attrs["units"] == "minute"
        np.testing.assert_allclose(old.duration.values, new.duration.values, atol=0.01)
        np.testing.assert_allclose(old.distance.values, new.distance.values, atol=0.01)
        old_records = netcdf_to_activity_records(old)
        new_records = netcdf_to_activity_records(new)
        for a, b in zip(old_records, new_records, strict=True):
            assert a.label == b.label
            assert a.duration_minutes == pytest.approx(b.duration_minutes, abs=0.01)
            assert a.dist_nm == pytest.approx(b.dist_nm, abs=0.01)
            assert abs((a.start_time - b.start_time).total_seconds()) < 1
        assert [r[:3] for r in list_activities(old)] == [
            r[:3] for r in list_activities(new)
        ]
        f_old = generate_forecast(old, 12, "2026-03-09T08:00:00", 48)
        f_new = generate_forecast(new, 12, "2026-03-09T08:00:00", 48)
        assert [r[0] for r in f_old] == [r[0] for r in f_new]
        for a, b in zip(f_old, f_new, strict=True):
            assert abs((a[1] - b[1]).total_seconds()) < 1
            assert a[5] == pytest.approx(b[5], abs=1e-3)  # hours
    finally:
        old.close()
        new.close()


def test_forecast_reads_units_from_the_attribute(tmp_path):
    """A duration without units is refused; seconds are converted, not assumed."""
    (path,) = _write(tmp_path, PYCNMIX)
    with xr.open_dataset(path) as ds:
        ds = ds.load()
    no_units = ds.copy()
    no_units["duration"].attrs.pop("units")
    with pytest.raises(ValueError, match="no units attribute"):
        to_current_format(no_units)
    seconds = ds.copy()
    seconds["duration"] = (ds.duration * 60.0).assign_attrs(units="seconds")
    np.testing.assert_allclose(
        to_current_format(seconds).duration.values, ds.duration.values
    )
