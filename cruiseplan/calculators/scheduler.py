"""
Clean scheduler implementation with unified operations model.

This module implements the new scheduler architecture from CLAUDE-v0.3.1-scheduler-fix.md
with a focus on:
- Everything as operations with entry/exit coordinates
- Clear separation between operations (science) and navigational transits (connections)
- Consistent coordinate system for accurate distance calculations
- Simplified, maintainable code (~500 lines vs 2000+ lines)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from cruiseplan.calculators.distance import haversine_distance
from cruiseplan.core.operations import (
    AreaOperation,
    BaseOperation,
    LineOperation,
    PointOperation,
)
from cruiseplan.schema import CruiseConfig, GeoPoint
from cruiseplan.utils.units import km_to_nm

logger = logging.getLogger(__name__)


# =============================================================================
# Core Data Structures
# =============================================================================

# Type alias for cruise schedule (timeline) - list of activity dictionaries
CruiseSchedule = list[dict[str, Any]]


@dataclass
class OperationCoordinates:
    """Unified coordinate representation for all operations."""

    entry: GeoPoint
    exit: GeoPoint

    def __post_init__(self):
        """Validate coordinates."""
        if not isinstance(self.entry, GeoPoint):
            self.entry = GeoPoint(latitude=self.entry[0], longitude=self.entry[1])
        if not isinstance(self.exit, GeoPoint):
            self.exit = GeoPoint(latitude=self.exit[0], longitude=self.exit[1])


@dataclass
class ActivityRecord:
    """Standardized activity record for timeline output."""

    activity: str
    label: str
    entry_lat: float
    entry_lon: float
    exit_lat: float
    exit_lon: float
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    dist_nm: float  # Unified distance field (was transit_dist_nm/operation_dist_nm)
    vessel_speed_kt: float
    leg_name: str
    op_type: str  # Main operation type: "station", "port", "transit", "area", etc.
    operation_class: str  # Implementation class: PointOperation, LineOperation, AreaOperation, NavigationalTransit
    action: Optional[str] = None
    operation_depth: Optional[float] = None  # Depth for operation (e.g. CTD max depth)
    water_depth: Optional[float] = None  # Water depth at location

    def __init__(self, data: dict[str, Any]):
        """Initialize from dictionary for compatibility with old system."""
        # Initialize all fields to None first
        for field in self.__dataclass_fields__:
            setattr(self, field, None)

        # Then set values from data
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for output compatibility."""
        result = {
            field: getattr(self, field, None) for field in self.__dataclass_fields__
        }
        # Add backward compatibility fields for legacy output generators
        result["lat"] = self.entry_lat
        result["lon"] = self.entry_lon
        return result

    @property
    def lat(self) -> float:
        """Backward compatibility: return entry_lat as lat."""
        return self.entry_lat

    @property
    def lon(self) -> float:
        """Backward compatibility: return entry_lon as lon."""
        return self.entry_lon


# =============================================================================
# Scheduler-Specific Operations
# =============================================================================


class NavigationalTransit(BaseOperation):
    """Pure navigational connection between operations."""

    def __init__(
        self,
        from_op: BaseOperation,
        to_op: BaseOperation,
        config: CruiseConfig,
        leg_name: str,
        vessel_speed: Optional[float] = None,
    ):
        name = f"Transit to {to_op.get_label()}"
        super().__init__(name)
        self.from_op = from_op
        self.to_op = to_op
        self.config = config
        self.leg_name = leg_name
        self.vessel_speed = vessel_speed or getattr(
            config, "default_vessel_speed", 10.0
        )

    def calculate_duration(self, rules: Any) -> float:
        """Calculate based on transit distance and vessel speed."""
        exit_pt = self.from_op.get_exit_point()
        entry_pt = self.to_op.get_entry_point()
        distance_km = haversine_distance(exit_pt, entry_pt)
        distance_nm = km_to_nm(distance_km)
        return (distance_nm / self.vessel_speed) * 60.0  # hours to minutes

    def get_entry_point(self) -> tuple[float, float]:
        """Transit starts where previous operation ended."""
        return self.from_op.get_exit_point()

    def get_exit_point(self) -> tuple[float, float]:
        """Transit ends where next operation begins."""
        return self.to_op.get_entry_point()

    def get_operation_type(self) -> str:
        """Override default to return specific transit type."""
        return "Transit"

    def get_operation_distance_nm(self) -> float:
        """Calculate straight-line distance between operations."""
        exit_pt = self.from_op.get_exit_point()
        entry_pt = self.to_op.get_entry_point()
        distance_km = haversine_distance(exit_pt, entry_pt)
        return km_to_nm(distance_km)

    def get_vessel_speed(self) -> float:
        """Get vessel speed (leg-specific or default)."""
        return self.vessel_speed


