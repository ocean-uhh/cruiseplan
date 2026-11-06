"""
Forecast generation functions for station plan activities.

This module provides functions to list activities and generate forecasts
from cruise schedule data.
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr

from cruiseplan.forecast.reader import stored_kind, to_current_format
from cruiseplan.timeline.distance import haversine_distance
from cruiseplan.utils.units import km_to_nm

logger = logging.getLogger(__name__)


def _extract_activity_depths(
    schedule: xr.Dataset, i: int
) -> tuple[float | None, float | None, float | None]:
    """Return (water_depth, operation_depth, distance_to_next) for activity i."""
    water_depth = None
    operation_depth = None
    distance = None

    if "water_depth" in schedule.variables:
        depth_val = float(schedule.water_depth[i].values)
        if not np.isnan(depth_val) and depth_val != -9999.0:
            water_depth = depth_val

    if "operation_depth" in schedule.variables:
        op_depth_val = float(schedule.operation_depth[i].values)
        if not np.isnan(op_depth_val) and op_depth_val != -9999.0:
            operation_depth = op_depth_val

    if "distance_to_next" in schedule.variables:
        dist_val = float(schedule.distance_to_next[i].values)
        if not np.isnan(dist_val) and dist_val != -9999.0:
            distance = dist_val
    if distance is None and "distance" in schedule.variables:
        dist_val = float(schedule.distance[i].values)
        if not np.isnan(dist_val) and dist_val != -9999.0:
            distance = dist_val

    return water_depth, operation_depth, distance


def list_activities(
    schedule: xr.Dataset,
) -> list[tuple[int, str, str, str, float, str, float, float, float]]:
    """
    List all activities with indices for user selection.

    Parameters
    ----------
    schedule : xr.Dataset
        Schedule dataset from read_schedule()

    Returns
    -------
    List[Tuple[int, str, str, str, float, str, float, float, float]]
        List of tuples containing:
        (index, time_offset, category, duration_str, duration_hours, name, water_depth, operation_depth, distance_to_next)

    Examples
    --------
    >>> activities = list_activities(schedule)
    >>> for idx, time_offset, category, duration_str, duration_hours, name in activities:
    ...     print(f"{idx:4d} | {time_offset} | {category:15s} | {duration_str:8s} | {name}")
    """
    activities = []
    schedule = to_current_format(schedule)
    time_offsets = _time_offsets(schedule)

    for i, (time_offset, category, duration, name) in enumerate(
        zip(
            time_offsets,
            (
                schedule.type.values
                if "type" in schedule.variables
                else schedule.category.values
            ),
            schedule.duration.values / 60.0,
            schedule.name.values,
            strict=False,
        )
    ):
        # Format time offset as days and decimal hours, rounded to nearest 0.1h
        total_hours = time_offset.total_seconds() / 3600
        days = int(total_hours // 24)
        decimal_hours = round(total_hours % 24, 1)

        if days > 0:
            time_str = f"{days}d {decimal_hours:.1f}h"
        else:
            time_str = f"{decimal_hours:.1f}h"

        # Format duration
        duration_hours = float(duration)
        duration_str = f"{duration_hours:.1f}h"

        water_depth, operation_depth, distance = _extract_activity_depths(schedule, i)

        # Clean up string values (remove numpy string artifacts)
        category_str = str(category).strip()
        name_str = str(name).strip()

        activities.append(
            (
                i,
                time_str,
                category_str,
                duration_str,
                duration_hours,
                name_str,
                water_depth,
                operation_depth,
                distance,
            )
        )

    return activities


def format_activities_table(
    activities: list[tuple[int, str, str, str, float, str, float, float, float]],
) -> str:
    """
    Format activities list as a readable table.

    Parameters
    ----------
    activities : List[Tuple[int, str, str, str, float, str, float, float, float]]
        Activities list from list_activities()

    Returns
    -------
    str
        Formatted table string ready for display

    Examples
    --------
    >>> activities = list_activities(schedule)
    >>> print(format_activities_table(activities))
    """
    if not activities:
        return "No activities found in schedule."

    # Table header
    lines = [
        "Index | Time Offset  | Category        | Duration | Water Depth | Op Depth | Distance | Name",
        "------|--------------|-----------------|----------|-------------|----------|----------|"
        + "-" * 30,
    ]

    # Table rows
    for (
        idx,
        time_offset,
        category,
        duration_str,
        _,
        name,
        water_depth,
        operation_depth,
        distance,
    ) in activities:
        # Format depth columns (show if available, including 0)
        water_depth_str = (
            f"{water_depth:8.0f}m" if water_depth is not None else "        -"
        )
        op_depth_str = (
            f"{operation_depth:6.0f}m" if operation_depth is not None else "      -"
        )
        distance_str = f"{distance:6.1f}nm" if distance is not None else "      -"

        # Truncate name if too long
        name_display = name[:25] + "..." if len(name) > 28 else name
        line = f"{idx:5d} | {time_offset:12s} | {category:15s} | {duration_str:8s} | {water_depth_str:11s} | {op_depth_str:8s} | {distance_str:8s} | {name_display}"
        lines.append(line)

    return "\n".join(lines)


FORECAST_TRANSIT_INDEX = -1
"""Index given to the transit from ``current_position`` in forecast rows."""

MIN_POSITION_TRANSIT_NM = 0.05
"""Below this distance (nm) from the anchored operation no transit is inserted."""


def parse_start_time(start_time: str) -> pd.Timestamp:
    """
    Parse a forecast start time as UTC.

    A time with a zone is converted to UTC; a time without one is taken as
    UTC. The result has no zone attached, like the schedule times.

    Parameters
    ----------
    start_time : str
        ISO time, e.g. ``"2026-08-30T14:00:00"`` or ``"2026-08-30T16:00+02:00"``.

    Returns
    -------
    pandas.Timestamp
        Naive UTC time, to the second.

    Raises
    ------
    ValueError
        If the time cannot be parsed.
    """
    try:
        moment = pd.to_datetime(start_time)
    except (ValueError, TypeError, OverflowError) as e:
        raise ValueError(f"Invalid start_time format '{start_time}': {e}") from e
    if moment.tzinfo is not None:
        moment = moment.tz_convert("UTC").tz_localize(None)
    return moment.floor("s")


def _time_offsets(schedule: xr.Dataset) -> list[pd.Timedelta]:
    """Row start times as offsets from the first row."""
    time_data = schedule.time.values
    if hasattr(time_data[0], "total_seconds"):
        offsets = [pd.Timedelta(seconds=float(t.total_seconds())) for t in time_data]
    else:
        # Numbers here would be undecoded CF times; to_current_format decodes them
        times = pd.to_datetime(time_data)
        offsets = [t - times[0] for t in times]
    # Stored as float seconds: drop the sub-millisecond noise so a time on a
    # rounding boundary is not floored to the minute before
    return [t.round("ms") for t in offsets]


def _category(schedule: xr.Dataset, i: int) -> str:
    """Category of row i, stripped."""
    return str(schedule.category[i].values).strip()


def resolve_anchor_index(
    schedule: xr.Dataset,
    start_index: int,
    current_position: tuple[float, float] | None = None,
    warn: bool = True,
) -> int:
    """
    Return the row a forecast is anchored on.

    Indices are the rows of ``cruiseplan list`` (ports, transits, operations
    and buffers). Without ``current_position`` the anchor is the row itself:
    an operation starts at the start time, and a transit starts at the start
    time from where it begins (the ship is starting that transit now). With
    ``current_position`` the given position wins: a transit row moves the
    anchor to the operation it leads to, and the forecast starts with a
    transit from the position to it.

    Parameters
    ----------
    schedule : xr.Dataset
        Schedule dataset from read_schedule().
    start_index : int
        Row index given by the user (0-based).
    current_position : tuple of float, optional
        Ship position (lat, lon) at the start time.
    warn : bool, optional
        Log a warning when a transit row moves the anchor (default True).

    Returns
    -------
    int
        Index of the anchored row.

    Raises
    ------
    ValueError
        If ``start_index`` is out of range, or (with ``current_position``) a
        transit with no row after it.
    """
    num_activities = len(schedule.time)
    if start_index < 0 or start_index >= num_activities:
        raise ValueError(
            f"start_index {start_index} out of range (0-{num_activities - 1})"
        )
    if current_position is None:
        return start_index
    anchor = start_index
    while anchor < num_activities and _category(schedule, anchor) == "transit":
        anchor += 1
    if anchor == num_activities:
        raise ValueError(
            f"start_index {start_index} is a transit with no operation after it"
        )
    if anchor != start_index and warn:
        logger.warning(
            f"Index {start_index} is a transit "
            f"('{str(schedule.name[start_index].values).strip()}'); with "
            f"--current-position the forecast goes from there to index {anchor} "
            f"('{str(schedule.name[anchor].values).strip()}')"
        )
    return anchor


def anchor_rule(
    schedule: xr.Dataset,
    start_index: int,
    start_time: str,
    current_position: tuple[float, float] | None = None,
) -> str:
    """
    Describe in one line how a forecast is anchored, for output headers.

    Parameters
    ----------
    schedule : xr.Dataset
        Schedule dataset from read_schedule().
    start_index : int
        Row index given by the user (0-based).
    start_time : str
        Start time as given (UTC).
    current_position : tuple of float, optional
        Ship position (lat, lon) at the start time.

    Returns
    -------
    str
        The rule applied, naming the row and the start time.
    """
    schedule = to_current_format(schedule)
    anchor = resolve_anchor_index(schedule, start_index, current_position, warn=False)
    name = str(schedule.name[anchor].values).strip()
    when = parse_start_time(start_time).strftime("%Y-%m-%d %H:%M")
    if current_position is not None:
        lat, lon = current_position
        return (
            f"Ship at {lat:.4f}, {lon:.4f} at {when} UTC; transit from there to "
            f"row {anchor} ({name}), then the plan"
        )
    if _category(schedule, anchor) == "transit":
        return (
            f"Row {anchor} ({name}) starts at {when} UTC from where the transit "
            "begins; the ship is starting this transit now"
        )
    return f"Row {anchor} ({name}) starts at {when} UTC; the ship is there"


def _leg_speed(schedule: xr.Dataset, anchor: int) -> float:
    """Transit speed (kt) of the anchored row's leg; 10 kt if none is stored."""
    if "vessel_speed" not in schedule.variables:
        return 10.0
    legs = (
        [str(v).strip() for v in schedule.leg_assignment.values]
        if "leg_assignment" in schedule.variables
        else None
    )
    n = len(schedule.time)
    # nearest transit row of the same leg: before the anchor first, then after
    for i in [*range(anchor - 1, -1, -1), *range(anchor + 1, n)]:
        if _category(schedule, i) != "transit":
            continue
        if legs is not None and legs[i] != legs[anchor]:
            continue
        speed = float(schedule.vessel_speed[i].values)
        if np.isfinite(speed) and speed > 0:
            return speed
    return 10.0


