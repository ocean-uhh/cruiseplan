"""
Build timeline records from the dictionaries older unit tests were written with.

Those tests describe one or two activities as dictionaries with the
pre-0.6.0 keys. ``as_records`` turns them into ``ActivityRecord`` objects so
the writers, which take records, can be tested on the same values. Keys a
dictionary leaves out get neutral values (zero distance and speed, an end time
equal to start plus duration, a start at the end of the previous row).
"""

from datetime import datetime, timedelta

from cruiseplan.timeline.record import ActivityRecord, kind_of

_RENAMED = {
    "operation_depth": "operation_depth_m",
    "water_depth": "water_depth_m",
    "delay_start": "delay_start_minutes",
    "depth": "water_depth_m",
    "operation_dist_nm": "dist_nm",
}
_CLASS_BY_ACTIVITY = {
    "Transit": "NavigationalTransit",
    "Line": "LineOperation",
    "Area": "AreaOperation",
    "Buffer": "Buffer",
}


def _time(value: datetime | str | None) -> datetime | None:
    """Parse an ISO string; pass datetimes and None through."""
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def as_record(row: dict) -> ActivityRecord:
    """Return the record for one pre-0.6.0 activity dictionary."""
    data = {_RENAMED.get(k, k): v for k, v in row.items()}
    activity = data.get("activity", "Station")
    operation_class = data.get(
        "operation_class", _CLASS_BY_ACTIVITY.get(activity, "PointOperation")
    )
    if activity == "Transit" and data.get("action") and "operation_class" not in data:
        # Before 0.6.0 a survey line was a transit with an action
        operation_class = "LineOperation"
    op_type = data.get("op_type") or data.get("operation_type") or ""
    if not op_type and activity == "Mooring":
        op_type = "mooring"
    lat = data.get("entry_lat", data.get("lat", 0.0))
    lon = data.get("entry_lon", data.get("lon", 0.0))
    start = data.get("start_time", data.get("time", datetime(2024, 1, 1)))
    if isinstance(start, str):
        start = datetime.fromisoformat(start)
    minutes = float(data.get("duration_minutes", 0.0))
    fields = set(ActivityRecord.__dataclass_fields__)
    extra = {k: v for k, v in data.items() if k in fields}
    extra.update(
        kind=kind_of(operation_class, op_type),
        activity=activity,
        label=data.get("label", "Unknown"),
        leg_name=data.get("leg_name", ""),
        op_type=op_type,
        operation_class=operation_class,
        entry_lat=lat,
        entry_lon=lon,
        exit_lat=data.get("exit_lat", lat),
        exit_lon=data.get("exit_lon", lon),
        start_time=start,
        end_time=_time(data.get("end_time")) or start + timedelta(minutes=minutes),
        duration_minutes=minutes,
        planned_duration_minutes=minutes,
        dist_nm=float(data.get("dist_nm", 0.0)),
        vessel_speed_kt=float(data.get("vessel_speed_kt", 0.0)),
        duration_is_fill=bool(data.get("duration_is_fill", False)),
    )
    return ActivityRecord(**extra)


def as_records(rows: list[dict]) -> list[ActivityRecord]:
    """Return records for activity dictionaries; a row without a start follows the previous one."""
    records: list[ActivityRecord] = []
    for row in rows:
        if records and "start_time" not in row and "time" not in row:
            row = {**row, "start_time": records[-1].end_time}
        records.append(as_record(row))
    return records
