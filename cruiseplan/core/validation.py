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
    """
    Exception raised when cruise configuration is invalid or cannot be processed.

    This exception is raised during configuration validation when the YAML
    file contains invalid data, missing required fields, or logical inconsistencies
    that prevent the cruise plan from being properly loaded.
    """

    pass


# --- Enums ---
class StrategyEnum(str, Enum):
    """
    Enumeration of scheduling strategies for cruise operations.

    Defines how operations within a cluster or composite should be executed.
    """

    SEQUENTIAL = "sequential"
    SPATIAL_INTERLEAVED = "spatial_interleaved"
    DAY_NIGHT_SPLIT = "day_night_split"


class OperationTypeEnum(str, Enum):
    """
    Enumeration of point operation types.

    Defines the type of scientific operation to be performed at a station.
    """

    CTD = "CTD"
    WATER_SAMPLING = "water_sampling"
    MOORING = "mooring"
    CALIBRATION = "calibration"


class ActionEnum(str, Enum):
    """
    Enumeration of specific actions for operations.

    Defines the specific scientific action to be taken for each operation type.
    """

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
    """
    Enumeration of line operation types.

    Defines the type of operation performed along a route or transect.
    """

    UNDERWAY = "underway"
    TOWING = "towing"


class AreaOperationTypeEnum(str, Enum):
    """
    Enumeration of area operation types.

    Defines operations that cover defined geographic areas.
    """

    SURVEY = "survey"


# --- Shared Models ---


