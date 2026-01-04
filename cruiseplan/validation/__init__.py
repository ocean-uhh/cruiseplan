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
    TransectDefinition,
    WaypointDefinition,
    # Legacy aliases for backward compatibility
    PortDefinition,
    StationDefinition,
    TransitDefinition,
)

# Schedule definitions (YAML layer)
from .schedule_definitions import ClusterDefinition, LegDefinition

# Generation utilities
from .generation_models import GenerateSection, GenerateTransect, SectionDefinition

# Main cruise configuration
from .cruise_config import CruiseConfig

# Validation utilities
from .validators import (
    show_deprecation_warning,
    validate_non_negative_number,
    validate_positive_number,
    validate_unique_names,
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
    # Schedule Definitions (YAML layer)
    "ClusterDefinition",
    "LegDefinition",
    # Generation Utilities
    "GenerateSection",
    "GenerateTransect",
    "SectionDefinition",
    # Main Configuration
    "CruiseConfig",
    # Validation Utilities
    "show_deprecation_warning",
    "validate_non_negative_number",
    "validate_positive_number",
    "validate_unique_names",
    # Legacy aliases (backward compatibility)
    "PortDefinition",
    "StationDefinition",
    "TransitDefinition",
]
