"""
Enumeration types for cruise configuration validation.

Defines all enum types used in cruise configuration models to ensure
consistent values across the system.
"""

from enum import Enum

from cruiseplan.utils.defaults import (
    DEFAULT_AREA_ACTION,
    DEFAULT_LINE_ACTION,
    DEFAULT_POINT_ACTION,
    DEFAULT_POINT_OPTYPE,
)


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

    # Placeholder for user guidance
    UPDATE_PLACEHOLDER = DEFAULT_POINT_OPTYPE


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
    # Placeholders for user guidance
    UPDATE_PROFILE_PLACEHOLDER = DEFAULT_POINT_ACTION
    UPDATE_LINE_PLACEHOLDER = DEFAULT_LINE_ACTION
    UPDATE_AREA_PLACEHOLDER = DEFAULT_AREA_ACTION


class LineOperationTypeEnum(str, Enum):
    """
    Enumeration of line operation types.

    Defines the type of operation performed along a route or transect.
    """

    UNDERWAY = "underway"
    TOWING = "towing"
    CTD = "CTD"  # Support for CTD sections that can be expanded


class AreaOperationTypeEnum(str, Enum):
    """
    Enumeration of area operation types.

    Defines operations that cover defined geographic areas.
    """

    SURVEY = "survey"
    # Placeholder for user guidance
    UPDATE_PLACEHOLDER = DEFAULT_AREA_ACTION
