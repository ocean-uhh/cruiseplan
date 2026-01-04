"""
Validation module for cruiseplan configuration.

Provides Pydantic models and validation functions for cruise configuration
files, split into logical modules for better maintainability.

This module re-exports the main classes to maintain backward compatibility
with existing imports.
"""

# Core exceptions and enums
# Basic data models
from .base_models import FlexibleLocationModel, GeoPoint

# Catalog definitions (with new terminology)
from .catalog_definitions import (
    AreaDefinition,
    # Legacy aliases for backward compatibility
    PortDefinition,
    StationDefinition,
    TransectDefinition,
    TransitDefinition,
    WaypointDefinition,
)
from .enums import (
    ActionEnum,
    AreaOperationTypeEnum,
    LineOperationTypeEnum,
    OperationTypeEnum,
    StrategyEnum,
)
from .exceptions import CruiseConfigurationError

__all__ = [
    # Exceptions
    "CruiseConfigurationError",
    # Enums
    "ActionEnum",
    "AreaOperationTypeEnum",
    "LineOperationTypeEnum",
    "OperationTypeEnum",
    "StrategyEnum",
    # Models
    "FlexibleLocationModel",
    "GeoPoint",
    # Catalog Definitions (new terminology)
    "AreaDefinition",
    "TransectDefinition",
    "WaypointDefinition",
    # Legacy aliases (backward compatibility)
    "PortDefinition",
    "StationDefinition",
    "TransitDefinition",
]
