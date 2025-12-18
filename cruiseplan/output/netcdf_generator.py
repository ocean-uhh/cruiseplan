"""
NetCDF Output Generation System (Phase 3c).

Generates CF-1.8 compliant NetCDF datasets for scientific data management and analysis.
Implements discrete sampling geometries as specified in netcdf_outputs.md.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np
import xarray as xr

from cruiseplan.calculators.scheduler import ActivityRecord
from cruiseplan.core.validation import CruiseConfig
from cruiseplan.output.netcdf_metadata import (
    create_coordinate_variables,
    create_global_attributes,
    create_operation_variables,
)

logger = logging.getLogger(__name__)


class NetCDFGenerator:
    """
    CF-1.8 compliant NetCDF generator using xarray.

    Generates CF-1.8 compliant NetCDF files organized by operation geometry type.
    Implements discrete sampling geometries for scientific data management and
    analysis as specified in the netcdf_outputs.md specification.

    Attributes
    ----------
    cf_conventions : str
        CF conventions version used for NetCDF files ("CF-1.8").
    """

    def __init__(self):
        self.cf_conventions = "CF-1.8"

    def generate_all_netcdf_outputs(
        self, config: CruiseConfig, timeline: List[ActivityRecord], output_dir: Path
    ) -> List[Path]:
        """
        Generate all NetCDF files according to netcdf_outputs.md specification.

        Uses master file approach: generate schedule.nc as master, then derive
        specialized files for different operation types. Implements CF-1.8
        compliant discrete sampling geometries.

        Parameters
        ----------
        config : CruiseConfig
            Cruise configuration object containing cruise metadata.
        timeline : list of ActivityRecord
            Timeline of scheduled activities from the scheduler.
        output_dir : Path
            Directory where NetCDF files will be written.

        Returns
        -------
        list of Path
            List of paths to all generated NetCDF files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)

        cruise_name = config.cruise_name.replace(" ", "_")
        generated_files = []

        # Step 1: Generate master schedule file (featureType: trajectory) with waterdepth
        schedule_file = output_dir / f"{cruise_name}_schedule.nc"
        self.generate_master_schedule(timeline, config, schedule_file)
        generated_files.append(schedule_file)

        # Step 2: Derive specialized files from master schedule
        # Generate points file (featureType: point)
        points_file = output_dir / f"{cruise_name}_points.nc"
        self.derive_point_operations(schedule_file, points_file, config)
        generated_files.append(points_file)

        # Generate lines file (featureType: trajectory)
        lines_file = output_dir / f"{cruise_name}_lines.nc"
        self.derive_line_operations(schedule_file, lines_file, config)
        generated_files.append(lines_file)

        # Generate areas file (placeholder)
        areas_file = output_dir / f"{cruise_name}_areas.nc"
        self.derive_area_operations(schedule_file, areas_file, config)
        generated_files.append(areas_file)

        logger.info(f"Generated {len(generated_files)} NetCDF files in {output_dir}")
        return generated_files

    def generate_point_operations(
        self, config: CruiseConfig, timeline: List[ActivityRecord], output_path: Path
    ) -> None:
        """
        Generate point operations NetCDF from stations and moorings.
        FeatureType: point (CF discrete sampling geometry)
        """
        logger.info(f"Generating point operations NetCDF: {output_path}")

        # Extract point operations from timeline (calculated durations) and match with station config
        point_operations = []

        # Create a lookup for station info
        station_lookup = {station.name: station for station in (config.stations or [])}

        # Get point operations from timeline
        for event in timeline:
            if event["activity"] in ["Station", "Mooring"]:
                station_name = event["label"]
                station = station_lookup.get(station_name)

                if station and hasattr(station, "position") and station.position:
                    # Map operation_type enum to string
                    operation_type = (
                        station.operation_type.value
                        if hasattr(station.operation_type, "value")
                        else str(station.operation_type)
                    )

                    # Map to CF-compliant operation names
                    operation_mapping = {
                        "CTD": "CTD_profile",
                        "water_sampling": "water_sampling",
                        "calibration": "calibration",
                        "mooring": f"Mooring_{getattr(station, 'action', 'operation').lower()}",
                    }
                    cf_operation = operation_mapping.get(operation_type, operation_type)

                    point_operations.append(
                        {
                            "name": station.name,
                            "latitude": station.latitude,
                            "longitude": station.longitude,
                            "waterdepth": getattr(station, "water_depth", None)
                            or getattr(station, "depth", 0.0)
                            or 0.0,
                            "operation_depth": getattr(
                                station, "operation_depth", None
                            ),
                            "category": "point_operation",
                            "type": cf_operation,
                            "action": getattr(station, "action", "unknown"),
                            "duration": event["duration_minutes"]
                            / 60.0,  # Convert calculated minutes to hours
                            "comment": getattr(station, "comment", ""),
                        }
                    )

        n_operations = len(point_operations)
        logger.info(f"Found {n_operations} point operations")

        if n_operations == 0:
            # Create empty dataset
            ds = xr.Dataset()
        else:
            # Create coordinate arrays
            lats = np.array(
                [op["latitude"] for op in point_operations], dtype=np.float32
            )
            lons = np.array(
                [op["longitude"] for op in point_operations], dtype=np.float32
            )
            depths = np.array(
                [op["waterdepth"] for op in point_operations], dtype=np.float32
            )
            operation_depths = np.array(
                [
                    (
                        op["operation_depth"]
                        if op["operation_depth"] is not None
                        else np.nan
                    )
                    for op in point_operations
                ],
                dtype=np.float32,
            )

            # Create data arrays
            names = [op["name"] for op in point_operations]
            categories = [op["category"] for op in point_operations]
            types = [op["type"] for op in point_operations]
            actions = [op["action"] for op in point_operations]
            durations = np.array(
                [op["duration"] for op in point_operations], dtype=np.float32
            )
            comments = [op["comment"] for op in point_operations]

            # Create coordinate variables using centralized metadata
            coord_vars = create_coordinate_variables(
                times=None,  # Point operations don't have time dimension
                lats=lats,
                lons=lons,
                depths=depths,
                operation_depths=operation_depths,
            )

            # Create operation variables using centralized metadata
            op_vars = create_operation_variables(
                names=names,
                types=types,
                actions=actions,
                durations=durations,
                comments=comments,
            )

            # Add category variable with specialized metadata
            category_attrs = {
                "long_name": "operation category",
                "flag_values": "point_operation line_operation area_operation transit",
                "coordinates": "latitude longitude water_depth",
            }
            op_vars["category"] = (["obs"], categories, category_attrs)

            # Create xarray Dataset from standardized variables
            data_vars = {}
            data_vars.update(coord_vars)
            data_vars.update(op_vars)

            ds = xr.Dataset(data_vars)

        # Set global attributes using centralized metadata
        global_attrs = create_global_attributes(
            feature_type="point",
            config=config,
            title_template="Point Operations: {cruise_name}",
            source="YAML configuration file",
        )
        ds.attrs.update(global_attrs)

        # Write to NetCDF file
        ds.to_netcdf(output_path, format="NETCDF4")
        logger.info(f"Point operations NetCDF written to: {output_path}")

    def generate_master_schedule(
        self, timeline: List[ActivityRecord], config: CruiseConfig, output_path: Path
    ) -> None:
        """
        Generate master schedule NetCDF from timeline with waterdepth included for all operations.
        FeatureType: trajectory (ship's continuous path)
        This is the master file containing all data that other files derive from.
        """
        if not timeline:
            # Create empty dataset with proper structure for derive methods
            ds = xr.Dataset(
                {
                    "category": (["obs"], [], {"long_name": "operation category"}),
                }
            )
        else:
            n_events = len(timeline)

            # Create station lookup for depth information
            station_lookup = {
                station.name: station for station in (config.stations or [])
            }

            # Create a lookup for area definitions
            area_lookup = {area.name: area for area in (config.areas or [])}

            # Create a lookup for transit definitions with routes
            transit_lookup = {}
            if hasattr(config, "transits") and config.transits:
                for transit in config.transits:
                    if hasattr(transit, "route") and transit.route:
                        transit_lookup[transit.name] = transit

            # Extract timeline data
            times = []
            lats = []
            lons = []
            waterdepths = []  # New: waterdepth for all operations
            names = []
            categories = []
            types = []
            actions = []
            comments = []
            leg_names = []
            durations = []
            vessel_speeds = []
            operation_depths = []
            # Additional coordinates for line operations
            start_lats = []
            start_lons = []
            end_lats = []
            end_lons = []

            for event in timeline:
                # Convert time to days since epoch for CF compliance
                time_obj = event.get("time", datetime.now())
                if isinstance(time_obj, str):
                    time_obj = datetime.fromisoformat(time_obj.replace("Z", "+00:00"))

                # Handle timezone-aware datetime objects properly
                if time_obj.tzinfo is not None:
                    # Convert to UTC and then to naive datetime
                    time_obj = time_obj.astimezone(timezone.utc).replace(tzinfo=None)

                epoch_days = (time_obj - datetime(1970, 1, 1)).total_seconds() / 86400.0
                times.append(epoch_days)

                lats.append(event["lat"])
                lons.append(event["lon"])
                names.append(event["label"])
                leg_names.append(event.get("leg_name", ""))
                durations.append(event["duration_minutes"] / 60.0)  # Convert to hours
                vessel_speeds.append(
                    event.get("vessel_speed_kt", config.default_vessel_speed)
                )

                # Determine waterdepth and operation_depth: real depths for point operations, NaN for others
                activity = event["activity"]
                if activity in ["Station", "Mooring"]:
                    station_name = event["label"]
                    station = station_lookup.get(station_name)
                    water_depth = getattr(station, "water_depth", None) or getattr(
                        station, "depth", None
                    )
                    operation_depth = getattr(station, "operation_depth", None)

                    if station and water_depth is not None:
                        waterdepths.append(float(water_depth))
                    else:
                        waterdepths.append(np.nan)

                    if station and operation_depth is not None:
                        operation_depths.append(float(operation_depth))
                    else:
                        operation_depths.append(np.nan)
                else:
                    waterdepths.append(np.nan)
                    operation_depths.append(np.nan)

                # Map activity details to standardized fields
                if activity in ["Station", "Mooring"]:
                    categories.append("point_operation")

                    # Get operation_type and action from the station config
                    station_name = event["label"]
                    station = station_lookup.get(station_name)
                    if (
                        station
                        and hasattr(station, "operation_type")
                        and hasattr(station, "action")
                    ):
                        # Combine operation_type and action (e.g., 'CTD_profile', 'mooring_recovery')
                        operation_type = getattr(station, "operation_type", "unknown")
                        action = getattr(station, "action", "unknown")

                        # Convert enum objects to strings if necessary
                        if hasattr(operation_type, "value"):
                            operation_type = operation_type.value
                        if hasattr(action, "value"):
                            action = action.value

                        # Create type with proper capitalization (e.g., 'CTD_profile', 'Mooring_recovery')
                        # Special case for CTD which should be all caps
                        if operation_type.upper() == "CTD":
                            formatted_type = f"CTD_{action}"
                        else:
                            formatted_type = f"{operation_type.capitalize()}_{action}"
                        types.append(formatted_type)
                        actions.append(str(action))
                    else:
                        # Fallback to activity type
                        types.append(activity.lower())
                        actions.append(event.get("action", "unknown"))

                elif activity == "Area":
                    categories.append("area_operation")

                    # Get area details from config
                    area_name = event["label"]
                    area = area_lookup.get(area_name)
                    if (
                        area
                        and hasattr(area, "operation_type")
                        and hasattr(area, "action")
                    ):
                        operation_type = getattr(area, "operation_type", "survey")
                        action = getattr(area, "action", "unknown")

                        # Convert enum objects to strings if necessary
                        if hasattr(operation_type, "value"):
                            operation_type = operation_type.value
                        if hasattr(action, "value"):
                            action = action.value

                        formatted_type = f"{operation_type.capitalize()}_{action}"
                        types.append(formatted_type)
                        actions.append(action)
                    else:
                        types.append("Survey_unknown")
                        actions.append("unknown")
                elif activity == "Transit" and event.get("action"):
                    categories.append("line_operation")
                    types.append(event.get("operation_type", "underway"))
                    actions.append(event.get("action", "unknown"))
                elif activity == "Transit":
                    categories.append("transit")
                    types.append("navigation")
                    actions.append("transit")
                else:
                    categories.append("other")
                    types.append("unknown")
                    actions.append("unknown")

                # Add comment (lookup from config if available)
                comment = ""
                if activity in ["Station", "Mooring"]:
                    station_name = event["label"]
                    station = station_lookup.get(station_name)
                    if station and hasattr(station, "comment"):
                        comment = getattr(station, "comment", "")
                elif activity == "Area":
                    area_name = event["label"]
                    area = area_lookup.get(area_name)
                    if area and hasattr(area, "comment"):
                        comment = getattr(area, "comment", "")
                elif activity == "Transit":
                    transit_name = event["label"]
                    transit = transit_lookup.get(transit_name)
                    if transit and hasattr(transit, "comment"):
                        comment = getattr(transit, "comment", "")
                comments.append(comment if comment is not None else "")

                # Extract start/end coordinates for line operations
                if activity == "Transit" and event.get("action"):
                    # This is a line operation - use provided start coordinates
                    start_lats.append(event.get("start_lat", event["lat"]))
                    start_lons.append(event.get("start_lon", event["lon"]))
                    # For end coordinates, use route end point from transit definition if available
                    transit_name = event["label"]
                    transit_def = transit_lookup.get(transit_name)

                    if (
                        transit_def
                        and hasattr(transit_def, "route")
                        and len(transit_def.route) >= 2
                    ):
                        end_point = transit_def.route[-1]
                        end_lats.append(end_point.latitude)
                        end_lons.append(end_point.longitude)
                    else:
                        # Fallback: use event position as end point
                        end_lats.append(event["lat"])
                        end_lons.append(event["lon"])
                else:
                    # Not a line operation - fill with NaN
                    start_lats.append(np.nan)
                    start_lons.append(np.nan)
                    end_lats.append(np.nan)
                    end_lons.append(np.nan)

            # Convert to numpy arrays
            times = np.array(times, dtype=np.float64)
            lats = np.array(lats, dtype=np.float32)
            lons = np.array(lons, dtype=np.float32)
            waterdepths = np.array(waterdepths, dtype=np.float32)
            operation_depths = np.array(operation_depths, dtype=np.float32)
            durations = np.array(durations, dtype=np.float32)
            vessel_speeds = np.array(vessel_speeds, dtype=np.float32)
            # Convert start/end coordinates to numpy arrays
            start_lats = np.array(start_lats, dtype=np.float32)
            start_lons = np.array(start_lons, dtype=np.float32)
            end_lats = np.array(end_lats, dtype=np.float32)
            end_lons = np.array(end_lons, dtype=np.float32)

            # Create xarray Dataset
            ds = xr.Dataset(
                {
                    # CF coordinate variables
                    "time": (
                        ["obs"],
                        times,
                        {
                            "standard_name": "time",
                            "long_name": "time of ship position",
                            "units": "days since 1970-01-01 00:00:00",
                        },
                    ),
                    "longitude": (
                        ["obs"],
                        lons,
                        {
                            "standard_name": "longitude",
                            "long_name": "ship longitude",
                            "units": "degrees_east",
                        },
                    ),
                    "latitude": (
                        ["obs"],
                        lats,
                        {
                            "standard_name": "latitude",
                            "long_name": "ship latitude",
                            "units": "degrees_north",
                        },
                    ),
                    "waterdepth": (
                        ["obs"],
                        waterdepths,
                        {
                            "long_name": "water depth at operation location",
                            "standard_name": "sea_floor_depth_below_sea_surface",
                            "vocabulary": "http://vocab.nerc.ac.uk/collection/P07/current/CFV13N17/",
                            "units": "m",
                            "positive": "down",
                            "axis": "Z",
                            "_FillValue": -9999.0,
                            "comment": "Available for point operations only, NaN for transits and line operations",
                        },
                    ),
                    "operation_depth": (
                        ["obs"],
                        operation_depths,
                        {
                            "long_name": "target operation depth",
                            "standard_name": "depth",
                            "units": "m",
                            "positive": "down",
                            "axis": "Z",
                            "_FillValue": -9999.0,
                            "comment": "Target depth for operation (e.g., CTD cast depth), NaN if not specified",
                        },
                    ),
                    # Schedule metadata
                    "name": (
                        ["obs"],
                        names,
                        {
                            "long_name": "activity identifier",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "category": (
                        ["obs"],
                        categories,
                        {
                            "long_name": "activity category",
                            "flag_values": "point_operation line_operation area_operation transit",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "type": (
                        ["obs"],
                        types,
                        {
                            "long_name": "specific type of activity",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "action": (
                        ["obs"],
                        actions,
                        {
                            "long_name": "specific action or method",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "comment": (
                        ["obs"],
                        comments,
                        {
                            "long_name": "activity comments",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "leg_assignment": (
                        ["obs"],
                        leg_names,
                        {
                            "long_name": "cruise leg identifier",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "duration": (
                        ["obs"],
                        durations,
                        {
                            "long_name": "activity duration",
                            "units": "hour",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    "vessel_speed": (
                        ["obs"],
                        vessel_speeds,
                        {
                            "long_name": "vessel speed",
                            "units": "knots",
                            "coordinates": "time latitude longitude waterdepth",
                        },
                    ),
                    # Start/end coordinates for line operations (NaN for other activities)
                    "start_latitude": (
                        ["obs"],
                        start_lats,
                        {
                            "standard_name": "latitude",
                            "long_name": "line operation start latitude",
                            "units": "degrees_north",
                            "coordinates": "time latitude longitude",
                            "_FillValue": np.nan,
                        },
                    ),
                    "start_longitude": (
                        ["obs"],
                        start_lons,
                        {
                            "standard_name": "longitude",
                            "long_name": "line operation start longitude",
                            "units": "degrees_east",
                            "coordinates": "time latitude longitude",
                            "_FillValue": np.nan,
                        },
                    ),
                    "end_latitude": (
                        ["obs"],
                        end_lats,
                        {
                            "standard_name": "latitude",
                            "long_name": "line operation end latitude",
                            "units": "degrees_north",
                            "coordinates": "time latitude longitude",
                            "_FillValue": np.nan,
                        },
                    ),
                    "end_longitude": (
                        ["obs"],
                        end_lons,
                        {
                            "standard_name": "longitude",
                            "long_name": "line operation end longitude",
                            "units": "degrees_east",
                            "coordinates": "time latitude longitude",
                            "_FillValue": np.nan,
                        },
                    ),
                }
            )

        # Set global attributes
        if not timeline:
            total_duration_days = 0.0
        # Calculate total cruise duration in days, handling edge cases
        elif len(times) > 1:
            total_duration_days = max(0.0, times[-1] - times[0])
        else:
            total_duration_days = 0.0
        ds.attrs.update(
            {
                "featureType": "trajectory",
                "title": f"Ship Schedule: {config.cruise_name}",
                "institution": "Generated by CruisePlan software",
                "source": "Scheduler computation from YAML configuration",
                "Conventions": self.cf_conventions,
                "cruise_name": config.cruise_name,
                "total_duration_days": total_duration_days,
                "creation_date": datetime.now().replace(microsecond=0).isoformat(),
                "comment": "Master file containing all cruise data - specialized files derived from this",
            }
        )

        # Write to NetCDF file
        ds.to_netcdf(output_path, format="NETCDF4")

    def _create_empty_derived_dataset(
        self, operation_type: str, config: CruiseConfig, comment: str = None
    ) -> xr.Dataset:
        """Create an empty dataset with proper global attributes for derived files."""
        # Determine featureType based on operation type
        feature_type = "point" if operation_type == "point" else "trajectory"

        # Base attributes
        attrs = {
            "featureType": feature_type,
            "title": f"{operation_type.title()} Operations: {config.cruise_name}",
            "institution": "Generated by CruisePlan software",
            "source": "YAML configuration file",
            "Conventions": self.cf_conventions,
            "cruise_name": config.cruise_name,
            "creation_date": datetime.now().isoformat(),
            "coordinate_system": "WGS84",
            "comment": comment
            or f"No {operation_type} operations defined in cruise plan",
        }

        # Add depth_datum for point operations
        if operation_type == "point":
            attrs["depth_datum"] = "Mean Sea Level"

        # Create empty dataset with proper data variables that xarray can handle
        if operation_type == "point":
            # Point operations need obs dimension and basic variables
            ds = xr.Dataset(
                data_vars={
                    "category": (
                        ("obs",),
                        np.array([], dtype="<U1"),  # Empty string array
                        {"long_name": "activity category"},
                    ),
                    "longitude": (
                        ("obs",),
                        np.array([], dtype=np.float64),
                        {
                            "standard_name": "longitude",
                            "long_name": "longitude",
                            "units": "degrees_east",
                        },
                    ),
                    "latitude": (
                        ("obs",),
                        np.array([], dtype=np.float64),
                        {
                            "standard_name": "latitude",
                            "long_name": "latitude",
                            "units": "degrees_north",
                        },
                    ),
                    "waterdepth": (
                        ("obs",),
                        np.array([], dtype=np.float64),
                        {
                            "standard_name": "sea_floor_depth_below_sea_surface",
                            "units": "m",
                        },
                    ),
                },
                coords={"obs": ("obs", np.array([], dtype=np.int32))},
                attrs=attrs,
            )
        elif operation_type == "line":
            # Line operations need operations and endpoints dimensions
            ds = xr.Dataset(
                data_vars={
                    "category": (
                        ("operations",),
                        np.array([], dtype="<U1"),
                        {"long_name": "activity category"},
                    ),
                    "longitude": (
                        ("operations", "endpoints"),
                        np.empty((0, 2), dtype=np.float64),
                        {
                            "standard_name": "longitude",
                            "long_name": "longitude",
                            "units": "degrees_east",
                        },
                    ),
                    "latitude": (
                        ("operations", "endpoints"),
                        np.empty((0, 2), dtype=np.float64),
                        {
                            "standard_name": "latitude",
                            "long_name": "latitude",
                            "units": "degrees_north",
                        },
                    ),
                },
                coords={
                    "operations": ("operations", np.array([], dtype=np.int32)),
                    "endpoints": ("endpoints", ["start", "end"]),
                },
                attrs=attrs,
            )
        else:  # area operations
            ds = xr.Dataset(
                data_vars={
                    "category": (
                        ("obs",),
                        np.array([], dtype="<U1"),
                        {"long_name": "activity category"},
                    ),
                    "longitude": (
                        ("obs",),
                        np.array([], dtype=np.float64),
                        {
                            "standard_name": "longitude",
                            "long_name": "longitude",
                            "units": "degrees_east",
                        },
                    ),
                    "latitude": (
                        ("obs",),
                        np.array([], dtype=np.float64),
                        {
                            "standard_name": "latitude",
                            "long_name": "latitude",
                            "units": "degrees_north",
                        },
                    ),
                },
                coords={"obs": ("obs", np.array([], dtype=np.int32))},
                attrs=attrs,
            )

        return ds

    def derive_point_operations(
        self, schedule_file: Path, points_file: Path, config: CruiseConfig
    ) -> None:
        """
        Derive point operations file from master schedule.nc.
        Filters to include only point_operation categories.
        """
        # Read master schedule
        ds_master = xr.open_dataset(schedule_file)

        # Filter to point operations only
        if "category" not in ds_master.data_vars:
            point_mask = []
        else:
            point_mask = ds_master["category"] == "point_operation"

        if len(point_mask) == 0 or not point_mask.any():
            logger.warning("No point operations found in master schedule")
            # Create empty dataset with proper attributes
            ds_points = self._create_empty_derived_dataset("point", config)
        else:
            # Select point operations data
            ds_points = ds_master.sel(obs=point_mask)

            # Update metadata for point operations file
            ds_points.attrs.update(
                {
                    "featureType": "point",
                    "title": f"Point Operations: {config.cruise_name}",
                    "institution": "Generated by CruisePlan software",
                    "source": "YAML configuration file",
                    "Conventions": self.cf_conventions,
                    "cruise_name": config.cruise_name,
                    "creation_date": datetime.now().replace(microsecond=0).isoformat(),
                    "coordinate_system": "WGS84",
                    "depth_datum": "Mean Sea Level",
                }
            )

        # Write derived file
        ds_points.to_netcdf(points_file, format="NETCDF4")
        logger.info(f"Point operations NetCDF derived and written to: {points_file}")
        ds_master.close()
        ds_points.close()

    def derive_line_operations(
        self, schedule_file: Path, lines_file: Path, config: CruiseConfig
    ) -> None:
        """
        Derive line operations file from master schedule.nc.
        Filters to include only line_operation categories.
        """
        # Read master schedule
        ds_master = xr.open_dataset(schedule_file)

        # Filter to line operations only
        if "category" not in ds_master.data_vars:
            line_mask = []
        else:
            line_mask = ds_master["category"] == "line_operation"

        if len(line_mask) == 0 or not line_mask.any():
            logger.warning("No line operations found in master schedule")
            # Create empty dataset with proper attributes and dimensions for tests
            ds_lines = self._create_empty_derived_dataset("line", config)
        else:
            # Select line operations data
            ds_lines = ds_master.sel(obs=line_mask)

            # Rename 'obs' dimension to 'operations' for backward compatibility
            if "obs" in ds_lines.dims:
                ds_lines = ds_lines.rename({"obs": "operations"})

            # For line operations, extract start/end coordinates from master schedule
            n_operations = ds_lines.sizes["operations"]

            # Create endpoints dimension
            ds_lines = ds_lines.assign_coords(endpoints=("endpoints", ["start", "end"]))

            # Reshape coordinate variables for trajectory format
            if n_operations > 0:
                # Use the actual start/end coordinates stored in master schedule
                start_lats = ds_lines["start_latitude"].values
                start_lons = ds_lines["start_longitude"].values
                end_lats = ds_lines["end_latitude"].values
                end_lons = ds_lines["end_longitude"].values

                # Create 2D arrays: (operations, endpoints) using actual route coordinates
                lat_2d = np.column_stack([start_lats, end_lats])
                lon_2d = np.column_stack([start_lons, end_lons])

                ds_lines = ds_lines.assign(
                    {
                        "longitude": (("operations", "endpoints"), lon_2d),
                        "latitude": (("operations", "endpoints"), lat_2d),
                    }
                )

                # Remove the intermediate start/end coordinate variables as they're now in the 2D format
                ds_lines = ds_lines.drop_vars(
                    [
                        "start_latitude",
                        "start_longitude",
                        "end_latitude",
                        "end_longitude",
                    ]
                )

            # Update metadata for line operations file
            ds_lines.attrs.update(
                {
                    "featureType": "trajectory",
                    "title": f"Line Operations: {config.cruise_name}",
                    "institution": "Generated by CruisePlan software",
                    "source": "YAML configuration file",
                    "Conventions": self.cf_conventions,
                    "cruise_name": config.cruise_name,
                    "creation_date": datetime.now().replace(microsecond=0).isoformat(),
                    "coordinate_system": "WGS84",
                }
            )

            # Remove waterdepth variable for line operations (not applicable)
            if "waterdepth" in ds_lines.data_vars:
                ds_lines = ds_lines.drop_vars(["waterdepth"])
                # Update coordinates attributes to remove waterdepth reference
                for var_name in [
                    "name",
                    "category",
                    "type",
                    "action",
                    "comment",
                    "operation_file_ref",
                    "leg_assignment",
                    "duration",
                    "vessel_speed",
                ]:
                    if var_name in ds_lines.data_vars:
                        ds_lines[var_name].attrs[
                            "coordinates"
                        ] = "time latitude longitude"

        # Write derived file
        ds_lines.to_netcdf(lines_file, format="NETCDF4")
        logger.info(f"Line operations NetCDF derived and written to: {lines_file}")
        ds_master.close()
        ds_lines.close()

    def derive_area_operations(
        self, schedule_file: Path, areas_file: Path, config: CruiseConfig
    ) -> None:
        """
        Derive area operations file from master schedule.nc.
        Filters to include only area_operation categories.
        """
        # Read master schedule
        ds_master = xr.open_dataset(schedule_file)

        # Filter to area operations only
        area_mask = ds_master["category"] == "area_operation"
        if not area_mask.any():
            logger.warning("No area operations found in master schedule")
            # Create empty dataset with proper attributes
            ds_areas = self._create_empty_derived_dataset("area", config)
        else:
            # Select area operations data
            ds_areas = ds_master.sel(obs=area_mask)

            # Update metadata for area operations file
            ds_areas.attrs.update(
                {
                    "featureType": "trajectory",
                    "title": f"Area Operations: {config.cruise_name}",
                    "institution": "Generated by CruisePlan software",
                    "source": "YAML configuration file",
                    "Conventions": self.cf_conventions,
                    "cruise_name": config.cruise_name,
                    "creation_date": datetime.now().replace(microsecond=0).isoformat(),
                    "coordinate_system": "WGS84",
                }
            )

            # Remove waterdepth variable for area operations (not applicable)
            if "waterdepth" in ds_areas.data_vars:
                ds_areas = ds_areas.drop_vars(["waterdepth"])
                # Update coordinates attributes to remove waterdepth reference
                for var_name in [
                    "name",
                    "category",
                    "type",
                    "action",
                    "comment",
                    "operation_file_ref",
                    "leg_assignment",
                    "duration",
                    "vessel_speed",
                ]:
                    if var_name in ds_areas.data_vars:
                        ds_areas[var_name].attrs[
                            "coordinates"
                        ] = "time latitude longitude"

        # Write derived file
        ds_areas.to_netcdf(areas_file, format="NETCDF4")
        logger.info(f"Area operations NetCDF derived and written to: {areas_file}")
        ds_master.close()
        ds_areas.close()

    def generate_ship_schedule(
        self, timeline: List[ActivityRecord], config: CruiseConfig, output_path: Path
    ) -> None:
        """
        Generate ship schedule NetCDF from timeline.
        FeatureType: trajectory (ship's continuous path)
        """
        logger.info(f"Generating ship schedule NetCDF: {output_path}")

        if not timeline:
            # Create empty dataset
            ds = xr.Dataset()
        else:
            n_events = len(timeline)

            # Extract timeline data
            times = []
            lats = []
            lons = []
            names = []
            categories = []
            types = []
            actions = []
            comments = []
            leg_names = []
            durations = []
            vessel_speeds = []

            for event in timeline:
                # Convert time to days since epoch for CF compliance
                time_obj = event.get("time", datetime.now())
                if isinstance(time_obj, str):
                    time_obj = datetime.fromisoformat(time_obj.replace("Z", "+00:00"))

                # Handle timezone-aware datetime objects properly
                if time_obj.tzinfo is not None:
                    # Convert to UTC and then to naive datetime
                    time_obj = time_obj.astimezone(timezone.utc).replace(tzinfo=None)

                epoch_days = (time_obj - datetime(1970, 1, 1)).total_seconds() / 86400.0
                times.append(epoch_days)

                lats.append(event["lat"])
                lons.append(event["lon"])
                names.append(event["label"])
                leg_names.append(event.get("leg_name", ""))
                durations.append(event["duration_minutes"] / 60.0)  # Convert to hours
                vessel_speeds.append(
                    event.get("vessel_speed_kt", config.default_vessel_speed)
                )

                # Map activity details to standardized fields
                activity = event["activity"]
                if activity in ["Station", "Mooring"]:
                    categories.append("point_operation")
                    types.append(activity.lower())  # 'station' or 'mooring'
                    actions.append(event.get("action", "unknown"))
                elif activity == "Transit" and event.get("action"):
                    categories.append("line_operation")
                    types.append(event.get("operation_type", "underway"))
                    actions.append(event.get("action", "unknown"))
                elif activity == "Transit":
                    categories.append("transit")
                    types.append("navigation")
                    actions.append("transit")
                else:
                    categories.append("other")
                    types.append("unknown")
                    actions.append("unknown")

                # Add comment (placeholder - would need to lookup from config)
                comments.append("")

            # Convert to numpy arrays
            times = np.array(times, dtype=np.float64)
            lats = np.array(lats, dtype=np.float32)
            lons = np.array(lons, dtype=np.float32)
            durations = np.array(durations, dtype=np.float32)
            vessel_speeds = np.array(vessel_speeds, dtype=np.float32)

            # Create xarray Dataset
            ds = xr.Dataset(
                {
                    # CF coordinate variables
                    "time": (
                        ["obs"],
                        times,
                        {
                            "standard_name": "time",
                            "long_name": "time of ship position",
                            "units": "days since 1970-01-01 00:00:00",
                        },
                    ),
                    "longitude": (
                        ["obs"],
                        lons,
                        {
                            "standard_name": "longitude",
                            "long_name": "ship longitude",
                            "units": "degrees_east",
                        },
                    ),
                    "latitude": (
                        ["obs"],
                        lats,
                        {
                            "standard_name": "latitude",
                            "long_name": "ship latitude",
                            "units": "degrees_north",
                        },
                    ),
                    # Schedule metadata
                    "name": (
                        ["obs"],
                        names,
                        {
                            "long_name": "activity identifier",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "category": (
                        ["obs"],
                        categories,
                        {
                            "long_name": "activity category",
                            "flag_values": "point_operation line_operation area_operation transit",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "type": (
                        ["obs"],
                        types,
                        {
                            "long_name": "specific type of activity",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "action": (
                        ["obs"],
                        actions,
                        {
                            "long_name": "specific action or method",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "comment": (
                        ["obs"],
                        comments,
                        {
                            "long_name": "activity comments",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "leg_assignment": (
                        ["obs"],
                        leg_names,
                        {
                            "long_name": "cruise leg identifier",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "duration": (
                        ["obs"],
                        durations,
                        {
                            "long_name": "activity duration",
                            "units": "hour",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                    "vessel_speed": (
                        ["obs"],
                        vessel_speeds,
                        {
                            "long_name": "vessel speed",
                            "units": "knots",
                            "coordinates": "time latitude longitude",
                        },
                    ),
                }
            )

        # Set global attributes
        if not timeline:
            total_duration_days = 0.0
        # Calculate total cruise duration in days, handling edge cases
        elif len(times) > 1:
            total_duration_days = max(0.0, times[-1] - times[0])
        else:
            total_duration_days = 0.0
        ds.attrs.update(
            {
                "featureType": "trajectory",
                "title": f"Ship Schedule: {config.cruise_name}",
                "institution": "Generated by CruisePlan software",
                "source": "Scheduler computation from YAML configuration",
                "Conventions": self.cf_conventions,
                "cruise_name": config.cruise_name,
                "total_duration_days": total_duration_days,
                "creation_date": datetime.now().replace(microsecond=0).isoformat(),
            }
        )

        # Write to NetCDF file
        ds.to_netcdf(output_path, format="NETCDF4")
        logger.info(f"Ship schedule NetCDF written to: {output_path}")

    def generate_line_operations(
        self, config: CruiseConfig, timeline: List[ActivityRecord], output_path: Path
    ) -> None:
        """
        Generate line operations NetCDF from scientific transits.
        FeatureType: trajectory (start/end points defining survey lines)
        """
        logger.info(f"Generating line operations NetCDF: {output_path}")

        # Create a lookup for transit definitions with routes
        transit_lookup = {}
        if hasattr(config, "transits") and config.transits:
            for transit in config.transits:
                if hasattr(transit, "route") and transit.route:
                    transit_lookup[transit.name] = transit

        # Extract line operations from timeline (scientific transits)
        line_operations = []
        for event in timeline:
            if event["activity"] == "Transit" and event.get("action"):
                # This is a scientific transit with action (ADCP, bathymetry, etc.)
                transit_name = event["label"]
                transit_def = transit_lookup.get(transit_name)

                if transit_def and len(transit_def.route) >= 2:
                    # Use actual route start and end points from YAML
                    start_point = transit_def.route[0]
                    end_point = transit_def.route[-1]

                    line_operations.append(
                        {
                            "name": event["label"],
                            "category": "line_operation",
                            "type": event.get("operation_type", "underway"),
                            "action": event.get("action", "unknown"),
                            "start_lat": start_point.latitude,
                            "start_lon": start_point.longitude,
                            "end_lat": end_point.latitude,
                            "end_lon": end_point.longitude,
                            "vessel_speed": event.get(
                                "vessel_speed_kt", config.default_vessel_speed
                            ),
                            "duration": event["duration_minutes"]
                            / 60.0,  # Convert to hours
                            "comment": getattr(transit_def, "comment", ""),
                        }
                    )
                else:
                    # Fallback: use event position with small offset (previous behavior)
                    start_lat = event["lat"]
                    start_lon = event["lon"]
                    operation_dist = event.get("operation_dist_nm", 10.0)
                    lat_offset = operation_dist / 60.0

                    line_operations.append(
                        {
                            "name": event["label"],
                            "category": "line_operation",
                            "type": event.get("operation_type", "underway"),
                            "action": event.get("action", "unknown"),
                            "start_lat": start_lat,
                            "start_lon": start_lon,
                            "end_lat": start_lat + lat_offset,
                            "end_lon": start_lon,
                            "vessel_speed": event.get(
                                "vessel_speed_kt", config.default_vessel_speed
                            ),
                            "duration": event["duration_minutes"]
                            / 60.0,  # Convert to hours
                            "comment": "",  # No comment available for fallback case
                        }
                    )

        n_operations = len(line_operations)
        logger.info(f"Found {n_operations} line operations")

        if n_operations == 0:
            # Create empty dataset
            ds = xr.Dataset()
        else:
            # Create coordinate arrays (2D: operations x endpoints)
            lons = np.zeros((n_operations, 2), dtype=np.float32)
            lats = np.zeros((n_operations, 2), dtype=np.float32)

            names = []
            categories = []
            types = []
            actions = []
            vessel_speeds = []
            durations = []
            comments = []

            for i, op in enumerate(line_operations):
                lons[i, 0] = op["start_lon"]  # Start point
                lons[i, 1] = op["end_lon"]  # End point
                lats[i, 0] = op["start_lat"]
                lats[i, 1] = op["end_lat"]

                names.append(op["name"])
                categories.append(op["category"])
                types.append(op["type"])
                actions.append(op["action"])
                vessel_speeds.append(op["vessel_speed"])
                durations.append(op["duration"])
                comments.append(op["comment"])

            vessel_speeds = np.array(vessel_speeds, dtype=np.float32)
            durations = np.array(durations, dtype=np.float32)

            # Create xarray Dataset
            ds = xr.Dataset(
                {
                    # Coordinate variables (2D arrays for start/end points)
                    "longitude": (
                        ["operations", "endpoints"],
                        lons,
                        {
                            "long_name": "longitude coordinates defining line operation",
                            "units": "degrees_east",
                            "comment": "endpoints dimension: 0=start point, 1=end point",
                        },
                    ),
                    "latitude": (
                        ["operations", "endpoints"],
                        lats,
                        {
                            "long_name": "latitude coordinates defining line operation",
                            "units": "degrees_north",
                            "comment": "endpoints dimension: 0=start point, 1=end point",
                        },
                    ),
                    # Operation metadata
                    "name": (
                        ["operations"],
                        names,
                        {"long_name": "operation identifier from cruise plan"},
                    ),
                    "category": (
                        ["operations"],
                        categories,
                        {
                            "long_name": "operation category",
                            "flag_values": "point_operation line_operation area_operation transit",
                        },
                    ),
                    "type": (
                        ["operations"],
                        types,
                        {
                            "long_name": "specific type of line operation",
                            "flag_values": "underway towing",
                            "flag_meanings": "underway_instruments towed_instruments",
                        },
                    ),
                    "action": (
                        ["operations"],
                        actions,
                        {
                            "long_name": "specific action or method from cruise plan",
                            "flag_values": "ADCP bathymetry thermosalinograph tow_yo seismic microstructure",
                        },
                    ),
                    "comment": (
                        ["operations"],
                        comments,
                        {"long_name": "operation comments from cruise plan"},
                    ),
                    "vessel_speed": (
                        ["operations"],
                        vessel_speeds,
                        {
                            "long_name": "planned vessel speed for operation",
                            "units": "knots",
                            "_FillValue": np.nan,
                        },
                    ),
                    "duration": (
                        ["operations"],
                        durations,
                        {
                            "long_name": "planned operation duration",
                            "units": "hour",
                            "_FillValue": np.nan,
                        },
                    ),
                }
            )

        # Set global attributes
        ds.attrs.update(
            {
                "featureType": "trajectory",
                "title": f"Line Operations: {config.cruise_name}",
                "institution": "Generated by CruisePlan software",
                "source": "YAML configuration file",
                "Conventions": self.cf_conventions,
                "cruise_name": config.cruise_name,
                "creation_date": datetime.now().replace(microsecond=0).isoformat(),
            }
        )

        # Write to NetCDF file
        ds.to_netcdf(output_path, format="NETCDF4")
        logger.info(f"Line operations NetCDF written to: {output_path}")

    def generate_area_operations(self, config: CruiseConfig, output_path: Path) -> None:
        """
        Generate area operations NetCDF (placeholder for future implementation).
        FeatureType: trajectory (coverage patterns)
        """
        logger.info(f"Generating area operations NetCDF (placeholder): {output_path}")

        # Create empty dataset as placeholder
        ds = xr.Dataset()

        # Set global attributes
        ds.attrs.update(
            {
                "featureType": "trajectory",
                "title": f"Area Operations: {config.cruise_name}",
                "institution": "Generated by CruisePlan software",
                "source": "YAML configuration file",
                "Conventions": self.cf_conventions,
                "cruise_name": config.cruise_name,
                "creation_date": datetime.now().replace(microsecond=0).isoformat(),
            }
        )

        # Write to NetCDF file
        ds.to_netcdf(output_path, format="NETCDF4")
        logger.info(f"Area operations NetCDF (placeholder) written to: {output_path}")


# Convenience function for external use
def generate_netcdf_outputs(
    config: CruiseConfig, timeline: List[ActivityRecord], output_dir: Path
) -> List[Path]:
    """
    Convenience function to generate all NetCDF outputs.

    Args:
        config: Cruise configuration
        timeline: Generated timeline from scheduler
        output_dir: Directory to write NetCDF files (defaults to tests_output/netcdf for tests)

    Returns
    -------
        List of generated NetCDF file paths
    """
    # Default output directory for tests - only redirect if directory name is exactly "tmp"
    if output_dir.name == "tmp":
        # This is likely a test temporary directory, redirect to tests_output
        output_dir = Path("tests_output/netcdf")

    generator = NetCDFGenerator()
    return generator.generate_all_netcdf_outputs(config, timeline, output_dir)
