"""
Validation module for cruiseplan configuration.

Provides Pydantic models and validation functions for cruise configuration
files, split into logical modules for better maintainability.

This module re-exports the main classes to maintain backward compatibility
with existing imports.
"""

# Core exceptions and enums
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
from .exceptions import BathymetryError, FileError, ValidationError
from .fields import (
    ACTION_FIELD,
    ACTIVITIES_FIELD,
    AREA_REGISTRY,
    AREAS_FIELD,
    ARRIVAL_PORT_FIELD,
    CLUSTERS_FIELD,
    DEFAULT_VESSEL_SPEED_FIELD,
    DEPARTURE_PORT_FIELD,
    DURATION_FIELD,
    FIRST_ACTIVITY_FIELD,
    LAST_ACTIVITY_FIELD,
    LEGS_FIELD,
    LINE_REGISTRY,
    LINES_FIELD,
    OP_DEPTH_FIELD,
    OP_TYPE_FIELD,
    POINT_REGISTRY,
    POINTS_FIELD,
    START_DATE_FIELD,
    START_TIME_FIELD,
    WATER_DEPTH_FIELD,
)
from .values import (
    ActionEnum,
    AreaOperationTypeEnum,
    LineOperationTypeEnum,
    OperationTypeEnum,  # TODO Why is this not a PointOperationTypeEnum?
    StrategyEnum,
)

__all__ = [
    "ACTION_FIELD",
    "ACTIVITIES_FIELD",
    "AREAS_FIELD",
    "AREA_REGISTRY",
    "ARRIVAL_PORT_FIELD",
    "CLUSTERS_FIELD",
    "DEFAULT_VESSEL_SPEED_FIELD",
    "DEPARTURE_PORT_FIELD",
    "DURATION_FIELD",
    "FIRST_ACTIVITY_FIELD",
    "LAST_ACTIVITY_FIELD",
    "LEGS_FIELD",
    "LINES_FIELD",
    "LINE_REGISTRY",
    "OP_DEPTH_FIELD",
    "OP_TYPE_FIELD",
    "POINTS_FIELD",
    "POINT_REGISTRY",
    "START_DATE_FIELD",
    "START_TIME_FIELD",
    "WATER_DEPTH_FIELD",
    "ActionEnum",
    "AreaDefinition",
    "AreaOperationTypeEnum",
    "BathymetryError",
    "ClusterDefinition",
    "CruiseConfig",
    "FileError",
    "FlexibleLocationModel",
    "GeoPoint",
    "LegDefinition",
    "LineDefinition",
    "LineOperationTypeEnum",
    "OperationTypeEnum",
    "PointDefinition",
    "StrategyEnum",
    "ValidationError",
]
