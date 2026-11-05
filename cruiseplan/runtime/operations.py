"""
Runtime operation classes for cruise planning activities.

Provides the business logic classes that represent active cruise operations.
These are the runtime layer that performs the cruise planning work.

**Relationship to config/activities.py:**
- config/activities.py: Pydantic models that validate YAML → Python data
- This module: Runtime business objects that do the actual work

Example flow: YAML → PointDefinition (config) → PointOperation (this module)

This module provides the base operation classes and specialized implementations
for stations, moorings, areas, and transects.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

from cruiseplan.config.activities import (
    AreaDefinition,
    GeoPoint,
    LineDefinition,
    PointDefinition,
)
from cruiseplan.config.fields import ACTION_FIELD
from cruiseplan.config.values import (
    DEFAULT_DEPTH,
    DEFAULT_MOORING_DURATION_MIN,
    ActionEnum,
)

if TYPE_CHECKING:
    from cruiseplan.config.cruise_config import CruiseConfig

# Port actions that identify mobilization/demobilization operations
PORT_ACTIONS = [ActionEnum.MOB.value, ActionEnum.DEMOB.value]


logger = logging.getLogger(__name__)


class DurationRules(Protocol):
    """Rules object passed to duration calculations: the cruise config and leg values."""

    config: "CruiseConfig"
    turnaround_time_minutes: float | None


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
        comment: str | None = None,
        display_name: str | None = None,
    ) -> None:
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
        # Actual minutes of the transit into this operation, when given
        self.transit_minutes: float | None = None

    @abstractmethod
    def calculate_duration(self, rules: DurationRules | None) -> float:
        """
        Calculate duration in minutes based on provided rules.

        Parameters
        ----------
        rules : DurationRules or None
            Duration calculation rules and parameters.

        Returns
        -------
        float
            Duration in minutes.
        """

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
        position: GeoPoint,
        operation_depth: float | None = None,
        water_depth: float = 0.0,
        duration: float = 0.0,
        comment: str | None = None,
        op_type: str = "station",
        action: str | None = None,
        display_name: str | None = None,
        delay_start: float | None = None,
    ) -> None:
        """
        Initialize a point operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        position : GeoPoint
            Geographic position.
        operation_depth : float, optional
            Operation depth in meters (e.g. CTD cast depth).
        water_depth : float, optional
            Seafloor depth in meters (default: 0.0).
        duration : float, optional
            Manual duration override in minutes (default: 0.0).
        comment : str, optional
            Human-readable comment or description.
        op_type : str, optional
            Type of operation ('station' or 'mooring', default: 'station').
        action : str, optional
            Specific action for moorings (deploy/recover).
        display_name : str, optional
            Human-readable label; defaults to ``name``.
        delay_start : float, optional
            Time to wait before operation begins in minutes.
        """
        super().__init__(name, comment, display_name)
        self.position = position
        self.operation_depth = operation_depth
        self.water_depth = water_depth
        self.manual_duration = duration
        self.op_type = op_type
        self.action = action  # Specific to Moorings
        self.delay_start = delay_start or 0.0
        # Set by calculate_duration when the fill duration was used
        self.duration_is_fill = False
        self.duration_fill_reason: str | None = None

    def get_depth(self) -> float:
        """
        Get the appropriate depth for this operation.

        Returns operation_depth if set to a real value, otherwise water_depth,
        otherwise 0.0. A fill-value operation_depth is skipped so a valid
        water_depth is not discarded.

        Returns
        -------
        float
            Depth in meters.
        """
        if self.operation_depth is not None and self.operation_depth != DEFAULT_DEPTH:
            return self.operation_depth
        if self.water_depth is not None:
            return self.water_depth
        return 0.0

    def calculate_duration(self, rules: DurationRules | None) -> float:
        """
        Calculate duration based on operation type and rules.

        If ``manual_duration > 0`` (set via ``duration_minutes:`` in YAML),
        that value is returned immediately and all type-based calculations
        (CTD cast time, etc.) are skipped.  This is the intended per-station
        override mechanism.

        When no duration can be computed, the fill value
        ``DEFAULT_MOORING_DURATION_MIN`` (999 h) is returned and
        ``duration_is_fill`` / ``duration_fill_reason`` are set (the scheduler
        logs one warning per operation): a mooring or yo-yo cast
        without ``duration_minutes``, a depth-driven cast without a usable depth
        (missing, zero or the fill depth), and an operation type with no
        duration rule. Ports and waypoints take 0 minutes.

        Parameters
        ----------
        rules : DurationRules or None
            Duration calculation rules containing config.

        Returns
        -------
        float
            Duration in minutes.
        """
        self.duration_is_fill = False
        self.duration_fill_reason = None
        # Manual duration (YAML `duration_minutes:`) always wins.
        if self.manual_duration > 0:
            # The enrich step writes the fill value for moorings without one
            if self.manual_duration == DEFAULT_MOORING_DURATION_MIN:
                self.duration_is_fill = True
                self.duration_fill_reason = "duration is the fill value"
            return self.manual_duration

        # Import calculator
        from cruiseplan.timeline.duration import DurationCalculator

        if not hasattr(rules, "config"):
            return 0.0

        if self.op_type in ("port", "waypoint"):
            # No operation time; waiting time is handled separately
            return 0.0

        calc = DurationCalculator(
            rules.config, getattr(rules, "turnaround_time_minutes", None)
        )

        # TODO - why is ADCP on the list? what is this hardcoded list for?
        # Check for station-like operations (CTD, ADCP, etc.) that need CTD time calculation
        # Exception: yo_yo CTD operations use specified duration like moorings
        if (
            self.op_type in ["station", "CTD", "ADCP", "XBT", "XCTD"]
            and self.action != "yo_yo"
        ) or (
            self.op_type != "mooring"
            and hasattr(self, "operation_depth")
            and self.operation_depth is not None
            and self.operation_depth > 0
            and self.action != "yo_yo"
        ):
            depth = self.get_depth()
            if depth is None or depth <= 0 or depth == DEFAULT_DEPTH:
                return self._fill_duration(
                    "no usable depth (operation_depth and water_depth missing, "
                    "zero or the fill value)"
                )
            return calc.calculate_ctd_time(depth)
        if self.op_type == "mooring" or (
            self.op_type == "CTD" and self.action == "yo_yo"
        ):
            return self._fill_duration("no duration given")

        return self._fill_duration(
            f"no duration rule for operation type '{self.op_type}'"
        )

    def _fill_duration(self, reason: str) -> float:
        """Flag this operation as using the fill duration and return it."""
        self.duration_is_fill = True
        self.duration_fill_reason = reason
        logger.debug(f"Operation {self.name}: {reason}; fill duration")
        return DEFAULT_MOORING_DURATION_MIN

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
        return (self.position.latitude, self.position.longitude)

    def get_exit_point(self) -> tuple[float, float]:
        """
        Get the geographic exit point for this point operation.

        For point operations, entry and exit are the same location.

        Returns
        -------
        tuple[float, float]
            (latitude, longitude) of the operation location.
        """
        return (self.position.latitude, self.position.longitude)

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
        Create a logical operation from a validated Pydantic model.

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
        pos = GeoPoint(latitude=obj.latitude, longitude=obj.longitude)

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
            obj.operation_depth_m
            if obj.operation_depth_m is not None
            else obj.water_depth_m
        )

        op = cls(
            name=obj.name,
            position=pos,
            operation_depth=operation_depth,
            water_depth=obj.water_depth_m,
            duration=obj.duration_minutes if obj.duration_minutes else 0.0,
            comment=obj.comment,
            op_type=display_op_type,
            action=action,
            delay_start=obj.delay_start_minutes,
        )
        op.transit_minutes = getattr(obj, "transit_minutes", None)
        return op

    @classmethod
    def from_port(cls, obj: PointDefinition) -> "PointOperation":
        """
        Create a PointOperation from a PointDefinition.

        Parameters
        ----------
        obj : PointDefinition
            Port definition model.

        Returns
        -------
        PointOperation
            New PointOperation instance representing a port.
        """
        pos = GeoPoint(latitude=obj.latitude, longitude=obj.longitude)

        op = cls(
            name=obj.name,
            position=pos,
            operation_depth=None,  # Ports don't have operation depth
            water_depth=None,  # Ports don't need water depth
            duration=obj.duration_minutes if obj.duration_minutes else 0.0,
            comment=getattr(obj, "description", None),
            op_type="port",
            action=getattr(
                obj, ACTION_FIELD, "mob"
            ),  # Use port's action or default to mob
            display_name=getattr(obj, "display_name", None),
            delay_start=obj.delay_start_minutes,
        )
        op.transit_minutes = getattr(obj, "transit_minutes", None)
        return op


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
        route: list[GeoPoint],
        speed: float = 10.0,
        comment: str | None = None,
        display_name: str | None = None,
        op_type: str = "line",
        action: str | None = None,
    ) -> None:
        """
        Initialize a line operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        route : list of GeoPoint
            Geographic waypoints along the line.
        speed : float, optional
            Vessel speed in knots (default: 10.0).
        comment : str, optional
            Human-readable comment or description.
        display_name : str, optional
            Human-readable label; defaults to ``name``.
        op_type : str, optional
            Operation type (default: 'line').
        action : str, optional
            Action for this operation, if any.
        """
        super().__init__(name, comment, display_name)
        self.route = route  # List of GeoPoint
        self.speed = speed
        self.op_type = op_type
        self.action = action

    def calculate_duration(self, rules: DurationRules | None) -> float:
        """
        Calculate duration for the line operation based on route distance and vessel speed.

        Parameters
        ----------
        rules : DurationRules or None
            Duration calculation rules containing config with default_vessel_speed.

        Returns
        -------
        float
            Duration in minutes.
        """
        if not self.route or len(self.route) < 2:
            return 0.0

        # Use centralized calculators
        from cruiseplan.timeline.distance import route_distance
        from cruiseplan.timeline.duration import DurationCalculator

        # Calculate route distance using centralized function
        route_distance_km = route_distance(self.route)

        # Use DurationCalculator if rules/config available
        if hasattr(rules, "config"):
            calc = DurationCalculator(rules.config)
            # Use default vessel speed if self.speed is 0 or None
            effective_speed = (
                self.speed
                if self.speed and self.speed > 0
                else rules.config.default_vessel_speed_kt
            )
            return calc.calculate_transit_time(route_distance_km, effective_speed)
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
        return (self.route[0].latitude, self.route[0].longitude)

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
        return (self.route[-1].latitude, self.route[-1].longitude)

    def get_vessel_speed(self) -> float:
        """
        Return the speed the line is run at (its own, else the leg or cruise speed).

        Returns
        -------
        float
            Speed in knots.
        """
        return self.speed

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
        from cruiseplan.timeline.distance import route_distance
        from cruiseplan.utils.units import km_to_nm

        # Calculate route distance and convert to nautical miles
        route_distance_km = route_distance(self.route)
        return km_to_nm(route_distance_km)

    @classmethod
    def from_pydantic(
        cls, obj: LineDefinition, default_speed: float
    ) -> "LineOperation":
        """
        Create a line operation from a validated Pydantic model.

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
        # Use GeoPoints directly instead of converting to tuples
        route_geopoints = obj.route

        # Use the original operation_type from YAML for display
        display_op_type = obj.operation_type.value if obj.operation_type else "line"
        action = obj.action.value if obj.action else None

        op = cls(
            name=obj.name,
            route=route_geopoints,
            speed=obj.vessel_speed_kt if obj.vessel_speed_kt else default_speed,
            comment=obj.comment,
            display_name=getattr(obj, "display_name", None),
            op_type=display_op_type,
            action=action,
        )
        op.transit_minutes = getattr(obj, "transit_minutes", None)
        return op


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
        boundary_polygon: list[GeoPoint],
        area_km2: float,
        duration: float | None = None,
        start_point: tuple[float, float] | None = None,
        end_point: tuple[float, float] | None = None,
        sampling_density: float = 1.0,
        comment: str | None = None,
        display_name: str | None = None,
        op_type: str = "area",
        action: str | None = None,
    ) -> None:
        """
        Initialize an area operation.

        Parameters
        ----------
        name : str
            Unique identifier for this operation.
        boundary_polygon : list of GeoPoint
            Corners defining the area boundary.
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
        display_name : str, optional
            Human-readable label; defaults to ``name``.
        op_type : str, optional
            Operation type (default: 'area').
        action : str, optional
            Action for this operation, if any.
        """
        super().__init__(name, comment, display_name)
        self.boundary_polygon = boundary_polygon  # List of GeoPoint
        self.area_km2 = area_km2
        self.duration = duration
        self.sampling_density = sampling_density
        self.op_type = op_type
        self.action = action

        # Set start/end points, defaulting to first/last corners if not specified
        self.start_point = start_point or (
            (self.boundary_polygon[0].latitude, self.boundary_polygon[0].longitude)
            if self.boundary_polygon
            else (0.0, 0.0)
        )
        self.end_point = end_point or (
            (self.boundary_polygon[-1].latitude, self.boundary_polygon[-1].longitude)
            if self.boundary_polygon
            else (0.0, 0.0)
        )

    def calculate_duration(self, rules: DurationRules | None) -> float:  # noqa: ARG002 - interface; area duration is user-set
        """
        Calculate duration using user-specified duration or fallback formula.

        For area operations, duration must be specified by the user (like moorings)
        since area coverage patterns are highly variable.

        Parameters
        ----------
        rules : DurationRules or None
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
        raise ValueError(
            f"Area operation '{self.name}' requires user-specified duration. "
            "Add 'duration_minutes: <minutes>' to the area definition in YAML."
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
        Create an area operation from a validated Pydantic model.

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
        if obj.duration_minutes is None:
            raise ValueError(
                f"Area operation '{obj.name}' requires user-specified duration. "
                "Add 'duration_minutes: <minutes>' to the area definition in YAML."
            )

        # Convert List[GeoPoint] -> List[tuple]
        # Use GeoPoints directly instead of converting to tuples
        boundary_geopoints = obj.corners

        # Calculate approximate area using shoelace formula (convert GeoPoints to tuples for calculation)
        boundary_tuples = [(p.latitude, p.longitude) for p in boundary_geopoints]
        area_km2 = cls._calculate_polygon_area(boundary_tuples)

        # Use first and last corners as start/end points
        start_point = boundary_tuples[0] if boundary_tuples else (0.0, 0.0)
        end_point = boundary_tuples[-1] if boundary_tuples else (0.0, 0.0)

        # Use the original operation_type from YAML for display
        display_op_type = obj.operation_type.value if obj.operation_type else "area"
        action = obj.action.value if obj.action else None

        op = cls(
            name=obj.name,
            boundary_polygon=boundary_geopoints,
            area_km2=area_km2,
            duration=obj.duration_minutes,
            start_point=start_point,
            end_point=end_point,
            comment=obj.comment,
            display_name=getattr(obj, "display_name", None),
            op_type=display_op_type,
            action=action,
        )
        op.transit_minutes = getattr(obj, "transit_minutes", None)
        return op

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
        return area * (km_per_degree**2)


class NavigationalTransit(BaseOperation):
    """
    Navigational connection between two operations.

    Parameters
    ----------
    from_op : BaseOperation
        Operation the transit leaves from (its exit point).
    to_op : BaseOperation
        Operation the transit leads to (its entry point).
    config : CruiseConfig
        Cruise configuration (default vessel speed).
    leg_name : str
        Name of the leg the transit belongs to.
    vessel_speed : float, optional
        Transit speed in knots; the cruise default when not given.
    """

    def __init__(
        self,
        from_op: BaseOperation,
        to_op: BaseOperation,
        config: "CruiseConfig",
        leg_name: str,
        vessel_speed: float | None = None,
    ) -> None:
        super().__init__(f"Transit to {to_op.get_label()}")
        self.from_op = from_op
        self.to_op = to_op
        self.config = config
        self.leg_name = leg_name
        self.vessel_speed = vessel_speed or config.default_vessel_speed_kt

    def calculate_duration(self, rules: DurationRules | None) -> float:  # noqa: ARG002 - interface; transit uses its own speed
        """
        Return the transit time in minutes at the transit speed.

        Parameters
        ----------
        rules : DurationRules or None
            Not used; the transit speed is set on the transit.

        Returns
        -------
        float
            Duration in minutes.
        """
        return (self.get_operation_distance_nm() / self.vessel_speed) * 60.0

    def get_entry_point(self) -> tuple[float, float]:
        """
        Return where the previous operation ended.

        Returns
        -------
        tuple of float
            (latitude, longitude).
        """
        return self.from_op.get_exit_point()

    def get_exit_point(self) -> tuple[float, float]:
        """
        Return where the next operation begins.

        Returns
        -------
        tuple of float
            (latitude, longitude).
        """
        return self.to_op.get_entry_point()

    def get_operation_type(self) -> str:
        """
        Return the display type, ``Transit``.

        Returns
        -------
        str
            ``"Transit"``.
        """
        return "Transit"

    def get_operation_distance_nm(self) -> float:
        """
        Return the great-circle distance between the two operations.

        Returns
        -------
        float
            Distance in nautical miles.
        """
        from cruiseplan.timeline.distance import haversine_distance
        from cruiseplan.utils.units import km_to_nm

        distance_km = haversine_distance(
            self.from_op.get_exit_point(), self.to_op.get_entry_point()
        )
        return km_to_nm(distance_km)

    def get_vessel_speed(self) -> float:
        """
        Return the transit speed (leg speed, or the cruise default).

        Returns
        -------
        float
            Speed in knots.
        """
        return self.vessel_speed
