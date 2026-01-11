"""
Core cruise management and organizational runtime classes.

This module provides the main Cruise class for loading, validating, and managing
cruise configurations from YAML files, along with the organizational runtime
classes (Leg, Cluster) that form the hierarchical structure for cruise execution.
The BaseOrganizationUnit abstract base class provides the common interface for
all organizational units in the cruise planning hierarchy.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

from cruiseplan.core.operations import BaseOperation
from cruiseplan.schema import (
    PointDefinition,
    LineDefinition,
    AreaDefinition,
    ClusterDefinition,
    LegDefinition,
    CruiseConfig,
    StrategyEnum,
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
            The operation to add (e.g., a single CTD cast or transit).
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

    def calculate_total_duration(self, rules: Any) -> float:
        """
        Calculate total duration for all operations in this leg.

        Includes port-to-port transit time, standalone operations, and cluster
        operations with proper boundary management.

        Parameters
        ----------
        rules : Any
            Duration calculation rules/parameters containing config.

        Returns
        -------
        float
            Total duration in minutes including all operations and transits.
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

    def _calculate_port_to_port_transit(self, rules: Any) -> float:
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
class Cruise:
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
        Initialize a Cruise object from a YAML configuration file.

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
        # Determine definition type based on key fields
        if "operation_type" in definition_dict:
            return PointDefinition(**definition_dict)
        elif "start" in definition_dict and "end" in definition_dict:
            return LineDefinition(**definition_dict)
        elif any(
            field in definition_dict for field in ["polygon", "center", "boundary"]
        ):
            # This is an area definition
            return AreaDefinition(**definition_dict)
        # Fallback: assume it's a station if it has common station fields
        elif any(
            field in definition_dict
            for field in ["latitude", "longitude", "position", "action"]
        ):
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
    def from_dict(cls, config_dict: dict[str, Any]) -> "Cruise":
        """
        Create a Cruise instance from a dictionary without file I/O.

        This class method provides single source of truth functionality by creating
        a Cruise object directly from a configuration dictionary, eliminating the
        need for temporary file creation during enrichment operations.

        Parameters
        ----------
        config_dict : Dict[str, Any]
            Dictionary containing cruise configuration data (e.g., from YAML parsing).

        Returns
        -------
        Cruise
            New Cruise instance with all registries built and references resolved.

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
        >>> cruise = Cruise.from_dict(config)
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
        Export Cruise configuration to a structured dictionary with comment preservation.

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
        output = {}

        # 1. Cruise Metadata
        output["cruise_name"] = self.config.cruise_name
        if self.config.description:
            output["description"] = self.config.description
        output["start_date"] = self.config.start_date
        if self.config.start_time:
            output["start_time"] = self.config.start_time

        # 2. Vessel Parameters
        output["default_vessel_speed"] = self.config.default_vessel_speed
        output["default_distance_between_stations"] = self.config.default_distance_between_stations
        output["turnaround_time"] = self.config.turnaround_time
        output["ctd_descent_rate"] = self.config.ctd_descent_rate
        output["ctd_ascent_rate"] = self.config.ctd_ascent_rate

        # 3. Calculation Settings
        output["calculate_transfer_between_sections"] = self.config.calculate_transfer_between_sections
        output["calculate_depth_via_bathymetry"] = self.config.calculate_depth_via_bathymetry
        output["day_start_hour"] = self.config.day_start_hour
        output["day_end_hour"] = self.config.day_end_hour
        output["station_label_format"] = self.config.station_label_format
        output["mooring_label_format"] = self.config.mooring_label_format

        # 3b. Single-leg cruise ports (if applicable)
        if self.config.departure_port:
            output["departure_port"] = self._serialize_point_definition(self.config.departure_port)
        if self.config.arrival_port:
            output["arrival_port"] = self._serialize_point_definition(self.config.arrival_port)

        # 4. Catalog Definitions
        if self.config.points:
            output["points"] = [self._serialize_point_definition(p) for p in self.config.points]
        if self.config.lines:
            output["lines"] = [self._serialize_line_definition(l) for l in self.config.lines]
        if self.config.areas:
            output["areas"] = [self._serialize_area_definition(a) for a in self.config.areas]
        if self.config.ports:
            output["ports"] = [self._serialize_point_definition(p) for p in self.config.ports]

        # 5. Schedule Organization
        if self.config.legs:
            output["legs"] = [self._serialize_leg_definition(leg) for leg in self.config.legs]

        return output

    def _serialize_point_definition(self, point: PointDefinition) -> dict[str, Any]:
        """Serialize a PointDefinition to dictionary format."""
        return point.model_dump(exclude_none=True)

    def _serialize_line_definition(self, line: LineDefinition) -> dict[str, Any]:
        """Serialize a LineDefinition to dictionary format."""
        return line.model_dump(exclude_none=True)

    def _serialize_area_definition(self, area: AreaDefinition) -> dict[str, Any]:
        """Serialize an AreaDefinition to dictionary format."""
        return area.model_dump(exclude_none=True)

    def _serialize_leg_definition(self, leg: LegDefinition) -> dict[str, Any]:
        """Serialize a LegDefinition to dictionary format."""
        leg_dict = leg.model_dump(exclude_none=True)
        
        # Handle port serialization
        if isinstance(leg_dict.get("departure_port"), PointDefinition):
            leg_dict["departure_port"] = leg_dict["departure_port"].model_dump(exclude_none=True)
        if isinstance(leg_dict.get("arrival_port"), PointDefinition):
            leg_dict["arrival_port"] = leg_dict["arrival_port"].model_dump(exclude_none=True)
            
        return leg_dict

    def to_yaml(self, output_path: Union[str, Path]) -> None:
        """
        Export Cruise configuration to YAML file with canonical ordering.

        This method provides direct YAML export capability with standardized
        field ordering and basic comment preservation. Uses ruamel.yaml for
        structured output that maintains readability.

        Parameters
        ----------
        output_path : Union[str, Path]
            Path where the YAML file should be written.

        Raises
        ------
        IOError
            If the output file cannot be written.

        Examples
        --------
        >>> cruise = Cruise.from_dict(config_dict)
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
        yaml.representer.add_representer(type(None), lambda dumper, value: dumper.represent_scalar('tag:yaml.org,2002:null', ''))

        with output_path.open("w", encoding="utf-8") as f:
            # Write file-level comment
            f.write("# Cruise configuration generated by CruisePlan\n")
            f.write("# Canonical field ordering enforced for consistency\n\n")
            
            yaml.dump(output_dict, f)