# =============================================================================
# Operation Factory
# =============================================================================


class OperationFactory:
    """Factory for creating operation objects from configuration data."""

    def __init__(self, config: CruiseConfig):
        self.config = config

    def create_operation(self, name: str, leg_name: str) -> BaseOperation:
        """Create operation from configuration using catalog-based type detection."""
        # Check each catalog to find the operation
        catalog_checks = [
            ("points", "point"),
            ("ports", "point"),
            ("lines", "line"),
            ("areas", "area"),
        ]

        for catalog_name, operation_type in catalog_checks:
            catalog = getattr(self.config, catalog_name, None)
            if not catalog:
                continue

            for item in catalog:
                if item.name == name:
                    # Use appropriate factory based on operation type
                    if operation_type == "point":
                        # Special handling for ports which use PortDefinition instead of StationDefinition
                        if catalog_name == "ports":
                            return PointOperation.from_port(item)
                        else:
                            return PointOperation.from_pydantic(item)
                    elif operation_type == "line":
                        return LineOperation.from_pydantic(
                            item, self.config.default_vessel_speed
                        )
                    elif operation_type == "area":
                        return AreaOperation.from_pydantic(item)

        # Fallback: Try to resolve from global ports registry
        try:
            from cruiseplan.schema.ports import resolve_port_reference

            port_def = resolve_port_reference(name)
            return PointOperation.from_port(port_def)
        except ValueError:
            pass

        raise ValueError(f"Could not resolve operation: {name}")


# =============================================================================
# Statistics Calculator
# =============================================================================


