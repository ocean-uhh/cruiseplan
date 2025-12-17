import logging
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cruiseplan.utils.constants import (
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
)
from cruiseplan.utils.coordinates import format_dmm_comment

logger = logging.getLogger(__name__)

# Track deprecation warnings to show only once per session
_shown_warnings = set()

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
    # Placeholder for user guidance
    UPDATE_PLACEHOLDER = "UPDATE-CTD-mooring-etc"


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
    SECTION = "section"  # For CTD sections that can be expanded
    # Placeholders for user guidance
    UPDATE_PROFILE_PLACEHOLDER = "UPDATE-profile-sampling-etc"
    UPDATE_LINE_PLACEHOLDER = "UPDATE-ADCP-bathymetry-etc"
    UPDATE_AREA_PLACEHOLDER = "UPDATE-bathymetry-survey-etc"


class LineOperationTypeEnum(str, Enum):
    """
    Enumeration of line operation types.

    Defines the type of operation performed along a route or transect.
    """

    UNDERWAY = "underway"
    TOWING = "towing"
    CTD = "CTD"  # Support for CTD sections that can be expanded


class AreaOperationTypeEnum(str, Enum):
    """
    Enumeration of area operation types.

    Defines operations that cover defined geographic areas.
    """

    SURVEY = "survey"
    # Placeholder for user guidance
    UPDATE_PLACEHOLDER = "UPDATE-survey-mapping-etc"


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
            # Check for incomplete coordinate pairs
            has_lat = "latitude" in data
            has_lon = "longitude" in data

            if has_lat and not has_lon:
                raise ValueError(
                    "Both latitude and longitude must be provided together"
                )
            if has_lon and not has_lat:
                raise ValueError(
                    "Both latitude and longitude must be provided together"
                )

            # Case A: Explicit Lat/Lon
            if has_lat and has_lon:
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

    @property
    def latitude(self) -> Optional[float]:
        """
        Convenient access to latitude coordinate.

        Returns the latitude from the internal position storage, providing
        direct access without needing to navigate through the position attribute.

        Returns
        -------
        Optional[float]
            Latitude in decimal degrees, or None if position not set.

        Examples
        --------
        >>> station = StationDefinition(name="CTD_001", latitude=60.0, longitude=-20.0, ...)
        >>> station.latitude  # Direct access
        60.0
        >>> station.position.latitude  # Traditional access (still works)
        60.0
        """
        return self.position.latitude if self.position else None

    @property
    def longitude(self) -> Optional[float]:
        """
        Convenient access to longitude coordinate.

        Returns the longitude from the internal position storage, providing
        direct access without needing to navigate through the position attribute.

        Returns
        -------
        Optional[float]
            Longitude in decimal degrees, or None if position not set.

        Examples
        --------
        >>> station = StationDefinition(name="CTD_001", latitude=60.0, longitude=-20.0, ...)
        >>> station.longitude  # Direct access
        -20.0
        >>> station.position.longitude  # Traditional access (still works)
        -20.0
        """
        return self.position.longitude if self.position else None


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
        Water depth at the station in meters (DEPRECATED: use operation_depth or water_depth).
    operation_depth : Optional[float]
        Target operation depth (e.g., CTD cast depth) in meters.
    water_depth : Optional[float]
        Water depth at location (seafloor depth) in meters.
    duration : Optional[float]
        Manual duration override in minutes.
    delay_start : Optional[float]
        Time to wait before operation begins in minutes (e.g., for daylight).
    delay_end : Optional[float]
        Time to wait after operation ends in minutes (e.g., for equipment settling).
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
    depth: Optional[float] = Field(
        None, description="DEPRECATED: Use operation_depth or water_depth for clarity"
    )
    operation_depth: Optional[float] = Field(
        None, description="Target operation depth (e.g., CTD cast depth)"
    )
    water_depth: Optional[float] = Field(
        None, description="Water depth at location (seafloor depth)"
    )
    duration: Optional[float] = None
    delay_start: Optional[float] = (
        None  # Time to wait before operation begins (minutes)
    )
    delay_end: Optional[float] = None  # Time to wait after operation ends (minutes)
    comment: Optional[str] = None
    equipment: Optional[str] = None
    position_string: Optional[str] = None

    @field_validator("duration")
    def validate_duration_positive(cls, v):
        """
        Validate duration value, detecting placeholder values and issuing warnings.

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
            If duration is negative (but not placeholder values).
        """
        if v is not None:
            if v == 9999.0:
                warnings.warn(
                    "Duration is set to placeholder value 9999.0 minutes. "
                    "Please update with your planned operation duration.",
                    UserWarning,
                    stacklevel=2,
                )
            elif v == 0.0:
                warnings.warn(
                    "Duration is 0.0 minutes. This may indicate incomplete configuration. "
                    "Consider updating the duration field or remove it to use automatic calculation.",
                    UserWarning,
                    stacklevel=2,
                )
            elif v < 0:
                raise ValueError("Duration cannot be negative")
        return v

    @field_validator("delay_start")
    def validate_delay_start_positive(cls, v):
        """
        Validate delay_start value to ensure it's non-negative.

        Parameters
        ----------
        v : Optional[float]
            Delay start value to validate.

        Returns
        -------
        Optional[float]
            Validated delay start value.

        Raises
        ------
        ValueError
            If delay_start is negative.
        """
        if v is not None and v < 0:
            raise ValueError("delay_start cannot be negative")
        return v

    @field_validator("delay_end")
    def validate_delay_end_positive(cls, v):
        """
        Validate delay_end value to ensure it's non-negative.

        Parameters
        ----------
        v : Optional[float]
            Delay end value to validate.

        Returns
        -------
        Optional[float]
            Validated delay end value.

        Raises
        ------
        ValueError
            If delay_end is negative.
        """
        if v is not None and v < 0:
            raise ValueError("delay_end cannot be negative")
        return v

    @field_validator("depth")
    def validate_depth_positive(cls, v):
        """
        Validate depth value to ensure it's positive.

        Issues deprecation warning and validates positivity.

        Parameters
        ----------
        v : Optional[float]
            Depth value to validate.

        Returns
        -------
        Optional[float]
            Validated depth value.

        Raises
        ------
        ValueError
            If depth is negative.
        """
        if v is not None:
            # Show deprecation warning only once per session
            warning_key = "depth_field_deprecated"
            if warning_key not in _shown_warnings:
                warnings.warn(
                    "The 'depth' field is deprecated. Use 'operation_depth' for target operation depth "
                    "or 'water_depth' for seafloor depth. This distinction improves scientific accuracy "
                    "and duration calculations.",
                    UserWarning,
                    stacklevel=2,
                )
                _shown_warnings.add(warning_key)
            if v < 0:
                raise ValueError(
                    "Station depth must be positive (depths should be given as positive values in meters)"
                )
        return v

    @field_validator("operation_depth")
    def validate_operation_depth_positive(cls, v):
        """
        Validate operation_depth value to ensure it's positive.

        Parameters
        ----------
        v : Optional[float]
            Operation depth value to validate.

        Returns
        -------
        Optional[float]
            Validated operation depth value.

        Raises
        ------
        ValueError
            If operation_depth is negative.
        """
        if v is not None and v < 0:
            raise ValueError(
                "Operation depth must be positive (depths should be given as positive values in meters)"
            )
        return v

    @field_validator("water_depth")
    def validate_water_depth_positive(cls, v):
        """
        Validate water_depth value to ensure it's positive.

        Parameters
        ----------
        v : Optional[float]
            Water depth value to validate.

        Returns
        -------
        Optional[float]
            Validated water depth value.

        Raises
        ------
        ValueError
            If water_depth is negative.
        """
        if v is not None and v < 0:
            raise ValueError(
                "Water depth must be positive (depths should be given as positive values in meters)"
            )
        return v

    @field_validator("operation_type")
    def validate_operation_type(cls, v):
        """
        Validate operation_type value.

        Parameters
        ----------
        v : OperationTypeEnum
            Operation type value to validate.

        Returns
        -------
        OperationTypeEnum
            Validated operation type value.
        """
        # Placeholder values are now valid enum values
        return v

    @field_validator("action")
    def validate_action(cls, v):
        """
        Validate action value.

        Parameters
        ----------
        v : ActionEnum
            Action value to validate.

        Returns
        -------
        ActionEnum
            Validated action value.
        """
        # Placeholder values are now valid enum values
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
        # Skip validation if either value is a placeholder
        if (
            self.operation_type == OperationTypeEnum.UPDATE_PLACEHOLDER
            or self.action
            in [
                ActionEnum.UPDATE_PROFILE_PLACEHOLDER,
                ActionEnum.UPDATE_LINE_PLACEHOLDER,
                ActionEnum.UPDATE_AREA_PLACEHOLDER,
            ]
        ):
            return self

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

    @model_validator(mode="after")
    def migrate_depth_fields(self):
        """
        Migrate from legacy depth field to new semantic depth fields.

        Provides backward compatibility by inferring operation_depth and water_depth
        from the deprecated depth field when the new fields are not specified.

        Returns
        -------
        StationDefinition
            Self for chaining.
        """
        # Migration logic: if depth is specified but new fields aren't, infer them
        if (
            self.depth is not None
            and self.operation_depth is None
            and self.water_depth is None
        ):
            # For most operations, assume the specified depth is the operation target
            # This matches existing behavior where depth was used for duration calculations
            self.operation_depth = self.depth
            # Also set water_depth to same value unless enrichment fills it from bathymetry
            self.water_depth = self.depth
            logger.warning(
                f"Station '{self.name}': Migrating deprecated 'depth' field ({self.depth}m) to both "
                f"operation_depth and water_depth. For CTD operations, operation_depth and water_depth "
                f"may differ. Please review and update your configuration to use explicit depth fields."
            )
        elif self.depth is not None:
            # If new fields are specified, the depth field should not be used
            # This prevents conflicting depth information
            pass  # The deprecation warning will already have been issued
        elif self.operation_depth is None and self.water_depth is not None:
            # If only water_depth specified, default operation_depth to water_depth (full water column)
            self.operation_depth = self.water_depth
        elif self.water_depth is None and self.operation_depth is not None:
            # If only operation_depth specified, user should provide water_depth via enrichment
            # Don't auto-set water_depth here as it should come from bathymetry
            pass

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
            # Skip validation if action is a placeholder
            if self.action in [
                ActionEnum.UPDATE_PROFILE_PLACEHOLDER,
                ActionEnum.UPDATE_LINE_PLACEHOLDER,
                ActionEnum.UPDATE_AREA_PLACEHOLDER,
            ]:
                return self

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
    operation_type : Optional[AreaOperationTypeEnum]
        Type of operation for the area (default: "survey").
    action : Optional[ActionEnum]
        Specific action for the area operation.
    duration : Optional[float]
        Duration for the area operation in minutes.
    """

    name: str
    corners: List[GeoPoint]
    comment: Optional[str] = None
    operation_type: Optional[AreaOperationTypeEnum] = AreaOperationTypeEnum.SURVEY
    action: Optional[ActionEnum] = None
    duration: Optional[float] = None  # Duration in minutes

    @field_validator("duration")
    def validate_duration_positive(cls, v):
        """
        Validate duration value, detecting placeholder values and issuing warnings.

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
            If duration is negative (but not placeholder values).
        """
        if v is not None:
            if v == 9999.0:
                warnings.warn(
                    "Duration is set to placeholder value 9999.0 minutes. "
                    "Please update with your planned operation duration.",
                    UserWarning,
                    stacklevel=2,
                )
            elif v == 0.0:
                warnings.warn(
                    "Duration is 0.0 minutes. This may indicate incomplete configuration. "
                    "Consider updating the duration field or remove it to use automatic calculation.",
                    UserWarning,
                    stacklevel=2,
                )
            elif v < 0:
                raise ValueError("Duration cannot be negative")
        return v


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
    buffer_time : Optional[float]
        Contingency time for entire leg operations in minutes (e.g., weather delays).
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
    buffer_time: Optional[float] = (
        None  # Contingency time for entire leg operations (minutes)
    )
    stations: Optional[List[Union[str, StationDefinition]]] = []
    clusters: Optional[List[ClusterDefinition]] = []
    sections: Optional[List[SectionDefinition]] = []
    sequence: Optional[List[Union[str, StationDefinition]]] = []

    @field_validator("buffer_time")
    def validate_buffer_time_positive(cls, v):
        """
        Validate buffer_time value to ensure it's non-negative.

        Parameters
        ----------
        v : Optional[float]
            Buffer time value to validate.

        Returns
        -------
        Optional[float]
            Validated buffer time value.

        Raises
        ------
        ValueError
            If buffer_time is negative.
        """
        if v is not None and v < 0:
            raise ValueError("buffer_time cannot be negative")
        return v


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
            lons.append(self.departure_port.longitude)
        if self.arrival_port:
            lons.append(self.arrival_port.longitude)

        # 2. Collect from Catalog
        if self.stations:
            lons.extend([s.longitude for s in self.stations])
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
                        lons.append(item.longitude)
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


def replace_placeholder_values(
    config_dict: Dict[str, Any],
) -> Tuple[Dict[str, Any], bool]:
    """
    Preserve placeholder values since they are now valid enum values.

    This function no longer replaces placeholders, as they are treated as valid
    enum values in the validation system. Users can continue using placeholders
    throughout the workflow and only replace them when manually updating the configuration.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Raw configuration dictionary from YAML

    Returns
    -------
    Tuple[Dict[str, Any], bool]
        Configuration dictionary unchanged and whether any replacements were made (always False)
    """
    # Placeholders are now valid enum values, so no replacement needed
    logger.debug("Preserving placeholder values as valid enum values")
    return config_dict, False


def expand_ctd_sections(
    config: Dict[str, Any],
    default_depth: float = -9999.0,  # Use placeholder value to trigger bathymetry lookup
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Expand CTD sections into individual station definitions.

    This function finds transits with operation_type="CTD" and action="section",
    expands them into individual stations along the route, and updates all
    references in legs to point to the new stations.

    Parameters
    ----------
    config : Dict[str, Any]
        The cruise configuration dictionary

    Returns
    -------
    Tuple[Dict[str, Any], Dict[str, int]]
        Modified configuration and summary with sections_expanded and stations_from_expansion counts
    """
    from cruiseplan.calculators.distance import haversine_distance

    # Preserve comments by avoiding deepcopy - modify config in place if it's a CommentedMap
    # or create a shallow working copy for plain dictionaries
    if hasattr(config, "copy"):
        # This is likely a CommentedMap - use its copy method to preserve structure
        config = config.copy()
    else:
        # Regular dictionary - use shallow copy and convert to plain dict
        import copy

        config = copy.copy(config)

    def interpolate_position(
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        fraction: float,
    ) -> Tuple[float, float]:
        """Interpolate position along great circle route."""
        import math

        # Convert degrees to radians
        lat1 = math.radians(start_lat)
        lon1 = math.radians(start_lon)
        lat2 = math.radians(end_lat)
        lon2 = math.radians(end_lon)

        # Calculate angular distance
        d = math.acos(
            min(
                1,
                math.sin(lat1) * math.sin(lat2)
                + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1),
            )
        )

        # Handle edge case for very short distances
        if d < 1e-9:
            return start_lat, start_lon

        # Spherical interpolation
        A = math.sin((1 - fraction) * d) / math.sin(d)
        B = math.sin(fraction * d) / math.sin(d)

        x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
        y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
        z = A * math.sin(lat1) + B * math.sin(lat2)

        # Convert back to lat/lon
        lat_result = math.atan2(z, math.sqrt(x * x + y * y))
        lon_result = math.atan2(y, x)

        return math.degrees(lat_result), math.degrees(lon_result)

    def expand_section(transit: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Expand a single CTD section transit into stations."""
        if not transit.get("route") or len(transit["route"]) < 2:
            logger.warning(
                f"Transit {transit.get('name', 'unnamed')} has insufficient route points for expansion"
            )
            return []

        start = transit["route"][0]
        end = transit["route"][-1]

        start_lat = start.get("latitude", start.get("lat"))
        start_lon = start.get("longitude", start.get("lon"))
        end_lat = end.get("latitude", end.get("lat"))
        end_lon = end.get("longitude", end.get("lon"))

        if any(coord is None for coord in [start_lat, start_lon, end_lat, end_lon]):
            logger.warning(
                f"Transit {transit.get('name', 'unnamed')} has missing coordinates"
            )
            return []

        total_distance_km = haversine_distance(
            (start_lat, start_lon), (end_lat, end_lon)
        )
        spacing_km = transit.get("distance_between_stations", 20.0)
        num_stations = max(2, int(total_distance_km / spacing_km) + 1)

        stations = []
        import re

        # Robust sanitization of station names - replace all non-alphanumeric with underscores
        base_name = re.sub(r"[^a-zA-Z0-9_]", "_", transit["name"])
        # Remove duplicate underscores and strip leading/trailing underscores
        base_name = re.sub(r"_+", "_", base_name).strip("_")

        for i in range(num_stations):
            fraction = i / (num_stations - 1) if num_stations > 1 else 0
            lat, lon = interpolate_position(
                start_lat, start_lon, end_lat, end_lon, fraction
            )

            station = {
                "name": f"{base_name}_Stn{i+1:03d}",
                "operation_type": "CTD",
                "action": "profile",
                "latitude": round(lat, 5),  # Modern flat structure
                "longitude": round(lon, 5),  # Modern flat structure
                "comment": f"Station {i+1}/{num_stations} on {transit['name']} section",
                # Only set water_depth if we have a valid default value
                # None will trigger bathymetry lookup during enrichment
                "duration": 120.0,  # Duration in minutes for consistency
            }

            # Copy additional fields if present, converting to modern field names
            if "max_depth" in transit:
                station["water_depth"] = transit[
                    "max_depth"
                ]  # Use semantic water_depth
            elif default_depth != -9999.0:
                # Use provided default depth if valid (not the placeholder value)
                station["water_depth"] = default_depth
            # If no depth is specified, let enrichment process handle bathymetry lookup

            if "planned_duration_hours" in transit:
                # Convert hours to minutes for consistency
                station["duration"] = float(transit["planned_duration_hours"]) * 60.0
            if "duration" in transit:
                station["duration"] = float(transit["duration"])  # Already in minutes

            stations.append(station)

        logger.info(f"Expanded '{transit['name']}' into {len(stations)} stations")
        return stations

    # Find CTD sections in transits
    ctd_sections = []
    if "transits" in config:
        for transit in config["transits"]:
            if (
                transit.get("operation_type") == "CTD"
                and transit.get("action") == "section"
            ):
                ctd_sections.append(transit)

    # Expand each section
    expanded_stations = {}  # Map from section name to list of station names
    total_stations_created = 0

    for section in ctd_sections:
        section_name = section["name"]
        new_stations = expand_section(section)

        if new_stations:
            # Add to stations catalog
            if "stations" not in config:
                config["stations"] = []

            # Check for existing station names to avoid duplicates
            existing_names = {
                s.get("name") for s in config["stations"] if s.get("name")
            }

            station_names = []
            for station in new_stations:
                station_name = station["name"]
                # Add unique suffix if name already exists
                counter = 1
                original_name = station_name
                while station_name in existing_names:
                    station_name = f"{original_name}_{counter:02d}"
                    counter += 1

                station["name"] = station_name
                existing_names.add(station_name)

                config["stations"].append(station)
                station_names.append(station_name)
                total_stations_created += 1

            expanded_stations[section_name] = station_names

    # Remove expanded transits from the transits list
    if "transits" in config and ctd_sections:
        config["transits"] = [
            t
            for t in config["transits"]
            if not (t.get("operation_type") == "CTD" and t.get("action") == "section")
        ]
        # Clean up empty transits list
        if not config["transits"]:
            del config["transits"]

    # Update first_station and last_station references if they point to expanded sections
    if "first_station" in config and config["first_station"] in expanded_stations:
        # Use the first station from the expansion
        config["first_station"] = expanded_stations[config["first_station"]][0]
        logger.info(f"Updated first_station to {config['first_station']}")

    if "last_station" in config and config["last_station"] in expanded_stations:
        # Use the last station from the expansion
        config["last_station"] = expanded_stations[config["last_station"]][-1]
        logger.info(f"Updated last_station to {config['last_station']}")

    # Update leg references
    for leg in config.get("legs", []):
        # Check direct stations in leg
        if leg.get("stations"):
            new_stations = []
            for item in leg["stations"]:
                if isinstance(item, str) and item in expanded_stations:
                    new_stations.extend(expanded_stations[item])
                else:
                    new_stations.append(item)
            leg["stations"] = new_stations

        # Check clusters
        for cluster in leg.get("clusters", []):
            # Check sequence field
            if cluster.get("sequence"):
                new_sequence = []
                for item in cluster["sequence"]:
                    if isinstance(item, str) and item in expanded_stations:
                        new_sequence.extend(expanded_stations[item])
                    else:
                        new_sequence.append(item)
                cluster["sequence"] = new_sequence

            # Check stations field
            if cluster.get("stations"):
                new_stations = []
                for item in cluster["stations"]:
                    if isinstance(item, str) and item in expanded_stations:
                        new_stations.extend(expanded_stations[item])
                    else:
                        new_stations.append(item)
                cluster["stations"] = new_stations

    summary = {
        "sections_expanded": len(ctd_sections),
        "stations_from_expansion": total_stations_created,
    }

    return config, summary


def enrich_configuration(
    config_path: Path,
    add_depths: bool = False,
    add_coords: bool = False,
    expand_sections: bool = False,
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
    expand_sections : bool, optional
        Whether to expand CTD sections into individual stations (default: False).
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
        - sections_expanded: Number of CTD sections expanded
        - stations_from_expansion: Number of stations generated from expansion
        - total_stations_processed: Total stations processed
    """
    from cruiseplan.cli.utils import save_yaml_config
    from cruiseplan.core.cruise import Cruise
    from cruiseplan.data.bathymetry import BathymetryManager
    from cruiseplan.utils.yaml_io import load_yaml, save_yaml

    # Load and preprocess the YAML configuration to replace placeholders
    config_dict = load_yaml(config_path)

    # Replace placeholder values with sensible defaults
    config_dict, placeholders_replaced = replace_placeholder_values(config_dict)

    # Expand CTD sections if requested
    sections_expanded = 0
    stations_from_expansion = 0
    if expand_sections:
        config_dict, expansion_summary = expand_ctd_sections(config_dict)
        sections_expanded = expansion_summary["sections_expanded"]
        stations_from_expansion = expansion_summary["stations_from_expansion"]

    # Create temporary file with processed config for Cruise loading
    import tempfile

    # Capture Python warnings for better formatting
    import warnings as python_warnings

    captured_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    # Set up warning capture
    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    # Use context manager for safe temporary file handling
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as tmp_file:
        temp_config_path = Path(tmp_file.name)

    try:
        # Use comment-preserving YAML save for temp file
        save_yaml(config_dict, temp_config_path, backup=False)
        # Load cruise configuration from preprocessed data
        cruise = Cruise(temp_config_path)
    finally:
        # Clean up temporary file safely
        if temp_config_path.exists():
            temp_config_path.unlink()
        # Restore original warning handler
        python_warnings.showwarning = old_showwarning

    enrichment_summary = {
        "stations_with_depths_added": 0,
        "stations_with_coords_added": 0,
        "sections_expanded": sections_expanded,
        "stations_from_expansion": stations_from_expansion,
        "total_stations_processed": len(cruise.station_registry),
    }

    # Initialize managers if needed
    if add_depths:
        bathymetry = BathymetryManager(source=bathymetry_source, data_dir="data")

    # Track which stations had depths added for accurate YAML updating
    stations_with_depths_added = set()

    # Process each station
    for station_name, station in cruise.station_registry.items():
        # Add water depths if requested (bathymetry enrichment targets water_depth field)
        should_add_water_depth = add_depths and (
            not hasattr(station, "water_depth")
            or station.water_depth is None
            or station.water_depth == -9999.0  # Replace placeholder depth
        )
        if should_add_water_depth:
            depth = bathymetry.get_depth_at_point(station.latitude, station.longitude)
            if depth is not None and depth != 0:
                station.water_depth = round(
                    abs(depth)
                )  # Convert to positive depth, rounded to nearest meter
                enrichment_summary["stations_with_depths_added"] += 1
                stations_with_depths_added.add(station_name)
                logger.debug(
                    f"Added water depth {station.water_depth:.0f}m to station {station_name}"
                )

    # Update YAML configuration with any changes
    # Note: Keep using original config_dict to preserve comments, don't overwrite with cruise.raw_data
    coord_changes_made = 0

    def add_dmm_coordinates(data_dict, lat, lon, coord_field_name):
        """Helper function to add DMM coordinates to a data dictionary."""
        nonlocal coord_changes_made
        if coord_format == "dmm":
            if coord_field_name not in data_dict or not data_dict.get(coord_field_name):
                dmm_comment = format_dmm_comment(lat, lon)

                # For ruamel.yaml CommentedMap, insert coordinates right after the name field
                if hasattr(data_dict, "insert"):
                    # Strategy: Insert coordinates_dmm right after the 'name' field (which is required)
                    if "name" in data_dict:
                        name_pos = list(data_dict.keys()).index("name")
                        insert_pos = name_pos + 1
                    else:
                        # Fallback to beginning if no name field (shouldn't happen)
                        insert_pos = 0

                    logger.debug(
                        f"Inserting {coord_field_name} at position {insert_pos} after 'name' field in {type(data_dict).__name__}"
                    )
                    data_dict.insert(insert_pos, coord_field_name, dmm_comment)
                else:
                    # Fallback for regular dict
                    data_dict[coord_field_name] = dmm_comment

                coord_changes_made += 1
                return dmm_comment
        elif coord_format == "dms":
            warnings.warn(
                "DMS coordinate format is not yet supported. No coordinates were added.",
                UserWarning,
            )
        else:
            warnings.warn(
                f"Unknown coordinate format '{coord_format}' specified. No coordinates were added.",
                UserWarning,
            )
        return None

    # Process coordinate additions for stations
    if "stations" in config_dict:
        for station_data in config_dict["stations"]:
            station_name = station_data["name"]
            if station_name in cruise.station_registry:
                station_obj = cruise.station_registry[station_name]

                # Update water_depth if it was newly added by this function
                if station_name in stations_with_depths_added:
                    # Add water_depth field with careful placement after name field
                    water_depth_value = float(station_obj.water_depth)

                    if hasattr(station_data, "insert"):
                        # Position water_depth after the 'name' field for consistent structure
                        if "name" in station_data:
                            name_pos = list(station_data.keys()).index("name")
                            insert_pos = name_pos + 1
                        else:
                            insert_pos = 0

                        logger.debug(
                            f"Inserting water_depth at position {insert_pos} after 'name' field"
                        )
                        station_data.insert(
                            insert_pos, "water_depth", water_depth_value
                        )
                    else:
                        # Fallback for regular dict
                        station_data["water_depth"] = water_depth_value

                # Add coordinate fields if requested
                if add_coords:
                    dmm_result = add_dmm_coordinates(
                        station_data,
                        station_obj.latitude,
                        station_obj.longitude,
                        "coordinates_dmm",
                    )
                    if dmm_result:
                        logger.debug(
                            f"Added DMM coordinates to station {station_name}: {dmm_result}"
                        )

    # Process coordinate additions for departure and arrival ports
    if add_coords:
        for port_key in ["departure_port", "arrival_port"]:
            if port_key in config_dict and config_dict[port_key]:
                port_data = config_dict[port_key]
                if hasattr(cruise.config, port_key):
                    port_obj = getattr(cruise.config, port_key)
                    if hasattr(port_obj, "position") and port_obj.position:
                        dmm_result = add_dmm_coordinates(
                            port_data,
                            port_obj.latitude,
                            port_obj.longitude,
                            "coordinates_dmm",
                        )
                        if dmm_result:
                            logger.debug(
                                f"Added DMM coordinates to {port_key}: {dmm_result}"
                            )

    # Process coordinate additions for transit routes
    if add_coords and "transits" in config_dict:
        for transit_data in config_dict["transits"]:
            if "route" in transit_data and transit_data["route"]:
                # Add route_dmm field with list of position_dmm entries
                if "route_dmm" not in transit_data:
                    route_dmm_list = []
                    for point in transit_data["route"]:
                        if "latitude" in point and "longitude" in point:
                            dmm_comment = format_dmm_comment(
                                point["latitude"], point["longitude"]
                            )
                            route_dmm_list.append({"position_dmm": dmm_comment})
                            coord_changes_made += 1

                    if route_dmm_list:
                        transit_data["route_dmm"] = route_dmm_list
                        logger.debug(
                            f"Added DMM coordinates to transit {transit_data.get('name', 'unnamed')} route: {len(route_dmm_list)} points"
                        )

    # Process coordinate additions for area corners
    if add_coords and "areas" in config_dict:
        for area_data in config_dict["areas"]:
            if "corners" in area_data and area_data["corners"]:
                # Add corners_dmm field with list of position_dmm entries
                if "corners_dmm" not in area_data:
                    corners_dmm_list = []
                    for corner in area_data["corners"]:
                        if "latitude" in corner and "longitude" in corner:
                            dmm_comment = format_dmm_comment(
                                corner["latitude"], corner["longitude"]
                            )
                            corners_dmm_list.append({"position_dmm": dmm_comment})
                            coord_changes_made += 1

                    if corners_dmm_list:
                        area_data["corners_dmm"] = corners_dmm_list
                        logger.debug(
                            f"Added DMM coordinates to area {area_data.get('name', 'unnamed')} corners: {len(corners_dmm_list)} points"
                        )
    # Update the enrichment summary
    enrichment_summary["stations_with_coords_added"] = coord_changes_made
    total_enriched = (
        enrichment_summary["stations_with_depths_added"]
        + enrichment_summary["stations_with_coords_added"]
        + enrichment_summary["sections_expanded"]
    )

    # Process captured warnings and display them in user-friendly format
    if captured_warnings:
        formatted_warnings = _format_validation_warnings(captured_warnings, cruise)
        for warning_group in formatted_warnings:
            logger.warning("⚠️ Configuration Warnings:")
            for line in warning_group.split("\n"):
                if line.strip():
                    logger.warning(f"  {line}")
            logger.warning("")  # Add spacing between warning groups

    # Save enriched configuration only if any changes were made OR if placeholders were replaced
    if output_path and (total_enriched > 0 or placeholders_replaced):
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
    import warnings as python_warnings

    from pydantic import ValidationError

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.data.bathymetry import BathymetryManager

    errors = []
    warnings = []

    # Capture Python warnings for better formatting
    captured_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    # Set up warning capture
    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    try:
        # Load and validate configuration
        cruise = Cruise(config_path)

        # Basic validation passed if we get here
        logger.debug("✓ YAML structure and schema validation passed")

        # Duplicate detection (always run)
        duplicate_errors, duplicate_warnings = check_duplicate_names(cruise)
        errors.extend(duplicate_errors)
        warnings.extend(duplicate_warnings)

        complete_dup_errors, complete_dup_warnings = check_complete_duplicates(cruise)
        errors.extend(complete_dup_errors)
        warnings.extend(complete_dup_warnings)

        if duplicate_errors or complete_dup_errors:
            logger.debug(
                f"Found {len(duplicate_errors + complete_dup_errors)} duplicate-related errors"
            )
        if duplicate_warnings or complete_dup_warnings:
            logger.debug(
                f"Found {len(duplicate_warnings + complete_dup_warnings)} duplicate-related warnings"
            )

        # Depth validation if requested
        if check_depths:
            bathymetry = BathymetryManager(source=bathymetry_source, data_dir="data")
            stations_checked, depth_warnings = validate_depth_accuracy(
                cruise, bathymetry, tolerance
            )
            warnings.extend(depth_warnings)
            logger.debug(f"Checked {stations_checked} stations for depth accuracy")

        # Additional validations can be added here

        # Check for unexpanded CTD sections (raw YAML and cruise object)
        ctd_section_warnings = _check_unexpanded_ctd_sections(cruise)
        warnings.extend(ctd_section_warnings)

        # Check for cruise metadata issues
        metadata_warnings = _check_cruise_metadata(cruise)
        warnings.extend(metadata_warnings)

        # Process captured warnings and format them nicely
        formatted_warnings = _format_validation_warnings(captured_warnings, cruise)
        warnings.extend(formatted_warnings)

        success = len(errors) == 0
        return success, errors, warnings

    except ValidationError as e:
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            errors.append(f"Schema error at {location}: {message}")

        # Still try to collect warnings even when validation fails
        try:
            # Try to load the YAML directly for metadata checking
            from cruiseplan.utils.yaml_io import load_yaml_safe

            raw_config = load_yaml_safe(config_path)

            # Check cruise metadata from raw YAML
            if raw_config:
                metadata_warnings = _check_cruise_metadata_raw(raw_config)
                warnings.extend(metadata_warnings)

                # Check for unexpanded CTD sections from raw YAML
                ctd_warnings = _check_unexpanded_ctd_sections_raw(raw_config)
                warnings.extend(ctd_warnings)
        except Exception:
            # If we can't load raw YAML, just continue
            pass

        # Process captured Pydantic warnings even on validation failure
        formatted_warnings = _format_validation_warnings(captured_warnings, None)
        warnings.extend(formatted_warnings)

        return False, errors, warnings

    except Exception as e:
        errors.append(f"Configuration loading error: {e}")
        return False, errors, warnings

    finally:
        # Restore original warning handler
        python_warnings.showwarning = old_showwarning


def _check_unexpanded_ctd_sections(cruise) -> List[str]:
    """
    Check for CTD sections that haven't been expanded yet.

    Parameters
    ----------
    cruise : Cruise
        Cruise object to check.

    Returns
    -------
    List[str]
        List of warning messages about unexpanded CTD sections.
    """
    warnings = []

    # Check if there are any transits with CTD sections
    if hasattr(cruise.config, "transits") and cruise.config.transits:
        for transit in cruise.config.transits:
            if (
                hasattr(transit, "operation_type")
                and hasattr(transit, "action")
                and transit.operation_type == "CTD"
                and transit.action == "section"
            ):
                warnings.append(
                    f"Transit '{transit.name}' is a CTD section that should be expanded. "
                    f"Run 'cruiseplan enrich --expand-sections' to convert it to individual stations."
                )

    return warnings


def _check_unexpanded_ctd_sections_raw(config_dict: Dict[str, Any]) -> List[str]:
    """
    Check for CTD sections that haven't been expanded yet from raw YAML.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Raw configuration dictionary from YAML.

    Returns
    -------
    List[str]
        List of warning messages about unexpanded CTD sections.
    """
    warnings = []

    # Check if there are any transits with CTD sections
    if "transits" in config_dict and config_dict["transits"]:
        for transit in config_dict["transits"]:
            if (
                transit.get("operation_type") == "CTD"
                and transit.get("action") == "section"
            ):
                name = transit.get("name", "unnamed")
                warnings.append(
                    f"Transit '{name}' is a CTD section that should be expanded. "
                    f"Run 'cruiseplan enrich --expand-sections' to convert it to individual stations."
                )

    return warnings


def _check_cruise_metadata(cruise) -> List[str]:
    """
    Check cruise metadata for placeholder values and default coordinates.

    Parameters
    ----------
    cruise : Cruise
        Cruise object to check.

    Returns
    -------
    List[str]
        List of cruise metadata warning messages.
    """
    metadata_warnings = []

    # Check for UPDATE- placeholders in cruise-level fields
    config = cruise.config

    # Check start_date
    if hasattr(config, "start_date"):
        if config.start_date.startswith("UPDATE-"):
            metadata_warnings.append(
                "Start date is set to placeholder 'UPDATE-YYYY-MM-DDTHH:MM:SSZ'. Please update with actual cruise start date."
            )
        elif config.start_date == "1970-01-01T00:00:00Z":
            metadata_warnings.append(
                "Start date is set to default '1970-01-01T00:00:00Z'. Please update with actual cruise start date."
            )

    # Check departure port
    if hasattr(config, "departure_port"):
        port = config.departure_port
        if hasattr(port, "name") and port.name.startswith("UPDATE-"):
            metadata_warnings.append(
                "Departure port name is set to placeholder 'UPDATE-departure-port-name'. Please update with actual port name."
            )

        if hasattr(port, "position"):
            if port.latitude == 0.0 and port.longitude == 0.0:
                metadata_warnings.append(
                    "Departure port coordinates are set to default (0.0, 0.0). Please update with actual port coordinates."
                )

        if hasattr(port, "timezone") and port.timezone == "GMT+0":
            metadata_warnings.append(
                "Departure port timezone is set to default 'GMT+0'. Please update with actual port timezone."
            )

    # Check arrival port
    if hasattr(config, "arrival_port"):
        port = config.arrival_port
        if hasattr(port, "name") and port.name.startswith("UPDATE-"):
            metadata_warnings.append(
                "Arrival port name is set to placeholder 'UPDATE-arrival-port-name'. Please update with actual port name."
            )

        if hasattr(port, "position"):
            if port.latitude == 0.0 and port.longitude == 0.0:
                metadata_warnings.append(
                    "Arrival port coordinates are set to default (0.0, 0.0). Please update with actual port coordinates."
                )

        if hasattr(port, "timezone") and port.timezone == "GMT+0":
            metadata_warnings.append(
                "Arrival port timezone is set to default 'GMT+0'. Please update with actual port timezone."
            )

    # Format warnings if any found
    if metadata_warnings:
        lines = ["Cruise Metadata:"]
        for warning in metadata_warnings:
            lines.append(f"  - {warning}")
        return ["\n".join(lines)]

    return []


def _check_cruise_metadata_raw(raw_config: dict) -> List[str]:
    """
    Check cruise metadata for placeholder values and default coordinates from raw YAML.

    Parameters
    ----------
    raw_config : dict
        Raw YAML configuration dictionary.

    Returns
    -------
    List[str]
        List of cruise metadata warning messages.
    """
    metadata_warnings = []

    # Check for UPDATE- placeholders in cruise-level fields

    # Check start_date
    if "start_date" in raw_config:
        start_date = str(raw_config["start_date"])
        if start_date.startswith("UPDATE-"):
            metadata_warnings.append(
                "Start date is set to placeholder 'UPDATE-YYYY-MM-DDTHH:MM:SSZ'. Please update with actual cruise start date."
            )
        elif start_date == "1970-01-01T00:00:00Z":
            metadata_warnings.append(
                "Start date is set to default '1970-01-01T00:00:00Z'. Please update with actual cruise start date."
            )

    # Check departure port
    if "departure_port" in raw_config:
        port = raw_config["departure_port"]
        if "name" in port and str(port["name"]).startswith("UPDATE-"):
            metadata_warnings.append(
                "Departure port name is set to placeholder 'UPDATE-departure-port-name'. Please update with actual port name."
            )

        if "position" in port:
            position = port["position"]
            if position.get("latitude") == 0.0 and position.get("longitude") == 0.0:
                metadata_warnings.append(
                    "Departure port coordinates are set to default (0.0, 0.0). Please update with actual port coordinates."
                )

        if port.get("timezone") == "GMT+0":
            metadata_warnings.append(
                "Departure port timezone is set to default 'GMT+0'. Please update with actual port timezone."
            )

    # Check arrival port
    if "arrival_port" in raw_config:
        port = raw_config["arrival_port"]
        if "name" in port and str(port["name"]).startswith("UPDATE-"):
            metadata_warnings.append(
                "Arrival port name is set to placeholder 'UPDATE-arrival-port-name'. Please update with actual port name."
            )

        if "position" in port:
            position = port["position"]
            if position.get("latitude") == 0.0 and position.get("longitude") == 0.0:
                metadata_warnings.append(
                    "Arrival port coordinates are set to default (0.0, 0.0). Please update with actual port coordinates."
                )

        if port.get("timezone") == "GMT+0":
            metadata_warnings.append(
                "Arrival port timezone is set to default 'GMT+0'. Please update with actual port timezone."
            )

    # Format warnings if any found
    if metadata_warnings:
        lines = ["Cruise Metadata:"]
        for warning in metadata_warnings:
            lines.append(f"  - {warning}")
        return ["\n".join(lines)]

    return []


def _format_validation_warnings(captured_warnings: List[str], cruise) -> List[str]:
    """
    Format captured Pydantic warnings into user-friendly grouped messages.

    Parameters
    ----------
    captured_warnings : List[str]
        List of captured warning messages from Pydantic validators.
    cruise : Cruise
        Cruise object to map warnings to specific entities.

    Returns
    -------
    List[str]
        Formatted warning messages grouped by type and sorted alphabetically.
    """
    if not captured_warnings:
        return []

    # Group warnings by type and entity
    warning_groups = {
        "Cruise Metadata": [],
        "Stations": {},
        "Transits": {},
        "Areas": {},
        "Configuration": [],
    }

    # Process each warning and try to associate it with specific entities
    for warning_msg in captured_warnings:
        # Try to identify which entity this warning belongs to
        entity_found = False

        # Check stations
        if hasattr(cruise, "station_registry"):
            for station_name, station in cruise.station_registry.items():
                if _warning_relates_to_entity(warning_msg, station):
                    if station_name not in warning_groups["Stations"]:
                        warning_groups["Stations"][station_name] = []
                    warning_groups["Stations"][station_name].append(
                        _clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # Check transits
        if not entity_found and hasattr(cruise, "transit_registry"):
            for transit_name, transit in cruise.transit_registry.items():
                if _warning_relates_to_entity(warning_msg, transit):
                    if transit_name not in warning_groups["Transits"]:
                        warning_groups["Transits"][transit_name] = []
                    warning_groups["Transits"][transit_name].append(
                        _clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # Check areas
        if (
            not entity_found
            and hasattr(cruise, "config")
            and hasattr(cruise.config, "areas")
            and cruise.config.areas
        ):
            for area in cruise.config.areas:
                if _warning_relates_to_entity(warning_msg, area):
                    area_name = area.name
                    if area_name not in warning_groups["Areas"]:
                        warning_groups["Areas"][area_name] = []
                    warning_groups["Areas"][area_name].append(
                        _clean_warning_message(warning_msg)
                    )
                    entity_found = True
                    break

        # If not found, add to general configuration warnings
        if not entity_found:
            warning_groups["Configuration"].append(_clean_warning_message(warning_msg))

    # Format the grouped warnings
    formatted_sections = []

    for group_name in ["Stations", "Transits", "Areas"]:
        if warning_groups[group_name]:
            lines = [f"{group_name}:"]
            # Sort entity names alphabetically
            for entity_name in sorted(warning_groups[group_name].keys()):
                entity_warnings = warning_groups[group_name][entity_name]
                for warning in entity_warnings:
                    lines.append(f"  - {entity_name}: {warning}")
            formatted_sections.append("\n".join(lines))

    # Add configuration warnings
    if warning_groups["Configuration"]:
        lines = ["Configuration:"]
        for warning in warning_groups["Configuration"]:
            lines.append(f"  - {warning}")
        formatted_sections.append("\n".join(lines))

    return formatted_sections


def _warning_relates_to_entity(warning_msg: str, entity) -> bool:
    """Check if a warning message relates to a specific entity by examining field values."""
    # Check for placeholder values that would trigger warnings
    if hasattr(entity, "operation_type") and str(entity.operation_type) in warning_msg:
        # Make sure this isn't a placeholder operation_type warning
        if "placeholder" not in warning_msg:
            return True
        # Check for placeholder operation_type values
        if hasattr(entity, "operation_type") and str(entity.operation_type) in [
            "UPDATE-CTD-mooring-etc",
            "UPDATE_PLACEHOLDER",
        ]:
            return True

    if hasattr(entity, "action") and str(entity.action) in warning_msg:
        # Make sure this isn't a placeholder action warning
        if "placeholder" not in warning_msg:
            return True
        # Check for placeholder action values
        if hasattr(entity, "action") and str(entity.action) in [
            "UPDATE-profile-sampling-etc",
            "UPDATE-ADCP-bathymetry-etc",
            "UPDATE-bathymetry-survey-etc",
        ]:
            return True

    if (
        hasattr(entity, "duration")
        and entity.duration is not None
        and entity.duration == 9999.0
        and "9999.0" in warning_msg
    ):
        return True
    return False


def _clean_warning_message(warning_msg: str) -> str:
    """Clean up warning message for user display."""
    # Remove redundant phrases and clean up the message
    cleaned = warning_msg.replace(
        "Duration is set to placeholder value ", "Duration is set to placeholder "
    )
    cleaned = cleaned.replace(
        "Operation type is set to placeholder ", "Operation type is set to placeholder "
    )
    cleaned = cleaned.replace(
        "Action is set to placeholder ", "Action is set to placeholder "
    )
    return cleaned


def validate_depth_accuracy(
    cruise, bathymetry_manager, tolerance: float
) -> Tuple[int, List[str]]:
    """
    Compare station water depths with bathymetry data.

    Validates that stated water depths are reasonably close to bathymetric depths.

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
        # Check water_depth field first (new), then fall back to legacy depth field
        water_depth = getattr(station, "water_depth", None) or getattr(
            station, "depth", None
        )
        if water_depth is not None:
            stations_checked += 1

            # Get depth from bathymetry
            bathymetry_depth = bathymetry_manager.get_depth_at_point(
                station.latitude, station.longitude
            )

            if bathymetry_depth is not None and bathymetry_depth != 0:
                # Convert to positive depth value
                expected_depth = abs(bathymetry_depth)
                stated_depth = water_depth

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

        # Additional validation for moorings: operation_depth should match water_depth (both sit on seafloor)
        operation_type = getattr(station, "operation_type", None)
        if operation_type == "mooring":
            operation_depth = getattr(station, "operation_depth", None)
            water_depth = getattr(station, "water_depth", None) or getattr(
                station, "depth", None
            )

            if operation_depth is not None and water_depth is not None:
                # For moorings, operation_depth and water_depth should be very close
                diff_percent = abs(operation_depth - water_depth) / water_depth * 100

                if diff_percent > tolerance:
                    warning_msg = (
                        f"Station {station_name} (mooring): operation_depth and water_depth mismatch of "
                        f"{diff_percent:.1f}% (operation: {operation_depth:.0f}m, water: {water_depth:.0f}m). "
                        f"Moorings should sit on the seafloor - these depths should match closely."
                    )
                    warning_messages.append(warning_msg)
            elif operation_depth is not None and water_depth is None:
                warning_msg = (
                    f"Station {station_name} (mooring): has operation_depth ({operation_depth:.0f}m) "
                    f"but missing water_depth. Moorings need both depths to verify seafloor placement."
                )
                warning_messages.append(warning_msg)

    return stations_checked, warning_messages


def check_duplicate_names(cruise) -> Tuple[List[str], List[str]]:
    """
    Check for duplicate names across different configuration sections.

    Parameters
    ----------
    cruise : Any
        Loaded cruise configuration object.

    Returns
    -------
    Tuple[List[str], List[str]]
        Tuple of (errors, warnings) for duplicate detection.
    """
    errors = []
    warnings = []

    # Check for duplicate station names - use raw config to catch duplicates
    # that were silently overwritten during station_registry creation
    if hasattr(cruise.config, "stations") and cruise.config.stations:
        station_names = [station.name for station in cruise.config.stations]
        if len(station_names) != len(set(station_names)):
            duplicates = [
                name for name in station_names if station_names.count(name) > 1
            ]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = station_names.count(dup_name)
                errors.append(
                    f"Duplicate station name '{dup_name}' found {count} times - station names must be unique"
                )

    # Check for duplicate leg names (if cruise has legs)
    if hasattr(cruise.config, "legs") and cruise.config.legs:
        leg_names = [leg.name for leg in cruise.config.legs]
        if len(leg_names) != len(set(leg_names)):
            duplicates = [name for name in leg_names if leg_names.count(name) > 1]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = leg_names.count(dup_name)
                errors.append(
                    f"Duplicate leg name '{dup_name}' found {count} times - leg names must be unique"
                )

    # Check for duplicate section names (if cruise has sections)
    if hasattr(cruise.config, "sections") and cruise.config.sections:
        section_names = [section.name for section in cruise.config.sections]
        if len(section_names) != len(set(section_names)):
            duplicates = [
                name for name in section_names if section_names.count(name) > 1
            ]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = section_names.count(dup_name)
                errors.append(
                    f"Duplicate section name '{dup_name}' found {count} times - section names must be unique"
                )

    # Check for duplicate mooring names (if cruise has moorings)
    if hasattr(cruise.config, "moorings") and cruise.config.moorings:
        mooring_names = [mooring.name for mooring in cruise.config.moorings]
        if len(mooring_names) != len(set(mooring_names)):
            duplicates = [
                name for name in mooring_names if mooring_names.count(name) > 1
            ]
            unique_duplicates = list(set(duplicates))
            for dup_name in unique_duplicates:
                count = mooring_names.count(dup_name)
                errors.append(
                    f"Duplicate mooring name '{dup_name}' found {count} times - mooring names must be unique"
                )

    return errors, warnings


def check_complete_duplicates(cruise) -> Tuple[List[str], List[str]]:
    """
    Check for completely identical entries (same name, position, operation, etc.).

    Parameters
    ----------
    cruise : Any
        Loaded cruise configuration object.

    Returns
    -------
    Tuple[List[str], List[str]]
        Tuple of (errors, warnings) for complete duplicate detection.
    """
    errors = []
    warnings = []
    warned_pairs = set()  # Track warned pairs to avoid duplicates

    # Check for complete duplicate stations
    if hasattr(cruise.config, "stations") and cruise.config.stations:
        stations = cruise.config.stations
        for i, station1 in enumerate(stations):
            for j, station2 in enumerate(stations[i + 1 :], i + 1):
                # Check if all key attributes are identical
                if (
                    station1.name
                    != station2.name  # Don't compare same names (handled above)
                    and getattr(station1.position, "latitude", None)
                    == getattr(station2.position, "latitude", None)
                    and getattr(station1.position, "longitude", None)
                    == getattr(station2.position, "longitude", None)
                    and getattr(station1, "operation_type", None)
                    == getattr(station2, "operation_type", None)
                    and getattr(station1, "action", None)
                    == getattr(station2, "action", None)
                ):

                    # Create a sorted pair to avoid duplicate warnings for same stations
                    pair = tuple(sorted([station1.name, station2.name]))
                    if pair not in warned_pairs:
                        warned_pairs.add(pair)
                        warnings.append(
                            f"Potentially duplicate stations '{station1.name}' and '{station2.name}' "
                            f"have identical coordinates and operations"
                        )

    return errors, warnings
