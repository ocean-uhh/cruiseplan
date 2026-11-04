"""Every duration path uses the 999 h fill value when no duration can be computed."""

import logging
from pathlib import Path

import yaml

import cruiseplan
from cruiseplan.config.values import DEFAULT_DEPTH, DEFAULT_MOORING_DURATION_MIN
from cruiseplan.runtime.cruise import CruiseInstance
from cruiseplan.timeline.scheduler import generate_timeline

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _record(timeline: list[dict], label: str) -> dict:
    """Return the first timeline record with ``label``."""
    return next(r for r in timeline if r["label"] == label)


def _variant(tmp_path: Path, fixture: str, station: str, **changes: object) -> Path:
    """Write ``fixture`` with ``station`` fields changed (None removes a field)."""
    config = yaml.safe_load((FIXTURES / fixture).read_text())
    point = next(p for p in config["points"] if p["name"] == station)
    for key, value in changes.items():
        if value is None:
            point.pop(key, None)
        else:
            point[key] = value
    path = tmp_path / fixture
    path.write_text(yaml.safe_dump(config, sort_keys=False))
    return path


def test_schedule_mooring_without_duration_gets_fill():
    """tc2 STN_002 (mooring, no duration) was 60 min via a missing config field."""
    timeline = cruiseplan.schedule(FIXTURES / "tc2_two_legs.yaml", format=None).timeline
    mooring = _record(timeline, "STN_002")
    assert mooring["duration_minutes"] == DEFAULT_MOORING_DURATION_MIN
    assert mooring["duration_is_fill"] is True


def test_mooring_with_operation_depth_still_gets_fill(tmp_path):
    """A mooring with an operation_depth is not timed as a CTD cast."""
    config = _variant(tmp_path, "tc2_two_legs.yaml", "STN_002", operation_depth=1000.0)
    timeline = cruiseplan.schedule(config, format=None).timeline
    mooring = _record(timeline, "STN_002")
    assert mooring["duration_is_fill"] is True
    assert mooring["duration_minutes"] == DEFAULT_MOORING_DURATION_MIN


def test_fill_duration_summary_excludes_fills():
    """The summary counts fill operations and totals the schedule without them."""
    from cruiseplan.timeline.scheduler import fill_duration_summary

    timeline = [
        {"duration_is_fill": True, "duration_minutes": DEFAULT_MOORING_DURATION_MIN},
        {"duration_is_fill": False, "duration_minutes": 120.0},
        {"duration_is_fill": False, "duration_minutes": 360.0},
    ]
    summary = fill_duration_summary(timeline)
    assert "1 operation(s) at the fill duration (1 x 999 h)" in summary
    assert "schedule total excluding fills" in summary
    no_fills = [{"duration_is_fill": False, "duration_minutes": 60.0}]
    assert fill_duration_summary(no_fills) is None


def test_enrich_and_schedule_agree_on_mooring_fill(tmp_path):
    """enrich writes the fill value; scheduling the enriched file flags it the same way."""
    result = cruiseplan.enrich(
        FIXTURES / "tc2_two_legs.yaml",
        output_dir=str(tmp_path),
        bathy_dir=str(tmp_path / "no_bathymetry"),
    )
    cruise = CruiseInstance(result.output_file)
    assert cruise.point_registry["STN_002"].duration == DEFAULT_MOORING_DURATION_MIN
    timeline = generate_timeline(cruise)
    mooring = _record(timeline, "STN_002")
    assert mooring["duration_minutes"] == DEFAULT_MOORING_DURATION_MIN
    assert mooring["duration_is_fill"] is True


def test_ctd_without_depth_gets_fill():
    """tc2 STN_001 (CTD, no depth) was scheduled for 0 min."""
    timeline = cruiseplan.schedule(FIXTURES / "tc2_two_legs.yaml", format=None).timeline
    ctd = _record(timeline, "STN_001")
    assert ctd["duration_minutes"] == DEFAULT_MOORING_DURATION_MIN
    assert ctd["duration_is_fill"] is True


def test_ctd_at_fill_depth_gets_fill(tmp_path):
    """tc1 STN_001 with water_depth at the fill value is not a 0-minute cast."""
    path = _variant(tmp_path, "tc1_single.yaml", "STN_001", water_depth=DEFAULT_DEPTH)
    timeline = cruiseplan.schedule(path, format=None).timeline
    ctd = _record(timeline, "STN_001")
    assert ctd["duration_minutes"] == DEFAULT_MOORING_DURATION_MIN
    assert ctd["duration_is_fill"] is True


def test_ctd_with_depth_is_computed():
    """tc1 STN_001 (2850 m, 1 m/s, 30 min turnaround) keeps its computed 125 min."""
    timeline = cruiseplan.schedule(FIXTURES / "tc1_single.yaml", format=None).timeline
    ctd = _record(timeline, "STN_001")
    assert ctd["duration_minutes"] == 125.0
    assert ctd["duration_is_fill"] is False


def test_operation_type_without_rule_gets_fill(tmp_path):
    """A water_sampling point with no depth and no duration was 0 min."""
    path = _variant(
        tmp_path,
        "tc1_single.yaml",
        "STN_001",
        operation_type="water_sampling",
        water_depth=None,
    )
    timeline = cruiseplan.schedule(path, format=None).timeline
    record = _record(timeline, "STN_001")
    assert record["duration_minutes"] == DEFAULT_MOORING_DURATION_MIN
    assert record["duration_is_fill"] is True


def test_fill_warning_names_each_station_once(caplog):
    """tc3 visits STN_001 in several legs; the warning names it once."""
    cruise = CruiseInstance(FIXTURES / "tc3_clusters.yaml")
    with caplog.at_level(logging.WARNING, logger="cruiseplan.timeline.scheduler"):
        generate_timeline(cruise)
    messages = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    stn_001 = [m for m in messages if m.startswith("Operation STN_001:")]
    assert len(stn_001) == 1
    assert "fill duration 999 h" in stn_001[0]


def test_ports_and_transits_are_not_flagged():
    """Ports take 0 minutes and transits are computed; neither is a fill."""
    timeline = cruiseplan.schedule(FIXTURES / "tc1_single.yaml", format=None).timeline
    for record in timeline:
        if record["op_type"] in ("port", "transit"):
            assert not record["duration_is_fill"]
