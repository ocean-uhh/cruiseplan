"""
Forecast (at-sea re-anchoring) against hand-calculated schedules.

Rule under test (``generate_forecast`` docstring): the operation at
``start_index`` starts at ``start_time`` (a transit row anchors on the
operation it leads to); with a current position, a transit from it comes
first; every later row keeps its planned offset. Expected values come from
``hand_calc`` (``hand_schedule``, ``hand_forecast``), not from the code.
"""

import importlib
import logging
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import xarray as xr
import yaml
from hand_calc import gc_nm, hand_anchor, hand_forecast, hand_schedule

import cruiseplan
from cruiseplan.forecast.generator import generate_forecast
from cruiseplan.forecast.reader import netcdf_to_activity_records, read_schedule
from cruiseplan.utils.units import round_to_minutes

cli_main = importlib.import_module("cruiseplan.cli.main")
ROOT = Path(__file__).parent.parent.parent
CONFIGS = {
    "pycnmix": ROOT / "data" / "pycnmix-2026-v1.yaml",
    "coldsnap": ROOT / "tests" / "fixtures" / "coldsnap-2028-newformat.yaml",
    "tc2_two_legs": ROOT / "tests" / "fixtures" / "tc2_two_legs.yaml",
}
T_TOL_S = 30.0
SHIFT = timedelta(hours=3)


def load(name: str) -> dict:
    """Read a config with yaml.safe_load (not through cruiseplan)."""
    return yaml.safe_load(CONFIGS[name].read_text())


def netcdf_for(tmp_path: Path, cfg: dict, stem: str) -> Path:
    """Write cfg to tmp_path and schedule it to NetCDF."""
    path = tmp_path / f"{stem}.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            files = cruiseplan.schedule(
                config_file=path, output_dir=str(tmp_path / stem), format="netcdf"
            ).files_created
        finally:
            logging.disable(logging.NOTSET)
    return next(Path(f) for f in files if str(f).endswith(".nc"))


_DATASETS: dict[Path, object] = {}


def forecast_rows(
    nc_path: Path,
    index: int,
    start: datetime,
    hours: float = 1e6,
    position: tuple[float, float] | None = None,
) -> list[tuple]:
    """Forecast rows from generate_forecast."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if nc_path not in _DATASETS:
            _DATASETS[nc_path] = read_schedule(nc_path).load()
        return generate_forecast(
            _DATASETS[nc_path], index, start.isoformat(), hours, position
        )


def forecast(nc_path: Path, index: int, start: datetime, hours: float = 1e6, **kw):
    """Forecast rows as {original index: start time}."""
    return {row[0]: row[1] for row in forecast_rows(nc_path, index, start, hours, **kw)}


def anchors(n: int) -> range:
    """Anchor indices: all of them, thinned to about 40 for long schedules."""
    return range(0, n, max(1, n // 40))


def seconds(a: datetime, b: datetime) -> float:
    """Absolute difference in seconds."""
    return abs((a - b).total_seconds())


def index_of(hand: list, label: str, nth: int = 0) -> int:
    """Index of the nth hand row with this label (same order as the NetCDF)."""
    return [i for i, r in enumerate(hand) if r.name == label][nth]


# =============================================================================
# Consistency across anchors
# =============================================================================


@pytest.mark.parametrize("name", list(CONFIGS))
def test_anchor_at_original_time_reproduces_schedule(tmp_path, name):
    """From every index i at the hand start of its anchor, later rows get their hand start."""
    cfg = load(name)
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, name)
    worst = 0.0
    for i in anchors(len(hand)):
        k = hand_anchor(hand, i)
        fc = forecast(nc_path, i, hand[k].start)
        assert sorted(fc) == list(range(k, len(hand)))
        worst = max(worst, *(seconds(t, hand[j].start) for j, t in fc.items()))
    assert worst <= T_TOL_S


@pytest.mark.parametrize("name", list(CONFIGS))
def test_shifted_anchor_shifts_everything(tmp_path, name):
    """Anchor i at its anchor's hand start + 3 h: every later row is hand + 3 h."""
    cfg = load(name)
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, name)
    for i in anchors(len(hand)):
        fc = forecast(nc_path, i, hand[hand_anchor(hand, i)].start + SHIFT)
        for j, t in fc.items():
            assert seconds(t, hand[j].start + SHIFT) <= T_TOL_S, (i, j)


