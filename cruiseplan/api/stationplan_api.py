"""
Station plan API for generating cruise activity lists and forecasts.

This module provides the main API functions for reading cruise schedules
and generating station plan outputs for real-time cruise operations.
"""

import dataclasses
import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import numpy as np
import xarray as xr

from cruiseplan.forecast.formatter import format_letsgo_output
from cruiseplan.forecast.generator import (
    anchor_rule,
    format_activities_table,
    generate_forecast,
    list_activities,
    parse_start_time,
    ship_time_offset,
    time_zone_label,
)
from cruiseplan.forecast.reader import read_schedule
from cruiseplan.output.kml_generator import KMLGenerator
from cruiseplan.timeline.record import KIND_OPERATION_CLASS, ActivityRecord, kind_of

logger = logging.getLogger(__name__)


@dataclass
class StationplanResult:
    """
    Result object for stationplan operations.

    Attributes
    ----------
    success : bool
        Whether the operation completed successfully
    message : str
        Status message or error description
    output : str, optional
        Generated output text (for list mode)
    """

    success: bool
    message: str
    output: str = ""


def stationplan_list(schedule_file: str | Path) -> StationplanResult:
    """
    List all activities in a cruise schedule with indices.

    This function reads a NetCDF schedule file and returns a formatted table
    of all activities with their indices, time offsets, categories, durations,
    and names. This is used for the --list mode of the stationplan command.

    Parameters
    ----------
    schedule_file : str or Path
        Path to NetCDF schedule file (e.g., 'MSM142_leg_2_schedule.nc')

    Returns
    -------
    StationplanResult
        Result object containing:
        - success: True if successful, False if error
        - message: Status message
        - output: Formatted activities table (if successful)

    Examples
    --------
    >>> result = stationplan_list("data/cruise_schedule.nc")
    >>> if result.success:
    ...     print(result.output)
    ... else:
    ...     print(f"Error: {result.message}")
    """
    try:
        logger.info(f"Loading schedule for activity listing: {schedule_file}")

        # Read the schedule file
        schedule = read_schedule(schedule_file)

        # Get activity list
        activities = list_activities(schedule)

        if not activities:
            return StationplanResult(
                success=False, message="No activities found in schedule file", output=""
            )

        # Format as table
        output_table = format_activities_table(activities)

        logger.info(f"Successfully listed {len(activities)} activities")

        return StationplanResult(
            success=True,
            message=f"Listed {len(activities)} activities from {schedule_file}",
            output=output_table,
        )

    except FileNotFoundError as e:
        error_msg = f"Schedule file not found: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")

    except ValueError as e:
        error_msg = f"Invalid schedule file: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Unexpected error processing schedule: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_forecast(
    schedule_file: str | Path,
    start_index: int,
    start_time: str,
    duration_hours: float = 24.0,
    transit_speed: float = 10.0,
    current_position: tuple[float, float] | None = None,
) -> StationplanResult:
    """
    Generate station plan forecast starting from specified activity.

    This function reads a NetCDF schedule file, generates a time-shifted forecast
    starting from the specified activity index with a new start time, and formats
    the output as letsgo.m compatible text.

    Parameters
    ----------
    schedule_file : str or Path
        Path to NetCDF schedule file (e.g., 'MSM142_leg_2_schedule.nc')
    start_index : int
        Row index (0-based, as in ``cruiseplan list``); an operation row
        starts at ``start_time``, a transit row starts at ``start_time`` from
        where it begins (with ``current_position``, the operation it leads to
        is used)
    start_time : str
        Start time of the anchored operation, or of the ship at
        ``current_position`` (ISO format). A time without a zone is UTC; with
        the ship's zone (``"2026-08-30T14:00+03:00"``) it is ship time
    duration_hours : float, optional
        Forecast duration in hours (default: 24.0)
    transit_speed : float, optional
        Ship transit speed in knots for header metadata (default: 10.0)
    current_position : tuple of float, optional
        Ship position (lat, lon) in decimal degrees at ``start_time``. A
        transit from it to the anchored operation is inserted at the leg's
        speed, and the operation starts when it ends.

    Returns
    -------
    StationplanResult
        Result object containing:
        - success: True if successful, False if error
        - message: Status message
        - output: Formatted letsgo.m forecast text (if successful)

    Examples
    --------
    >>> result = stationplan_forecast("data/cruise_schedule.nc", 18, "2026-08-30T14:00:00", 36.0)
    >>> if result.success:
    ...     print(result.output)
    ... else:
    ...     print(f"Error: {result.message}")
    """
    try:
        logger.info(
            f"Generating forecast from {schedule_file} starting at index {start_index}"
        )

        # Read the schedule file
        schedule = read_schedule(schedule_file)

        # Generate forecast
        forecast_activities = generate_forecast(
            schedule, start_index, start_time, duration_hours, current_position
        )

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No activities found in forecast window ({duration_hours}h from {start_time})",
                output="",
            )

        # Format as letsgo.m output
        output_text = format_letsgo_output(
            forecast_activities,
            start_time,
            transit_speed,
            anchor_note=anchor_rule(
                schedule, start_index, start_time, current_position
            ),
        )

        logger.info(
            f"Successfully generated forecast with {len(forecast_activities)} activities"
        )

        return StationplanResult(
            success=True,
            message=f"Generated {duration_hours}h forecast with {len(forecast_activities)} activities",
            output=output_text,
        )

    except FileNotFoundError as e:
        error_msg = f"Schedule file not found: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")

    except ValueError as e:
        error_msg = f"Invalid forecast parameters: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Unexpected error generating forecast: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_tex(
    schedule_file: str | Path,
    output_path: str | Path | None = None,
    logo_path: str | Path | None = None,
    workplan_number: str | None = None,
    cruise_title: str | None = None,
) -> StationplanResult:
    """
    Generate TeX station table in letsgo.m format from NetCDF schedule file.

    This function reads a NetCDF schedule file and generates a TeX table
    in the letsgo.m format using rich NetCDF data with proper coordinates,
    depths, and distance calculations.

    Parameters
    ----------
    schedule_file : str or Path
        Path to NetCDF schedule file (e.g., 'MSM142_leg_2_schedule.nc')
    output_path : str or Path, optional
        Output path for .tex file. If None, uses schedule_file name with .tex extension
    logo_path : str or Path, optional
        Path to a logo image (PNG, JPG or PDF). If None, ``config/images/`` is
        searched for a default logo.
    workplan_number : str, optional
        Workplan number printed in the TeX header (e.g. ``"28"``).
    cruise_title : str, optional
        Cruise title printed in the TeX header (e.g. ``"MSM142"``).

    Returns
    -------
    StationplanResult
        Result object containing:
        - success: True if successful, False if error
        - message: Status message
        - output: Path to generated .tex file (if successful)

    Examples
    --------
    >>> result = stationplan_tex("data/cruise_schedule.nc", "station_plan.tex")
    >>> if result.success:
    ...     print(f"TeX table generated: {result.output}")
    ... else:
    ...     print(f"Error: {result.message}")
    """
    try:
        from cruiseplan.output.latex_generator import generate_letsgo_table_from_netcdf

        schedule_path = Path(schedule_file)
        logger.info(f"Generating TeX table from schedule: {schedule_path}")

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_suffix(".tex")
        else:
            output_file = Path(output_path)

        # Generate TeX table using our letsgo-style generator
        generated_file = generate_letsgo_table_from_netcdf(
            schedule_path, output_file, logo_path, workplan_number, cruise_title
        )

        logger.info(f"Successfully generated TeX table: {generated_file}")

        return StationplanResult(
            success=True,
            message=f"Generated TeX station table: {generated_file}",
            output=str(generated_file),
        )

    except FileNotFoundError as e:
        error_msg = f"Schedule file not found: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Error generating TeX table: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")


