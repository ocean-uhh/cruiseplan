"""
Prepare a YAML configuration dictionary for validation.

Applied by every loader before the pydantic models see the data:

- renamed keys (``cruiseplan._deprecated.RENAMED_KEYS``) are accepted under
  their old name with a warning naming the new key and the release that
  removes the old one;
- removed keys (``cruiseplan._deprecated.REMOVED_KEYS``) are dropped with a
  warning that says what to use instead;
- keys no model knows are reported, one warning per key per file (they are
  rejected in the release after 0.6.0);
- an activity listed more than once in a leg is reported (it is scheduled
  each time; repeat stations are a valid use).
"""

import logging
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

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

logger = logging.getLogger(__name__)

# Keys accepted at every level although no model declares them
_ALWAYS_ACCEPTED = frozenset({"position"})  # legacy "lat, lon" string (S5/8)


def _known(model: type[BaseModel]) -> frozenset[str]:
    """Return the field names a model accepts."""
    return frozenset(model.model_fields) | _ALWAYS_ACCEPTED


_KNOWN = {
    "cruise": _known(CruiseConfig),
    "point": _known(PointDefinition),
    "line": _known(LineDefinition),
    "area": _known(AreaDefinition),
    "leg": _known(LegDefinition),
    "cluster": _known(ClusterDefinition),
    "geopoint": _known(GeoPoint),
}


class _Report:
    """Collects key problems in one file and logs one warning per key."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.renamed: dict[str, list[str]] = defaultdict(list)
        self.removed: dict[str, list[str]] = defaultdict(list)
        self.unknown: dict[str, list[str]] = defaultdict(list)

    def log(self) -> None:
        """Log the collected warnings."""
        for old, where in self.renamed.items():
            logger.warning(
                f"{self.source}: {_deprecated.key_message(old)} ({_where(where)})"
            )
        for old, where in self.removed.items():
            logger.warning(
                f"{self.source}: {_deprecated.removed_key_message(old)} "
                f"({_where(where)})"
            )
        for key, where in self.unknown.items():
            logger.warning(
                f"{self.source}: unknown key '{key}' is not used ({_where(where)}); "
                "unknown keys are rejected in the release after 0.6.0"
            )


def _where(places: list[str]) -> str:
    """Name the first places a key was found, and how many there were."""
    shown = ", ".join(places[:3])
    return shown if len(places) <= 3 else f"{shown} and {len(places) - 3} more"


def _clean(
    data: Mapping[str, Any], level: str, where: str, report: _Report
) -> dict[str, Any]:
    """Return a copy of one mapping with keys renamed, removed keys dropped."""
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key in _deprecated.REMOVED_KEYS:
            report.removed[key].append(where)
            continue
        new = _deprecated.RENAMED_KEYS.get(key)
        if new is not None and new in _KNOWN[level]:
            report.renamed[key].append(where)
            if new in data:
                if data[new] != value:
                    raise ValueError(
                        f"{report.source}: {where} has both '{key}' and '{new}' "
                        f"with different values; keep only '{new}'"
                    )
                continue
            key = new
        elif key not in _KNOWN[level]:
            report.unknown[key].append(where)
        out[key] = value
    return out


def _name(item: Mapping[str, Any], index: int) -> str:
    """Display name of a list item for warnings."""
    return str(item.get("name", f"#{index}"))


def _inline_level(item: Mapping[str, Any]) -> str:
    """Model an inline activity definition is validated with."""
    if "route" in item:
        return "line"
    if "corners" in item:
        return "area"
    return "point"


def _clean_list(items: object, level: str, where: str, report: _Report) -> object:
    """Clean every mapping in a list; other values pass through."""
    if not isinstance(items, list):
        return items
    out = []
    for i, item in enumerate(items):
        if not isinstance(item, Mapping):
            out.append(item)
            continue
        item_level = _inline_level(item) if level == "inline" else level
        cleaned = _clean(item, item_level, f"{where} '{_name(item, i)}'", report)
        for vertices in ("route", "corners"):
            if vertices in cleaned:
                cleaned[vertices] = _clean_list(
                    cleaned[vertices], "geopoint", f"{where} {vertices}", report
                )
        out.append(cleaned)
    return out


def _clean_port(value: object, where: str, report: _Report) -> object:
    """Clean an inline port definition; port names pass through."""
    if isinstance(value, Mapping):
        return _clean(value, "point", where, report)
    return value


def _leg_activities(leg: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Return (activity name, where listed) for a leg in schedule order."""
    listed = []
    if leg.get("clusters"):
        for cluster in leg["clusters"]:
            for activity in cluster.get("activities") or []:
                name = (
                    activity.get("name") if isinstance(activity, Mapping) else activity
                )
                listed.append((str(name), f"cluster '{cluster.get('name', '?')}'"))
    else:
        for activity in leg.get("activities") or []:
            name = activity.get("name") if isinstance(activity, Mapping) else activity
            listed.append((str(name), "leg activities"))
    return listed


