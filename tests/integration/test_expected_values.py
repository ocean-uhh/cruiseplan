"""
Expected values for real cruise configs, computed by hand.

Every expected number comes from ``hand_calc`` (haversine with R = 6371 km,
nm = km / 1.852, transit = nm / kt * 60, CTD = depth / descent + depth / ascent
+ turnaround) or from arithmetic written out in the test, never from a run of
the code. Where the hand value and the code disagree, the test carries the hand
value and is marked ``xfail(strict=True)`` with the suspected cause.

Tolerances: times 30 s, durations 0.5 min, distances 0.01 nm.
"""

import csv
import logging
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import netCDF4  # noqa: F401 - netcdf backend for xarray
import pytest
import xarray as xr
import yaml
from hand_calc import (
    FILL_MIN,
    Row,
    ctd_min,
    gc_nm,
    hand_schedule,
    transit_min,
)

import cruiseplan
import cruiseplan.data.bathymetry as bathy_module
from cruiseplan.timeline import ActivityRecord
from cruiseplan.timeline.scheduler import timeline_minutes

ROOT = Path(__file__).parent.parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
CONFIGS = {
    "tc1_single": FIXTURES / "tc1_single.yaml",
    "tc1_mooring": FIXTURES / "tc1_mooring.yaml",
    "tc2_two_legs": FIXTURES / "tc2_two_legs.yaml",
    "tc3_clusters": FIXTURES / "tc3_clusters.yaml",
    "tc4_mixed_ops": FIXTURES / "tc4_mixed_ops.yaml",
    "tc5_sections": FIXTURES / "tc5_sections.yaml",
    # every activity listed twice (group and pair clusters): 164 rows
    "coldsnap": FIXTURES / "coldsnap-2028-newformat_old.yaml",
    # the same activities listed once, K1 first in West Greenland: 84 rows
    "mooring_sequence": FIXTURES / "mooring_sequence_greenland.yaml",
    "pycnmix": ROOT / "data" / "pycnmix-2026-v1.yaml",
    # Leg1 10 kt, Leg2 5 kt, Leg3 15 kt
    "pycnmix_leg_speeds": FIXTURES / "pycnmix_leg_speeds.yaml",
}
HALIFAX_FILE = "gebco2025_halifax_subset.nc"
T_TOL_S = 30.0
MIN_TOL = 0.5
NM_TOL = 0.01


def load(name: str) -> dict:
    """Read a config with yaml.safe_load (not through cruiseplan)."""
    return yaml.safe_load(CONFIGS[name].read_text())


def write(tmp_path: Path, cfg: dict, name: str) -> Path:
    """Write a modified copy of a real config."""
    path = tmp_path / f"{name}.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return path


