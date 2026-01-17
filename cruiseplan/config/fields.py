"""
YAML field name constants for cruise configuration schema.

Centralized field name constants to enable easy renaming across the codebase.
This module focuses on the structural field names (left-hand side of YAML),
while cruiseplan.schema.values focuses on field values (right-hand side of YAML).

Note: New field constants need to be added above and in the __all__ list at the bottom.
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
DEFAULT_STATION_SPACING_FIELD = "default_distance_between_stations"
CTD_DESCENT_RATE_FIELD = "ctd_descent_rate"
CTD_ASCENT_RATE_FIELD = "ctd_ascent_rate"
DAY_START_HOUR_FIELD = "day_start_hour"
DAY_END_HOUR_FIELD = "day_end_hour"
TURNAROUND_TIME_FIELD = "turnaround_time"
DEPARTURE_PORT_FIELD = "departure_port"
ARRIVAL_PORT_FIELD = "arrival_port"
REVERSIBLE_FIELD = "reversible"
DELAY_START_FIELD = "delay_start"
DELAY_END_FIELD = "delay_end"
BUFFER_TIME_FIELD = "buffer_time"
HISTORY_FIELD = "history"
LEGS_FIELD = "legs"
PORTS_FIELD = "port"
CLUSTERS_FIELD = "clusters"
ACTIVITIES_FIELD = "activities"
STRATEGY_FIELD = "strategy"
STATION_SPACING_FIELD = "distance_between_stations"
COMMENT_FIELD = "comment"
DESCRIPTION_FIELD = "description"
VESSEL_SPEED_FIELD = "vessel_speed"
LATITUDE_FIELD = "latitude"
LONGITUDE_FIELD = "longitude"
MAX_DEPTH_FIELD = "max_depth"

# Geometry field constants
LINE_VERTEX_FIELD = "route"
AREA_VERTEX_FIELD = "corners"

# Registry name constants for schema
POINT_REGISTRY = "point_registry"
LINE_REGISTRY = "line_registry"
AREA_REGISTRY = "area_registry"

# Master canonical field ordering for ALL definition types
# Format: (yaml_field_name, pydantic_field_name)
YAML_FIELD_ORDER = [
    # Identity fields
    ("cruise_name", "cruise_name"),  # For top-level cruise name
    ("name", "name"),
    ("display_name", "display_name"),
    (COMMENT_FIELD, "comment"),
    (DESCRIPTION_FIELD, "description"),
    # Port and routing fields
    (DEPARTURE_PORT_FIELD, "departure_port"),
    (ARRIVAL_PORT_FIELD, "arrival_port"),
    (FIRST_ACTIVITY_FIELD, "first_activity"),
    (LAST_ACTIVITY_FIELD, "last_activity"),
    # Operation fields
    (OP_TYPE_FIELD, "operation_type"),
    (ACTION_FIELD, "action"),
    # Depth and measurement fields
    (OP_DEPTH_FIELD, "operation_depth"),
    (MAX_DEPTH_FIELD, "max_depth"),
    (WATER_DEPTH_FIELD, "water_depth"),
    # Timing and spacing fields
    (DURATION_FIELD, "duration"),
    (VESSEL_SPEED_FIELD, "vessel_speed"),
    (STATION_SPACING_FIELD, "distance_between_stations"),
    (REVERSIBLE_FIELD, "reversible"),
    (TURNAROUND_TIME_FIELD, "turnaround_time"),
    # Timing fields
    (DELAY_START_FIELD, "delay_start"),
    (DELAY_END_FIELD, "delay_end"),
    (BUFFER_TIME_FIELD, "buffer_time"),
    # Geographic fields
    (LATITUDE_FIELD, "latitude"),
    (LONGITUDE_FIELD, "longitude"),
    (LINE_VERTEX_FIELD, "route"),
    (AREA_VERTEX_FIELD, "corners"),
    ("position_string", "position_string"),
    # Organization fields
    (STRATEGY_FIELD, "strategy"),
    ("ordered", "ordered"),
    (ACTIVITIES_FIELD, "activities"),
    (CLUSTERS_FIELD, "clusters"),
    # Provenance fields
    (HISTORY_FIELD, "history"),
]

# Allowed fields for each definition type
POINT_ALLOWED_FIELDS = {
    "name",
    "display_name",
    "comment",
    "description",
    "operation_type",
    "action",
    "latitude",
    "longitude",
    "water_depth",
    "operation_depth",
    "duration",
    "delay_start",
    "delay_end",
    "history",
}

LINE_ALLOWED_FIELDS = {
    "name",
    "comment",
    "description",
    "operation_type",
    "action",
    "distance_between_stations",
    "max_depth",
    "vessel_speed",
    "duration",
    "route",
    "reversible",
    "history",
    "delay_start",
    "delay_end",
}

AREA_ALLOWED_FIELDS = {
    "name",
    "comment",
    "description",
    "operation_type",
    "action",
    "duration",
    "corners",
    "history",
    "delay_start",
    "delay_end",
}

CLUSTER_ALLOWED_FIELDS = {
    "name",
    "comment",
    "description",
    "strategy",
    "ordered",
    "activities",
    "history",
    "buffer_time",
}

LEG_ALLOWED_FIELDS = {
    "name",
    "description",
    "comment",
    "departure_port",
    "arrival_port",
    "first_activity",
    "last_activity",
    "vessel_speed",
    "activities",
    "clusters",
    "buffer_time",
    "distance_between_stations",
    "turnaround_time",
    "history",
}

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
    "STATION_SPACING_FIELD",
    "COMMENT_FIELD",
    "DESCRIPTION_FIELD",
    "VESSEL_SPEED_FIELD",
    "LATITUDE_FIELD",
    "LONGITUDE_FIELD",
    "MAX_DEPTH_FIELD",
    "REVERSIBLE_FIELD",
    "DELAY_START_FIELD",
    "DELAY_END_FIELD",
    "BUFFER_TIME_FIELD",
    "HISTORY_FIELD",
    # Geometry field constants
    "LINE_VERTEX_FIELD",
    "AREA_VERTEX_FIELD",
    # Field ordering and allowed field configurations
    "YAML_FIELD_ORDER",
    "POINT_ALLOWED_FIELDS",
    "LINE_ALLOWED_FIELDS",
    "AREA_ALLOWED_FIELDS",
    "CLUSTER_ALLOWED_FIELDS",
    "LEG_ALLOWED_FIELDS",
    # Registry name constants
    "POINT_REGISTRY",
    "LINE_REGISTRY",
    "AREA_REGISTRY",
]
