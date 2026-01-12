"""
Cruise configuration processing module.

This module contains business logic for cruise configuration operations
that directly support the main cruiseplan API functions:

- enrich.py: Data enrichment (sections, coordinates, depths, ports)
- validate.py: Configuration validation and verification
- map.py: Map generation and visualization

The module structure mirrors the cruise processing workflow:
cruiseplan.process() -> enrichment -> validation -> map generation
"""

# Re-export main functions for convenience and backward compatibility
from .enrich import enrich_configuration
from .validate import validate_configuration

__all__ = [
    "enrich_configuration",
    "validate_configuration",
]
