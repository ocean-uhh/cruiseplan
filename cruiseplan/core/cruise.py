"""
Core cruise management and organizational runtime classes.

This module provides the main CruiseInstance class for loading, validating, and managing
cruise configurations from YAML files, along with the organizational runtime
classes (Leg, Cluster) that form the hierarchical structure for cruise execution.
The BaseOrganizationUnit abstract base class provides the common interface for
all organizational units in the cruise planning hierarchy.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)

from cruiseplan.core.operations import BaseOperation
from cruiseplan.schema import (
    AreaDefinition,
    ClusterDefinition,
    CruiseConfig,
    LegDefinition,
    LineDefinition,
    PointDefinition,
    StrategyEnum,
)
from cruiseplan.schema.vocabulary import (
    ACTION_FIELD,
    AREA_ALLOWED_FIELDS,
    AREA_VERTEX_FIELD,
    AREAS_FIELD,
    ARRIVAL_PORT_FIELD,
    CLUSTER_ALLOWED_FIELDS,
    CTD_ASCENT_RATE_FIELD,
    CTD_DESCENT_RATE_FIELD,
    DAY_END_HOUR_FIELD,
    DAY_START_HOUR_FIELD,
    DEFAULT_STATION_SPACING_FIELD,
    DEFAULT_VESSEL_SPEED_FIELD,
    DEPARTURE_PORT_FIELD,
    DURATION_FIELD,
    LEG_ALLOWED_FIELDS,
    LEGS_FIELD,
    LINE_ALLOWED_FIELDS,
    LINE_VERTEX_FIELD,
    LINES_FIELD,
    OP_TYPE_FIELD,
    POINT_ALLOWED_FIELDS,
    POINTS_FIELD,
    START_DATE_FIELD,
    START_TIME_FIELD,
    TURNAROUND_TIME_FIELD,
    WATER_DEPTH_FIELD,
    YAML_FIELD_ORDER,
)
from cruiseplan.utils.global_ports import resolve_port_reference
from cruiseplan.utils.units import NM_PER_KM
from cruiseplan.utils.yaml_io import load_yaml


class ReferenceError(Exception):
    """
    Exception raised when a referenced item is not found in the catalog.

    This exception is raised during the reference resolution phase when
    string identifiers in the cruise configuration cannot be matched to
    their corresponding definitions in the station or transit registries.
    """


class BaseOrganizationUnit(ABC):
    """
    Abstract base class for organizational units in cruise planning.

    Provides common interface for hierarchical organization units (Leg, Cluster)
    that can contain operations and support parameter inheritance, boundary
    management, and geographic routing.

    All organizational units share common capabilities:
    - Entry/exit point management for routing
    - Operation counting and duration calculation
    - Parameter inheritance from parent units
    - Reordering policies for scheduling flexibility
    """

    @abstractmethod
    def get_all_operations(self) -> list[BaseOperation]:
        """Get all operations within this organizational unit."""
        pass

    @abstractmethod
    def get_operation_count(self) -> int:
        """Get total number of operations in this unit."""
        pass

    @abstractmethod
    def allows_reordering(self) -> bool:
        """Check if this unit allows operation reordering."""
        pass

    @abstractmethod
    def get_entry_point(self) -> Optional[tuple[float, float]]:
        """Get geographic entry point for this unit."""
        pass

    @abstractmethod
    def get_exit_point(self) -> Optional[tuple[float, float]]:
        """Get geographic exit point for this unit."""
        pass


class Cluster(BaseOrganizationUnit):
    """
    Runtime container for operation boundary management during scheduling.

    Clusters define boundaries for operation shuffling/reordering. Operations within
    a cluster can be reordered according to the cluster's strategy, but cannot be
    mixed with operations from other clusters or the parent leg.

    This provides scientific flexibility (weather-dependent reordering) while
    maintaining operational safety (critical sequences protected).

    Attributes
    ----------
    name : str
        Unique identifier for this cluster.
    description : Optional[str]
        Human-readable description of the cluster's purpose.
    strategy : StrategyEnum
        Scheduling strategy for operations within this cluster.
    ordered : bool
        Whether operations should maintain their defined order.
    operations : List[BaseOperation]
        List of operations contained within this cluster boundary.

    Examples
    --------
    >>> # Weather-flexible CTD cluster
    >>> ctd_cluster = Cluster(
    ...     name="CTD_Survey",
    ...     description="CTD operations that can be reordered for weather",
    ...     strategy=StrategyEnum.SEQUENTIAL,
    ...     ordered=False  # Allow weather-based reordering
    ... )

    >>> # Critical mooring sequence cluster
    >>> mooring_cluster = Cluster(
    ...     name="Mooring_Deployment",
    ...     description="Critical mooring sequence - strict order required",
    ...     strategy=StrategyEnum.SEQUENTIAL,
    ...     ordered=True  # Maintain deployment order for safety
    ... )
    """

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        strategy: StrategyEnum = StrategyEnum.SEQUENTIAL,
        ordered: bool = True,
    ):
        """
        Initialize a Cluster with the specified parameters.

        Parameters
        ----------
        name : str
            Unique identifier for this cluster.
        description : Optional[str], optional
            Human-readable description of the cluster's purpose.
        strategy : StrategyEnum, optional
            Scheduling strategy for operations within cluster (default: SEQUENTIAL).
        ordered : bool, optional
            Whether operations should maintain their defined order (default: True).
        """
        self.name = name
        self.description = description
        self.strategy = strategy
        self.ordered = ordered

        # Operation container - maintains cluster boundary
        self.operations: list[BaseOperation] = []

    def add_operation(self, operation: BaseOperation) -> None:
        """
        Add an operation to this cluster boundary.

        Operations added to a cluster can be reordered with other operations
        in the same cluster (subject to the cluster's ordering constraints)
        but will not be mixed with operations from other clusters.

        Parameters
        ----------
        operation : BaseOperation
            The operation to add to this cluster boundary.
        """
        self.operations.append(operation)

    def remove_operation(self, operation_name: str) -> bool:
        """
        Remove an operation from this cluster by name.

        Parameters
        ----------
        operation_name : str
            Name of the operation to remove.

        Returns
        -------
        bool
            True if operation was found and removed, False otherwise.
        """
        for i, operation in enumerate(self.operations):
            if operation.name == operation_name:
                del self.operations[i]
                return True
        return False

    def get_operation(self, operation_name: str) -> Optional[BaseOperation]:
        """
        Get an operation from this cluster by name.

        Parameters
        ----------
        operation_name : str
            Name of the operation to retrieve.

        Returns
        -------
        Optional[BaseOperation]
            The operation if found, None otherwise.
        """
        for operation in self.operations:
            if operation.name == operation_name:
                return operation
        return None

    def get_all_operations(self) -> list[BaseOperation]:
        """
        Get all operations within this cluster boundary.

        Returns a copy of the operations list to prevent external modification
        of the cluster boundary.

        Returns
        -------
        List[BaseOperation]
            Copy of all operations within this cluster.
        """
        return self.operations.copy()

    def calculate_total_duration(self, rules: Any) -> float:
        """
        Calculate total duration for all operations within this cluster.

        Parameters
        ----------
        rules : Any
            Duration calculation rules/parameters.

        Returns
        -------
        float
            Total duration in appropriate units (typically minutes).
        """
        total = 0.0
        for operation in self.operations:
            total += operation.calculate_duration(rules)
        return total

    def is_empty(self) -> bool:
        """
        Check if this cluster contains no operations.

        Returns
        -------
        bool
            True if cluster is empty, False otherwise.
        """
        return len(self.operations) == 0

    def get_operation_count(self) -> int:
        """
        Get the number of operations in this cluster.

        Returns
        -------
        int
            Number of operations within the cluster boundary.
        """
        return len(self.operations)

    def allows_reordering(self) -> bool:
        """
        Check if this cluster allows operation reordering.

        Returns
        -------
        bool
            True if operations can be reordered within cluster, False if strict order required.
        """
        return not self.ordered

    def get_operation_names(self) -> list[str]:
        """
        Get names of all operations within this cluster.

        Returns
        -------
        List[str]
            List of operation names within the cluster.
        """
        return [operation.name for operation in self.operations]

    def get_entry_point(self) -> Optional[tuple[float, float]]:
        """
        Get the geographic entry point for this cluster (first operation location).

        This provides a standardized interface regardless of internal field names.

        Returns
        -------
        tuple[float, float] or None
            (latitude, longitude) of the cluster's entry point, or None if no operations.
        """
        if not self.operations:
            return None
        first_op = self.operations[0]
        if hasattr(first_op, "latitude") and hasattr(first_op, "longitude"):
            return (first_op.latitude, first_op.longitude)
        return None

    def get_exit_point(self) -> Optional[tuple[float, float]]:
        """
        Get the geographic exit point for this cluster (last operation location).

        This provides a standardized interface regardless of internal field names.

        Returns
        -------
        tuple[float, float] or None
            (latitude, longitude) of the cluster's exit point, or None if no operations.
        """
        if not self.operations:
            return None
        last_op = self.operations[-1]
        if hasattr(last_op, "latitude") and hasattr(last_op, "longitude"):
            return (last_op.latitude, last_op.longitude)
        return None

    def __repr__(self) -> str:
        """
        String representation of the cluster.

        Returns
        -------
        str
            String representation showing cluster name and operation count.
        """
        return f"Cluster(name='{self.name}', operations={self.get_operation_count()}, ordered={self.ordered})"

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns
        -------
        str
            Human-readable description of the cluster.
        """
        order_desc = "strict order" if self.ordered else "flexible order"
        return f"Cluster '{self.name}': {self.get_operation_count()} operations ({order_desc})"

    @classmethod
    def from_definition(cls, cluster_def: ClusterDefinition) -> "Cluster":
        """
        Create a Cluster runtime instance from a ClusterDefinition.

        This factory method converts a validated ClusterDefinition into a runtime
        Cluster with proper boundary management configuration.

        Parameters
        ----------
        cluster_def : ClusterDefinition
            Validated cluster definition from YAML configuration.

        Returns
        -------
        Cluster
            New Cluster runtime instance with boundary management settings.
        """
        cluster = cls(
            name=cluster_def.name,
            description=cluster_def.description,
            strategy=(
                cluster_def.strategy
                if cluster_def.strategy
                else StrategyEnum.SEQUENTIAL
            ),
            ordered=cluster_def.ordered if cluster_def.ordered is not None else True,
        )

        # Note: Operations will be added later during resolution phase
        # based on the activities listed in cluster_def.activities
        # The cluster boundary structure is established here

        return cluster


class Leg(BaseOrganizationUnit):
    """
    Port-to-port maritime leg container following nautical terminology.

    A Leg represents a discrete maritime journey between two ports, containing
    all scientific operations and clusters executed during that voyage segment.
    This follows maritime tradition where a 'leg' always has departure and
    arrival ports, providing clear operational boundaries.

    The Leg manages parameter inheritance (from parent Cruise), cluster boundaries,
    and port-to-port routing for realistic maritime scheduling.

    Attributes
    ----------
    name : str
        Unique identifier for this leg.
    description : Optional[str]
        Optional human-readable description of the leg's purpose.
    departure_port : PointDefinition
        Required departure port for this maritime leg.
    arrival_port : PointDefinition
        Required arrival port for this maritime leg.
    strategy : StrategyEnum
        Execution strategy for operations (default: SEQUENTIAL).
    ordered : bool
        Whether operations should maintain their specified order (default: True).
    operations : List[BaseOperation]
        List of standalone operations (e.g., single CTD, single Transit).
    clusters : List[Cluster]
        List of cluster boundaries for operation shuffling control.
    first_activity : Optional[str]
        First waypoint/navigation marker for routing (not executed).
    last_activity : Optional[str]
        Last waypoint/navigation marker for routing (not executed).
    vessel_speed : Optional[float]
        Leg-specific vessel speed override (None uses cruise default).
    turnaround_time : Optional[float]
        Leg-specific turnaround time override in minutes (None uses cruise default).
    distance_between_stations : Optional[float]
        Leg-specific station spacing override (None uses cruise default).

    Examples
    --------
    >>> # Arctic research leg with weather-flexible clusters
    >>> leg = Leg(
    ...     name="Arctic_Survey",
    ...     departure_port=resolve_port_reference("port_tromsoe"),
    ...     arrival_port=resolve_port_reference("port_longyearbyen"),
    ...     vessel_speed=12.0,  # Faster speed for ice conditions
    ...     turnaround_time=45.0  # Extra time for Arctic operations
    ... )
    """

    def __init__(
        self,
        name: str,
        departure_port: Union[str, PointDefinition, dict],
        arrival_port: Union[str, PointDefinition, dict],
        description: Optional[str] = None,
        strategy: StrategyEnum = StrategyEnum.SEQUENTIAL,
        ordered: bool = True,
        first_activity: Optional[str] = None,
        last_activity: Optional[str] = None,
    ):
        """
        Initialize a maritime Leg with port-to-port structure.

        Parameters
        ----------
        name : str
            Unique identifier for this leg.
        departure_port : Union[str, PointDefinition, dict]
            Required departure port (can be global reference, PointDefinition, or dict).
        arrival_port : Union[str, PointDefinition, dict]
            Required arrival port (can be global reference, PointDefinition, or dict).
        description : Optional[str], optional
            Human-readable description of the leg's purpose.
        strategy : StrategyEnum, optional
            Execution strategy for operations (default: SEQUENTIAL).
        ordered : bool, optional
            Whether operations should maintain their specified order (default: True).
        first_activity : Optional[str], optional
            First waypoint for navigation (not executed).
        last_activity : Optional[str], optional
            Last waypoint for navigation (not executed).
        """
        self.name = name
        self.description = description
        self.strategy = strategy
        self.ordered = ordered
        self.first_activity = first_activity
        self.last_activity = last_activity

        # Resolve ports using global port system
        self.departure_port = resolve_port_reference(departure_port)
        self.arrival_port = resolve_port_reference(arrival_port)

        # Operation containers
        # Operations are simple, standalone tasks (e.g., a single CTD, a single Transit)
        self.operations: list[BaseOperation] = []
        # Clusters provide boundary management for operation shuffling
        self.clusters: list[Cluster] = []

        # Parameter inheritance attributes (to be set by parent Cruise)
        # These allow a Leg to override global cruise settings for this maritime segment.
        self.vessel_speed: Optional[float] = None
        self.turnaround_time: Optional[float] = None
        self.distance_between_stations: Optional[float] = None

    def add_operation(self, operation: BaseOperation) -> None:
        """
        Add a single, standalone operation to this leg.

        Parameters
        ----------
        operation : BaseOperation
            The operation to add (e.g., a single CTD cast or section).
        """
        self.operations.append(operation)

    def add_cluster(self, cluster: Cluster) -> None:
        """
        Add a cluster boundary to this leg for operation shuffling control.

        Parameters
        ----------
        cluster : Cluster
            The cluster boundary to add for operation reordering management.
        """
        self.clusters.append(cluster)

    def get_all_operations(self) -> list[BaseOperation]:
        """
        Flatten all operations including those within cluster boundaries.

        This provides a unified list of atomic operations for route optimization
        that respects the Leg's port-to-port boundaries.

        Returns
        -------
        List[BaseOperation]
            Unified list containing both standalone operations and operations
            from within cluster boundaries.
        """
        # Start with simple, direct operations
        all_ops = self.operations.copy()

        # Add operations from all cluster boundaries
        for cluster in self.clusters:
            all_ops.extend(cluster.get_all_operations())

        return all_ops

    def get_all_clusters(self) -> list[Cluster]:
        """
        Get all clusters within this leg for boundary management.

        Returns
        -------
        List[Cluster]
            List of all cluster boundaries within this leg.
        """
        return self.clusters.copy()

    def calculate_total_duration_legacy(self, rules: Any) -> float:
        """
        Calculate total duration for all operations in this leg.

        Includes port transit time, standalone operations, and cluster
        operations with proper boundary management.

        Parameters
        ----------
        rules : Any
            Duration calculation rules/parameters containing config.

        Returns
        -------
        float
            Total duration in minutes including all operations and port transits.
        """
        total = 0.0

        # Duration of standalone operations (Point, Line, Area)
        for op in self.operations:
            total += op.calculate_duration(rules)

        # Duration of cluster operations (includes boundary management)
        for cluster in self.clusters:
            total += cluster.calculate_total_duration(rules)

        # Add port-to-port transit time
        total += self._calculate_port_to_port_transit(rules)

        return total

    def _calculate_port_to_port_transit_legacy(self, rules: Any) -> float:
        """
        Calculate transit time from departure port to arrival port.

        Parameters
        ----------
        rules : Any
            Duration calculation rules containing config with vessel speed.

        Returns
        -------
        float
            Transit duration in minutes.
        """
        from cruiseplan.calculators.distance import haversine_distance

        # Calculate distance between ports
        departure_pos = (self.departure_port.latitude, self.departure_port.longitude)
        arrival_pos = (self.arrival_port.latitude, self.arrival_port.longitude)

        distance_km = haversine_distance(departure_pos, arrival_pos)
        distance_nm = distance_km * NM_PER_KM  # km to nautical miles

        # Get effective vessel speed for this leg
        default_speed = (
            getattr(rules.config, "default_vessel_speed", 10.0)
            if hasattr(rules, "config")
            else 10.0
        )
        speed_knots = self.get_vessel_speed(default_speed)

        # Calculate duration in hours, convert to minutes
        duration_hours = distance_nm / speed_knots
        return duration_hours * 60.0

    def get_vessel_speed(self, default_speed: float) -> float:
        """
        Get vessel speed for this leg (leg-specific override or cruise default).

        Parameters
        ----------
        default_speed : float
            The default speed from the parent cruise configuration.

        Returns
        -------
        float
            The effective vessel speed for this leg.
        """
        return self.vessel_speed if self.vessel_speed is not None else default_speed

    def get_station_spacing(self, default_spacing: float) -> float:
        """
        Get station spacing for this leg (leg-specific override or cruise default).

        Parameters
        ----------
        default_spacing : float
            The default spacing from the parent cruise configuration.

        Returns
        -------
        float
            The effective station spacing for this leg.
        """
        return (
            self.distance_between_stations
            if self.distance_between_stations is not None
            else default_spacing
        )

    def get_turnaround_time(self, default_turnaround: float) -> float:
        """
        Get turnaround time for this leg (leg-specific override or cruise default).

        Parameters
        ----------
        default_turnaround : float
            The default turnaround time from the parent cruise configuration.

        Returns
        -------
        float
            The effective turnaround time for this leg in minutes.
        """
        return (
            self.turnaround_time
            if self.turnaround_time is not None
            else default_turnaround
        )

    def allows_reordering(self) -> bool:
        """
        Check if this leg allows operation reordering.

        A leg allows reordering if it's not strictly ordered or if any of its
        clusters allow reordering.

        Returns
        -------
        bool
            True if operations can be reordered within this leg, False if strict order required.
        """
        if not self.ordered:
            return True

        # Check if any clusters allow reordering
        return any(cluster.allows_reordering() for cluster in self.clusters)

    def get_boundary_waypoints(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get the first and last waypoint boundaries for this leg.

        Returns
        -------
        tuple[Optional[str], Optional[str]]
            Tuple of (first_activity, last_activity) for boundary management.
        """
        return (self.first_activity, self.last_activity)

    def get_entry_point(self) -> tuple[float, float]:
        """
        Get the geographic entry point for this leg (departure port).

        This provides a standardized interface regardless of internal field names.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the leg's entry point.
        """
        return (self.departure_port.latitude, self.departure_port.longitude)

    def get_exit_point(self) -> tuple[float, float]:
        """
        Get the geographic exit point for this leg (arrival port).

        This provides a standardized interface regardless of internal field names.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the leg's exit point.
        """
        return (self.arrival_port.latitude, self.arrival_port.longitude)

    def get_operational_entry_point(
        self, resolver=None
    ) -> Optional[tuple[float, float]]:
        """
        Get the geographic entry point for operations within this leg.

        Uses first_activity if available, otherwise first activity.

        Parameters
        ----------
        resolver : object, optional
            Operation resolver to look up waypoint coordinates.

        Returns
        -------
        tuple[float, float] or None
            (latitude, longitude) of the operational entry point, or None if not resolvable.
        """
        if self.first_activity and resolver:
            from ..calculators.scheduler import _resolve_station_details

            details = _resolve_station_details(resolver, self.first_activity)
            if details:
                return (details["lat"], details["lon"])
        return None

    def get_operational_exit_point(
        self, resolver=None
    ) -> Optional[tuple[float, float]]:
        """
        Get the geographic exit point for operations within this leg.

        Uses last_activity if available, otherwise last activity.

        Parameters
        ----------
        resolver : object, optional
            Operation resolver to look up waypoint coordinates.

        Returns
        -------
        tuple[float, float] or None
            (latitude, longitude) of the operational exit point, or None if not resolvable.
        """
        if self.last_activity and resolver:
            from ..calculators.scheduler import _resolve_station_details

            details = _resolve_station_details(resolver, self.last_activity)
            if details:
                return (details["lat"], details["lon"])
        return None

    # TODO Check: why does this return Tuples instead of GeoPoints?
    def get_port_positions(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """
        Get the geographic positions of departure and arrival ports.

        Returns
        -------
        tuple[tuple[float, float], tuple[float, float]]
            Tuple of ((dep_lat, dep_lon), (arr_lat, arr_lon)) port positions.
        """
        departure_pos = (self.departure_port.latitude, self.departure_port.longitude)
        arrival_pos = (self.arrival_port.latitude, self.arrival_port.longitude)
        return (departure_pos, arrival_pos)

    def is_same_port_leg(self) -> bool:
        """
        Check if this leg departs and arrives at the same port.

        Returns
        -------
        bool
            True if departure and arrival ports are the same, False otherwise.
        """
        return self.departure_port.name == self.arrival_port.name

    def get_operation_count(self) -> int:
        """
        Get the total number of operations in this leg.

        Returns
        -------
        int
            Total count of operations including those within clusters.
        """
        total = len(self.operations)
        for cluster in self.clusters:
            total += cluster.get_operation_count()
        return total

    def __repr__(self) -> str:
        """
        String representation of the leg.

        Returns
        -------
        str
            String representation showing leg name, ports, and operation count.
        """
        return (
            f"Leg(name='{self.name}', "
            f"departure='{self.departure_port.name}', "
            f"arrival='{self.arrival_port.name}', "
            f"operations={self.get_operation_count()}, "
            f"clusters={len(self.clusters)})"
        )

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns
        -------
        str
            Human-readable description of the leg with port-to-port information.
        """
        port_desc = (
            f"{self.departure_port.name} → {self.arrival_port.name}"
            if not self.is_same_port_leg()
            else f"{self.departure_port.name} (round trip)"
        )
        return (
            f"Leg '{self.name}': {port_desc}, "
            f"{self.get_operation_count()} operations, "
            f"{len(self.clusters)} clusters"
        )

    @classmethod
    def from_definition(cls, leg_def: LegDefinition) -> "Leg":
        """
        Create a Leg runtime instance from a LegDefinition.

        This factory method converts a validated LegDefinition into a runtime Leg
        with proper port-to-port structure and default cluster creation.

        Parameters
        ----------
        leg_def : LegDefinition
            Validated leg definition from YAML configuration.

        Returns
        -------
        Leg
            New Leg runtime instance with resolved ports and clusters.
        """
        # Create runtime leg with port-to-port structure
        leg = cls(
            name=leg_def.name,
            departure_port=leg_def.departure_port,
            arrival_port=leg_def.arrival_port,
            description=leg_def.description,
            strategy=leg_def.strategy if leg_def.strategy else StrategyEnum.SEQUENTIAL,
            ordered=leg_def.ordered if leg_def.ordered is not None else True,
            first_activity=leg_def.first_activity,
            last_activity=leg_def.last_activity,
        )

        # Set parameter overrides from leg definition
        leg.vessel_speed = leg_def.vessel_speed
        leg.turnaround_time = leg_def.turnaround_time
        leg.distance_between_stations = leg_def.distance_between_stations

        # Create default cluster for activities if no clusters are defined
        if leg_def.activities and not leg_def.clusters:
            # Create a default cluster containing all activities
            default_cluster = Cluster(
                name=f"{leg_def.name}_operations",
                description=f"Default cluster for {leg_def.name} activities",
                strategy=(
                    leg_def.strategy if leg_def.strategy else StrategyEnum.SEQUENTIAL
                ),
                ordered=leg_def.ordered if leg_def.ordered is not None else True,
            )
            leg.add_cluster(default_cluster)

        # Process defined clusters
        elif leg_def.clusters:
            for cluster_def in leg_def.clusters:
                cluster = Cluster.from_definition(cluster_def)
                leg.add_cluster(cluster)

        # Note: Operations will be added later during resolution phase
        # The leg structure and boundaries are established here

        return leg


# TODO Question - why do we not also have a "leg_registry" and maybe a "cluster_registry"?
class CruiseInstance:
    """
    The main container object for cruise planning.

    Responsible for parsing YAML configuration files, validating the schema
    using Pydantic models, and resolving string references to full objects
    from the catalog registries.

    Attributes
    ----------
    config_path : Path
        Absolute path to the configuration file.
    raw_data : Dict[str, Any]
        Raw dictionary data loaded from the YAML file.
    config : CruiseConfig
        Validated Pydantic configuration object.
    point_registry : Dict[str, PointDefinition]
        Dictionary mapping point names to PointDefinition objects.
    line_registry : Dict[str, LineDefinition]
        Dictionary mapping line names to LineDefinition objects.
    port_registry : Dict[str, PointDefinition]
        Dictionary mapping port names to PointDefinition objects.
    area_registry : Dict[str, AreaDefinition]
        Dictionary mapping area names to AreaDefinition objects.
    runtime_legs : List[Leg]
        List of runtime Leg objects converted from LegDefinition objects.
    """

    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize a CruiseInstance object from a YAML configuration file.

        Performs three main operations:
        1. Loads and validates the YAML configuration using Pydantic
        2. Builds registries for points and lines
        3. Resolves string references to full objects

        Parameters
        ----------
        config_path : Union[str, Path]
            Path to the YAML configuration file containing cruise definition.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        YAMLIOError
            If the YAML file cannot be parsed.
        ValidationError
            If the configuration does not match the expected schema.
        ReferenceError
            If referenced points or lines are not found in the catalog.
        """
        self.config_path = Path(config_path)
        self.raw_data = self._load_yaml()

        # 1. Validation Pass (Pydantic)
        self.config = CruiseConfig(**self.raw_data)

        # 2. Indexing Pass (Build the Catalog Registry)
        self.point_registry: dict[str, PointDefinition] = {
            s.name: s for s in (self.config.points or [])
        }
        self.line_registry: dict[str, LineDefinition] = {
            t.name: t for t in (self.config.lines or [])
        }
        self.area_registry: dict[str, AreaDefinition] = {
            a.name: a for a in (self.config.areas or [])
        }
        self.port_registry: dict[str, PointDefinition] = {
            p.name: p for p in (self.config.ports or [])
        }

        # 3. Config Port Resolution Pass (Resolve top-level departure/arrival ports)
        self._resolve_config_ports()

        # 4. Port Enrichment Pass (Auto-expand leg port references with actions)
        self._enrich_leg_ports()

        # 5. Resolution Pass (Link Schedule to Catalog)
        self._resolve_references()

        # 6. Leg Conversion Pass (Convert LegDefinition to runtime Leg objects)
        self.runtime_legs = self._convert_leg_definitions_to_legs()

    def _load_yaml(self) -> dict[str, Any]:
        """
        Load and parse the YAML configuration file.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing the parsed YAML data.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        YAMLIOError
            If the YAML file cannot be parsed.
        """
        return load_yaml(self.config_path)

    def _resolve_references(self):
        """
        Resolve string references to full objects from the registry.

        Traverses the cruise legs, clusters, and sections to convert string
        identifiers into their corresponding PointDefinition and
        LineDefinition objects from the registries.

        Resolves all references within legs to their corresponding definitions.

        Raises
        ------
        ReferenceError
            If any referenced station or transit ID is not found in the
            corresponding registry.
        """
        # Note: Global anchor validation removed - waypoints are now handled at leg level

        for leg in self.config.legs:
            # Resolve Direct Leg Activities (modern field)
            if leg.activities:
                leg.activities = self._resolve_mixed_list(leg.activities)

            # Resolve Clusters
            if leg.clusters:
                for cluster in leg.clusters:
                    # Resolve Activities (new unified field)
                    if cluster.activities:
                        cluster.activities = self._resolve_mixed_list(
                            cluster.activities
                        )

    # TODO update docstring, I don't think we have "Station" and "Transit" are these supposed to be human readable for "operation_type"?
    def _resolve_list(
        self, items: list[Union[str, Any]], registry: dict[str, Any], type_label: str
    ) -> list[Any]:
        """
        Resolve a list containing items of a specific type.

        Handles the "Hybrid Pattern" where strings are treated as lookups
        into the registry, while objects are kept as-is (already validated
        by Pydantic).

        Parameters
        ----------
        items : List[Union[str, Any]]
            List of items that may be strings (references) or objects.
        registry : Dict[str, Any]
            Dictionary mapping string IDs to their corresponding objects.
        type_label : str
            Human-readable label for the type (e.g., "Station", "Transit")
            used in error messages.

        Returns
        -------
        List[Any]
            List with string references resolved to their corresponding objects.

        Raises
        ------
        ReferenceError
            If any string reference is not found in the registry.
        """
        resolved_items = []
        for item in items:
            if isinstance(item, str):
                if item not in registry:
                    raise ReferenceError(
                        f"{type_label} ID '{item}' referenced in schedule but not found in Catalog."
                    )
                resolved_items.append(registry[item])
            else:
                # Item is already an inline object (validated by Pydantic)
                resolved_items.append(item)
        return resolved_items

    def _resolve_mixed_list(self, items: list[Union[str, Any]]) -> list[Any]:
        """
        Resolve a mixed sequence list containing points, lines, or areas.

        Searches through all available registries to resolve string references
        and converts inline dictionary definitions to proper object types.

        Parameters
        ----------
        items : List[Union[str, Any]]
            List of items that may be strings (references), dictionaries
            (inline definitions), or already-resolved objects.

        Returns
        -------
        List[Any]
            List with string references resolved and dictionaries converted
            to their corresponding definition objects.

        Raises
        ------
        ReferenceError
            If any string reference is not found in any registry.
        """
        resolved_items = []
        for item in items:
            if isinstance(item, str):
                # Try finding it in any registry
                if item in self.point_registry:
                    resolved_items.append(self.point_registry[item])
                elif item in self.line_registry:
                    resolved_items.append(self.line_registry[item])
                elif item in self.area_registry:
                    resolved_items.append(self.area_registry[item])
                else:
                    raise ReferenceError(
                        f"Activity ID '{item}' not found in any Catalog (Points, Lines, Areas)."
                    )
            elif isinstance(item, dict):
                # Convert inline dictionary definition to proper object type
                resolved_items.append(self._convert_inline_definition(item))
            else:
                # Item is already a resolved object
                resolved_items.append(item)
        return resolved_items

    # TODO What is going on here? why is "operation_type" returning a PointDefinition?
    # Can we use vocabularly.py and OP_TYPE_FIELD here?
    def _convert_inline_definition(
        self, definition_dict: dict
    ) -> Union[PointDefinition, LineDefinition, AreaDefinition]:
        """
        Convert an inline dictionary definition to the appropriate definition object.

        Determines the type of definition based on the presence of key fields
        and creates the corresponding Pydantic object.

        Parameters
        ----------
        definition_dict : dict
            Dictionary containing the inline definition fields.

        Returns
        -------
        Union[PointDefinition, LineDefinition, AreaDefinition]
            The appropriate definition object created from the dictionary.

        Raises
        ------
        ValueError
            If the definition type cannot be determined or validation fails.
        """
        # Import vocabulary constants

        # Determine definition type based on key fields (check most specific first)
        if LINE_VERTEX_FIELD in definition_dict:  # "route"
            return LineDefinition(**definition_dict)
        elif AREA_VERTEX_FIELD in definition_dict:
            return AreaDefinition(**definition_dict)
        # Fallback: assume it's a station if it has common station fields
        elif any(field in definition_dict for field in ["latitude", "longitude"]):
            # Add default operation_type if missing
            if "operation_type" not in definition_dict:
                definition_dict = definition_dict.copy()
                definition_dict["operation_type"] = (
                    "CTD"  # Default operation type - TODO this doesn't seem right, do we have a default operation defined in defaults.py?
                )
            return PointDefinition(**definition_dict)
        else:
            raise ValueError(
                f"Cannot determine definition type for inline definition: {definition_dict}"
            )

    def _resolve_port_reference(self, port_ref) -> PointDefinition:
        """
        Resolve a port reference checking catalog first, then global registry.

        Follows the catalog-based pattern where string references are first
        checked against the local port catalog, then fall back to global
        port registry for resolution.

        Parameters
        ----------
        port_ref : Union[str, PointDefinition, dict]
            Port reference to resolve.

        Returns
        -------
        PointDefinition
            Resolved port definition object.

        Raises
        ------
        ReferenceError
            If string reference is not found in catalog or global registry.
        """
        # Catch-all for any port-like object at the beginning
        if (
            hasattr(port_ref, "name")
            and hasattr(port_ref, "latitude")
            and hasattr(port_ref, "longitude")
        ):
            return port_ref

        # If already a PointDefinition object, return as-is
        if isinstance(port_ref, PointDefinition):
            return port_ref

        # If dictionary, create PointDefinition
        if isinstance(port_ref, dict):
            return PointDefinition(**port_ref)

        # String reference - check catalog first, then global registry
        if isinstance(port_ref, str):
            # Check local catalog first
            if port_ref in self.port_registry:
                catalog_port = self.port_registry[port_ref]
                # If catalog port is already a PointDefinition, return it
                if isinstance(catalog_port, PointDefinition):
                    return catalog_port
                # If it's a dict, convert to PointDefinition
                elif isinstance(catalog_port, dict):
                    return PointDefinition(**catalog_port)
                else:
                    # Handle unexpected type in catalog
                    raise ReferenceError(
                        f"Unexpected type in port catalog: {type(catalog_port)}"
                    )

            # Fall back to global port registry
            try:
                return resolve_port_reference(port_ref)
            except ValueError as e:
                raise ReferenceError(
                    f"Port reference '{port_ref}' not found in catalog or global registry: {e}"
                ) from e

        raise ReferenceError(f"Invalid port reference type: {type(port_ref)}")

    # TODO check is this pydantic or yaml-based, if yaml-based can we use vocabulary.py for DEPARTURE_PORT_FIELD and ARRIVAL_PORT_FIELD?
    def _resolve_config_ports(self):
        """
        Resolve top-level config departure_port and arrival_port references.

        This method resolves string references in the cruise configuration's
        top-level departure_port and arrival_port fields to PointDefinition objects.
        """
        if hasattr(self.config, "departure_port") and self.config.departure_port:
            if isinstance(self.config.departure_port, str):
                self.config.departure_port = self._resolve_port_reference(
                    self.config.departure_port
                )

        if hasattr(self.config, "arrival_port") and self.config.arrival_port:
            if isinstance(self.config.arrival_port, str):
                self.config.arrival_port = self._resolve_port_reference(
                    self.config.arrival_port
                )

    # TODO check if we can use vocabulary.py for DEPARTURE_PORT_FIELD and ARRIVAL_PORT_FIELD or if this is a pydantic-based thing
    def _enrich_leg_ports(self):
        """
        Automatically enrich leg-level port references with actions.

        Handles both string port references and inline port objects:
        - String references are expanded using global port registry
        - Inline port objects get action and operation_type fields added
        - departure_port gets action='mob' (mobilization)
        - arrival_port gets action='demob' (demobilization)
        """
        for leg_def in self.config.legs or []:
            # Enrich departure_port with mob action
            if hasattr(leg_def, "departure_port") and leg_def.departure_port:
                if isinstance(leg_def.departure_port, str):
                    # String reference - expand from global registry
                    port_ref = leg_def.departure_port
                    try:
                        port_definition = resolve_port_reference(port_ref)
                        # Create enriched port with action
                        enriched_port = PointDefinition(
                            name=port_definition.name,
                            latitude=port_definition.latitude,
                            longitude=port_definition.longitude,
                            operation_type="port",
                            action="mob",  # Departure ports are mobilization
                            display_name=getattr(
                                port_definition, "display_name", port_definition.name
                            ),
                        )
                        leg_def.departure_port = enriched_port
                    except ValueError:
                        # If global port resolution fails, keep as string
                        pass
                else:
                    # Inline port object - add missing fields
                    port_obj = leg_def.departure_port
                    if not hasattr(port_obj, "action") or port_obj.action is None:
                        port_obj.action = "mob"
                    if (
                        not hasattr(port_obj, "operation_type")
                        or port_obj.operation_type is None
                    ):
                        port_obj.operation_type = "port"

            # Enrich arrival_port with demob action
            if hasattr(leg_def, "arrival_port") and leg_def.arrival_port:
                if isinstance(leg_def.arrival_port, str):
                    # String reference - expand from global registry
                    port_ref = leg_def.arrival_port
                    try:
                        port_definition = resolve_port_reference(port_ref)
                        # Create enriched port with action
                        enriched_port = PointDefinition(
                            name=port_definition.name,
                            latitude=port_definition.latitude,
                            longitude=port_definition.longitude,
                            operation_type="port",
                            action="demob",  # Arrival ports are demobilization
                            display_name=getattr(
                                port_definition, "display_name", port_definition.name
                            ),
                        )
                        leg_def.arrival_port = enriched_port
                    except ValueError:
                        # If global port resolution fails, keep as string
                        pass
                else:
                    # Inline port object - add missing fields
                    port_obj = leg_def.arrival_port
                    if not hasattr(port_obj, "action") or port_obj.action is None:
                        port_obj.action = "demob"
                    if (
                        not hasattr(port_obj, "operation_type")
                        or port_obj.operation_type is None
                    ):
                        port_obj.operation_type = "port"

    def _convert_leg_definitions_to_legs(self) -> list[Leg]:
        """
        Convert LegDefinition objects to runtime Leg objects with clusters.

        This method implements Phase 4 of the CLAUDE-legclass.md architecture:
        - Creates runtime Leg objects from LegDefinition YAML data
        - Resolves port references using global port system
        - Applies parameter inheritance from cruise to leg level
        - Creates clusters (explicit or default) within each leg
        - Validates required maritime structure (departure_port + arrival_port)

        Returns
        -------
        List[Leg]
            List of runtime Leg objects ready for scheduling.

        Raises
        ------
        ValueError
            If leg is missing required departure_port or arrival_port.
        ReferenceError
            If port references cannot be resolved.
        """
        runtime_legs = []

        for leg_def in self.config.legs or []:
            # Validate required maritime structure
            if not leg_def.departure_port or not leg_def.arrival_port:
                raise ValueError(
                    f"Leg '{leg_def.name}' missing required departure_port or arrival_port. "
                    "Maritime legs must be port-to-port segments."
                )

            # Resolve port references (check catalog first, then global registry)
            try:
                departure_port = self._resolve_port_reference(leg_def.departure_port)
                arrival_port = self._resolve_port_reference(leg_def.arrival_port)
            except ValueError as e:
                raise ReferenceError(
                    f"Port resolution failed for leg '{leg_def.name}': {e}"
                ) from e

            # Create runtime leg with maritime structure
            runtime_leg = Leg(
                name=leg_def.name,
                departure_port=departure_port,
                arrival_port=arrival_port,
                description=leg_def.description,
                strategy=leg_def.strategy or StrategyEnum.SEQUENTIAL,
                ordered=leg_def.ordered if leg_def.ordered is not None else True,
                first_activity=leg_def.first_activity,
                last_activity=leg_def.last_activity,
            )

            # Apply parameter inheritance (leg overrides cruise defaults)
            runtime_leg.vessel_speed = leg_def.vessel_speed or getattr(
                self.config, "default_vessel_speed", None
            )
            runtime_leg.distance_between_stations = (
                leg_def.distance_between_stations
                or getattr(self.config, "default_distance_between_stations", None)
            )
            runtime_leg.turnaround_time = leg_def.turnaround_time or getattr(
                self.config, "turnaround_time", None
            )

            # Create clusters within the leg
            if leg_def.clusters:
                # Explicit clusters defined
                for cluster_def in leg_def.clusters:
                    runtime_cluster = Cluster.from_definition(cluster_def)
                    # TODO: Resolve activities to operations in Phase 3 completion
                    runtime_leg.clusters.append(runtime_cluster)
            elif leg_def.activities:
                # Create default cluster from leg activities
                default_cluster = Cluster(
                    name=f"{leg_def.name}_Default",
                    description=f"Default cluster for leg {leg_def.name}",
                    strategy=leg_def.strategy or StrategyEnum.SEQUENTIAL,
                    ordered=leg_def.ordered if leg_def.ordered is not None else True,
                )
                # TODO: Resolve activities to operations in Phase 3 completion
                runtime_leg.clusters.append(default_cluster)

            runtime_legs.append(runtime_leg)

        return runtime_legs

    def _anchor_exists_in_catalog(self, anchor_ref: str) -> bool:
        """
        Check if an anchor reference exists in any catalog registry.

        Anchors can be points, areas, or other operation entities
        that can serve as routing points for maritime planning.

        Parameters
        ----------
        anchor_ref : str
            String reference to check against all registries.

        Returns
        -------
        bool
            True if the anchor reference exists in any registry.
        """
        # Check all registries for the anchor reference
        return (
            anchor_ref in self.point_registry
            or anchor_ref in self.area_registry
            or anchor_ref in self.line_registry
        )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "CruiseInstance":
        """
        Create a CruiseInstance from a dictionary without file I/O.

        This class method provides single source of truth functionality by creating
        a CruiseInstance object directly from a configuration dictionary, eliminating the
        need for temporary file creation during enrichment operations.

        Parameters
        ----------
        config_dict : Dict[str, Any]
            Dictionary containing cruise configuration data (e.g., from YAML parsing).

        Returns
        -------
        CruiseInstance
            New CruiseInstance with all registries built and references resolved.

        Raises
        ------
        ValidationError
            If the configuration does not match the expected schema.
        ReferenceError
            If referenced points or lines are not found in the catalog.

        Examples
        --------
        >>> config = {
        ...     "cruise_name": "Test Cruise",
        ...     "default_vessel_speed": 10.0,
        ...     "points": [{"name": "P1", "latitude": 60.0, "longitude": 5.0}],
        ...     "legs": [{"name": "Leg1", "departure_port": "Bergen", "arrival_port": "Tromsø"}]
        ... }
        >>> cruise = CruiseInstance.from_dict(config)
        >>> cruise.config.cruise_name
        'Test Cruise'
        """
        # Create a temporary instance to leverage existing initialization logic
        instance = cls.__new__(cls)

        # Set path to None since we're creating from dict
        instance.config_path = None
        instance.raw_data = config_dict.copy()

        # 1. Validation Pass (Pydantic)
        instance.config = CruiseConfig(**instance.raw_data)

        # 2. Indexing Pass (Build the Catalog Registry)
        instance.point_registry: dict[str, PointDefinition] = {
            s.name: s for s in (instance.config.points or [])
        }
        instance.line_registry: dict[str, LineDefinition] = {
            t.name: t for t in (instance.config.lines or [])
        }
        instance.area_registry: dict[str, AreaDefinition] = {
            a.name: a for a in (instance.config.areas or [])
        }
        instance.port_registry: dict[str, PointDefinition] = {
            p.name: p for p in (instance.config.ports or [])
        }

        # 3. Config Port Resolution Pass
        instance._resolve_config_ports()

        # 4. Port Enrichment Pass
        instance._enrich_leg_ports()

        # 5. Resolution Pass
        instance._resolve_references()

        # 6. Leg Conversion Pass
        instance.runtime_legs = instance._convert_leg_definitions_to_legs()

        return instance

    def to_commented_dict(self) -> dict[str, Any]:
        """
        Export CruiseInstance configuration to a structured dictionary with comment preservation.

        This method provides the foundation for YAML output with canonical field
        ordering and comment preservation capabilities. Returns a dictionary that
        can be processed by ruamel.yaml for structured output with comments.

        Returns
        -------
        Dict[str, Any]
            Dictionary with canonical field ordering suitable for YAML export
            with comment preservation.

        Notes
        -----
        The output dictionary follows canonical ordering:
        1. Cruise Metadata (cruise_name, description, start_date, start_time)
        2. Vessel Parameters (default_vessel_speed, turnaround_time, etc.)
        3. Calculation Settings (calculate_*, day_start_hour, etc.)
        4. Catalog Definitions (points, lines, areas, ports)
        5. Schedule Organization (legs)

        Comment preservation is handled at the YAML layer using ruamel.yaml
        with end-of-line and section header comment support.
        """
        # Build ordered output dictionary following canonical structure
        try:
            from ruamel.yaml.comments import CommentedMap

            output = CommentedMap()
        except ImportError:
            # Fallback to regular dict if ruamel.yaml not available
            output = {}

        # 1. Cruise Metadata
        output["cruise_name"] = self.config.cruise_name
        if self.config.description:
            output["description"] = self.config.description
        output[START_DATE_FIELD] = self.config.start_date
        if self.config.start_time:
            output[START_TIME_FIELD] = self.config.start_time

        # 2. Vessel Parameters
        output[DEFAULT_VESSEL_SPEED_FIELD] = self.config.default_vessel_speed
        output[DEFAULT_STATION_SPACING_FIELD] = (
            self.config.default_distance_between_stations
        )
        output[TURNAROUND_TIME_FIELD] = self.config.turnaround_time
        output[CTD_DESCENT_RATE_FIELD] = self.config.ctd_descent_rate
        output[CTD_ASCENT_RATE_FIELD] = self.config.ctd_ascent_rate

        # 3. Calculation Settings
        output[DAY_START_HOUR_FIELD] = self.config.day_start_hour
        output[DAY_END_HOUR_FIELD] = self.config.day_end_hour

        # 3b. Single-leg cruise ports (if applicable)
        if self.config.departure_port:
            output[DEPARTURE_PORT_FIELD] = self._serialize_point_definition(
                self.config.departure_port
            )
        if self.config.arrival_port:
            output[ARRIVAL_PORT_FIELD] = self._serialize_point_definition(
                self.config.arrival_port
            )

        # 4. Catalog Definitions
        if self.point_registry:
            output[POINTS_FIELD] = [
                self._serialize_point_definition(p)
                for p in self.point_registry.values()
            ]
        if self.line_registry:
            output[LINES_FIELD] = [
                self._serialize_line_definition(l) for l in self.line_registry.values()
            ]
        if self.area_registry:
            output[AREAS_FIELD] = [
                self._serialize_area_definition(a) for a in self.area_registry.values()
            ]

        # Add section comment for catalog definitions
        try:
            if (
                hasattr(output, "yaml_set_comment_before_after_key")
                and self.point_registry
            ):
                output.yaml_set_comment_before_after_key(
                    POINTS_FIELD,
                    before="\n# === CATALOG DEFINITIONS ===\n# Station definitions, transect routes, and survey areas",
                )
        except (AttributeError, ImportError):
            pass  # Fallback for when ruamel.yaml is not available
        if self.config.ports:
            output["ports"] = [
                self._serialize_point_definition(p) for p in self.config.ports
            ]

        # 5. Schedule Organization
        if self.config.legs:
            output[LEGS_FIELD] = [
                self._serialize_leg_definition(leg) for leg in self.config.legs
            ]

            # Add section comment for cruise organization
            try:
                if hasattr(output, "yaml_set_comment_before_after_key"):
                    output.yaml_set_comment_before_after_key(
                        LEGS_FIELD,
                        before="\n# === CRUISE ORGANIZATION ===\n# Leg definitions with port-to-port routing and activity schedules",
                    )
            except (AttributeError, ImportError):
                pass  # Fallback for when ruamel.yaml is not available

        return output

    def _serialize_definition(
        self, obj: Any, allowed_fields: set[str]
    ) -> dict[str, Any]:
        """Serialize any definition using master field ordering and allowed fields."""
        data = obj.model_dump(exclude_none=True, mode="json")
        ordered_dict = {}

        # Check for fields that would be filtered out and warn about them
        filtered_fields = set(data.keys()) - allowed_fields
        if filtered_fields:
            obj_type = type(obj).__name__
            obj_name = getattr(obj, "name", "unnamed")
            warning_msg = (
                f"{obj_type} '{obj_name}' has fields not in allowed set: {sorted(filtered_fields)}. "
                f"These fields will not be included in YAML output. "
                f"To include them, add to the appropriate ALLOWED_FIELDS set in vocabulary.py"
            )

            logger.warning(warning_msg)

        # Apply master field ordering, filtering by allowed fields
        for yaml_field, pydantic_field in YAML_FIELD_ORDER:
            if pydantic_field in allowed_fields and pydantic_field in data:
                # Handle special field processing
                processed_value = self._process_field_value(
                    obj, pydantic_field, data[pydantic_field]
                )
                ordered_dict[yaml_field] = processed_value

        # Add remaining fields alphabetically
        processed_fields = {pf for _, pf in YAML_FIELD_ORDER}
        remaining_fields = sorted(set(data.keys()) - processed_fields)
        for field in remaining_fields:
            if field in allowed_fields:
                ordered_dict[field] = data[field]

        return ordered_dict

    def _process_field_value(self, obj: Any, pydantic_field: str, value: Any) -> Any:
        """Process special field values during serialization."""
        # Handle activities field - convert objects to name strings
        if pydantic_field == "activities" and hasattr(obj, "activities") and value:
            activity_names = []
            activities = getattr(obj, "activities", [])
            for activity in activities:
                if hasattr(activity, "name"):
                    activity_names.append(activity.name)
                else:
                    # Fallback if it's already a string
                    activity_names.append(str(activity))
            return activity_names

        # Handle first_activity and last_activity - convert to name strings
        elif pydantic_field in ("first_activity", "last_activity"):
            activity = getattr(obj, pydantic_field, None)
            if activity:
                if hasattr(activity, "name"):
                    return activity.name
                else:
                    return str(activity)
            return value

        # Handle port fields - re-serialize through unified system for proper ordering
        elif pydantic_field in ("departure_port", "arrival_port"):
            port_obj = getattr(obj, pydantic_field, None)
            if port_obj and hasattr(port_obj, "model_dump"):
                # Re-serialize the port object through our unified system
                return self._serialize_definition(port_obj, POINT_ALLOWED_FIELDS)
            return value

        # Handle clusters - recursive serialization
        elif pydantic_field == "clusters" and hasattr(obj, "clusters") and value:
            return [
                self._serialize_definition(cluster, CLUSTER_ALLOWED_FIELDS)
                for cluster in getattr(obj, "clusters", [])
            ]

        # Default: return value as-is
        return value

    def _serialize_point_definition(self, point: PointDefinition) -> dict[str, Any]:
        """Serialize a PointDefinition to dictionary format with canonical field ordering."""
        return self._serialize_definition(point, POINT_ALLOWED_FIELDS)

    def _serialize_line_definition(self, line: LineDefinition) -> dict[str, Any]:
        """Serialize a LineDefinition to dictionary format with canonical field ordering."""
        return self._serialize_definition(line, LINE_ALLOWED_FIELDS)

    def _serialize_area_definition(self, area: AreaDefinition) -> dict[str, Any]:
        """Serialize an AreaDefinition to dictionary format with canonical field ordering."""
        return self._serialize_definition(area, AREA_ALLOWED_FIELDS)

    def _serialize_cluster_definition(
        self, cluster: ClusterDefinition
    ) -> dict[str, Any]:
        """Serialize a ClusterDefinition to dictionary format with canonical field ordering."""
        return self._serialize_definition(cluster, CLUSTER_ALLOWED_FIELDS)

    def _serialize_leg_definition(self, leg: LegDefinition) -> dict[str, Any]:
        """Serialize a LegDefinition to dictionary format."""
        return self._serialize_definition(leg, LEG_ALLOWED_FIELDS)

    def to_yaml(
        self, output_path: Union[str, Path], enrichment_command: Optional[str] = None
    ) -> None:
        """
        Export CruiseInstance configuration to YAML file with canonical ordering.

        This method provides direct YAML export capability with standardized
        field ordering and basic comment preservation. Uses ruamel.yaml for
        structured output that maintains readability.

        Parameters
        ----------
        output_path : Union[str, Path]
            Path where the YAML file should be written.
        enrichment_command : Optional[str]
            The enrichment command that was used to create this file, for documentation.

        Raises
        ------
        IOError
            If the output file cannot be written.

        Examples
        --------
        >>> cruise = CruiseInstance.from_dict(config_dict)
        >>> cruise.to_yaml("enhanced_cruise.yaml")

        Notes
        -----
        The exported YAML follows canonical field ordering and includes
        section comments for improved readability. This replaces the need
        for dual state management during enrichment operations.
        """
        try:
            from ruamel.yaml import YAML
        except ImportError:
            # Fallback to basic yaml if ruamel.yaml not available
            import yaml

            output_dict = self.to_commented_dict()
            output_path = Path(output_path)

            with output_path.open("w", encoding="utf-8") as f:
                # Write file-level comment
                f.write("# Cruise configuration generated by CruisePlan\n")
                f.write("# Canonical field ordering enforced for consistency\n")
                if enrichment_command:
                    f.write(f"# Enriched with command: {enrichment_command}\n")
                f.write("\n")

                yaml.dump(output_dict, f, default_flow_style=False, sort_keys=False)
            return

        # Use ruamel.yaml for better formatting and comment preservation
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.width = 4096  # Prevent line wrapping
        yaml.indent(mapping=2, sequence=4, offset=2)

        output_dict = self.to_commented_dict()
        output_path = Path(output_path)

        # Add section comments for readability
        yaml.representer.add_representer(
            type(None),
            lambda dumper, value: dumper.represent_scalar("tag:yaml.org,2002:null", ""),
        )

        with output_path.open("w", encoding="utf-8") as f:
            # Write file-level comment
            f.write("# Cruise configuration generated by CruisePlan\n")
            f.write("# Canonical field ordering enforced for consistency\n")
            if enrichment_command:
                f.write(f"# Enriched with command: {enrichment_command}\n")
            f.write("\n")

            yaml.dump(output_dict, f)

    # === CruiseInstance Enhancement Methods ===
    # These methods modify the CruiseInstance object state to add functionality

    def expand_sections(self, default_depth: float = -9999.0) -> dict[str, int]:
        """
        Expand CTD sections into individual station definitions.

        This method finds CTD sections in lines catalog and expands them into
        individual stations, adding them to the point_registry. This is structural
        enrichment that modifies the cruise configuration.

        Parameters
        ----------
        default_depth : float, optional
            Default depth value for expanded stations. Default is -9999.0.

        Returns
        -------
        dict[str, int]
            Dictionary with expansion summary:
            - sections_expanded: Number of sections expanded
            - stations_from_expansion: Number of stations created
        """
        sections_expanded = 0
        total_stations_created = 0

        # Find CTD sections in lines catalog
        ctd_sections = []
        for line_name, line_def in self.line_registry.items():
            if (
                hasattr(line_def, "operation_type")
                and line_def.operation_type == "CTD"
                and hasattr(line_def, "action")
                and line_def.action == "section"
            ):
                ctd_sections.append(
                    {
                        "name": line_name,
                        "route": line_def.route,
                        "distance_between_stations": (
                            getattr(line_def, "distance_between_stations", None) or 20.0
                        ),
                        "max_depth": getattr(line_def, "max_depth", None),
                        "planned_duration_hours": getattr(
                            line_def, "planned_duration_hours", None
                        ),
                        DURATION_FIELD: getattr(line_def, DURATION_FIELD, None),
                    }
                )

        # Expand each section
        sections_to_remove = []
        for section in ctd_sections:
            expanded_stations = self._expand_single_ctd_section(section, default_depth)
            if expanded_stations:
                section_name = section["name"]
                station_names = []

                # Add stations to point registry
                for station_dict in expanded_stations:
                    station_name = station_dict["name"]
                    # Convert dict back to PointDefinition
                    point_def = PointDefinition(**station_dict)
                    self.point_registry[station_name] = point_def
                    station_names.append(station_name)
                    total_stations_created += 1

                # Update leg activities to reference expanded stations
                self._update_leg_activities_for_expanded_section(
                    section_name, station_names
                )

                # Mark section for removal from line registry
                sections_to_remove.append(section_name)
                sections_expanded += 1

        # Remove expanded sections from line registry
        for section_name in sections_to_remove:
            if section_name in self.line_registry:
                del self.line_registry[section_name]

        return {
            "sections_expanded": sections_expanded,
            "stations_from_expansion": total_stations_created,
        }

    def _update_leg_activities_for_expanded_section(
        self, section_name: str, station_names: list[str]
    ) -> None:
        """
        Update leg activities to replace expanded section with station names.

        Parameters
        ----------
        section_name : str
            Name of the section that was expanded.
        station_names : list[str]
            Names of the stations created from the expansion.
        """
        for leg in self.config.legs:
            # Update activities list - activities are resolved objects, not strings
            if hasattr(leg, "activities") and leg.activities:
                updated_activities = []
                for activity in leg.activities:
                    # Check if this activity object has the name we're looking for
                    if hasattr(activity, "name") and activity.name == section_name:
                        # Replace with PointDefinition objects from registry
                        for station_name in station_names:
                            if station_name in self.point_registry:
                                updated_activities.append(
                                    self.point_registry[station_name]
                                )
                    else:
                        updated_activities.append(activity)
                leg.activities = updated_activities

            # Update first_activity if it points to the expanded section
            if hasattr(leg, "first_activity") and leg.first_activity:
                # Handle both string references and resolved objects
                activity_name = (
                    leg.first_activity.name
                    if hasattr(leg.first_activity, "name")
                    else leg.first_activity
                )
                if activity_name == section_name:
                    leg.first_activity = self.point_registry[station_names[0]]

            # Update last_activity if it points to the expanded section
            if hasattr(leg, "last_activity") and leg.last_activity:
                # Handle both string references and resolved objects
                activity_name = (
                    leg.last_activity.name
                    if hasattr(leg.last_activity, "name")
                    else leg.last_activity
                )
                if activity_name == section_name:
                    leg.last_activity = self.point_registry[station_names[-1]]

    def _expand_single_ctd_section(
        self, section: dict[str, Any], default_depth: float = -9999.0
    ) -> list[dict[str, Any]]:
        """
        Expand a single CTD section into individual station definitions.

        Parameters
        ----------
        section : dict[str, Any]
            Line definition containing route and section parameters.
        default_depth : float, optional
            Default depth value to use for stations. Default is -9999.0.

        Returns
        -------
        list[dict[str, Any]]
            List of station definitions along the section.
        """
        from cruiseplan.calculators.distance import haversine_distance
        from cruiseplan.utils.plot_config import interpolate_great_circle_position

        if not section.get("route") or len(section["route"]) < 2:
            return []

        start = section["route"][0]
        end = section["route"][-1]
        # Extract coordinates from GeoPoint objects
        start_lat = start.latitude
        start_lon = start.longitude
        end_lat = end.latitude
        end_lon = end.longitude

        if any(coord is None for coord in [start_lat, start_lon, end_lat, end_lon]):
            return []

        total_distance_km = haversine_distance(
            (start_lat, start_lon), (end_lat, end_lon)
        )
        spacing_km = section.get("distance_between_stations", 20.0)
        num_stations = max(2, int(total_distance_km / spacing_km) + 1)

        stations = []
        base_name = self._sanitize_name_for_stations(section["name"])

        for i in range(num_stations):
            fraction = i / (num_stations - 1) if num_stations > 1 else 0
            lat, lon = interpolate_great_circle_position(
                start_lat, start_lon, end_lat, end_lon, fraction
            )

            # Generate unique station name (handle duplicates)
            base_station_name = f"{base_name}_Stn{i+1:03d}"
            station_name = self._generate_unique_name(base_station_name)

            station = {
                "name": station_name,
                OP_TYPE_FIELD: "CTD",
                ACTION_FIELD: "profile",
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "comment": f"Station {i+1}/{num_stations} on {section['name']} section",
                DURATION_FIELD: 120.0,
            }

            # Add depth if available
            if "max_depth" in section:
                station[WATER_DEPTH_FIELD] = section["max_depth"]
            elif default_depth != -9999.0:
                station[WATER_DEPTH_FIELD] = default_depth

            # Add duration if specified
            if (
                "planned_duration_hours" in section
                and section["planned_duration_hours"] is not None
            ):
                station[DURATION_FIELD] = (
                    float(section["planned_duration_hours"]) * 60.0
                )
            elif DURATION_FIELD in section and section[DURATION_FIELD] is not None:
                station[DURATION_FIELD] = float(section[DURATION_FIELD])

            stations.append(station)

        return stations

    def _generate_unique_name(self, base_name: str) -> str:
        """
        Generate a unique name by checking against existing point registry.

        If the base name already exists, append _1, _2, etc. until a unique name is found.

        Parameters
        ----------
        base_name : str
            The base name to make unique.

        Returns
        -------
        str
            A unique name that doesn't exist in the point registry.
        """
        if base_name not in self.point_registry:
            return base_name

        # Name exists, find unique suffix (using legacy format _01, _02, etc.)
        counter = 1
        while f"{base_name}_{counter:02d}" in self.point_registry:
            counter += 1

        return f"{base_name}_{counter:02d}"

    def _sanitize_name_for_stations(self, name: str) -> str:
        """
        Sanitize a name for use as a station name base.

        Removes special characters, converts Unicode to ASCII, and ensures
        the result contains only alphanumeric characters and underscores.

        Parameters
        ----------
        name : str
            Original name to sanitize.

        Returns
        -------
        str
            Sanitized name suitable for station naming.
        """
        import re
        import unicodedata

        # Convert Unicode to ASCII equivalent
        name = unicodedata.normalize("NFD", name)
        name = name.encode("ascii", "ignore").decode("ascii")

        # Replace common separators and special chars with underscores
        name = re.sub(r"[^\w\s]", "_", name)  # Replace non-word chars (except spaces)
        name = re.sub(r"\s+", "_", name)  # Replace spaces with underscores

        # Clean up multiple consecutive underscores
        name = re.sub(r"_+", "_", name)

        # Remove leading and trailing underscores
        name = name.strip("_")

        # If name becomes empty, provide a fallback
        if not name:
            name = "Section"

        return name

    def enrich_depths(
        self, bathymetry_source: str = "etopo2022", bathymetry_dir: str = "data"
    ) -> set[str]:
        """
        Add bathymetry depths to stations that are missing water_depth values.

        This method modifies the point_registry directly by adding water depth
        information from bathymetry datasets to stations that don't have depth
        values or have placeholder values.

        Parameters
        ----------
        bathymetry_source : str, optional
            Bathymetry dataset to use. Default is "etopo2022".
        bathymetry_dir : str, optional
            Directory containing bathymetry data. Default is "data".

        Returns
        -------
        set[str]
            Set of station names that had depths added.
        """
        from cruiseplan.data.bathymetry import BathymetryManager

        stations_with_depths_added = set()

        # Initialize bathymetry manager
        bathymetry = BathymetryManager(
            source=bathymetry_source, data_dir=bathymetry_dir
        )

        # Process each station in the point registry
        for _, station in self.point_registry.items():
            # Check if station needs water depth
            should_add_water_depth = (
                not hasattr(station, "water_depth")
                or station.water_depth is None
                or station.water_depth == -9999.0  # Replace placeholder depth
            )

            if should_add_water_depth:
                depth = bathymetry.get_depth_at_point(
                    station.latitude, station.longitude
                )
                if depth is not None and depth != 0:
                    # Modify the station object directly
                    station.water_depth = round(abs(depth))  # Convert to positive depth
                    stations_with_depths_added.add(station.name)

        return stations_with_depths_added

    def add_station_defaults(self) -> int:
        """
        Add missing defaults to station definitions.

        This method adds default duration to mooring operations and other stations
        that lack required default values.

        Returns
        -------
        int
            Number of station defaults added.
        """
        station_defaults_added = 0

        # Process each station in the point registry
        for _, station in self.point_registry.items():
            # Check for mooring operations without duration
            if (
                hasattr(station, "operation_type")
                and station.operation_type == "mooring"
                and (not hasattr(station, "duration") or station.duration is None)
            ):
                from cruiseplan.utils.defaults import DEFAULT_MOORING_DURATION_MIN

                # Add default mooring duration
                station.duration = DEFAULT_MOORING_DURATION_MIN
                station_defaults_added += 1

        return station_defaults_added

    def expand_ports(self) -> dict[str, int]:
        """
        Expand global port references into full PortDefinition objects.

        This method finds string port references and expands them into full
        PortDefinition objects with coordinates and other metadata from the
        global ports database.

        Returns
        -------
        dict[str, int]
            Dictionary with expansion summary:
            - ports_expanded: Number of global ports expanded
            - leg_ports_expanded: Number of leg ports expanded
        """
        from cruiseplan.utils.global_ports import resolve_port_reference

        ports_expanded_count = 0
        leg_ports_expanded = 0

        # Expand departure and arrival ports if they are string references
        if isinstance(self.config.departure_port, str):
            try:
                port_obj = resolve_port_reference(self.config.departure_port)
                self.config.departure_port = port_obj
                ports_expanded_count += 1
            except ValueError:
                pass  # Keep as string reference if can't resolve

        if isinstance(self.config.arrival_port, str):
            try:
                port_obj = resolve_port_reference(self.config.arrival_port)
                self.config.arrival_port = port_obj
                ports_expanded_count += 1
            except ValueError:
                pass  # Keep as string reference if can't resolve

        # Expand leg-level port references
        for leg in self.runtime_legs:
            if hasattr(leg, "departure_port") and isinstance(leg.departure_port, str):
                try:
                    port_obj = resolve_port_reference(leg.departure_port)
                    leg.departure_port = port_obj
                    leg_ports_expanded += 1
                except ValueError:
                    # If global port resolution fails, keep as string reference
                    pass

            if hasattr(leg, "arrival_port") and isinstance(leg.arrival_port, str):
                try:
                    port_obj = resolve_port_reference(leg.arrival_port)
                    leg.arrival_port = port_obj
                    leg_ports_expanded += 1
                except ValueError:
                    # If global port resolution fails, keep as string reference
                    pass

        return {
            "ports_expanded": ports_expanded_count,
            "leg_ports_expanded": leg_ports_expanded,
        }

    def add_coordinate_displays(self, coord_format: str = "ddm") -> int:
        """
        Add human-readable coordinate display fields for final YAML output.

        This method adds formatted coordinate annotations that will appear in
        the YAML output but don't affect the core cruise data. This is for
        display enhancement only.

        Parameters
        ----------
        coord_format : str, optional
            Coordinate format to use for display. Default is "ddm".

        Returns
        -------
        int
            Number of coordinate display fields added.
        """
        coord_changes_made = 0

        # Add coordinate displays for points that have coordinates but lack display fields
        for _, point in self.point_registry.items():
            if (
                hasattr(point, "latitude")
                and hasattr(point, "longitude")
                and point.latitude is not None
                and point.longitude is not None
            ):

                # For now, we'll add the coordinate display as a "position_string" field
                # This will be used for display purposes in the output
                if coord_format == "ddm":
                    from cruiseplan.utils.coordinates import format_ddm_comment

                    position_display = format_ddm_comment(
                        point.latitude, point.longitude
                    )
                    # Set the position string for display (this gets used in YAML output)
                    point.position_string = position_display
                    coord_changes_made += 1

        return coord_changes_made