def calculate_timeline_statistics(timeline: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Calculate summary statistics for cruise timeline activities.

    Categorizes activities into scientific operations (stations, surveys, areas)
    and supporting operations (transits, ports) for summary reporting.

    Parameters
    ----------
    timeline : List[Dict[str, Any]]
        List of activity records from the scheduler.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing statistics for each activity type with keys:
        'stations', 'surveys', 'areas', 'moorings', 'within_area_transits',
        'port_transits', and raw activity lists.
    """
    from cruiseplan.utils.units import hours_to_days

    # Initialize categorized activity lists
    station_activities = []
    mooring_activities = []
    area_activities = []
    scientific_transits = []  # Line operations like ADCP surveys
    port_activities = []
    port_transits_to_area = []  # Transits from port to working area
    port_transits_from_area = []  # Transits from working area to port
    within_area_transits = []  # Transits between scientific operations

    # Categorize every activity in the timeline using operation_class and op_type

    for i, activity in enumerate(timeline):
        # Use new operation_class and op_type fields for categorization
        operation_class = activity.get("operation_class", "Unknown")
        op_type = activity.get("op_type", "")
        activity_type = activity.get("activity", "")
        label = activity.get("label", "")

        if operation_class == "PointOperation":
            if op_type in ["CTD"]:
                station_activities.append(activity)
                logger.info(
                    f"   Adding to stations: {label} (activity={activity_type}, op_class={operation_class}, op_type={op_type})"
                )
            elif op_type == "mooring":
                mooring_activities.append(activity)
                logger.info(
                    f"   Adding to moorings: {label} (activity={activity_type}, op_class={operation_class}, op_type={op_type})"
                )
            elif op_type == "port":
                port_activities.append(activity)
                logger.info(
                    f"   Adding to ports: {label} (activity={activity_type}, op_class={operation_class}, op_type={op_type})"
                )
            else:
                # Other point operations (waypoints, etc.) - treat as stations
                station_activities.append(activity)
                logger.info(
                    f"   Adding to stations (other): {label} (activity={activity_type}, op_class={operation_class}, op_type={op_type})"
                )
        elif operation_class == "LineOperation":
            # Line operations are scientific transits (ADCP surveys, etc.)
            scientific_transits.append(activity)
            logger.info(
                f"   Adding to scientific_transits: {label} (activity={activity_type}, op_class={operation_class}, op_type={op_type})"
            )
        elif operation_class == "AreaOperation":
            area_activities.append(activity)
            logger.info(
                f"   Adding to areas: {label} (activity={activity_type}, op_class={operation_class}, op_type={op_type})"
            )
        elif operation_class == "NavigationalTransit":
            # Check if this transit connects to/from a port and categorize direction
            is_from_port = False
            is_to_port = False

            # Check previous activity (if exists)
            if i > 0:
                prev_activity = timeline[i - 1]
                if (
                    prev_activity.get("operation_class") == "PointOperation"
                    and prev_activity.get("op_type") == "port"
                ):
                    is_from_port = True

            # Check next activity (if exists)
            if i < len(timeline) - 1:
                next_activity = timeline[i + 1]
                if (
                    next_activity.get("operation_class") == "PointOperation"
                    and next_activity.get("op_type") == "port"
                ):
                    is_to_port = True

            # Categorize based on direction
            if is_from_port:
                port_transits_to_area.append(activity)
            elif is_to_port:
                port_transits_from_area.append(activity)
            else:
                within_area_transits.append(activity)
        else:
            # Any unrecognized activities also go to within-area as a fallback
            within_area_transits.append(activity)

    # Calculate statistics for each category
    def calc_stats(activities, include_distance=False, include_depth=False):
        if not activities:
            stats = {
                "count": 0,
                "avg_duration_h": 0,
                "total_duration_h": 0,
                "total_duration_days": 0,
            }
            if include_distance:
                stats.update({"avg_distance_nm": 0, "total_distance_nm": 0})
            if include_depth:
                stats.update({"avg_depth_m": 0})
            return stats

        total_duration_h = sum(a["duration_minutes"] for a in activities) / 60.0
        avg_duration_h = total_duration_h / len(activities)

        stats = {
            "count": len(activities),
            "avg_duration_h": avg_duration_h,
            "total_duration_h": total_duration_h,
            "total_duration_days": hours_to_days(total_duration_h),
        }

        if include_distance:
            total_distance_nm = sum(a.get("dist_nm", 0) for a in activities)
            stats.update(
                {
                    "avg_distance_nm": (
                        total_distance_nm / len(activities) if activities else 0
                    ),
                    "total_distance_nm": total_distance_nm,
                }
            )

        if include_depth:
            # Use operation_depth if available, otherwise fall back to water_depth
            depths = []
            for a in activities:
                depth = a.get("operation_depth")
                if depth is None:
                    depth = a.get("water_depth")
                if depth is not None:
                    depths.append(depth)
            avg_depth = sum(depths) / len(depths) if depths else 0.0
            stats.update({"avg_depth_m": avg_depth})

        return stats

    # Calculate transit statistics (special handling for distance)
    transit_stats = {}
    if within_area_transits:
        total_duration_h = (
            sum(a["duration_minutes"] for a in within_area_transits) / 60.0
        )
        total_distance_nm = sum(a.get("dist_nm", 0) for a in within_area_transits)
        avg_speed_kt = (
            total_distance_nm / total_duration_h if total_duration_h > 0 else 0
        )

        transit_stats = {
            "count": len(within_area_transits),
            "total_duration_h": total_duration_h,
            "total_duration_days": hours_to_days(total_duration_h),
            "total_distance_nm": total_distance_nm,
            "avg_speed_kt": avg_speed_kt,
        }
    else:
        transit_stats = {
            "count": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
            "total_distance_nm": 0,
            "avg_speed_kt": 0,
        }

    # Calculate separate port transit statistics (to area and from area)
    def calc_port_transit_stats(transits):
        if not transits:
            return {
                "count": 0,
                "total_duration_h": 0,
                "total_duration_days": 0,
                "total_distance_nm": 0,
                "avg_speed_kt": 0,
            }
        total_duration_h = sum(a["duration_minutes"] for a in transits) / 60.0
        total_distance_nm = sum(a.get("dist_nm", 0) for a in transits)
        avg_speed_kt = (
            total_distance_nm / total_duration_h if total_duration_h > 0 else 0
        )
        return {
            "count": len(transits),
            "total_duration_h": total_duration_h,
            "total_duration_days": hours_to_days(total_duration_h),
            "total_distance_nm": total_distance_nm,
            "avg_speed_kt": avg_speed_kt,
        }

    port_transit_to_area_stats = calc_port_transit_stats(port_transits_to_area)
    port_transit_from_area_stats = calc_port_transit_stats(port_transits_from_area)

    # Calculate leg-specific operation counts
    leg_stats = {}
    for activity in timeline:
        leg_name = activity.get("leg_name", "Unknown")
        if leg_name not in leg_stats:
            leg_stats[leg_name] = {
                "stations": 0,
                "moorings": 0,
                "surveys": 0,
                "areas": 0,
                "total_scientific": 0,
                "ports": 0,
                "transits": 0,
                "total_activities": 0,
            }

        leg_stats[leg_name]["total_activities"] += 1

        operation_class = activity.get("operation_class", "")
        op_type = activity.get("op_type", "")

        # Count all operations except ports
        if op_type == "port":
            leg_stats[leg_name]["ports"] += 1
        elif operation_class == "NavigationalTransit":
            leg_stats[leg_name]["transits"] += 1
        else:
            # This is a scientific operation - count it
            leg_stats[leg_name]["total_scientific"] += 1

            # Also increment specific counters for detailed stats
            if operation_class == "PointOperation":
                if op_type in {"station", "CTD"}:
                    leg_stats[leg_name]["stations"] += 1
                elif op_type == "mooring":
                    leg_stats[leg_name]["moorings"] += 1
            elif operation_class == "LineOperation":
                leg_stats[leg_name]["surveys"] += 1
            elif operation_class == "AreaOperation":
                leg_stats[leg_name]["areas"] += 1

    # Debug output for operation counts
    total_scientific_operations = (
        len(station_activities)
        + len(mooring_activities)
        + len(scientific_transits)
        + len(area_activities)
    )
    logger.info("🔍 Cruise-level operation counts:")
    logger.info(f"   Stations: {len(station_activities)}")
    logger.info(f"   Moorings: {len(mooring_activities)}")
    logger.info(f"   Scientific transits (surveys): {len(scientific_transits)}")
    logger.info(f"   Area operations: {len(area_activities)}")
    logger.info(f"   Total scientific operations: {total_scientific_operations}")
    logger.info(f"   Port activities: {len(port_activities)}")
    logger.info(f"   Within-area transits: {len(within_area_transits)}")

    # Debug output for leg-specific counts
    for leg_name, stats in leg_stats.items():
        logger.info(f"🔍 Leg '{leg_name}' operation counts:")
        logger.info(f"   Stations: {stats['stations']}")
        logger.info(f"   Moorings: {stats['moorings']}")
        logger.info(f"   Surveys: {stats['surveys']}")
        logger.info(f"   Areas: {stats['areas']}")
        logger.info(f"   Total scientific operations: {stats['total_scientific']}")
        logger.info(f"   Total activities in leg: {stats['total_activities']}")

    # Calculate total scientific operations from leg totals for consistency
    total_scientific_operations_from_legs = sum(
        leg_stats[leg_name]["total_scientific"] for leg_name in leg_stats
    )

    return {
        "stations": calc_stats(station_activities, include_depth=True),
        "moorings": calc_stats(mooring_activities),
        "surveys": calc_stats(scientific_transits, include_distance=True),
        "areas": calc_stats(area_activities),
        "within_area_transits": transit_stats,
        "port_transits_to_area": port_transit_to_area_stats,
        "port_transits_from_area": port_transit_from_area_stats,
        "port_activities": calc_stats(port_activities),
        # Leg-specific operation counts
        "leg_stats": leg_stats,
        # Total scientific operations calculated from legs for consistency
        "total_scientific": total_scientific_operations_from_legs,
        # Raw data for detailed processing
        "station_activities": station_activities,
        "mooring_activities": mooring_activities,
        "scientific_transits": scientific_transits,
        "area_activities": area_activities,
        "within_area_transits_activities": within_area_transits,
        "port_transits_to_area_activities": port_transits_to_area,
        "port_transits_from_area_activities": port_transits_from_area,
        "port_activities_raw": port_activities,
    }


# =============================================================================
# Timeline Generator
# =============================================================================


class TimelineGenerator:
    """Generates cruise timeline from operations and legs."""

    def __init__(self, config: CruiseConfig):
        self.config = config
        self.factory = OperationFactory(config)
        self.current_time = self._parse_start_datetime()

    def generate_timeline(self, legs: Optional[list[Any]] = None) -> CruiseSchedule:
        """Generate complete cruise timeline."""
        if legs is None:
            legs = self._create_runtime_legs()

        timeline = []

        for leg in legs:
            leg_activities = self._process_leg(leg)
            timeline.extend(leg_activities)

        return [activity.to_dict() for activity in timeline]

    def _create_runtime_legs(self) -> list[Any]:
        """Create runtime legs from config."""
        # Import here to avoid circular imports
        from cruiseplan.core.organizational import Leg

        runtime_legs = []
        for leg_def in self.config.legs or []:
            try:
                runtime_leg = Leg(
                    name=leg_def.name,
                    departure_port=getattr(leg_def, "departure_port", None),
                    arrival_port=getattr(leg_def, "arrival_port", None),
                    description=getattr(leg_def, "description", None),
                    first_activity=getattr(leg_def, "first_activity", None),
                    last_activity=getattr(leg_def, "last_activity", None),
                )
                runtime_leg.vessel_speed = getattr(leg_def, "vessel_speed", None)
                runtime_leg.turnaround_time = getattr(leg_def, "turnaround_time", None)
                runtime_leg.distance_between_stations = getattr(
                    leg_def, "distance_between_stations", None
                )

                runtime_legs.append(runtime_leg)
            except Exception as e:
                logger.warning(
                    f"Failed to create runtime leg for '{leg_def.name}': {e}"
                )

        return runtime_legs

    def _process_leg(self, leg: Any) -> list[ActivityRecord]:
        """Process a single leg and generate activities."""
        # Initialize current_time if not set
        if self.current_time is None:
            self.current_time = self._parse_start_datetime()

        activities = []

        # Build complete activities sequence: departure_port + leg_activities + arrival_port
        # Validation ensures departure_port and arrival_port are required fields
        # Use full port objects (which may contain enriched action info) instead of just names
        complete_activities = [leg.departure_port]

        # Get leg activities - check both runtime leg and config leg
        leg_activities = self._extract_activities_from_leg(leg)
        if not leg_activities and hasattr(self.config, "legs"):
            for config_leg in self.config.legs:
                if config_leg.name == leg.name and hasattr(config_leg, "activities"):
                    leg_activities = config_leg.activities
                    break

        # Add leg activities to sequence
        complete_activities.extend(leg_activities or [])

        # Add arrival port to sequence (validation ensures it exists)
        complete_activities.append(leg.arrival_port)

        previous_operation = None

        # Process complete activities sequence (ports are treated as regular operations)
        for activity in complete_activities:
            try:
                # Handle both activity names (strings) and definition objects
                if isinstance(activity, str):
                    # Regular activity name - use factory
                    operation = self.factory.create_operation(activity, leg.name)
                else:
                    # Definition object (PointDefinition, LineDefinition, AreaDefinition) - create directly
                    from cruiseplan.core.operations import (
                        AreaOperation,
                        LineOperation,
                        PointOperation,
                    )
                    from cruiseplan.schema.activities import (
                        AreaDefinition,
                        LineDefinition,
                        PointDefinition,
                    )

                    # Handle Pydantic objects directly (no dictionary handling needed)
                    if isinstance(activity, PointDefinition):
                        if (
                            hasattr(activity, "operation_type")
                            and activity.operation_type
                            and activity.operation_type.value == "port"
                        ):
                            # Port waypoint - create as port
                            operation = PointOperation.from_port(activity)
                        else:
                            # Non-port waypoint - create as scientific operation
                            operation = PointOperation.from_pydantic(activity)
                    elif isinstance(activity, LineDefinition):
                        # Transect - create as line operation
                        operation = LineOperation.from_pydantic(
                            activity, leg.vessel_speed
                        )
                    elif isinstance(activity, AreaDefinition):
                        # Area - create as area operation
                        operation = AreaOperation.from_pydantic(activity)
                    else:
                        raise TypeError(
                            f"Unknown activity type: {type(activity)}. "
                            f"Expected PointDefinition, LineDefinition, or AreaDefinition, got {activity}"
                        )

                # Add navigational transit between all operations
                # Zero-duration transits will be filtered out in presentation layer
                if previous_operation is not None:
                    transit = self._create_navigational_transit(
                        previous_operation, operation, leg.name, leg
                    )
                    if transit:
                        activities.append(transit)

                # Add the operation activity
                operation_activity = self._create_operation_activity(
                    operation, leg.name
                )
                activities.append(operation_activity)

                previous_operation = operation

            except Exception:
                activity_name = getattr(activity, "name", str(activity))
                logger.exception(f"Failed to process activity '{activity_name}'")
                continue

        return activities

    def _create_navigational_transit(
        self,
        from_op: BaseOperation,
        to_op: BaseOperation,
        leg_name: str = "unknown",
        leg: Any = None,
    ) -> Optional[ActivityRecord]:
        """Create navigational transit between operations."""
        # Get leg-specific vessel speed if available
        leg_vessel_speed = None
        if leg and hasattr(leg, "vessel_speed"):
            leg_vessel_speed = leg.vessel_speed

        transit = NavigationalTransit(
            from_op, to_op, self.config, leg_name, vessel_speed=leg_vessel_speed
        )

        # Create rules object for calculate_duration
        rules = type("Rules", (), {"config": self.config})()
        duration_minutes = transit.calculate_duration(rules)

        # Skip zero-distance transits
        if duration_minutes <= 0:
            return None

        entry_pt, exit_pt = transit.get_coordinates()
        activity = ActivityRecord(
            {
                "activity": "Transit",
                "label": transit.get_label(),
                "entry_lat": entry_pt.latitude,
                "entry_lon": entry_pt.longitude,
                "exit_lat": exit_pt.latitude,
                "exit_lon": exit_pt.longitude,
                "operation_depth": None,
                "water_depth": None,
                "start_time": self.current_time,
                "end_time": self.current_time + timedelta(minutes=duration_minutes),
                "duration_minutes": duration_minutes,
                "dist_nm": transit.get_operation_distance_nm(),
                "vessel_speed_kt": transit.get_vessel_speed(),
                "leg_name": leg_name,
                "op_type": "transit",
                "operation_class": transit.__class__.__name__,
            }
        )

        self.current_time = activity.end_time
        return activity

    def _create_operation_activity(
        self, operation: BaseOperation, leg_name: str = "unknown"
    ) -> ActivityRecord:
        """Create activity record for a scientific operation."""
        entry_pt, exit_pt = operation.get_coordinates()

        # Create rules object for calculate_duration
        rules = type("Rules", (), {"config": self.config})()
        duration_minutes = operation.calculate_duration(rules)

        activity = ActivityRecord(
            {
                "activity": operation.get_operation_type(),
                "label": operation.get_label(),
                "entry_lat": entry_pt.latitude,
                "entry_lon": entry_pt.longitude,
                "exit_lat": exit_pt.latitude,
                "exit_lon": exit_pt.longitude,
                "operation_depth": getattr(operation, "operation_depth", None),
                "water_depth": getattr(operation, "water_depth", None),
                # Note: depth field has mysterious issues, HTML generator should use operation_depth/water_depth directly
                "start_time": self.current_time,
                "end_time": self.current_time + timedelta(minutes=duration_minutes),
                "duration_minutes": duration_minutes,
                "dist_nm": getattr(
                    operation, "get_operation_distance_nm", lambda: 0.0
                )(),
                "vessel_speed_kt": getattr(
                    operation,
                    "get_vessel_speed",
                    lambda: getattr(self.config, "default_vessel_speed", 10.0),
                )(),
                "leg_name": leg_name,
                "op_type": getattr(
                    operation, "op_type", operation.get_operation_type().lower()
                ),
                "operation_class": operation.__class__.__name__,
                "action": getattr(operation, "action", None)
                and (
                    operation.action.value
                    if hasattr(operation.action, "value")
                    else str(operation.action)
                ),
            }
        )

        self.current_time = activity.end_time
        return activity

    def _extract_activities_from_leg(self, leg: Any) -> list[str]:
        """Extract activity names from leg definition."""
        activities = []

        # Check runtime leg structure first
        if hasattr(leg, "operations") and leg.operations:
            for operation in leg.operations:
                if hasattr(operation, "name"):
                    activities.append(operation.name)
                elif hasattr(operation, "station") and hasattr(
                    operation.station, "name"
                ):
                    activities.append(operation.station.name)

        # Check clusters if no direct operations
        elif hasattr(leg, "clusters") and leg.clusters:
            for cluster in leg.clusters:
                if hasattr(cluster, "activities") and cluster.activities:
                    # Clusters may have StationDefinition objects or string names
                    for activity in cluster.activities:
                        if hasattr(activity, "name"):
                            # StationDefinition object
                            activities.append(activity.name)
                        else:
                            # String name
                            activities.append(str(activity))

        # If no activities found from runtime leg, check config leg
        if not activities and hasattr(self.config, "legs"):
            for config_leg in self.config.legs:
                if config_leg.name == leg.name:
                    # Check config leg clusters
                    if hasattr(config_leg, "clusters") and config_leg.clusters:
                        for cluster in config_leg.clusters:
                            if hasattr(cluster, "activities") and cluster.activities:
                                for activity in cluster.activities:
                                    if hasattr(activity, "name"):
                                        # StationDefinition object
                                        activities.append(activity.name)
                                    else:
                                        # String name
                                        activities.append(str(activity))
                    # Check config leg activities (for backwards compatibility)
                    elif hasattr(config_leg, "activities") and config_leg.activities:
                        activities.extend(config_leg.activities)
                    break

        # Fallback: Get activities from leg definition (for backwards compatibility)
        if not activities and hasattr(leg, "activities") and leg.activities:
            activities.extend(leg.activities)

        return activities

    def _parse_start_datetime(self) -> datetime:
        """Parse start datetime from config."""
        try:
            start_date = getattr(self.config, "start_date", "1970-01-01T00:00:00+00:00")
            if "T" in start_date:
                start_date_clean = start_date.replace("Z", "").replace("+00:00", "")
                return datetime.fromisoformat(start_date_clean)
            else:
                start_time = getattr(self.config, "start_time", "08:00")
                return datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            logger.exception("Invalid start_date or start_time format")
            # Return a default datetime instead of None
            return datetime(1970, 1, 1, 8, 0, 0)


# =============================================================================
# Main API Functions (for backward compatibility)
# =============================================================================


def generate_timeline(cruise, legs: Optional[list[Any]] = None) -> CruiseSchedule:
    """
    Generate cruise timeline directly from CruiseInstance object.

    This function eliminates the need for YAML serialization/deserialization
    by working directly with the CruiseInstance object's validated configuration.

    Parameters
    ----------
    cruise : cruiseplan.core.cruise.CruiseInstance
        CruiseInstance object with enhanced data
    legs : Optional[List[Any]]
        Runtime legs (if None, will be created from config)

    Returns
    -------
    List[Dict[str, Any]]
        Timeline activities as dictionaries
    """
    # The CruiseInstance object already contains a validated CruiseConfig object
    # This avoids the YAML serialization/deserialization that causes
    # objects to become dictionaries
    config = cruise.config

    # Use existing timeline generation
    generator = TimelineGenerator(config)
    return generator.generate_timeline(legs)


def generate_cruise_schedule(
    config_path: str,
    output_dir: str = "data",
    formats: Optional[list[str]] = None,
    validate_depths: bool = False,
    selected_leg: Optional[str] = None,
    derive_netcdf: bool = False,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data",
    bathy_stride: int = 10,
    figsize: Optional[list[float]] = None,
    output_basename: Optional[str] = None,
) -> dict[str, Any]:
    """
    Generate cruise schedule (backward compatibility function).

    Parameters
    ----------
    config_path : str
        Path to configuration file
    output_dir : str
        Output directory for generated files
    formats : Optional[List[str]]
        Output formats to generate
    validate_depths : bool
        Whether to validate depths
    selected_leg : Optional[str]
        Specific leg to process (if None, process all legs)
    derive_netcdf : bool
        Whether to generate NetCDF output
    bathy_source : str
        Bathymetry data source
    bathy_dir : str
        Bathymetry data directory
    bathy_stride : int
        Bathymetry stride for maps
    figsize : Optional[List[float]]
        Figure size for maps
    output_basename : Optional[str]
        Base name for output files

    Returns
    -------
    Dict[str, Any]
        Schedule data with timeline and summary information
    """
    from cruiseplan.core.cruise import CruiseInstance

    # Load cruise configuration
    cruise = CruiseInstance(config_path)

    # Validate depths if requested
    validation_warnings = []
    if validate_depths:
        from cruiseplan.api.validate import (
            _validate_configuration as validate_configuration,
        )

        is_valid, errors, warnings = validate_configuration(
            config_path, check_depths=True, tolerance=10.0
        )
        if not is_valid:
            raise RuntimeError(f"Configuration validation failed: {errors}")
        validation_warnings.extend(warnings)

    # Filter legs if specific leg requested
    legs_to_process = cruise.runtime_legs
    if selected_leg:
        # Check runtime legs first, then config legs
        legs_to_process = [
            leg for leg in cruise.runtime_legs if leg.name == selected_leg
        ]
        if (
            not legs_to_process
            and hasattr(cruise.config, "legs")
            and cruise.config.legs
        ):
            # Also check config legs for backward compatibility
            config_legs = [
                leg for leg in cruise.config.legs if leg.name == selected_leg
            ]
            if config_legs:
                legs_to_process = (
                    cruise.runtime_legs
                )  # Use all runtime legs if config leg found
        if not legs_to_process:
            raise ValueError(f"Leg '{selected_leg}' not found in configuration")

    # Generate timeline
    timeline = generate_timeline(cruise.config, legs_to_process)

    # Calculate summary statistics
    total_duration_h = sum(activity["duration_minutes"] for activity in timeline) / 60.0
    total_transit_nm = sum(
        activity.get("dist_nm", 0)
        for activity in timeline
        if activity.get("operation_class") == "NavigationalTransit"
    )

    return {
        "success": True,
        "timeline": timeline,
        "total_activities": len(timeline),
        "total_duration_hours": total_duration_h,
        "total_distance_nm": total_transit_nm,
        "formats_generated": formats or [],
        "output_files": [],
        "warnings": validation_warnings,
        "cruise_name": cruise.config.cruise_name,
        "description": getattr(cruise.config, "description", None),
        "summary": {
            "total_duration_hours": total_duration_h,
            "total_duration_days": total_duration_h / 24.0,
            "total_transit_distance_nm": total_transit_nm,
            "total_activities": len(timeline),
        },
        "config": cruise.config,
        "legs": legs_to_process,
    }
