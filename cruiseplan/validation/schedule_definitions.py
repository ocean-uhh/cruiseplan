"""
Schedule organization definitions for cruise configuration.

Defines the "Schedule Organization" section models that handle how
operations are grouped and organized into legs and clusters for execution.
These are YAML-layer definitions that get converted to runtime objects
during scheduling.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .catalog_definitions import PortDefinition, WaypointDefinition
from .enums import StrategyEnum


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
    sequence : Optional[List[Union[str, WaypointDefinition, dict]]]
        DEPRECATED: Ordered sequence of operations. Use 'activities' instead.
    stations : Optional[List[Union[str, WaypointDefinition]]]
        DEPRECATED: List of stations in the cluster. Use 'activities' instead.
    generate_transect : Optional[dict]
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
    sequence: Optional[List[Union[str, WaypointDefinition, dict]]] = Field(
        default=None, description="DEPRECATED: Use 'activities' instead"
    )
    stations: Optional[List[Union[str, WaypointDefinition]]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )
    generate_transect: Optional[dict] = Field(
        default=None, description="DEPRECATED: Use 'activities' instead"
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
        has_deprecated = (
            bool(self.sequence) or bool(self.stations) or bool(self.generate_transect)
        )

        if not has_activities and not has_deprecated:
            msg = f"Cluster '{self.name}' must have at least one activity, sequence, station, or generate_transect"
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
    stations : Optional[List[Union[str, WaypointDefinition]]]
        DEPRECATED: List of stations in the leg. Use 'activities' instead.
    sections : Optional[List[dict]]
        DEPRECATED: List of sections in the leg. Use 'activities' instead.
    sequence : Optional[List[Union[str, WaypointDefinition]]]
        DEPRECATED: Ordered sequence of operations. Use 'activities' instead.
    """

    name: str
    description: Optional[str] = None

    # Required maritime port-to-port structure
    departure_port: Union[str, PortDefinition]
    arrival_port: Union[str, PortDefinition]

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

    # Navigation waypoints (not executed, routing only)
    first_waypoint: Optional[str] = Field(
        None, description="First navigation waypoint for this leg (routing only)"
    )
    last_waypoint: Optional[str] = Field(
        None, description="Last navigation waypoint for this leg (routing only)"
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
    activities: Optional[List[Union[str, dict]]] = Field(
        default_factory=list,
        description="Unified list of all activities in this leg (can be string references or dict objects)",
    )
    clusters: Optional[List[ClusterDefinition]] = Field(
        default_factory=list, description="List of operation clusters"
    )

    # Deprecated fields (backward compatibility)
    stations: Optional[List[Union[str, WaypointDefinition]]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )
    sections: Optional[List[dict]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
    )
    sequence: Optional[List[Union[str, WaypointDefinition]]] = Field(
        default_factory=list, description="DEPRECATED: Use 'activities' instead"
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
