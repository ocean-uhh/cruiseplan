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
from cruiseplan.output.kml_generator import KMLGenerator

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
    schedule_file: Union[str, Path], 
    output_path: Union[str, Path] = None,
    logo_path: Union[str, Path] = None,
    workplan_number: str = None,
    cruise_title: str = None,
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
        generated_file = generate_letsgo_table_from_netcdf(schedule_path, output_file, logo_path, workplan_number, cruise_title)

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
    logo_path: Union[str, Path] = None,
    workplan_number: str = None,
    cruise_title: str = None,
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
    logo_path : str or Path, optional
        Path to logo image file (PNG, JPG, or PDF). If None, checks for default logos in images/ folder

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
        
        # First pass: collect transit distances for repositioning
        transit_distances = {}  # Maps operation_index -> transit_distance_to_next
        for i, activity_tuple in enumerate(forecast_activities):
            index, time, category, activity_type, action, duration, latitude, longitude, name = activity_tuple
            if category == "transit" and i > 0:
                # This is a transit - find the previous operation
                prev_activity = forecast_activities[i-1]
                prev_index = prev_activity[0]
                # Get transit distance from NetCDF
                transit_dist = float(schedule.dist_nm[index].values) if "dist_nm" in schedule.variables else 0.0
                transit_distances[prev_index] = transit_dist
        
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
            comment = ""
            
            if "water_depth" in schedule.variables:
                try:
                    depth_val = schedule.water_depth[index].values
                    if depth_val is not None and not np.isnan(float(depth_val)):
                        water_depth = float(depth_val)
                except (TypeError, ValueError):
                    pass  # Keep water_depth as None

            if "operation_depth" in schedule.variables:
                try:
                    op_depth_val = schedule.operation_depth[index].values
                    if op_depth_val is not None and not np.isnan(float(op_depth_val)):
                        operation_depth = float(op_depth_val)
                except (TypeError, ValueError):
                    pass  # Keep operation_depth as None
                    
            if "comment" in schedule.variables:
                comment_val = str(schedule.comment[index].values)
                if comment_val and comment_val != "nan" and comment_val != "_":
                    comment = comment_val

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

            # Create single record for all operations (including line operations)
            # Calculate end time
            from datetime import timedelta
            end_time = time + timedelta(hours=duration)

            # Get operation distance from NetCDF (for line operations)
            operation_distance = float(schedule.dist_nm[index].values) if "dist_nm" in schedule.variables else 0.0
            
            # Get transit distance to next operation (for repositioning)
            next_transit_distance = transit_distances.get(index, 0.0)

            # Single record for operation
            record_data = {
                "activity": category,
                "label": name,  # Use original name without "Start"/"End"
                "entry_lat": float(latitude),
                "entry_lon": float(longitude),
                "exit_lat": float(exit_lat),
                "exit_lon": float(exit_lon),
                "start_time": time,
                "end_time": end_time,
                "duration_minutes": float(duration) * 60.0,
                "water_depth": water_depth,
                "operation_depth": operation_depth,
                "dist_nm": operation_distance,  # Distance of the operation itself
                "transit_dist_nm": next_transit_distance,  # Distance to next operation
                "vessel_speed_kt": 10.0,
                "leg_name": "forecast",
                "op_type": activity_type,
                "operation_class": "LineOperation" if operation_distance > 0.1 else "PointOperation",
                "action": action if action else None,
                "comment": comment,
            }

            # Create ActivityRecord-like objects
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
        tex_content = generator.generate_letsgo_table(
            activity_records, 
            cruise_name, 
            logo_path=logo_path,
            workplan_number=workplan_number,
            cruise_title=cruise_title
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

        # Generate waypoint content in both coordinate formats
        def generate_waypoint_content(use_decimal_degrees=False):
            waypoint_lines = []

            # Add header with proper spacing
            waypoint_lines.append("%")

            # Add start date if available (at top)
            if start_time:
                waypoint_lines.append(f"% start_date = {start_time}")

            waypoint_lines.append("%")
            
            # Add coordinate format indicator
            format_type = "Decimal Degrees" if use_decimal_degrees else "Degrees Decimal Minutes (DDM)"
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

                    # Convert coordinates to appropriate format
                    if use_decimal_degrees:
                        entry_lat_formatted = _format_decimal_degrees(latitude, "lat")
                        entry_lon_formatted = _format_decimal_degrees(longitude, "lon")
                        exit_lat_formatted = _format_decimal_degrees(exit_lat, "lat")
                        exit_lon_formatted = _format_decimal_degrees(exit_lon, "lon")
                    else:
                        entry_lat_formatted = _format_ddm_coordinate(latitude, "lat")
                        entry_lon_formatted = _format_ddm_coordinate(longitude, "lon")
                        exit_lat_formatted = _format_ddm_coordinate(exit_lat, "lat")
                        exit_lon_formatted = _format_ddm_coordinate(exit_lon, "lon")

                    # Create waypoint lines
                    # If start and end are the same, just show one waypoint
                    if (
                        abs(latitude - exit_lat) > 0.001
                        or abs(longitude - exit_lon) > 0.001
                    ):
                        # Different start/end positions - show both
                        waypoint_lines.append(
                            f"{work_code}\t{entry_lat_formatted}\t{entry_lon_formatted}\t{name} Start"
                        )
                        waypoint_lines.append(
                            f"{work_code}\t{exit_lat_formatted}\t{exit_lon_formatted}\t{name} End"
                        )
                    else:
                        # Same position - show single waypoint without suffix
                        waypoint_lines.append(
                            f"{work_code}\t{entry_lat_formatted}\t{entry_lon_formatted}\t{name}"
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
            
            base_path = output_file.with_suffix('')  # Remove .txt extension
            ddm_file = Path(str(base_path) + '_ddm.txt')
            decdeg_file = Path(str(base_path) + '_decdeg.txt')
            
            # Write both files
            ddm_file.write_text(waypoint_content_ddm, encoding="utf-8")
            decdeg_file.write_text(waypoint_content_decdeg, encoding="utf-8")

            logger.info(f"Generated bridge waypoints: {ddm_file} and {decdeg_file}")
            
            # Count waypoints (exclude comment lines)
            waypoint_count = len([l for l in waypoint_content_ddm.split('\n') if l and not l.startswith('%')])

            return StationplanResult(
                success=True,
                message=f"Generated {waypoint_count} waypoints in both coordinate formats",
                output=f"{ddm_file} and {decdeg_file}",
            )
        else:
            # Return DDM content directly (default format)
            waypoint_count = len([l for l in waypoint_content_ddm.split('\n') if l and not l.startswith('%')])
            return StationplanResult(
                success=True,
                message=f"Generated {waypoint_count} waypoints (DDM format)",
                output=waypoint_content_ddm,
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


def _format_decimal_degrees(decimal_degrees: float, coord_type: str) -> str:
    """Format a coordinate in decimal degrees for bridge waypoints."""
    if coord_type == "lat":
        # Latitude: format with 6 decimal places, signed (negative for South)
        return f"{decimal_degrees:8.5f}"
    else:  # longitude
        # Longitude: format with 6 decimal places, signed (negative for West)  
        return f"{decimal_degrees:9.5f}"


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


def stationplan_forecast_kml(
    schedule_file: Union[str, Path],
    start_index: int,
    start_time: str,
    duration_hours: float,
    output_path: Union[str, Path, None] = None,
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
        Activity index to start forecast from
    start_time : str
        Forecast start time in ISO format (e.g., '2026-05-05 08:00')
    duration_hours : float
        Forecast duration in hours
    output_path : Union[str, Path, None], optional
        Path to output KML file, by default None

    Returns
    -------
    StationplanResult
        Result object with success status, message, and output path
    """
    try:
        import netCDF4
        from datetime import datetime
        import pandas as pd
        from cruiseplan.config.cruise_config import CruiseConfig

        schedule_path = Path(schedule_file)
        if not schedule_path.exists():
            return StationplanResult(
                success=False, message=f"Schedule file not found: {schedule_path}"
            )

        # Convert start_time string to datetime
        try:
            forecast_start = pd.to_datetime(start_time)
        except Exception as e:
            return StationplanResult(
                success=False,
                message=f"Invalid start time format '{start_time}': {e}",
            )

        forecast_end = forecast_start + pd.Timedelta(hours=duration_hours)

        # Read the NetCDF schedule
        with netCDF4.Dataset(schedule_path, "r") as schedule:
            # Get basic dimensions and data
            num_activities = len(schedule.dimensions["index"])
            
            if start_index >= num_activities:
                return StationplanResult(
                    success=False,
                    message=f"Start index {start_index} is beyond available activities (max: {num_activities - 1})",
                )

            # Extract time data
            time_data = schedule.variables["time"][:]
            time_units = schedule.variables["time"].units
            
            # Convert to datetime
            times = pd.to_datetime(netCDF4.num2date(time_data, time_units))
            
            # Find activities within forecast window
            forecast_activities = []
            
            for i in range(start_index, num_activities):
                activity_time = times[i]
                
                # Stop if we've gone beyond forecast window
                if activity_time > forecast_end:
                    break
                
                # Include activities that start within or overlap the forecast window
                if activity_time >= forecast_start:
                    latitude = float(schedule.variables["latitude"][i])
                    longitude = float(schedule.variables["longitude"][i])
                    
                    # Skip if coordinates are invalid
                    if np.isnan(latitude) or np.isnan(longitude):
                        continue
                    
                    # Get activity details
                    name = str(schedule.variables["name"][i])
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    
                    category = str(schedule.variables["category"][i])
                    if isinstance(category, bytes):
                        category = category.decode('utf-8')
                    
                    activity_type = str(schedule.variables["activity"][i])
                    if isinstance(activity_type, bytes):
                        activity_type = activity_type.decode('utf-8')
                    
                    action = ""
                    if "action" in schedule.variables:
                        action = str(schedule.variables["action"][i])
                        if isinstance(action, bytes):
                            action = action.decode('utf-8')
                    
                    duration = float(schedule.variables["duration"][i])
                    
                    # Get water depth
                    water_depth = None
                    if "water_depth" in schedule.variables:
                        depth_val = schedule.variables["water_depth"][i]
                        if not np.isnan(depth_val):
                            water_depth = float(depth_val)
                    
                    # Get operation distance for line operations
                    operation_distance = 0.0
                    if "dist_nm" in schedule.variables:
                        dist_val = schedule.variables["dist_nm"][i]
                        if not np.isnan(dist_val):
                            operation_distance = float(dist_val)
                    
                    # Skip transit activities - only include scientific operations
                    if category == "transit":
                        continue
                    
                    # Create activity record compatible with KMLGenerator
                    activity_record = {
                        "label": name,
                        "lat": latitude,
                        "lon": longitude,
                        "start_time": activity_time,
                        "duration_minutes": duration * 60.0,
                        "activity": "Station" if category in ["station", "ctd"] else category.title(),
                        "action": action,
                        "depth": water_depth,
                        "dist_nm": operation_distance,
                    }
                    
                    # Add line operation coordinates if available
                    if operation_distance > 0.1:  # Line operation
                        # Try to get start coordinates (entry point)
                        if i > 0:
                            start_lat = float(schedule.variables["latitude"][i-1])
                            start_lon = float(schedule.variables["longitude"][i-1])
                            if not (np.isnan(start_lat) or np.isnan(start_lon)):
                                activity_record["start_lat"] = start_lat
                                activity_record["start_lon"] = start_lon
                    
                    forecast_activities.append(activity_record)

        if not forecast_activities:
            return StationplanResult(
                success=False,
                message=f"No scientific activities found in forecast window {forecast_start} to {forecast_end}",
            )

        # Create a minimal cruise config for KML generation
        class MockCruiseConfig:
            def __init__(self):
                self.cruise_name = schedule_path.stem
                self.description = f"Forecast from {forecast_start.strftime('%Y-%m-%d %H:%M')} for {duration_hours}h"

        mock_config = MockCruiseConfig()

        # Convert to ActivityRecord-like objects for KMLGenerator
        class MockActivityRecord:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
                
                # Convert to dict access for KML generator compatibility
                self.data = data
                
            def __getitem__(self, key):
                return self.data[key]
                
            def get(self, key, default=None):
                return self.data.get(key, default)

        activity_records = [MockActivityRecord(activity) for activity in forecast_activities]

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_name(f"{schedule_path.stem}_forecast.kml")
        else:
            output_file = Path(output_path)

        # Generate KML
        generator = KMLGenerator()
        output_file = generator.generate_schedule_kml(mock_config, activity_records, output_file)

        logger.info(f"Successfully generated KML forecast: {output_file}")
        
        # Count activities
        activity_count = len(forecast_activities)

        return StationplanResult(
            success=True,
            message=f"Generated {activity_count} activities in KML format",
            output=str(output_file),
        )

    except Exception as e:
        error_msg = f"Error generating KML forecast: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")


def stationplan_forecast_png(
    schedule_file: Union[str, Path],
    start_index: int,
    start_time: str,
    duration_hours: float,
    output_path: Union[str, Path, None] = None,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data",
    bathy_stride: int = 10,
    figsize: tuple[float, float] = (12.0, 8.0),
    lat_bounds: list[float] = None,
    lon_bounds: list[float] = None,
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
        Activity index to start forecast from
    start_time : str
        Forecast start time in ISO format (e.g., '2026-05-05 08:00')
    duration_hours : float
        Forecast duration in hours
    output_path : Union[str, Path, None], optional
        Path to output PNG file, by default None
    bathy_source : str, optional
        Bathymetry dataset to use, by default "etopo2022"
    bathy_dir : str, optional
        Directory containing bathymetry data, by default "data"
    bathy_stride : int, optional
        Bathymetry contour stride, by default 10
    figsize : tuple[float, float], optional
        Figure size in inches, by default (12.0, 8.0)
    lat_bounds : list[float], optional
        Latitude bounds [min, max], by default None
    lon_bounds : list[float], optional
        Longitude bounds [min, max], by default None

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
            schedule, start_index, start_time, duration_hours
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
                action,
                duration,
                latitude,
                longitude,
                name,
            ) = activity_tuple

            # Skip transit activities for map visualization (focus on science operations)
            if category == "transit":
                continue

            # Create timeline record compatible with map generator
            # The map generator extracts lat/lon and labels from these records
            timeline_record = {
                "activity": category,
                "label": name,
                "lat": float(latitude),  # Map generator expects "lat", not "entry_lat"
                "lon": float(longitude),  # Map generator expects "lon", not "entry_lon"
                "entry_lat": float(latitude),
                "entry_lon": float(longitude),
                "start_time": time,
                "duration_minutes": float(duration) * 60.0,
                "operation_class": "PointOperation",  # Simplified for forecast map
                "leg_name": "forecast",
                "op_type": activity_type,
            }

            # Add operation depth and water depth if available from schedule
            try:
                if "water_depth" in schedule.variables:
                    depth_val = schedule.water_depth[index].values
                    if not np.isnan(float(depth_val)):
                        timeline_record["water_depth"] = float(depth_val)
                        
                if "operation_depth" in schedule.variables:
                    op_depth_val = schedule.operation_depth[index].values
                    if not np.isnan(float(op_depth_val)):
                        timeline_record["operation_depth"] = float(op_depth_val)
            except:
                pass  # Skip if depth data unavailable
                
            timeline_for_map.append(timeline_record)

        # Determine output path
        if output_path is None:
            output_file = schedule_path.with_name(f"{schedule_path.stem}_forecast.png")
        else:
            output_file = Path(output_path)
            if output_file.suffix.lower() in ['.txt', '.tex', '.kml']:
                output_file = output_file.with_suffix('.png')

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
        )

        if map_file:
            logger.info(f"Successfully generated PNG forecast map: {map_file}")
            activity_count = len(timeline_for_map)
            return StationplanResult(
                success=True,
                message=f"Generated PNG forecast map with {activity_count} activities",
                output=str(map_file),
            )
        else:
            return StationplanResult(
                success=False,
                message="PNG map generation failed",
                output="",
            )

    except Exception as e:
        error_msg = f"Error generating PNG forecast: {e}"
        logger.error(error_msg)
        return StationplanResult(success=False, message=error_msg, output="")
