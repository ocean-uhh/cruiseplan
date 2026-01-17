"""
Validation module for cruiseplan configuration.

Provides Pydantic models and validation functions for cruise configuration
files, split into logical modules for better maintainability.

This module re-exports the main classes to maintain backward compatibility
with existing imports.
"""

# Core exceptions and enums
# Basic data models

# Field name constants for yaml - centralized for easy renaming
# Activity definitions (new terminology)
from .activities import (
    AreaDefinition,
    FlexibleLocationModel,
    GeoPoint,
    LineDefinition,
    PointDefinition,
)

# Main cruise configuration
# Schedule definitions (YAML layer)
from .cruise_config import ClusterDefinition, CruiseConfig, LegDefinition
from .fields import *
from .values import (
    ActionEnum,
    AreaOperationTypeEnum,
    LineOperationTypeEnum,
    OperationTypeEnum,  # TODO Why is this not a PointOperationTypeEnum?
    StrategyEnum,
)

__all__ = [
    # Field name constants
    "POINTS_FIELD",
    "LINES_FIELD",
    "AREAS_FIELD",
    "FIRST_ACTIVITY_FIELD",
    "LAST_ACTIVITY_FIELD",
    "OP_TYPE_FIELD",
    "ACTION_FIELD",
    "ACTIVITIES_FIELD",
    "ARRIVAL_PORT_FIELD",
    "CLUSTERS_FIELD",
    "DEPARTURE_PORT_FIELD",
    "DURATION_FIELD",
    "LEGS_FIELD",
    "OP_DEPTH_FIELD",
    "START_DATE_FIELD",
    "START_TIME_FIELD",
    "DEFAULT_VESSEL_SPEED_FIELD",
    "WATER_DEPTH_FIELD",
    "POINT_REGISTRY",
    "LINE_REGISTRY",
    "AREA_REGISTRY",
    # Enums
    "ActionEnum",
    "AreaOperationTypeEnum",
    "LineOperationTypeEnum",
    "OperationTypeEnum",
    "StrategyEnum",
    # Models
    "FlexibleLocationModel",
    "GeoPoint",
    # Activity Definitions (new terminology)
    "AreaDefinition",
    "LineDefinition",
    "PointDefinition",
    # Schedule Definitions (YAML layer)
    "ClusterDefinition",
    "LegDefinition",
    # Main Configuration
    "CruiseConfig",
]
