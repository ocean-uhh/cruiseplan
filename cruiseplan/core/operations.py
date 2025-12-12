from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from cruiseplan.core.validation import (
    StationDefinition,
    TransitDefinition,
)


class BaseOperation(ABC):
    """
    Abstract base class for all cruise operations.

    This class defines the common interface that all cruise operations must
    implement, providing a foundation for different types of oceanographic
    activities.

    Attributes
    ----------
    name : str
        Unique identifier for this operation.
    comment : Optional[str]
        Optional human-readable comment or description.
    """

    def __init__(self, name: str, comment: Optional[str] = None):
        """
        Initialize a base operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        comment : Optional[str], optional
            Human-readable comment or description.
        """
        self.name = name
        self.comment = comment

    @abstractmethod
    def calculate_duration(self, rules: Any) -> float:
        """
        Calculate duration in minutes based on provided rules.

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Duration in minutes.
        """
        pass


class PointOperation(BaseOperation):
    """
    Atomic activity at a fixed location.

    Handles both Stations (CTD casts) and Moorings (deploy/recover operations).
    Represents the most basic unit of work in a cruise plan.

    Attributes
    ----------
    position : tuple
        Geographic position as (latitude, longitude).
    depth : float
        Operation depth in meters.
    manual_duration : float
        User-specified duration override in minutes.
    op_type : str
        Type of operation ('station' or 'mooring').
    action : str
        Specific action for moorings (deploy/recover).
    """

    def __init__(
        self,
        name: str,
        position: tuple,
        depth: float = 0.0,
        duration: float = 0.0,
        comment: str = None,
        op_type: str = "station",
        action: str = None,
    ):
        """
        Initialize a point operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        position : tuple
            Geographic position as (latitude, longitude).
        depth : float, optional
            Operation depth in meters (default: 0.0).
        duration : float, optional
            Manual duration override in minutes (default: 0.0).
        comment : str, optional
            Human-readable comment or description.
        op_type : str, optional
            Type of operation ('station' or 'mooring', default: 'station').
        action : str, optional
            Specific action for moorings (deploy/recover).
        """
        super().__init__(name, comment)
        self.position = position  # (lat, lon)
        self.depth = depth
        self.manual_duration = duration
        self.op_type = op_type
        self.action = action  # Specific to Moorings

    def calculate_duration(self, rules: Any) -> float:
        """
        Calculate duration based on operation type and rules.

        Uses manual duration if specified, otherwise calculates based on
        operation type (CTD time for stations, default duration for moorings).

        Parameters
        ----------
        rules : Any
            Duration calculation rules containing config.

        Returns
        -------
        float
            Duration in minutes.
        """
        # Phase 2 Logic: Manual duration always wins
        if self.manual_duration > 0:
            return self.manual_duration

        # Import calculator
        from cruiseplan.calculators.duration import DurationCalculator

        if not hasattr(rules, "config"):
            return 0.0

        calc = DurationCalculator(rules.config)

        if self.op_type == "station":
            return calc.calculate_ctd_time(self.depth)
        elif self.op_type == "mooring":
            # Moorings should have manual duration, but fallback to default
            return (
                rules.config.default_mooring_duration
                if hasattr(rules.config, "default_mooring_duration")
                else 60.0
            )

        return 0.0

    @classmethod
    def from_pydantic(cls, obj: StationDefinition) -> "PointOperation":
        """
        Factory to create a logical operation from a validated Pydantic model.

        Handles the internal 'position' normalization done by FlexibleLocationModel.

        Parameters
        ----------
        obj : StationDefinition
            Validated Pydantic station definition model.

        Returns
        -------
        PointOperation
            New PointOperation instance.
        """
        # 1. Extract Position (Guaranteed by validation.py to exist)
        pos = (obj.position.latitude, obj.position.longitude)

        # 2. Map operation types to legacy internal types
        op_type_mapping = {
            "CTD": "station",
            "water_sampling": "station",
            "calibration": "station",
            "mooring": "mooring",
        }

        internal_op_type = op_type_mapping.get(obj.operation_type.value, "station")
        action = obj.action.value if obj.action else None

        return cls(
            name=obj.name,
            position=pos,
            depth=obj.depth if obj.depth else 0.0,
            duration=obj.duration if obj.duration else 0.0,
            comment=obj.comment,
            op_type=internal_op_type,
            action=action,
        )


