"""
Schedules written before 0.6.0 keep their operation times when read.

All three files are schedules of the same three-station leg out of and
back to Reykjavik (0.5.0 key names), with a delay on STN_002:

- ``delay_mid_leg_schedule_0.5.0.nc``: ``delay_start: 90``, written by
  0.5.0, which stores the wait as a gap before STN_002 and no
  ``delay_start`` variable.
- ``delay_mid_leg_schedule_0.5.0_with_delay_start.nc``: ``delay_start: 90``,
  the 0.5.0 layout with the ``delay_start`` variable, as written after 0.5.0
  and before 0.6.0 (hours, ``dist_nm``).
- ``delay_mid_leg_negative_schedule_0.5.0.nc``: ``delay_start: -30``, written
  by 0.5.0: STN_002 starts 30 min before the transit into it ends.

The transit into STN_002 ends at 22:07; STN_002 starts at 23:37 (+90) or
21:37 (-30). Read in the current layout, no row is added or moved: a
positive delay stays the gap before STN_002 (the wait), and a negative one
shortens the transit into STN_002 so it ends when STN_002 starts.
"""

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from cruiseplan.forecast.reader import read_schedule

SCHEDULES = Path(__file__).parents[2] / "tests" / "fixtures" / "schedules"
CASES = [
    ("delay_mid_leg_schedule_0.5.0.nc", 90, "2028-06-03T23:37"),
    ("delay_mid_leg_schedule_0.5.0_with_delay_start.nc", 90, "2028-06-03T23:37"),
    ("delay_mid_leg_negative_schedule_0.5.0.nc", -30, "2028-06-03T21:37"),
]


def _minutes(values) -> np.ndarray:
    return values.astype("datetime64[m]").astype(np.int64)


@pytest.mark.parametrize(("name", "delay", "stn2_start"), CASES)
def test_operation_start_times_unchanged(name, delay, stn2_start):
    """Stations and ports start at their stored times."""
    path = SCHEDULES / name
    with xr.open_dataset(path) as raw:
        stored = _minutes(raw.time.values)
        is_op = raw.activity.values != "Transit"
    schedule = read_schedule(path)
    read = _minutes(schedule.time.values)
    np.testing.assert_array_equal(read[is_op], stored[is_op])
    stn2 = list(schedule.name.values).index("STN_002")
    assert str(schedule.time.values[stn2])[:16] == stn2_start


def _read(name):
    path = SCHEDULES / name
    with xr.open_dataset(path) as raw:
        stored = _minutes(raw.time.values)
        stored_minutes = raw.duration.values * 60.0  # 0.5.0: hours
    return stored, stored_minutes, read_schedule(path)


@pytest.mark.parametrize(("name", "delay", "stn2_start"), CASES)
def test_no_row_moves(name, delay, stn2_start):
    """Every start time, transits included, is the stored one."""
    stored, _, schedule = _read(name)
    np.testing.assert_array_equal(_minutes(schedule.time.values), stored)
    assert schedule.sizes["obs"] == len(stored)


@pytest.mark.parametrize(("name", "delay", "stn2_start"), CASES)
def test_delay_where_it_happened(name, delay, stn2_start):
    """+90: a 90 min gap before STN_002; -30: the transit into it is 30 min shorter."""
    _, stored_minutes, schedule = _read(name)
    names = list(schedule.name.values)
    transit = names.index("Transit to STN_002")
    stn2 = names.index("STN_002")
    start = _minutes(schedule.time.values)
    end = start + np.round(schedule.duration.values).astype(np.int64)
    change = float(schedule.duration.values[transit]) - stored_minutes[transit]
    gap = start[stn2] - end[transit]
    if delay > 0:
        assert change == pytest.approx(0.0, abs=0.01)
        assert gap == pytest.approx(delay, abs=1)
    else:
        assert change == pytest.approx(delay, abs=0.01)
        assert gap == pytest.approx(0, abs=1)
    stn1 = names.index("STN_001")
    assert float(schedule.duration.values[stn1]) == pytest.approx(
        stored_minutes[stn1], abs=0.01
    )


def test_delay_on_the_first_row_keeps_its_time(tmp_path):
    """A pre-0.6.0 file with delay_start 60 on the departure port: no row moves."""
    path = SCHEDULES / "delay_mid_leg_schedule_0.5.0_with_delay_start.nc"
    with xr.open_dataset(path) as raw:
        ds = raw.load()
    ds["delay_start"].values[0] = 60.0
    edited = tmp_path / "first_row_delay.nc"
    ds.to_netcdf(edited)
    stored = _minutes(ds.time.values)
    schedule = read_schedule(edited)
    np.testing.assert_array_equal(_minutes(schedule.time.values), stored)


def test_leg_start_never_before_the_previous_leg_ends():
    """An older file whose Leg2 is stored starting before Leg1 ends: no overlap."""
    import dataclasses
    import warnings
    from datetime import timedelta

    import cruiseplan
    from cruiseplan.timeline.scheduler import apply_delays

    pycnmix = Path(__file__).parents[2] / "data" / "pycnmix-2026-v1.yaml"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        timeline = cruiseplan.schedule(config_file=pycnmix, format=None).timeline
    records = [r for r in timeline if r.kind != "wait"]
    k = next(i for i, r in enumerate(records) if r.leg_name == "Leg2")
    early = records[k - 1].end_time - timedelta(hours=2)
    records[k] = dataclasses.replace(records[k], start_time=early)
    out = apply_delays(records, insert_waits=False)
    assert all(b.start_time >= a.end_time for a, b in zip(out, out[1:], strict=False))
    assert out[k].start_time == out[k - 1].end_time
