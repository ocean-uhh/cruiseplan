"""
Scientific data format output (NetCDF and CSV).
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

import netCDF4 as nc
import numpy as np
import pandas as pd

# Assume ActivityRecord is imported from the new scheduler module
from cruiseplan.calculators.scheduler import ActivityRecord
from cruiseplan.core.validation import CruiseConfig
from cruiseplan.utils.constants import minutes_to_hours
from cruiseplan.utils.coordinates import format_position_string

logger = logging.getLogger(__name__)


def generate_netcdf_output(
    config: CruiseConfig,
    timeline: List[ActivityRecord],
    output_dir: Path,
    file_name: str = "cruise.nc",
) -> Path:
    """
    Generates the primary NetCDF file based on the scheduled timeline.

    Adheres to CF (Climate and Forecast) conventions where applicable.

    Returns
    -------
        Path to the generated NetCDF file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name

    if not timeline:
        logger.warning("Timeline is empty; skipping NetCDF generation.")
        return output_path

    # Filter out Transit activities for the 'station' dimension
    # (Since dimensions are often based on physical sampling points)
    station_timeline = [
        r for r in timeline if r["operation_type"] not in ["Transit", "Area", "Line"]
    ]

    if not station_timeline:
        logger.warning(
            "No discrete sampling activities found; skipping NetCDF generation."
        )
        return output_path

    # --- 1. Prepare Data Arrays ---

    # Convert datetimes to seconds since epoch (a common NetCDF time format)
    epoch = datetime(1970, 1, 1)
    time_seconds = np.array(
        [(r["start_time"] - epoch).total_seconds() for r in station_timeline]
    )

    # Calculate cumulative distance (in nautical miles, as used in spec)
    cumulative_distance = np.cumsum([r["transit_dist_nm"] for r in station_timeline])

    # Map operation types to integer categories
    op_types = sorted(list(set(r["operation_type"] for r in station_timeline)))
    op_type_map = {name: i for i, name in enumerate(op_types)}
    op_category_index = np.array(
        [op_type_map[r["operation_type"]] for r in station_timeline]
    )

    # --- 2. Write NetCDF File ---

    with nc.Dataset(output_path, "w", format="NETCDF4") as ds:
        # --- Dimensions ---
        ds.createDimension("station", len(station_timeline))

        # --- Global Attributes (Metadata) ---
        ds.title = config.cruise_name
        ds.vessel_speed_kt = config.default_vessel_speed
        ds.total_duration_days = (
            station_timeline[-1]["end_time"] - station_timeline[0]["start_time"]
        ).total_seconds() / (24 * 3600)
        ds.creator_name = "cruiseplan v1.0.0"
        ds.date_created = datetime.now().isoformat()
        ds.Conventions = "CF-1.6"
        ds.geospatial_lat_max = max(r["lat"] for r in station_timeline)
        # Add all global attributes from the specification here...

        # --- Variables ---

        # Time
        time_var = ds.createVariable("time", "f8", ("station",))
        time_var[:] = time_seconds
        time_var.units = "seconds since 1970-01-01 00:00:00"
        time_var.long_name = "Time of operation start"

        # Position (CF Standard)
        lon_var = ds.createVariable("longitude", "f4", ("station",))
        lon_var[:] = np.array([r["lon"] for r in station_timeline])
        lon_var.units = "degrees_east"

        lat_var = ds.createVariable("latitude", "f4", ("station",))
        lat_var[:] = np.array([r["lat"] for r in station_timeline])
        lat_var.units = "degrees_north"

        # Depth
        depth_var = ds.createVariable("depth", "f4", ("station",))
        depth_var[:] = np.array([r["depth"] for r in station_timeline])
        depth_var.units = "m"
        depth_var.standard_name = "sea_floor_depth_below_sea_surface"

        # Duration
        duration_var = ds.createVariable("duration_minutes", "f4", ("station",))
        duration_var[:] = np.array([r["duration_minutes"] for r in station_timeline])
        duration_var.units = "minutes"
        duration_var.long_name = "Duration of station operation"

        # Cumulative Distance
        dist_var = ds.createVariable("distance_from_start", "f4", ("station",))
        dist_var[:] = cumulative_distance
        dist_var.units = "nautical_miles"
        dist_var.long_name = "Cumulative distance from cruise start"

        # Operation Type (Categorical Lookup)
        op_idx_var = ds.createVariable("operation_type_index", "i2", ("station",))
        op_idx_var[:] = op_category_index
        op_idx_var.long_name = "Index of operation type"

        # Lookup table for operation names (as string)
        op_name_var = ds.createVariable("operation_type_names", "S20", ("station",))
        op_name_var[:] = np.array(
            [r["operation_type"] for r in station_timeline], dtype="S20"
        )
        op_name_var.long_name = "Operation type names"

        logger.info(f"✅ NetCDF file successfully created at {output_path}")

    return output_path


def generate_csv_output(
    config: CruiseConfig,
    timeline: List[ActivityRecord],
    output_dir: Path,
    file_name: str = "cruise_schedule.csv",
) -> Path:
    """
    Generates the comprehensive operational CSV file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / file_name

    if not timeline:
        logger.warning("Timeline is empty; skipping CSV generation.")
        return output_path

    # Prepare data for DataFrame
    csv_data = []

    for i, rec in enumerate(timeline):

        # Format position string using the external utility function
        pos_str = "N/A"
        try:
            pos_str = format_position_string(rec["lat"], rec["lon"])
        except Exception:
            pass  # Keep N/A if conversion fails

        csv_data.append(
            {
                "Activity": rec["activity"],
                "Label (name)": rec["label"],
                "Location": pos_str,
                "Activity duration [h]": minutes_to_hours(rec["duration_minutes"]),
                "Depth [m]": f"{rec['depth']:.0f}",
                "Lat [deg]": rec["lat"],
                "Lon [deg]": rec["lon"],
                "Transit distance [nm]": f"{rec['transit_dist_nm']:.1f}",
                "Transit time [h]": f"{rec['transit_dist_nm'] / rec['vessel_speed_kt']:.1f}",
                "Vessel speed [kt]": rec["vessel_speed_kt"],
                "Start (date)": rec["start_time"].strftime("%Y-%m-%d"),
                "Start (time HH:MM:SS)": rec["start_time"].strftime("%H:%M:%S"),
                "End (date)": rec["end_time"].strftime("%Y-%m-%d"),
                "End (time HH:MM:SS)": rec["end_time"].strftime("%H:%M:%S"),
                "Leg": rec["leg_name"],
                "Notes": "",
                # Add other required fields from spec here...
            }
        )

    # Create and write DataFrame
    df = pd.DataFrame(csv_data)
    df.to_csv(output_path, index=False)

    logger.info(f"✅ CSV file successfully created at {output_path}")
    return output_path
