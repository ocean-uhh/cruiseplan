"""Depth enrichment without a bathymetry file: fill values and provenance."""

from pathlib import Path

import yaml

import cruiseplan
from cruiseplan.config.values import DEFAULT_DEPTH
from cruiseplan.runtime.cruise import CruiseInstance

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _enrich_without_bathymetry(config: Path, tmp_path: Path) -> dict:
    """Enrich ``config`` with an empty bathymetry directory; return the YAML."""
    result = cruiseplan.enrich(
        config_file=config,
        output_dir=str(tmp_path / "out"),
        add_depths=True,
        bathy_source="gebco2025",
        bathy_dir=str(tmp_path / "no_bathymetry"),
    )
    return yaml.safe_load(Path(result.output_file).read_text())


def test_missing_file_writes_fill_depth(tmp_path):
    """tc4: the station without a depth gets the fill value, not a formula depth."""
    enriched = _enrich_without_bathymetry(FIXTURES / "tc4_mixed_ops.yaml", tmp_path)
    station = next(p for p in enriched["points"] if p["name"] == "STN_001")
    assert station["water_depth_m"] == DEFAULT_DEPTH
    assert "bathymetry_source" not in station


def test_enriched_yaml_records_bathymetry_provenance(tmp_path):
    """The enriched YAML says which source was asked for and how many depths were filled."""
    enriched = _enrich_without_bathymetry(FIXTURES / "tc4_mixed_ops.yaml", tmp_path)
    provenance = enriched["bathymetry_provenance"]
    assert provenance["source"] == "gebco2025"
    assert provenance["file"] == "GEBCO_2025.nc"
    assert provenance["file_found"] is False
    assert provenance["depths_from_source"] == 0
    assert provenance["depths_filled"] == 1
    assert provenance["fill_value"] == DEFAULT_DEPTH


def test_stated_depths_are_kept(tmp_path):
    """mooring sequence: stations with a stated water_depth are not overwritten by the fill."""
    source = yaml.safe_load((FIXTURES / "mooring_sequence_greenland.yaml").read_text())
    stated = {
        p["name"]: p["water_depth_m"] for p in source["points"] if "water_depth_m" in p
    }
    assert stated, "fixture should state at least one depth"
    enriched = _enrich_without_bathymetry(
        FIXTURES / "mooring_sequence_greenland.yaml", tmp_path
    )
    for point in enriched["points"]:
        if point["name"] in stated:
            assert point["water_depth_m"] == stated[point["name"]]


def test_enriched_yaml_with_fill_depth_reloads(tmp_path):
    """The fill value passes water_depth validation when the enriched file is read back."""
    _enrich_without_bathymetry(FIXTURES / "tc4_mixed_ops.yaml", tmp_path)
    enriched_path = next((tmp_path / "out").glob("*_enriched.yaml"))
    cruise = CruiseInstance(enriched_path)
    assert cruise.point_registry["STN_001"].water_depth_m == DEFAULT_DEPTH
