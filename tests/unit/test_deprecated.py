"""Every deprecated name and YAML key in one table: it still works, warns, and expires."""

import importlib
import logging
import re
from importlib.metadata import version
from pathlib import Path

import pytest
import yaml
from packaging.version import Version

import cruiseplan
from cruiseplan import _deprecated
from cruiseplan.config.activities import (
    AreaDefinition,
    GeoPoint,
    LineDefinition,
    PointDefinition,
)
from cruiseplan.config.cruise_config import (
    ClusterDefinition,
    CruiseConfig,
    LegDefinition,
)
from cruiseplan.config.loader import prepare_config
from cruiseplan.runtime.cruise import CruiseInstance

FIXTURES = Path(__file__).parents[1] / "fixtures"
PYCNMIX = Path(__file__).parents[2] / "data" / "pycnmix-2026-v1.yaml"
PAGE = Path(__file__).parents[2] / "docs" / "source" / "migrating_0_6_0.rst"
MODELS = (
    CruiseConfig,
    LegDefinition,
    ClusterDefinition,
    PointDefinition,
    LineDefinition,
    AreaDefinition,
    GeoPoint,
)
UNIT_SUFFIXES = ("_minutes", "_m_s", "_kt", "_km", "_m")
# Fields new in 0.6.0 that had no unit-less name before
NEW_KEYS = {"transit_minutes"}


def _fields() -> set[str]:
    """Every field name of the configuration models."""
    return {name for model in MODELS for name in model.model_fields}


def _schedule(path: Path) -> list:
    """Records of a config, without writing files."""
    return cruiseplan.schedule(config_file=path, format=None).timeline


def test_removal_version_is_after_this_version():
    """An entry must be removed once its removal release is reached."""
    assert Version(_deprecated.REMOVED_IN) > Version(version("cruiseplan")), (
        "remove the entries of cruiseplan._deprecated (their release is due)"
    )


def test_yaml_key_table_covers_every_renamed_key():
    """Each field named with a unit has its old (unit-less) name in the table."""
    fields = _fields()
    for name in fields:
        for suffix in UNIT_SUFFIXES:
            stem = name.removesuffix(suffix)
            if stem != name and stem not in fields and name not in NEW_KEYS:
                assert _deprecated.RENAMED_KEYS.get(stem) == name, name
                break
    for old, new in _deprecated.RENAMED_KEYS.items():
        assert new in fields, f"{old} -> {new}: {new} is not a field"
        assert old not in fields, f"{old} is still a field"
    for old in _deprecated.REMOVED_KEYS:
        assert old not in fields


@pytest.mark.parametrize("old", sorted(_deprecated.RENAMED))
def test_every_old_api_name_resolves_and_warns(old):
    """CruiseSchedule and friends still resolve to the new object, with a warning."""
    module, _, attr = old.rpartition(".")
    new_module, _, new_attr = _deprecated.RENAMED[old].rpartition(".")
    with pytest.warns(DeprecationWarning, match=re.escape(_deprecated.message(old))):
        obj = getattr(importlib.import_module(module), attr)
    assert obj is getattr(importlib.import_module(new_module), new_attr)


def test_an_unknown_module_attribute_is_an_attribute_error():
    """A typo is an AttributeError, not a deprecated name."""
    with pytest.raises(AttributeError):
        cruiseplan.timeline.NoSuchName  # noqa: B018


def test_record_dictionary_access_warns_with_the_attribute():
    """record['delay_start'] warns and returns record.delay_start_minutes."""
    record = _schedule(FIXTURES / "tc1_single.yaml")[2]
    with pytest.warns(DeprecationWarning, match="record.delay_start_minutes"):
        assert record["delay_start"] == record.delay_start_minutes
    with pytest.warns(DeprecationWarning, match="record.label"):
        assert record["label"] == "STN_001"


def test_old_keys_fixture_schedules_like_the_new_one(caplog):
    """tc4 in the pre-0.6.0 keys gives the same schedule, with one warning per key."""
    with caplog.at_level(logging.WARNING, logger="cruiseplan.config.loader"):
        old = _schedule(FIXTURES / "tc4_mixed_ops_old_keys.yaml")
    new = _schedule(FIXTURES / "tc4_mixed_ops.yaml")
    assert [r.to_dict() for r in old] == [r.to_dict() for r in new]
    raw = yaml.safe_load((FIXTURES / "tc4_mixed_ops_old_keys.yaml").read_text())
    used = {"operation_depth", "vessel_speed", "duration"}
    assert used <= {
        k for section in ("points", "lines", "areas") for k in raw[section][0]
    }
    for old_key in used:
        expected = _deprecated.key_message(old_key)
        hits = [m for m in caplog.messages if expected in m]
        assert len(hits) == 1, old_key
        assert _deprecated.RENAMED_KEYS[old_key] in hits[0]
        assert "0.7.0" in hits[0]


