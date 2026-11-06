"""
Clean scheduler implementation with unified operations model.

The scheduler treats every activity as an operation with entry and exit
coordinates:
- Operations (science) are kept separate from navigational transits (connections)
- All distances are computed in one coordinate system
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from cruiseplan.config.activities import (
    AreaDefinition,
    LineDefinition,
    PointDefinition,
)
from cruiseplan.config.cruise_config import ClusterDefinition, CruiseConfig
from cruiseplan.config.values import DEFAULT_MOORING_DURATION_MIN
from cruiseplan.runtime.operations import (
    AreaOperation,
    BaseOperation,
    LineOperation,
    NavigationalTransit,
    PointOperation,
)
from cruiseplan.timeline.record import ActivityRecord, Timeline, kind_of

if TYPE_CHECKING:
    from cruiseplan.runtime.cruise import CruiseInstance
    from cruiseplan.runtime.organizational import Cluster, Leg

logger = logging.getLogger(__name__)

__all__ = [
    "ActivityRecord",
    "NavigationalTransit",
    "OperationFactory",
    "Timeline",
    "TimelineGenerator",
    "calculate_timeline_statistics",
    "fill_duration_summary",
    "generate_timeline",
    "timeline_minutes",
    "trim_overlaps",
]


def __getattr__(name: str) -> object:
    """Resolve deprecated names (CruiseSchedule) with a warning."""
    from cruiseplan import _deprecated

    return _deprecated.module_getattr(__name__, name, {"CruiseSchedule": Timeline})


# =============================================================================
# Operation Factory
# =============================================================================


class OperationFactory:
    """Factory for creating operation objects from configuration data."""

    def __init__(self, config: CruiseConfig) -> None:
        self.config = config

    def create_operation(self, name: str, leg_name: str) -> BaseOperation:  # noqa: ARG002 - public signature; leg_name not used yet
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
                        return PointOperation.from_pydantic(item)
                    if operation_type == "line":
                        return LineOperation.from_pydantic(
                            item, self.config.default_vessel_speed_kt
                        )
                    if operation_type == "area":
                        return AreaOperation.from_pydantic(item)

        # Fallback: Try to resolve from global ports registry
        try:
            from cruiseplan.config.ports import resolve_port_reference

            port_def = resolve_port_reference(name)
            return PointOperation.from_port(port_def)
        except ValueError:
            pass

        raise ValueError(f"Could not resolve operation: {name}")


# =============================================================================
# Statistics Calculator
# =============================================================================


def _categorize_activities(timeline: Timeline) -> dict[str, list]:
    """Group records into the statistics categories by kind and transit direction."""
    groups: dict[str, list] = {
        "station_activities": [],
        "mooring_activities": [],
        "area_activities": [],
        "scientific_transits": [],
        "port_activities": [],
        "port_transits_to_area": [],
        "port_transits_from_area": [],
        "within_area_transits": [],
    }
    by_kind = {
        "station": "station_activities",
        "mooring": "mooring_activities",
        "port": "port_activities",
        "line": "scientific_transits",
        "area": "area_activities",
    }
    for i, record in enumerate(timeline):
        if record.kind in by_kind:
            groups[by_kind[record.kind]].append(record)
            logger.info(f"   Adding to {by_kind[record.kind]}: {record.label}")
        elif record.kind == "transit":
            is_from_port, is_to_port = _check_transit_direction(timeline, i)
            if is_from_port:
                groups["port_transits_to_area"].append(record)
            elif is_to_port:
                groups["port_transits_from_area"].append(record)
            else:
                groups["within_area_transits"].append(record)
        # Buffers are contingency time, in no group
    return groups


def _check_transit_direction(timeline: Timeline, index: int) -> tuple[bool, bool]:
    """Return (from port, to port) for the transit at *index*."""
    is_from_port = index > 0 and timeline[index - 1].kind == "port"
    is_to_port = index < len(timeline) - 1 and timeline[index + 1].kind == "port"
    return is_from_port, is_to_port


def timeline_minutes(timeline: Timeline) -> float:
    """
    Return the elapsed time of a timeline: last end minus first start.

    Waiting from a positive ``delay_start_minutes`` lies between records, so
    this total includes it where a sum of durations would not.

    Parameters
    ----------
    timeline : Timeline
        Records in schedule order.

    Returns
    -------
    float
        Minutes from the first start to the last end (0 for an empty timeline).
    """
    if not timeline:
        return 0.0
    end = max(record.end_time for record in timeline)
    return (end - timeline[0].start_time).total_seconds() / 60.0


def fill_duration_summary(timeline: Timeline) -> str | None:
    """
    Return a one-line summary of operations scheduled at the fill duration.

    Names how many operations use the fill duration and the schedule total with
    those operations excluded, so the inflated fill hours do not hide the real
    total.

    Parameters
    ----------
    timeline : Timeline
        Records making up the schedule.

    Returns
    -------
    str or None
        The summary line, or None when no operation uses the fill duration.
    """
    from cruiseplan.utils.units import hours_to_days

    filled = [r for r in timeline if r.duration_is_fill]
    if not filled:
        return None
    fill_hours = DEFAULT_MOORING_DURATION_MIN / 60
    real_minutes = sum(r.duration_minutes for r in timeline if not r.duration_is_fill)
    real_days = hours_to_days(real_minutes / 60)
    return (
        f"{len(filled)} operation(s) at the fill duration "
        f"({len(filled)} x {fill_hours:.0f} h); schedule total excluding fills: "
        f"{real_days:.1f} days"
    )


def _calculate_transit_stats(transits: Timeline) -> dict[str, float]:
    """Count, duration, distance and mean speed of transit records."""
    from cruiseplan.utils.units import hours_to_days

    if not transits:
        return {
            "count": 0,
            "total_duration_h": 0,
            "total_duration_days": 0,
            "total_distance_nm": 0,
            "avg_speed_kt": 0,
        }

    total_duration_h = sum(r.duration_minutes for r in transits) / 60.0
    total_distance_nm = sum(r.dist_nm for r in transits)
    avg_speed_kt = total_distance_nm / total_duration_h if total_duration_h > 0 else 0

    return {
        "count": len(transits),
        "total_duration_h": total_duration_h,
        "total_duration_days": hours_to_days(total_duration_h),
        "total_distance_nm": total_distance_nm,
        "avg_speed_kt": avg_speed_kt,
    }


def _log_debug_counts(
    categorized: dict[str, list], leg_stats: dict[str, dict[str, int]]
) -> None:
    """Log debug information about operation counts."""
    station_activities = categorized["station_activities"]
    mooring_activities = categorized["mooring_activities"]
    scientific_transits = categorized["scientific_transits"]
    area_activities = categorized["area_activities"]
    port_activities = categorized["port_activities"]
    within_area_transits = categorized["within_area_transits"]

    total_scientific_operations = (
        len(station_activities)
        + len(mooring_activities)
        + len(scientific_transits)
        + len(area_activities)
    )

    logger.info("Cruise-level operation counts:")
    logger.info(f"   Stations: {len(station_activities)}")
    logger.info(f"   Moorings: {len(mooring_activities)}")
    logger.info(f"   Scientific transits (surveys): {len(scientific_transits)}")
    logger.info(f"   Area operations: {len(area_activities)}")
    logger.info(f"   Total scientific operations: {total_scientific_operations}")
    logger.info(f"   Port activities: {len(port_activities)}")
    logger.info(f"   Within-area transits: {len(within_area_transits)}")

    for leg_name, stats in leg_stats.items():
        logger.info(f"Leg '{leg_name}' operation counts:")
        logger.info(f"   Stations: {stats['stations']}")
        logger.info(f"   Moorings: {stats['moorings']}")
        logger.info(f"   Surveys: {stats['surveys']}")
        logger.info(f"   Areas: {stats['areas']}")
        logger.info(f"   Total scientific operations: {stats['total_scientific']}")
        logger.info(f"   Total activities in leg: {stats['total_activities']}")


def _calculate_leg_statistics(timeline: Timeline) -> dict[str, dict[str, int]]:
    """Operation counts per leg."""
    counter = {
        "station": "stations",
        "mooring": "moorings",
        "line": "surveys",
        "area": "areas",
    }
    leg_stats: dict[str, dict[str, int]] = {}
    for record in timeline:
        stats = leg_stats.setdefault(
            record.leg_name,
            {
                "stations": 0,
                "moorings": 0,
                "surveys": 0,
                "areas": 0,
                "total_scientific": 0,
                "ports": 0,
                "transits": 0,
                "total_activities": 0,
            },
        )
        stats["total_activities"] += 1
        if record.kind == "port":
            stats["ports"] += 1
        elif record.kind == "transit":
            stats["transits"] += 1
        elif record.is_science:
            stats["total_scientific"] += 1
            stats[counter[record.kind]] += 1
    return leg_stats


def calculate_timeline_statistics(timeline: Timeline) -> dict[str, Any]:
    """
    Calculate summary statistics for cruise timeline activities.

    Groups records into scientific operations (stations, surveys, areas) and
    supporting operations (transits, ports) for summary reporting.

    Parameters
    ----------
    timeline : Timeline
        Records from the scheduler.

    Returns
    -------
    dict
        Statistics for each activity type with keys 'stations', 'surveys',
        'areas', 'moorings', 'within_area_transits', 'port_transits', the
        per-leg counts, and the grouped record lists.
    """
    from cruiseplan.utils.units import hours_to_days

    categorized = _categorize_activities(timeline)

    def calc_stats(
        activities: Timeline,
        include_distance: bool = False,
        include_depth: bool = False,
    ) -> dict[str, float]:
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

        total_duration_h = sum(r.duration_minutes for r in activities) / 60.0
        stats = {
            "count": len(activities),
            "avg_duration_h": total_duration_h / len(activities),
            "total_duration_h": total_duration_h,
            "total_duration_days": hours_to_days(total_duration_h),
        }
        if include_distance:
            total_distance_nm = sum(r.dist_nm for r in activities)
            stats.update(
                {
                    "avg_distance_nm": total_distance_nm / len(activities),
                    "total_distance_nm": total_distance_nm,
                }
            )
        if include_depth:
            depths = [r.depth_m for r in activities if r.depth_m is not None]
            stats.update({"avg_depth_m": sum(depths) / len(depths) if depths else 0.0})
        return stats

    station_activities = categorized["station_activities"]
    mooring_activities = categorized["mooring_activities"]
    area_activities = categorized["area_activities"]
    scientific_transits = categorized["scientific_transits"]
    port_activities = categorized["port_activities"]
    port_transits_to_area = categorized["port_transits_to_area"]
    port_transits_from_area = categorized["port_transits_from_area"]
    within_area_transits = categorized["within_area_transits"]

    leg_stats = _calculate_leg_statistics(timeline)
    _log_debug_counts(categorized, leg_stats)

    return {
        "stations": calc_stats(station_activities, include_depth=True),
        "moorings": calc_stats(mooring_activities),
        "surveys": calc_stats(scientific_transits, include_distance=True),
        "areas": calc_stats(area_activities),
        "within_area_transits": _calculate_transit_stats(within_area_transits),
        "port_transits_to_area": _calculate_transit_stats(port_transits_to_area),
        "port_transits_from_area": _calculate_transit_stats(port_transits_from_area),
        "port_activities": calc_stats(port_activities),
        "leg_stats": leg_stats,
        "total_scientific": sum(s["total_scientific"] for s in leg_stats.values()),
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


@dataclass(frozen=True)
class _Rules:
    """Duration rules for one operation: the cruise config and the leg's values."""

    config: CruiseConfig
    turnaround_time_minutes: float | None = None