def _lookup_schedule_depth_data(
    schedule: xr.Dataset, index: int
) -> tuple[float | None, float | None, str]:
    """Look up water_depth, operation_depth, and comment from a NetCDF schedule.

    Returns (water_depth, operation_depth, comment) with None/empty defaults.
    """
    water_depth = None
    operation_depth = None
    comment = ""

    if "water_depth" in schedule.variables:
        try:
            depth_val = schedule.water_depth[index].values
            if depth_val is not None and not np.isnan(float(depth_val)):
                water_depth = float(depth_val)
        except (TypeError, ValueError):
            pass

    if "operation_depth" in schedule.variables:
        try:
            op_depth_val = schedule.operation_depth[index].values
            if op_depth_val is not None and not np.isnan(float(op_depth_val)):
                operation_depth = float(op_depth_val)
        except (TypeError, ValueError):
            pass

    if "comment" in schedule.variables:
        comment_val = str(schedule.comment[index].values)
        if comment_val and comment_val not in {"nan", "_"}:
            comment = comment_val

    return water_depth, operation_depth, comment


def _lookup_tex_exit_coords(
    schedule: xr.Dataset, index: int, latitude: float, longitude: float
) -> tuple[float, float]:
    """Return exit (lat, lon) from schedule variables, falling back to entry coords."""
    try:
        if (
            "exit_latitude" in schedule.variables
            and "exit_longitude" in schedule.variables
        ):
            exit_lat_val = float(schedule.exit_latitude[index].values)
            exit_lon_val = float(schedule.exit_longitude[index].values)
            if not (np.isnan(exit_lat_val) or np.isnan(exit_lon_val)):
                return exit_lat_val, exit_lon_val
    except (AttributeError, TypeError, ValueError, IndexError):
        pass
    return latitude, longitude


