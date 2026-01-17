"""
YAML field values and enumeration types for cruise configuration.

This module defines valid values that can appear in YAML configuration fields
(right-hand side of YAML), along with their defaults. This complements
cruiseplan.schema.fields which defines field names (left-hand side of YAML).

Contains:
- Default value constants for YAML fields
- Placeholder values for user guidance
- Enumeration classes for valid field values
"""

from datetime import datetime, timezone
from enum import Enum

# =============================================================================
# Default Values for YAML Fields
# =============================================================================

# --- Default Cruise Parameters ---
# These are used as code-level fallbacks if a configuration parameter is
# required before the CruiseConfig object is fully initialized

# Default vessel transit speed in knots (kt)
DEFAULT_VESSEL_SPEED_KT = 10.0

# Default profile turnaround time in minutes (minutes)
DEFAULT_TURNAROUND_TIME_MIN = 30.0

# Default CTD descent/ascent rate in meters per second (m/s)
DEFAULT_CTD_RATE_M_S = 1.0

# Default distance between stations in kilometers (km)
DEFAULT_STATION_SPACING_KM = 15.0

# Default mooring operation duration in minutes (999 hours = 59940 minutes)
# Used as a highly visible placeholder for mooring operations without specified duration
DEFAULT_MOORING_DURATION_MIN = 59940.0

# Default start date/time
DEFAULT_START_DATE_NUM = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
DEFAULT_START_DATE = DEFAULT_START_DATE_NUM.isoformat()

# Default hours for daylight operations window
DEFAULT_DAY_START_HR = 8
DEFAULT_DAY_END_HR = 20

# Default leg name for minimal cruise configurations
DEFAULT_LEG_NAME = "CRUISE"

# Default strategy
DEFAULT_STRATEGY = "sequential"

# Sentinel value indicating that depth data is missing, the station is outside
# the bathymetry grid boundaries, or a calculation failed.
# This value is defined in the specs as the default depth if ETOPO data is not found.
DEFAULT_DEPTH = -9999.0

# =============================================================================
# Placeholder Values for User Guidance
# =============================================================================

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
DEFAULT_LINE_OPTYPE = "UPDATE-underway-etc"
DEFAULT_AREA_OPTYPE = "UPDATE-survey-etc"

# Default first_waypoint
DEFAULT_FIRST_ACTIVITY = "UPDATE-first-station-name"
DEFAULT_LAST_ACTIVITY = "UPDATE-last-station-name"


# =============================================================================
# Enumeration Types for Valid Field Values
# =============================================================================


class StrategyEnum(str, Enum):
    """
    Enumeration of scheduling strategies for cruise operations.

    Defines how operations within a cluster or composite should be executed.
    """

    SEQUENTIAL = "sequential"
    SPATIAL_INTERLEAVED = "spatial_interleaved"
    DAY_NIGHT_SPLIT = "day_night_split"


class OperationTypeEnum(str, Enum):
    """
    Enumeration of point operation types.

    Defines the type of scientific operation to be performed at a station.
    """

    # Existing scientific operations
    CTD = "CTD"
    WATER_SAMPLING = "water_sampling"
    MOORING = "mooring"
    CALIBRATION = "calibration"

    # v0.3.1 Unified operations - ports and waypoints become point operations
    PORT = "port"  # Departure/arrival ports
    WAYPOINT = "waypoint"  # Navigation waypoints

    # Default placeholder for interactive operations
    DEFAULT = DEFAULT_POINT_OPTYPE


class ActionEnum(str, Enum):
    """
    Enumeration of specific actions for operations.

    Defines the specific scientific action to be taken for each operation type.
    """

    # Point operation actions
    PROFILE = "profile"
    SAMPLING = "sampling"
    DEPLOYMENT = "deployment"
    RECOVERY = "recovery"
    CALIBRATION = "calibration"

    # v0.3.1 Port operation actions
    MOB = "mob"  # Port departure (mobilization)
    DEMOB = "demob"  # Port arrival (demobilization)

    # Line operation actions
    ADCP = "ADCP"
    BATHYMETRY = "bathymetry"
    THERMOSALINOGRAPH = "thermosalinograph"
    TOW_YO = "tow_yo"
    SEISMIC = "seismic"
    MICROSTRUCTURE = "microstructure"
    SECTION = "section"  # For CTD sections that can be expanded

    # Default placeholder for interactive operations
    DEFAULT_POINT = DEFAULT_POINT_ACTION
    DEFAULT_LINE = DEFAULT_LINE_ACTION
    DEFAULT_AREA = DEFAULT_AREA_ACTION


class LineOperationTypeEnum(str, Enum):
    """
    Enumeration of line operation types.

    Defines the type of operation performed along a route or transect.
    """

    UNDERWAY = "underway"
    TOWING = "towing"
    CTD = "CTD"  # Support for CTD sections that can be expanded

    # Default placeholder for interactive operations
    DEFAULT = DEFAULT_LINE_OPTYPE


class AreaOperationTypeEnum(str, Enum):
    """
    Enumeration of area operation types.

    Defines operations that cover defined geographic areas.
    """

    SURVEY = "survey"

    # Default placeholder for interactive operations
    DEFAULT = DEFAULT_AREA_OPTYPE


# =============================================================================
# Export all constants and enums
# =============================================================================

__all__ = [
    # Enumeration classes
    "StrategyEnum",
    "OperationTypeEnum",
    "ActionEnum",
    "LineOperationTypeEnum",
    "AreaOperationTypeEnum",
    # Default cruise parameters
    "DEFAULT_VESSEL_SPEED_KT",
    "DEFAULT_TURNAROUND_TIME_MIN",
    "DEFAULT_CTD_RATE_M_S",
    "DEFAULT_STATION_SPACING_KM",
    "DEFAULT_MOORING_DURATION_MIN",
    "DEFAULT_START_DATE",
    "DEFAULT_START_DATE_NUM",
    "DEFAULT_DAY_START_HR",
    "DEFAULT_DAY_END_HR",
    "DEFAULT_LEG_NAME",
    "DEFAULT_STRATEGY",
    # Placeholder values
    "DEFAULT_DEPARTURE_PORT",
    "DEFAULT_ARRIVAL_PORT",
    "DEFAULT_UPDATE_PREFIX",
    "DEFAULT_POINT_ACTION",
    "DEFAULT_LINE_ACTION",
    "DEFAULT_AREA_ACTION",
    "DEFAULT_POINT_OPTYPE",
    "DEFAULT_LINE_OPTYPE",
    "DEFAULT_AREA_OPTYPE",
    "DEFAULT_FIRST_ACTIVITY",
    "DEFAULT_LAST_ACTIVITY",
]
