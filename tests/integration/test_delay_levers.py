"""
Delay and transit-time rules on pycnmix, the cases beyond the basic rule.

pycnmix: Leg1 Lyttelton -> Jangbogo Station, Leg2 Jangbogo -> Jangbogo
(first operation NISS, after "Transit to NISS"), Leg3 Jangbogo -> Lyttelton.
Both ports come from the ``ports:`` catalog; port records last 0 min.
"""

import csv
import logging
import math
import warnings
from pathlib import Path

import pytest
import yaml

import cruiseplan

PYCNMIX = Path(__file__).parents[2] / "data" / "pycnmix-2026-v1.yaml"


def _write(tmp_path: Path, edit) -> Path:
    cfg = yaml.safe_load(PYCNMIX.read_text())
    edit(cfg)
    path = tmp_path / "pycnmix.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return path


def _point(cfg, name):
    return next(p for p in cfg["points"] if p["name"] == name)


def _schedule(path, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cruiseplan.schedule(config_file=path, **kwargs)


def test_transit_minutes_on_a_catalog_port(tmp_path):
    """transit_minutes on a catalog port sets the transit into it."""

    def edit(cfg):
        port = next(p for p in cfg["ports"] if p["name"] == "port_jang_bogo")
        port["transit_minutes"] = 2000.0

    timeline = _schedule(_write(tmp_path, edit), format=None).timeline
    transits = [
        r
        for r in timeline
        if r.label == "Transit to Jangbogo Station" and r.leg_name == "Leg1"
    ]
    (transit,) = transits
    assert transit.duration_minutes == pytest.approx(2000.0)
    assert transit.planned_duration_minutes == pytest.approx(2576.0, abs=0.5)


def _transit_to_niss() -> float:
    """Minutes of the transit from the Leg2 departure port to NISS."""
    timeline = _schedule(PYCNMIX, format=None).timeline
    return next(r for r in timeline if r.label == "Transit to NISS").duration_minutes


def _leg_delay_cases(cfg, leg_delay):
    """NISS starts 45 min earlier than the transit in can give."""
    cfg["legs"][1]["delay_start_minutes"] = leg_delay
    _point(cfg, "NISS")["delay_start_minutes"] = -(_transit_to_niss() + 45.0)


def test_lever_splits_between_leg_delay_and_previous_leg(tmp_path, caplog):
    """Leg delay 30 min, 45 min left at the leg start: 30 from one, 15 from the other."""
    path = _write(tmp_path, lambda cfg: _leg_delay_cases(cfg, 30.0))
    with caplog.at_level(logging.WARNING):
        _schedule(path, format=None)
    (message,) = [
        r.getMessage() for r in caplog.records if "could not be" in r.getMessage()
    ]
    assert "reduce the delay_start_minutes of leg Leg2 (30 min) by 30.0 min" in message
    assert "end the previous leg (Leg1) 15.0 min earlier" in message


def test_lever_for_a_later_leg_scheduled_alone(tmp_path, caplog):
    """--leg Leg2: Leg2 starts at its given start, which is the lever."""
    path = _write(tmp_path, lambda cfg: _leg_delay_cases(cfg, 0.0))
    with caplog.at_level(logging.WARNING):
        timeline = _schedule(path, format=None, leg="Leg2").timeline
    (message,) = [
        r.getMessage() for r in caplog.records if "could not be" in r.getMessage()
    ]
    assert "start the cruise" not in message
    assert "set the start_date / start_time of leg Leg2 45.0 min earlier" in message
    assert f"{timeline[0].start_time:%Y-%m-%d %H:%M}" == "2026-03-05 12:00"


def test_lever_for_a_later_leg_without_a_given_start(tmp_path, caplog):
    """--leg Leg2 with no given start: the lever is the previous leg."""

    def edit(cfg):
        _leg_delay_cases(cfg, 0.0)
        for leg in cfg["legs"]:
            for k in ("start_date", "start_time", "end_date", "end_time"):
                leg.pop(k, None)

    with caplog.at_level(logging.WARNING):
        _schedule(_write(tmp_path, edit), format=None, leg="Leg2")
    (message,) = [
        r.getMessage() for r in caplog.records if "could not be" in r.getMessage()
    ]
    assert "start the cruise" not in message
    assert "end the previous leg 45.0 min earlier" in message


def test_transit_minutes_zero_has_no_speed(tmp_path):
    """A 0 min transit has no speed (NaN), and the CSV speeds are rounded."""

    def edit(cfg):
        _point(cfg, "NISS")["transit_minutes"] = 0.0
        _point(cfg, "LDEO_heavy_shallow_recovery")["transit_minutes"] = 60.0

    out = tmp_path / "out"
    result = _schedule(_write(tmp_path, edit), format="csv", output_dir=str(out))
    (niss,) = [r for r in result.timeline if r.label == "Transit to NISS"]
    assert niss.duration_minutes == 0.0
    assert math.isnan(niss.vessel_speed_kt)
    csv_file = next(Path(f) for f in result.files_created if str(f).endswith(".csv"))
    with csv_file.open() as f:
        speeds = [row["Vessel speed [kt]"] for row in csv.DictReader(f)]
    assert speeds
    assert all(len(s.split(".")[-1]) <= 1 for s in speeds if "." in s)


def test_wait_row_in_csv_and_netcdf(tmp_path):
    """NISS +30: a 30 min "Waiting before NISS" row in the CSV and the NetCDF."""
    import xarray as xr

    from cruiseplan.forecast.reader import read_schedule, stored_kind

    def edit(cfg):
        _point(cfg, "NISS")["delay_start_minutes"] = 30.0

    out = tmp_path / "out"
    result = _schedule(_write(tmp_path, edit), format="csv,netcdf", output_dir=str(out))
    csv_file = next(Path(f) for f in result.files_created if str(f).endswith(".csv"))
    with csv_file.open() as f:
        rows = list(csv.DictReader(f))
    labels = [row["label"] for row in rows]
    k = labels.index("Waiting before NISS")
    assert labels[k + 1] == "NISS"
    assert labels[k - 1] == "Transit to NISS"
    assert float(rows[k]["Duration [hrs]"]) == pytest.approx(0.5)
    nc = next(Path(f) for f in result.files_created if str(f).endswith(".nc"))
    ds = read_schedule(nc)
    names = [str(n) for n in ds.name.values]
    i = names.index("Waiting before NISS")
    assert stored_kind(ds, i) == "wait"
    assert float(ds.duration.values[i]) == pytest.approx(30.0)
    with xr.open_dataset(nc) as raw:
        assert str(raw.category.values[i]) == "other"


def _forecast_outputs(tmp_path, delays):
    """Schedule pycnmix with *delays*; forecast text, waypoints and PNG from Leg2."""
    from cruiseplan.api.stationplan_api import (
        stationplan_forecast,
        stationplan_forecast_png,
        stationplan_waypoints,
    )
    from cruiseplan.forecast.reader import read_schedule, stored_kind

    def edit(cfg):
        for name, minutes in delays.items():
            _point(cfg, name)["delay_start_minutes"] = minutes

    out = tmp_path / "out"
    result = _schedule(_write(tmp_path, edit), format="netcdf", output_dir=str(out))
    nc = next(Path(f) for f in result.files_created if str(f).endswith(".nc"))
    ds = read_schedule(nc)
    start = next(
        i for i in range(ds.sizes["obs"]) if stored_kind(ds, i) == "port" and i > 0
    )
    when = "2026-03-09T08:00"
    text = stationplan_forecast(nc, start, when, 48).output
    waypoints = stationplan_waypoints(nc, start, when, 48).output
    png = stationplan_forecast_png(nc, start, when, 48, tmp_path / "f.png")
    return text, waypoints, png.message


def test_forecast_outputs_with_wait_rows(tmp_path):
    """Waits are no waypoints or map points; the text codes them 1 (no work)."""
    text, waypoints, png = _forecast_outputs(tmp_path, {"NISS": 30.0})
    (tmp_path / "plain").mkdir()
    _, plain_waypoints, plain_png = _forecast_outputs(tmp_path / "plain", {})
    assert "Waiting before" not in waypoints
    assert waypoints.count("NISS") == plain_waypoints.count("NISS") == 1
    # the same number of map records with and without the wait
    assert png.split(" with ")[1] == plain_png.split(" with ")[1]
    (line,) = [row for row in text.splitlines() if "Waiting before NISS" in row]
    assert line.startswith("1,")
