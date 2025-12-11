import logging
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from cruiseplan.utils.constants import (
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
)

logger = logging.getLogger(__name__)

# cruiseplan/core/validation.py


# --- Custom Exception ---
class CruiseConfigurationError(Exception):
    """Raised when cruise configuration is invalid or cannot be processed."""

    pass


# --- Enums ---
class StrategyEnum(str, Enum):
    SEQUENTIAL = "sequential"
    SPATIAL_INTERLEAVED = "spatial_interleaved"
    DAY_NIGHT_SPLIT = "day_night_split"


class OperationTypeEnum(str, Enum):
    CTD = "CTD"
    WATER_SAMPLING = "water_sampling"
    MOORING = "mooring"
    CALIBRATION = "calibration"


class ActionEnum(str, Enum):
    PROFILE = "profile"
    SAMPLING = "sampling"
    DEPLOYMENT = "deployment"
    RECOVERY = "recovery"
    CALIBRATION = "calibration"
    # Line operation actions
    ADCP = "ADCP"
    BATHYMETRY = "bathymetry"
    THERMOSALINOGRAPH = "thermosalinograph"
    TOW_YO = "tow_yo"
    SEISMIC = "seismic"
    MICROSTRUCTURE = "microstructure"


class LineOperationTypeEnum(str, Enum):
    UNDERWAY = "underway"
    TOWING = "towing"


# --- Shared Models ---


