"""
Station plan API for generating cruise activity lists and forecasts.

This module provides the main API functions for reading cruise schedules
and generating station plan outputs for real-time cruise operations.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np

from cruiseplan.forecast.formatter import format_letsgo_output
from cruiseplan.forecast.generator import (
    format_activities_table,
    generate_forecast,
    list_activities,
)
from cruiseplan.forecast.reader import read_schedule

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


def stationplan_list(schedule_file: Union[str, Path]) -> StationplanResult:
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

    except Exception as e:
        error_msg = f"Unexpected error processing schedule: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_forecast(
    schedule_file: Union[str, Path],
    start_index: int,
    start_time: str,
    duration_hours: float = 24.0,
    transit_speed: float = 10.0,
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
        Index of first activity in forecast (0-based)
    start_time : str
        New absolute start time for the selected activity (ISO format: "2026-08-30T14:00:00")
    duration_hours : float, optional
        Forecast duration in hours (default: 24.0)
    transit_speed : float, optional
        Ship transit speed in knots for header metadata (default: 10.0)

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
            schedule, start_index, start_time, duration_hours
        )

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No activities found in forecast window ({duration_hours}h from {start_time})",
                output="",
            )

        # Format as letsgo.m output
        output_text = format_letsgo_output(
            forecast_activities, start_time, transit_speed
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

    except Exception as e:
        error_msg = f"Unexpected error generating forecast: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_tex(
    schedule_file: Union[str, Path], output_path: Union[str, Path] = None
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
        generated_file = generate_letsgo_table_from_netcdf(schedule_path, output_file)

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

    except Exception as e:
        error_msg = f"Error generating TeX table: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_forecast_tex(
    schedule_file: Union[str, Path],
    start_index: int,
    start_time: str,
    duration_hours: float = 24.0,
    output_path: Union[str, Path] = None,
) -> StationplanResult:
    """
    Generate TeX station forecast starting from specified activity.

    Combines forecast generation with TeX formatting - generates a time-shifted
    forecast and outputs it as a complete LaTeX document.

    Parameters
    ----------
    schedule_file : str or Path
        Path to NetCDF schedule file
    start_index : int
        Index of first activity in forecast (0-based)
    start_time : str
        New absolute start time (ISO format: "2026-08-30T14:00:00")
    duration_hours : float
        Forecast duration in hours (default: 24.0)
    output_path : str or Path, optional
        Output path for .tex file

    Returns
    -------
    StationplanResult
        Result object with success status and generated file path
    """
    try:

        import numpy as np

        from cruiseplan.forecast.generator import generate_forecast
        from cruiseplan.forecast.reader import read_schedule
        from cruiseplan.output.latex_generator import LaTeXGenerator

        schedule_path = Path(schedule_file)
        logger.info(
            f"Generating TeX forecast from {schedule_path} starting at index {start_index}"
        )

        # Read schedule and generate forecast with time shifting
        schedule = read_schedule(schedule_path)
        forecast_activities = generate_forecast(
            schedule, start_index, start_time, duration_hours
        )

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No activities found in forecast window ({duration_hours}h from {start_time})",
                output="",
            )

        # Convert forecast activities to ActivityRecord objects for TeX generation
        # generate_forecast returns tuples: (index, time, category, type, action, duration, lat, lon, name)
        activity_records = []
        for activity_tuple in forecast_activities:
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
            ) = activity_tuple

            # Look up additional data from original schedule using the index
            water_depth = None
            operation_depth = None
            if "water_depth" in schedule.variables:
                depth_val = schedule.water_depth[index].values
                if not np.isnan(depth_val):
                    water_depth = float(depth_val)

            if "operation_depth" in schedule.variables:
                op_depth_val = schedule.operation_depth[index].values
                if not np.isnan(op_depth_val):
                    operation_depth = float(op_depth_val)

            # Look up exit coordinates if available
            exit_lat, exit_lon = latitude, longitude  # Default to same position
            try:
                if (
                    "exit_latitude" in schedule.variables
                    and "exit_longitude" in schedule.variables
                ):
                    exit_lat_val = float(schedule.exit_latitude[index].values)
                    exit_lon_val = float(schedule.exit_longitude[index].values)
                    if not (np.isnan(exit_lat_val) or np.isnan(exit_lon_val)):
                        exit_lat, exit_lon = exit_lat_val, exit_lon_val
            except:
                pass  # Use entry coordinates as fallback

            # Skip transit activities for TeX output (like waypoints)
            if category == "transit":
                continue

            # Check if we need start/end entries
            if abs(latitude - exit_lat) > 0.001 or abs(longitude - exit_lon) > 0.001:
                # Different start/end positions - create two records

                # Start position record
                start_record_data = {
                    "activity": category,
                    "label": f"{name} Start",
                    "entry_lat": float(latitude),
                    "entry_lon": float(longitude),
                    "exit_lat": float(latitude),
                    "exit_lon": float(longitude),
                    "start_time": time,
                    "end_time": time,
                    "duration_minutes": float(duration) * 60.0,
                    "water_depth": water_depth,
                    "operation_depth": operation_depth,
                    "dist_nm": 0.0,
                    "vessel_speed_kt": 10.0,
                    "leg_name": "forecast",
                    "op_type": activity_type,
                    "operation_class": "PointOperation",
                    "action": action if action else None,
                }

                # End position record
                end_record_data = {
                    "activity": category,
                    "label": f"{name} End",
                    "entry_lat": float(exit_lat),
                    "entry_lon": float(exit_lon),
                    "exit_lat": float(exit_lat),
                    "exit_lon": float(exit_lon),
                    "start_time": time,
                    "end_time": time,
                    "duration_minutes": float(duration) * 60.0,
                    "water_depth": water_depth,
                    "operation_depth": operation_depth,
                    "dist_nm": 0.0,
                    "vessel_speed_kt": 10.0,
                    "leg_name": "forecast",
                    "op_type": activity_type,
                    "operation_class": "PointOperation",
                    "action": action if action else None,
                }

                # Create ActivityRecord-like objects
                class ForecastRecord:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)

                activity_records.append(ForecastRecord(start_record_data))
                activity_records.append(ForecastRecord(end_record_data))
            else:
                # Same position - create single record
                record_data = {
                    "activity": category,
                    "label": name,
                    "entry_lat": float(latitude),
                    "entry_lon": float(longitude),
                    "exit_lat": float(latitude),
                    "exit_lon": float(longitude),
                    "start_time": time,
                    "end_time": time,
                    "duration_minutes": float(duration) * 60.0,
                    "water_depth": water_depth,
                    "operation_depth": operation_depth,
                    "dist_nm": 0.0,
                    "vessel_speed_kt": 10.0,
                    "leg_name": "forecast",
                    "op_type": activity_type,
                    "operation_class": "PointOperation",
                    "action": action if action else None,
                }

                # Create ActivityRecord-like object
                class ForecastRecord:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)

                activity_records.append(ForecastRecord(record_data))

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_name(f"{schedule_path.stem}_forecast.tex")
        else:
            output_file = Path(output_path)

        # Generate TeX using our LaTeX generator
        generator = LaTeXGenerator()
        cruise_name = f"{schedule_path.stem} forecast"
        tex_content = generator.generate_letsgo_table(activity_records, cruise_name)

        # Write to file
        output_file.parent.mkdir(exist_ok=True, parents=True)
        output_file.write_text(tex_content, encoding="utf-8")

        logger.info(f"Successfully generated TeX forecast: {output_file}")

        return StationplanResult(
            success=True,
            message=f"Generated TeX forecast with {len(activity_records)} activities: {output_file}",
            output=str(output_file),
        )

    except Exception as e:
        error_msg = f"Error generating TeX forecast: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_waypoints(
    schedule_file: Union[str, Path],
    start_index: int,
    start_time: str = None,
    duration_hours: float = 48.0,
    current_position: tuple[float, float] = None,
    output_path: Union[str, Path] = None,
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
        Starting activity index for forecast mode (if None, uses full schedule)
    start_time : str, optional
        New start time for forecast mode (ISO format)
    duration_hours : float, optional
        Forecast duration in hours (if None, uses remaining schedule)
    current_position : tuple[float, float], optional
        Current ship position as (lat, lon) in decimal degrees
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

        # Default start_time to now, rounded to 10 minutes
        if start_time is None:
            from datetime import datetime

            now = datetime.now()
            # Round to nearest 10 minutes (like letsgo.m)
            total_minutes = now.hour * 60 + now.minute
            rounded_minutes = round(total_minutes / 10) * 10
            hours = rounded_minutes // 60
            minutes = rounded_minutes % 60
            start_time = now.replace(
                hour=hours % 24, minute=minutes, second=0, microsecond=0
            ).isoformat()

        # Always use forecast mode for waypoints (from start_index forward)
        activities = generate_forecast(
            schedule, start_index, start_time, duration_hours or 1000
        )

        if not activities:
            return StationplanResult(
                success=False, message="No activities found in schedule", output=""
            )

        # Generate waypoint content
        waypoint_lines = []

        # Add header with proper spacing
        waypoint_lines.append("%")

        # Add start date if available (at top)
        if start_time:
            waypoint_lines.append(f"% start_date = {start_time}")

        waypoint_lines.append("%")

        # Add legend header
        waypoint_lines.append(
            "% (1: Transit, 2: CTD, 3: Mooring, 4: PIES, 5: Float/Drifter, 6: Survey)"
        )
        waypoint_lines.append("%")

        # Add current position if provided
        if current_position:
            lat, lon = current_position
            lat_ddm = _format_ddm_coordinate(lat, "lat")
            lon_ddm = _format_ddm_coordinate(lon, "lon")
            waypoint_lines.append(f"1, {lat_ddm}, {lon_ddm}, Merian")

        # Process activities and convert to waypoints
        for activity in activities:
            if len(activity) >= 9:
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

                # Skip transit activities (we only want operational stations)
                if category == "transit":
                    continue

                # Map activity types to work codes
                work_code = _map_activity_to_work_code(category, activity_type, name)

                # For stations, we need both entry and exit positions
                # Check if we have separate exit coordinates in the original schedule
                exit_lat, exit_lon = latitude, longitude  # Default to same position

                if index < len(schedule.latitude) - 1:
                    # Look up exit coordinates from original schedule if available
                    try:
                        if (
                            "exit_latitude" in schedule.variables
                            and "exit_longitude" in schedule.variables
                        ):
                            exit_lat_val = float(schedule.exit_latitude[index].values)
                            exit_lon_val = float(schedule.exit_longitude[index].values)
                            if not (np.isnan(exit_lat_val) or np.isnan(exit_lon_val)):
                                exit_lat, exit_lon = exit_lat_val, exit_lon_val
                        # For line operations without explicit exit coordinates,
                        # use the next waypoint as the exit position
                        elif (
                            "Transit_" in name
                            or "Bathy_" in name
                            or activity_type in ["survey", "unknown", "underway"]
                        ):
                            next_lat = float(schedule.latitude[index + 1].values)
                            next_lon = float(schedule.longitude[index + 1].values)
                            if not (np.isnan(next_lat) or np.isnan(next_lon)):
                                exit_lat, exit_lon = next_lat, next_lon
                    except:
                        pass  # Use entry coordinates as fallback

                # Convert coordinates to DDM format
                entry_lat_ddm = _format_ddm_coordinate(latitude, "lat")
                entry_lon_ddm = _format_ddm_coordinate(longitude, "lon")
                exit_lat_ddm = _format_ddm_coordinate(exit_lat, "lat")
                exit_lon_ddm = _format_ddm_coordinate(exit_lon, "lon")

                # Create waypoint lines
                # If start and end are the same, just show one waypoint
                if (
                    abs(latitude - exit_lat) > 0.001
                    or abs(longitude - exit_lon) > 0.001
                ):
                    # Different start/end positions - show both
                    waypoint_lines.append(
                        f"{work_code}, {entry_lat_ddm}, {entry_lon_ddm}, {name} Start"
                    )
                    waypoint_lines.append(
                        f"{work_code}, {exit_lat_ddm}, {exit_lon_ddm}, {name} End"
                    )
                else:
                    # Same position - show single waypoint without suffix
                    waypoint_lines.append(
                        f"{work_code}, {entry_lat_ddm}, {entry_lon_ddm}, {name}"
                    )

        # Join all lines
        waypoint_content = "\n".join(waypoint_lines) + "\n"

        # Write to file if path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(exist_ok=True, parents=True)
            output_file.write_text(waypoint_content, encoding="utf-8")

            logger.info(f"Generated bridge waypoints: {output_file}")

            return StationplanResult(
                success=True,
                message=f"Generated {len([l for l in waypoint_lines if not l.startswith('%')])} waypoints: {output_file}",
                output=str(output_file),
            )
        else:
            # Return content directly
            return StationplanResult(
                success=True,
                message=f"Generated {len([l for l in waypoint_lines if not l.startswith('%')])} waypoints",
                output=waypoint_content,
            )

    except Exception as e:
        error_msg = f"Error generating bridge waypoints: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")


def _format_ddm_coordinate(decimal_degrees: float, coord_type: str) -> str:
    """Format a coordinate in degrees decimal minutes for bridge waypoints."""
    from cruiseplan.utils.coordinates import CoordConverter

    degrees, minutes = CoordConverter.decimal_degrees_to_ddm(decimal_degrees)

    if coord_type == "lat":
        # Latitude: 2 digits for degrees, N/S direction with space
        direction = "N" if decimal_degrees >= 0 else "S"
        return f"{int(abs(degrees)):02d} {minutes:05.2f} {direction}"
    else:  # longitude
        # Longitude: 3 digits for degrees, E/W direction with space
        direction = "E" if decimal_degrees >= 0 else "W"
        return f"{int(abs(degrees)):03d} {minutes:05.2f} {direction}"


def _map_activity_to_work_code(
    category: str, activity_type: str, name: str = ""
) -> int:
    """
    Map activity category/type to letsgo.m work code.

    Work codes: 1=Transit, 2=CTD, 3=Mooring, 4=PIES, 5=Float/Drifter, 6=Survey
    """
    if activity_type in ["ctd", "station"]:
        return 2  # CTD
    elif activity_type in ["mooring"]:
        return 3  # Mooring
    elif activity_type in ["pies"]:
        return 4  # PIES
    elif activity_type in ["float", "drifter"]:
        return 5  # Float/Drifter
    elif activity_type in ["survey"]:
        return 6  # Survey
    elif activity_type in ["navigation", "transit"]:
        return 1  # Transit
    elif activity_type in ["unknown"] and "Transit_" in name:
        return 6  # Survey lines (Transit_X_Y pattern)
    elif activity_type in ["underway"] or "Bathy_" in name:
        return 6  # Survey lines (underway operations or Bathy_X_Y pattern)
    else:
        return 2  # Default to CTD for unknown types
