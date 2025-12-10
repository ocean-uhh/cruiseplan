"""
Core cruise scheduling and timeline generation logic (Phase 3a/3c).

Implements sequential ordering logic and time/distance calculation.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from cruiseplan.calculators.distance import (
    haversine_distance,  # Returns km
    km_to_nm,
    route_distance,
)
from cruiseplan.calculators.duration import (
    DurationCalculator,  # Provides duration lookup
)

# Import core components and calculators (assuming they are complete)
from cruiseplan.core.validation import CruiseConfig, GeoPoint
from cruiseplan.utils.constants import hours_to_minutes

logger = logging.getLogger(__name__)

# --- Data Structure Definitions ---


class ActivityRecord(Dict):
    """Standardized output structure for a single scheduled activity."""

    activity: str
    label: str
    lat: float
    lon: float
    depth: float
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    transit_dist_nm: float  # Inter-operation distance (to reach this operation)
    operation_dist_nm: float  # Distance traveled during this operation
    vessel_speed_kt: float
    leg_name: str
    operation_type: str
    # Reference to original object/definition for detailed export


# --- Core Scheduling Logic ---


def _resolve_station_details(config: CruiseConfig, name: str) -> Optional[Dict]:
    """Finds a station, mooring, or transit definition by name."""
    # Check stations (includes all point operations: CTD, mooring, etc.)
    if config.stations:
        match = next((s for s in config.stations if s.name == name), None)
        if match and match.position:
            # Map operation type to legacy op_type for backward compatibility
            op_type_mapping = {
                "CTD": "station",
                "water_sampling": "station",
                "calibration": "station",
                "mooring": "mooring",
            }
            op_type = op_type_mapping.get(match.operation_type.value, "station")

            return {
                "name": match.name,
                "lat": match.position.latitude,
                "lon": match.position.longitude,
                "depth": getattr(match, "depth", 0.0),
                "op_type": op_type,
                "manual_duration": getattr(match, "duration", 0.0)
                or 0.0,  # Duration in minutes
                "action": (
                    (
                        match.action.value
                        if match.action and hasattr(match.action, "value")
                        else match.action
                    )
                    if match.action
                    else None
                ),
            }

    # Note: moorings are now included in stations list with operation_type="mooring"

    # Check transits third
    if config.transits:
        match = next((t for t in config.transits if t.name == name), None)
        if match and match.route:
            # For transits, use the last point in the route as the "position"
            first_point = match.route[
                0
            ]  # <-- Capture start point for scientific transits
            last_point = match.route[-1]

            # Calculate total route distance for proper transit duration
            total_route_distance_km = 0.0
            for i in range(len(match.route) - 1):
                start_point = match.route[i]
                end_point = match.route[i + 1]
                segment_distance = haversine_distance(start_point, end_point)
                total_route_distance_km += segment_distance

            # Convert to nautical miles and calculate duration
            route_distance_nm = km_to_nm(total_route_distance_km)
            # Use transit-specific vessel speed if provided, otherwise use default
            vessel_speed = (
                getattr(match, "vessel_speed", None) or config.default_vessel_speed
            )
            transit_time_h = route_distance_nm / vessel_speed
            transit_duration_min = hours_to_minutes(transit_time_h)

            return {
                "name": match.name,
                # XXX: Is it a problem that the default position is the last position?
                "lat": last_point.latitude,
                "lon": last_point.longitude,
                "start_lat": first_point.latitude,
                "start_lon": first_point.longitude,
                "depth": 0.0,
                "op_type": "transit",
                "manual_duration": transit_duration_min,
                "route_distance_nm": route_distance_nm,  # Store for debugging
                "vessel_speed_kt": vessel_speed,  # Include transit-specific vessel speed
                "operation_type": getattr(match, "operation_type", None),
                "action": (
                    getattr(match, "action", None).value
                    if getattr(match, "action", None)
                    and hasattr(getattr(match, "action", None), "value")
                    else getattr(match, "action", None)
                ),
                "leg_name": None,  # Will be set by calling code
            }

    return None


def generate_timeline(config: CruiseConfig) -> List[ActivityRecord]:
    """
    Generates a flattened, time-ordered list of all cruise activities.

    Dummy Scheduler Logic (Phase 3a):
    1. Order is strictly sequential based on YAML leg/sequence order.
    2. Start time is calculated cumulatively: End Time (N) = Start Time (N) + Duration (N).
    3. Start Time (N+1) = End Time (N) + Transit Time (N -> N+1).
    """
    timeline: List[ActivityRecord] = []

    # 1. Initialize start time and duration calculator
    try:
        # Handle different start_date formats
        if "T" in config.start_date:
            # ISO format with time included (e.g., "2028-06-01T08:00:00Z")
            # Remove timezone suffix and parse
            start_date_clean = config.start_date.replace("Z", "").replace("+00:00", "")
            current_time = datetime.fromisoformat(start_date_clean)
        else:
            # Separate date and time (e.g., start_date="2028-06-01", start_time="08:00")
            current_time = datetime.strptime(
                f"{config.start_date} {config.start_time}", "%Y-%m-%d %H:%M"
            )
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid start_date or start_time format in config: {e}")
        return []

    duration_calc = DurationCalculator(config)
    last_position: Optional[GeoPoint] = None

    # --- Step 2: Transit to Working Area ---
    first_station_details = _resolve_station_details(config, config.first_station)
    if first_station_details:
        start_pos = config.departure_port.position
        end_pos = GeoPoint(
            latitude=first_station_details["lat"],
            longitude=first_station_details["lon"],
        )

        distance_km = haversine_distance(start_pos, end_pos)
        distance_nm = km_to_nm(distance_km)
        transit_time_h = distance_nm / config.default_vessel_speed
        transit_time_min = hours_to_minutes(transit_time_h)

        timeline.append(
            ActivityRecord(
                {
                    "activity": "Transit",
                    "label": f"Transit to working area: {config.departure_port.name} to {config.first_station}",
                    "lat": end_pos.latitude,
                    "lon": end_pos.longitude,
                    "depth": 0.0,
                    "start_time": current_time,
                    "end_time": current_time + timedelta(minutes=transit_time_min),
                    "duration_minutes": transit_time_min,
                    "transit_dist_nm": distance_nm,  # Inter-operation distance
                    "operation_dist_nm": 0.0,  # No operation distance for pure navigation
                    "vessel_speed_kt": config.default_vessel_speed,
                    "leg_name": "Transit_to_working_area",
                    "operation_type": "Transit",
                    # Added for completeness, though unused for pure navigation
                    "action": None,
                    "start_lat": start_pos.latitude,
                    "start_lon": start_pos.longitude,
                }
            )
        )
        current_time += timedelta(minutes=transit_time_min)
        last_position = end_pos

    # --- Step 3: Iterate through Legs and Activities (Sequential Science) ---
    all_activities: List[Dict[str, Any]] = []
    for leg in config.legs:
        # Check for sequence field first, then fall back to stations
        if leg.sequence:
            activity_names = leg.sequence
        else:
            activity_names = leg.stations or []

        for name in activity_names:
            details = _resolve_station_details(config, name)
            if details:
                # Add leg name to activity details
                details["leg_name"] = leg.name
                all_activities.append(details)

    # Process sequential activities (no complex Composite parsing yet)
    for i, activity in enumerate(all_activities):

        # Get the action early for use in ActivityRecord
        action = activity.get("action", None)

        # 3a. Calculate Transit time from last activity
        # For transits, calculate distance to the START of the route, not the end
        if activity["op_type"] == "transit" and "start_lat" in activity:
            target_position = GeoPoint(
                latitude=activity["start_lat"], longitude=activity["start_lon"]
            )
        else:
            target_position = GeoPoint(
                latitude=activity["lat"], longitude=activity["lon"]
            )

        transit_time_min, transit_dist_nm = _calculate_inter_operation_transit(
            last_position,
            target_position,
            config.default_vessel_speed,
        )
        # Add inter-operation transit record if distance > threshold
        if transit_dist_nm > 0.1:  # Only add if meaningful distance
            timeline.append(
                {
                    "activity": "Transit",
                    "label": f"Transit to {activity['name']}",
                    "operation_type": "Transit",
                    "action": None,  # Pure navigation
                    "lat": target_position.latitude,
                    "lon": target_position.longitude,
                    "depth": 0.0,
                    "start_time": current_time,
                    "end_time": current_time + timedelta(minutes=transit_time_min),
                    "duration_minutes": transit_time_min,
                    "transit_dist_nm": transit_dist_nm,  # Inter-operation distance
                    "operation_dist_nm": 0.0,  # No operation distance for pure navigation
                    "vessel_speed_kt": config.default_vessel_speed,
                    "leg_name": activity.get("leg_name", "Inter-operation Transit"),
                    "start_lat": last_position.latitude if last_position else None,
                    "start_lon": last_position.longitude if last_position else None,
                }
            )
            # Advance current_time after the inter-operation transit
            current_time += timedelta(minutes=transit_time_min)

        # For transit operations, we need to handle route logic differently
        if activity["op_type"] == "transit":
            # Find the original transit definition to get the route start
            transit_def = next(
                (t for t in config.transits if t.name == activity["name"]), None
            )
            if transit_def and transit_def.route:
                route_start = transit_def.route[0]
                route_end = transit_def.route[-1]

                # Calculate transit TO the route start (if not first activity)
                if i > 0 and last_position:
                    distance_km = haversine_distance(
                        last_position,
                        GeoPoint(
                            latitude=route_start.latitude,
                            longitude=route_start.longitude,
                        ),
                    )
                    transit_dist_nm = km_to_nm(distance_km)
                    transit_time_h = transit_dist_nm / config.default_vessel_speed
                    transit_time_min = hours_to_minutes(transit_time_h)
                    current_time += timedelta(minutes=transit_time_min)

                # Current position for this activity is the route END
                current_pos = GeoPoint(
                    latitude=route_end.latitude, longitude=route_end.longitude
                )
            else:
                # Fallback if route not found
                current_pos = GeoPoint(
                    latitude=activity["lat"], longitude=activity["lon"]
                )
                if i > 0 and last_position:
                    distance_km = haversine_distance(last_position, current_pos)
                    transit_dist_nm = km_to_nm(distance_km)
                    transit_time_h = transit_dist_nm / config.default_vessel_speed
                    transit_time_min = hours_to_minutes(transit_time_h)
                    current_time += timedelta(minutes=transit_time_min)
        else:
            # Regular operations (stations, moorings)
            current_pos = GeoPoint(latitude=activity["lat"], longitude=activity["lon"])

            # Note: Inter-operation transit time is now handled by explicit transit records above
            # so we don't add it to current_time here to avoid double-counting

        # 3b. Calculate Operation Duration
        if activity["manual_duration"] > 0:
            op_duration_min = activity["manual_duration"]
        elif activity["op_type"] == "station":
            op_duration_min = duration_calc.calculate_ctd_time(activity["depth"])
        else:
            op_duration_min = 60.0  # Default fallback for non-CTD/Mooring ops

        # Set operation distance: route distance for scientific transits, 0 for point operations
        if activity["op_type"] == "transit" and "route_distance_nm" in activity:
            operation_distance = activity["route_distance_nm"]
        else:
            operation_distance = 0.0  # No operation distance for point operations

        # For scientific transits, transit_dist_nm should be 0 since inter-operation transit is separate
        # For point operations, transit_dist_nm should show the distance to reach this operation
        if activity["op_type"] == "transit":
            transit_distance = (
                0.0  # Scientific transits: inter-operation distance handled separately
            )
        else:
            transit_distance = (
                transit_dist_nm  # Point operations: show distance to reach here
            )

        timeline.append(
            ActivityRecord(
                {
                    "activity": activity["op_type"].title(),
                    "label": activity["name"],
                    "lat": current_pos.latitude,  # Use current_pos which accounts for route ends
                    "lon": current_pos.longitude,
                    "depth": activity["depth"],
                    "start_time": current_time,
                    "end_time": current_time + timedelta(minutes=op_duration_min),
                    "duration_minutes": op_duration_min,
                    "transit_dist_nm": transit_distance,  # Distance to reach this operation
                    "operation_dist_nm": operation_distance,  # Distance traveled during this operation
                    "vessel_speed_kt": config.default_vessel_speed,
                    "leg_name": activity.get("leg_name", "Unknown_Leg"),
                    "operation_type": activity["op_type"],
                    # Propagate scientific/start coordinates
                    "action": action,
                    "start_lat": activity.get("start_lat", current_pos.latitude),
                    "start_lon": activity.get("start_lon", current_pos.longitude),
                }
            )
        )

        current_time += timedelta(minutes=op_duration_min)
        last_position = current_pos

    # --- Step 4: Transit from Working Area ---
    if last_position:
        end_pos = config.arrival_port.position
        distance_km = haversine_distance(last_position, end_pos)
        distance_nm = km_to_nm(distance_km)
        transit_time_h = distance_nm / config.default_vessel_speed
        transit_time_min = hours_to_minutes(transit_time_h)

        # Demobilization (transit) starts after the last station ends
        demob_start_time = current_time
        demob_end_time = current_time + timedelta(minutes=transit_time_min)

        timeline.append(
            ActivityRecord(
                {
                    "activity": "Transit",
                    "label": f"Transit from working area to {config.arrival_port.name}",
                    "lat": end_pos.latitude,
                    "lon": end_pos.longitude,
                    "depth": 0.0,
                    "start_time": demob_start_time,
                    "end_time": demob_end_time,
                    "duration_minutes": transit_time_min,
                    "transit_dist_nm": distance_nm,  # Inter-operation distance
                    "operation_dist_nm": 0.0,  # No operation distance for pure navigation
                    "vessel_speed_kt": config.default_vessel_speed,
                    "leg_name": "Transit_from_working_area",
                    "operation_type": "Transit",
                    # Added for completeness, though unused for pure navigation
                    "action": None,
                    "start_lat": last_position.latitude,
                    "start_lon": last_position.longitude,
                }
            )
        )

    return timeline


def _calculate_inter_operation_transit(last_pos, current_pos, vessel_speed_kt):
    """Calculate transit time and distance between two operations."""
    if not last_pos or not current_pos:
        return 0.0, 0.0

    # Use existing route_distance function with a 2-point route
    distance_km = route_distance([last_pos, current_pos])

    # Use existing DurationCalculator.calculate_transit_time
    # Note: You'll need to create a DurationCalculator instance or pass it in
    # For now, we can calculate directly:
    distance_nm = km_to_nm(distance_km)
    transit_time_h = distance_nm / vessel_speed_kt if vessel_speed_kt > 0 else 0.0
    transit_time_min = transit_time_h * 60

    return transit_time_min, distance_nm