def _warn_repeated_activities(legs: object, source: str) -> None:
    """Warn once per activity that a leg schedules more than once."""
    if not isinstance(legs, list):
        return
    for leg in legs:
        if not isinstance(leg, Mapping):
            continue
        places: dict[str, list[str]] = defaultdict(list)
        for name, where in _leg_activities(leg):
            places[name].append(where)
        for name, where in places.items():
            if len(where) > 1:
                logger.warning(
                    f"{source}: leg '{leg.get('name', '?')}' schedules activity "
                    f"'{name}' {len(where)} times (in {', '.join(where)}); each "
                    "listing is scheduled. Remove the extra listings unless the "
                    "repeat is intended."
                )


def prepare_config(data: Mapping[str, Any], source: str = "configuration") -> dict:
    """
    Return a configuration dictionary ready for ``CruiseConfig``.

    Renamed keys are moved to their new names, removed keys are dropped, and
    unknown keys and repeated activities are reported; each problem is logged
    once per key (or activity) for the file.

    Parameters
    ----------
    data : Mapping
        Configuration as read from YAML.
    source : str, optional
        File name used in the warnings.

    Returns
    -------
    dict
        A new dictionary; *data* is not changed.

    Raises
    ------
    ValueError
        If a mapping has an old key and its new key with different values.
    """
    report = _Report(source)
    out = _clean(data, "cruise", "cruise", report)
    for catalog, level in (
        ("points", "point"),
        ("ports", "point"),
        ("lines", "line"),
        ("areas", "area"),
    ):
        if catalog in out:
            out[catalog] = _clean_list(out[catalog], level, catalog, report)
    for port in ("departure_port", "arrival_port"):
        if port in out:
            out[port] = _clean_port(out[port], port, report)
    if isinstance(out.get("legs"), list):
        legs = []
        for i, leg in enumerate(out["legs"]):
            if not isinstance(leg, Mapping):
                legs.append(leg)
                continue
            where = f"leg '{_name(leg, i)}'"
            leg = _clean(leg, "leg", where, report)
            for port in ("departure_port", "arrival_port"):
                if port in leg:
                    leg[port] = _clean_port(leg[port], f"{where} {port}", report)
            if "activities" in leg:
                leg["activities"] = _clean_list(
                    leg["activities"], "inline", f"{where} activity", report
                )
            if isinstance(leg.get("clusters"), list):
                clusters = _clean_list(
                    leg["clusters"], "cluster", f"{where} cluster", report
                )
                for cluster in clusters:
                    if isinstance(cluster, dict) and "activities" in cluster:
                        cluster["activities"] = _clean_list(
                            cluster["activities"],
                            "inline",
                            f"{where} cluster activity",
                            report,
                        )
                leg["clusters"] = clusters
            legs.append(leg)
        out["legs"] = legs
    report.log()
    _warn_repeated_activities(out.get("legs"), source)
    return out
