import logging
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cruiseplan.utils.constants import (
    DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY,
    DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS,
    DEFAULT_MOORING_DURATION_MIN,
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
    DEFAULT_VESSEL_SPEED_KT,
)
from cruiseplan.utils.coordinates import format_dmm_comment
from cruiseplan.utils.global_ports import resolve_port_reference

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
    coordinates_dmm: Optional[str] = Field(
        None, description="Degrees decimal minutes coordinate string"
    )

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

    @model_validator(mode="before")
    @classmethod
    def reject_deprecated_depth_field(cls, values):
        """
        Reject usage of the deprecated 'depth' field.

        The 'depth' field has been removed in favor of semantically clear
        'operation_depth' and 'water_depth' fields to prevent data confusion.

        Raises
        ------
        ValueError
            If the deprecated 'depth' field is found in the input.
        """
        if isinstance(values, dict) and "depth" in values:
            raise ValueError(
                f"The 'depth' field is no longer supported. Please use:\n"
                f"  - 'operation_depth': Target operation depth (e.g., CTD cast depth)\n"
                f"  - 'water_depth': Water depth at location (seafloor depth)\n"
                f"For CTD operations, these may be different values.\n"
                f"Migration guide: If you had 'depth: {values['depth']}' and it represents:\n"
                f"  • CTD cast depth: use 'operation_depth: {values['depth']}'\n"
                f"  • Seafloor depth: use 'water_depth: {values['depth']}'\n"
                f"  • Both (full water column): use both fields with the same value"
            )
        return values

    @model_validator(mode="after")
    def validate_depth_fields(self):
        """
        Validate depth field relationships and set defaults.

        Returns
        -------
        StationDefinition
            Self for chaining.
        """
        if self.operation_depth is None and self.water_depth is not None:
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