def timeline(path: Path) -> list[ActivityRecord]:
    """Schedule a config without writing files."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return cruiseplan.schedule(config_file=path, format=None).timeline


def by_label(rows: list, label: str, nth: int = 0):
    """Return the nth row with this label (records or hand rows)."""
    hits = [r for r in rows if (r.name if isinstance(r, Row) else r.label) == label]
    return hits[nth]


def assert_time(actual: datetime, expected: datetime) -> None:
    """Times agree to the minute (30 s)."""
    delta = abs((actual - expected).total_seconds())
    assert delta <= T_TOL_S, f"{actual} vs hand {expected} ({delta:.0f} s)"


def assert_rows_match(code: list[ActivityRecord], hand: list) -> None:
    """Every row: label, start, end, duration and distance agree with hand."""
    assert [c.label for c in code] == [h.name for h in hand]
    for c, h in zip(code, hand, strict=True):
        assert_time(c.start_time, h.start)
        assert_time(c.end_time, h.end)
        assert c.duration_minutes == pytest.approx(h.minutes, abs=MIN_TOL), h.name
        assert c.dist_nm == pytest.approx(h.nm, abs=NM_TOL), h.name


# =============================================================================
# Worked examples (written-out arithmetic)
# =============================================================================


def test_hand_helpers_written_out():
    """The hand helpers equal the formulas written out once."""
    # 1 degree of latitude = 6371 * pi / 180 / 1.852 nm
    assert gc_nm((45.0, -50.0), (46.0, -50.0)) == pytest.approx(
        6371.0 * 3.141592653589793 / 180 / 1.852, abs=1e-9
    )
    assert transit_min(60.0, 10.0) == 360.0
    # 2850 m at 1 m/s down and up: 47.5 + 47.5 + 30 turnaround
    assert ctd_min(2850.0) == pytest.approx(125.0)
    assert FILL_MIN == 59940.0


def test_tc1_single_worked_example():
    """tc1_single: Halifax -> STN_001 (45 N, 45 W, 2850 m) -> Cadiz, 10 kt."""
    tl = timeline(CONFIGS["tc1_single"])
    out_nm = gc_nm((44.6488, -63.5752), (45.0, -45.0))
    back_nm = gc_nm((45.0, -45.0), (36.5298, -6.2923))
    assert out_nm == pytest.approx(789.57, abs=0.01)
    assert back_nm == pytest.approx(1813.14, abs=0.01)

    t0 = datetime(1970, 1, 1)
    arrive = t0 + timedelta(minutes=out_nm / 10 * 60)  # 4737.43 min
    stn = by_label(tl, "STN_001")
    assert_time(stn.start_time, arrive)
    assert stn.duration_minutes == pytest.approx(2850 / 60 + 2850 / 60 + 30)
    assert stn.operation_depth_m == 2850.0
    end = arrive + timedelta(minutes=125 + back_nm / 10 * 60)
    assert_time(tl[-1].end_time, end)
    assert tl[1].dist_nm == pytest.approx(out_nm, abs=NM_TOL)
    assert tl[3].dist_nm == pytest.approx(back_nm, abs=NM_TOL)


def test_tc4_line_and_area_worked_example():
    """tc4: CTD at 58 m, ADCP line at its own 5 kt, area entered at first corner."""
    tl = timeline(CONFIGS["tc4_mixed_ops"])
    stn = by_label(tl, "STN_001")
    assert stn.duration_minutes == pytest.approx(58 / 60 * 2 + 30)  # 31.93
    line = by_label(tl, "ADCP_Survey")
    line_nm = gc_nm((46.0, -50.0), (47.0, -50.0))  # 60.04 nm
    assert line.dist_nm == pytest.approx(line_nm, abs=NM_TOL)
    assert line.duration_minutes == pytest.approx(line_nm / 5 * 60, abs=MIN_TOL)
    # transit from line end (47 N, 50 W) to area first corner (47.5 N, 50.5 W)
    to_area = by_label(tl, "Transit to Area_01")
    assert to_area.dist_nm == pytest.approx(
        gc_nm((47.0, -50.0), (47.5, -50.5)), abs=NM_TOL
    )
    # transit to Cadiz leaves from the area's last corner (47.5 N, 49.5 W)
    home = by_label(tl, "Transit to Cadiz")
    assert home.dist_nm == pytest.approx(
        gc_nm((47.5, -49.5), (36.5298, -6.2923)), abs=NM_TOL
    )


# =============================================================================
# Every row of every real config
# =============================================================================


@pytest.mark.parametrize("name", list(CONFIGS))
def test_every_row_matches_hand(name):
    """Start, end, duration and distance of every row match the hand schedule."""
    assert_rows_match(timeline(CONFIGS[name]), hand_schedule(load(name)))


@pytest.mark.parametrize("name", list(CONFIGS))
def test_leg_totals(name):
    """Per leg: start, end, duration (end - start) and distance."""
    code = timeline(CONFIGS[name])
    hand = hand_schedule(load(name))
    for leg in load(name)["legs"]:
        c = [r for r in code if r.leg_name == leg["name"]]
        h = [r for r in hand if r.leg == leg["name"]]
        assert_time(c[0].start_time, h[0].start)
        assert_time(c[-1].end_time, h[-1].end)
        c_hours = (c[-1].end_time - c[0].start_time).total_seconds() / 3600
        h_hours = (h[-1].end - h[0].start).total_seconds() / 3600
        assert c_hours == pytest.approx(h_hours, abs=T_TOL_S / 3600)
        assert sum(r.dist_nm for r in c) == pytest.approx(
            sum(r.nm for r in h), abs=NM_TOL
        )


@pytest.mark.parametrize(
    ("name", "hours", "nm"),
    [
        # hand totals, rounded to 0.01 h and 0.01 nm
        ("tc1_single", 262.35, 2602.71),
        ("tc1_mooring", 1113.44, 1144.43),
        ("tc2_two_legs", 2438.47, 4404.70),
        ("pycnmix", 610.42, 4840.91),
        ("coldsnap", 908.36, 6047.70),
        ("mooring_sequence", 377.33, 2225.39),
    ],
)
def test_schedule_totals(name, hours, nm):
    """Schedule total duration (sum of durations, as the CLI reports) and distance."""
    code = timeline(CONFIGS[name])
    hand = hand_schedule(load(name))
    span_h = (hand[-1].end - hand[0].start).total_seconds() / 3600
    assert span_h == pytest.approx(hours, abs=0.01)
    assert sum(r.nm for r in hand) == pytest.approx(nm, abs=0.01)
    assert sum(r.duration_minutes for r in code) / 60 == pytest.approx(span_h, abs=0.01)
    assert sum(r.dist_nm for r in code) == pytest.approx(nm, abs=0.02)


def test_tc3_leg_vessel_speed():
    """tc3 Leg_Survey_Faster (12 kt) is shorter than Leg_Survey (10 kt) by d/10 - d/12."""
    code = timeline(CONFIGS["tc3_clusters"])
    hand = hand_schedule(load("tc3_clusters"))
    transit_nm = sum(r.nm for r in hand if r.leg == "Leg_Survey")
    assert transit_nm == pytest.approx(1248.35, abs=0.01)
    expected_gain_h = transit_nm / 10 - transit_nm / 12  # 20.81 h

    def span(leg):
        rows = [r for r in code if r.leg_name == leg]
        return (rows[-1].end_time - rows[0].start_time).total_seconds() / 3600

    assert span("Leg_Survey") - span("Leg_Survey_Faster") == pytest.approx(
        expected_gain_h, abs=0.01
    )
    faster = [
        r for r in code if r.leg_name == "Leg_Survey_Faster" and r.activity == "Transit"
    ]
    assert {r.vessel_speed_kt for r in faster} == {12.0}


# =============================================================================
# Named operations
# =============================================================================


@pytest.mark.parametrize(
    ("name", "label", "nth", "minutes", "depth"),
    [
        ("coldsnap", "STN68", 0, 2329 / 60 * 2 + 30, 2329.0),
        ("coldsnap", "K7_Recovery", 0, 240.0, 1380.0),
        ("coldsnap", "K7_Recovery", 1, 240.0, 1380.0),
        ("coldsnap", "AE1_Recovery", 0, 120.0, 300.0),
        ("mooring_sequence", "STN68", 0, 2329 / 60 * 2 + 30, 2329.0),
        ("mooring_sequence", "K7_Recovery", 0, 240.0, 1380.0),
        ("mooring_sequence", "AE1_Recovery", 0, 120.0, 300.0),
        ("pycnmix", "SouthCapeAdair", 0, 10.0, None),
        ("pycnmix", "SouthCapeAdair", 1, 10.0, None),
        ("pycnmix", "NISS", 0, 120.0, None),
        ("pycnmix", "Option_AD", 1, 1080.0, None),
        ("tc2_two_legs", "STN_001", 0, FILL_MIN, None),
        ("tc2_two_legs", "STN_002", 0, FILL_MIN, None),
    ],
)
def test_named_operations(name, label, nth, minutes, depth):
    """Start/end time, duration and depth used for named operations."""
    code = by_label(timeline(CONFIGS[name]), label, nth)
    hand = by_label(hand_schedule(load(name)), label, nth)
    assert hand.minutes == pytest.approx(minutes)
    assert code.duration_minutes == pytest.approx(minutes)
    assert_time(code.start_time, hand.start)
    assert_time(code.end_time, hand.end)
    assert code.operation_depth_m == depth
    assert code.duration_is_fill == (minutes == FILL_MIN)


@pytest.mark.parametrize(
    ("name", "src", "dst", "lat_lon_src", "lat_lon_dst"),
    [
        (
            "pycnmix",
            "Lyttelton",
            "SouthCapeAdair",
            (-43.5333, 172.6333),
            (-72.0, 173.0),
        ),
        # area exit is its last corner, area entry its first corner
        ("pycnmix", "Option_C", "Option_AD", (-67.8, 173.0), (-68.2, 171.0)),
        ("pycnmix", "NIWA_WBAT", "Jangbogo Station", (-74.6901, 164.2419), None),
        ("tc2_two_legs", "Bremerhaven", "STN_002", (53.5395, 8.5809), (60.0, -30.0)),
        ("coldsnap", "STN68", "Reykjavik", (64.75, -30.3333), (64.1466, -21.9426)),
        (
            "mooring_sequence",
            "STN68",
            "Reykjavik",
            (64.75, -30.3333),
            (64.1466, -21.9426),
        ),
    ],
)
def test_transit_between_named_points(name, src, dst, lat_lon_src, lat_lon_dst):
    """Transit distance and time between named points, 10 kt."""
    cfg = load(name)
    if lat_lon_dst is None:
        port = next(p for p in cfg["ports"] if p["name"] == "port_jang_bogo")
        lat_lon_dst = (port["latitude"], port["longitude"])
    nm = gc_nm(lat_lon_src, lat_lon_dst)
    tl = timeline(CONFIGS[name])
    idx = next(
        i
        for i, r in enumerate(tl)
        if r.label == f"Transit to {dst}"
        and tl[i - 1].label in (src,)
        or (
            r.label == f"Transit to {dst}"
            and tl[i - 1].activity == "Buffer"
            and tl[i - 2].label == src
        )
    )
    assert tl[idx].dist_nm == pytest.approx(nm, abs=NM_TOL)
    assert tl[idx].duration_minutes == pytest.approx(nm / 10 * 60, abs=MIN_TOL)


# =============================================================================
# buffer_time
# =============================================================================


@pytest.mark.parametrize(
    ("name", "leg", "last_op", "arrival"),
    [
        ("pycnmix", "Leg1", "Option_AD", "Jangbogo Station"),
        ("pycnmix", "Leg2", "NIWA_WBAT", "Jangbogo Station"),
        ("pycnmix", "Leg3", "Pycnogen_inner1", "Lyttelton"),
        ("coldsnap", "COLDSNAP", "STN68", "Reykjavik"),
        ("mooring_sequence", "Mooring_Sequence", "STN68", "Reykjavik"),
    ],
)
def test_buffer_block(name, leg, last_op, arrival):
    """360 min buffer: after the last operation, before the transit to the port."""
    tl = [r for r in timeline(CONFIGS[name]) if r.leg_name == leg]
    i = next(k for k, r in enumerate(tl) if r.activity == "Buffer")
    assert [r.activity for r in tl].count("Buffer") == 1
    buf, before, after = tl[i], tl[i - 1], tl[i + 1]
    assert before.label == last_op
    assert after.label == f"Transit to {arrival}"
    assert buf.duration_minutes == 360.0
    assert buf.start_time == before.end_time
    assert_time(buf.end_time, before.end_time + timedelta(minutes=360))
    assert after.start_time == buf.end_time
    assert (buf.entry_lat, buf.entry_lon) == (
        before.exit_lat,
        before.exit_lon,
    )
    assert buf.dist_nm == 0.0


# =============================================================================
# delay_start (per operation, per leg)
# =============================================================================


def pycnmix_with_delays() -> dict:
    """pycnmix with per-op and per-leg delay_start set (no real config uses it)."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] == "LDEO_heavy_shallow_deployment":
            p["delay_start_minutes"] = 90.0  # same position as the recovery: no transit
        if p["name"] == "SouthCapeAdair":
            p["delay_start_minutes"] = 45.0  # used in Leg1 and Leg3
        if p["name"] == "NISS":
            p["delay_start_minutes"] = 30.0  # first op of Leg2, after a transit
    for leg in cfg["legs"]:
        if leg["name"] == "Leg2":
            leg["delay_start_minutes"] = 120.0
    return cfg


