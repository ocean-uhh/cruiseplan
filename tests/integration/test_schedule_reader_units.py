"""
Reading schedules by their units attributes, on the pycnmix schedule.

The 0.5.0 file stores durations in hours, ``dist_nm`` and times as days
since 1970; a fresh schedule stores minutes, ``distance`` and seconds.
"""

import logging
import warnings
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

import cruiseplan
from cruiseplan.forecast.reader import (
    netcdf_to_activity_records,
    read_schedule,
    to_current_format,
)
from cruiseplan.output.netcdf_metadata import get_variable_attributes

ROOT = Path(__file__).parents[2]
OLD_FILE = (
    ROOT / "tests" / "fixtures" / "schedules" / "pycnmix-2026-v1_schedule_0.5.0.nc"
)
PYCNMIX = ROOT / "data" / "pycnmix-2026-v1.yaml"


@pytest.fixture(scope="module")
def new_file(tmp_path_factory):
    """NetCDF schedule of pycnmix in the current layout."""
    out = tmp_path_factory.mktemp("pycnmix")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            files = cruiseplan.schedule(
                config_file=PYCNMIX, output_dir=str(out), format="netcdf"
            ).files_created
        finally:
            logging.disable(logging.NOTSET)
    return next(Path(f) for f in files if str(f).endswith(".nc"))


def test_records_from_a_raw_050_dataset():
    """netcdf_to_activity_records takes an opened 0.5.0 file as it is."""
    with xr.open_dataset(OLD_FILE) as raw:
        records = netcdf_to_activity_records(raw.load())
    expected = netcdf_to_activity_records(read_schedule(OLD_FILE))
    assert [r.duration_minutes for r in records] == [
        r.duration_minutes for r in expected
    ]
    assert sum(r.duration_minutes for r in records) / 60.0 == pytest.approx(
        610.0, abs=1.0
    )


@pytest.mark.parametrize("which", ["old", "new"])
def test_undecoded_times_are_decoded(which, new_file):
    """A file opened with decode_times=False reads to the same times."""
    path = OLD_FILE if which == "old" else new_file
    with xr.open_dataset(path, decode_times=False) as raw:
        undecoded = to_current_format(raw.load())
    np.testing.assert_array_equal(
        undecoded.time.values.astype("datetime64[s]"),
        read_schedule(path).time.values.astype("datetime64[s]"),
    )


def test_distance_in_km_is_converted(new_file, tmp_path):
    """A distance stored in km is read in nautical miles."""
    with xr.open_dataset(new_file) as raw:
        ds = raw.load()
    nm = ds.distance.values.copy()
    ds["distance"] = ds.distance * 1.852
    ds["distance"].attrs["units"] = "km"
    converted = to_current_format(ds)
    np.testing.assert_allclose(converted.distance.values, nm, rtol=1e-6)
    assert converted.distance.attrs["units"] == "nautical_mile"


def test_missing_units_say_how_to_fix(new_file):
    """A physical variable without units is refused, naming the remedy."""
    with xr.open_dataset(new_file) as raw:
        ds = raw.load()
    del ds["vessel_speed"].attrs["units"]
    with pytest.raises(ValueError, match="cruiseplan schedule"):
        to_current_format(ds)


def test_written_units_match_the_metadata_table(new_file):
    """The schedule writer and the metadata table agree on every unit."""
    with xr.open_dataset(new_file, decode_times=False) as ds:
        for name, var in ds.variables.items():
            table = get_variable_attributes(name).get("units")
            if table is not None and "units" in var.attrs:
                assert var.attrs["units"] == table, name
