"""
Provenance fields written into schedule outputs.

The schedule writers (NetCDF, HTML, LaTeX) record which configuration file,
bathymetry source and planning parameters a schedule was computed from, so a
schedule can be traced back without the command line that produced it.
"""

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from cruiseplan.config.cruise_config import CruiseConfig


def _utc_now() -> str:
    """Return the current UTC time as ISO 8601 with a trailing Z, to the second."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_version() -> str:
    """Return the installed cruiseplan version, or 'unknown'."""
    try:
        from cruiseplan._version import __version__
    except ImportError:
        return "unknown"
    return __version__


def record_source_config(config: CruiseConfig, config_path: str | Path) -> None:
    """
    Attach the configuration file name, its SHA-256 and the creation time to ``config``.

    The schedule writers read these through ``planning_provenance``.

    Parameters
    ----------
    config : CruiseConfig
        Configuration the schedule is computed from.
    config_path : str or Path
        YAML file ``config`` was loaded from.
    """
    path = Path(config_path)
    config.source_config_provenance = {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "date_created": _utc_now(),
    }


def _parameter(config: CruiseConfig, name: str) -> float | str:
    """Return a numeric planning parameter of ``config``, or 'not set'."""
    value = getattr(config, name, None)
    # bool is a subclass of int; a boolean is not a numeric planning parameter.
    if isinstance(value, bool) or not isinstance(value, int | float):
        return "not set"
    return float(value)


def _bathymetry_source(config: CruiseConfig) -> tuple[str, int | None]:
    """Return the bathymetry source description and fill count recorded on ``config``."""
    record = getattr(config, "bathymetry_provenance", None)
    if record:
        source = str(record.get("source", "unknown"))
        if not record.get("file_found", True):
            source += f" ({record.get('file', 'file')} not found)"
        return source, int(record.get("depths_filled", 0))
    points = getattr(config, "points", None)
    sources = sorted(
        {
            str(point.bathymetry_source)
            for point in (points if isinstance(points, list) else [])
            if getattr(point, "bathymetry_source", None)
        }
    )
    if sources:
        return ", ".join(sources), None
    return "none (water depths from configuration)", None


def planning_provenance(config: CruiseConfig) -> dict[str, str | float | int]:
    """
    Return the provenance fields for a schedule computed from ``config``.

    Parameters
    ----------
    config : CruiseConfig
        Configuration the schedule was computed from. If
        ``record_source_config`` was not called, the configuration file is
        reported as ``"not recorded"``.

    Returns
    -------
    dict
        ``cruiseplan_version``, ``source_config``, ``source_config_sha256``,
        ``bathymetry_source``, ``bathymetry_depths_filled`` (when recorded),
        the planning parameters ``default_vessel_speed_kt``,
        ``ctd_descent_rate_m_s``, ``ctd_ascent_rate_m_s``,
        ``turnaround_time_min``, ``start_date``, and ``date_created`` (UTC,
        ISO 8601 with ``Z``).
    """
    source = getattr(config, "source_config_provenance", None) or {}
    bathymetry_source, depths_filled = _bathymetry_source(config)
    fields: dict[str, str | float | int] = {
        "cruiseplan_version": _package_version(),
        "source_config": source.get("file", "not recorded"),
        "source_config_sha256": source.get("sha256", "not recorded"),
        "bathymetry_source": bathymetry_source,
    }
    if depths_filled is not None:
        fields["bathymetry_depths_filled"] = depths_filled
    fields.update(
        {
            "default_vessel_speed_kt": _parameter(config, "default_vessel_speed_kt"),
            "ctd_descent_rate_m_s": _parameter(config, "ctd_descent_rate_m_s"),
            "ctd_ascent_rate_m_s": _parameter(config, "ctd_ascent_rate_m_s"),
            "turnaround_time_min": _parameter(config, "turnaround_time_minutes"),
            "start_date": str(getattr(config, "start_date", None) or "not set"),
            "date_created": source.get("date_created") or _utc_now(),
        }
    )
    return fields


def provenance_lines(config: CruiseConfig) -> list[str]:
    """
    Return the provenance fields as ``"name: value"`` lines for text headers.

    Parameters
    ----------
    config : CruiseConfig
        Configuration the schedule was computed from.

    Returns
    -------
    list of str
        One line per field of ``planning_provenance``.
    """
    return [f"{key}: {value}" for key, value in planning_provenance(config).items()]