def test_delay_start_every_row(tmp_path):
    """All rows of the delayed copy match the hand schedule."""
    cfg = pycnmix_with_delays()
    assert_rows_match(timeline(write(tmp_path, cfg, "delays")), hand_schedule(cfg))


def test_delay_start_effects(tmp_path):
    """
    Each delay lengthens the operation before it in the same leg.

    SouthCapeAdair +45 (first op of Leg1 and Leg3): the departure port rows
    last 45 min. NISS +30 (first op of Leg2): the Leg2 Jang Bogo row lasts
    30 min. LDEO_heavy_shallow_deployment +90: the recovery lasts 120 + 90.
    Operation starts move as before; transits keep their length.
    """
    base = timeline(CONFIGS["pycnmix"])
    tl = timeline(write(tmp_path, pycnmix_with_delays(), "delays"))

    def shift(label, nth=0):
        a, b = by_label(base, label, nth), by_label(tl, label, nth)
        return (b.start_time - a.start_time).total_seconds() / 60

    def minutes(label, nth=0):
        r = by_label(tl, label, nth)
        return r.duration_minutes, r.planned_duration_minutes

    assert shift("SouthCapeAdair") == pytest.approx(45)
    assert minutes("Lyttelton", 0) == pytest.approx((45, 0))
    # Leg2 starts 45 later (Leg1) + 120 leg delay; NISS adds its own 30
    assert shift("Jangbogo Station", 1) == pytest.approx(45 + 120)
    assert minutes("Jangbogo Station", 1) == pytest.approx((30, 0))
    assert shift("Transit to NISS") == pytest.approx(45 + 120 + 30)
    assert shift("NISS") == pytest.approx(45 + 120 + 30)
    assert shift("LDEO_heavy_shallow_recovery") == pytest.approx(195)
    assert minutes("LDEO_heavy_shallow_recovery") == pytest.approx((210, 120))
    assert shift("LDEO_heavy_shallow_deployment") == pytest.approx(195 + 90)
    # Leg3: SouthCapeAdair again (shared definition), after the Leg3 port row
    assert minutes("Jangbogo Station", 3) == pytest.approx((45, 0))
    assert shift("SouthCapeAdair", 1) == pytest.approx(285 + 45)
    for label in ("Transit to NISS", "Transit to LDEO_heavy_shallow_recovery"):
        assert by_label(tl, label).duration_minutes == pytest.approx(
            by_label(base, label).duration_minutes
        )
    assert by_label(tl, "LDEO_heavy_shallow_deployment").delay_start_minutes == 90.0