def _build_tex_forecast_record(
    schedule: xr.Dataset, index: int, activity_tuple: tuple
) -> "ActivityRecord | None":
    """Convert one forecast row to a record for TeX output; None for transits."""
    (
        _idx,
        time,
        category,
        activity_type,
        action,
        duration,
        latitude,
        longitude,
        name,
    ) = activity_tuple

    if category == "transit":
        return None

    water_depth, operation_depth, comment = _lookup_schedule_depth_data(schedule, index)
    exit_lat, exit_lon = _lookup_tex_exit_coords(schedule, index, latitude, longitude)
    end_time = time + timedelta(hours=duration)

    operation_distance = (
        float(schedule.distance[index].values)
        if "distance" in schedule.variables
        else 0.0
    )
    next_transit_distance = (
        float(schedule.distance_to_next[index].values)
        if "distance_to_next" in schedule.variables
        else 0.0
    )

    from cruiseplan.forecast.reader import _float, _text, stored_kind

    kind = "transit" if index < 0 else stored_kind(schedule, index)
    return ActivityRecord(
        kind=kind,
        activity=_text(schedule, "activity", index, category),
        label=name,
        entry_lat=float(latitude),
        entry_lon=float(longitude),
        exit_lat=float(exit_lat),
        exit_lon=float(exit_lon),
        start_time=time,
        end_time=end_time,
        duration_minutes=float(duration) * 60.0,
        planned_duration_minutes=float(duration) * 60.0,
        water_depth_m=water_depth,
        operation_depth_m=operation_depth,
        dist_nm=operation_distance,
        transit_dist_nm=next_transit_distance,
        vessel_speed_kt=_float(schedule, "vessel_speed", index, np.nan),
        leg_name="forecast",
        op_type=activity_type,
        operation_class=KIND_OPERATION_CLASS[kind],
        action=action if action else None,
        comment=comment,
    )


def stationplan_forecast_tex(
    schedule_file: str | Path,
    start_index: int,
    start_time: str,
    duration_hours: float = 24.0,
    output_path: str | Path | None = None,
    logo_path: str | Path | None = None,
    workplan_number: str | None = None,
    cruise_title: str | None = None,
    current_position: tuple[float, float] | None = None,
) -> StationplanResult:
    """
    Generate TeX station forecast starting from specified activity.

    Combines forecast generation with TeX formatting - generates a time-shifted
    forecast and outputs it as a complete LaTeX document. When ``start_time``
    carries the ship's zone, the table is printed in that ship time and the
    time column is labelled with it; otherwise it is in UTC.

    Parameters
    ----------
    schedule_file : str or Path
        Path to NetCDF schedule file
    start_index : int
        Row index (0-based, as in ``cruiseplan list``); an operation row
        starts at ``start_time``, a transit row starts at ``start_time`` from
        where it begins (with ``current_position``, the operation it leads to
        is used)
    start_time : str
        Start time of the anchored operation, or of the ship at
        ``current_position`` (ISO format). A time without a zone is UTC; with
        the ship's zone (``"2026-08-30T14:00+03:00"``) it is ship time
    duration_hours : float
        Forecast duration in hours (default: 24.0)
    output_path : str or Path, optional
        Output path for .tex file
    logo_path : str or Path, optional
        Path to logo image file (PNG, JPG, or PDF). If None, checks for default logos in config/images/ folder
    workplan_number : str, optional
        Workplan number printed in the TeX header (e.g. ``"28"``).
    cruise_title : str, optional
        Cruise title printed in the TeX header (e.g. ``"MSM142"``).
    current_position : tuple of float, optional
        Ship position (lat, lon) in decimal degrees at ``start_time``. A
        transit from it to the anchored operation is inserted at the leg's
        speed, and the operation starts when it ends.

    Returns
    -------
    StationplanResult
        Result object with success status and generated file path
    """
    try:
        from cruiseplan.output.latex_generator import LaTeXGenerator

        schedule_path = Path(schedule_file)
        logger.info(
            f"Generating TeX forecast from {schedule_path} starting at index {start_index}"
        )

        # Read schedule and generate forecast with time shifting
        schedule = read_schedule(schedule_path)
        forecast_activities = generate_forecast(
            schedule, start_index, start_time, duration_hours, current_position
        )

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No activities found in forecast window ({duration_hours}h from {start_time})",
                output="",
            )

        if "vessel_speed" not in schedule.variables:
            logger.warning(
                f"{schedule_path}: no vessel_speed variable; record speeds are NaN"
            )
        activity_records = [
            record
            for activity_tuple in forecast_activities
            if (
                record := _build_tex_forecast_record(
                    schedule, activity_tuple[0], activity_tuple
                )
            )
            is not None
        ]

        # Ship time: the table is printed in the clock of --start-time
        offset = ship_time_offset(start_time)
        if offset is not None:
            activity_records = [
                dataclasses.replace(
                    r, start_time=r.start_time + offset, end_time=r.end_time + offset
                )
                for r in activity_records
            ]

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_name(f"{schedule_path.stem}_forecast.tex")
        else:
            output_file = Path(output_path)

        # Generate TeX using our LaTeX generator
        generator = LaTeXGenerator()
        cruise_name = f"{schedule_path.stem} forecast"
        tex_content = generator.generate_letsgo_table(
            activity_records,
            cruise_name,
            logo_path=logo_path,
            workplan_number=workplan_number,
            cruise_title=cruise_title,
            anchor_note=anchor_rule(
                schedule, start_index, start_time, current_position
            ),
            time_label=time_zone_label(offset),
        )

        # Write to file
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(tex_content, encoding="utf-8")

        logger.info(f"Successfully generated TeX forecast: {output_file}")

        return StationplanResult(
            success=True,
            message=f"Generated TeX forecast with {len(activity_records)} activities: {output_file}",
            output=str(output_file),
        )

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Error generating TeX forecast: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")


