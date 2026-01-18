## Project Architecture

### Directory Structure
```
cruiseplan/
├── cli/              # Command-line interface modules
│   ├── main.py       # Entry point and argument parsing
│   ├── download.py   # Bathymetry download command
│   ├── stations.py   # Interactive station picker
│   ├── enrich.py     # Configuration enrichment
│   ├── validate.py   # Configuration validation
│   ├── schedule.py   # Schedule generation
│   ├── pandoi.py     # PANGAEA dataset search command
│   ├── pangaea.py    # PANGAEA data integration command
│   └── utils.py      # CLI utility functions
├── core/             # Core cruise planning logic
│   ├── cruise.py     # Main Cruise class
│   ├── leg.py        # Leg class
│   ├── operations.py # Operations class: Point, Line, Area
│   └── validation.py # Pydantic data models
├── calculators/      # Mathematical computations
│   ├── distance.py   # Geographic distance calculations
│   ├── duration.py   # Operation timing calculations
│   ├── routing.py    # Optimization of route
│   └── scheduler.py  # Timeline generation
├── data/             # External data integration
│   ├── bathymetry.py # Bathymetric data management
│   ├── pangaea.py    # PANGAEA database integration
│   └── cache/        # Data caching utilities and storage
├── interactive/      # Interactive user interfaces
│   ├── station_picker.py # Main interactive planning tool
│   ├── widgets.py    # UI components and controls
│   ├── campaign_selector.py # PANGAEA campaign selection interface
│   └── colormaps.py  # Color mapping utilities for visualizations
├── output/           # Multi-format output generation
│   ├── html_generator.py  # HTML report generation
│   ├── latex_generator.py # LaTeX document generation
│   ├── csv_generator.py   # CSV data export
│   ├── kml_generator.py   # KML/Google Earth export
│   ├── netcdf_generator.py # Scientific NetCDF output
│   ├── map_generator.py   # Static and interactive maps
│   ├── templates/     # Output format templates
│   └── netcdf_metadata.py # NetCDF metadata management
└── utils/            # Shared utilities
    ├── coordinates.py # Coordinate system utilities
    ├── config.py     # Configuration management
    ├── yaml_io.py    # YAML processing with comments
    ├── activity_utils.py # Activity and operation utilities
    └── constants.py  # Project-wide constants and defaults
```

### Key Design Principles
1. **Separation of Concerns**: Clear boundaries between UI, business logic, and data
2. **Modular Architecture**: Independent components that can be used separately
3. **Scientific Rigor**: Traceable calculations with proper error propagation
4. **User-Centric Design**: Workflows optimized for oceanographic use cases
5. **Extensibility**: Plugin architecture for custom functionality