"""
Legs start at their given time, and every wait before a leg is a row.

pycnmix (data/pycnmix-2026-v1.yaml) gives each leg a start and an end:
Leg1 2026-02-24 12:00 to 03-05 00:00, Leg2 03-05 12:00 to 03-17 00:00,
Leg3 03-17 12:00. Scheduled, Leg1 arrives at Jangbogo on 03-08 07:56
(after its given end and Leg2's given start), Leg2 on 03-12 18:42; Leg3
waits there until 03-17 12:00.
"""

import logging
import warnings
from datetime import datetime
from pathlib import Path

import pytest
import yaml

import cruiseplan

PYCNMIX = Path(__file__).parents[2] / "data" / "pycnmix-2026-v1.yaml"


def _timeline(path, caplog=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if caplog is None:
            return cruiseplan.schedule(config_file=path, format=None).timeline
        with caplog.at_level(logging.WARNING, logger="cruiseplan.timeline.scheduler"):
            return cruiseplan.schedule(config_file=path, format=None).timeline


def _write(tmp_path, edit):
    cfg = yaml.safe_load(PYCNMIX.read_text())
    edit(cfg)
    path = tmp_path / "pycnmix.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    return path


def _legs(cfg, keep=()):
    for leg in cfg["legs"]:
        for k in ("start_date", "start_time", "end_date", "end_time"):
            if k not in keep:
                leg.pop(k, None)


def _first_of(timeline, leg):
    return next(r for r in timeline if r.leg_name == leg)


def test_leg_waits_for_its_given_start(caplog):
    """Leg3 waits at Jangbogo from Leg2's arrival until 2026-03-17 12:00."""
    tl = _timeline(PYCNMIX, caplog)
    wait = _first_of(tl, "Leg3")
    assert wait.kind == "wait"
    assert wait.label == "Waiting before Jangbogo Station"
    leg2_end = next(r for r in reversed(tl) if r.leg_name == "Leg2").end_time
    assert wait.start_time == leg2_end
    assert wait.end_time == datetime(2026, 3, 17, 12, 0)
    assert "leg start 2026-03-17 12:00" in wait.comment
    port = tl[tl.index(wait) + 1]
    assert (port.kind, port.start_time) == ("port", datetime(2026, 3, 17, 12, 0))
    messages = caplog.messages
    assert any(
        "Leg Leg2: given start 2026-03-05 12:00 is before the ship can depart" in m
        for m in messages
    )
    assert any(
        "Leg Leg1 arrives 2026-03-08 07:55, after its given end 2026-03-05 00:00" in m
        for m in messages
    )


def test_leg_delay_is_a_wait_row(tmp_path):
    """Leg2 delay_start_minutes 120 (no given times): a 120 min wait at Jangbogo."""

    def edit(cfg):
        _legs(cfg)
        cfg["legs"][1]["delay_start_minutes"] = 120.0

    tl = _timeline(_write(tmp_path, edit))
    wait = _first_of(tl, "Leg2")
    assert (wait.kind, wait.duration_minutes) == ("wait", 120.0)
    assert "delay_start_minutes 120 of leg Leg2" in wait.comment
    leg1_end = next(r for r in reversed(tl) if r.leg_name == "Leg1").end_time
    assert wait.start_time == leg1_end
    # no gaps anywhere
    for a, b in zip(tl, tl[1:], strict=False):
        assert b.start_time == a.end_time, b.label


def test_given_start_and_leg_delay_add_up(tmp_path):
    """Leg3: waits until its start (03-17 12:00), then 60 min more."""

    def edit(cfg):
        cfg["legs"][2]["delay_start_minutes"] = 60.0

    wait = _first_of(_timeline(_write(tmp_path, edit)), "Leg3")
    assert wait.end_time == datetime(2026, 3, 17, 13, 0)
    assert "leg start 2026-03-17 12:00" in wait.comment
    assert "delay_start_minutes 60 of leg Leg3" in wait.comment


def test_departure_port_delay_is_a_wait_row(tmp_path):
    """port_lyttelton +60: the cruise starts with 60 min waiting at Lyttelton."""

    def edit(cfg):
        _legs(cfg)
        port = next(p for p in cfg["ports"] if p["name"] == "port_lyttelton")
        port["delay_start_minutes"] = 60.0

    tl = _timeline(_write(tmp_path, edit))
    first, port = tl[0], tl[1]
    assert (first.kind, first.label) == ("wait", "Waiting before Lyttelton")
    assert first.start_time == datetime(2026, 2, 24, 12, 0)
    assert first.duration_minutes == pytest.approx(60.0)
    assert port.start_time == datetime(2026, 2, 24, 13, 0)


def test_leg_start_holds_after_unabsorbed_negative_delay(tmp_path):
    """
    NISS (Leg2's first operation) 45 min earlier than the transit in allows.

    45 min cannot be taken off, so Leg2 runs as before; Leg3 still starts
    at its given 03-17 12:00, its wait computed from Leg2's actual arrival.
    """
    from hand_calc import hand_schedule

    base = _timeline(PYCNMIX)
    transit = next(r for r in base if r.label == "Transit to NISS")

    def edit(cfg):
        niss = next(p for p in cfg["points"] if p["name"] == "NISS")
        niss["delay_start_minutes"] = -(transit.duration_minutes + 45.0)

    path = _write(tmp_path, edit)
    tl = _timeline(path)
    wait = _first_of(tl, "Leg3")
    leg2_end = next(r for r in reversed(tl) if r.leg_name == "Leg2").end_time
    assert wait.start_time == leg2_end
    assert wait.end_time == datetime(2026, 3, 17, 12, 0)
    hand = hand_schedule(yaml.safe_load(path.read_text()))
    assert [r.name for r in hand] == [r.label for r in tl]
    assert hand[tl.index(wait)].end == wait.end_time


def test_leg_scheduled_alone_starts_at_its_given_start():
    """--leg Leg3: no 21-day wait from the cruise start; Leg3 starts 03-17 12:00."""
    from hand_calc import hand_schedule

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tl = cruiseplan.schedule(config_file=PYCNMIX, format=None, leg="Leg3").timeline
    assert tl[0].kind == "port"
    assert tl[0].start_time == datetime(2026, 3, 17, 12, 0)
    hand = hand_schedule(yaml.safe_load(PYCNMIX.read_text()), only="Leg3")
    assert [r.name for r in hand] == [r.label for r in tl]
    assert abs((hand[-1].end - tl[-1].end_time).total_seconds()) < 60


def test_leg_start_with_an_offset_is_utc(tmp_path):
    """Leg3 start "2026-03-17T12:00:00+13:00" (NZDT) is 03-16 23:00 UTC."""

    def edit(cfg):
        cfg["legs"][2]["start_date"] = "2026-03-17T12:00:00+13:00"
        cfg["legs"][2].pop("start_time", None)

    wait = _first_of(_timeline(_write(tmp_path, edit)), "Leg3")
    assert wait.end_time == datetime(2026, 3, 16, 23, 0)


def test_unquoted_yaml_date_is_read(tmp_path):
    """start_date: 2026-03-17 without quotes (a YAML date) works like the text."""
    path = tmp_path / "pycnmix.yaml"
    text = PYCNMIX.read_text().replace(
        'start_date: "2026-03-17"', "start_date: 2026-03-17"
    )
    assert "start_date: 2026-03-17\n" in text
    path.write_text(text)
    wait = _first_of(_timeline(path), "Leg3")
    assert wait.end_time == datetime(2026, 3, 17, 12, 0)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("start_time", "noon", "must be YYYY-MM-DD and HH:MM"),
        ("start_date", "17/03/2026", "must be YYYY-MM-DD and HH:MM"),
        ("start_time", 720, "Write the time in quotes"),
    ],
)
def test_bad_leg_time_fails_validation(tmp_path, field, value, message):
    """validate reports a leg time it cannot read (720: YAML's reading of 12:00)."""

    def edit(cfg):
        cfg["legs"][2][field] = value

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = cruiseplan.validate(
            config_file=_write(tmp_path, edit), check_depths=False
        )
    assert not result.success
    assert any(message in e for e in result.errors), result.errors