@pytest.mark.parametrize("name", list(CONFIGS))
def test_anchors_i_and_i_plus_k_agree(tmp_path, name):
    """Forecasts from i, i+1, i+2 (each at its own shifted start) agree on later ops."""
    cfg = load(name)
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, name)
    for i in anchors(len(hand) - 2):
        runs = [
            forecast(nc_path, i + k, hand[hand_anchor(hand, i + k)].start + SHIFT, 72)
            for k in range(3)
        ]
        common = set(runs[0]) & set(runs[1]) & set(runs[2])
        for j in common:
            assert seconds(runs[0][j], runs[1][j]) < 1
            assert seconds(runs[0][j], runs[2][j]) < 1


@pytest.mark.parametrize("name", list(CONFIGS))
def test_transit_row_anchors_on_its_operation(tmp_path, name):
    """A transit row i and the operation i+1 give the same forecast at the same T."""
    cfg = load(name)
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, name)
    t0 = datetime(2026, 3, 9, 8, 0)
    transits = [i for i, r in enumerate(hand) if r.kind == "transit"]
    for i in transits[:: max(1, len(transits) // 20)]:
        assert forecast_rows(nc_path, i, t0, 72) == forecast_rows(
            nc_path, i + 1, t0, 72
        )
        expected = hand_forecast(hand, i, t0)
        fc = forecast(nc_path, i, t0)
        assert sorted(fc) == [r.index for r in expected]
        for r in expected:
            assert seconds(fc[r.index], r.start) <= T_TOL_S


def test_anchor_on_transit_versus_on_station(tmp_path, caplog):
    """
    Same start time, anchored on 'Transit to NISS' versus on NISS itself.

    Both put NISS at T: the ship is at NISS. The transit row anchors on NISS
    and says so in a warning.
    """
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    k_tr = index_of(hand, "Transit to NISS")
    k_op = index_of(hand, "NISS")
    assert k_op == k_tr + 1
    t0 = datetime(2026, 3, 9, 8, 0)
    with caplog.at_level(logging.WARNING, logger="cruiseplan.forecast.generator"):
        from_transit = forecast(nc_path, k_tr, t0)
    assert f"anchoring on index {k_op} ('NISS')" in caplog.text
    from_op = forecast(nc_path, k_op, t0)
    assert k_tr not in from_transit
    assert from_transit == from_op
    assert from_op[k_op] == t0


def test_her_i_versus_i_plus_2(tmp_path):
    """
    Anchor 12 (NISS) and 14 (LDEO_heavy_shallow_recovery), each at its own
    planned start + 3 h, agree on row 16; anchor 11 (the transit) now does too.
    """
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    assert [hand[i].name for i in (11, 12, 14, 16)] == [
        "Transit to NISS",
        "NISS",
        "LDEO_heavy_shallow_recovery",
        "Transit to LDEO_heavy_deep_recovery",
    ]
    row16 = {i: forecast(nc_path, i, hand[12].start + SHIFT)[16] for i in (11, 12)}
    row16[14] = forecast(nc_path, 14, hand[14].start + SHIFT)[16]
    for t in row16.values():
        assert seconds(t, hand[16].start + SHIFT) <= T_TOL_S


@pytest.mark.parametrize("index_label", ["Transit to NISS", "NISS"])
def test_current_position_sets_transit(tmp_path, index_label):
    """Ship between Jang Bogo and NISS at T: NISS starts T + gc(P, NISS) / 10 kt."""
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    k = index_of(hand, index_label)
    k_op = index_of(hand, "NISS")
    t0 = datetime(2026, 3, 9, 8, 0)
    here = (-74.98, 163.48)  # on the way from Jang Bogo to NISS
    nm = gc_nm(here, (-75.14, 163.42))
    assert nm == pytest.approx(9.65, abs=0.01)
    rows = forecast_rows(nc_path, k, t0, position=here)
    first = rows[0]
    assert first[0] == -1
    assert first[1] == t0
    assert first[2] == "transit"
    assert first[8] == "Transit to NISS"
    assert first[5] * 60 == pytest.approx(nm * 6, abs=0.5)
    fc = {row[0]: row[1] for row in rows}
    assert seconds(fc[k_op], t0 + timedelta(minutes=nm * 6)) <= T_TOL_S
    expected = hand_forecast(hand, k, t0, position=here)
    assert [r[0] for r in rows] == [r.index for r in expected]
    for row, r in zip(rows, expected, strict=True):
        assert seconds(row[1], r.start) <= T_TOL_S
        assert row[5] * 60 == pytest.approx(r.minutes, abs=0.5)


def test_current_position_shortens_window(tmp_path):
    """The current-position transit takes time out of the window, in every format."""
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    k_op = index_of(hand, "NISS")
    t0 = datetime(2026, 3, 9, 8, 0)
    here = (-74.98, 163.48)
    expected = hand_forecast(hand, k_op, t0, position=here)
    # window ends 1 min before the hand start of LDEO_heavy_shallow_deployment
    k_dep = index_of(hand, "LDEO_heavy_shallow_deployment")
    t_dep = next(r.start for r in expected if r.index == k_dep)
    hours = ((t_dep - t0).total_seconds() / 60 - 1) / 60
    with_pos = forecast(nc_path, k_op, t0, hours, position=here)
    without = forecast(nc_path, k_op, t0, hours)
    assert k_dep not in with_pos
    assert k_dep in without
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wp = cruiseplan.stationplan_waypoints(
            schedule_file=nc_path,
            start_index=k_op,
            start_time=t0.isoformat(),
            duration_hours=hours,
            current_position=here,
        )
    assert wp.success
    assert "LDEO_heavy_shallow_recovery" in wp.output
    assert "LDEO_heavy_shallow_deployment" not in wp.output
    assert wp.output.splitlines()[6] == "1\t74 58.80 S\t163 28.80 E\tMerian"


def test_current_position_in_text_and_tex(tmp_path):
    """Text lists the transit from P; TeX prints NISS at T + 57.9 min (rounded 09:00)."""
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    k_op = index_of(hand, "NISS")
    here = (-74.98, 163.48)
    minutes = gc_nm(here, (-75.14, 163.42)) * 6
    assert minutes == pytest.approx(57.9, abs=0.05)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        text = cruiseplan.stationplan_forecast(
            nc_path, k_op, "2026-03-09T08:00:00", 6, current_position=here
        )
        out = tmp_path / "plan.tex"
        tex = cruiseplan.stationplan_forecast_tex(
            nc_path,
            k_op,
            "2026-03-09T08:00:00",
            6,
            output_path=out,
            current_position=here,
        )
    assert text.success
    lines = [line for line in text.output.splitlines() if not line.startswith("%")]
    lines = [line for line in lines if line]
    assert (
        lines[0] == f"1, 74 58.800 S, 163 28.800 E, Transit to NISS, {minutes / 60:.1f}"
    )
    assert lines[1].split(", ")[3] == "NISS"
    assert tex.success
    row = next(line for line in out.read_text().splitlines() if "& NISS &" in line)
    assert row.startswith("09:00")


def test_current_position_in_kml_and_png(tmp_path, monkeypatch):
    """KML and PNG take their times from the same re-timed forecast."""
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    k_op = index_of(hand, "NISS")
    t0 = datetime(2026, 3, 9, 8, 0)
    here = (-74.98, 163.48)
    t_niss = t0 + timedelta(minutes=gc_nm(here, (-75.14, 163.42)) * 6)
    captured = {}

    def capture_map(timeline, output_file, **_kwargs):
        captured["timeline"] = timeline
        return output_file

    monkeypatch.setattr(
        "cruiseplan.output.map_generator.generate_map_from_timeline", capture_map
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        png = cruiseplan.stationplan_forecast_png(
            nc_path,
            k_op,
            t0.isoformat(),
            6,
            output_path=tmp_path / "plan.png",
            current_position=here,
        )
        kml = cruiseplan.stationplan_forecast_kml(
            nc_path,
            k_op,
            t0.isoformat(),
            6,
            output_path=tmp_path / "plan.kml",
            current_position=here,
        )
    assert png.success
    niss = next(r for r in captured["timeline"] if r.label == "NISS")
    assert seconds(niss.start_time, t_niss) <= T_TOL_S
    assert kml.success
    kml_text = (tmp_path / "plan.kml").read_text()
    niss_kml = kml_text[kml_text.index("<name>NISS</name>") :]
    assert f"Start: {t_niss:%Y-%m-%d %H:%M}" in niss_kml.split("</Placemark>")[0]


# =============================================================================
# Delays and buffer through NetCDF into the forecast
# =============================================================================


def with_delays(delays: dict[str, float]) -> dict:
    """pycnmix with per-operation delay_start values."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] in delays:
            p["delay_start"] = delays[p["name"]]
    return cfg


@pytest.mark.parametrize(
    ("delays", "label", "transit_label", "delay"),
    [
        ({"NIWA_DITN": 90.0}, "NIWA_DITN", "Transit to NIWA_DITN", 90.0),
        ({"NIWA_DITN": -60.0}, "NIWA_DITN", "Transit to NIWA_DITN", -60.0),
        ({"NISS": -45.0}, "NISS", "Transit to NISS", -45.0),
    ],
)
def test_delay_survives_into_forecast(tmp_path, delays, label, transit_label, delay):
    """
    Anchor on the row before the transit at T: op starts T + prev + transit + delay.

    A negative delay (the transit ended early) shortens the transit row to
    transit + delay, so the transit ends where the op starts.
    """
    cfg = with_delays(delays)
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "delay")
    k_tr = index_of(hand, transit_label)
    k_prev = k_tr - 1
    assert hand[k_prev].kind != "transit"
    t0 = datetime(2026, 3, 10, 6, 0)
    rows = {row[0]: row for row in forecast_rows(nc_path, k_prev, t0)}
    expected = t0 + timedelta(minutes=hand[k_prev].minutes + hand[k_tr].minutes + delay)
    k = index_of(hand, label)
    assert seconds(rows[k][1], expected) <= T_TOL_S
    # the transit row ends where the op starts
    transit_end = rows[k_tr][1] + timedelta(hours=rows[k_tr][5])
    assert rows[k_tr][5] * 60 == pytest.approx(
        hand[k_tr].minutes + min(delay, 0.0), abs=0.5
    )
    assert seconds(transit_end, expected) <= T_TOL_S or delay > 0
    # the next row after the op: + op duration
    assert (
        seconds(rows[k + 1][1], expected + timedelta(minutes=hand[k].minutes))
        <= T_TOL_S
    )
    # same values from the independent hand forecast
    for r in hand_forecast(hand, k_prev, t0):
        assert seconds(rows[r.index][1], r.start) <= T_TOL_S
        assert rows[r.index][5] * 60 == pytest.approx(r.minutes, abs=0.5)


def test_negative_delay_rows_do_not_overlap(tmp_path):
    """With NISS -45 and LDEO_heavy_shallow_deployment -30, each row ends where the next starts."""
    cfg = with_delays({"NISS": -45.0, "LDEO_heavy_shallow_deployment": -30.0})
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "neg")
    k0 = index_of(hand, "Jangbogo Station", 1)
    t0 = datetime(2026, 3, 9, 8, 0)
    rows = forecast_rows(nc_path, k0, t0)
    for a, b in zip(rows, rows[1:], strict=False):
        end = a[1] + timedelta(hours=a[5])
        assert end <= b[1] + timedelta(seconds=T_TOL_S), (a[8], b[8])
    k_rec = index_of(hand, "LDEO_heavy_shallow_recovery")
    rec = next(r for r in rows if r[0] == k_rec)
    assert rec[5] * 60 == pytest.approx(hand[k_rec].minutes - 30.0, abs=0.5)


def test_buffer_survives_into_forecast(tmp_path):
    """Leg2 buffer: anchored on NIWA_WBAT at T, port arrival at T + 120 + 360 + 24.95."""
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    k = index_of(hand, "NIWA_WBAT")
    assert hand[k + 1].kind == "buffer"
    t0 = datetime(2026, 3, 12, 6, 0)
    fc = forecast(nc_path, k, t0)
    port = next(p for p in cfg["ports"] if p["name"] == "port_jang_bogo")
    nm = gc_nm((-74.6901, 164.2419), (port["latitude"], port["longitude"]))
    assert nm == pytest.approx(4.16, abs=0.01)
    assert seconds(fc[k + 1], t0 + timedelta(minutes=120)) <= T_TOL_S
    assert seconds(fc[k + 3], t0 + timedelta(minutes=120 + 360 + nm * 6)) <= T_TOL_S


def test_netcdf_round_trip_durations(tmp_path):
    """Reader records: start, end and duration_minutes as in the hand schedule."""
    cfg = with_delays({"NIWA_DITN": -60.0})
    hand = hand_schedule(cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ds = read_schedule(netcdf_for(tmp_path, cfg, "rt"))
        records = netcdf_to_activity_records(ds)
        ds.close()
    assert len(records) == len(hand)
    for rec, h in zip(records, hand, strict=True):
        assert rec.label == h.name
        assert seconds(rec.start_time, h.start) <= T_TOL_S
        assert seconds(rec.end_time, h.end) <= T_TOL_S
        assert rec.duration_minutes == pytest.approx(h.minutes, abs=0.01)


def test_netcdf_round_trip_keeps_delay_value(tmp_path):
    """NIWA_DITN delay_start -60 is read back from the NetCDF."""
    cfg = with_delays({"NIWA_DITN": -60.0})
    hand = hand_schedule(cfg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ds = read_schedule(netcdf_for(tmp_path, cfg, "rt"))
        records = netcdf_to_activity_records(ds)
        ds.close()
    k = index_of(hand, "NIWA_DITN")
    assert records[k].delay_start_minutes == -60.0
    assert records[k - 1].delay_start_minutes is None  # the transit into it
    with xr.open_dataset(netcdf_for(tmp_path, cfg, "rt2")) as ds:
        assert ds.delay_start.attrs["units"] == "minute"


def test_netcdf_without_delay_variable_still_reads(tmp_path):
    """A schedule written before delay_start was stored reads and forecasts the same."""
    cfg = with_delays({"NIWA_DITN": -60.0})
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "new")
    old_path = tmp_path / "old_schedule.nc"
    with xr.open_dataset(nc_path) as ds:
        ds.drop_vars("delay_start").load().to_netcdf(old_path)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ds = read_schedule(old_path)
        records = netcdf_to_activity_records(ds)
        ds.close()
    assert records[index_of(hand, "NIWA_DITN")].delay_start_minutes is None
    t0 = datetime(2026, 3, 10, 6, 0)
    k = index_of(hand, "Transit to NIWA_DITN") - 1
    assert forecast_rows(old_path, k, t0) == forecast_rows(nc_path, k, t0)


# =============================================================================
# Output formatting on the at-sea path
# =============================================================================


def test_tex_rounding_past_midnight(tmp_path):
    """NISS anchored at 23:56 on 09.03.2026 rounds to 00:00 on 10.03.2026."""
    cfg = load("pycnmix")
    hand = hand_schedule(cfg)
    nc_path = netcdf_for(tmp_path, cfg, "pycnmix")
    out = tmp_path / "plan.tex"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = cruiseplan.stationplan_forecast_tex(
            nc_path, index_of(hand, "NISS"), "2026-03-09T23:56:00", 6, output_path=out
        )
    assert result.success
    lines = out.read_text().splitlines()
    row = next(i for i, line in enumerate(lines) if "& NISS &" in line)
    header = next(line for line in reversed(lines[:row]) if "textbf{" in line)
    assert lines[row].startswith("00:00")
    assert "10.03.2026" in header


def run_cli(monkeypatch, args: list[str]) -> int:
    """Run the cruiseplan CLI; return the exit code (0 when it returns)."""
    monkeypatch.setattr(sys, "argv", ["cruiseplan", *args])
    try:
        cli_main.main()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def test_cli_current_position_southern_equals_form(tmp_path, monkeypatch, capsys):
    """--current-position=-74.62,164.30 works and prints the ship position first."""
    nc_path = netcdf_for(tmp_path, load("pycnmix"), "pycnmix")
    code = run_cli(
        monkeypatch,
        [
            "forecast",
            str(nc_path),
            "--start-index",
            "12",
            "--start-time",
            "2026-03-09 08:00",
            "--duration",
            "6",
            "--format",
            "waypoints",
            "--current-position=-74.62,164.30",
        ],
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "1\t74 37.20 S\t164 18.00 E\tMerian" in out


def test_cli_current_position_southern_space_form(tmp_path, monkeypatch):
    """--current-position -74.62,164.30 (space form) is accepted."""
    nc_path = netcdf_for(tmp_path, load("pycnmix"), "pycnmix")
    code = run_cli(
        monkeypatch,
        [
            "forecast",
            str(nc_path),
            "--start-index",
            "12",
            "--start-time",
            "2026-03-09 08:00",
            "--format",
            "waypoints",
            "--current-position",
            "-74.62,164.30",
        ],
    )
    assert code == 0


@pytest.mark.parametrize(
    "value",
    [["-74.62", "164.30"], ["-74.62,", "164.30"], ["-74.62, 164.30"]],
)
def test_cli_current_position_other_forms(tmp_path, monkeypatch, capsys, value):
    """Two values, a comma then a space, or one quoted value all parse."""
    nc_path = netcdf_for(tmp_path, load("pycnmix"), "pycnmix")
    code = run_cli(
        monkeypatch,
        [
            "forecast",
            str(nc_path),
            "--start-index",
            "12",
            "--start-time",
            "2026-03-09 08:00",
            "--format",
            "waypoints",
            "--current-position",
            *value,
        ],
    )
    assert code == 0
    assert "1\t74 37.20 S\t164 18.00 E\tMerian" in capsys.readouterr().out


def test_cli_current_position_moves_tex_times(tmp_path, monkeypatch):
    """Her generate_stationplan.sh call: --current-position now moves the TeX times."""
    nc_path = netcdf_for(tmp_path, load("pycnmix"), "pycnmix")
    base = [
        "forecast",
        str(nc_path),
        "--start-index",
        "12",
        "--start-time",
        "2026-03-09 08:00",
        "--duration",
        "6",
        "--format",
        "tex",
        "--output-dir",
        str(tmp_path),
    ]
    assert run_cli(monkeypatch, [*base, "--output", "a.tex"]) == 0
    assert (
        run_cli(
            monkeypatch,
            [*base, "--current-position", "-74.98,163.48", "--output", "b.tex"],
        )
        == 0
    )

    def niss_row(name: str) -> str:
        text = (tmp_path / name).read_text()
        return next(line for line in text.splitlines() if "& NISS &" in line)

    assert niss_row("a.tex").startswith("08:00")
    assert niss_row("b.tex").startswith("09:00")


@pytest.mark.parametrize(
    ("given", "rounded"),
    [
        (datetime(2026, 3, 9, 23, 56), datetime(2026, 3, 10, 0, 0)),
        (datetime(2026, 3, 9, 23, 54, 59), datetime(2026, 3, 9, 23, 50)),
        (datetime(2026, 12, 31, 23, 58), datetime(2027, 1, 1, 0, 0)),
        (datetime(2026, 3, 9, 8, 3), datetime(2026, 3, 9, 8, 0)),
    ],
)
def test_round_to_ten_minutes_carries_the_day(given, rounded):
    """Waypoints without --start-time and TeX times round with the date carried."""
    assert round_to_minutes(given, 10) == rounded