def _gc_nm(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in nm between (lat, lon) points."""
    return km_to_nm(haversine_distance(a, b))


def generate_forecast(
    schedule: xr.Dataset,
    start_index: int,
    start_time: str,
    duration_hours: float = 24.0,
    current_position: tuple[float, float] | None = None,
) -> list[tuple[int, datetime, str, str, str, float, float, float, str]]:
    """
    Generate a re-anchored forecast starting from a row of the schedule.

    The anchored row starts at ``start_time`` (UTC; see
    ``resolve_anchor_index``): an operation row means the ship is there, so
    the transit into it is not included; a transit row means the ship is
    starting that transit now. With ``current_position``, ``start_time`` is
    the time at that position: a transit from it to the anchored operation,
    at the leg's speed, is inserted first and the operation starts when it
    ends. Every later row keeps its planned offset from the anchored row. The
    anchored operation's own ``delay_start_minutes`` is replaced by the
    anchor time.

    A row that runs past the start of the next row (the next operation has a
    negative ``delay_start_minutes``: the previous activity ended early) is shortened
    to end where the next row starts.

    Parameters
    ----------
    schedule : xr.Dataset
        Schedule dataset from read_schedule().
    start_index : int
        Row index (0-based, as in ``cruiseplan list``).
    start_time : str
        Absolute start time, UTC (ISO format, e.g. "2026-08-30T14:00:00"): of the
        anchored operation, or of the ship at ``current_position``.
    duration_hours : float, optional
        Forecast window in hours from ``start_time`` (default: 24.0).
    current_position : tuple of float, optional
        Ship position (lat, lon) in decimal degrees at ``start_time``.

    Returns
    -------
    list of tuple
        Forecast rows ``(original_index, absolute_time, category, type,
        action, duration_hours, latitude, longitude, name)``. The transit
        from ``current_position`` has index ``FORECAST_TRANSIT_INDEX``.

    Raises
    ------
    ValueError
        If ``start_index`` is out of range or ``start_time`` is invalid.

    Examples
    --------
    >>> forecast = generate_forecast(schedule, 18, "2026-08-30T14:00:00", 36.0)
    >>> for idx, abs_time, cat, typ, act, dur, lat, lon, name in forecast:
    ...     print(f"{abs_time:%Y-%m-%d %H:%M} | {name}")
    """
    schedule = to_current_format(schedule)
    anchor = resolve_anchor_index(schedule, start_index, current_position)
    num_activities = len(schedule.time)

    new_start_time = parse_start_time(start_time)

    time_offsets = _time_offsets(schedule)
    forecast_end_time = new_start_time + pd.Timedelta(hours=duration_hours)
    forecast_activities = []

    anchor_time = new_start_time
    nm = 0.0
    if current_position is not None:
        target = (
            float(schedule.latitude[anchor].values),
            float(schedule.longitude[anchor].values),
        )
        nm = _gc_nm(tuple(current_position), target)
    if nm >= MIN_POSITION_TRANSIT_NM:
        hours = nm / _leg_speed(schedule, anchor)
        forecast_activities.append(
            (
                FORECAST_TRANSIT_INDEX,
                new_start_time.to_pydatetime(),
                "transit",
                "transit",
                "",
                hours,
                float(current_position[0]),
                float(current_position[1]),
                f"Transit to {str(schedule.name[anchor].values).strip()}",
            )
        )
        anchor_time = new_start_time + pd.Timedelta(hours=hours)

    for i in range(anchor, num_activities):
        absolute_time = (anchor_time + (time_offsets[i] - time_offsets[anchor])).floor(
            "s"
        )
        if absolute_time > forecast_end_time:
            break

        duration = float(schedule.duration[i].values) / 60.0
        if i + 1 < num_activities:
            gap_hours = (time_offsets[i + 1] - time_offsets[i]).total_seconds() / 3600
            if gap_hours < duration:
                duration = max(gap_hours, 0.0)

        forecast_activities.append(
            (
                i,
                absolute_time.to_pydatetime(),
                _category(schedule, i),
                (
                    str(schedule.type[i].values).strip()
                    if "type" in schedule.variables
                    else ""
                ),
                (
                    str(schedule.action[i].values).strip()
                    if "action" in schedule.variables
                    else ""
                ),
                duration,
                float(schedule.latitude[i].values),
                float(schedule.longitude[i].values),
                str(schedule.name[i].values).strip(),
            )
        )

    in_window = [row[0] for row in forecast_activities if row[0] >= 0]
    # Ports count (a window may end the cruise); transits and buffers do not
    if all(stored_kind(schedule, i) in {"transit", "buffer"} for i in in_window):
        reason = ""
        if nm >= MIN_POSITION_TRANSIT_NM:
            reason = (
                f" (the transit from --current-position to row {anchor} is {nm:.1f} nm)"
            )
        raise ValueError(
            f"No operation starts within {duration_hours:g} h of {start_time} "
            f"from row {start_index}{reason}; give a longer --duration"
        )
    logger.info(
        f"Generated forecast with {len(forecast_activities)} activities "
        f"from index {anchor} for {duration_hours}h"
    )

    return forecast_activities