def trim_overlaps(timeline: Timeline) -> Timeline:
    """
    Shorten each record that runs past the start of the next one.

    A negative ``delay_start_minutes`` means the previous activity ended
    early: the next record starts before the previous one ends. The previous
    record is ended where the next one starts (its duration is never below
    zero); ``planned_duration_minutes`` keeps the planned value. The sum of
    the durations then equals the elapsed time, and the schedule matches what
    the forecast shows.

    Parameters
    ----------
    timeline : Timeline
        Records in schedule order.

    Returns
    -------
    Timeline
        A new list; trimmed records are replaced by copies.
    """
    out = list(timeline)
    for i in range(1, len(out)):
        previous, record = out[i - 1], out[i]
        if record.start_time < previous.end_time:
            end = max(record.start_time, previous.start_time)
            out[i - 1] = previous.replace(
                end_time=end,
                duration_minutes=(end - previous.start_time).total_seconds() / 60.0,
            )
    return out


class TimelineGenerator:
    """Generates cruise timeline from operations and legs."""

    def __init__(self, config: CruiseConfig) -> None:
        self.config = config
        self.factory = OperationFactory(config)
        self.current_time = self._parse_start_datetime()
        # Operation label -> why it was scheduled with the fill duration
        self._fill_reasons: dict[str, str] = {}

    def generate_timeline(self, legs: list["Leg"] | None = None) -> Timeline:
        """
        Generate the cruise timeline.

        Parameters
        ----------
        legs : list of Leg, optional
            Runtime legs; built from the configuration when not given.

        Returns
        -------
        Timeline
            Records in schedule order.
        """
        if legs is None:
            legs = self._create_runtime_legs()

        timeline = []
        self._fill_reasons = {}

        for leg in legs:
            leg_activities = self._process_leg(leg)
            timeline.extend(leg_activities)
        timeline = trim_overlaps(timeline)

        for name, reason in self._fill_reasons.items():
            logger.warning(
                f"Operation {name}: {reason}; scheduled with the fill duration "
                f"{DEFAULT_MOORING_DURATION_MIN / 60:.0f} h. Add 'duration_minutes:' or a "
                f"depth in the YAML."
            )
        summary = fill_duration_summary(timeline)
        if summary:
            logger.warning(summary)

        return timeline

    def _create_runtime_legs(self) -> list["Leg"]:
        """Create runtime legs from config."""
        # Import here to avoid circular imports
        from cruiseplan.runtime.organizational import Leg

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
                runtime_leg.vessel_speed = leg_def.vessel_speed_kt
                runtime_leg.turnaround_time = leg_def.turnaround_time_minutes
                runtime_leg.distance_between_stations = (
                    leg_def.distance_between_stations_km
                )
                runtime_leg.delay_start = leg_def.delay_start_minutes
                runtime_leg.buffer_time = leg_def.buffer_time_minutes

                runtime_legs.append(runtime_leg)
            except Exception as e:  # noqa: BLE001 - skip a leg that cannot be built; others are scheduled
                logger.warning(
                    f"Failed to create runtime leg for '{leg_def.name}': {e}"
                )

        return runtime_legs

    def _process_leg(self, leg: "Leg") -> list[ActivityRecord]:
        """Process a single leg and generate activities."""
        # Initialize current_time if not set
        if self.current_time is None:
            self.current_time = self._parse_start_datetime()

        # Apply leg-level delay (e.g. port clearance wait before departure)
        leg_delay = getattr(leg, "delay_start", None) or 0.0
        if leg_delay:
            self.current_time = self.current_time + timedelta(minutes=leg_delay)

        activities = []

        # Build scientific sequence: departure_port + leg_activities (arrival_port handled separately)
        # Validation ensures departure_port and arrival_port are required fields
        # Use full port objects (which may contain enriched action info) instead of just names
        scientific_activities = [leg.departure_port]

        # Get leg activities - check both runtime leg and config leg
        leg_activities = self._extract_activities_from_leg(leg)
        if not leg_activities and hasattr(self.config, "legs"):
            for config_leg in self.config.legs:
                if config_leg.name == leg.name and hasattr(config_leg, "activities"):
                    leg_activities = config_leg.activities
                    break

        scientific_activities.extend(leg_activities or [])

        previous_operation = None

        # Process departure port and all scientific activities
        for activity in scientific_activities:
            try:
                operation = self._create_operation_from_activity(activity, leg)
                self._add_transit_and_operation(
                    operation, activities, leg, previous_operation
                )
                previous_operation = operation
            except Exception:
                activity_name = getattr(activity, "name", str(activity))
                logger.exception(f"Failed to process activity '{activity_name}'")
                continue

        # Insert buffer time contingency block after last scientific station,
        # before the return transit to arrival port
        buffer_time = getattr(leg, "buffer_time", None)
        if buffer_time and previous_operation is not None:
            buffer_activity = self._create_buffer_activity(
                leg, previous_operation, buffer_time
            )
            activities.append(buffer_activity)

        # Process arrival port (transit computed from current_time, which includes buffer)
        try:
            operation = self._create_operation_from_activity(leg.arrival_port, leg)
            self._add_transit_and_operation(
                operation, activities, leg, previous_operation
            )
        except Exception:
            logger.exception("Failed to process arrival port")

        return activities

    def _create_buffer_activity(
        self, leg: "Leg", last_operation: BaseOperation, duration_minutes: float
    ) -> ActivityRecord:
        """Create a contingency buffer block at the position of the last operation.

        Parameters
        ----------
        leg : Leg
            The current leg (provides name for labelling).
        last_operation : BaseOperation
            The last scientific operation; the buffer is placed at its exit position.
        duration_minutes : float
            Buffer duration in minutes.

        Returns
        -------
        ActivityRecord
            A stationary buffer record; advances ``self.current_time`` by duration.
        """
        _, exit_pt = last_operation.get_coordinates()

        buffer_start = self.current_time
        buffer_end = buffer_start + timedelta(minutes=duration_minutes)

        activity = ActivityRecord(
            kind="buffer",
            activity="Buffer",
            label=f"Contingency ({duration_minutes:.0f} min)",
            entry_lat=exit_pt.latitude,
            entry_lon=exit_pt.longitude,
            exit_lat=exit_pt.latitude,
            exit_lon=exit_pt.longitude,
            start_time=buffer_start,
            end_time=buffer_end,
            duration_minutes=duration_minutes,
            planned_duration_minutes=duration_minutes,
            dist_nm=0.0,
            vessel_speed_kt=0.0,
            leg_name=leg.name,
            op_type="buffer",
            operation_class="Buffer",
            comment="Weather/operational contingency buffer",
        )

        self.current_time = buffer_end
        return activity

    def _create_operation_from_activity(
        self,
        activity: str | PointDefinition | LineDefinition | AreaDefinition,
        leg: "Leg",
    ) -> BaseOperation:
        """Create operation object from activity definition."""
        if isinstance(activity, str):
            # Regular activity name - use factory
            return self.factory.create_operation(activity, leg.name)
        # Definition object - create directly
        return self._create_operation_from_definition(activity, leg)

    def _create_operation_from_definition(
        self, activity: PointDefinition | LineDefinition | AreaDefinition, leg: "Leg"
    ) -> BaseOperation:
        """Create operation from Pydantic definition object."""
        from cruiseplan.config.activities import (
            AreaDefinition,
            LineDefinition,
            PointDefinition,
        )
        from cruiseplan.runtime.operations import (
            AreaOperation,
            LineOperation,
            PointOperation,
        )

        if isinstance(activity, PointDefinition):
            if (
                hasattr(activity, "operation_type")
                and activity.operation_type
                and activity.operation_type.value == "port"
            ):
                return PointOperation.from_port(activity)
            return PointOperation.from_pydantic(activity)
        if isinstance(activity, LineDefinition):
            return LineOperation.from_pydantic(activity, leg.vessel_speed)
        if isinstance(activity, AreaDefinition):
            return AreaOperation.from_pydantic(activity)
        raise TypeError(
            f"Unknown activity type: {type(activity)}. "
            f"Expected PointDefinition, LineDefinition, or AreaDefinition, got {activity}"
        )

    def _add_transit_and_operation(
        self,
        operation: BaseOperation,
        activities: list[ActivityRecord],
        leg: "Leg",
        previous_operation: BaseOperation | None,
    ) -> None:
        """Add navigational transit and operation to activities list."""
        # Add navigational transit between all operations
        if previous_operation is not None:
            transit = self._create_navigational_transit(
                previous_operation, operation, leg.name, leg
            )
            if transit:
                activities.append(transit)

        # Add the operation activity
        operation_activity = self._create_operation_activity(operation, leg)
        activities.append(operation_activity)

    def _create_navigational_transit(
        self,
        from_op: BaseOperation,
        to_op: BaseOperation,
        leg_name: str = "unknown",
        leg: "Leg | None" = None,
    ) -> ActivityRecord | None:
        """Create navigational transit between operations."""
        # Get leg-specific vessel speed if available
        leg_vessel_speed = None
        if leg and hasattr(leg, "vessel_speed"):
            leg_vessel_speed = leg.vessel_speed

        transit = NavigationalTransit(
            from_op, to_op, self.config, leg_name, vessel_speed=leg_vessel_speed
        )

        # Create rules object for calculate_duration
        duration_minutes = transit.calculate_duration(_Rules(self.config))

        # Skip zero-distance transits
        if duration_minutes <= 0:
            return None

        entry_pt, exit_pt = transit.get_coordinates()
        activity = ActivityRecord(
            kind="transit",
            activity="Transit",
            label=transit.get_label(),
            entry_lat=entry_pt.latitude,
            entry_lon=entry_pt.longitude,
            exit_lat=exit_pt.latitude,
            exit_lon=exit_pt.longitude,
            start_time=self.current_time,
            end_time=self.current_time + timedelta(minutes=duration_minutes),
            duration_minutes=duration_minutes,
            planned_duration_minutes=duration_minutes,
            dist_nm=transit.get_operation_distance_nm(),
            vessel_speed_kt=transit.get_vessel_speed(),
            leg_name=leg_name,
            op_type="transit",
            operation_class=transit.__class__.__name__,
        )

        self.current_time = activity.end_time
        return activity

    def _create_operation_activity(
        self, operation: BaseOperation, leg: "Leg"
    ) -> ActivityRecord:
        """Create activity record for a scientific operation."""
        entry_pt, exit_pt = operation.get_coordinates()
        leg_name = leg.name
        rules = _Rules(self.config, getattr(leg, "turnaround_time", None))
        duration_minutes = operation.calculate_duration(rules)
        if getattr(operation, "duration_is_fill", False):
            self._fill_reasons.setdefault(
                operation.get_label(),
                getattr(operation, "duration_fill_reason", None) or "no duration",
            )

        # Apply delay_start if specified
        delay_start_minutes = getattr(operation, "delay_start", 0.0) or 0.0
        actual_start_time = self.current_time + timedelta(minutes=delay_start_minutes)

        op_type = getattr(operation, "op_type", operation.get_operation_type().lower())
        action = getattr(operation, "action", None)
        if action is not None:
            action = action.value if hasattr(action, "value") else str(action)
        activity = ActivityRecord(
            kind=kind_of(operation.__class__.__name__, op_type),
            activity=operation.get_operation_type(),
            label=operation.get_label(),
            entry_lat=entry_pt.latitude,
            entry_lon=entry_pt.longitude,
            exit_lat=exit_pt.latitude,
            exit_lon=exit_pt.longitude,
            operation_depth_m=getattr(operation, "operation_depth", None),
            water_depth_m=getattr(operation, "water_depth", None),
            start_time=actual_start_time,
            end_time=actual_start_time + timedelta(minutes=duration_minutes),
            duration_minutes=duration_minutes,
            planned_duration_minutes=duration_minutes,
            duration_is_fill=bool(getattr(operation, "duration_is_fill", False)),
            delay_start_minutes=delay_start_minutes,
            comment=getattr(operation, "comment", None),
            dist_nm=getattr(operation, "get_operation_distance_nm", lambda: 0.0)(),
            vessel_speed_kt=getattr(
                operation,
                "get_vessel_speed",
                lambda: self.config.default_vessel_speed_kt,
            )(),
            leg_name=leg_name,
            op_type=op_type,
            operation_class=operation.__class__.__name__,
            action=action or None,
        )

        self.current_time = activity.end_time
        return activity

    def _extract_activities_from_operations(self, leg: "Leg") -> list[str]:
        """Extract activities from leg operations."""
        activities = []
        if hasattr(leg, "operations") and leg.operations:
            for operation in leg.operations:
                if hasattr(operation, "name"):
                    activities.append(operation.name)
                elif hasattr(operation, "station") and hasattr(
                    operation.station, "name"
                ):
                    activities.append(operation.station.name)
        return activities

    def _extract_activities_from_clusters(
        self, clusters: "list[Cluster] | list[ClusterDefinition]"
    ) -> list[str]:
        """Extract activities from cluster definitions."""
        activities = []
        for cluster in clusters:
            if hasattr(cluster, "activities") and cluster.activities:
                for activity in cluster.activities:
                    if hasattr(activity, "name"):
                        activities.append(activity.name)
                    else:
                        activities.append(str(activity))
        return activities

    def _extract_activities_from_config_leg(self, leg: "Leg") -> list[str]:
        """Extract activities from matching config leg."""
        activities = []
        if hasattr(self.config, "legs"):
            for config_leg in self.config.legs:
                if config_leg.name == leg.name:
                    if hasattr(config_leg, "clusters") and config_leg.clusters:
                        activities.extend(
                            self._extract_activities_from_clusters(config_leg.clusters)
                        )
                    elif hasattr(config_leg, "activities") and config_leg.activities:
                        activities.extend(config_leg.activities)
                    break
        return activities

    def _extract_activities_from_leg(self, leg: "Leg") -> list[str]:
        """Extract activity names from leg definition."""
        # Try runtime leg operations first
        activities = self._extract_activities_from_operations(leg)

        # Try runtime leg clusters
        if not activities and hasattr(leg, "clusters") and leg.clusters:
            activities = self._extract_activities_from_clusters(leg.clusters)

        # Try config leg as fallback
        if not activities:
            activities = self._extract_activities_from_config_leg(leg)

        # Final fallback: direct activities attribute
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
            start_time = getattr(self.config, "start_time", "08:00")
            return datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            logger.exception("Invalid start_date or start_time format")
            # Return a default datetime instead of None
            return datetime(1970, 1, 1, 8, 0, 0)