class GeoPoint(BaseModel):
    """
    Internal representation of a geographic point.

    Represents a latitude/longitude coordinate pair with validation.

    Attributes
    ----------
    latitude : float
        Latitude in decimal degrees (-90 to 90).
    longitude : float
        Longitude in decimal degrees (-180 to 360).
    """

    latitude: float
    longitude: float

    @field_validator("latitude")
    def validate_lat(cls, v):
        """
        Validate latitude is within valid range.

        Parameters
        ----------
        v : float
            Latitude value to validate.

        Returns
        -------
        float
            Validated latitude value.

        Raises
        ------
        ValueError
            If latitude is outside -90 to 90 degrees.
        """
        if not (-90 <= v <= 90):
            raise ValueError(f"Latitude {v} must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_lon(cls, v):
        """
        Validate longitude is within valid range.

        Parameters
        ----------
        v : float
            Longitude value to validate.

        Returns
        -------
        float
            Validated longitude value.

        Raises
        ------
        ValueError
            If longitude is outside -180 to 360 degrees.
        """
        # Individual point check: Must be valid in at least one system (-180..360 covers both)
        if not (-180 <= v <= 360):
            raise ValueError(f"Longitude {v} must be between -180 and 360")
        return v


class FlexibleLocationModel(BaseModel):
    """
    Base class that allows users to define location in multiple formats.

    Supports both explicit latitude/longitude fields and string position format
    ("lat, lon") for backward compatibility.

    Attributes
    ----------
    position : Optional[GeoPoint]
        Internal storage of the geographic position.
    """

    position: Optional[GeoPoint] = None  # Internal storage

    @model_validator(mode="before")
    @classmethod
    def unify_coordinates(cls, data: Any) -> Any:
        """
        Unify different coordinate input formats into a single GeoPoint.

        Handles both explicit lat/lon fields and string position format.

        Parameters
        ----------
        data : Any
            Input data dictionary to process.

        Returns
        -------
        Any
            Processed data with unified position field.

        Raises
        ------
        ValueError
            If position string cannot be parsed as "lat, lon".
        """
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
    """
    Definition of a port location for cruise departure/arrival.

    Attributes
    ----------
    name : str
        Name of the port.
    timezone : Optional[str]
        Timezone identifier (default: "UTC").
    """

    name: str
    timezone: Optional[str] = "UTC"


class StationDefinition(FlexibleLocationModel):
    """
    Definition of a station location with operation details.

    Represents a specific geographic point where scientific operations
    will be performed.

    Attributes
    ----------
    name : str
        Unique identifier for the station.
    operation_type : OperationTypeEnum
        Type of scientific operation to perform.
    action : ActionEnum
        Specific action for the operation.
    depth : Optional[float]
        Water depth at the station in meters.
    duration : Optional[float]
        Manual duration override in minutes.
    comment : Optional[str]
        Human-readable comment or description.
    equipment : Optional[str]
        Equipment required for the operation.
    position_string : Optional[str]
        Original position string for reference.
    """

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
        """
        Validate that duration is positive.

        Parameters
        ----------
        v : Optional[float]
            Duration value to validate.

        Returns
        -------
        Optional[float]
            Validated duration value.

        Raises
        ------
        ValueError
            If duration is not positive.
        """
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v

    @model_validator(mode="after")
    def validate_action_matches_operation(self):
        """
        Validate that action is compatible with operation_type.

        Returns
        -------
        StationDefinition
            Self for chaining.

        Raises
        ------
        ValueError
            If action is not compatible with operation_type.
        """
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
    """
    Definition of a transit route between locations.

    Represents a planned movement between geographic points, which may be
    navigational or include scientific operations.

    Attributes
    ----------
    name : str
        Unique identifier for the transit.
    route : List[GeoPoint]
        List of waypoints defining the transit route.
    comment : Optional[str]
        Human-readable comment or description.
    vessel_speed : Optional[float]
        Speed for this transit in knots.
    operation_type : Optional[LineOperationTypeEnum]
        Type of operation if this is a scientific transit.
    action : Optional[ActionEnum]
        Specific action for scientific transits.
    """

    name: str
    route: List[GeoPoint]
    comment: Optional[str] = None
    vessel_speed: Optional[float] = None
    # Optional fields for scientific transits
    operation_type: Optional[LineOperationTypeEnum] = None
    action: Optional[ActionEnum] = None

    @field_validator("route", mode="before")
    def parse_route_strings(cls, v):
        """
        Parse route strings into GeoPoint objects.

        Parameters
        ----------
        v : List[Union[str, dict]]
            List of route points as strings or dictionaries.

        Returns
        -------
        List[dict]
            List of parsed route points.
        """
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
        """
        Validate scientific transit field combinations.

        Returns
        -------
        TransitDefinition
            Self for chaining.

        Raises
        ------
        ValueError
            If operation_type and action are not provided together.
        """
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
    """
    Parameters for generating a transect of stations.

    Defines how to create a series of stations along a line between two points.

    Attributes
    ----------
    start : GeoPoint
        Starting point of the transect.
    end : GeoPoint
        Ending point of the transect.
    spacing : float
        Distance between stations in kilometers.
    id_pattern : str
        Pattern for generating station IDs.
    start_index : int
        Starting index for station numbering (default: 1).
    reversible : bool
        Whether the transect can be traversed in reverse (default: True).
    """

    start: GeoPoint
    end: GeoPoint
    spacing: float
    id_pattern: str
    start_index: int = 1
    reversible: bool = True

    @model_validator(mode="before")
    @classmethod
    def parse_endpoints(cls, data):
        """
        Parse endpoint strings into GeoPoint objects.

        Parameters
        ----------
        data : dict
            Input data dictionary.

        Returns
        -------
        dict
            Processed data with parsed endpoints.
        """
        # Helper to parse start/end strings
        for field in ["start", "end"]:
            if field in data and isinstance(data[field], str):
                lat, lon = map(float, data[field].split(","))
                data[field] = {"latitude": lat, "longitude": lon}
        return data


class SectionDefinition(BaseModel):
    """
    Definition of a section with start/end points.

    Represents a geographic section along which stations may be placed.

    Attributes
    ----------
    name : str
        Unique identifier for the section.
    start : GeoPoint
        Starting point of the section.
    end : GeoPoint
        Ending point of the section.
    distance_between_stations : Optional[float]
        Spacing between stations in kilometers.
    reversible : bool
        Whether the section can be traversed in reverse (default: True).
    stations : Optional[List[str]]
        List of station names in this section.
    """

    name: str
    start: GeoPoint
    end: GeoPoint
    distance_between_stations: Optional[float] = None
    reversible: bool = True
    stations: Optional[List[str]] = []

    @model_validator(mode="before")
    @classmethod
    def parse_endpoints(cls, data):
        """
        Parse endpoint strings into GeoPoint objects.

        Parameters
        ----------
        data : dict
            Input data dictionary.

        Returns
        -------
        dict
            Processed data with parsed endpoints.
        """
        for field in ["start", "end"]:
            if field in data and isinstance(data[field], str):
                lat, lon = map(float, data[field].split(","))
                data[field] = {"latitude": lat, "longitude": lon}
        return data


class AreaDefinition(BaseModel):
    """
    Definition of an area for survey operations.

    Represents a polygonal region for area-based scientific operations.

    Attributes
    ----------
    name : str
        Unique identifier for the area.
    corners : List[GeoPoint]
        List of corner points defining the area boundary.
    comment : Optional[str]
        Human-readable comment or description.
    operation_type : Optional[str]
        Type of operation for the area (default: "survey").
    action : Optional[ActionEnum]
        Specific action for the area operation.
    duration : Optional[float]
        Duration for the area operation in minutes.
    """

    name: str
    corners: List[GeoPoint]
    comment: Optional[str] = None
    operation_type: Optional[str] = "survey"
    action: Optional[ActionEnum] = None
    duration: Optional[float] = None  # Duration in minutes


class ClusterDefinition(BaseModel):
    """
    Definition of a cluster of related operations.

    Groups operations that should be scheduled together with specific strategies.

    Attributes
    ----------
    name : str
        Unique identifier for the cluster.
    strategy : StrategyEnum
        Scheduling strategy for the cluster (default: SEQUENTIAL).
    ordered : bool
        Whether operations should maintain their order (default: True).
    sequence : Optional[List[Union[str, StationDefinition, TransitDefinition]]]
        Ordered sequence of operations.
    stations : Optional[List[Union[str, StationDefinition]]]
        List of stations in the cluster.
    generate_transect : Optional[GenerateTransect]
        Parameters for generating a transect of stations.
    activities : Optional[List[dict]]
        List of activity definitions.
    """

    name: str
    strategy: StrategyEnum = StrategyEnum.SEQUENTIAL
    ordered: bool = True
    sequence: Optional[List[Union[str, StationDefinition, TransitDefinition]]] = None
    stations: Optional[List[Union[str, StationDefinition]]] = []
    generate_transect: Optional[GenerateTransect] = None
    activities: Optional[List[dict]] = []


class LegDefinition(BaseModel):
    """
    Definition of a cruise leg containing operations and clusters.

    Represents a major phase or segment of the cruise with its own
    operations, clusters, and scheduling parameters.

    Attributes
    ----------
    name : str
        Unique identifier for the leg.
    description : Optional[str]
        Human-readable description of the leg.
    strategy : Optional[StrategyEnum]
        Default scheduling strategy for the leg.
    ordered : Optional[bool]
        Whether the leg operations should be ordered.
    stations : Optional[List[Union[str, StationDefinition]]]
        List of stations in the leg.
    clusters : Optional[List[ClusterDefinition]]
        List of operation clusters in the leg.
    sections : Optional[List[SectionDefinition]]
        List of sections in the leg.
    sequence : Optional[List[Union[str, StationDefinition]]]
        Ordered sequence of operations.
    """

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
    """
    Root configuration model for cruise planning.

    Contains all the high-level parameters and definitions for a complete
    oceanographic cruise plan.

    Attributes
    ----------
    cruise_name : str
        Name of the cruise.
    description : Optional[str]
        Human-readable description of the cruise.
    default_vessel_speed : float
        Default vessel speed in knots.
    default_distance_between_stations : float
        Default station spacing in kilometers.
    turnaround_time : float
        Time required for station turnaround in minutes.
    ctd_descent_rate : float
        CTD descent rate in meters per second.
    ctd_ascent_rate : float
        CTD ascent rate in meters per second.
    day_start_hour : int
        Start hour for daytime operations (0-23).
    day_end_hour : int
        End hour for daytime operations (0-23).
    calculate_transfer_between_sections : bool
        Whether to calculate transit times between sections.
    calculate_depth_via_bathymetry : bool
        Whether to calculate depths using bathymetry data.
    start_date : str
        Cruise start date.
    start_time : Optional[str]
        Cruise start time.
    station_label_format : str
        Format string for station labels.
    mooring_label_format : str
        Format string for mooring labels.
    departure_port : PortDefinition
        Port where the cruise begins.
    arrival_port : PortDefinition
        Port where the cruise ends.
    first_station : str
        Name of the first station.
    last_station : str
        Name of the last station.
    stations : Optional[List[StationDefinition]]
        List of station definitions.
    transits : Optional[List[TransitDefinition]]
        List of transit definitions.
    areas : Optional[List[AreaDefinition]]
        List of area definitions.
    legs : List[LegDefinition]
        List of cruise legs.
    """

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
    areas: Optional[List[AreaDefinition]] = []
    legs: List[LegDefinition]

    model_config = ConfigDict(extra="forbid")

    # --- VALIDATORS ---

    @field_validator("default_vessel_speed")
    def validate_speed(cls, v):
        """
        Validate vessel speed is within realistic bounds.

        Parameters
        ----------
        v : float
            Vessel speed value to validate.

        Returns
        -------
        float
            Validated vessel speed.

        Raises
        ------
        ValueError
            If speed is not positive, > 20 knots, or < 1 knot.
        """
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
        """
        Validate station spacing is within reasonable bounds.

        Parameters
        ----------
        v : float
            Distance value to validate.

        Returns
        -------
        float
            Validated distance.

        Raises
        ------
        ValueError
            If distance is not positive or > 150 km.
        """
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
        """
        Validate turnaround time is reasonable.

        Parameters
        ----------
        v : float
            Turnaround time value to validate.

        Returns
        -------
        float
            Validated turnaround time.

        Raises
        ------
        ValueError
            If turnaround time is negative.
        """
        if v < 0:
            raise ValueError("Turnaround time cannot be negative")
        if v > 60:
            warnings.warn(
                f"Turnaround time {v} minutes is high (> 60). Ensure units are minutes."
            )
        return v

    @field_validator("ctd_descent_rate", "ctd_ascent_rate")
    def validate_ctd_rates(cls, v):
        """
        Validate CTD rates are within safe operating limits.

        Parameters
        ----------
        v : float
            CTD rate value to validate.

        Returns
        -------
        float
            Validated CTD rate.

        Raises
        ------
        ValueError
            If rate is outside 0.5-2.0 m/s range.
        """
        if not (0.5 <= v <= 2.0):
            raise ValueError(f"CTD Rate {v} m/s is outside safe limits (0.5 - 2.0).")
        return v

    @field_validator("day_start_hour", "day_end_hour")
    def validate_hours(cls, v):
        """
        Validate hours are within valid range.

        Parameters
        ----------
        v : int
            Hour value to validate.

        Returns
        -------
        int
            Validated hour.

        Raises
        ------
        ValueError
            If hour is outside 0-23 range.
        """
        if not (0 <= v <= 23):
            raise ValueError("Hour must be between 0 and 23")
        return v

    @model_validator(mode="after")
    def validate_day_window(self):
        """
        Validate that day start time is before day end time.

        Returns
        -------
        CruiseConfig
            Self for chaining.

        Raises
        ------
        ValueError
            If day_start_hour >= day_end_hour.
        """
        if self.day_start_hour >= self.day_end_hour:
            raise ValueError(
                f"Day start ({self.day_start_hour}) must be before day end ({self.day_end_hour})"
            )
        return self

    @model_validator(mode="after")
    def check_longitude_consistency(self):
        """
        Ensure the entire cruise uses consistent longitude coordinate systems.

        Validates that all longitude values in the cruise use either the
        [-180, 180] system or the [0, 360] system, but not both.

        Returns
        -------
        CruiseConfig
            Self for chaining.

        Raises
        ------
        ValueError
            If inconsistent longitude systems are detected.
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

    Enriches the cruise configuration by adding bathymetric depths and
    formatted coordinates where missing.

    Parameters
    ----------
    config_path : Path
        Path to input YAML configuration.
    add_depths : bool, optional
        Whether to add missing depth values (default: False).
    add_coords : bool, optional
        Whether to add formatted coordinate fields (default: False).
    bathymetry_source : str, optional
        Bathymetry dataset to use (default: "etopo2022").
    coord_format : str, optional
        Coordinate format ("dmm" or "dms", default: "dmm").
    output_path : Optional[Path], optional
        Path for output file (if None, modifies in place).

    Returns
    -------
    Dict[str, Any]
        Dictionary with enrichment summary containing:
        - stations_with_depths_added: Number of depths added
        - stations_with_coords_added: Number of coordinates added
        - total_stations_processed: Total stations processed
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

    Performs schema validation, logical consistency checks, and optional
    depth verification against bathymetry data.

    Parameters
    ----------
    config_path : Path
        Path to input YAML configuration.
    check_depths : bool, optional
        Whether to validate depths against bathymetry (default: False).
    tolerance : float, optional
        Depth difference tolerance percentage (default: 10.0).
    bathymetry_source : str, optional
        Bathymetry dataset to use (default: "etopo2022").
    strict : bool, optional
        Whether to use strict validation mode (default: False).

    Returns
    -------
    Tuple[bool, List[str], List[str]]
        Tuple of (success, errors, warnings) where:
        - success: True if validation passed
        - errors: List of error messages
        - warnings: List of warning messages
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

    Validates that stated depths are reasonably close to bathymetric depths.

    Parameters
    ----------
    cruise : Any
        Loaded cruise configuration object.
    bathymetry_manager : Any
        Bathymetry data manager instance.
    tolerance : float
        Tolerance percentage for depth differences.

    Returns
    -------
    Tuple[int, List[str]]
        Tuple of (stations_checked, warning_messages) where:
        - stations_checked: Number of stations with depth data
        - warning_messages: List of depth discrepancy warnings
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