def _activity_to_waypoint_lines(
    activity: tuple,
    schedule: object,
    use_decimal_degrees: bool,
) -> list[str]:
    """Convert one forecast activity tuple to 1-2 bridge waypoint lines.

    Returns an empty list for transit activities or malformed tuples.
    """
    if len(activity) < 9:
        return []

    (
        index,
        _time,
        category,
        activity_type,
        _action,
        _duration,
        latitude,
        longitude,
        name,
    ) = activity

    if category == "transit":
        return []

    work_code = _map_activity_to_work_code(category, activity_type, name)
    exit_lat, exit_lon = _resolve_exit_coordinates(
        schedule, index, latitude, longitude, name, activity_type
    )

    fmt = _format_decimal_degrees if use_decimal_degrees else _format_ddm_coordinate
    entry_lat = fmt(latitude, "lat")
    entry_lon = fmt(longitude, "lon")
    exit_lat_s = fmt(exit_lat, "lat")
    exit_lon_s = fmt(exit_lon, "lon")

    if abs(latitude - exit_lat) > 0.001 or abs(longitude - exit_lon) > 0.001:
        return [
            f"{work_code}\t{entry_lat}\t{entry_lon}\t{name} Start",
            f"{work_code}\t{exit_lat_s}\t{exit_lon_s}\t{name} End",
        ]
    return [f"{work_code}\t{entry_lat}\t{entry_lon}\t{name}"]


def _resolve_exit_coordinates(
    schedule: object,
    index: int,
    latitude: float,
    longitude: float,
    name: str,
    activity_type: str,
) -> tuple[float, float]:
    """Return (exit_lat, exit_lon) for an activity, falling back to entry coords.

    Checks explicit exit_latitude/exit_longitude variables first, then falls
    back to the next waypoint for survey/transit line operations.
    """
    if index >= len(schedule.latitude) - 1:
        return latitude, longitude

    try:
        if (
            "exit_latitude" in schedule.variables
            and "exit_longitude" in schedule.variables
        ):
            exit_lat_val = float(schedule.exit_latitude[index].values)
            exit_lon_val = float(schedule.exit_longitude[index].values)
            if not (np.isnan(exit_lat_val) or np.isnan(exit_lon_val)):
                return exit_lat_val, exit_lon_val
        if (
            "Transit_" in name
            or "Bathy_" in name
            or activity_type in ["survey", "unknown", "underway"]
        ):
            next_lat = float(schedule.latitude[index + 1].values)
            next_lon = float(schedule.longitude[index + 1].values)
            if not (np.isnan(next_lat) or np.isnan(next_lon)):
                return next_lat, next_lon
    except (AttributeError, TypeError, ValueError, IndexError):
        pass

    return latitude, longitude