class GeoPoint(BaseModel):
    """
    Internal representation of a point.
    """

    latitude: float
    longitude: float

    @field_validator("latitude")
    def validate_lat(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError(f"Latitude {v} must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_lon(cls, v):
        # Individual point check: Must be valid in at least one system (-180..360 covers both)
        if not (-180 <= v <= 360):
            raise ValueError(f"Longitude {v} must be between -180 and 360")
        return v


class FlexibleLocationModel(BaseModel):
    """
    Base class that allows users to define location as either:
    1. position: "lat, lon" (Legacy/Fast)
    2. latitude: float, longitude: float (Explicit/Clear)
    """

    position: Optional[GeoPoint] = None  # Internal storage

    @model_validator(mode="before")
    @classmethod
    def unify_coordinates(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Case A: Explicit Lat/Lon
            if "latitude" in data and "longitude" in data:
                data["position"] = {
                    "latitude": data.pop("latitude"),
                    "longitude": data.pop("longitude"),
                }
            # Case B: String Position
            elif "position" in data and isinstance(data["position"], str):
                try:
                    lat, lon = map(float, data["position"].split(","))
                    data["position"] = {"latitude": lat, "longitude": lon}
                except ValueError:
                    raise ValueError(
                        f"Invalid position string: '{data['position']}'. Expected 'lat, lon'"
                    )
        return data


# --- Catalog Definitions ---


class PortDefinition(FlexibleLocationModel):
    name: str
    timezone: Optional[str] = "UTC"


class StationDefinition(FlexibleLocationModel):
    name: str
    operation_type: OperationTypeEnum
    action: ActionEnum
    depth: Optional[float] = None
    duration: Optional[float] = None
    comment: Optional[str] = None
    equipment: Optional[str] = None
    position_string: Optional[str] = None

    @field_validator("duration")
    def validate_duration_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v

    @model_validator(mode="after")
    def validate_action_matches_operation(self):
        """Ensure action is compatible with operation_type."""
        valid_combinations = {
            OperationTypeEnum.CTD: [ActionEnum.PROFILE],
            OperationTypeEnum.WATER_SAMPLING: [ActionEnum.SAMPLING],
            OperationTypeEnum.MOORING: [ActionEnum.DEPLOYMENT, ActionEnum.RECOVERY],
            OperationTypeEnum.CALIBRATION: [ActionEnum.CALIBRATION],
        }

        if self.operation_type in valid_combinations:
            if self.action not in valid_combinations[self.operation_type]:
                valid_actions = ", ".join(
                    [a.value for a in valid_combinations[self.operation_type]]
                )
                raise ValueError(
                    f"Operation type '{self.operation_type.value}' must use action: {valid_actions}. "
                    f"Got '{self.action.value}'"
                )

        return self


class TransitDefinition(BaseModel):
    name: str
    route: List[GeoPoint]
    comment: Optional[str] = None
    vessel_speed: Optional[float] = None
    # Optional fields for scientific transits
    operation_type: Optional[LineOperationTypeEnum] = None
    action: Optional[ActionEnum] = None

    @field_validator("route", mode="before")
    def parse_route_strings(cls, v):
        # Allow list of strings ["lat,lon", "lat,lon"]
        parsed = []
        for point in v:
            if isinstance(point, str):
                lat, lon = map(float, point.split(","))
                parsed.append({"latitude": lat, "longitude": lon})
            else:
                parsed.append(point)
        return parsed

    @model_validator(mode="after")
    def validate_scientific_transit_fields(self):
        """If operation_type is provided, action must also be provided and vice versa."""
        if (self.operation_type is None) != (self.action is None):
            raise ValueError(
                "Both operation_type and action must be provided together for scientific transits"
            )

        # If this is a scientific transit, validate action matches operation_type
        if self.operation_type is not None and self.action is not None:
            valid_combinations = {
                LineOperationTypeEnum.UNDERWAY: [
                    ActionEnum.ADCP,
                    ActionEnum.BATHYMETRY,
                    ActionEnum.THERMOSALINOGRAPH,
                ],
                LineOperationTypeEnum.TOWING: [
                    ActionEnum.TOW_YO,
                    ActionEnum.SEISMIC,
                    ActionEnum.MICROSTRUCTURE,
                ],
            }

            if self.operation_type in valid_combinations:
                if self.action not in valid_combinations[self.operation_type]:
                    valid_actions = ", ".join(
                        [a.value for a in valid_combinations[self.operation_type]]
                    )
                    raise ValueError(
                        f"Operation type '{self.operation_type.value}' must use action: {valid_actions}. "
                        f"Got '{self.action.value}'"
                    )

        return self


# --- Schedule Definitions ---


class GenerateTransect(BaseModel):
    start: GeoPoint
    end: GeoPoint
    spacing: float
    id_pattern: str
    start_index: int = 1
    reversible: bool = True

    @model_validator(mode="before")
    @classmethod
    def parse_endpoints(cls, data):
        # Helper to parse start/end strings
        for field in ["start", "end"]:
            if field in data and isinstance(data[field], str):
                lat, lon = map(float, data[field].split(","))
                data[field] = {"latitude": lat, "longitude": lon}
        return data


class SectionDefinition(BaseModel):
    name: str
    start: GeoPoint
    end: GeoPoint
    distance_between_stations: Optional[float] = None
    reversible: bool = True
    stations: Optional[List[str]] = []

    @model_validator(mode="before")
    @classmethod
    def parse_endpoints(cls, data):
        for field in ["start", "end"]:
            if field in data and isinstance(data[field], str):
                lat, lon = map(float, data[field].split(","))
                data[field] = {"latitude": lat, "longitude": lon}
        return data


class ClusterDefinition(BaseModel):
    name: str
    strategy: StrategyEnum = StrategyEnum.SEQUENTIAL
    ordered: bool = True
    sequence: Optional[List[Union[str, StationDefinition, TransitDefinition]]] = None
    stations: Optional[List[Union[str, StationDefinition]]] = []
    generate_transect: Optional[GenerateTransect] = None
    activities: Optional[List[dict]] = []


class LegDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    strategy: Optional[StrategyEnum] = None
    ordered: Optional[bool] = None
    stations: Optional[List[Union[str, StationDefinition]]] = []
    clusters: Optional[List[ClusterDefinition]] = []
    sections: Optional[List[SectionDefinition]] = []
    sequence: Optional[List[Union[str, StationDefinition]]] = []


# --- Root Config ---


class CruiseConfig(BaseModel):
    cruise_name: str
    description: Optional[str] = None

    # --- LOGIC CONSTRAINTS ---
    default_vessel_speed: float
    default_distance_between_stations: float = DEFAULT_STATION_SPACING_KM
    turnaround_time: float = DEFAULT_TURNAROUND_TIME_MIN
    ctd_descent_rate: float = 1.0
    ctd_ascent_rate: float = 1.0

    # Configuration "daylight" or "dayshift" window for moorings
    day_start_hour: int = 8  # Default 08:00
    day_end_hour: int = 20  # Default 20:00

    calculate_transfer_between_sections: bool
    calculate_depth_via_bathymetry: bool
    start_date: str = DEFAULT_START_DATE
    start_time: Optional[str] = "08:00"
    station_label_format: str = "C{:03d}"
    mooring_label_format: str = "M{:02d}"

    departure_port: PortDefinition
    arrival_port: PortDefinition
    first_station: str
    last_station: str

    stations: Optional[List[StationDefinition]] = []
    transits: Optional[List[TransitDefinition]] = []
    legs: List[LegDefinition]

    model_config = ConfigDict(extra="forbid")

    # --- VALIDATORS ---

    @field_validator("default_vessel_speed")
    def validate_speed(cls, v):
        if v <= 0:
            raise ValueError("Vessel speed must be positive")
        if v > 20:
            raise ValueError(
                f"Vessel speed {v} knots is unrealistic (> 20). Raise an Error."
            )
        if v < 1:
            warnings.warn(f"Vessel speed {v} knots is unusually low (< 1).")
        return v

    @field_validator("default_distance_between_stations")
    def validate_distance(cls, v):
        if v <= 0:
            raise ValueError("Distance must be positive")
        if v > 150:
            raise ValueError(
                f"Station spacing {v} km is too large (> 150). Raise an Error."
            )
        if v < 4 or v > 50:
            warnings.warn(f"Station spacing {v} km is outside typical range (4-50 km).")
        return v

    @field_validator("turnaround_time")
    def validate_turnaround(cls, v):
        if v < 0:
            raise ValueError("Turnaround time cannot be negative")
        if v > 60:
            warnings.warn(
                f"Turnaround time {v} minutes is high (> 60). Ensure units are minutes."
            )
        return v

    @field_validator("ctd_descent_rate", "ctd_ascent_rate")
    def validate_ctd_rates(cls, v):
        if not (0.5 <= v <= 2.0):
            raise ValueError(f"CTD Rate {v} m/s is outside safe limits (0.5 - 2.0).")
        return v

    @field_validator("day_start_hour", "day_end_hour")
    def validate_hours(cls, v):
        if not (0 <= v <= 23):
            raise ValueError("Hour must be between 0 and 23")
        return v

    @model_validator(mode="after")
    def validate_day_window(self):
        if self.day_start_hour >= self.day_end_hour:
            raise ValueError(
                f"Day start ({self.day_start_hour}) must be before day end ({self.day_end_hour})"
            )
        return self

    @model_validator(mode="after")
    def check_longitude_consistency(self):
        """
        Ensures the entire cruise uses EITHER [-180, 180] OR [0, 360], but not both.
        Example: Cannot have one point at -5 (355) and another at 355 (355) if inputs differ.
        """
        lons = []

        # 1. Collect from Global Anchors
        if self.departure_port:
            lons.append(self.departure_port.position.longitude)
        if self.arrival_port:
            lons.append(self.arrival_port.position.longitude)

        # 2. Collect from Catalog
        if self.stations:
            lons.extend([s.position.longitude for s in self.stations])
        if self.transits:
            for t in self.transits:
                lons.extend([p.longitude for p in t.route])

        # 3. Collect from Legs (Inline Definitions)
        for leg in self.legs:
            # Helper to extract GeoPoint from various inline objects
            def extract_from_list(items):
                if not items:
                    return
                for item in items:
                    if hasattr(item, "position") and isinstance(
                        item.position, GeoPoint
                    ):
                        lons.append(item.position.longitude)
                    elif hasattr(item, "start") and isinstance(item.start, GeoPoint):
                        # Sections / Generators
                        lons.append(item.start.longitude)
                        if hasattr(item, "end") and isinstance(item.end, GeoPoint):
                            lons.append(item.end.longitude)

            extract_from_list(leg.stations)
            extract_from_list(leg.sections)

            if leg.clusters:
                for cluster in leg.clusters:
                    extract_from_list(cluster.stations)
                    if cluster.generate_transect:
                        lons.append(cluster.generate_transect.start.longitude)
                        lons.append(cluster.generate_transect.end.longitude)

        # 4. Perform the Logic Check
        if not lons:
            return self

        is_system_standard = all(-180 <= x <= 180 for x in lons)
        is_system_positive = all(0 <= x <= 360 for x in lons)

        if not (is_system_standard or is_system_positive):
            # Find the culprits for a helpful error message
            min_lon = min(lons)
            max_lon = max(lons)
            raise ValueError(
                f"Inconsistent Longitude Systems detected across the cruise.\n"
                f"Found values ranging from {min_lon} to {max_lon}.\n"
                f"You must use EITHER [-180, 180] OR [0, 360] consistently, but not both.\n"
                f"(Example: Do not mix -5.0 and 355.0 in the same file)"
            )

        return self


# ===== Configuration Enrichment and Validation Functions =====


def enrich_configuration(
    config_path: Path,
    add_depths: bool = False,
    add_coords: bool = False,
    bathymetry_source: str = "etopo2022",
    coord_format: str = "dmm",
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Add missing data to cruise configuration.

    Args:
        config_path: Path to input YAML configuration
        add_depths: Whether to add missing depth values
        add_coords: Whether to add formatted coordinate fields
        bathymetry_source: Bathymetry dataset to use
        coord_format: Coordinate format ("dmm" or "dms")
        output_path: Path for output file (if None, modifies in place)

    Returns
    -------
        Dictionary with enrichment summary
    """
    from cruiseplan.cli.utils import save_yaml_config
    from cruiseplan.core.cruise import Cruise
    from cruiseplan.data.bathymetry import BathymetryManager
    from cruiseplan.utils.coordinates import format_dmm_comment

    # Load cruise configuration
    cruise = Cruise(config_path)

    enrichment_summary = {
        "stations_with_depths_added": 0,
        "stations_with_coords_added": 0,
        "total_stations_processed": len(cruise.station_registry),
    }

    # Initialize managers if needed
    if add_depths:
        bathymetry = BathymetryManager(source=bathymetry_source, data_dir="data")

    # Track which stations had depths added for accurate YAML updating
    stations_with_depths_added = set()

    # Process each station
    for station_name, station in cruise.station_registry.items():
        # Add depths if requested
        if add_depths and (not hasattr(station, "depth") or station.depth is None):
            depth = bathymetry.get_depth_at_point(
                station.position.latitude, station.position.longitude
            )
            if depth is not None and depth != 0:
                station.depth = abs(depth)
                enrichment_summary["stations_with_depths_added"] += 1
                stations_with_depths_added.add(station_name)
                logger.debug(
                    f"Added depth {station.depth:.0f}m to station {station_name}"
                )

    # Update YAML configuration with any changes
    config_dict = cruise.raw_data.copy()
    coord_changes_made = 0

    # Process coordinate additions and other changes
    if "stations" in config_dict:
        for station_data in config_dict["stations"]:
            station_name = station_data["name"]
            if station_name in cruise.station_registry:
                station_obj = cruise.station_registry[station_name]

                # Update depth only if it was newly added by this function
                if station_name in stations_with_depths_added:
                    station_data["depth"] = float(station_obj.depth)

                # Add coordinate fields if requested
                if add_coords:
                    if coord_format == "dmm":
                        if (
                            "coordinates_dmm" not in station_data
                            or not station_data.get("coordinates_dmm")
                        ):
                            dmm_comment = format_dmm_comment(
                                station_obj.position.latitude,
                                station_obj.position.longitude,
                            )
                            station_data["coordinates_dmm"] = dmm_comment
                            coord_changes_made += 1
                            logger.debug(
                                f"Added DMM coordinates to station {station_name}: {dmm_comment}"
                            )
                    elif coord_format == "dms":
                        warnings.warn(
                            "DMS coordinate format is not yet supported. No coordinates were added for station "
                            f"{station_name}.",
                            UserWarning,
                        )
                    else:
                        warnings.warn(
                            f"Unknown coordinate format '{coord_format}' specified. No coordinates were added for station "
                            f"{station_name}.",
                            UserWarning,
                        )
    # Update the enrichment summary
    enrichment_summary["stations_with_coords_added"] = coord_changes_made
    total_enriched = (
        enrichment_summary["stations_with_depths_added"]
        + enrichment_summary["stations_with_coords_added"]
    )

    # Save enriched configuration if any changes were made
    if total_enriched > 0 and output_path:
        save_yaml_config(config_dict, output_path, backup=True)

    return enrichment_summary


def validate_configuration_file(
    config_path: Path,
    check_depths: bool = False,
    tolerance: float = 10.0,
    bathymetry_source: str = "etopo2022",
    strict: bool = False,
) -> Tuple[bool, List[str], List[str]]:
    """
    Comprehensive validation of YAML configuration file.

    Args:
        config_path: Path to input YAML configuration
        check_depths: Whether to validate depths against bathymetry
        tolerance: Depth difference tolerance percentage
        bathymetry_source: Bathymetry dataset to use
        strict: Whether to use strict validation mode

    Returns
    -------
        Tuple of (success, errors, warnings)
    """
    from pydantic import ValidationError

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.data.bathymetry import BathymetryManager

    errors = []
    warnings = []

    try:
        # Load and validate configuration
        cruise = Cruise(config_path)

        # Basic validation passed if we get here
        logger.debug("✓ YAML structure and schema validation passed")

        # Depth validation if requested
        if check_depths:
            bathymetry = BathymetryManager(source=bathymetry_source, data_dir="data")
            stations_checked, depth_warnings = validate_depth_accuracy(
                cruise, bathymetry, tolerance
            )
            warnings.extend(depth_warnings)
            logger.debug(f"Checked {stations_checked} stations for depth accuracy")

        # Additional validations can be added here

        success = len(errors) == 0
        return success, errors, warnings

    except ValidationError as e:
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            errors.append(f"Schema error at {location}: {message}")
        return False, errors, warnings

    except Exception as e:
        errors.append(f"Configuration loading error: {e}")
        return False, errors, warnings


def validate_depth_accuracy(
    cruise, bathymetry_manager, tolerance: float
) -> Tuple[int, List[str]]:
    """
    Compare station depths with bathymetry data.

    Args:
        cruise: Loaded cruise configuration
        bathymetry_manager: Bathymetry data manager
        tolerance: Tolerance percentage for depth differences

    Returns
    -------
        Tuple of (stations_checked, warning_messages)
    """
    stations_checked = 0
    warning_messages = []

    for station_name, station in cruise.station_registry.items():
        if hasattr(station, "depth") and station.depth is not None:
            stations_checked += 1

            # Get depth from bathymetry
            bathymetry_depth = bathymetry_manager.get_depth_at_point(
                station.position.latitude, station.position.longitude
            )

            if bathymetry_depth is not None and bathymetry_depth != 0:
                # Convert to positive depth value
                expected_depth = abs(bathymetry_depth)
                stated_depth = station.depth

                # Calculate percentage difference
                if expected_depth > 0:
                    diff_percent = (
                        abs(stated_depth - expected_depth) / expected_depth * 100
                    )

                    if diff_percent > tolerance:
                        warning_msg = (
                            f"Station {station_name}: depth discrepancy of "
                            f"{diff_percent:.1f}% (stated: {stated_depth:.0f}m, "
                            f"bathymetry: {expected_depth:.0f}m)"
                        )
                        warning_messages.append(warning_msg)
            else:
                warning_msg = f"Station {station_name}: could not verify depth (no bathymetry data)"
                warning_messages.append(warning_msg)

    return stations_checked, warning_messages
