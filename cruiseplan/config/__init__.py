"""
Configuration and validation module for cruise planning.

This module provides configuration schemas and validation for cruise planning YAML files.
Import classes directly from submodules for explicit dependencies:

Examples
--------
    from cruiseplan.config.activities import PointDefinition, AreaDefinition, LineDefinition
    from cruiseplan.config.cruise_config import CruiseConfig, LegDefinition, ClusterDefinition
    from cruiseplan.config.exceptions import ValidationError, BathymetryError, FileError
    from cruiseplan.config.fields import POINTS_FIELD, LEGS_FIELD, ACTION_FIELD
    from cruiseplan.config.values import OperationTypeEnum, ActionEnum, StrategyEnum
    from cruiseplan.config.ports import resolve_port_reference, get_available_ports
"""

# No re-exports - use direct submodule imports for clarity and maintainability
# This eliminates Sphinx cross-reference warnings and follows modern Python patterns
