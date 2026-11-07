"""
Forecast headers and window checks on the pycnmix schedule.

Times in every header are UTC, as in the rows; a window that holds only a
buffer is reported; the transit-row warning is logged once.
"""

import logging
import warnings
from pathlib import Path

import pytest

import cruiseplan
from cruiseplan.api.stationplan_api import stationplan_forecast, stationplan_waypoints
from cruiseplan.forecast.generator import generate_forecast
from cruiseplan.forecast.reader import read_schedule, stored_kind

PYCNMIX = Path(__file__).parents[2] / "data" / "pycnmix-2026-v1.yaml"
ZONED = "2026-12-01T12:00:00+13:00"  # 2026-11-30 23:00 UTC


@pytest.fixture(scope="module")
def schedule_nc(tmp_path_factory):
    """NetCDF schedule of pycnmix."""
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


def _row(schedule_nc, kind, offset=0):
    """Index of the first row of *kind*, plus *offset*."""
    ds = read_schedule(schedule_nc)
    first = next(i for i in range(ds.sizes["obs"]) if stored_kind(ds, i) == kind)
    return first + offset


def test_text_header_is_utc(schedule_nc):
    """A zoned --start-time is converted in the Start_Date header."""
    index = _row(schedule_nc, "station")
    result = stationplan_forecast(schedule_nc, index, ZONED, duration_hours=3)
    assert result.success
    assert "% Start_Date = 2026/11/30 23:00 UTC" in result.output


def test_waypoints_header_is_utc(schedule_nc):
    """The waypoints start_date is the UTC time, labelled."""
    index = _row(schedule_nc, "station")
    result = stationplan_waypoints(schedule_nc, index, ZONED, 3)
    assert result.success
    assert "% start_date = 2026-11-30T23:00:00 UTC" in result.output


def test_buffer_only_window_is_an_error(schedule_nc):
    """A window holding only a buffer (and transits) is reported."""
    index = _row(schedule_nc, "buffer")
    with pytest.raises(ValueError, match="No operation starts within"):
        generate_forecast(read_schedule(schedule_nc), index, "2026-12-01T12:00", 1)


def test_far_position_names_the_transit(schedule_nc):
    """With a far current position, the error gives the transit distance."""
    index = _row(schedule_nc, "station")
    with pytest.raises(ValueError, match=r"transit from --current-position .* nm"):
        generate_forecast(
            read_schedule(schedule_nc), index, "2026-12-01T12:00", 6, (74.6, -164.3)
        )


def test_transit_row_warning_once(schedule_nc, caplog):
    """Anchoring on a transit with a current position warns once."""
    transit = _row(schedule_nc, "station", -1)
    ds = read_schedule(schedule_nc)
    position = (float(ds.latitude[transit + 1]), float(ds.longitude[transit + 1]))
    with caplog.at_level(logging.WARNING):
        result = stationplan_forecast(
            schedule_nc, transit, "2026-12-01T12:00", 6, current_position=position
        )
    assert result.success
    assert sum("is a transit" in r.getMessage() for r in caplog.records) == 1


def test_empty_window_names_one_row(schedule_nc):
    """From a transit row, the error names the anchored row and the index given."""
    transit = _row(schedule_nc, "station", -1)
    with pytest.raises(ValueError) as error:
        generate_forecast(
            read_schedule(schedule_nc), transit, "2026-12-01T12:00", 6, (74.6, -164.3)
        )
    message = str(error.value)
    assert f"from row {transit + 1} (--start-index {transit} is the transit" in message
    assert "the transit from --current-position is" in message


def test_tex_forecast_in_ship_time(schedule_nc, tmp_path):
    """With the ship's zone, the TeX rows are ship time and say so."""
    from cruiseplan.api.stationplan_api import stationplan_forecast_tex

    index = _row(schedule_nc, "station")
    local = tmp_path / "local.tex"
    utc = tmp_path / "utc.tex"
    assert stationplan_forecast_tex(schedule_nc, index, ZONED, 6, local).success
    assert stationplan_forecast_tex(
        schedule_nc, index, "2026-11-30T23:00", 6, utc
    ).success
    local_tex, utc_tex = local.read_text(), utc.read_text()
    assert "LT (UTC+13:00)" in local_tex
    assert "\\ UTC &" in utc_tex
    # The anchored operation: 12:00 ship time on 1 Dec, 23:00 UTC on 30 Nov
    assert "12:00" in local_tex
    assert "23:00" in utc_tex
    assert "01.12.2026" in local_tex
    assert "30.11.2026" in utc_tex
