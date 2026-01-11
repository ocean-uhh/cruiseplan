"""
Runtime operation classes for cruise planning activities.

Provides the business logic classes that represent active cruise operations.
These are the "core layer" that actually perform cruise planning work.

**Relationship to schema/definitions.py:**
- schema/definitions.py: Pydantic models that validate YAML → Python data
- This module: Runtime business objects that do the actual work

Example flow: YAML → PointDefinition (schema) → PointOperation (this module)

This module provides the base operation classes and specialized implementations
for stations, moorings, areas, and transects.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from cruiseplan.schema import (
    ACTION_FIELD,
    AreaDefinition,
    GeoPoint,
    LineDefinition,
    PointDefinition,
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

    def __init__(
        self,
        name: str,
        comment: Optional[str] = None,
        display_name: Optional[str] = None,
    ):
        """
        Initialize a base operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        comment : Optional[str], optional
            Human-readable comment or description.
        display_name : Optional[str], optional
            Human-readable display name for maps, CSV, and HTML output.
            Defaults to name if not provided.
        """
        self.name = name
        self.comment = comment
        self.display_name = display_name or name

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

    def get_coordinates(self) -> tuple[GeoPoint, GeoPoint]:
        """
        Get entry and exit coordinates as GeoPoint objects.

        Returns
        -------
        Tuple[GeoPoint, GeoPoint]
            (entry_point, exit_point) as GeoPoint objects.
        """
        entry = self.get_entry_point()
        exit = self.get_exit_point()
        return (
            GeoPoint(latitude=entry[0], longitude=entry[1]),
            GeoPoint(latitude=exit[0], longitude=exit[1]),
        )

    def get_operation_type(self) -> str:
        """
        Get operation type for timeline display.

        Returns
        -------
        str
            Operation type identifier (e.g., "Station", "Transit", "Area").
        """
        # Default implementation based on class name
        class_name = self.__class__.__name__
        return class_name.replace("Operation", "")

    def get_label(self) -> str:
        """
        Get human-readable label for this operation.

        Returns
        -------
        str
            Human-readable label, defaults to operation name.
        """
        # For ports, use display name if available
        if hasattr(self, "display_name") and self.display_name:
            # Extract just the city name (before comma) for cleaner display
            return self.display_name.split(",")[0].strip()

        return self.name


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
        operation_depth: Optional[float] = None,
        water_depth: float = 0.0,
        duration: float = 0.0,
        comment: Optional[str] = None,
        op_type: str = "station",
        action: Optional[str] = None,
        display_name: Optional[str] = None,
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
        super().__init__(name, comment, display_name)
        self.position = position  # (lat, lon)
        self.operation_depth = operation_depth
        self.water_depth = water_depth
        self.manual_duration = duration
        self.op_type = op_type
        self.action = action  # Specific to Moorings

    def get_depth(self) -> float:
        """
        Get the appropriate depth for this operation.

        Returns operation_depth if available, otherwise water_depth,
        otherwise 0.0.

        Returns
        -------
        float
            Depth in meters.
        """
        if self.operation_depth is not None:
            return self.operation_depth
        elif self.water_depth is not None:
            return self.water_depth
        else:
            return 0.0

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

        # TODO - why is ADCP on the list? what is this hardcoded list for?
        # Check for station-like operations (CTD, ADCP, etc.) that need CTD time calculation
        if self.op_type in ["station", "CTD", "ADCP", "XBT", "XCTD"] or (
            hasattr(self, "operation_depth")
            and self.operation_depth is not None
            and self.operation_depth > 0
        ):
            return calc.calculate_ctd_time(self.get_depth())
        # TODO: replace with default
        elif self.op_type == "mooring":
            # Moorings should have manual duration, but fallback to default
            return (
                rules.config.default_mooring_duration
                if hasattr(rules.config, "default_mooring_duration")
                else 60.0
            )
        elif self.op_type == "port":
            # Ports typically have no operation duration (mobilization/demobilization time is separate)
            return 0.0
        elif self.op_type == "waypoint":
            # Waypoints have no operation duration by default (waiting time is handled separately)
            return 0.0

        return 0.0

    # Todo, check why these arenot using geopoint.
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

    # What is this used for? probably belongs in vocabulary.py if it's just a lookup.
    def get_operation_type(self) -> str:
        """
        Get operation type for timeline display.

        Returns appropriate display type based on the op_type and action attributes.
        For ports, returns "Port_Departure" or "Port_Arrival" based on action.

        Returns
        -------
        str
            Operation type identifier ("Station", "Mooring", "Port_Departure", "Port_Arrival", etc.).
        """
        # Map internal op_types to display names
        type_mapping = {
            "station": "Station",
            "mooring": "Mooring",
            "port": "Port",
            "waypoint": "Waypoint",
        }
        return type_mapping.get(self.op_type, "Station")

    @classmethod
    def from_pydantic(cls, obj: PointDefinition) -> "PointOperation":
        """
        Factory to create a logical operation from a validated Pydantic model.

        Handles the internal 'position' normalization done by FlexibleLocationModel.

        Parameters
        ----------
        obj : PointDefinition
            Validated Pydantic station definition model.

        Returns
        -------
        PointOperation
            New PointOperation instance.
        """
        # 1. Extract Position (Guaranteed by validation.py to exist)
        pos = (obj.latitude, obj.longitude)

        # 2. Map operation types to legacy internal types
        # Use the original operation_type from YAML for display
        # The operation_class already tells us the implementation type
        if obj.operation_type:
            display_op_type = obj.operation_type.value
        elif (
            hasattr(obj, ACTION_FIELD)
            and obj.action
            and obj.action.value in PORT_ACTIONS  # ["mob", "demob"]
        ):
            # This is a port (has mob/demob action)
            display_op_type = "port"
        else:
            display_op_type = "station"
        action = obj.action.value if obj.action else None

        # Use water_depth as fallback for operation_depth
        operation_depth = (
            obj.operation_depth if obj.operation_depth is not None else obj.water_depth
        )

        return cls(
            name=obj.name,
            position=pos,
            operation_depth=operation_depth,
            water_depth=obj.water_depth,
            duration=obj.duration if obj.duration else 0.0,
            comment=obj.comment,
            op_type=display_op_type,
            action=action,
        )

    @classmethod
    def from_port(cls, obj: PointDefinition) -> "PointOperation":
        """
        Factory to create a PointOperation from a PointDefinition.

        Parameters
        ----------
        obj : PointDefinition
            Port definition model.

        Returns
        -------
        PointOperation
            New PointOperation instance representing a port.
        """
        pos = (obj.latitude, obj.longitude)

        return cls(
            name=obj.name,
            position=pos,
            operation_depth=None,  # Ports don't have operation depth
            water_depth=None,  # Ports don't need water depth
            duration=0.0,  # Ports have no operation duration
            comment=getattr(obj, "description", None),
            op_type="port",
            action=getattr(
                obj, ACTION_FIELD, "mob"
            ),  # Use port's action or default to mob
            display_name=getattr(obj, "display_name", None),
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
        self,
        name: str,
        route: list[tuple],
        speed: float = 10.0,
        comment: Optional[str] = None,
        display_name: Optional[str] = None,
        op_type: str = "line",
        action: Optional[str] = None,
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
        super().__init__(name, comment, display_name)
        self.route = route  # List of (lat, lon)
        self.speed = speed
        self.op_type = op_type
        self.action = action

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

        # Use centralized calculators
        from cruiseplan.calculators.distance import route_distance
        from cruiseplan.calculators.duration import DurationCalculator

        # Calculate route distance using centralized function
        route_distance_km = route_distance(self.route)

        # Use DurationCalculator if rules/config available
        if hasattr(rules, "config"):
            calc = DurationCalculator(rules.config)
            # Use default vessel speed if self.speed is 0 or None
            effective_speed = (
                self.speed
                if self.speed and self.speed > 0
                else rules.config.default_vessel_speed
            )
            return calc.calculate_transit_time(route_distance_km, effective_speed)
        else:
            # Fallback for cases without config
            from cruiseplan.utils.units import hours_to_minutes, km_to_nm

            vessel_speed = self.speed or 10.0
            route_distance_nm = km_to_nm(route_distance_km)
            duration_hours = route_distance_nm / vessel_speed
            return hours_to_minutes(duration_hours)

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

    def get_operation_distance_nm(self) -> float:
        """
        Calculate the total route distance for this line operation.

        Returns
        -------
        float
            Total route distance in nautical miles.
        """
        if not self.route or len(self.route) < 2:
            return 0.0

        # Use centralized calculators
        from cruiseplan.calculators.distance import route_distance
        from cruiseplan.utils.units import km_to_nm

        # Calculate route distance and convert to nautical miles
        route_distance_km = route_distance(self.route)
        return km_to_nm(route_distance_km)

    @classmethod
    def from_pydantic(
        cls, obj: LineDefinition, default_speed: float
    ) -> "LineOperation":
        """
        Factory to create a line operation from a validated Pydantic model.

        Parameters
        ----------
        obj : LineDefinition
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

        # Use the original operation_type from YAML for display
        display_op_type = obj.operation_type.value if obj.operation_type else "line"
        action = obj.action.value if obj.action else None

        return cls(
            name=obj.name,
            route=route_tuples,
            speed=obj.vessel_speed if obj.vessel_speed else default_speed,
            comment=obj.comment,
            display_name=getattr(obj, "display_name", None),
            op_type=display_op_type,
            action=action,
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
        Starting coordinates for area operation (latitude, longitude).
    end_point : Tuple[float, float]
        Ending coordinates for area operation (latitude, longitude).
    """

    def __init__(
        self,
        name: str,
        boundary_polygon: list[tuple[float, float]],
        area_km2: float,
        duration: Optional[float] = None,
        start_point: Optional[tuple[float, float]] = None,
        end_point: Optional[tuple[float, float]] = None,
        sampling_density: float = 1.0,
        comment: Optional[str] = None,
        display_name: Optional[str] = None,
        op_type: str = "area",
        action: Optional[str] = None,
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
            Starting coordinates (latitude, longitude). Defaults to first corner.
        end_point : Optional[Tuple[float, float]], optional
            Ending coordinates (latitude, longitude). Defaults to last corner.
        sampling_density : float, optional
            Sampling density factor for duration calculations (default: 1.0).
        comment : str, optional
            Human-readable comment or description.
        """
        super().__init__(name, comment, display_name)
        self.boundary_polygon = boundary_polygon
        self.area_km2 = area_km2
        self.duration = duration
        self.sampling_density = sampling_density
        self.op_type = op_type
        self.action = action

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

        # Use the original operation_type from YAML for display
        display_op_type = obj.operation_type.value if obj.operation_type else "area"
        action = obj.action.value if obj.action else None

        return cls(
            name=obj.name,
            boundary_polygon=boundary_tuples,
            area_km2=area_km2,
            duration=obj.duration,
            start_point=start_point,
            end_point=end_point,
            comment=obj.comment,
            display_name=getattr(obj, "display_name", None),
            op_type=display_op_type,
            action=action,
        )

    @staticmethod
    def _calculate_polygon_area(coords: list[tuple[float, float]]) -> float:
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