class PortDefinition(BaseModel):
    """
    Definition of a port for departure/arrival points in cruise legs.

    Represents a geographic port location where vessels can depart from or
    arrive at during multi-leg expeditions. Ports serve as boundaries between
    cruise legs in maritime terminology.

    Parameters
    ----------
    name : str
        Unique port identifier.
    latitude : float
        Port latitude in decimal degrees (-90 to 90).
    longitude : float
        Port longitude in decimal degrees (-180 to 180).
    timezone : str, optional
        Port timezone identifier (e.g., 'GMT+0', 'UTC-5'), by default None.
    description : str, optional
        Human-readable port description, by default None.

    Examples
    --------
    >>> port = PortDefinition(
    ...     name="REYKJAVIK",
    ...     latitude=64.1466,
    ...     longitude=-21.9426,
    ...     timezone="GMT+0",
    ...     description="Capital port of Iceland"
    ... )
    """

    name: str = Field(..., description="Unique port identifier")
    display_name: Optional[str] = Field(
        None, description="Human-readable port name for display purposes"
    )
    latitude: float = Field(
        ..., ge=-90.0, le=90.0, description="Port latitude in decimal degrees"
    )
    longitude: float = Field(
        ..., ge=-180.0, le=180.0, description="Port longitude in decimal degrees"
    )
    timezone: Optional[str] = Field(
        None, description="Port timezone (e.g., 'GMT+0', 'UTC-5')"
    )
    description: Optional[str] = Field(
        None, description="Human-readable port description"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate port name is non-empty and contains valid characters.

        Parameters
        ----------
        v : str
            Port name to validate.

        Returns
        -------
        str
            Validated port name.

        Raises
        ------
        ValueError
            If port name is empty or contains invalid characters.
        """
        if not v or not v.strip():
            raise ValueError("Port name cannot be empty")
        return v.strip()


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
    Definition of a cluster for operation boundary management.

    Clusters define boundaries for operation shuffling/reordering during scheduling.
    Operations within a cluster can be reordered according to the cluster's strategy,
    but cannot be mixed with operations from other clusters or the parent leg.

    Attributes
    ----------
    name : str
        Unique identifier for the cluster.
    description : Optional[str]
        Human-readable description of the cluster purpose.
    strategy : StrategyEnum
        Scheduling strategy for the cluster (default: SEQUENTIAL).
    ordered : bool
        Whether operations should maintain their order (default: True).
    activities : List[dict]
        Unified list of all activities (stations, transits, areas) in this cluster.
    sequence : Optional[List[Union[str, StationDefinition, TransitDefinition]]]
        DEPRECATED: Ordered sequence of operations. Use 'activities' instead.
    stations : Optional[List[Union[str, StationDefinition]]]
        DEPRECATED: List of stations in the cluster. Use 'activities' instead.
    generate_transect : Optional[GenerateTransect]
        DEPRECATED: Transect generation parameters. Use 'activities' instead.
    """

    name: str
    description: Optional[str] = Field(
        None, description="Human-readable description of the cluster purpose"
    )
    strategy: StrategyEnum = Field(
        default=StrategyEnum.SEQUENTIAL,
        description="Scheduling strategy for operations within this cluster",
    )
    ordered: bool = Field(
        default=True,
        description="Whether operations should maintain their defined order",
    )

    # New activities-based architecture
    activities: List[Union[str, dict]] = Field(
        default_factory=list,
        description="Unified list of all activities in this cluster (can be string references or dict objects)",
    )

    # Deprecated fields (maintain temporarily for backward compatibility)
    sequence: Optional[List[Union[str, StationDefinition, TransitDefinition]]] = Field(
        default=None, description="DEPRECATED: Use 'activities' instead"
    )
    stations: Optional[List[Union[str, StationDefinition]]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )
    generate_transect: Optional[GenerateTransect] = Field(
        default=None, description="DEPRECATED: Use 'activities' instead"
    )

    @field_validator("name")
    def validate_name_not_empty(cls, v):
        """
        Validate cluster name is not empty.

        Parameters
        ----------
        v : str
            Cluster name to validate.

        Returns
        -------
        str
            Validated cluster name.

        Raises
        ------
        ValueError
            If name is empty.
        """
        if not v or not v.strip():
            raise ValueError("Cluster name cannot be empty")
        return v.strip()

    @field_validator("activities")
    def validate_activities_structure(cls, v):
        """
        Validate activities list structure and content.

        Parameters
        ----------
        v : List[Union[str, dict]]
            Activities list to validate (string references or dictionary objects).

        Returns
        -------
        List[Union[str, dict]]
            Validated activities list.

        Raises
        ------
        ValueError
            If activities contain invalid structure.
        """
        if not isinstance(v, list):
            raise ValueError("Activities must be a list")

        activity_names = []
        for i, activity in enumerate(v):
            if isinstance(activity, str):
                # String reference - validate it's not empty
                if not activity or not activity.strip():
                    raise ValueError(f"Activity {i} string reference cannot be empty")
                activity_names.append(activity.strip())
            elif isinstance(activity, dict):
                # Dictionary object - validate structure
                if "name" not in activity:
                    raise ValueError(f"Activity {i} must have a 'name' field")
                if not activity["name"] or not str(activity["name"]).strip():
                    raise ValueError(f"Activity {i} name cannot be empty")
                activity_names.append(str(activity["name"]).strip())
            else:
                raise ValueError(
                    f"Activity {i} must be either a string reference or a dictionary"
                )

        # Check for duplicate names within cluster and issue warnings
        import warnings

        duplicates = set(
            [name for name in activity_names if activity_names.count(name) > 1]
        )
        if duplicates:
            warnings.warn(
                f"⚠️ Duplicate activity names in cluster: {', '.join(duplicates)}. "
                f"These activities will be executed multiple times as specified.",
                UserWarning,
                stacklevel=2,
            )

        return v

    @model_validator(mode="after")
    def validate_cluster_consistency(self):
        """
        Validate cluster-level consistency rules.

        Returns
        -------
        ClusterDefinition
            Validated cluster definition.

        Raises
        ------
        ValueError
            If validation constraints are violated.
        """
        # Warn about deprecated field usage
        deprecated_fields = []
        if self.sequence is not None:
            deprecated_fields.append("sequence")
        if self.stations:
            deprecated_fields.append("stations")
        if self.generate_transect is not None:
            deprecated_fields.append("generate_transect")

        if deprecated_fields:
            import warnings

            warnings.warn(
                f"Cluster '{self.name}' uses deprecated fields: {', '.join(deprecated_fields)}. "
                "Use 'activities' field instead for future compatibility.",
                DeprecationWarning,
                stacklevel=2,
            )

        return self


class LegDefinition(BaseModel):
    """
    Definition of a maritime cruise leg (port-to-port segment).

    Represents a complete leg of the cruise from departure port to arrival port,
    containing all operations and clusters that occur during this segment.
    Maritime legs are always port-to-port with defined departure and arrival points.

    Attributes
    ----------
    name : str
        Unique identifier for the leg.
    description : Optional[str]
        Human-readable description of the leg.
    departure_port : Union[str, PortDefinition]
        Required departure port for this leg.
    arrival_port : Union[str, PortDefinition]
        Required arrival port for this leg.
    vessel_speed : Optional[float]
        Vessel speed for this leg in knots (inheritable from cruise).
    distance_between_stations : Optional[float]
        Default station spacing for this leg in kilometers (inheritable from cruise).
    turnaround_time : Optional[float]
        Turnaround time between operations in minutes (inheritable from cruise).
    first_waypoint : Optional[str]
        First waypoint/navigation marker for this leg (routing only, not executed).
    last_waypoint : Optional[str]
        Last waypoint/navigation marker for this leg (routing only, not executed).
    strategy : Optional[StrategyEnum]
        Default scheduling strategy for the leg.
    ordered : Optional[bool]
        Whether the leg operations should be ordered.
    buffer_time : Optional[float]
        Contingency time for entire leg operations in minutes (e.g., weather delays).
    activities : Optional[List[dict]]
        Unified list of all activities (stations, transits, areas) in this leg.
    clusters : Optional[List[ClusterDefinition]]
        List of operation clusters in the leg.
    stations : Optional[List[Union[str, StationDefinition]]]
        DEPRECATED: List of stations in the leg. Use 'activities' instead.
    sections : Optional[List[SectionDefinition]]
        DEPRECATED: List of sections in the leg. Use 'activities' instead.
    sequence : Optional[List[Union[str, StationDefinition]]]
        DEPRECATED: Ordered sequence of operations. Use 'activities' instead.
    """

    name: str
    description: Optional[str] = None

    # Required maritime port-to-port structure
    departure_port: Union[str, PortDefinition] = Field(
        ..., description="Required departure port for this leg"
    )
    arrival_port: Union[str, PortDefinition] = Field(
        ..., description="Required arrival port for this leg"
    )

    # Parameter inheritance from cruise level
    vessel_speed: Optional[float] = Field(
        None, gt=0, description="Vessel speed for this leg in knots"
    )
    distance_between_stations: Optional[float] = Field(
        None, gt=0, description="Default station spacing for this leg in kilometers"
    )
    turnaround_time: Optional[float] = Field(
        None, ge=0, description="Turnaround time between operations in minutes"
    )

    # Waypoint boundary management for routing
    first_waypoint: Optional[str] = Field(
        None,
        description="First waypoint/navigation marker for this leg (used for routing only, not execution)",
    )
    last_waypoint: Optional[str] = Field(
        None,
        description="Last waypoint/navigation marker for this leg (used for routing only, not execution)",
    )

    # Scheduling and organization
    strategy: Optional[StrategyEnum] = None
    ordered: Optional[bool] = None
    buffer_time: Optional[float] = Field(
        None, ge=0, description="Contingency time for entire leg operations in minutes"
    )

    # New activities-based architecture
    activities: Optional[List[Union[str, dict]]] = Field(
        default_factory=list,
        description="Unified list of all activities in this leg (can be string references or dict objects)",
    )
    clusters: Optional[List[ClusterDefinition]] = Field(
        default_factory=list, description="List of operation clusters in the leg"
    )

    # Deprecated fields (maintain temporarily for backward compatibility)
    stations: Optional[List[Union[str, StationDefinition]]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )
    sections: Optional[List[SectionDefinition]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )
    sequence: Optional[List[Union[str, StationDefinition]]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )

    @field_validator("departure_port", "arrival_port")
    def validate_ports_required_maritime(cls, v):
        """
        Validate port fields to ensure maritime terminology compliance.

        Maritime legs MUST have both departure_port and arrival_port defined.
        Accepts global port references (e.g., 'port_reykjavik'), PortDefinition
        objects, or port dictionaries. Global port references are resolved later
        in the Cruise initialization process.

        Parameters
        ----------
        v : Union[str, PortDefinition, dict]
            Port value to validate.

        Returns
        -------
        Union[str, PortDefinition, dict]
            Validated port value.

        Raises
        ------
        ValueError
            If port is None, empty string, or invalid reference.
        """
        # Handle None values
        if v is None:
            raise ValueError(
                "Port cannot be None. Maritime terminology requires all legs to be "
                "port-to-port segments with valid departure and arrival ports."
            )

        # Handle string references (including global port references)
        if isinstance(v, str):
            if not v.strip():
                raise ValueError(
                    "Port names cannot be empty. Maritime legs require both "
                    "departure_port and arrival_port following nautical conventions."
                )
            # Allow global port references like 'port_reykjavik'
            # These will be resolved during Cruise initialization
            return v

        # Handle PortDefinition objects directly
        if isinstance(v, PortDefinition):
            return v

        # Handle dictionary format ports
        if isinstance(v, dict):
            # Basic validation that required fields are present
            required_fields = {"name", "latitude", "longitude"}
            if not required_fields.issubset(v.keys()):
                missing = required_fields - v.keys()
                raise ValueError(
                    f"Port dictionary missing required fields: {missing}. "
                    f"Required: {required_fields}"
                )
            return v

        # Invalid type
        raise ValueError(
            f"Port must be a string reference, PortDefinition object, or dictionary. "
            f"Got {type(v).__name__}"
        )

        return v

    @field_validator("first_waypoint", "last_waypoint")
    def validate_station_names(cls, v):
        """
        Validate station name fields to ensure they are not empty strings.

        Parameters
        ----------
        v : Optional[str]
            Station name to validate.

        Returns
        -------
        Optional[str]
            Validated station name.

        Raises
        ------
        ValueError
            If station name is an empty string.
        """
        if v is not None and isinstance(v, str) and not v.strip():
            raise ValueError("Station names cannot be empty")
        return v

    @field_validator(
        "buffer_time", "vessel_speed", "distance_between_stations", "turnaround_time"
    )
    def validate_positive_values(cls, v, info):
        """
        Validate numeric fields to ensure they are positive or non-negative as appropriate.

        Parameters
        ----------
        v : Optional[float]
            Numeric value to validate.
        info : FieldValidationInfo
            Field validation context.

        Returns
        -------
        Optional[float]
            Validated numeric value.

        Raises
        ------
        ValueError
            If value constraints are violated.
        """
        if v is None:
            return v

        field_name = info.field_name
        if field_name in ("buffer_time", "turnaround_time") and v < 0:
            raise ValueError(f"{field_name} cannot be negative")
        elif field_name in ("vessel_speed", "distance_between_stations") and v <= 0:
            raise ValueError(f"{field_name} must be positive")
        return v

    @model_validator(mode="after")
    def validate_leg_consistency(self):
        """
        Validate leg-level consistency rules.

        Returns
        -------
        LegDefinition
            Validated leg definition.

        Raises
        ------
        ValueError
            If validation constraints are violated.
        """
        # Note: Round-trip cruises (same departure/arrival port) are valid maritime operations

        # Note: Waypoints (first_waypoint/last_waypoint) are used only for routing
        # They are NOT required to exist in the activities list since they serve
        # as navigation markers, not execution targets

        return self


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
    stations : Optional[List[StationDefinition]]
        List of station definitions.
    transits : Optional[List[TransitDefinition]]
        List of transit definitions.
    areas : Optional[List[AreaDefinition]]
        List of area definitions.
    ports : Optional[List[PortDefinition]]
        List of port definitions.
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

    departure_port: Optional[Union[str, PortDefinition]] = Field(
        None,
        description="Port where the cruise begins (can be global port reference). Optional for multi-leg cruises.",
    )
    arrival_port: Optional[Union[str, PortDefinition]] = Field(
        None,
        description="Port where the cruise ends (can be global port reference). Optional for multi-leg cruises.",
    )

    stations: Optional[List[StationDefinition]] = []
    transits: Optional[List[TransitDefinition]] = []
    areas: Optional[List[AreaDefinition]] = []
    ports: Optional[List[PortDefinition]] = []
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

    @field_validator("departure_port", "arrival_port")
    def validate_cruise_ports(cls, v):
        """
        Validate port fields at cruise level to support global port references.

        Accepts global port references (e.g., 'port_reykjavik'), PortDefinition
        objects, or port dictionaries. Global port references are resolved during
        Cruise initialization.

        Parameters
        ----------
        v : Union[str, PortDefinition, dict]
            Port value to validate.

        Returns
        -------
        Union[str, PortDefinition, dict]
            Validated port value.

        Raises
        ------
        ValueError
            If port is None, empty string, or invalid reference.
        """
        # Handle None values
        if v is None:
            raise ValueError(
                "Cruise port cannot be None. Maritime cruises require "
                "departure and arrival ports."
            )

        # Handle string references (including global port references)
        if isinstance(v, str):
            if not v.strip():
                raise ValueError(
                    "Cruise port names cannot be empty. Specify a valid port "
                    "reference or PortDefinition."
                )
            # Allow global port references like 'port_reykjavik'
            # These will be resolved during Cruise initialization
            return v

        # Handle PortDefinition objects directly
        if isinstance(v, PortDefinition):
            return v

        # Handle dictionary format ports
        if isinstance(v, dict):
            # Basic validation that required fields are present
            required_fields = {"name", "latitude", "longitude"}
            if not required_fields.issubset(v.keys()):
                missing = required_fields - v.keys()
                raise ValueError(
                    f"Cruise port dictionary missing required fields: {missing}. "
                    f"Required: {required_fields}"
                )
            return v

        # Invalid type
        raise ValueError(
            f"Cruise port must be a string reference, PortDefinition object, or dictionary. "
            f"Got {type(v).__name__}"
        )

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
    def validate_no_global_leg_fields(self):
        """
        Validate that departure_port and arrival_port are not defined at cruise level.

        These fields must now be defined only at the leg level to avoid conflicts
        during section expansion and multi-leg cruise processing.

        Returns
        -------
        CruiseConfig
            Self for chaining.

        Raises
        ------
        ValueError
            If departure_port or arrival_port are defined at the cruise level.
        """
        global_fields_errors = []

        if self.departure_port is not None:
            global_fields_errors.append("departure_port")

        if self.arrival_port is not None:
            global_fields_errors.append("arrival_port")

        if global_fields_errors:
            fields_str = ", ".join(global_fields_errors)
            raise ValueError(
                f"Global cruise-level fields no longer supported: {fields_str}. "
                f"These fields must be defined within individual leg definitions to "
                f"avoid conflicts during section expansion and multi-leg processing. "
                f"Please move these fields into the 'legs' section of your configuration."
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
            # Handle both string references and PortDefinition objects
            if isinstance(self.departure_port, str):
                # Skip string references - they'll be resolved later
                pass
            else:
                lons.append(self.departure_port.longitude)
        if self.arrival_port:
            # Handle both string references and PortDefinition objects
            if isinstance(self.arrival_port, str):
                # Skip string references - they'll be resolved later
                pass
            else:
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

    @model_validator(mode="after")
    def validate_cruise_leg_consistency(self):
        """
        Validate consistency between cruise-level and leg-level definitions.

        For single-leg cruises: RECOMMEND cruise-level fields
        For multi-leg cruises: ALLOW leg-level only, but validate consistency if both present

        Returns
        -------
        CruiseConfig
            Self for chaining.

        Raises
        ------
        ValueError
            If cruise-level and leg-level definitions conflict.
        """
        if not self.legs:
            raise ValueError("At least one leg must be defined")

        is_single_leg = len(self.legs) == 1
        first_leg = self.legs[0]
        last_leg = self.legs[-1]

        # Check if we have any cruise-level definitions
        has_cruise_departure = self.departure_port is not None
        has_cruise_arrival = self.arrival_port is not None

        # For single-leg cruises, derive missing cruise-level fields from leg
        if is_single_leg:
            if (
                not has_cruise_departure
                and hasattr(first_leg, "departure_port")
                and first_leg.departure_port
            ):
                self.departure_port = first_leg.departure_port
            if (
                not has_cruise_arrival
                and hasattr(first_leg, "arrival_port")
                and first_leg.arrival_port
            ):
                self.arrival_port = first_leg.arrival_port

        # Validate consistency if both cruise-level and leg-level are present
        if (
            has_cruise_departure
            and hasattr(first_leg, "departure_port")
            and first_leg.departure_port
        ):
            if str(self.departure_port) != str(first_leg.departure_port):
                raise ValueError(
                    f"Cruise departure_port '{self.departure_port}' conflicts with first leg departure_port '{first_leg.departure_port}'"
                )

        if (
            has_cruise_arrival
            and hasattr(last_leg, "arrival_port")
            and last_leg.arrival_port
        ):
            if str(self.arrival_port) != str(last_leg.arrival_port):
                raise ValueError(
                    f"Cruise arrival_port '{self.arrival_port}' conflicts with last leg arrival_port '{last_leg.arrival_port}'"
                )

        # For multi-leg cruises, just ensure each leg has required fields
        for i, leg in enumerate(self.legs):
            if not hasattr(leg, "departure_port") or not leg.departure_port:
                raise ValueError(f"Leg {i+1} ('{leg.name}') must define departure_port")
            if not hasattr(leg, "arrival_port") or not leg.arrival_port:
                raise ValueError(f"Leg {i+1} ('{leg.name}') must define arrival_port")

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
                # Create appropriate list type based on config type
                if hasattr(config, "copy"):  # CommentedMap
                    from ruamel.yaml.comments import CommentedSeq

                    config["stations"] = CommentedSeq()
                else:
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

                # Convert station to CommentedMap if needed for comment support
                if hasattr(config, "copy"):  # CommentedMap config
                    from ruamel.yaml.comments import CommentedMap

                    if not isinstance(station, CommentedMap):
                        commented_station = CommentedMap(station)
                        station = commented_station

                config["stations"].append(station)

                # Add expansion comment if config supports it (ruamel.yaml CommentedMap)
                if hasattr(config["stations"], "yaml_add_eol_comment"):
                    station_index = len(config["stations"]) - 1
                    config["stations"].yaml_add_eol_comment(
                        " expanded by cruiseplan enrich --expand-sections",
                        station_index,
                    )

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

    # Update leg waypoint references
    for leg in config.get("legs", []):
        # Check leg-level waypoint fields (first_waypoint and last_waypoint)
        if leg.get("first_waypoint") and leg["first_waypoint"] in expanded_stations:
            # Use the first station from the expansion
            leg["first_waypoint"] = expanded_stations[leg["first_waypoint"]][0]
            logger.info(f"Updated leg first_waypoint to {leg['first_waypoint']}")

        if leg.get("last_waypoint") and leg["last_waypoint"] in expanded_stations:
            # Use the last station from the expansion
            leg["last_waypoint"] = expanded_stations[leg["last_waypoint"]][-1]
            logger.info(f"Updated leg last_waypoint to {leg['last_waypoint']}")

        # Check direct stations in leg
        if leg.get("stations"):
            new_stations = []
            for item in leg["stations"]:
                if isinstance(item, str) and item in expanded_stations:
                    new_stations.extend(expanded_stations[item])
                else:
                    new_stations.append(item)
            leg["stations"] = new_stations

        # Check activities list
        if leg.get("activities"):
            new_activities = []
            for item in leg["activities"]:
                if isinstance(item, str) and item in expanded_stations:
                    new_activities.extend(expanded_stations[item])
                    logger.info(
                        f"Expanded activities list: {item} → {expanded_stations[item]}"
                    )
                else:
                    new_activities.append(item)
            leg["activities"] = new_activities

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


def add_missing_required_fields(
    config_dict: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Add missing required fields with sensible defaults and provide user feedback.

    Inserts missing fields at the top of the configuration after cruise_name with
    appropriate comments indicating they were added by enrichment.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary loaded from YAML

    Returns
    -------
    Tuple[Dict[str, Any], List[str]]
        Updated configuration dictionary and list of fields that were added
    """
    from ruamel.yaml.comments import CommentedMap

    defaults_added = []

    # Check which fields need to be added
    fields_to_add = []

    if "default_vessel_speed" not in config_dict:
        fields_to_add.append(
            (
                "default_vessel_speed",
                DEFAULT_VESSEL_SPEED_KT,
                f"{DEFAULT_VESSEL_SPEED_KT} knots",
            )
        )
        defaults_added.append(f"default_vessel_speed = {DEFAULT_VESSEL_SPEED_KT}")
        logger.warning(
            f"⚠️ Added missing field: default_vessel_speed = {DEFAULT_VESSEL_SPEED_KT} knots"
        )

    if "calculate_transfer_between_sections" not in config_dict:
        fields_to_add.append(
            (
                "calculate_transfer_between_sections",
                DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS,
                str(DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS),
            )
        )
        defaults_added.append(
            f"calculate_transfer_between_sections = {DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS}"
        )
        logger.warning(
            f"⚠️ Added missing field: calculate_transfer_between_sections = {DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS}"
        )

    if "calculate_depth_via_bathymetry" not in config_dict:
        fields_to_add.append(
            (
                "calculate_depth_via_bathymetry",
                DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY,
                str(DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY),
            )
        )
        defaults_added.append(
            f"calculate_depth_via_bathymetry = {DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY}"
        )
        logger.warning(
            f"⚠️ Added missing field: calculate_depth_via_bathymetry = {DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY}"
        )

    if "default_distance_between_stations" not in config_dict:
        fields_to_add.append(
            (
                "default_distance_between_stations",
                DEFAULT_STATION_SPACING_KM,
                f"{DEFAULT_STATION_SPACING_KM} km",
            )
        )
        defaults_added.append(
            f"default_distance_between_stations = {DEFAULT_STATION_SPACING_KM}"
        )
        logger.warning(
            f"⚠️ Added missing field: default_distance_between_stations = {DEFAULT_STATION_SPACING_KM} km"
        )

    if "start_date" not in config_dict:
        fields_to_add.append(
            ("start_date", DEFAULT_START_DATE, f"'{DEFAULT_START_DATE}' (placeholder)")
        )
        defaults_added.append(f"start_date = '{DEFAULT_START_DATE}'")
        logger.warning(
            f"⚠️ Added missing field: start_date = '{DEFAULT_START_DATE}' (placeholder)"
        )

    # If we have fields to add, insert them properly at the top
    if fields_to_add:
        # Convert to CommentedMap if it isn't already
        if not isinstance(config_dict, CommentedMap):
            new_config = CommentedMap(config_dict)
            config_dict = new_config

        # Get current keys and find where to insert (after cruise_name)
        keys = list(config_dict.keys())
        insert_index = 1 if "cruise_name" in keys else 0

        # Insert fields in reverse order so they appear in correct sequence
        for field_name, field_value, comment_text in reversed(fields_to_add):
            # Use the correct CommentedMap.insert() method signature
            config_dict.insert(insert_index, field_name, field_value)

            # Add comment indicating this was added by enrichment
            config_dict.yaml_add_eol_comment(
                "# default added by cruiseplan enrich", field_name
            )

        logger.info(
            "ℹ️ Missing required fields added with defaults. Update these values as needed."
        )

    return config_dict, defaults_added


def add_missing_station_defaults(config_dict: Dict[str, Any]) -> int:
    """
    Add missing defaults to station definitions.

    Adds default duration to mooring operations that lack this field.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary loaded from YAML

    Returns
    -------
    int
        Number of station defaults added
    """
    from ruamel.yaml.comments import CommentedMap

    station_defaults_added = 0

    # Process stations for missing defaults
    if "stations" in config_dict:
        for station_data in config_dict["stations"]:
            # Check for mooring operations without duration
            if (
                station_data.get("operation_type") == "mooring"
                and "duration" not in station_data
            ):
                station_name = station_data.get("name", "unnamed")

                # Add default mooring duration
                if isinstance(station_data, CommentedMap):
                    # Find appropriate position to insert duration (after operation_type if present)
                    keys = list(station_data.keys())
                    insert_index = len(keys)  # Default to end

                    if "operation_type" in keys:
                        insert_index = keys.index("operation_type") + 1
                    elif "name" in keys:
                        insert_index = keys.index("name") + 1

                    station_data.insert(
                        insert_index, "duration", DEFAULT_MOORING_DURATION_MIN
                    )
                    station_data.yaml_add_eol_comment(
                        "# default added by cruiseplan enrich", "duration"
                    )
                else:
                    # Fallback for regular dict
                    station_data["duration"] = DEFAULT_MOORING_DURATION_MIN

                station_defaults_added += 1
                logger.warning(
                    f"⚠️ Added missing mooring duration to station '{station_name}': {DEFAULT_MOORING_DURATION_MIN} minutes (999 hours)"
                )

    # Process moorings for missing defaults (if moorings section exists)
    if "moorings" in config_dict:
        for mooring_data in config_dict["moorings"]:
            # Check for mooring definitions without duration
            if "duration" not in mooring_data:
                mooring_name = mooring_data.get("name", "unnamed")

                # Add default mooring duration
                if isinstance(mooring_data, CommentedMap):
                    # Find appropriate position to insert duration
                    keys = list(mooring_data.keys())
                    insert_index = len(keys)  # Default to end

                    if "name" in keys:
                        insert_index = keys.index("name") + 1

                    mooring_data.insert(
                        insert_index, "duration", DEFAULT_MOORING_DURATION_MIN
                    )
                    mooring_data.yaml_add_eol_comment(
                        "# default added by cruiseplan enrich", "duration"
                    )
                else:
                    # Fallback for regular dict
                    mooring_data["duration"] = DEFAULT_MOORING_DURATION_MIN

                station_defaults_added += 1
                logger.warning(
                    f"⚠️ Added missing mooring duration to mooring '{mooring_name}': {DEFAULT_MOORING_DURATION_MIN} minutes (999 hours)"
                )

    return station_defaults_added


def enrich_configuration(
    config_path: Path,
    add_depths: bool = False,
    add_coords: bool = False,
    expand_sections: bool = False,
    expand_ports: bool = False,
    bathymetry_source: str = "etopo2022",
    bathymetry_dir: str = "data",
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
    expand_ports : bool, optional
        Whether to expand global port references into full PortDefinition objects (default: False).
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

    # Add missing required fields with sensible defaults
    config_dict, defaults_added = add_missing_required_fields(config_dict)

    # Add missing station-level defaults (e.g., mooring durations)
    station_defaults_added = add_missing_station_defaults(config_dict)

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
        "ports_expanded": 0,
        "defaults_added": len(defaults_added),
        "station_defaults_added": station_defaults_added,
        "defaults_list": defaults_added,
        "total_stations_processed": len(cruise.station_registry),
    }

    # Initialize managers if needed
    if add_depths:
        bathymetry = BathymetryManager(
            source=bathymetry_source, data_dir=bathymetry_dir
        )

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

    # Expand global port references to ports catalog if requested
    if expand_ports:
        ports_expanded_count = 0

        # Create ports catalog section if it doesn't exist
        if "ports" not in config_dict:
            config_dict["ports"] = []

        # Track which ports we've already added to avoid duplicates
        existing_port_names = {port.get("name", "") for port in config_dict["ports"]}

        # Collect all port references from cruise-level and leg-level
        port_references = set()

        # Check cruise-level ports
        for port_field in ["departure_port", "arrival_port"]:
            if port_field in config_dict and isinstance(config_dict[port_field], str):
                port_ref = config_dict[port_field]
                if port_ref.startswith("port_"):
                    port_references.add(port_ref)

        # Check leg-level ports
        if "legs" in config_dict:
            for leg_data in config_dict["legs"]:
                for port_field in ["departure_port", "arrival_port"]:
                    if port_field in leg_data and isinstance(leg_data[port_field], str):
                        port_ref = leg_data[port_field]
                        if port_ref.startswith("port_"):
                            port_references.add(port_ref)

        # Resolve each unique port reference and add to catalog
        for port_ref in port_references:
            if port_ref not in existing_port_names:
                try:
                    port_definition = resolve_port_reference(port_ref)
                    # Add to ports catalog with display_name from global registry
                    catalog_port = {
                        "name": port_ref,  # Keep the full port_* name as catalog identifier
                        "latitude": port_definition.latitude,
                        "longitude": port_definition.longitude,
                        "position": {
                            "latitude": port_definition.latitude,
                            "longitude": port_definition.longitude,
                        },
                    }
                    # Add display_name if available
                    if hasattr(port_definition, "display_name"):
                        catalog_port["display_name"] = port_definition.display_name
                    elif hasattr(port_definition, "name"):
                        catalog_port["display_name"] = port_definition.name

                    config_dict["ports"].append(catalog_port)
                    ports_expanded_count += 1
                    logger.debug(
                        f"Added port '{port_ref}' to catalog as '{catalog_port.get('display_name', port_ref)}'"
                    )
                except ValueError as e:
                    logger.warning(
                        f"Could not resolve port reference '{port_ref}': {e}"
                    )

        enrichment_summary["ports_expanded"] = ports_expanded_count

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
        + enrichment_summary["ports_expanded"]
        + enrichment_summary["defaults_added"]
        + enrichment_summary["station_defaults_added"]
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

    # Save enriched configuration if output path is specified (always save for testing purposes)
    if output_path:
        save_yaml_config(config_dict, output_path, backup=True)

    return enrichment_summary


def validate_configuration_file(
    config_path: Path,
    check_depths: bool = False,
    tolerance: float = 10.0,
    bathymetry_source: str = "etopo2022",
    bathymetry_dir: str = "data",
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
            bathymetry = BathymetryManager(
                source=bathymetry_source, data_dir=bathymetry_dir
            )
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
        # Load raw config first to help with error formatting
        raw_config = None
        try:
            from cruiseplan.utils.yaml_io import load_yaml_safe

            raw_config = load_yaml_safe(config_path)
        except Exception:
            # Best-effort: if we cannot load raw YAML, continue with basic error reporting
            pass

        for error in e.errors():
            # Enhanced location formatting with station names when possible
            location = _format_error_location(error["loc"], raw_config)
            message = error["msg"]
            errors.append(f"Schema error at {location}: {message}")

        # Still try to collect warnings even when validation fails
        try:

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


def _format_error_location(location_path: tuple, raw_config: dict) -> str:
    """
    Format error location path to be more user-friendly.

    Converts array indices to meaningful names when possible.
    E.g., "stations -> 0 -> position -> latitude" becomes
    "station 'Station_A' -> position -> latitude"
    """
    if not location_path:
        return "unknown"

    # Convert to list for easier manipulation
    path_parts = list(location_path)

    # Handle stations array indices
    if (
        len(path_parts) >= 2
        and path_parts[0] == "stations"
        and isinstance(path_parts[1], int)
    ):
        station_index = path_parts[1]
        station_name = None

        # Try to get station name from raw config
        if (
            raw_config
            and "stations" in raw_config
            and isinstance(raw_config["stations"], list)
            and 0 <= station_index < len(raw_config["stations"])
        ):

            station_data = raw_config["stations"][station_index]
            if isinstance(station_data, dict) and "name" in station_data:
                station_name = station_data["name"]

        # Replace index with descriptive text
        if station_name:
            path_parts[0] = f"station '{station_name}'"
            path_parts.pop(1)  # Remove the index
        else:
            path_parts[0] = f"station #{station_index + 1}"
            path_parts.pop(1)  # Remove the index

    # Handle other array indices (moorings, transits, etc.) similarly
    elif len(path_parts) >= 2 and isinstance(path_parts[1], int):
        array_name = path_parts[0]
        index = path_parts[1]

        # Try to get name from raw config
        item_name = None
        if (
            raw_config
            and array_name in raw_config
            and isinstance(raw_config[array_name], list)
            and 0 <= index < len(raw_config[array_name])
        ):

            item_data = raw_config[array_name][index]
            if isinstance(item_data, dict) and "name" in item_data:
                item_name = item_data["name"]

        # Replace with descriptive text
        if item_name:
            path_parts[0] = f"{array_name[:-1]} '{item_name}'"  # Remove 's' from plural
            path_parts.pop(1)  # Remove the index
        else:
            path_parts[0] = f"{array_name[:-1]} #{index + 1}"
            path_parts.pop(1)  # Remove the index

    return " -> ".join(str(part) for part in path_parts)


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
        # Check water_depth field (preferred for bathymetry comparison)
        water_depth = getattr(station, "water_depth", None)
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