class LineOperation(BaseOperation):
    """
    Continuous activity involving movement (Transit, Towyo).

    Represents operations that involve traveling between points, such as
    vessel transits or towed instrument deployments.

    Attributes
    ----------
    route : List[tuple]
        List of geographic waypoints as (latitude, longitude) tuples.
    speed : float
        Vessel speed in knots.
    """

    def __init__(
        self, name: str, route: List[tuple], speed: float = 10.0, comment: str = None
    ):
        """
        Initialize a line operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        route : List[tuple]
            List of geographic waypoints as (latitude, longitude) tuples.
        speed : float, optional
            Vessel speed in knots (default: 10.0).
        comment : str, optional
            Human-readable comment or description.
        """
        super().__init__(name, comment)
        self.route = route  # List of (lat, lon)
        self.speed = speed

    def calculate_duration(self, rules: Any) -> float:
        """
        Calculate duration for the line operation.

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Duration in minutes.
        """
        # Placeholder for Phase 2 distance calculation
        return 0.0

    @classmethod
    def from_pydantic(
        cls, obj: TransitDefinition, default_speed: float
    ) -> "LineOperation":
        """
        Factory to create a line operation from a validated Pydantic model.

        Parameters
        ----------
        obj : TransitDefinition
            Validated Pydantic transit definition model.
        default_speed : float
            Default vessel speed to use if not specified in the model.

        Returns
        -------
        LineOperation
            New LineOperation instance.
        """
        # Convert List[GeoPoint] -> List[tuple]
        route_tuples = [(p.latitude, p.longitude) for p in obj.route]

        return cls(
            name=obj.name,
            route=route_tuples,
            speed=obj.vessel_speed if obj.vessel_speed else default_speed,
            comment=obj.comment,
        )


class CompositeOperation(BaseOperation):
    """
    Logical container for grouping related PointOperations or other BaseOperations.

    Examples: "53N Section" (20 CTDs), "OSNAP Array" (Mixed CTDs + Moorings).
    Provides different scheduling strategies for optimizing execution order.

    Attributes
    ----------
    children : List[BaseOperation]
        List of child operations contained within this composite.
    geometry_definition : Optional[Any]
        Geometric definition (LineString or Polygon) for spatial operations.
    scheduling_strategy : str
        Strategy for scheduling child operations ('sequential', 'spatial_interleaved', 'day_night_split').
    ordered : bool
        Whether the order of operations should be preserved.
    """

    def __init__(
        self,
        name: str,
        children: List[BaseOperation],
        geometry_definition: Optional[Any] = None,  # LineString or Polygon
        scheduling_strategy: str = "sequential",
        ordered: bool = True,
        comment: str = None,
    ):
        """
        Initialize a composite operation.

        Parameters
        ----------
        name : str
            Unique identifier for this composite operation.
        children : List[BaseOperation]
            List of child operations to contain.
        geometry_definition : Optional[Any], optional
            Geometric definition for spatial operations.
        scheduling_strategy : str, optional
            Scheduling strategy ('sequential', 'spatial_interleaved', 'day_night_split', default: 'sequential').
        ordered : bool, optional
            Whether to preserve operation order (default: True).
        comment : str, optional
            Human-readable comment or description.
        """
        super().__init__(name, comment)
        self.children = children
        self.geometry_definition = geometry_definition
        self.scheduling_strategy = scheduling_strategy
        self.ordered = ordered

    def calculate_duration(self, rules: Any) -> float:
        """
        Calculate total duration by solving internal routing logic.

        Accounts for strategy (sequential, day_night_split, spatial_interleaved).

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Total duration in minutes.
        """
        if not self.children:
            return 0.0

        # Import here to avoid circular imports
        from cruiseplan.calculators.routing import optimize_composite_route

        if self.scheduling_strategy == "sequential":
            return sum(child.calculate_duration(rules) for child in self.children)
        elif self.scheduling_strategy == "spatial_interleaved":
            return optimize_composite_route(self.children, rules)
        elif self.scheduling_strategy == "day_night_split":
            return self._calculate_day_night_duration(rules)
        else:
            # Default to sequential if strategy is unknown/invalid
            return sum(child.calculate_duration(rules) for child in self.children)

    def _calculate_day_night_duration(self, rules: Any) -> float:
        """
        Calculate duration for day/night split strategy.

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Duration in minutes.
        """
        # Implement zipper pattern logic from specs
        total_duration = 0.0
        # This is a placeholder - implement according to PROJECT_SPECS.md section 3.2
        for child in self.children:
            total_duration += child.calculate_duration(rules)
        return total_duration


class AreaOperation(BaseOperation):
    """
    Activities within defined polygonal regions.

    Examples: grid surveys, area monitoring, search patterns.
    Operations that cover a defined geographic area rather than specific points or lines.

    Attributes
    ----------
    boundary_polygon : List[Tuple[float, float]]
        List of (latitude, longitude) tuples defining the area boundary.
    area_km2 : float
        Area of the polygon in square kilometers.
    sampling_density : float
        Sampling density factor for duration calculations.
    """

    def __init__(
        self,
        name: str,
        boundary_polygon: List[Tuple[float, float]],
        area_km2: float,
        sampling_density: float = 1.0,
        comment: str = None,
    ):
        """
        Initialize an area operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        boundary_polygon : List[Tuple[float, float]]
            List of (latitude, longitude) tuples defining the area boundary.
        area_km2 : float
            Area of the polygon in square kilometers.
        sampling_density : float, optional
            Sampling density factor for duration calculations (default: 1.0).
        comment : str, optional
            Human-readable comment or description.
        """
        super().__init__(name, comment)
        self.boundary_polygon = boundary_polygon
        self.area_km2 = area_km2
        self.sampling_density = sampling_density

    def calculate_duration(self, rules: Any) -> float:
        """
        Calculate duration using area coverage models or user-defined formulas.

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Duration in minutes.
        """
        # Placeholder - implement area coverage calculation
        return self.area_km2 * self.sampling_density * 0.1  # Example formula
