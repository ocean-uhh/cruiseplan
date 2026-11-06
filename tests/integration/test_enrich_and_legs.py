"""
Enrich keeps port fields; timelines built without runtime legs keep buffers.

pycnmix: catalog ports port_lyttelton and port_jang_bogo; every leg has
buffer_time_minutes: 360.
"""

import logging
import warnings
from pathlib import Path

import yaml

import cruiseplan
from cruiseplan.config.yaml_io import load_yaml
from cruiseplan.runtime.cruise import CruiseInstance
from cruiseplan.timeline.scheduler import generate_timeline

ROOT = Path(__file__).parents[2]
PYCNMIX = ROOT / "data" / "pycnmix-2026-v1.yaml"


def test_enrich_keeps_port_timezone(tmp_path):
    """A catalog port's timezone and equipment are written back by enrich."""
    cfg = yaml.safe_load(PYCNMIX.read_text())
    port = next(p for p in cfg["ports"] if p["name"] == "port_lyttelton")
    port["timezone"] = "GMT+13"
    port["equipment"] = "crane"
    config = tmp_path / "pycnmix.yaml"
    config.write_text(yaml.safe_dump(cfg, sort_keys=False))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            result = cruiseplan.enrich(
                config_file=config,
                output_dir=str(tmp_path / "out"),
                add_depths=False,
                add_coords=False,
                expand_sections=False,
            )
        finally:
            logging.disable(logging.NOTSET)
    enriched = next(Path(f) for f in result.files_created if str(f).endswith(".yaml"))
    ports = yaml.safe_load(enriched.read_text())["ports"]
    (port,) = [p for p in ports if p["name"] == "port_lyttelton"]
    assert port["timezone"] == "GMT+13"
    assert port["equipment"] == "crane"
    # Leg 1 refers to the port by name: its inline copy keeps them too
    legs = yaml.safe_load(enriched.read_text())["legs"]
    assert legs[0]["departure_port"]["timezone"] == "GMT+13"
    assert legs[0]["departure_port"]["equipment"] == "crane"
    assert legs[2]["arrival_port"]["timezone"] == "GMT+13"


def test_timeline_without_runtime_legs_has_buffers():
    """generate_timeline(cruise) schedules each leg's buffer, as schedule() does."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            cruise = CruiseInstance.from_dict(load_yaml(PYCNMIX))
            cruise.add_station_defaults()
            timeline = generate_timeline(cruise)
        finally:
            logging.disable(logging.NOTSET)
    buffers = [r for r in timeline if r.kind == "buffer"]
    assert [r.leg_name for r in buffers] == ["Leg1", "Leg2", "Leg3"]
    assert all(r.duration_minutes == 360.0 for r in buffers)


def test_station_picker_lines_and_areas_keep_speed_and_duration():
    """Interactive lines keep their speed, areas their duration."""
    from cruiseplan.interactive.station_picker import StationPicker

    line = StationPicker._create_line_definition(
        None,
        {"start": {"lat": 60.0, "lon": -40.0}, "end": {"lat": 61.0, "lon": -40.0}},
        1,
    )
    area = StationPicker._create_area_definition(
        None, {"points": [(-40.0, 60.0), (-39.0, 60.0), (-39.0, 61.0)]}, 1
    )
    assert line.vessel_speed_kt == 10.0
    assert area.duration_minutes == 9999.0
