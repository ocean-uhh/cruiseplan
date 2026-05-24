"""
Forecast generation functions for station plan activities.

This module provides functions to list activities and generate forecasts
from cruise schedule data.
"""

import logging
from datetime import datetime
from typing import List, Tuple

import numpy as np
import pandas as pd
import xarray as xr

logger = logging.getLogger(__name__)


def list_activities(
    schedule: xr.Dataset,
) -> List[Tuple[int, str, str, str, float, str, float, float, float]]:
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

    # Convert time to pandas datetime for easier formatting
    time_data = schedule.time.values

    # Handle different time formats that might exist in NetCDF
    if hasattr(time_data[0], "total_seconds"):
        # If it's already timedelta objects
        time_offsets = [
            pd.Timedelta(seconds=float(t.total_seconds())) for t in time_data
        ]
    elif np.issubdtype(time_data.dtype, np.number):
        # If it's numeric (hours from start)
        time_offsets = [pd.Timedelta(hours=float(t)) for t in time_data]
    else:
        # If it's datetime, convert to offset from first time
        times = pd.to_datetime(time_data)
        start_time = times[0]
        time_offsets = [t - start_time for t in times]

    for i, (time_offset, category, duration, name) in enumerate(
        zip(
            time_offsets,
            (
                schedule.type.values
                if "type" in schedule.variables
                else schedule.category.values
            ),
            schedule.duration.values,
            schedule.name.values,
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

        # Get water depth and operation depth (if available)
        water_depth = None  # Use None instead of 0 to distinguish between 0 and missing
        operation_depth = None

        # Check for water depth (seafloor depth)
        if "water_depth" in schedule.variables:
            depth_val = float(schedule.water_depth[i].values)
            if not np.isnan(depth_val) and depth_val != -9999.0:
                water_depth = depth_val

        # Check for operation depth (target depth for operations like CTD)
        if "operation_depth" in schedule.variables:
            op_depth_val = float(schedule.operation_depth[i].values)
            if not np.isnan(op_depth_val) and op_depth_val != -9999.0:
                operation_depth = op_depth_val

        # Get distance for current activity (if available)
        distance = None  # Use None instead of 0 to distinguish between 0 and missing
        if "dist_nm" in schedule.variables:
            dist_val = float(schedule.dist_nm[i].values)
            if not np.isnan(dist_val) and dist_val != -9999.0:
                distance = dist_val

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
    activities: List[Tuple[int, str, str, str, float, str, float, float, float]],
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


def generate_forecast(
    schedule: xr.Dataset,
    start_index: int,
    start_time: str,
    duration_hours: float = 24.0,
) -> List[Tuple[int, datetime, str, str, str, float, float, float, str]]:
    """
    Generate time-shifted forecast starting from specified activity.

    Parameters
    ----------
    schedule : xr.Dataset
        Schedule dataset from read_schedule()
    start_index : int
        Index of first activity in forecast (0-based)
    start_time : str
        New absolute start time for the selected activity (ISO format: "2026-08-30T14:00:00")
    duration_hours : float, optional
        Forecast duration in hours (default: 24.0)

    Returns
    -------
    List[Tuple[int, datetime, str, str, str, float, float, float, str]]
        List of forecast activities containing:
        (original_index, absolute_time, category, type, action, duration_hours, latitude, longitude, name)

    Raises
    ------
    ValueError
        If start_index is out of range or start_time format is invalid

    Examples
    --------
    >>> forecast = generate_forecast(schedule, 18, "2026-08-30T14:00:00", 36.0)
    >>> for idx, abs_time, cat, typ, act, dur, lat, lon, name in forecast:
    ...     print(f"{abs_time:%Y-%m-%d %H:%M} | {name}")
    """
    # Validate start_index
    num_activities = len(schedule.time)
    if start_index < 0 or start_index >= num_activities:
        raise ValueError(
            f"start_index {start_index} out of range (0-{num_activities - 1})"
        )

    # Parse start_time
    try:
        new_start_time = pd.to_datetime(start_time)
    except Exception as e:
        raise ValueError(f"Invalid start_time format '{start_time}': {e}")

    # Get all activities (we only need the time offsets for forecast calculation)
    activities = list_activities(schedule)

    # Convert time data to pandas timedeltas for easier calculation
    time_data = schedule.time.values
    if hasattr(time_data[0], "total_seconds"):
        time_offsets = [
            pd.Timedelta(seconds=float(t.total_seconds())) for t in time_data
        ]
    elif np.issubdtype(time_data.dtype, np.number):
        time_offsets = [pd.Timedelta(hours=float(t)) for t in time_data]
    else:
        times = pd.to_datetime(time_data)
        # Always use first time entry as reference, regardless of its absolute value
        start_time_orig = times[0]
        time_offsets = [t - start_time_orig for t in times]

    # Get time offset of start activity
    start_activity_offset = time_offsets[start_index]

    # Truncate activities from start_index onwards
    forecast_activities = []

    for i in range(start_index, num_activities):
        activity_offset = time_offsets[i]

        # Calculate new absolute time: new_start_time + (activity_offset - start_activity_offset)
        # This ensures the activity at start_index occurs exactly at new_start_time
        time_diff = activity_offset - start_activity_offset
        absolute_time = new_start_time + time_diff

        # Check if activity falls within forecast window
        forecast_end_time = new_start_time + pd.Timedelta(hours=duration_hours)
        if absolute_time > forecast_end_time:
            break

        # Extract activity data
        category = str(schedule.category[i].values).strip()
        activity_type = (
            str(schedule.type[i].values).strip() if "type" in schedule.variables else ""
        )
        action = (
            str(schedule.action[i].values).strip()
            if "action" in schedule.variables
            else ""
        )
        duration = float(schedule.duration[i].values)
        latitude = float(schedule.latitude[i].values)
        longitude = float(schedule.longitude[i].values)
        name = str(schedule.name[i].values).strip()

        forecast_activities.append(
            (
                i,
                absolute_time.to_pydatetime(),
                category,
                activity_type,
                action,
                duration,
                latitude,
                longitude,
                name,
            )
        )

    logger.info(
        f"Generated forecast with {len(forecast_activities)} activities "
        f"from index {start_index} for {duration_hours}h"
    )

    return forecast_activities