def pycnmix_with_negative_delays() -> dict:
    """pycnmix with negative per-op delay_start (at-sea correction: start earlier)."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] == "LDEO_heavy_shallow_deployment":
            p[
                "delay_start_minutes"
            ] = -30.0  # no transit before it: overlaps the recovery
        if p["name"] == "NIWA_DITN":
            p["delay_start_minutes"] = -60.0  # after a 193.08 nm transit
    return cfg


def test_negative_delay_start_every_row(tmp_path):
    """Negative delays: the operation before ends early; every row matches the hand schedule."""
    cfg = pycnmix_with_negative_delays()
    assert_rows_match(timeline(write(tmp_path, cfg, "neg")), hand_schedule(cfg))


def test_negative_delay_start_effects(tmp_path):
    """A negative delay shortens the operation before it and moves the rest earlier."""
    base = timeline(CONFIGS["pycnmix"])
    tl = timeline(write(tmp_path, pycnmix_with_negative_delays(), "neg"))

    def shift(label):
        a, b = by_label(base, label), by_label(tl, label)
        return (b.start_time - a.start_time).total_seconds() / 60

    assert shift("LDEO_heavy_shallow_recovery") == pytest.approx(0)
    assert shift("LDEO_heavy_shallow_deployment") == pytest.approx(-30)
    assert shift("NIWA_DITN") == pytest.approx(-30 - 60)
    assert shift("NIWA_WBAT") == pytest.approx(-90)
    # The model accepts the negative value and the record carries it
    assert by_label(tl, "NIWA_DITN").delay_start_minutes == -60.0
    # The recovery ended 30 min early: 120 - 30 = 90 min actual, 120 planned
    rec = by_label(tl, "LDEO_heavy_shallow_recovery")
    dep = by_label(tl, "LDEO_heavy_shallow_deployment")
    assert rec.end_time == dep.start_time
    assert rec.duration_minutes == pytest.approx(120 - 30)
    assert rec.planned_duration_minutes == pytest.approx(120)
    # NIWA_DITN -60: Option_E (1080 min), the operation before the transit,
    # lasts 1020 min; the transit keeps its 193.08 nm / 10 kt and moves earlier
    opt = by_label(tl, "Option_E")
    assert opt.duration_minutes == pytest.approx(1080 - 60)
    assert opt.planned_duration_minutes == pytest.approx(1080)
    transit = by_label(tl, "Transit to NIWA_DITN")
    assert transit.dist_nm == pytest.approx(193.08, abs=NM_TOL)
    assert transit.duration_minutes == pytest.approx(193.08 * 6, abs=MIN_TOL)
    assert transit.start_time == opt.end_time
    assert transit.end_time == by_label(tl, "NIWA_DITN").start_time
    assert shift("Transit to NIWA_DITN") == pytest.approx(-30 - 60)
    # No gaps or overlaps: the durations add up to the elapsed time
    span_min = (tl[-1].end_time - tl[0].start_time).total_seconds() / 60
    assert sum(r.duration_minutes for r in tl) == pytest.approx(span_min, abs=0.01)


def test_negative_delay_longer_than_the_operation_before(tmp_path, caplog):
    """LDEO_heavy_shallow_deployment -150 after a 120 min recovery: 0 min, 30 min lost."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] == "LDEO_heavy_shallow_deployment":
            p["delay_start_minutes"] = -150.0
    base = timeline(CONFIGS["pycnmix"])
    with caplog.at_level(logging.WARNING, logger="cruiseplan.timeline.scheduler"):
        tl = timeline(write(tmp_path, cfg, "clamp"))
    rec = by_label(tl, "LDEO_heavy_shallow_recovery")
    assert rec.duration_minutes == 0.0
    assert rec.planned_duration_minutes == pytest.approx(120)
    dep = by_label(tl, "LDEO_heavy_shallow_deployment")
    shift = (dep.start_time - by_label(base, dep.label).start_time).total_seconds()
    assert shift / 60 == pytest.approx(-120)
    assert any(
        "LDEO_heavy_shallow_deployment" in m
        and "LDEO_heavy_shallow_recovery" in m
        and "30.0 min could not be absorbed" in m
        for m in caplog.messages
    )
    assert_rows_match(tl, hand_schedule(cfg))


