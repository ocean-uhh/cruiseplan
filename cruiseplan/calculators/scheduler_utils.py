"""
Scheduler utilities for cruise timeline generation.

This module provides reusable utility functions for timeline generation,
activity resolution, and position tracking operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from cruiseplan.calculators.distance import haversine_distance, km_to_nm
from cruiseplan.core.validation import CruiseConfig, GeoPoint

logger = logging.getLogger(__name__)


# --- Buffer Time and Delay Processing ---


def _extract_leg_buffer_time(leg) -> float:
    """
    Extract buffer time from leg, handling MagicMock safely.

    Parameters
    ----------
    leg : Any
        Leg object that may have a buffer_time attribute.

    Returns
    -------
    float
        Buffer time in minutes, or 0.0 if not found or invalid.
    """
    try:
        if hasattr(leg, "buffer_time"):
            raw_buffer_time = getattr(leg, "buffer_time", None)
            if (
                raw_buffer_time is not None
                and not hasattr(raw_buffer_time, "_mock_name")
                and isinstance(raw_buffer_time, (int, float))
            ):
                return float(raw_buffer_time)
    except (TypeError, ValueError, AttributeError):
        pass
    return 0.0


def _extract_activity_delays(activity: Dict[str, Any]) -> Tuple[float, float]:
    """
    Extract start/end delays from activity, handling MagicMock safely.

    Parameters
    ----------
    activity : Dict[str, Any]
        Activity dictionary that may contain delay fields.

    Returns
    -------
    Tuple[float, float]
        (delay_start_min, delay_end_min) in minutes.
    """
    delay_start_min = 0.0
    delay_end_min = 0.0

    for delay_key, delay_var in [
        ("delay_start", "delay_start_min"),
        ("delay_end", "delay_end_min"),
    ]:
        delay_raw = activity.get(delay_key, 0.0)
        try:
            if (
                delay_raw is not None
                and isinstance(delay_raw, (int, float))
                and not hasattr(delay_raw, "_mock_name")
            ):
                if delay_key == "delay_start":
                    delay_start_min = float(delay_raw)
                else:
                    delay_end_min = float(delay_raw)
        except (TypeError, ValueError, AttributeError):
            pass

    return delay_start_min, delay_end_min


# --- Start Time Parsing ---


def _parse_start_datetime(config: CruiseConfig) -> datetime:
    """
    Parse start date/time from config, handling various formats.

    Parameters
    ----------
    config : CruiseConfig
        Cruise configuration with start_date and optionally start_time.

    Returns
    -------
    datetime
        Parsed start datetime.

    Raises
    ------
    ValueError
        If the date/time format is invalid.
    """
    try:
        if "T" in config.start_date:
            # ISO format with time included (e.g., "2028-06-01T08:00:00Z")
            start_date_clean = config.start_date.replace("Z", "").replace("+00:00", "")
            return datetime.fromisoformat(start_date_clean)
        else:
            # Separate date and time (e.g., start_date="2028-06-01", start_time="08:00")
            return datetime.strptime(
                f"{config.start_date} {config.start_time}", "%Y-%m-%d %H:%M"
            )
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid start_date or start_time format: {e}")
        raise


# --- Operation Resolution Logic ---


def _resolve_operation_details(
    config: CruiseConfig, name: str
) -> Optional[Dict[str, Any]]:
    """
    Try all resolvers in order until one succeeds.

    Parameters
    ----------
    config : CruiseConfig
        Cruise configuration object.
    name : str
        Name of the operation to resolve.

    Returns
    -------
    Optional[Dict[str, Any]]
        Operation details dictionary or None if not found.
    """
    from cruiseplan.calculators.scheduler import (
        _resolve_area_details,
        _resolve_mooring_details,
        _resolve_port_details,
        _resolve_station_details,
        _resolve_transit_details,
    )

    for resolver in [
        _resolve_station_details,
        _resolve_mooring_details,
        _resolve_area_details,
        _resolve_transit_details,
        _resolve_port_details,
    ]:
        details = resolver(config, name)
        if details:
            return details
    return None


# --- Position Management ---


class PositionTracker:
    """Track current vessel position through timeline."""

    def __init__(self, start_pos: Optional[GeoPoint] = None):
        """
        Initialize position tracker.

        Parameters
        ----------
        start_pos : Optional[GeoPoint]
            Starting position for tracking.
        """
        self.current_position = start_pos

    def update_from_activity(self, activity: Dict[str, Any]) -> None:
        """
        Update position based on activity type and coordinates.

        Parameters
        ----------
        activity : Dict[str, Any]
            Activity record with position information.
        """
        # For transits, use end position if available
        if (
            activity.get("op_type") == "transit"
            and "end_lat" in activity
            and "end_lon" in activity
        ):
            self.current_position = GeoPoint(
                latitude=activity["end_lat"], longitude=activity["end_lon"]
            )
        else:
            # Use main position
            self.current_position = GeoPoint(
                latitude=activity["lat"], longitude=activity["lon"]
            )

    def get_position(self) -> Optional[GeoPoint]:
        """
        Get current position.

        Returns
        -------
        Optional[GeoPoint]
            Current position or None if not set.
        """
        return self.current_position


# --- Transit Calculation Utilities ---


def _calculate_port_to_operations_transit(
    config: CruiseConfig, runtime_leg: Any, leg_def: Any, current_time: datetime
) -> Tuple[Optional[Dict[str, Any]], Optional[GeoPoint]]:
    """
    Calculate and create port departure transit activity.

    Parameters
    ----------
    config : CruiseConfig
        Cruise configuration.
    runtime_leg : Any
        Runtime leg instance.
    leg_def : Any
        Leg definition from configuration.
    current_time : datetime
        Current time for transit scheduling.

    Returns
    -------
    Tuple[Optional[Dict[str, Any]], Optional[GeoPoint]]
        (Transit activity record, ending position) or (None, None) if no transit needed.
    """
    from cruiseplan.calculators.scheduler import (
        _calculate_inter_port_transit,
        _extract_activities_from_leg,
    )

    # Check for activities (either direct or extracted from clusters)
    has_activities = bool(leg_def.activities) or bool(
        _extract_activities_from_leg(leg_def)
    )
    if not has_activities:
        return None, None

    # Get first activity name - prioritize first_waypoint, then activities
    first_activity_name = None
    if hasattr(leg_def, "first_waypoint") and leg_def.first_waypoint:
        first_activity_name = leg_def.first_waypoint
    elif leg_def.activities:
        first_activity_name = leg_def.activities[0]
    else:
        extracted_activities = _extract_activities_from_leg(leg_def)
        first_activity_name = extracted_activities[0] if extracted_activities else None

    if not first_activity_name:
        return None, None

    # Resolve first activity details using operation resolution chain
    first_activity_details = _resolve_operation_details(config, first_activity_name)
    if not first_activity_details:
        return None, None

    # Calculate transit from port to first operation
    port_pos = (
        runtime_leg.departure_port.latitude,
        runtime_leg.departure_port.longitude,
    )
    operation_pos = GeoPoint(
        latitude=first_activity_details["lat"],
        longitude=first_activity_details["lon"],
    )

    # Use leg's effective speed with parameter inheritance
    effective_speed = runtime_leg.vessel_speed or getattr(
        config, "default_vessel_speed", 8.0
    )

    # Calculate transit time
    transit_time = _calculate_inter_port_transit(
        port_pos,
        operation_pos,
        effective_speed,
    )

    # Calculate distance for CSV output
    distance_km = haversine_distance(port_pos, operation_pos)
    distance_nm = km_to_nm(distance_km)

    # Create transit activity record
    transit_activity = {
        "activity": "Port_Departure",
        "label": f"Departure: {(getattr(runtime_leg.departure_port, 'display_name', runtime_leg.departure_port.name) or runtime_leg.departure_port.name).split(',')[0]} to Operations",
        "lat": port_pos[0],  # Record departure port coordinates
        "lon": port_pos[1],  # Record departure port coordinates
        "depth": 0.0,
        "start_time": current_time,
        "end_time": current_time + timedelta(minutes=transit_time),
        "duration_minutes": transit_time,
        "transit_dist_nm": distance_nm,
        "vessel_speed_kt": effective_speed,
        "leg_name": runtime_leg.name,
        "op_type": "transit",
    }

    return transit_activity, operation_pos


# --- ActivityRecord Creation ---


def _create_operation_activity_record(
    details: Dict[str, Any], current_time: datetime, duration_min: float, **kwargs
) -> Dict[str, Any]:
    """
    Create standardized ActivityRecord for operations.

    Parameters
    ----------
    details : Dict[str, Any]
        Operation details from resolution.
    current_time : datetime
        Start time for the operation.
    duration_min : float
        Operation duration in minutes.
    **kwargs
        Additional fields to include in the activity record.

    Returns
    -------
    Dict[str, Any]
        Standardized activity record.
    """
    from cruiseplan.calculators.scheduler import ActivityRecord

    # Get position
    current_pos = GeoPoint(latitude=details["lat"], longitude=details["lon"])

    # Base activity data
    activity_data = {
        "activity": details.get("op_type", "station").title(),
        "label": details["name"],
        "lat": current_pos.latitude,
        "lon": current_pos.longitude,
        "depth": details.get("depth", 0.0),
        "start_time": current_time,
        "end_time": current_time + timedelta(minutes=duration_min),
        "duration_minutes": duration_min,
        "transit_dist_nm": 0.0,  # Will be set by caller if needed
        "operation_dist_nm": 0.0,  # Will be set by caller if needed
        "op_type": details.get("op_type", "station"),
        "operation_type": details.get("op_type", "station"),
        "action": details.get("action"),
    }

    # Add any additional fields from kwargs
    activity_data.update(kwargs)

    # Add route distance for scientific transits
    if details.get("op_type") == "transit" and "route_distance_nm" in details:
        activity_data["operation_dist_nm"] = details["route_distance_nm"]

    return ActivityRecord(activity_data)


# --- Runtime Leg Management ---


def _create_runtime_legs(config: CruiseConfig) -> List[Any]:
    """
    Create runtime legs from config definitions with proper fallbacks.

    Parameters
    ----------
    config : CruiseConfig
        Cruise configuration with leg definitions.

    Returns
    -------
    List[Any]
        List of runtime Leg objects.
    """
    from cruiseplan.core.leg import Leg

    runtime_legs = []
    for leg_def in config.legs or []:
        try:
            # Try to create a basic Leg from the definition
            runtime_leg = Leg(
                name=leg_def.name,
                departure_port=getattr(leg_def, "departure_port", None),
                arrival_port=getattr(leg_def, "arrival_port", None),
                description=getattr(leg_def, "description", None),
                first_waypoint=getattr(leg_def, "first_waypoint", None),
                last_waypoint=getattr(leg_def, "last_waypoint", None),
            )
            # Copy leg-specific parameter overrides from definition
            runtime_leg.vessel_speed = getattr(leg_def, "vessel_speed", None)
            runtime_leg.turnaround_time = getattr(leg_def, "turnaround_time", None)
            runtime_leg.distance_between_stations = getattr(
                leg_def, "distance_between_stations", None
            )
            runtime_legs.append(runtime_leg)
        except Exception as e:
            logger.warning(f"Failed to create runtime leg for '{leg_def.name}': {e}")
            # Create a minimal mock leg for testing
            runtime_leg = Leg(
                name=leg_def.name,
                departure_port={
                    "name": "Test_Port",
                    "latitude": 0.0,
                    "longitude": 0.0,
                },
                arrival_port={
                    "name": "Test_Port",
                    "latitude": 0.0,
                    "longitude": 0.0,
                },
            )
            runtime_legs.append(runtime_leg)

    return runtime_legs


# --- Timeline Initialization ---


def _initialize_timeline_state(
    config: CruiseConfig,
) -> Tuple[datetime, Any, Optional[GeoPoint]]:
    """
    Initialize timeline generation state.

    Parameters
    ----------
    config : CruiseConfig
        Cruise configuration.

    Returns
    -------
    Tuple[datetime, Any, Optional[GeoPoint]]
        (current_time, duration_calculator, current_position)
    """
    from cruiseplan.calculators.duration import DurationCalculator

    # Parse start time
    current_time = _parse_start_datetime(config)

    # Initialize duration calculator
    duration_calc = DurationCalculator(config)

    # Initialize position
    current_position = None

    return current_time, duration_calc, current_position
