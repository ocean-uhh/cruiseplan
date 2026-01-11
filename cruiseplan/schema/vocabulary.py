"""
Field name vocabulary for YAML configuration.

Centralized vocabulary for field names to enable easy renaming across the codebase.
Note: the field needs to be added above and in the __all__ list at the bottom.
"""

# YAML field name constants - centralized for easy renaming
POINTS_FIELD = "points"
LINES_FIELD = "lines"
AREAS_FIELD = "areas"
FIRST_ACTIVITY_FIELD = "first_activity"
LAST_ACTIVITY_FIELD = "last_activity"
OP_TYPE_FIELD = "operation_type"
ACTION_FIELD = "action"
DURATION_FIELD = "duration"
OP_DEPTH_FIELD = "operation_depth"
WATER_DEPTH_FIELD = "water_depth"
START_DATE_FIELD = "start_date"
START_TIME_FIELD = "start_time"
DEFAULT_VESSEL_SPEED_FIELD = "default_vessel_speed"
DEPARTURE_PORT_FIELD = "departure_port"
ARRIVAL_PORT_FIELD = "arrival_port"
LEGS_FIELD = "legs"
CLUSTERS_FIELD = "clusters"
ACTIVITIES_FIELD = "activities"
STRATEGY_FIELD = "strategy"

# Geometry field constants
LINE_VERTEX_FIELD = "route"
AREA_VERTEX_FIELD = "corners"

# Registry name constants for schema
POINT_REGISTRY = "point_registry"
LINE_REGISTRY = "line_registry"
AREA_REGISTRY = "area_registry"

# Export all constants for star import
__all__ = [
    # YAML field name constants
    "POINTS_FIELD",
    "LINES_FIELD",
    "AREAS_FIELD",
    "FIRST_ACTIVITY_FIELD",
    "LAST_ACTIVITY_FIELD",
    "OP_TYPE_FIELD",
    "ACTION_FIELD",
    "DURATION_FIELD",
    "OP_DEPTH_FIELD",
    "WATER_DEPTH_FIELD",
    "START_DATE_FIELD",
    "START_TIME_FIELD",
    "DEFAULT_VESSEL_SPEED_FIELD",
    "DEPARTURE_PORT_FIELD",
    "ARRIVAL_PORT_FIELD",
    "LEGS_FIELD",
    "CLUSTERS_FIELD",
    "ACTIVITIES_FIELD",
    "STRATEGY_FIELD",
    # Geometry field constants
    "LINE_VERTEX_FIELD",
    "AREA_VERTEX_FIELD",
    # Registry name constants
    "POINT_REGISTRY",
    "LINE_REGISTRY",
    "AREA_REGISTRY",
]