@pytest.mark.parametrize(
    ("op", "leg", "leg2_delay", "lever"),
    [
        (
            "NISS",
            "Leg2",
            None,
            "To start leg Leg2 earlier, end the previous leg (Leg1) 45.0 min earlier",
        ),
        (
            "NISS",
            "Leg2",
            120.0,
            "To start leg Leg2 earlier, reduce the delay_start_minutes of leg Leg2 "
            "(120 min) by 45.0 min",
        ),
        (
            "SouthCapeAdair",
            "Leg1",
            None,
            "To start leg Leg1 earlier, start the cruise 45.0 min earlier "
            "(cruise start_date / start_time)",
        ),
    ],
)
def test_negative_delay_at_leg_start_names_the_lever(
    tmp_path, caplog, op, leg, leg2_delay, lever
):
    """-45 on a leg's first operation after a 0 min departure port: kept, with a warning."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] == op:
            p["delay_start_minutes"] = -45.0
    if leg2_delay is not None:
        for leg_def in cfg["legs"]:
            if leg_def["name"] == "Leg2":
                leg_def["delay_start_minutes"] = leg2_delay
    with caplog.at_level(logging.WARNING, logger="cruiseplan.timeline.scheduler"):
        tl = timeline(write(tmp_path, cfg, "leg_start"))
    expected = (
        f"Operation {op}: 45.0 min of its negative delay_start_minutes in leg "
        f"{leg} could not be absorbed; nothing earlier in the leg is long enough. "
        f"{lever}"
    )
    assert expected in caplog.messages
    # SouthCapeAdair is also the first operation of Leg3; no generic clamp warning
    assert not any("is set to 0 min" in m for m in caplog.messages)
    assert_rows_match(tl, hand_schedule(cfg))


def test_total_duration_includes_delays(tmp_path):
    """
    The durations add up to the elapsed span, less the leg delay between legs.

    pycnmix with delays 45 + 30 + 90 + 45 = 210 min on operations (absorbed in
    the operations before them) and a 120 min Leg2 delay (a gap between legs).
    The reported total (CLI, result summary) is the span.
    """
    path = write(tmp_path, pycnmix_with_delays(), "delays")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = cruiseplan.schedule(config_file=path, format=None)
    tl = result.timeline
    base = timeline(CONFIGS["pycnmix"])
    span_min = (tl[-1].end_time - tl[0].start_time).total_seconds() / 60
    base_span = (base[-1].end_time - base[0].start_time).total_seconds() / 60
    assert span_min - base_span == pytest.approx(210 + 120, abs=0.01)
    durations = sum(r.duration_minutes for r in tl)
    assert durations - sum(r.duration_minutes for r in base) == pytest.approx(
        210, abs=0.01
    )
    assert span_min - durations == pytest.approx(120, abs=0.01)
    assert result.summary["total_duration_hours"] * 60 == pytest.approx(
        span_min, abs=0.01
    )
    assert timeline_minutes(tl) == pytest.approx(span_min, abs=0.01)


# =============================================================================
# Leg-level overrides
# =============================================================================


def test_leg_turnaround_time(tmp_path):
    """tc1_single with leg turnaround_time 20: 2850/60 * 2 + 20 = 115 min."""
    cfg = load("tc1_single")
    cfg["legs"][0]["turnaround_time_minutes"] = 20.0
    stn = by_label(timeline(write(tmp_path, cfg, "turn")), "STN_001")
    assert stn.duration_minutes == pytest.approx(115.0)


def tc5_leg_speed(tmp_path: Path) -> tuple[list[dict], float]:
    """tc5 with leg vessel_speed 12 kt; returns timeline and section length."""
    cfg = load("tc5_sections")
    cfg["legs"][0]["vessel_speed_kt"] = 12.0
    nm = gc_nm((45.0, -50.0), (47.0, -48.0))  # 146.20 nm
    return timeline(write(tmp_path, cfg, "tc5_12kt")), nm


def test_leg_speed_applies_to_transits(tmp_path):
    """Transits use the leg speed of 12 kt."""
    tl, _ = tc5_leg_speed(tmp_path)
    out = by_label(tl, "Transit to SEC_001")
    nm = gc_nm((44.6488, -63.5752), (45.0, -50.0))
    assert out.duration_minutes == pytest.approx(nm / 12 * 60, abs=MIN_TOL)


def test_leg_speed_applies_to_line_without_speed(tmp_path):
    """SEC_001 (146.20 nm, no own speed) at the leg's 12 kt: 731.0 min."""
    tl, nm = tc5_leg_speed(tmp_path)
    line = by_label(tl, "SEC_001")
    assert line.duration_minutes == pytest.approx(nm / 12 * 60, abs=MIN_TOL)


