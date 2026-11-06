"""Provenance and fill-duration markers in the schedule outputs."""

import csv
import hashlib
from pathlib import Path

import pytest
import xarray as xr

import cruiseplan
from cruiseplan.forecast.reader import netcdf_to_activity_records
from cruiseplan.output.html_generator import UNASSIGNED_LEG, HTMLGenerator
from cruiseplan.output.latex_generator import _is_station_record
from cruiseplan.runtime.cruise import CruiseInstance
from cruiseplan.timeline.scheduler import generate_timeline

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="module")
def tc2_outputs(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Schedule tc2 (one CTD without depth, one mooring without duration)."""
    out = tmp_path_factory.mktemp("tc2")
    cruiseplan.schedule(
        FIXTURES / "tc2_two_legs.yaml",
        output_dir=str(out),
        format="html,latex,csv,netcdf",
    )
    files = {
        "nc": "_schedule.nc",
        "csv": "_schedule.csv",
        "html": "_schedule.html",
        "stations": "_stations.tex",
        "work_days": "_work_days.tex",
    }
    return {key: next(out.glob(f"*{suffix}")) for key, suffix in files.items()}


def test_netcdf_global_provenance(tc2_outputs):
    """Version, source file and hash, bathymetry, parameters and a UTC date."""
    config = FIXTURES / "tc2_two_legs.yaml"
    with xr.open_dataset(tc2_outputs["nc"]) as ds:
        attrs = dict(ds.attrs)
    assert attrs["cruiseplan_version"]
    assert attrs["source_config"] == "tc2_two_legs.yaml"
    assert (
        attrs["source_config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    )
    assert attrs["bathymetry_source"] == "none (water depths from configuration)"
    assert attrs["default_vessel_speed_kt"] == 10.0
    assert attrs["ctd_descent_rate_m_s"] == 1.0
    assert attrs["ctd_ascent_rate_m_s"] == 1.0
    assert attrs["turnaround_time_min"] == 30.0
    assert attrs["date_created"].endswith("Z")
    assert attrs["creation_date"] == attrs["date_created"]


def test_netcdf_flags_fill_durations(tc2_outputs):
    """duration_fill_flag is 1 exactly for the two operations without a duration."""
    with xr.open_dataset(tc2_outputs["nc"]) as ds:
        flagged = sorted(
            str(n) for n in ds["name"].values[ds["duration_fill_flag"].values == 1]
        )
        assert ds.attrs["fill_duration_count"] == 2
        assert ds.attrs["fill_duration_hours"] == 999.0
    assert flagged == ["STN_001", "STN_002"]


def test_netcdf_fill_flag_round_trips(tc2_outputs):
    """Records read back from the NetCDF carry duration_is_fill."""
    with xr.open_dataset(tc2_outputs["nc"]) as ds:
        records = netcdf_to_activity_records(ds)
    flags = {r.label: r.duration_is_fill for r in records}
    assert flags["STN_001"] is True
    assert flags["Transit to STN_001"] is False


def test_csv_duration_note(tc2_outputs):
    """CSV rows for fill durations say so in the last column."""
    with tc2_outputs["csv"].open(newline="", encoding="utf-8") as f:
        rows = {row["label"]: row for row in csv.DictReader(f)}
    assert rows["STN_002"]["Duration note"] == "fill value (999 h)"
    assert rows["Transit to STN_002"]["Duration note"] == ""


def test_html_provenance_and_fill_notice(tc2_outputs):
    """HTML names the fill operations at the top and lists provenance at the end."""
    html = tc2_outputs["html"].read_text()
    assert "2 operation(s) at the fill duration (2 x 999 h)" in html
    assert "schedule total excluding fills:" in html
    assert "999.0 (fill)" in html
    assert "source_config: tc2_two_legs.yaml" in html
    assert "date_created: " in html


def test_tex_header_comments(tc2_outputs):
    """Both TeX tables start with provenance comment lines."""
    for key in ("stations", "work_days"):
        lines = tc2_outputs[key].read_text().splitlines()
        assert lines[0].startswith("% cruiseplan_version: ")
        assert "% source_config: tc2_two_legs.yaml" in lines
        assert "% fill duration 999 h used for: STN_001, STN_002" in lines


def test_letsgo_station_test_uses_record_kind(tmp_path):
    """tc_decmin: 'Transit to test_station_1' is not a station despite its label."""
    result = cruiseplan.schedule(
        FIXTURES / "tc_decmin_only.yaml", output_dir=str(tmp_path), format="netcdf"
    )
    with xr.open_dataset(result.files_created[0]) as ds:
        records = netcdf_to_activity_records(ds)
    kinds = {r.label: _is_station_record(r) for r in records}
    assert kinds["test_station_1"] is True
    assert kinds["test_station_2"] is True
    assert kinds["Transit to test_station_1"] is False
    assert kinds["Test Port"] is False


def test_is_station_record_fallback_covers_ctd_and_prefixes():
    """Records without operation_class fall back to the activity value and label prefix."""
    from types import SimpleNamespace

    def record(**kwargs):
        kwargs.setdefault("label", "")
        return SimpleNamespace(**kwargs)

    # Older files: no usable operation_class, fall back to activity / label.
    assert _is_station_record(record(operation_class="unknown", activity="CTD"))
    assert _is_station_record(record(operation_class=None, activity="Mooring"))
    assert _is_station_record(
        record(operation_class="unknown", activity="T", label="FD-01")
    )
    assert _is_station_record(
        record(operation_class="unknown", activity="T", label="svp-2")
    )
    assert not _is_station_record(
        record(operation_class="unknown", activity="Transit", label="port call")
    )
    # Primary path keys on operation_class and op_type.
    assert _is_station_record(record(operation_class="PointOperation", op_type="CTD"))
    assert not _is_station_record(
        record(operation_class="PointOperation", op_type="port")
    )


def test_html_unknown_leg_is_listed_separately():
    """tc2: an activity whose leg is not configured is not merged into the first leg."""
    cruise = CruiseInstance(FIXTURES / "tc2_two_legs.yaml")
    timeline = generate_timeline(cruise)
    timeline[-1] = timeline[-1].replace(leg_name="Leg_Missing")
    groups = HTMLGenerator()._group_activities_by_leg(cruise.config, timeline)
    assert [a.label for a in groups[UNASSIGNED_LEG]["activities"]] == [
        timeline[-1].label
    ]
    assert timeline[-1] not in groups["Leg_Atlantic"]["activities"]
    assert timeline[-1] not in groups["Leg_North"]["activities"]
