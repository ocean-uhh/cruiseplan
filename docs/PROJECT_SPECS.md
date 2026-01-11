# CruisePlan Project Architecture & Developer Guide

*Version 2.0 - Updated for v0.3.4+ Schema Architecture*

---

## Table of Contents

1. [Overview & Vision](#overview--vision)
2. [Architecture Overview](#architecture-overview)
3. [Layer-by-Layer Deep Dive](#layer-by-layer-deep-dive)
4. [YAML Configuration Reference](#yaml-configuration-reference)
5. [Python API Reference](#python-api-reference)
6. [Developer Workflow](#developer-workflow)
7. [Testing & Quality](#testing--quality)
8. [Contributing Guidelines](#contributing-guidelines)

---

## Overview & Vision

### Purpose

CruisePlan is a comprehensive oceanographic cruise planning system designed for research scientists and marine operations. It transforms complex multi-week research cruises into manageable, schedulable operations with precise timing calculations and professional output generation.

**Target Users**: Oceanographers planning research cruises who need to:
- Plan station distributions along survey lines with optimal spacing
- Calculate operational timings for CTD profiles, mooring operations, and transfers
- Integrate past cruise locations from PANGAEA database for context
- Generate professional outputs for cruise proposals and operational planning
- Manage complex multi-area expeditions with discrete working phases

### Core Scientific Use Cases

**User Intent**: *"I need to place oceanographic stations along specific survey lines with bathymetry context"*

**Key Capabilities**:
- **Interactive Station Placement**: Graphical interface with bathymetry background
- **Scientific Accuracy**: Great-circle route calculations, validated timing models
- **Flexible Organization**: Hierarchical grouping (Cruise → Leg → Cluster → Operations)
- **Multi-Format Output**: Timeline generation, maps, CSV exports, NetCDF files
- **Data Integration**: PANGAEA historical data, ETOPO bathymetry

---

## Architecture Overview

### Design Philosophy

CruisePlan follows a **layered architecture** that cleanly separates concerns between data validation, business logic, and output generation:

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                          │
│  YAML Files  │  Interactive GUI  │  CLI Commands           │
├─────────────────────────────────────────────────────────────┤
│                     Schema Layer                           │
│  Pydantic Models for YAML Validation & Parsing             │
│  cruiseplan.schema.*                                        │
├─────────────────────────────────────────────────────────────┤
│                      Core Layer                            │
│  Business Logic & Runtime Operations                       │
│  cruiseplan.core.*                                          │
├─────────────────────────────────────────────────────────────┤
│                   Processing Layer                         │
│  Data Enrichment & Validation                              │
│  cruiseplan.processing.*                                    │
├─────────────────────────────────────────────────────────────┤
│                     Output Layer                           │
│  Multi-Format Generation (Timeline, Maps, NetCDF)          │
│  cruiseplan.output.*                                        │
├─────────────────────────────────────────────────────────────┤
│                   Utilities Layer                          │
│  Calculations, Data Access, Shared Utilities               │
│  cruiseplan.utils.*, cruiseplan.data.*, etc.               │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Schema-First Design**: Pydantic models define the "contract" for YAML structure
2. **Separation of Concerns**: YAML validation ≠ runtime business logic
3. **Scientific Accuracy**: Validated oceanographic calculations with proper units
4. **Flexible Hierarchical Grouping**: Support complex multi-leg expeditions
5. **Parameter Inheritance**: Cruise → Leg → Cluster → Operation configuration cascade

---

## Layer-by-Layer Deep Dive

### 1. Schema Layer (`cruiseplan.schema.*`)

**Purpose**: Validates and parses YAML configuration into Python data structures.

**Key Distinction**: These are **validation models**, not runtime business objects. They ensure your YAML is structured correctly and convert it to Python data that the core layer can work with.

```python
# Example: Schema layer validates YAML structure
from cruiseplan.schema.cruise import CruiseConfig
from cruiseplan.schema.activities import PointDefinition

# This validates YAML → Python conversion
cruise_config = CruiseConfig.model_validate(yaml_data)
point_def = cruise_config.points[0]  # PointDefinition object
print(point_def.latitude)  # Validated latitude from YAML
```

#### Core Schema Models

**`cruiseplan.schema.cruise.CruiseConfig`**
- Root configuration model representing the entire YAML file
- Contains cruise metadata, global catalogs, and schedule organization
- Handles parameter inheritance and validation

**`cruiseplan.schema.activities.*`**
- `PointDefinition`: Individual stations, moorings, ports
- `LineDefinition`: Transects, survey lines with waypoint routes  
- `AreaDefinition`: Box surveys, search areas with boundary polygons

**`cruiseplan.schema.organization.*`**
- `LegDefinition`: Major cruise segments with scheduling strategy
- `ClusterDefinition`: Operation groupings within legs

#### Schema vs. Runtime Objects

```python
# YAML → Schema (Validation Layer)
from cruiseplan.schema.activities import PointDefinition
point_schema = PointDefinition(name="STN_001", latitude=60.0, longitude=-30.0)

# Schema → Runtime (Business Logic Layer)  
from cruiseplan.core.operations import PointOperation
point_runtime = PointOperation.from_definition(point_schema)
point_runtime.calculate_duration()  # Business logic method
```

### 2. Core Layer (`cruiseplan.core.*`)

**Purpose**: Runtime business objects that perform the actual oceanographic calculations and scheduling logic.

**Key Files**:
- `operations.py`: PointOperation, LineOperation, AreaOperation classes
- `cruise.py`: Main Cruise class that orchestrates everything
- `leg.py`: LegController for schedule management
- `cluster.py`: ClusterController for operation grouping

#### Runtime Operation Objects

```python
from cruiseplan.core.operations import PointOperation, LineOperation

# Business objects with calculation methods
point_op = PointOperation(name="CTD_001", latitude=60.0, longitude=-30.0)
point_op.calculate_duration()  # Returns duration in minutes
point_op.get_position()  # Returns (lat, lon) tuple

line_op = LineOperation(name="ADCP_Section", route=[(60.0, -30.0), (61.0, -29.0)])
line_op.calculate_route_distance()  # Great-circle distance calculation
line_op.calculate_duration(vessel_speed=10.0)  # Duration based on distance
```

#### The Cruise Class

```python
from cruiseplan.core.cruise import Cruise

# Main orchestrator class
cruise = Cruise("path/to/config.yaml")

# Access registries (catalogs)
cruise.point_registry    # Dict of all point operations
cruise.line_registry     # Dict of all line operations  
cruise.area_registry     # Dict of all area operations

# Schedule generation
timeline = cruise.generate_timeline()
for event in timeline:
    print(f"{event.start_time}: {event.operation.name}")
```

### 3. Processing Layer (`cruiseplan.processing.*`)

**Purpose**: Data enrichment and validation operations on configuration files.

**Key Operations**:
- **Enrichment** (`enrich.py`): Add bathymetry depths, coordinate formats, expand sections
- **Validation** (`validate.py`): Check configuration integrity, detect conflicts

```bash
# CLI processing operations
cruiseplan enrich -c config.yaml --add-depths --expand-sections
cruiseplan validate -c config.yaml --strict
```

#### Section Expansion

One of the most powerful processing features - converts line definitions into individual station points:

```python
# Input YAML: Line definition
lines:
  - name: "CTD_Section"
    route:
      - latitude: 60.0
        longitude: -30.0
      - latitude: 61.0
        longitude: -29.0
    distance_between_stations: 25.0  # km spacing

# Output YAML: Expanded individual stations  
points:
  - name: "CTD_Section_001"
    latitude: 60.0
    longitude: -30.0
    operation_type: "CTD"
  - name: "CTD_Section_002"  
    latitude: 60.5  # Interpolated position
    longitude: -29.5
    operation_type: "CTD"
```

### 4. Output Layer (`cruiseplan.output.*`)

**Purpose**: Generate professional outputs in multiple formats for different stakeholders.

**Key Generators**:
- `html_generator.py`: Interactive timeline with maps
- `csv_generator.py`: Spreadsheet-compatible schedules
- `netcdf_generator.py`: CF-compliant scientific data files
- `map_generator.py`: Publication-quality cruise track maps
- `kml_generator.py`: Google Earth overlays

```python
from cruiseplan.output.html_generator import HTMLGenerator
from cruiseplan.core.cruise import Cruise

cruise = Cruise("config.yaml")
generator = HTMLGenerator(cruise)
generator.generate("output_timeline.html")
```

### 5. Utilities Layer

**Purpose**: Shared functionality for calculations, data access, and common operations.

**Key Modules**:
- `cruiseplan.utils.coordinates`: Coordinate validation and conversion
- `cruiseplan.utils.defaults`: Configuration defaults and constants
- `cruiseplan.calculators.*`: Scientific calculation engines
- `cruiseplan.data.*`: External data access (bathymetry, PANGAEA)

---

## YAML Configuration Reference

### File Structure Overview

```yaml
# =================================================================
# CRUISE METADATA & GLOBAL SETTINGS
# =================================================================
cruise_name: "Iceland Survey 2025"
description: "Multi-area oceanographic survey"
default_vessel_speed: 10.0  # knots
default_distance_between_stations: 25.0  # km

# Timing parameters (all in minutes)
turnaround_time: 30.0
ctd_descent_rate: 1.0  # m/s
ctd_ascent_rate: 2.0   # m/s

# Operation windows
day_start_hour: 8   # For mooring operations
day_end_hour: 20

# Processing flags  
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: true

# Cruise timing
start_date: "2025-06-01T08:00:00Z"

# =================================================================
# GLOBAL CATALOGS (Reusable Definitions)
# =================================================================

# Point Operations: Fixed location activities
points:
  - name: "CTD_001"
    latitude: 64.1466
    longitude: -21.9426
    operation_type: "CTD"
    action: "profile"
    operation_depth: 2000.0  # meters
    duration: 180.0          # minutes

  - name: "MOORING_K1"
    latitude: 59.5000
    longitude: -39.5000
    operation_type: "mooring"
    action: "deployment" 
    duration: 240.0

# Line Operations: Routes with waypoints
lines:
  - name: "OVIDE_Section"
    operation_type: "CTD"
    action: "section"
    distance_between_stations: 25.0  # km
    route:
      - latitude: 59.5000
        longitude: -42.0000
      - latitude: 60.5000
        longitude: -40.0000
    reversible: true

# Area Operations: Boundary-defined regions
areas:
  - name: "IB_Survey_Box"
    operation_type: "underway"
    action: "survey"
    boundary:
      - latitude: 59.0000
        longitude: -42.0000
      - latitude: 60.0000
        longitude: -42.0000  
      - latitude: 60.0000
        longitude: -40.0000
      - latitude: 59.0000
        longitude: -40.0000

# Port definitions
ports:
  - name: "port_reykjavik"
    latitude: 64.1466
    longitude: -21.9426
    timezone: "Atlantic/Reykjavik"

# =================================================================
# SCHEDULE ORGANIZATION
# =================================================================

legs:
  - name: "Leg_01_Iceland_Greenland" 
    description: "Transit and initial survey"
    departure_port: "port_reykjavik"
    
    # Unified activities list (references to catalog items)
    activities:
      - "CTD_001"           # Point operation
      - "OVIDE_Section"     # Line operation  
      - "IB_Survey_Box"     # Area operation
      - "MOORING_K1"        # Another point operation

  - name: "Leg_02_Greenland_Work"
    strategy: "spatial_interleaved"  # TSP optimization
    ordered: false                   # Allow reordering
    
    activities:
      - "CTD_002" 
      - "CTD_003"
      
    # Sub-groupings within leg
    clusters:
      - name: "Deep_Stations"
        strategy: "sequential"
        ordered: true
        activities:
          - "CTD_004"
          - "CTD_005"
```

### Key YAML Concepts

#### 1. Global Catalogs vs. Schedule Organization

**Catalogs** (`points:`, `lines:`, `areas:`, `ports:`): 
- Define **what** operations are available
- Reusable definitions with full parameters
- Can be referenced by name in multiple places

**Schedule Organization** (`legs:`, `clusters:`):
- Define **when** and **how** operations are executed  
- Reference catalog items by name in `activities:` lists
- Control routing strategy and operation ordering

#### 2. Parameter Inheritance

Configuration flows from global → leg → cluster → operation:

```yaml
# Global default
default_vessel_speed: 10.0

legs:
  - name: "Fast_Leg"
    vessel_speed: 12.0  # Overrides global default
    
    activities:
      - name: "CTD_001"  # Uses leg vessel_speed (12.0)
      - name: "CTD_002"
        vessel_speed: 8.0  # Overrides leg default
```

#### 3. Activity References vs. Inline Definitions

```yaml
# Method 1: Reference catalog items (recommended)
activities:
  - "CTD_001"        # String reference to points catalog
  - "OVIDE_Section"  # String reference to lines catalog

# Method 2: Inline definitions (for leg-specific operations)  
activities:
  - name: "Transit_to_Area"
    operation_type: "transit"
    route: 
      - latitude: 60.0
        longitude: -30.0
      - latitude: 61.0  
        longitude: -29.0
```

---

## Python API Reference

### For Oceanographer-Developers

If you're an oceanographer getting into CruisePlan development, here are the key classes and patterns you'll work with:

#### Loading and Working with Configurations

```python
from cruiseplan.core.cruise import Cruise
from cruiseplan.schema.cruise import CruiseConfig

# Method 1: High-level Cruise class (recommended)
cruise = Cruise("path/to/config.yaml")

# Access operation registries
print(f"Total points: {len(cruise.point_registry)}")
print(f"Total lines: {len(cruise.line_registry)}")

# Generate timeline
timeline = cruise.generate_timeline()
for event in timeline:
    print(f"{event.start_time}: {event.operation_name} at {event.location}")

# Method 2: Schema-level validation only
config = CruiseConfig.model_validate_yaml_file("config.yaml")
print(f"Cruise: {config.cruise_name}")
print(f"Points defined: {len(config.points)}")
```

#### Working with Operations

```python
from cruiseplan.core.operations import PointOperation, LineOperation

# Access specific operations
ctd_station = cruise.point_registry["CTD_001"]
print(f"Location: {ctd_station.latitude:.4f}°N, {ctd_station.longitude:.4f}°E")
print(f"Duration: {ctd_station.calculate_duration():.1f} minutes")

# Calculate distances
survey_line = cruise.line_registry["OVIDE_Section"]
total_distance = survey_line.calculate_route_distance()  # km
transit_time = survey_line.calculate_duration(vessel_speed=10.0)  # minutes

print(f"Line distance: {total_distance:.1f} km")
print(f"Transit time: {transit_time/60:.1f} hours")
```

#### Creating New Operations Programmatically

```python
from cruiseplan.core.operations import PointOperation
from cruiseplan.schema.activities import PointDefinition

# Create via schema definition
point_def = PointDefinition(
    name="NEW_CTD",
    latitude=65.0,
    longitude=-25.0,
    operation_type="CTD",
    action="profile"
)

# Convert to runtime operation
point_op = PointOperation.from_definition(point_def)
duration = point_op.calculate_duration()
```

#### Processing Operations

```python
from cruiseplan.processing.enrich import enrich_configuration
from cruiseplan.processing.validate import validate_configuration

# Enrich with bathymetry data
enriched_config = enrich_configuration(
    "input.yaml",
    add_depths=True,
    expand_sections=True,
    output_file="enriched.yaml"
)

# Validate configuration
validation_results = validate_configuration("config.yaml")
if validation_results.has_errors():
    for error in validation_results.errors:
        print(f"Error: {error}")
```

### Common Development Patterns

#### 1. Adding New Operation Types

```python
# 1. Add to schema enums
from cruiseplan.schema.enums import OperationTypeEnum

# 2. Update validation in schema models
from cruiseplan.schema.activities import PointDefinition

# 3. Add business logic in core operations
from cruiseplan.core.operations import PointOperation

class PointOperation:
    def calculate_duration(self) -> float:
        if self.operation_type == "CTD":
            return self._calculate_ctd_duration()
        elif self.operation_type == "NEW_TYPE":
            return self._calculate_new_type_duration()  # Your logic here
```

#### 2. Custom Output Generators

```python
from cruiseplan.output.csv_generator import CSVGenerator
from cruiseplan.core.cruise import Cruise

class CustomReportGenerator:
    def __init__(self, cruise: Cruise):
        self.cruise = cruise
        
    def generate_station_summary(self, output_path: str):
        """Generate custom station summary."""
        with open(output_path, 'w') as f:
            for name, point_op in self.cruise.point_registry.items():
                f.write(f"{name},{point_op.latitude},{point_op.longitude}\n")

# Usage
cruise = Cruise("config.yaml")
generator = CustomReportGenerator(cruise) 
generator.generate_station_summary("stations.csv")
```

---

## Developer Workflow

### Setting Up Development Environment

```bash
# Clone and setup
git clone https://github.com/ocean-uhh/cruiseplan.git
cd cruiseplan

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Testing Workflow

```bash
# Run full test suite
pytest

# Run with coverage reporting
pytest --cov=cruiseplan --cov-report=html

# Run specific test categories
pytest -m "not slow"          # Skip slow tests during development
pytest tests/unit/             # Unit tests only
pytest tests/integration/      # Integration tests only
pytest -k "calculate"          # Tests with 'calculate' in the name
```

### Code Quality Checks

```bash
# Format code
black .

# Lint and auto-fix
ruff check . --fix

# Type checking
mypy cruiseplan/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Documentation Building

```bash
# Build documentation
cd docs
make html

# Serve locally for testing
python -m http.server --directory build/html 8080
# Visit http://localhost:8080
```

---

## Testing & Quality

### Test Organization

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── schema/             # Pydantic model validation
│   ├── core/               # Business logic
│   ├── calculators/        # Scientific calculations
│   └── utils/              # Utility functions
├── integration/            # End-to-end workflow tests
│   ├── processing/         # Enrich/validate operations
│   ├── output/             # Output generation
│   └── cli/                # Command-line interface
└── fixtures/               # Test data files
    ├── yaml_configs/       # Example YAML configurations
    └── expected_outputs/    # Reference output files
```

### Writing Tests

#### Schema Layer Tests

```python
import pytest
from cruiseplan.schema.activities import PointDefinition

def test_point_definition_validation():
    """Test point definition with valid coordinates."""
    point = PointDefinition(
        name="TEST_STN",
        latitude=60.0,
        longitude=-30.0,
        operation_type="CTD"
    )
    assert point.name == "TEST_STN"
    assert point.latitude == 60.0

def test_point_definition_invalid_latitude():
    """Test validation fails for invalid latitude."""
    with pytest.raises(ValidationError):
        PointDefinition(
            name="BAD_STN",
            latitude=91.0,  # Invalid: outside [-90, 90]
            longitude=-30.0
        )
```

#### Core Layer Tests

```python
from cruiseplan.core.operations import PointOperation
from cruiseplan.schema.activities import PointDefinition

def test_point_operation_duration_calculation():
    """Test CTD duration calculation."""
    point_def = PointDefinition(
        name="CTD_TEST",
        latitude=60.0,
        longitude=-30.0,
        operation_type="CTD",
        operation_depth=1000.0
    )
    
    point_op = PointOperation.from_definition(point_def)
    duration = point_op.calculate_duration()
    
    # CTD duration should be based on depth and descent/ascent rates
    expected_duration = (1000.0 / 1.0) + (1000.0 / 2.0)  # Down + up time
    assert abs(duration - expected_duration) < 1.0  # Within 1 minute
```

### Quality Standards

- **Test Coverage**: Maintain >80% coverage
- **Function Length**: Keep functions <75 statements  
- **Type Hints**: Use type annotations consistently
- **Docstrings**: NumPy format with units clearly specified
- **Scientific Citations**: Include references for oceanographic algorithms

---

## Contributing Guidelines

### Code Style and Conventions

#### 1. Coordinate Systems and Units

Always be explicit about coordinate systems and units:

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points.
    
    Parameters
    ----------
    lat1, lat2 : float
        Latitude coordinates in decimal degrees (WGS84).
    lon1, lon2 : float  
        Longitude coordinates in decimal degrees (WGS84).
        
    Returns
    -------
    float
        Distance in kilometers.
    """
```

#### 2. Time and Duration Handling

CruisePlan uses minutes as the standard duration unit:

```python
# Good: Explicit units
turnaround_time: float = 30.0  # minutes
ctd_descent_rate: float = 1.0  # m/s

# Use helper functions for conversion
from cruiseplan.utils.units import hours_to_minutes, minutes_to_hours

duration_hours = 2.5
duration_minutes = hours_to_minutes(duration_hours)  # 150.0
```

#### 3. Error Handling

Use specific exceptions with helpful messages:

```python
from cruiseplan.schema.exceptions import ValidationError, ConfigurationError

def validate_operation_depth(depth: float, max_depth: float) -> None:
    """Validate operation depth against bathymetry."""
    if depth > max_depth:
        raise ValidationError(
            f"Operation depth {depth}m exceeds water depth {max_depth}m. "
            f"CTD operations cannot exceed seafloor depth."
        )
```

### Git Workflow

1. **Feature Branches**: `git checkout -b feature/descriptive-name`
2. **Commit Messages**: Follow conventional commits
   ```
   feat(core): add support for multi-beam survey operations
   fix(schema): validate CTD depth against bathymetry  
   docs(api): update point operation examples
   ```
3. **Pull Requests**: Include comprehensive description with:
   - Summary of changes
   - Scientific rationale (if applicable)
   - Breaking changes (if any)
   - Test coverage information

### Documentation Requirements

#### Docstring Format (NumPy Style)

```python
def calculate_ctd_duration(depth: float, descent_rate: float, ascent_rate: float) -> float:
    """
    Calculate CTD cast duration based on oceanographic standard practices.
    
    Uses typical CTD operation timing with descent, bottom time, and ascent phases.
    Based on standard oceanographic practices (UNESCO, 1988).
    
    Parameters
    ----------
    depth : float
        Target depth for CTD cast in meters below surface.
    descent_rate : float
        CTD descent rate in meters per second.
    ascent_rate : float
        CTD ascent rate in meters per second.
        
    Returns
    -------
    float
        Total operation duration in minutes.
        
    Notes
    -----
    Calculation includes:
    - Descent time: depth / descent_rate  
    - Bottom time: 2 minutes (standard sampling time)
    - Ascent time: depth / ascent_rate
    
    References
    ----------
    UNESCO. 1988. The Acquisition, Calibration and Analysis of CTD Data. 
    UNESCO Technical Papers in Marine Science, No. 54.
    """
```

### Version Strategy

**Semantic Versioning** (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to YAML schema or API
- **MINOR**: New features, backward-compatible changes
- **PATCH**: Bug fixes, documentation updates

### Release Checklist

1. Update version in `_version.py`
2. Update `CHANGELOG.md` with new features and fixes
3. Run full test suite: `pytest`
4. Build documentation: `cd docs && make html`
5. Tag release: `git tag -a v0.4.0 -m "Release v0.4.0"`
6. Push tags: `git push --tags`

---

## Troubleshooting Common Issues

### YAML Configuration Errors

**Problem**: `ValidationError: 'stations' field not recognized`
```yaml
# ❌ Incorrect: Old field name
stations:
  - name: "CTD_001"
    
# ✅ Correct: Modern field name  
points:
  - name: "CTD_001"
```

**Problem**: `TypeError: PointDefinition missing required fields`
```yaml
# ❌ Incorrect: Missing required latitude/longitude
points:
  - name: "CTD_001"
    operation_type: "CTD"
    
# ✅ Correct: Include all required fields
points:
  - name: "CTD_001"
    latitude: 60.0
    longitude: -30.0
    operation_type: "CTD"
```

### API Usage Issues

**Problem**: Mixing schema and runtime objects
```python
# ❌ Incorrect: Using schema definition for calculations
from cruiseplan.schema.activities import PointDefinition
point_def = PointDefinition(name="CTD", latitude=60.0, longitude=-30.0)
duration = point_def.calculate_duration()  # AttributeError!

# ✅ Correct: Convert to runtime operation
from cruiseplan.core.operations import PointOperation
point_op = PointOperation.from_definition(point_def)
duration = point_op.calculate_duration()  # Works!
```

### Development Environment Issues

**Problem**: Import errors after package updates
```bash
# Solution: Reinstall in development mode
pip install -e ".[dev]" --force-reinstall
```

**Problem**: Type checking failures
```bash
# Solution: Update type stubs
pip install --upgrade mypy
mypy --install-types
```

---

This architecture guide provides the foundation for understanding and contributing to CruisePlan's codebase. The layered design ensures that oceanographic domain knowledge is properly separated from software engineering concerns, making the system both scientifically accurate and maintainable.

For specific implementation questions, refer to the API documentation or reach out to the development team through GitHub issues.