def test_line_record_reports_its_speed():
    """ADCP_Survey runs at 5 kt and its record says so."""
    line = by_label(timeline(CONFIGS["tc4_mixed_ops"]), "ADCP_Survey")
    assert line.vessel_speed_kt == 5.0


# =============================================================================
# Fill values and bathymetry
# =============================================================================


@pytest.mark.parametrize(
    ("name", "fills"),
    [
        ("tc1_single", 0),  # water_depth 2850 in YAML
        ("tc1_mooring", 1),  # mooring without duration
        ("tc2_two_legs", 2),  # CTD without depth, mooring without duration
        ("tc3_clusters", 15),  # STN_001/002 x (2 + 2 + 3 + 3 + 3 + 2) occurrences
        ("tc4_mixed_ops", 0),  # operation_depth 58 kept
        ("tc5_sections", 19),  # int(270.76 km / 15 km) + 1 = 19 section stations
        ("coldsnap", 0),
        ("mooring_sequence", 0),
        ("pycnmix", 0),  # every point has a duration
    ],
)
def test_fill_counts_without_bathymetry(tmp_path, name, fills):
    """Enrich with no bathymetry file: depths become -9999, casts get the 999 h fill."""
    empty = tmp_path / "bathy"
    empty.mkdir()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = cruiseplan.enrich(
            config_file=CONFIGS[name],
            output_dir=str(tmp_path / "out"),
            add_depths=True,
            bathy_source="gebco2025",
            bathy_dir=str(empty),
        )
    tl = timeline(Path(result.output_file))
    filled = [r for r in tl if r.duration_is_fill]
    assert len(filled) == fills
    assert all(r.duration_minutes == FILL_MIN for r in filled)