# =============================================================================
# Main API Functions (for backward compatibility)
# =============================================================================


def generate_timeline(
    cruise: "CruiseInstance", legs: list["Leg"] | None = None
) -> Timeline:
    """
    Generate cruise timeline directly from CruiseInstance object.

    This function eliminates the need for YAML serialization/deserialization
    by working directly with the CruiseInstance object's validated configuration.

    Parameters
    ----------
    cruise : cruiseplan.runtime.cruise.CruiseInstance
        CruiseInstance object with enhanced data
    legs : Optional[List[Any]]
        Runtime legs (if None, will be created from config)

    Returns
    -------
    Timeline
        Records in schedule order.
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
    output_dir: str = "data",  # noqa: ARG001 - kept for backward compatibility
    formats: list[str] | None = None,
    validate_depths: bool = False,
    selected_leg: str | None = None,
    derive_netcdf: bool = False,  # noqa: ARG001 - kept for backward compatibility
    bathy_source: str = "gebco2025",  # noqa: ARG001 - kept for backward compatibility
    bathy_dir: str = "data/bathymetry",  # noqa: ARG001 - kept for backward compatibility
    bathy_stride: int = 10,  # noqa: ARG001 - kept for backward compatibility
    figsize: list[float] | None = None,  # noqa: ARG001 - kept for backward compatibility
    output_basename: str | None = None,  # noqa: ARG001 - kept for backward compatibility
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
    from cruiseplan.runtime.cruise import CruiseInstance

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
    total_duration_h = timeline_minutes(timeline) / 60.0
    total_transit_nm = sum(
        record.dist_nm for record in timeline if record.kind == "transit"
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
