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


def test_netcdf_category_and_line_ends_by_kind(tc4, tmp_path):
    """Schedule rows: one category per kind; the line keeps its two ends."""
    import xarray as xr

    from cruiseplan.output.netcdf_generator import NetCDFGenerator

    cruise, timeline = tc4
    out = tmp_path / "s.nc"
    NetCDFGenerator().generate_master_schedule(timeline, cruise.config, out)
    with xr.open_dataset(out) as ds:
        category = dict(zip(ds.name.values, ds.category.values, strict=True))
        names = list(ds.name.values)
        line = names.index("ADCP_Survey")
        start = (float(ds.start_latitude[line]), float(ds.start_longitude[line]))
        end = (float(ds.end_latitude[line]), float(ds.end_longitude[line]))
        actions = [str(a) for a in ds.action.values]
    assert category["ADCP_Survey"] == "line_operation"
    assert category["Area_01"] == "area_operation"
    assert category["STN_001"] == "point_operation"
    assert category["Halifax"] == "point_operation"
    assert category["Transit to STN_001"] == "transit"
    assert start == pytest.approx((46.0, -50.0))
    assert end == pytest.approx((47.0, -50.0))
    assert "None" not in actions


def test_netcdf_point_and_line_files_from_records(tc4, tmp_path):
    """Derived files are built from the records, not the catalog."""
    import xarray as xr

    from cruiseplan.output.netcdf_generator import NetCDFGenerator

    cruise, timeline = tc4
    gen = NetCDFGenerator()
    points, lines = tmp_path / "p.nc", tmp_path / "l.nc"
    # An empty catalog: the record alone carries the station
    gen.generate_point_operations(
        cruise.config.model_copy(update={"points": []}), timeline, points
    )
    gen.generate_line_operations(cruise.config, timeline, lines)
    with xr.open_dataset(points) as ds:
        assert [str(n) for n in ds.station_name.values] == ["STN_001"]
    with xr.open_dataset(lines) as ds:
        assert [str(n) for n in ds.name.values] == ["ADCP_Survey"]
        assert ds.latitude.values.ravel().tolist() == pytest.approx([46.0, 47.0])


def test_map_points_leave_out_lines_and_areas(tc4):
    """Lines and areas are drawn by their own layers, not as points."""
    _, timeline = tc4
    names = {p["name"] for p in extract_points_from_timeline(timeline)}
    assert "ADCP_Survey" not in names
    assert "Area_01" not in names


def test_buffers_are_not_science_or_transit():
    """pycnmix legs end with a buffer: not scientific, not transit time."""
    import cruiseplan
    from cruiseplan.timeline.scheduler import _categorize_activities

    pycnmix = Path(__file__).parents[2] / "data" / "pycnmix-2026-v1.yaml"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            timeline = cruiseplan.schedule(config_file=pycnmix, format=None).timeline
        finally:
            logging.disable(logging.NOTSET)
    buffers = [r for r in timeline if r.kind == "buffer"]
    assert buffers
    groups = _categorize_activities(timeline)
    grouped = {id(r) for group in groups.values() for r in group}
    assert not any(id(r) in grouped for r in buffers)
    for stats in _calculate_leg_statistics(timeline).values():
        named = (
            stats["stations"] + stats["moorings"] + stats["surveys"] + stats["areas"]
        )
        assert named == stats["total_scientific"]


def test_html_has_no_none_cells(tc4, tmp_path):
    """Missing comments and actions print as empty, not 'None'."""
    from cruiseplan.output.html_generator import generate_html_schedule

    cruise, timeline = tc4
    html = generate_html_schedule(cruise.config, timeline, tmp_path / "s.html")
    assert "<td>None</td>" not in Path(html).read_text()