def stationplan_waypoints(
    schedule_file: str | Path,
    start_index: int | None,
    start_time: str | None = None,
    duration_hours: float | None = 48.0,
    current_position: tuple[float, float] | None = None,
    output_path: str | Path | None = None,
) -> StationplanResult:
    """
    Generate bridge waypoints file in Stationsplan.txt format.

    Creates a simple waypoint list suitable for bridge navigation systems
    with DDM coordinate format and work type codes.

    Parameters
    ----------
    schedule_file : str or Path
        Path to NetCDF schedule file
    start_index : int, optional
        Row index (0-based, as in ``cruiseplan list``); an operation row
        starts at ``start_time``, a transit row starts at ``start_time`` from
        where it begins. If None, the full schedule from row 0.
    start_time : str, optional
        Start time of the anchored operation, or of the ship at
        ``current_position`` (ISO format, UTC; a time without a zone is taken
        as UTC). If None, now (UTC) rounded to 10 minutes.
    duration_hours : float, optional
        Forecast duration in hours (if None, uses remaining schedule)
    current_position : tuple of float, optional
        Ship position (lat, lon) in decimal degrees at ``start_time``. A
        transit from it to the anchored operation is inserted at the leg's
        speed, and the operation starts when it ends.
    output_path : str or Path, optional
        Output file path. If None, returns content as string

    Returns
    -------
    StationplanResult
        Result object containing success status and waypoint content
    """
    try:
        from cruiseplan.forecast.generator import generate_forecast
        from cruiseplan.forecast.reader import read_schedule

        logger.info(f"Generating bridge waypoints from {schedule_file}")

        # Read the schedule file
        schedule = read_schedule(schedule_file)

        # Default start_index to 0 if not provided (full cruise from beginning)
        if start_index is None:
            start_index = 0

        # Default start_time to now, rounded to 10 minutes (like letsgo.m)
        if start_time is None:
            from datetime import UTC, datetime

            from cruiseplan.utils.units import round_to_minutes

            now = datetime.now(UTC).replace(tzinfo=None)
            start_time = round_to_minutes(now, 10).isoformat()

        # Always use forecast mode for waypoints (from start_index forward)
        activities = generate_forecast(
            schedule,
            start_index,
            start_time,
            duration_hours or 1000,
            current_position,
        )

        if not activities:
            return StationplanResult(
                success=False, message="No activities found in schedule", output=""
            )

        # Generate waypoint content in both coordinate formats
        def generate_waypoint_content(use_decimal_degrees: bool = False) -> str:
            waypoint_lines = []

            # Add header with proper spacing
            waypoint_lines.append("%")

            # Add start date if available (at top)
            if start_time:
                start_utc = parse_start_time(start_time).strftime(
                    "%Y-%m-%dT%H:%M:%S UTC"
                )
                waypoint_lines.append(f"% start_date = {start_utc}")

            waypoint_lines.append("%")

            # Add coordinate format indicator
            format_type = (
                "Decimal Degrees"
                if use_decimal_degrees
                else "Degrees Decimal Minutes (DDM)"
            )
            waypoint_lines.append(f"% Coordinate format: {format_type}")

            # Add legend header
            waypoint_lines.append(
                "% (1: Transit, 2: CTD, 3: Mooring, 4: PIES, 5: Float/Drifter, 6: Survey)"
            )
            waypoint_lines.append("%")

            # Add current position if provided
            if current_position:
                lat, lon = current_position
                if use_decimal_degrees:
                    lat_formatted = _format_decimal_degrees(lat, "lat")
                    lon_formatted = _format_decimal_degrees(lon, "lon")
                else:
                    lat_formatted = _format_ddm_coordinate(lat, "lat")
                    lon_formatted = _format_ddm_coordinate(lon, "lon")
                waypoint_lines.append(f"1\t{lat_formatted}\t{lon_formatted}\tMerian")

            # Process activities and convert to waypoints
            for activity in activities:
                waypoint_lines.extend(
                    _activity_to_waypoint_lines(activity, schedule, use_decimal_degrees)
                )

            # Join all lines
            return "\n".join(waypoint_lines) + "\n"

        # Generate content for both formats
        waypoint_content_ddm = generate_waypoint_content(use_decimal_degrees=False)
        waypoint_content_decdeg = generate_waypoint_content(use_decimal_degrees=True)

        # Write to file(s) if path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(exist_ok=True, parents=True)

            # Generate both filenames based on the provided path
            # If output_path is "route/Stationsplan28.txt", generate:
            # - route/Stationsplan28_ddm.txt (degrees decimal minutes)
            # - route/Stationsplan28_decdeg.txt (decimal degrees)

            base_path = output_file.with_suffix("")  # Remove .txt extension
            ddm_file = Path(str(base_path) + "_ddm.txt")
            decdeg_file = Path(str(base_path) + "_decdeg.txt")

            # Write both files
            ddm_file.write_text(waypoint_content_ddm, encoding="utf-8")
            decdeg_file.write_text(waypoint_content_decdeg, encoding="utf-8")

            logger.info(f"Generated bridge waypoints: {ddm_file} and {decdeg_file}")

            # Count waypoints (exclude comment lines)
            waypoint_count = len(
                [
                    line
                    for line in waypoint_content_ddm.split("\n")
                    if line and not line.startswith("%")
                ]
            )

            return StationplanResult(
                success=True,
                message=f"Generated {waypoint_count} waypoints in both coordinate formats",
                output=f"{ddm_file} and {decdeg_file}",
            )
        # Return DDM content directly (default format)
        waypoint_count = len(
            [
                line
                for line in waypoint_content_ddm.split("\n")
                if line and not line.startswith("%")
            ]
        )
        return StationplanResult(
            success=True,
            message=f"Generated {waypoint_count} waypoints (DDM format)",
            output=waypoint_content_ddm,
        )

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Error generating bridge waypoints: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")


