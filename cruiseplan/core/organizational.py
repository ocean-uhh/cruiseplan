"""
Organizational unit classes for cruise planning.

This module contains the hierarchical organizational classes (BaseOrganizationUnit,
Cluster, Leg) that form the structural framework for cruise execution and scheduling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from cruiseplan.core.operations import BaseOperation
from cruiseplan.schema.activities import PointDefinition
from cruiseplan.schema.cruise_config import ClusterDefinition, LegDefinition
from cruiseplan.schema.ports import resolve_port_reference
from cruiseplan.schema.values import StrategyEnum
from cruiseplan.utils.units import NM_PER_KM

logger = logging.getLogger(__name__)


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
            Scheduling strategy for operations within this cluster.
            Default is StrategyEnum.SEQUENTIAL.
        ordered : bool, optional
            Whether operations should maintain their defined order.
            Default is True (strict ordering).
        """
        self.name = name
        self.description = description
        self.strategy = strategy
        self.ordered = ordered
        self.operations: list[BaseOperation] = []

    def add_operation(self, operation: BaseOperation) -> None:
        """
        Add an operation to this cluster.

        The operation is added to the end of the cluster's operation list.
        For ordered clusters, this determines the execution sequence.

        Parameters
        ----------
        operation : BaseOperation
            The operation to add to this cluster.

        Raises
        ------
        ValueError
            If operation with the same name already exists in cluster.
        """
        # Check for name conflicts within the cluster
        if any(op.name == operation.name for op in self.operations):
            raise ValueError(
                f"Operation '{operation.name}' already exists in cluster '{self.name}'"
            )

        self.operations.append(operation)
        logger.debug(f"Added operation {operation.name} to cluster {self.name}")

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
                removed_op = self.operations.pop(i)
                logger.debug(
                    f"Removed operation {removed_op.name} from cluster {self.name}"
                )
                return True
        return False

    def get_operation(self, operation_name: str) -> Optional[BaseOperation]:
        """
        Get an operation from this cluster by name.

        Parameters
        ----------
        operation_name : str
            Name of the operation to find.

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
        Get all operations within this cluster.

        Returns operations in their current order. For ordered clusters,
        this represents the required execution sequence.

        Returns
        -------
        List[BaseOperation]
            List of all operations in this cluster.
        """
        return self.operations.copy()

    def calculate_total_duration(self, rules: Any) -> float:
        """
        Calculate total duration for all operations in this cluster.

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Total duration in hours for all operations in cluster.
        """
        total_hours = 0.0
        for operation in self.operations:
            if hasattr(operation, "calculate_duration"):
                total_hours += operation.calculate_duration(rules)
        return total_hours

    def is_empty(self) -> bool:
        """
        Check if this cluster contains any operations.

        Returns
        -------
        bool
            True if cluster has no operations, False otherwise.
        """
        return len(self.operations) == 0

    def get_operation_count(self) -> int:
        """
        Get total number of operations in this cluster.

        Returns
        -------
        int
            Number of operations in this cluster.
        """
        return len(self.operations)

    def allows_reordering(self) -> bool:
        """
        Check if this cluster allows operation reordering.

        Returns
        -------
        bool
            True if operations can be reordered, False if strict order required.
        """
        return not self.ordered

    def get_operation_names(self) -> list[str]:
        """
        Get names of all operations in this cluster.

        Returns
        -------
        List[str]
            List of operation names in cluster order.
        """
        return [op.name for op in self.operations]

    def get_entry_point(self) -> Optional[tuple[float, float]]:
        """
        Get geographic entry point for this cluster.

        Returns the coordinates of the first operation in the cluster.

        Returns
        -------
        Optional[Tuple[float, float]]
            (latitude, longitude) of entry point, or None if cluster is empty.
        """
        if self.operations:
            first_op = self.operations[0]
            if hasattr(first_op, "latitude") and hasattr(first_op, "longitude"):
                return (first_op.latitude, first_op.longitude)
        return None

    def get_exit_point(self) -> Optional[tuple[float, float]]:
        """
        Get geographic exit point for this cluster.

        Returns the coordinates of the last operation in the cluster.

        Returns
        -------
        Optional[Tuple[float, float]]
            (latitude, longitude) of exit point, or None if cluster is empty.
        """
        if self.operations:
            last_op = self.operations[-1]
            if hasattr(last_op, "latitude") and hasattr(last_op, "longitude"):
                return (last_op.latitude, last_op.longitude)
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"Cluster(name='{self.name}', strategy={self.strategy.name}, "
            f"ordered={self.ordered}, operations={len(self.operations)})"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        order_str = "strict order" if self.ordered else "flexible order"
        return (
            f"Cluster '{self.name}' ({order_str}, {len(self.operations)} operations, "
            f"strategy: {self.strategy.name})"
        )

    @classmethod
    def from_definition(cls, cluster_def: ClusterDefinition) -> "Cluster":
        """
        Create a Cluster instance from a ClusterDefinition.

        Parameters
        ----------
        cluster_def : ClusterDefinition
            The cluster definition to convert.

        Returns
        -------
        Cluster
            New Cluster instance with parameters from definition.
        """
        strategy = getattr(cluster_def, "strategy", None)
        if strategy is None:
            strategy = StrategyEnum.SEQUENTIAL
        ordered = getattr(cluster_def, "ordered", None)
        if ordered is None:
            ordered = True
        description = getattr(cluster_def, "description", None)

        return cls(
            name=cluster_def.name,
            description=description,
            strategy=strategy,
            ordered=ordered,
        )


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
