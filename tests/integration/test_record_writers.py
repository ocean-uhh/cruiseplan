"""
Writers read the timeline records: positions, depths, kinds and ports.

Built from tests/fixtures/tc4_mixed_ops.yaml: Halifax, CTD STN_001 at
(45N, 50W), the ADCP_Survey line (46N, 50W) -> (47N, 50W), Area_01 and
Cadiz, all in one leg.
"""

import dataclasses
import logging
import warnings
from pathlib import Path

import pytest

from cruiseplan.config.yaml_io import load_yaml
from cruiseplan.output.kml_generator import generate_kml_schedule
from cruiseplan.output.latex_generator import LaTeXGenerator, _format_depth_for_latex
from cruiseplan.output.map_generator import extract_points_from_timeline
from cruiseplan.runtime.cruise import CruiseInstance
from cruiseplan.timeline.scheduler import (
    _calculate_leg_statistics,
    generate_timeline,
)

TC4 = Path(__file__).parents[2] / "tests" / "fixtures" / "tc4_mixed_ops.yaml"


@pytest.fixture(scope="module")
def tc4():
    """Cruise and timeline of tc4_mixed_ops."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            cruise = CruiseInstance.from_dict(load_yaml(TC4))
            cruise.add_station_defaults()
            timeline = generate_timeline(cruise)
        finally:
            logging.disable(logging.NOTSET)
    return cruise, timeline


def _record(timeline, label):
    (record,) = [r for r in timeline if r.label == label]
    return record


def test_latex_line_row_prints_both_ends(tc4):
    """The survey row runs from the entry (46N) to the exit (47N)."""
    cruise, timeline = tc4
    rows = LaTeXGenerator()._generate_stations_rows(cruise.config, timeline)
    (row,) = [r for r in rows if r["station"] == "ADCP-Survey"]
    start, end = row["position"].split(") to (")
    assert "46" in start
    assert "47" in end


def test_latex_depth_zero_is_a_depth(tc4):
    """An operation depth of 0 m is printed, not replaced by the water depth."""
    _, timeline = tc4
    record = dataclasses.replace(
        _record(timeline, "STN_001"), operation_depth_m=0.0, water_depth_m=4000.0
    )
    assert _format_depth_for_latex(record) == "0"


def test_kml_line_is_a_linestring(tc4, tmp_path):
    """The survey is drawn as a line from entry to exit in the line style."""
    cruise, timeline = tc4
    kml = generate_kml_schedule(cruise.config, timeline, tmp_path / "s.kml")
    text = kml.read_text()
    placemark = text.split("<name>ADCP_Survey</name>")[1].split("</Placemark>")[0]
    assert "#lineOpStyle" in placemark
    assert "<LineString>" in placemark
    assert "-50.0,46.0,0" in placemark
    assert "-50.0,47.0,0" in placemark
    station = text.split("<name>STN_001</name>")[1].split("</Placemark>")[0]
    assert "#stationStyle" in station


def test_map_points_ports(tc4):
    """Ports are labelled departure/arrival and left out with include_ports=False."""
    _, timeline = tc4
    points = {p["name"]: p for p in extract_points_from_timeline(timeline)}
    assert points["Halifax"]["entity_type"] == "departure_port"
    assert points["Cadiz"]["entity_type"] == "arrival_port"
    assert points["STN_001"]["entity_type"] == "station"
    names = {p["name"] for p in extract_points_from_timeline(timeline, False)}
    assert "Halifax" not in names
    assert "Cadiz" not in names
    assert "STN_001" in names


def test_leg_statistics_count_every_station(tc4):
    """Every station-kind record is counted, whatever its operation type."""
    _, timeline = tc4
    record = _record(timeline, "STN_001")
    other = dataclasses.replace(record, op_type="water_sample", label="WS_001")
    stats = _calculate_leg_statistics([*timeline, other])["Mixed_Survey"]
    assert stats["stations"] == 2
    named = stats["stations"] + stats["moorings"] + stats["surveys"] + stats["areas"]
    assert named == stats["total_scientific"]