def _format_ddm_coordinate(decimal_degrees: float, coord_type: str) -> str:
    """Format a coordinate in degrees decimal minutes for bridge waypoints."""
    from cruiseplan.utils.coordinates import ddm_parts

    degrees, minutes = ddm_parts(decimal_degrees, 2)

    if coord_type == "lat":
        # Latitude: 2 digits for degrees, N/S direction with space
        direction = "N" if decimal_degrees >= 0 else "S"
        return f"{degrees:02d} {minutes:05.2f} {direction}"
    # longitude
    # Longitude: 3 digits for degrees, E/W direction with space
    direction = "E" if decimal_degrees >= 0 else "W"
    return f"{degrees:03d} {minutes:05.2f} {direction}"


def _format_decimal_degrees(decimal_degrees: float, coord_type: str) -> str:
    """Format a coordinate in decimal degrees for bridge waypoints."""
    if coord_type == "lat":
        # Latitude: format with 6 decimal places, signed (negative for South)
        return f"{decimal_degrees:8.5f}"
    # longitude
    # Longitude: format with 6 decimal places, signed (negative for West)
    return f"{decimal_degrees:9.5f}"


def _log_failure(message: str, error: Exception) -> None:
    """Log a failed forecast: a bad input without a traceback, anything else with one."""
    if isinstance(error, ValueError):
        logger.error(message)
    else:
        logger.exception(message)


_WORK_CODE_BY_TYPE: dict[str, int] = {
    "ctd": 2,
    "station": 2,
    "mooring": 3,
    "pies": 4,
    "float": 5,
    "drifter": 5,
    "survey": 6,
    "navigation": 1,
    "transit": 1,
}


def _map_activity_to_work_code(
    _category: str, activity_type: str, name: str = ""
) -> int:
    """
    Map activity category/type to letsgo.m work code.

    Work codes: 1=Transit, 2=CTD, 3=Mooring, 4=PIES, 5=Float/Drifter, 6=Survey
    """
    activity_type_lower = activity_type.lower()
    name_lower = name.lower()

    code = _WORK_CODE_BY_TYPE.get(activity_type_lower)
    if code is not None:
        return code
    if activity_type_lower == "unknown" and "transit_" in name_lower:
        return 6
    if activity_type_lower == "underway" or "bathy_" in name_lower:
        return 6
    return 2


def _convert_raw_activity_to_kml_record(
    activity: tuple, schedule: xr.Dataset | None = None
) -> "ActivityRecord | None":
    """Convert a forecast row to a KML record; None for transits or invalid positions."""
    import pandas as pd

    if len(activity) < 9:
        return None

    (
        index,
        time,
        category,
        activity_type,
        action,
        duration,
        latitude,
        longitude,
        name,
    ) = activity

    if np.isnan(latitude) or np.isnan(longitude):
        return None

    if category == "transit":
        return None

    def stored(var: str, default: str) -> str:
        if schedule is not None and var in schedule.variables and index >= 0:
            return str(schedule[var][index].values).strip()
        return default

    from cruiseplan.forecast.reader import stored_kind

    operation_class = stored("operation_class", "PointOperation")
    if operation_class not in {"PointOperation", "LineOperation", "AreaOperation"}:
        return None  # only scientific operations and ports are shown
    if schedule is not None and index >= 0:
        kind = stored_kind(schedule, index)
    else:
        kind = kind_of(operation_class, activity_type)

    start = pd.to_datetime(time).to_pydatetime()
    minutes = float(duration) * 60.0
    return ActivityRecord(
        kind=kind,
        activity=stored("activity", "Station"),
        label=name,
        entry_lat=float(latitude),
        entry_lon=float(longitude),
        exit_lat=float(latitude),
        exit_lon=float(longitude),
        start_time=start,
        end_time=start + timedelta(minutes=minutes),
        duration_minutes=minutes,
        planned_duration_minutes=minutes,
        dist_nm=0.0,
        vessel_speed_kt=0.0,
        leg_name=stored("leg_assignment", "forecast"),
        op_type=activity_type,
        operation_class=operation_class,
        action=action or None,
    )


