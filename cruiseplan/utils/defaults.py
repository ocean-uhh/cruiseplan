"""
Constants and default values for cruise planning.

This module defines default parameters, conversion factors, and sentinel values
used throughout the cruiseplan system. These constants provide fallback values
for configuration parameters and standard conversion utilities.

Notes
-----
All constants are defined at the module level for easy importing and use.
Default values and sentinel constants for cruise planning operations.
"""

from datetime import datetime, timezone

# --- Depth/Bathymetry Constants ---

# Sentinel value indicating that depth data is missing, the station is outside
# the bathymetry grid boundaries, or a calculation failed.
# This value is defined in the specs as the default depth if ETOPO data is not found.
DEFAULT_DEPTH = -9999.0

# --- Default Cruise Parameters ---
# These are used as code-level fallbacks if a configuration parameter is
# required before the CruiseConfig object is fully initialized or if a
# required field is missing (though the YAML schema should prevent the latter).

# Default vessel transit speed in knots (kt)
DEFAULT_VESSEL_SPEED_KT = 10.0

# Default profile turnaround time in minutes (minutes)
# Corresponds to CruiseConfig.turnaround_time default.
DEFAULT_TURNAROUND_TIME_MIN = 30.0

# Default CTD descent/ascent rate in meters per second (m/s)
# Corresponds to CruiseConfig.ctd_descent_rate/ascent_rate default.
DEFAULT_CTD_RATE_M_S = 1.0

# Default distance between stations in kilometers (km)
# Corresponds to CruiseConfig.default_distance_between_stations default.
DEFAULT_STATION_SPACING_KM = 15.0

# Default calculation flags - typically True for automated processing
# Whether to calculate transit times between section waypoints
DEFAULT_CALC_TRANSFER = True

# Whether to automatically look up depth values from bathymetry data
DEFAULT_CALC_DEPTH = True

# Default mooring operation duration in minutes (999 hours = 59940 minutes)
# Used as a highly visible placeholder for mooring operations without specified duration
DEFAULT_MOORING_DURATION_MIN = 59940.0

DEFAULT_START_DATE_NUM = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
# Make this an ISO8601 string
DEFAULT_START_DATE = DEFAULT_START_DATE_NUM.isoformat()

# --- Placeholder Values ---
# Port placeholder names used to indicate fields that need user updates
DEFAULT_DEPARTURE_PORT = "port_update_departure"
DEFAULT_ARRIVAL_PORT = "port_update_arrival"

# Legacy placeholder prefix for backwards compatibility
DEFAULT_UPDATE_PREFIX = "UPDATE-"

# Default action values for interactive operations that need user review
DEFAULT_POINT_ACTION = "UPDATE-profile-sampling-etc"
DEFAULT_LINE_ACTION = "UPDATE-ADCP-bathymetry-etc"
DEFAULT_AREA_ACTION = "UPDATE-bathymetry-survey-etc"

# Default operation type values for interactive operations
DEFAULT_POINT_OPTYPE = "UPDATE-CTD-mooring-etc"
DEFAULT_LINE_OPTYPE = "underway"
DEFAULT_AREA_OPTYPE = "survey"

# Default first_waypoint
DEFAULT_FIRST_ACTIVITY = "UPDATE-first-station-name"
DEFAULT_LAST_ACTIVITY = "UPDATE-last-station-name"

DEFAULT_STRATEGY = "sequential"
