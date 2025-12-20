from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from cruiseplan.core.validation import (
    AreaDefinition,
    StationDefinition,
    TransitDefinition,
)
from cruiseplan.utils.constants import NM_PER_KM


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

    @abstractmethod
    def get_entry_point(self) -> tuple[float, float]:
        """
        Get the geographic entry point for this operation.

        For point operations (stations, moorings): same as operation location.
        For line operations (transits): start of the route.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the operation's entry point.
        """
        pass

    @abstractmethod
    def get_exit_point(self) -> tuple[float, float]:
        """
        Get the geographic exit point for this operation.

        For point operations (stations, moorings): same as operation location.
        For line operations (transits): end of the route.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the operation's exit point.
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

    def get_entry_point(self) -> tuple[float, float]:
        """
        Get the geographic entry point for this point operation.

        For point operations, entry and exit are the same location.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the operation location.
        """
        return self.position

    def get_exit_point(self) -> tuple[float, float]:
        """
        Get the geographic exit point for this point operation.

        For point operations, entry and exit are the same location.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the operation location.
        """
        return self.position

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

        # Use operation_depth for duration calculations, fallback to water_depth if needed
        operation_depth = obj.operation_depth or obj.water_depth or 0.0

        return cls(
            name=obj.name,
            position=pos,
            depth=operation_depth,  # This is now operation_depth for duration calculations
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
        Calculate duration for the line operation based on route distance and vessel speed.

        Parameters
        ----------
        rules : Any
            Duration calculation rules containing config with default_vessel_speed.

        Returns
        -------
        float
            Duration in minutes.
        """
        if not self.route or len(self.route) < 2:
            return 0.0

        # Import here to avoid circular imports
        from cruiseplan.calculators.distance import haversine_distance

        # Calculate total route distance by summing distances between consecutive waypoints
        total_route_distance_km = 0.0
        for i in range(len(self.route) - 1):
            start_point = self.route[i]
            end_point = self.route[i + 1]
            segment_distance = haversine_distance(start_point, end_point)
            total_route_distance_km += segment_distance

        # Convert to nautical miles
        route_distance_nm = total_route_distance_km * NM_PER_KM  # km to nautical miles

        # Use transit-specific vessel speed if provided, otherwise use default
        vessel_speed = self.speed
        if not vessel_speed and hasattr(rules, "config"):
            vessel_speed = getattr(rules.config, "default_vessel_speed", 10.0)
        elif not vessel_speed:
            vessel_speed = 10.0  # Fallback if no rules provided

        # Calculate duration in hours, then convert to minutes
        duration_hours = route_distance_nm / vessel_speed
        return duration_hours * 60.0

    def get_entry_point(self) -> tuple[float, float]:
        """
        Get the geographic entry point for this line operation.

        For line operations, this is the start of the route.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the route start point.
        """
        if not self.route:
            return (0.0, 0.0)  # Fallback for empty routes
        return self.route[0]

    def get_exit_point(self) -> tuple[float, float]:
        """
        Get the geographic exit point for this line operation.

        For line operations, this is the end of the route.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the route end point.
        """
        if not self.route:
            return (0.0, 0.0)  # Fallback for empty routes
        return self.route[-1]

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
    duration : Optional[float]
        User-specified duration in minutes (required like moorings).
    start_point : Tuple[float, float]
        Starting position for area operation (latitude, longitude).
    end_point : Tuple[float, float]
        Ending position for area operation (latitude, longitude).
    """

    def __init__(
        self,
        name: str,
        boundary_polygon: List[Tuple[float, float]],
        area_km2: float,
        duration: Optional[float] = None,
        start_point: Optional[Tuple[float, float]] = None,
        end_point: Optional[Tuple[float, float]] = None,
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
        duration : Optional[float], optional
            User-specified duration in minutes (required for scheduling).
        start_point : Optional[Tuple[float, float]], optional
            Starting position (latitude, longitude). Defaults to first corner.
        end_point : Optional[Tuple[float, float]], optional
            Ending position (latitude, longitude). Defaults to last corner.
        sampling_density : float, optional
            Sampling density factor for duration calculations (default: 1.0).
        comment : str, optional
            Human-readable comment or description.
        """
        super().__init__(name, comment)
        self.boundary_polygon = boundary_polygon
        self.area_km2 = area_km2
        self.duration = duration
        self.sampling_density = sampling_density

        # Set start/end points, defaulting to first/last corners if not specified
        self.start_point = start_point or (
            boundary_polygon[0] if boundary_polygon else (0.0, 0.0)
        )
        self.end_point = end_point or (
            boundary_polygon[-1] if boundary_polygon else (0.0, 0.0)
        )

    def calculate_duration(self, rules: Any) -> float:
        """
        Calculate duration using user-specified duration or fallback formula.

        For area operations, duration must be specified by the user (like moorings)
        since area coverage patterns are highly variable.

        Parameters
        ----------
        rules : Any
            Duration calculation rules and parameters (unused for area operations).

        Returns
        -------
        float
            Duration in minutes.

        Raises
        ------
        ValueError
            If duration is not specified by user.
        """
        if self.duration is not None:
            return self.duration
        else:
            raise ValueError(
                f"Area operation '{self.name}' requires user-specified duration. "
                "Add 'duration: <minutes>' to the area definition in YAML."
            )

    def get_entry_point(self) -> tuple[float, float]:
        """
        Get the geographic entry point for this area operation.

        For area operations, this is the start point of the survey pattern.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the area entry point.
        """
        return self.start_point

    def get_exit_point(self) -> tuple[float, float]:
        """
        Get the geographic exit point for this area operation.

        For area operations, this is the end point of the survey pattern.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the area exit point.
        """
        return self.end_point

    @classmethod
    def from_pydantic(cls, obj: AreaDefinition) -> "AreaOperation":
        """
        Factory to create an area operation from a validated Pydantic model.

        Parameters
        ----------
        obj : AreaDefinition
            Validated Pydantic area definition model.

        Returns
        -------
        AreaOperation
            New AreaOperation instance.

        Raises
        ------
        ValueError
            If duration is not specified in the area definition.
        """
        if obj.duration is None:
            raise ValueError(
                f"Area operation '{obj.name}' requires user-specified duration. "
                "Add 'duration: <minutes>' to the area definition in YAML."
            )

        # Convert List[GeoPoint] -> List[tuple]
        boundary_tuples = [(p.latitude, p.longitude) for p in obj.corners]

        # Calculate approximate area using shoelace formula
        area_km2 = cls._calculate_polygon_area(boundary_tuples)

        # Use first and last corners as start/end points
        start_point = boundary_tuples[0] if boundary_tuples else (0.0, 0.0)
        end_point = boundary_tuples[-1] if boundary_tuples else (0.0, 0.0)

        return cls(
            name=obj.name,
            boundary_polygon=boundary_tuples,
            area_km2=area_km2,
            duration=obj.duration,
            start_point=start_point,
            end_point=end_point,
            comment=obj.comment,
        )

    @staticmethod
    def _calculate_polygon_area(coords: List[Tuple[float, float]]) -> float:
        """
        Calculate polygon area using shoelace formula.

        Parameters
        ----------
        coords : List[Tuple[float, float]]
            List of (latitude, longitude) tuples.

        Returns
        -------
        float
            Area in square kilometers (approximate).
        """
        if len(coords) < 3:
            return 0.0

        # Simple shoelace formula for approximate area
        # Note: This assumes small areas where lat/lon can be treated as Cartesian
        # For more accurate results, should use spherical geometry
        n = len(coords)
        area = 0.0

        for i in range(n):
            j = (i + 1) % n
            area += coords[i][0] * coords[j][1]
            area -= coords[j][0] * coords[i][1]

        area = abs(area) / 2.0

        # Rough conversion from lat/lon degrees to km²
        # (very approximate, assumes mid-latitude ~45°)
        km_per_degree = 111.0  # Rough conversion
        area_km2 = area * (km_per_degree**2)

        return area_km2
