"""
Validation module for cruiseplan configuration.

Provides Pydantic models and validation functions for cruise configuration
files, split into logical modules for better maintainability.

This module re-exports the main classes to maintain backward compatibility
with existing imports.
"""

# Core exceptions and enums
# Basic data models
# Legacy validation functions (from validation_old.py)
from ..core.validation_old import (
    check_complete_duplicates,
    check_duplicate_names,
    enrich_configuration,
    expand_ctd_sections,
    validate_configuration_file,
    validate_depth_accuracy,
)
from .base_models import FlexibleLocationModel, GeoPoint

# Catalog definitions (with new terminology)
from .catalog_definitions import (
    AreaDefinition,
    # Legacy aliases for backward compatibility (TODO: Remove in v0.4.0)
    PortDefinition,  # Use WaypointDefinition instead
    StationDefinition,  # Use WaypointDefinition instead
    TransectDefinition,
    TransitDefinition,  # Use TransectDefinition instead
    WaypointDefinition,
)

# Main cruise configuration
from .cruise_config import CruiseConfig
from .enums import (
    ActionEnum,
    AreaOperationTypeEnum,
    LineOperationTypeEnum,
    OperationTypeEnum,
    StrategyEnum,
)
from .exceptions import CruiseConfigurationError

# Generation utilities
from .generation_models import GenerateSection, GenerateTransect, SectionDefinition

# Schedule definitions (YAML layer)
from .schedule_definitions import ClusterDefinition, LegDefinition

# Validation utilities
from .validators import (
    show_deprecation_warning,
    validate_non_negative_number,
    validate_positive_number,
    validate_unique_names,
)

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
    # Legacy validation functions
    "check_complete_duplicates",
    "check_duplicate_names",
    "enrich_configuration",
    "expand_ctd_sections",
    "validate_configuration_file",
    "validate_depth_accuracy",
    # Legacy aliases (backward compatibility)
    "PortDefinition",
    "StationDefinition",
    "TransitDefinition",
]
