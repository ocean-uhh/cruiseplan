"""
Main cruise configuration and schedule organization models.

Defines the root CruiseConfig class and schedule organization models
(LegDefinition, ClusterDefinition) that represent the complete cruise
configuration file. This is the top-level YAML structure that contains
all cruise metadata, global catalog definitions, and schedule organization.
"""

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cruiseplan.schema.values import (
    DEFAULT_CTD_RATE_M_S,
    DEFAULT_DAY_END_HR,
    DEFAULT_DAY_START_HR,
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
    DEFAULT_VESSEL_SPEED_KT,
)

from .activities import AreaDefinition, LineDefinition, PointDefinition
from .values import StrategyEnum


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
    activities: list[Union[str, dict]] = Field(
        default_factory=list,
        description="Unified list of all activities in this cluster (can be string references or dict objects)",
    )

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_cluster_activities(self):
        """
        Validate cluster has activities and handle deprecated fields.

        Returns
        -------
        ClusterDefinition
            Validated cluster definition.

        Raises
        ------
        ValueError
            If cluster has no activities defined.
        """
        # Check for deprecated field usage and migrate to activities
        has_activities = bool(self.activities)

        if not has_activities:
            msg = f"Cluster '{self.name}' must have at least one activity"
            raise ValueError(msg)

        # Warning for deprecated usage would go here in production
        # (omitting to avoid import dependencies)

        return self

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v):
        """Ensure strategy is a valid StrategyEnum."""
        if isinstance(v, str):
            try:
                return StrategyEnum(v)
            except ValueError as exc:
                msg = f"Invalid strategy: {v}. Must be one of {list(StrategyEnum)}"
                raise ValueError(msg) from exc
        return v


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
    departure_port : Union[str, PointDefinition]
        Required departure port for this leg.
    arrival_port : Union[str, PointDefinition]
        Required arrival port for this leg.
    vessel_speed : Optional[float]
        Vessel speed for this leg in knots (inheritable from cruise).
    distance_between_stations : Optional[float]
        Default station spacing for this leg in kilometers (inheritable from cruise).
    turnaround_time : Optional[float]
        Turnaround time between operations in minutes (inheritable from cruise).
    first_activity : Optional[str]
        First activity/navigation marker for this leg (routing only, not executed).
    last_activity : Optional[str]
        Last activity/navigation marker for this leg (routing only, not executed).
    strategy : Optional[StrategyEnum]
        Default scheduling strategy for the leg.
    ordered : Optional[bool]
        Whether the leg operations should be ordered.
    buffer_time : Optional[float]
        Contingency time for entire leg operations in minutes (e.g., weather delays).
    activities : Optional[List[dict]]
        Unified list of all activities (points, lines, areas) in this leg.
    clusters : Optional[List[ClusterDefinition]]
        List of operation clusters in the leg.
    """

    name: str
    description: Optional[str] = None

    # Required maritime port-to-port structure
    departure_port: Union[str, PointDefinition]
    arrival_port: Union[str, PointDefinition]

    # Inheritable cruise parameters
    vessel_speed: Optional[float] = Field(
        None, description="Vessel speed for this leg in knots"
    )
    distance_between_stations: Optional[float] = Field(
        None, description="Default station spacing for this leg in kilometers"
    )
    turnaround_time: Optional[float] = Field(
        None, description="Turnaround time between operations in minutes"
    )

    # Navigation activities (not executed, routing only)
    first_activity: Optional[str] = Field(
        None, description="First navigation activity for this leg (routing only)"
    )
    last_activity: Optional[str] = Field(
        None, description="Last navigation activity for this leg (routing only)"
    )

    # Scheduling parameters
    strategy: Optional[StrategyEnum] = Field(
        None, description="Default scheduling strategy for this leg"
    )
    ordered: Optional[bool] = Field(
        None, description="Whether leg operations should maintain order"
    )
    buffer_time: Optional[float] = Field(
        None, description="Contingency time for weather delays (minutes)"
    )

    # Activity organization
    activities: Optional[list[Union[str, dict]]] = Field(
        default_factory=list,
        description="Unified list of all activities in this leg (can be string references or dict objects)",
    )
    clusters: Optional[list[ClusterDefinition]] = Field(
        default_factory=list, description="List of operation clusters"
    )

    model_config = ConfigDict(extra="allow")

    @field_validator("departure_port", "arrival_port")
    @classmethod
    def validate_ports(cls, v):
        """Validate port references are not None."""
        if v is None:
            msg = "Departure and arrival ports are required for all legs"
            raise ValueError(msg)
        return v

    @field_validator("vessel_speed")
    @classmethod
    def validate_vessel_speed(cls, v):
        """Validate vessel speed is positive."""
        if v is not None and v <= 0:
            msg = "Vessel speed must be positive"
            raise ValueError(msg)
        return v

    @field_validator("distance_between_stations")
    @classmethod
    def validate_station_spacing(cls, v):
        """Validate station spacing is positive."""
        if v is not None and v <= 0:
            msg = "Distance between stations must be positive"
            raise ValueError(msg)
        return v

    @field_validator("turnaround_time", "buffer_time")
    @classmethod
    def validate_time_fields(cls, v):
        """Validate time fields are non-negative."""
        if v is not None and v < 0:
            msg = "Time values must be non-negative"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_leg_structure(self):
        """
        Validate leg has valid structure and content.

        Returns
        -------
        LegDefinition
            Validated leg definition.

        Raises
        ------
        ValueError
            If leg structure is invalid.
        """
        return self


class CruiseConfig(BaseModel):
    """
    Root configuration model for cruise planning.

    Contains all the high-level parameters and definitions for a complete
    oceanographic cruise plan. Represents the top-level YAML structure
    with cruise metadata, global catalog, and schedule organization.

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
    start_date : str
        Cruise start date.
    start_time : Optional[str]
        Cruise start time.
    departure_port : Optional[Union[str, PointDefinition]]
        Port where the cruise begins.
    arrival_port : Optional[Union[str, PointDefinition]]
        Port where the cruise ends.
    points : Optional[List[PointDefinition]]
        Global catalog of point definitions.
    lines : Optional[List[LineDefinition]]
        Global catalog of line definitions.
    areas : Optional[List[AreaDefinition]]
        Global catalog of area definitions.
    ports : Optional[List[WaypointDefinition]]
        Global catalog of port definitions.
    legs : Optional[List[LegDefinition]]
        List of cruise legs for schedule organization.
    """

    cruise_name: str  # TODO: Decide if needed as default - could use "Untitled Cruise"
    description: Optional[str] = None

    # --- LOGIC CONSTRAINTS ---
    default_vessel_speed: float = (
        DEFAULT_VESSEL_SPEED_KT  # TODO: Decide if needed as default
    )
    default_distance_between_stations: float = DEFAULT_STATION_SPACING_KM
    turnaround_time: float = DEFAULT_TURNAROUND_TIME_MIN
    ctd_descent_rate: float = DEFAULT_CTD_RATE_M_S
    ctd_ascent_rate: float = DEFAULT_CTD_RATE_M_S

    # Configuration "daylight" or "dayshift" window for moorings
    day_start_hour: int = DEFAULT_DAY_START_HR  # Default 08:00
    day_end_hour: int = DEFAULT_DAY_END_HR  # Default 20:00

    start_date: str = DEFAULT_START_DATE
    start_time: Optional[str] = "08:00"

    # Port definitions for single-leg cruises
    departure_port: Optional[Union[str, PointDefinition]] = Field(
        None,
        description="Port where the cruise begins (can be global port reference). Required for single-leg cruises, forbidden for multi-leg cruises.",
    )
    arrival_port: Optional[Union[str, PointDefinition]] = Field(
        None,
        description="Port where the cruise ends (can be global port reference). Required for single-leg cruises, forbidden for multi-leg cruises.",
    )

    # Global catalog definitions
    points: Optional[list[PointDefinition]] = Field(
        default_factory=list, description="Global catalog of point definitions"
    )
    lines: Optional[list[LineDefinition]] = Field(
        default_factory=list, description="Global catalog of line definitions"
    )
    areas: Optional[list[AreaDefinition]] = Field(
        default_factory=list, description="Global catalog of area definitions"
    )
    ports: Optional[list[PointDefinition]] = Field(
        default_factory=list, description="Global catalog of port definitions"
    )

    # Schedule organization
    legs: Optional[list[LegDefinition]] = Field(
        default_factory=list,
        description="List of cruise legs for schedule organization",
    )

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_cruise_structure(self):
        """
        Validate overall cruise configuration structure.

        Returns
        -------
        CruiseConfig
            Validated cruise configuration.

        Raises
        ------
        ValueError
            If cruise structure is invalid.
        """
        # Basic validation - more complex validators can be added later
        if not self.cruise_name.strip():
            msg = "Cruise name cannot be empty"
            raise ValueError(msg)

        if self.default_vessel_speed <= 0:
            msg = "Default vessel speed must be positive"
            raise ValueError(msg)

        if self.default_distance_between_stations <= 0:
            msg = "Default distance between stations must be positive"
            raise ValueError(msg)

        return self