@pytest.fixture
def halifax_source(monkeypatch):
    """Point the gebco2025 source at the real Halifax subset file."""
    monkeypatch.setattr(bathy_module, "source_file", lambda source: (HALIFAX_FILE, 0.0))
    return "gebco2025"


@pytest.mark.parametrize(
    ("keep_op_depth", "depth_used"),
    [(True, 58.0), (False, 93.5)],
)
def test_depth_from_gebco_subset(tmp_path, halifax_source, keep_op_depth, depth_used):
    """tc4 with STN_001 at 44.40 N, 63.50 W: GEBCO depth 93.5 m (cell-center mean)."""
    cfg = load("tc4_mixed_ops")
    stn = cfg["points"][0]
    stn["latitude"], stn["longitude"] = 44.40, -63.50
    if not keep_op_depth:
        del stn["operation_depth_m"]
    result = cruiseplan.enrich(
        config_file=write(tmp_path, cfg, "tc4_halifax"),
        output_dir=str(tmp_path / "out"),
        add_depths=True,
        bathy_source=halifax_source,
        bathy_dir=str(FIXTURES / "bathymetry"),
    )
    tl = timeline(Path(result.output_file))
    row = by_label(tl, "STN_001")
    assert row.water_depth_m == pytest.approx(93.5)
    assert row.operation_depth_m == pytest.approx(depth_used)
    assert row.duration_minutes == pytest.approx(depth_used / 60 * 2 + 30)
    nm = gc_nm((44.6488, -63.5752), (44.40, -63.50))
    assert tl[1].dist_nm == pytest.approx(nm, abs=NM_TOL)  # 15.28 nm
    assert_time(row.start_time, datetime(1970, 1, 1) + timedelta(minutes=nm * 6))


# =============================================================================
# Output files
# =============================================================================