def test_enrich_writes_the_new_keys(tmp_path):
    """Enriching the old-keys fixture writes only the new key names."""
    result = cruiseplan.enrich(
        config_file=FIXTURES / "tc4_mixed_ops_old_keys.yaml",
        output_dir=str(tmp_path),
        add_depths=False,
    )
    text = Path(result.output_file).read_text()
    for old in _deprecated.RENAMED_KEYS:
        assert not re.search(rf"^\s*(- )?{old}:", text, re.M), old
    for new in ("operation_depth_m", "vessel_speed_kt", "duration_minutes"):
        assert re.search(rf"^\s*(- )?{new}:", text, re.M), new


def test_old_and_new_key_with_different_values_is_an_error():
    """duration and duration_minutes on one area must agree."""
    raw = yaml.safe_load((FIXTURES / "tc4_mixed_ops.yaml").read_text())
    raw["areas"][0]["duration"] = 60.0
    with pytest.raises(ValueError, match="both 'duration' and 'duration_minutes'"):
        prepare_config(raw, "tc4")


def test_delay_end_is_dropped_with_advice(tmp_path, caplog):
    """pycnmix NISS delay_end: 30 is not applied; the warning names the replacements."""
    raw = yaml.safe_load(PYCNMIX.read_text())
    next(p for p in raw["points"] if p["name"] == "NISS")["delay_end"] = 30.0
    path = tmp_path / "delay_end.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False))
    with caplog.at_level(logging.WARNING, logger="cruiseplan.config.loader"):
        changed = _schedule(path)
    base = _schedule(PYCNMIX)
    assert [r.start_time for r in changed] == [r.start_time for r in base]
    message = next(m for m in caplog.messages if "delay_end" in m)
    for advice in ("delay_start_minutes", "buffer_time_minutes", "duration_minutes"):
        assert advice in message


def test_unknown_keys_warn_once_per_key_per_file(caplog):
    """pycnmix areas carry description (4 areas): one warning names it and them."""
    with caplog.at_level(logging.WARNING, logger="cruiseplan.config.loader"):
        CruiseInstance(PYCNMIX)
    hits = [m for m in caplog.messages if "unknown key 'description'" in m]
    assert len(hits) == 1
    assert "areas 'Option_AD'" in hits[0]
    assert "pycnmix-2026-v1.yaml" in hits[0]
    # leg start and end times are known keys
    assert not any("unknown key 'start_date'" in m for m in caplog.messages)


def test_repeated_activity_in_a_leg_warns(caplog):
    """tc3 Leg_Survey_Duplicate2 lists STN_002 twice in CTD_Cluster3; it is still scheduled twice."""
    with caplog.at_level(logging.WARNING, logger="cruiseplan.config.loader"):
        cruise = CruiseInstance(FIXTURES / "tc3_clusters.yaml")
    hits = [
        m
        for m in caplog.messages
        if "'Leg_Survey_Duplicate2'" in m and "'STN_002' 2 times" in m
    ]
    assert len(hits) == 1
    assert "cluster 'CTD_Cluster3'" in hits[0]
    tl = cruiseplan.timeline.generate_timeline(cruise)
    labels = [r.label for r in tl if r.leg_name == "Leg_Survey_Duplicate2"]
    assert labels.count("STN_002") == 2


def _table_pairs(text: str) -> set[tuple[str, str]]:
    """(old, new) pairs from the two-column list tables of an RST page."""
    pairs = re.findall(r"\* - ``([^`]+)``\n\s+- ``([^`]+)``", text)
    return set(pairs)


@pytest.mark.parametrize(
    "table",
    [_deprecated.RENAMED_KEYS, _deprecated.RECORD_KEYS, _deprecated.RENAMED],
    ids=["yaml keys", "record keys", "api names"],
)
def test_migration_page_lists_every_entry(table):
    """The migration page has a row old -> new for each entry of the table."""
    pairs = _table_pairs(PAGE.read_text(encoding="utf-8"))
    for old, new in table.items():
        assert (old, new) in pairs, f"{old} -> {new} missing from {PAGE.name}"


def test_migration_page_lists_removed_keys():
    """Each removed key is on the page with its advice."""
    page = PAGE.read_text(encoding="utf-8")
    for old in _deprecated.REMOVED_KEYS:
        assert f"* - ``{old}``" in page
