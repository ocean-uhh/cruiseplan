"""
Configuration objects for CruisePlan API functions.

This module provides dataclass-based configuration objects to reduce
the number of arguments in main API functions, following the refactoring
plan outlined in docs/legacy/CLAUDE-v0.3.3-refactor-complex.md.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class BathymetryConfig:
    """Configuration for bathymetry-related parameters."""

    source: str = "etopo2022"
    """Bathymetry data source"""

    directory: str = "data/bathymetry"
    """Directory for bathymetry files"""

    stride: int = 10
    """Stride for bathymetry data sampling"""


@dataclass
class OutputConfig:
    """Configuration for output generation parameters."""

    directory: str = "data"
    """Output directory for generated files"""

    filename: Optional[str] = None
    """Specific output filename (if None, auto-generated)"""

    format: str = "all"
    """Output format(s): 'html', 'csv', 'netcdf', 'latex', 'kml', or 'all'"""

    verbose: bool = False
    """Enable verbose output"""


@dataclass
class ValidationConfig:
    """Configuration for validation parameters."""

    run_validation: bool = True
    """Whether to run validation checks"""

    depth_check: bool = True
    """Whether to validate depths against bathymetry"""

    tolerance: float = 10.0
    """Tolerance for depth validation (percentage)"""


@dataclass
class VisualizationConfig:
    """Configuration for map and visualization parameters."""

    figsize: Optional[list] = None
    """Figure size [width, height] in inches"""

    show_plot: bool = False
    """Whether to display plot interactively"""

    include_ports: bool = True
    """Whether to include ports on the map"""


@dataclass
class ProcessConfig:
    """Configuration for cruise processing workflow."""

    # Core processing options
    add_depths: bool = True
    """Whether to add depth information"""

    add_coords: bool = True
    """Whether to add coordinate information"""

    expand_sections: bool = True
    """Whether to expand CTD sections"""

    run_map_generation: bool = True
    """Whether to generate maps as part of processing"""

    # Nested configuration objects
    bathymetry: BathymetryConfig = None
    """Bathymetry configuration"""

    output: OutputConfig = None
    """Output configuration"""

    validation: ValidationConfig = None
    """Validation configuration"""

    visualization: VisualizationConfig = None
    """Visualization configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.bathymetry is None:
            self.bathymetry = BathymetryConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.validation is None:
            self.validation = ValidationConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()


@dataclass
class ScheduleConfig:
    """Configuration for schedule generation."""

    leg: Optional[str] = None
    """Specific leg to generate schedule for (if None, all legs)"""

    derive_netcdf: bool = False
    """Whether to derive NetCDF output"""

    # Nested configuration objects
    bathymetry: BathymetryConfig = None
    """Bathymetry configuration"""

    output: OutputConfig = None
    """Output configuration"""

    visualization: VisualizationConfig = None
    """Visualization configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.bathymetry is None:
            self.bathymetry = BathymetryConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()


@dataclass
class MapConfig:
    """Configuration for map generation."""

    # Nested configuration objects
    bathymetry: BathymetryConfig = None
    """Bathymetry configuration"""

    output: OutputConfig = None
    """Output configuration"""

    visualization: VisualizationConfig = None
    """Visualization configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.bathymetry is None:
            self.bathymetry = BathymetryConfig()
        if self.output is None:
            self.output = OutputConfig()
        if self.visualization is None:
            self.visualization = VisualizationConfig()


@dataclass
class PangaeaConfig:
    """Configuration for PANGAEA database searching."""

    # Search parameters
    lat_bounds: Optional[list[float]] = None
    """Latitude bounds [min, max] for spatial filtering"""

    lon_bounds: Optional[list[float]] = None
    """Longitude bounds [min, max] for spatial filtering"""

    limit: int = 10
    """Maximum number of results to return"""

    rate_limit: float = 1.0
    """Rate limiting delay between requests (seconds)"""

    merge_campaigns: bool = True
    """Whether to merge campaigns from the same expedition"""

    # Nested configuration objects
    output: OutputConfig = None
    """Output configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.output is None:
            self.output = OutputConfig()


@dataclass
class BathymetryDownloadConfig:
    """Configuration for bathymetry data download."""

    source: str = "etopo2022"
    """Bathymetry dataset to download ('etopo2022' or 'gebco2025')"""

    output_dir: Optional[str] = None
    """Output directory for bathymetry files (default: 'data/bathymetry')"""

    citation: bool = False
    """Show citation information for the bathymetry source"""


@dataclass
class EnrichConfig:
    """Configuration for cruise enrichment operations."""

    # Core enrichment options
    add_depths: bool = True
    """Whether to add depth information"""

    add_coords: bool = True
    """Whether to add coordinate information"""

    coord_format: str = "ddm"
    """Coordinate format ('ddm', 'dd', or 'dms')"""

    expand_sections: bool = True
    """Whether to expand CTD sections"""

    # Nested configuration objects
    bathymetry: BathymetryConfig = None
    """Bathymetry configuration"""

    output: OutputConfig = None
    """Output configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.bathymetry is None:
            self.bathymetry = BathymetryConfig()
        if self.output is None:
            self.output = OutputConfig()


@dataclass
class ValidateConfig:
    """Configuration for cruise validation operations."""

    check_depths: bool = True
    """Whether to validate depths against bathymetry"""

    tolerance: float = 10.0
    """Tolerance for depth validation (percentage)"""

    warnings_only: bool = False
    """Whether to show warnings only (no errors)"""

    verbose: bool = False
    """Enable verbose output"""

    # Nested configuration objects
    bathymetry: BathymetryConfig = None
    """Bathymetry configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.bathymetry is None:
            self.bathymetry = BathymetryConfig()


@dataclass
class StationsConfig:
    """Configuration for interactive station picker."""

    # Coordinate bounds
    lat_bounds: Optional[tuple[float, float]] = None
    """Latitude bounds (min, max) for station placement"""

    lon_bounds: Optional[tuple[float, float]] = None
    """Longitude bounds (min, max) for station placement"""

    pangaea_file: Optional[str] = None
    """Path to PANGAEA data file for context"""

    bathy_source: str = "etopo2022"
    """Bathymetry dataset for depth information"""

    bathy_dir: str = "data/bathymetry"
    """Directory containing bathymetry data"""

    initial_stations: int = 1
    """Initial number of stations to place"""

    # Nested configuration objects
    output: OutputConfig = None
    """Output configuration"""

    def __post_init__(self):
        """Initialize nested config objects with defaults if not provided."""
        if self.output is None:
            self.output = OutputConfig()
