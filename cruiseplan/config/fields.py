"""
YAML field name constants for cruise configuration schema.

Centralized field name constants to enable easy renaming across the codebase.
This module focuses on the structural field names (left-hand side of YAML),
while cruiseplan.config.values focuses on field values (right-hand side of YAML).

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
DURATION_FIELD = "duration_minutes"
OP_DEPTH_FIELD = "operation_depth_m"
WATER_DEPTH_FIELD = "water_depth_m"
START_DATE_FIELD = "start_date"
START_TIME_FIELD = "start_time"
CRUISE_NAME_FIELD = "cruise_name"
PRINCIPAL_INVESTIGATOR_FIELD = "principal_investigator"
INSTITUTION_FIELD = "institution"
VESSEL_FIELD = "vessel"
DEFAULT_VESSEL_SPEED_FIELD = "default_vessel_speed_kt"
DEFAULT_STATION_SPACING_FIELD = "default_distance_between_stations_km"
CTD_DESCENT_RATE_FIELD = "ctd_descent_rate_m_s"
CTD_ASCENT_RATE_FIELD = "ctd_ascent_rate_m_s"
DAY_START_HOUR_FIELD = "day_start_hour"
DAY_END_HOUR_FIELD = "day_end_hour"
TURNAROUND_TIME_FIELD = "turnaround_time_minutes"
DEPARTURE_PORT_FIELD = "departure_port"
ARRIVAL_PORT_FIELD = "arrival_port"
REVERSIBLE_FIELD = "reversible"
DELAY_START_FIELD = "delay_start_minutes"
BUFFER_TIME_FIELD = "buffer_time_minutes"
HISTORY_FIELD = "history"
LEGS_FIELD = "legs"
PORTS_FIELD = "ports"
CLUSTERS_FIELD = "clusters"
ACTIVITIES_FIELD = "activities"
STRATEGY_FIELD = "strategy"
STATION_SPACING_FIELD = "distance_between_stations_km"
COMMENT_FIELD = "comment"
DESCRIPTION_FIELD = "description"
VESSEL_SPEED_FIELD = "vessel_speed_kt"
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
    ("timezone", "timezone"),
    ("equipment", "equipment"),
    # Port and routing fields
    (DEPARTURE_PORT_FIELD, "departure_port"),
    (ARRIVAL_PORT_FIELD, "arrival_port"),
    (FIRST_ACTIVITY_FIELD, "first_activity"),
    (LAST_ACTIVITY_FIELD, "last_activity"),
    # Operation fields
    (OP_TYPE_FIELD, "operation_type"),
    (ACTION_FIELD, "action"),
    # Depth and measurement fields
    (OP_DEPTH_FIELD, "operation_depth_m"),
    (MAX_DEPTH_FIELD, "max_depth"),
    (WATER_DEPTH_FIELD, "water_depth_m"),
    ("bathymetry_source", "bathymetry_source"),
    # Timing and spacing fields
    (DURATION_FIELD, "duration_minutes"),
    ("transit_minutes", "transit_minutes"),
    (VESSEL_SPEED_FIELD, "vessel_speed_kt"),
    (STATION_SPACING_FIELD, "distance_between_stations_km"),
    (REVERSIBLE_FIELD, "reversible"),
    (TURNAROUND_TIME_FIELD, "turnaround_time_minutes"),
    # Timing fields
    (DELAY_START_FIELD, "delay_start_minutes"),
    (BUFFER_TIME_FIELD, "buffer_time_minutes"),
    # Geographic fields
    (LATITUDE_FIELD, "latitude"),
    (LONGITUDE_FIELD, "longitude"),
    ("latitude_decmin", "latitude_decmin"),
    ("longitude_decmin", "longitude_decmin"),
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
    "timezone",
    "equipment",
    "operation_type",
    "action",
    "latitude",
    "longitude",
    "latitude_decmin",
    "longitude_decmin",
    "water_depth_m",
    "bathymetry_source",
    "operation_depth_m",
    "duration_minutes",
    "delay_start_minutes",
    "history",
    "transit_minutes",
}

LINE_ALLOWED_FIELDS = {
    "name",
    "comment",
    "description",
    "operation_type",
    "action",
    "distance_between_stations_km",
    "max_depth",
    "vessel_speed_kt",
    "duration_minutes",
    "route",
    "reversible",
    "history",
    "delay_start_minutes",
    "transit_minutes",
}

AREA_ALLOWED_FIELDS = {
    "name",
    "comment",
    "description",
    "operation_type",
    "action",
    "duration_minutes",
    "corners",
    "history",
    "delay_start_minutes",
    "transit_minutes",
}

CLUSTER_ALLOWED_FIELDS = {
    "name",
    "comment",
    "description",
    "strategy",
    "ordered",
    "activities",
    "history",
    "buffer_time_minutes",
}

LEG_ALLOWED_FIELDS = {
    "name",
    "description",
    "comment",
    "departure_port",
    "arrival_port",
    "first_activity",
    "last_activity",
    "vessel_speed_kt",
    "activities",
    "clusters",
    "buffer_time_minutes",
    "delay_start_minutes",
    "distance_between_stations_km",
    "turnaround_time_minutes",
    "strategy",
    "ordered",
    "history",
}

# Export all constants for star import
__all__ = [
    "ACTION_FIELD",
    "ACTIVITIES_FIELD",
    "AREAS_FIELD",
    "AREA_ALLOWED_FIELDS",
    "AREA_REGISTRY",
    "AREA_VERTEX_FIELD",
    "ARRIVAL_PORT_FIELD",
    "BUFFER_TIME_FIELD",
    "CLUSTERS_FIELD",
    "CLUSTER_ALLOWED_FIELDS",
    "COMMENT_FIELD",
    "CRUISE_NAME_FIELD",
    "DEFAULT_VESSEL_SPEED_FIELD",
    "DELAY_START_FIELD",
    "DEPARTURE_PORT_FIELD",
    "DESCRIPTION_FIELD",
    "DURATION_FIELD",
    "FIRST_ACTIVITY_FIELD",
    "HISTORY_FIELD",
    "INSTITUTION_FIELD",
    "LAST_ACTIVITY_FIELD",
    "LATITUDE_FIELD",
    "LEGS_FIELD",
    "LEG_ALLOWED_FIELDS",
    "LINES_FIELD",
    "LINE_ALLOWED_FIELDS",
    "LINE_REGISTRY",
    "LINE_VERTEX_FIELD",
    "LONGITUDE_FIELD",
    "MAX_DEPTH_FIELD",
    "OP_DEPTH_FIELD",
    "OP_TYPE_FIELD",
    "POINTS_FIELD",
    "POINT_ALLOWED_FIELDS",
    "POINT_REGISTRY",
    "PRINCIPAL_INVESTIGATOR_FIELD",
    "REVERSIBLE_FIELD",
    "START_DATE_FIELD",
    "START_TIME_FIELD",
    "STATION_SPACING_FIELD",
    "STRATEGY_FIELD",
    "VESSEL_FIELD",
    "VESSEL_SPEED_FIELD",
    "WATER_DEPTH_FIELD",
    "YAML_FIELD_ORDER",
]
