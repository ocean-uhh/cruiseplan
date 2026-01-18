"""
CruisePlan: Oceanographic Research Cruise Planning System.

This package provides tools for planning oceanographic research cruises,
including bathymetry data management, station planning, and schedule generation.

Notebook-Friendly API
=====================

For interactive use in Jupyter notebooks, use these simplified functions
that mirror the CLI commands:

    import cruiseplan

    # Download bathymetry data (mirrors: cruiseplan bathymetry)
    bathy_file = cruiseplan.bathymetry(bathy_source="etopo2022", output_dir="data/bathymetry")

    # Search PANGAEA database (mirrors: cruiseplan pangaea)
    stations, files = cruiseplan.pangaea("CTD", lat_bounds=[70, 80], lon_bounds=[-10, 10])

    # Process configuration workflow (mirrors: cruiseplan process)
    config, files = cruiseplan.process(config_file="cruise.yaml", add_depths=True, add_coords=True)

    # Validate configuration (mirrors: cruiseplan validate)
    is_valid = cruiseplan.validate(config_file="cruise.yaml")

    # Interactive station placement (mirrors: cruiseplan stations)
    result = cruiseplan.stations(lat_bounds=[70, 80], lon_bounds=[-10, 10], pangaea_file="campaign.pkl")

    # Generate schedule (mirrors: cruiseplan schedule)
    timeline, files = cruiseplan.schedule(config_file="cruise.yaml", format="html")

Architecture Overview
====================

CruisePlan follows a modular architecture with three main components:

- **cruiseplan.config**: Configuration schemas and validation (CruiseConfig, activities, ports)
- **cruiseplan.runtime**: Business logic and data processing (CruiseInstance, enrichment, validation)
- **cruiseplan.timeline**: Scheduling algorithms and timeline generation

For more advanced usage, import the underlying classes directly:

    from cruiseplan.data.bathymetry import download_bathymetry
    from cruiseplan.runtime.cruise import CruiseInstance
    from cruiseplan.timeline.scheduler import generate_timeline
"""

import logging

from cruiseplan.api import (
    bathymetry,
    enrich,
    map,
    pangaea,
    process,
    schedule,
    stations,
    validate,
)
from cruiseplan.api.types import (
    BathymetryResult,
    EnrichResult,
    MapResult,
    PangaeaResult,
    ProcessResult,
    ScheduleResult,
    StationPickerResult,
    ValidationResult,
)
from cruiseplan.config.exceptions import BathymetryError, FileError, ValidationError
from cruiseplan.data.bathymetry import download_bathymetry
from cruiseplan.timeline import CruiseSchedule

logger = logging.getLogger(__name__)

# Export the core classes for advanced users
__all__ = [
    "BathymetryError",
    "BathymetryResult",
    "CruiseSchedule",
    "EnrichResult",
    "FileError",
    "MapResult",
    "PangaeaResult",
    "ProcessResult",
    "ScheduleResult",
    "StationPickerResult",
    "ValidationError",
    "ValidationResult",
    "bathymetry",
    "download_bathymetry",
    "enrich",
    "map",
    "pangaea",
    "process",
    "schedule",
    "stations",
    "validate",
]
