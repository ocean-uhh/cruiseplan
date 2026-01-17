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

For more advanced usage, import the underlying classes directly:

    from cruiseplan.data.bathymetry import download_bathymetry
    from cruiseplan.core.cruise import CruiseInstance
    from cruiseplan.calculators.scheduler import generate_timeline
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
from cruiseplan.calculators import CruiseSchedule
from cruiseplan.data.bathymetry import download_bathymetry
from cruiseplan.exceptions import BathymetryError, FileError, ValidationError
from cruiseplan.types import (
    BathymetryResult,
    EnrichResult,
    MapResult,
    PangaeaResult,
    ProcessResult,
    ScheduleResult,
    StationPickerResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# Export the core classes for advanced users
__all__ = [
    "bathymetry",
    "enrich",
    "map",
    "pangaea",
    "process",
    "schedule",
    "stations",
    "validate",
    # Exception classes
    "ValidationError",
    "FileError",
    "BathymetryError",
    # Result classes
    "EnrichResult",
    "ValidationResult",
    "ScheduleResult",
    "PangaeaResult",
    "ProcessResult",
    "MapResult",
    "BathymetryResult",
    "StationPickerResult",
    # Legacy compatibility
    "CruiseSchedule",
    # Advanced usage functions
    "download_bathymetry",
]