def test_enrich_keeps_leg_times(tmp_path):
    """The enriched file keeps each leg's start and end (read as cruiseplan does)."""
    from cruiseplan.config.yaml_io import load_yaml

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = cruiseplan.enrich(
            config_file=PYCNMIX,
            output_dir=str(tmp_path),
            add_depths=False,
            add_coords=False,
        )
    enriched = load_yaml(result.output_file)
    original = yaml.safe_load(PYCNMIX.read_text())
    for before, after in zip(original["legs"], enriched["legs"], strict=True):
        for k in ("start_date", "start_time", "end_date", "end_time"):
            assert str(after.get(k)) == str(before.get(k)), (before["name"], k)
    assert enriched["start_date"] == original["start_date"]


def test_given_start_is_the_departure_with_time_in_port(tmp_path):
    """
    Jangbogo 24 h in port: Leg3 still departs at 03-17 12:00.

    The ship arrives from Leg2, waits until 03-16 12:00, spends 24 h in
    port and departs at its given start.
    """
    from hand_calc import hand_schedule

    def edit(cfg):
        port = next(p for p in cfg["ports"] if p["name"] == "port_jang_bogo")
        port["duration_minutes"] = 1440.0

    path = _write(tmp_path, edit)
    tl = _timeline(path)
    wait = _first_of(tl, "Leg3")
    port = tl[tl.index(wait) + 1]
    assert wait.end_time == datetime(2026, 3, 16, 12, 0)
    assert (port.kind, port.end_time) == ("port", datetime(2026, 3, 17, 12, 0))
    hand = hand_schedule(yaml.safe_load(path.read_text()))
    assert [r.name for r in hand] == [r.label for r in tl]
    assert hand[tl.index(port)].end == port.end_time
