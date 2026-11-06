"""Enriched YAML keeps the cruise-level parameters the schedule is computed from."""

from pathlib import Path

import pytest

import cruiseplan
from cruiseplan.config.yaml_io import load_yaml
from cruiseplan.runtime.cruise import CruiseInstance

ROOT = Path(__file__).parent.parent.parent
CONFIGS = [
    ROOT / "data" / "pycnmix-2026-v1.yaml",
    ROOT / "tests" / "fixtures" / "tc1_single.yaml",
    ROOT / "tests" / "fixtures" / "mooring_sequence_greenland.yaml",
]
PARAMETERS = [
    "start_date",
    "start_time",
    "default_vessel_speed_kt",
    "default_distance_between_stations_km",
    "turnaround_time_minutes",
    "ctd_descent_rate_m_s",
    "ctd_ascent_rate_m_s",
]


@pytest.mark.parametrize("config", CONFIGS, ids=lambda p: p.stem)
def test_enriched_config_keeps_parameters(config, tmp_path):
    """Every parameter stated in the source YAML has the same value after enrich."""
    result = cruiseplan.enrich(
        config_file=config,
        output_dir=str(tmp_path),
        bathy_dir=str(tmp_path / "no_bathymetry"),
    )
    original = CruiseInstance(config).config
    enriched = CruiseInstance(result.output_file).config
    for name in PARAMETERS:
        assert getattr(enriched, name) == getattr(original, name), name


def test_pycnmix_start_date_survives_enrich(tmp_path):
    """pycnmix starts 2026-02-24 12:00; the enriched file must not fall back to 1970."""
    result = cruiseplan.enrich(
        config_file=CONFIGS[0],
        output_dir=str(tmp_path),
        bathy_dir=str(tmp_path / "no_bathymetry"),
    )
    enriched = load_yaml(result.output_file)
    assert str(enriched["start_date"]) == "2026-02-24"
    assert str(enriched["start_time"]) == "12:00"
    assert [p["name"] for p in enriched["ports"]] == [
        "port_lyttelton",
        "port_jang_bogo",
    ]


def test_pycnmix_clusters_resolve():
    """Every activity named in the pycnmix legs exists in its catalog."""
    cruise = CruiseInstance(CONFIGS[0])
    leg2 = next(leg for leg in cruise.config.legs if leg.name == "Leg2")
    names = [a if isinstance(a, str) else a.name for a in leg2.clusters[0].activities]
    assert "LDEO_heavy_shallow_recovery" in names
    assert "LDEO_heavy_shallow_deployment" in names
    assert names.index("LDEO_heavy_shallow_recovery") < names.index(
        "LDEO_heavy_shallow_deployment"
    )