def schedule_files(tmp_path: Path, name: str) -> tuple[list[dict], Path]:
    """Write CSV and NetCDF; return CSV rows and NetCDF path."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            files = []
            for fmt in ("csv", "netcdf"):
                files += cruiseplan.schedule(
                    config_file=CONFIGS[name], output_dir=str(tmp_path), format=fmt
                ).files_created
        finally:
            logging.disable(logging.NOTSET)
    csv_path = next(Path(f) for f in files if str(f).endswith(".csv"))
    nc_path = next(Path(f) for f in files if str(f).endswith(".nc"))
    with csv_path.open() as fh:
        return list(csv.DictReader(fh)), nc_path


@pytest.mark.parametrize(
    "name", ["pycnmix", "coldsnap", "mooring_sequence", "tc2_two_legs"]
)
def test_csv_columns(tmp_path, name):
    """CSV duration (0.1 h), distance (0.1 nm) and times (within the minute)."""
    rows, _ = schedule_files(tmp_path, name)
    hand = hand_schedule(load(name))
    assert len(rows) == len(hand)
    for r, h in zip(rows, hand, strict=True):
        assert r["label"] == h.name
        assert float(r["Duration [hrs]"]) == pytest.approx(
            round(h.minutes / 60, 1), abs=0.051
        )
        assert float(r["Transit dist [nm]"]) == pytest.approx(round(h.nm, 1), abs=0.051)
        start = datetime.fromisoformat(r["start_time"])
        assert abs((start - h.start).total_seconds()) < 60


def test_csv_times_nearest_minute(tmp_path):
    """CSV start times equal the hand start rounded to the nearest minute."""
    rows, _ = schedule_files(tmp_path, "pycnmix")
    hand = hand_schedule(load("pycnmix"))
    for r, h in zip(rows, hand, strict=True):
        nearest = (h.start + timedelta(seconds=30)).replace(second=0, microsecond=0)
        assert datetime.fromisoformat(r["start_time"]) == nearest, h.name


@pytest.mark.parametrize(
    "name", ["pycnmix", "coldsnap", "mooring_sequence", "tc2_two_legs"]
)
def test_netcdf_values(tmp_path, name):
    """NetCDF start times, durations (minutes) and distances match hand values."""
    _, nc_path = schedule_files(tmp_path, name)
    hand = hand_schedule(load(name))
    with xr.open_dataset(nc_path) as ds:
        assert ds.sizes["obs"] == len(hand)
        times = [t.astype("datetime64[us]").item() for t in ds.time.values]
        for i, h in enumerate(hand):
            assert str(ds.name[i].values) == h.name
            assert_time(times[i], h.start)
            assert ds.duration.attrs["units"] == "minute"
            assert float(ds.duration[i]) == pytest.approx(h.minutes, abs=0.01)
            assert float(ds.planned_duration[i]) == pytest.approx(h.minutes, abs=0.01)
            assert float(ds.distance[i]) == pytest.approx(h.nm, abs=NM_TOL)
            assert int(ds.duration_fill_flag[i]) == int(h.is_fill)


# =============================================================================
# transit_minutes (actual transit time into an operation)
# =============================================================================


def pycnmix_with_transit_minutes() -> dict:
    """pycnmix: Transit to NISS (33.61 nm, 201.65 min at 10 kt) took 150 min."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] == "NISS":
            p["transit_minutes"] = 150.0
    return cfg


def test_transit_minutes_every_row(tmp_path):
    """All rows of the copy match the hand schedule."""
    cfg = pycnmix_with_transit_minutes()
    assert_rows_match(timeline(write(tmp_path, cfg, "tm")), hand_schedule(cfg))


def test_transit_minutes_moves_later_rows_and_shows_its_speed(tmp_path):
    """NISS and every later row 201.65 - 150 = 51.65 min earlier; 33.61 nm / 2.5 h."""
    base = timeline(CONFIGS["pycnmix"])
    tl = timeline(write(tmp_path, pycnmix_with_transit_minutes(), "tm"))
    nm = gc_nm((-74.621, 164.224), (-75.14, 163.42))
    assert nm == pytest.approx(33.61, abs=0.01)
    planned = transit_min(nm, 10.0)
    assert planned == pytest.approx(201.65, abs=0.01)
    transit = by_label(tl, "Transit to NISS")
    assert transit.duration_minutes == pytest.approx(150.0)
    assert transit.planned_duration_minutes == pytest.approx(planned, abs=MIN_TOL)
    assert transit.dist_nm == pytest.approx(nm, abs=NM_TOL)
    assert transit.vessel_speed_kt == pytest.approx(nm / 2.5, abs=0.01)  # 13.44 kt
    k = next(i for i, r in enumerate(tl) if r.label == "NISS")
    for a, b in zip(base[k:], tl[k:], strict=True):
        shift = (b.start_time - a.start_time).total_seconds() / 60
        assert shift == pytest.approx(150.0 - planned, abs=0.01), b.label
    for a, b in zip(base[:k], tl[:k], strict=True):
        assert a.start_time == b.start_time


def test_transit_minutes_without_a_transit_is_ignored(tmp_path, caplog):
    """LDEO_heavy_shallow_deployment sits on the recovery: no transit, a warning."""
    cfg = load("pycnmix")
    for p in cfg["points"]:
        if p["name"] == "LDEO_heavy_shallow_deployment":
            p["transit_minutes"] = 30.0
    with caplog.at_level(logging.WARNING, logger="cruiseplan.timeline.scheduler"):
        tl = timeline(write(tmp_path, cfg, "tm0"))
    base = timeline(CONFIGS["pycnmix"])
    assert [r.start_time for r in tl] == [r.start_time for r in base]
    assert any(
        "LDEO_heavy_shallow_deployment" in m and "transit_minutes 30 is ignored" in m
        for m in caplog.messages
    )