def stationplan_forecast_kml(
    schedule_file: str | Path,
    start_index: int,
    start_time: str,
    duration_hours: float,
    output_path: str | Path | None = None,
    current_position: tuple[float, float] | None = None,
) -> StationplanResult:
    """
    Generate KML forecast from a cruise schedule for a specific time window.

    Creates a Google Earth compatible KML file showing scientific operations
    within the specified forecast period.

    Parameters
    ----------
    schedule_file : Union[str, Path]
        Path to the NetCDF schedule file
    start_index : int
        Row index (0-based, as in ``cruiseplan list``); an operation row
        starts at ``start_time``, a transit row starts at ``start_time`` from
        where it begins (with ``current_position``, the operation it leads to
        is used)
    start_time : str
        Start time of the anchored operation, or of the ship at
        ``current_position`` (ISO format, UTC, e.g. '2026-05-05 08:00')
    duration_hours : float
        Forecast duration in hours
    output_path : Union[str, Path, None], optional
        Path to output KML file, by default None
    current_position : tuple of float, optional
        Ship position (lat, lon) in decimal degrees at ``start_time``. A
        transit from it to the anchored operation is inserted at the leg's
        speed, and the operation starts when it ends.

    Returns
    -------
    StationplanResult
        Result object with success status, message, and output path
    """
    try:
        schedule_path = Path(schedule_file)
        if not schedule_path.exists():
            return StationplanResult(
                success=False, message=f"Schedule file not found: {schedule_path}"
            )

        from cruiseplan.forecast.generator import generate_forecast
        from cruiseplan.forecast.reader import read_schedule

        # Read schedule and generate forecast with proper time shifting
        schedule = read_schedule(schedule_file)
        forecast_activities_raw = generate_forecast(
            schedule, start_index, start_time, duration_hours, current_position
        )

        # Convert forecast activities to the format expected by KML generation
        forecast_activities = [
            record
            for activity in forecast_activities_raw
            if (record := _convert_raw_activity_to_kml_record(activity, schedule))
            is not None
        ]

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No scientific activities found in forecast window starting from index {start_index} for {duration_hours} hours",
            )

        # Create a minimal cruise config for KML generation
        class MockCruiseConfig:
            def __init__(self) -> None:
                self.cruise_name = schedule_path.stem
                self.description = (
                    f"Forecast starting from {start_time} for {duration_hours}h"
                )

        mock_config = MockCruiseConfig()

        activity_records = forecast_activities

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_name(f"{schedule_path.stem}_forecast.kml")
        else:
            output_file = Path(output_path)

        # Generate KML
        generator = KMLGenerator()
        output_file = generator.generate_schedule_kml(
            mock_config, activity_records, output_file
        )

        logger.info(f"Successfully generated KML forecast: {output_file}")

        # Count activities
        activity_count = len(forecast_activities)

        return StationplanResult(
            success=True,
            message=f"Generated {activity_count} activities in KML format",
            output=str(output_file),
        )

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Error generating KML forecast: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_forecast_png(
    schedule_file: str | Path,
    start_index: int,
    start_time: str,
    duration_hours: float,
    output_path: str | Path | None = None,
    bathy_source: str = "gebco2025",
    bathy_dir: str = "data/bathymetry",
    bathy_stride: int = 10,
    figsize: tuple[float, float] = (10.0, 8.1),
    lat_bounds: list[float] | None = None,
    lon_bounds: list[float] | None = None,
    max_depth: int | None = None,
    bathy_contours: list[float] | None = None,
    no_title: bool = False,
    no_labels: bool = False,
    no_legend: bool = False,
    current_position: tuple[float, float] | None = None,
) -> StationplanResult:
    """
    Generate PNG map forecast from a cruise schedule for a specific time window.

    Creates a static PNG map showing scientific operations within the specified
    forecast period, using the same map generation system as 'cruiseplan schedule --format png'
    but filtered to show only work from the start-index for the specified duration.

    Parameters
    ----------
    schedule_file : Union[str, Path]
        Path to the NetCDF schedule file
    start_index : int
        Row index (0-based, as in ``cruiseplan list``); an operation row
        starts at ``start_time``, a transit row starts at ``start_time`` from
        where it begins (with ``current_position``, the operation it leads to
        is used)
    start_time : str
        Start time of the anchored operation, or of the ship at
        ``current_position`` (ISO format, UTC, e.g. '2026-05-05 08:00')
    duration_hours : float
        Forecast duration in hours
    output_path : Union[str, Path, None], optional
        Path to output PNG file, by default None
    bathy_source : str, optional
        Bathymetry dataset to use, by default "gebco2025"
    bathy_dir : str, optional
        Directory containing bathymetry data, by default "data/bathymetry"
    bathy_stride : int, optional
        Bathymetry grid downsampling factor, by default 10
    figsize : tuple[float, float], optional
        Figure size in inches, by default (10.0, 8.1)
    lat_bounds : list[float], optional
        Latitude bounds [min, max], by default None
    lon_bounds : list[float], optional
        Longitude bounds [min, max], by default None
    max_depth : int, optional
        Maximum water depth (m) for the bathymetry colour scale, by default None
    bathy_contours : list[float], optional
        Explicit contour depths in metres, by default None
    no_title : bool, optional
        Suppress the map title, by default False
    no_labels : bool, optional
        Suppress station name labels, by default False
    no_legend : bool, optional
        Suppress the map legend, by default False
    current_position : tuple of float, optional
        Ship position (lat, lon) in decimal degrees at ``start_time``. A
        transit from it to the anchored operation is inserted at the leg's
        speed, and the operation starts when it ends.

    Returns
    -------
    StationplanResult
        Result object with success status, message, and output path
    """
    try:
        from cruiseplan.forecast.generator import generate_forecast
        from cruiseplan.forecast.reader import read_schedule
        from cruiseplan.output.map_generator import generate_map_from_timeline

        schedule_path = Path(schedule_file)
        if not schedule_path.exists():
            return StationplanResult(
                success=False, message=f"Schedule file not found: {schedule_path}"
            )

        logger.info(
            f"Generating PNG forecast from {schedule_path} starting at index {start_index}"
        )

        # Read schedule and generate forecast with time shifting
        schedule = read_schedule(schedule_path)
        forecast_activities = generate_forecast(
            schedule, start_index, start_time, duration_hours, current_position
        )

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No activities found in forecast window ({duration_hours}h from {start_time})",
                output="",
            )

        # Convert forecast activities to timeline format compatible with map generator
        # The map generator expects timeline data similar to what comes from the scheduler
        timeline_for_map = []

        for activity_tuple in forecast_activities:
            (
                index,
                time,
                category,
                activity_type,
                _action,
                duration,
                latitude,
                longitude,
                name,
            ) = activity_tuple

            # Skip transit activities for map visualization (focus on science operations)
            if category == "transit":
                continue

            water_depth, operation_depth, _ = _lookup_schedule_depth_data(
                schedule, index
            )
            minutes = float(duration) * 60.0
            timeline_record = ActivityRecord(
                kind="station",
                activity=category,
                label=name,
                entry_lat=float(latitude),
                entry_lon=float(longitude),
                exit_lat=float(latitude),
                exit_lon=float(longitude),
                start_time=time,
                end_time=time + timedelta(minutes=minutes),
                duration_minutes=minutes,
                planned_duration_minutes=minutes,
                dist_nm=0.0,
                vessel_speed_kt=0.0,
                operation_class="PointOperation",
                leg_name="forecast",
                op_type=activity_type,
                water_depth_m=water_depth,
                operation_depth_m=operation_depth,
            )

            timeline_for_map.append(timeline_record)

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_name(f"{schedule_path.stem}_forecast.png")
        else:
            output_file = Path(output_path)
            if output_file.suffix.lower() in [".txt", ".tex", ".kml"]:
                output_file = output_file.with_suffix(".png")

        # Generate PNG map using the same function as cruiseplan schedule
        map_file = generate_map_from_timeline(
            timeline=timeline_for_map,
            output_file=output_file,
            bathy_source=bathy_source,
            bathy_dir=bathy_dir,
            bathy_stride=bathy_stride,
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            figsize=figsize,
            no_ports=True,  # Focus on operations, not ports for forecast
            config=None,  # No cruise config needed for forecast
            max_depth=max_depth,
            bathy_contours=bathy_contours,
            no_title=no_title,
            no_labels=no_labels,
            no_legend=no_legend,
        )

        if map_file:
            logger.info(f"Successfully generated PNG forecast map: {map_file}")
            activity_count = len(timeline_for_map)
            return StationplanResult(
                success=True,
                message=f"Generated PNG forecast map with {activity_count} activities",
                output=str(map_file),
            )
        return StationplanResult(
            success=False,
            message="PNG map generation failed",
            output="",
        )

    except Exception as e:  # noqa: BLE001 - reported in the result; logged with a traceback
        error_msg = f"Error generating PNG forecast: {e}"
        _log_failure(error_msg, e)
        return StationplanResult(success=False, message=error_msg, output="")
