"""
The timeline record: one scheduled activity, and the timeline type.

Every stage after the scheduler works from :class:`ActivityRecord`: the
writers (CSV, HTML, LaTeX, KML, NetCDF, maps) and the forecast, which reads
records back from the NetCDF schedule.
"""

from dataclasses import dataclass, fields, replace
from datetime import datetime
from typing import Literal, get_args

ActivityKind = Literal[
    "station", "mooring", "line", "area", "transit", "port", "buffer"
]
"""What a record is: a point operation (station or mooring), a line, an area,
a navigational transit, a port call or a contingency buffer."""

KINDS: tuple[str, ...] = get_args(ActivityKind)

SCIENCE_KINDS = frozenset({"station", "mooring", "line", "area"})
"""Kinds that count as scientific operations."""


def kind_of(operation_class: str, op_type: str | None) -> str:
    """
    Return the record kind for an operation class and operation type.

    Parameters
    ----------
    operation_class : str
        Implementation class name: ``PointOperation``, ``LineOperation``,
        ``AreaOperation``, ``NavigationalTransit`` or ``Buffer``.
    op_type : str or None
        Operation type from the configuration (``CTD``, ``mooring``,
        ``port``, ...).

    Returns
    -------
    str
        One of :data:`KINDS`.

    Raises
    ------
    ValueError
        If the operation class is not known.
    """
    if operation_class == "PointOperation":
        if op_type == "port":
            return "port"
        if op_type == "mooring":
            return "mooring"
        return "station"
    by_class = {
        "LineOperation": "line",
        "AreaOperation": "area",
        "NavigationalTransit": "transit",
        "Buffer": "buffer",
    }
    if operation_class not in by_class:
        raise ValueError(f"Unknown operation class: {operation_class!r}")
    return by_class[operation_class]


@dataclass(frozen=True, kw_only=True, slots=True)
class ActivityRecord:
    """
    One scheduled activity of a cruise timeline.

    Records are immutable: a change (for example trimming an activity that
    ended early) makes a new record with :meth:`replace`.

    Parameters
    ----------
    kind : str
        One of :data:`KINDS`.
    activity : str
        Display type: ``Station``, ``Mooring``, ``Port``, ``Waypoint``,
        ``Line``, ``Area``, ``Transit`` or ``Buffer``.
    label : str
        Name shown in outputs.
    leg_name : str
        Name of the leg the activity belongs to.
    op_type : str
        Operation type (``CTD``, ``mooring``, ``port``, ``transit``, ...).
    operation_class : str
        Implementation class the record was made from.
    entry_lat, entry_lon : float
        Where the activity starts, in decimal degrees.
    exit_lat, exit_lon : float
        Where the activity ends, in decimal degrees.
    start_time, end_time : datetime
        Start and end (UTC, no time zone attached).
    duration_minutes : float
        Actual duration: ``end_time - start_time``.
    planned_duration_minutes : float
        Duration from the planning rules, before any trimming.
    dist_nm : float
        Distance covered by the activity in nautical miles.
    vessel_speed_kt : float
        Vessel speed in knots.
    action : str or None
        Action (``profile``, ``deployment``, ``mob``, ...).
    operation_depth_m : float or None
        Target depth of the operation in meters.
    water_depth_m : float or None
        Water depth at the location in meters.
    delay_start_minutes : float or None
        Delay before the activity starts in minutes (negative: the previous
        activity ended early); None for transits and buffers.
    comment : str or None
        Comment from the configuration.
    duration_is_fill : bool
        True when the duration is the fill value.
    transit_dist_nm : float or None
        Distance to the next waypoint in nautical miles, where known.
    """

    kind: ActivityKind
    activity: str
    label: str
    leg_name: str
    op_type: str
    operation_class: str
    entry_lat: float
    entry_lon: float
    exit_lat: float
    exit_lon: float
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    planned_duration_minutes: float
    dist_nm: float
    vessel_speed_kt: float
    action: str | None = None
    operation_depth_m: float | None = None
    water_depth_m: float | None = None
    delay_start_minutes: float | None = None
    comment: str | None = None
    duration_is_fill: bool = False
    transit_dist_nm: float | None = None

    def __post_init__(self) -> None:
        """Check the kind."""
        if self.kind not in KINDS:
            raise ValueError(f"Unknown record kind {self.kind!r}; use one of {KINDS}")

    @property
    def is_science(self) -> bool:
        """True for scientific operations (stations, moorings, lines, areas)."""
        return self.kind in SCIENCE_KINDS

    @property
    def depth_m(self) -> float | None:
        """Operation depth if given, otherwise water depth, otherwise None."""
        if self.operation_depth_m is not None:
            return self.operation_depth_m
        return self.water_depth_m

    def replace(self, **changes: object) -> "ActivityRecord":
        """
        Return a copy with the given fields changed.

        Parameters
        ----------
        **changes : object
            Field names and their new values.

        Returns
        -------
        ActivityRecord
            The new record.
        """
        return replace(self, **changes)

    def to_dict(self) -> dict[str, object]:
        """
        Return the record as a plain dictionary of its fields.

        Returns
        -------
        dict
            Field name to value.
        """
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def __getitem__(self, key: str) -> object:
        """Return the attribute for a dictionary key, with a deprecation warning."""
        from cruiseplan import _deprecated

        _deprecated.warn_record_key(key)
        return getattr(self, _deprecated.RECORD_KEYS.get(key, key))


Timeline = list[ActivityRecord]
"""A cruise timeline: records in schedule order."""
