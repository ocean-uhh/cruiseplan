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
21:37 (-30). Read in the current layout, the delay is part of STN_001 (the
transit keeps its length and moves), whether ``delay_start`` is stored or
taken from the gap.
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


@pytest.mark.parametrize(("name", "delay", "stn2_start"), CASES)
def test_transit_into_delayed_station_moves(name, delay, stn2_start):
    """Only the transit into STN_002 moves, by the delay."""
    path = SCHEDULES / name
    with xr.open_dataset(path) as raw:
        stored = _minutes(raw.time.values)
    schedule = read_schedule(path)
    shift = _minutes(schedule.time.values) - stored
    transit = list(schedule.name.values).index("Transit to STN_002")
    assert shift[transit] == delay
    assert np.count_nonzero(shift) == 1


@pytest.mark.parametrize(("name", "delay", "stn2_start"), CASES)
def test_records_are_contiguous(name, delay, stn2_start):
    """Each record ends where the next one starts: no gaps, no overlaps."""
    schedule = read_schedule(SCHEDULES / name)
    start = _minutes(schedule.time.values)
    end = start + np.round(schedule.duration.values).astype(np.int64)
    np.testing.assert_allclose(end[:-1], start[1:], atol=1)


@pytest.mark.parametrize(("name", "delay", "stn2_start"), CASES)
def test_delay_moves_into_the_station_before(name, delay, stn2_start):
    """The delay changes the actual duration of STN_001 by its value."""
    schedule = read_schedule(SCHEDULES / name)
    stn1 = list(schedule.name.values).index("STN_001")
    planned = float(schedule.planned_duration.values[stn1])
    actual = float(schedule.duration.values[stn1])
    assert actual - planned == pytest.approx(delay, abs=0.01)
