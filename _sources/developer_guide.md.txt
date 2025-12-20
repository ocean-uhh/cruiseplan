# CruisePlan Developer Guide

## Introduction & Architecture Overview

CruisePlan is a oceanographic cruise planning system.  This guide provides developers with an architectural overview to enable effective contribution to the codebase.

### Design Principles

- **Separation of Concerns**: Clear boundaries between validation, calculation, and output generation
- **Type Safety**: Pydantic models with comprehensive validation at the YAML layer
- **Abstraction**: Common interfaces for different operation types and organizational levels
- **Extensibility**: Clean modular design that facilitates adding new operation types and output formats

### Technology Stack

- **Core**: Python 3.9+ with Pydantic for data validation
- **Geospatial**: Built-in coordinate utilities, ETOPO/GEBCO bathymetry integration
- **Scientific**: NumPy, xarray for data processing
- **Visualization**: Matplotlib>=3.7 for static maps, Folium for interactive web maps
- **Data**: NetCDF4, Pandas for scientific data formats
- **Web**: HTML/CSS generation, KML for Google Earth

## Two-Layer Architecture System

CruisePlan implements a dual-layer architecture that separates YAML configuration validation from runtime operational calculations.

### YAML Layer (Validation Models)

The YAML layer uses Pydantic models for configuration parsing and validation:

```python
# Configuration container
class CruiseConfig(BaseModel):
    # Many more fields!
    cruise_name: str
    description: Optional[str] = None
    default_vessel_speed: float
    turnaround_time: float = DEFAULT_TURNAROUND_TIME_MIN
    # ... 20+ more fields
    departure_port: Optional[Union[str, PortDefinition]] = None  # Optional!
    stations: Optional[List[StationDefinition]] = None  # Optional!
    legs: List[LegDefinition]
    
# Organizational definitions  
class LegDefinition(BaseModel):
    # Much more complex!
    name: str
    departure_port: Union[str, PortDefinition]  # Required
    arrival_port: Union[str, PortDefinition]   # Required  
    activities: Optional[List[dict]]  # Not just stations!
    # ... many more fields
    
# Operation definitions
class StationDefinition(FlexibleLocationModel):  # Inherits coordinates!
    name: str
    operation_type: OperationTypeEnum  # Not OperationType
    action: ActionEnum
    operation_depth: Optional[float] = None
    water_depth: Optional[float] = None
    # ... many more fields
```




### Operations Layer (Runtime Classes)

The operations layer provides runtime objects optimized for scheduling calculations:

```python
  # Runtime organizational classes  
  class Cruise:
      def __init__(self, config_path: Union[str, Path]):
          # Complex initialization with registries and resolution
          self.runtime_legs: List[Leg] = [...]

  class Leg:
      @classmethod
      def from_definition(cls, leg_def: LegDefinition) -> "Leg":
          # Converts LegDefinition to runtime Leg

      def get_effective_speed(self, default_speed: float) -> float:
          # Parameter inheritance with defaults

  # Runtime operation classes
  class PointOperation(BaseOperation):
      def get_entry_point(self) -> tuple[float, float]:
          return self.position  # (lat, lon) tuple

      def calculate_duration(self, rules: Any) -> float:
          # Duration calculation with rules parameter
```

### Source Code References

**Configuration Models (Pydantic)**:
Look for `CruiseConfig`, `LegDefinition` and `StationDefinition` in:
- [Core validation models: cruiseplan/core/validation.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/validation.py)
- [All Pydantic models documentation: cruiseplan/core/](https://github.com/ocean-uhh/cruiseplan/tree/main/cruiseplan/core)

**Runtime Classes**: Look for
- `Cruise` in [cruiseplan/core/cruise.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/cruise.py)
- `Leg` in [cruiseplan/core/leg.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/leg.py)
- `BaseOperation` and `PointOperation` in [cruiseplan/core/operations.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/operations.py)

### Conversion Process

The system converts validation models to operational objects via factory methods:

```python
# Definition → Operation conversion
point_op = PointOperation.from_pydantic(station_definition)
line_op = LineOperation.from_pydantic(transit_definition, default_speed)
area_op = AreaOperation.from_pydantic(area_definition)

# Definition → Organizational conversion  
cruise = Cruise(config_path)  # Takes file path, not config object
leg = Leg.from_definition(leg_definition)
cluster = Cluster.from_definition(cluster_definition)
```

**Benefits**: This separation allows comprehensive validation at parse time while providing optimized objects for calculation-intensive scheduling operations.

## Organizational Hierarchy

### Cruise Level (Top Container)
- **Purpose**: Global settings and expedition-wide configuration
- **Key Features**: Port management, global defaults, multi-leg coordination
- **Runtime Class**: `Cruise` with leg collection and global state

### Leg Level (Operational Phases)
- **Purpose**: Discrete cruise phases with parameter inheritance
- **Runtime Features**:
  - Parameter inheritance: `get_effective_speed()`, `get_effective_spacing()`
  - Boundary management: departure/arrival ports as entry/exit points
  - Operation sequencing and cluster coordination

```python
class Leg:
    def get_effective_speed(self, default_speed: float) -> float:
        # Inherit from cruise config, override with leg-specific
        return self.vessel_speed if self.vessel_speed is not None else default_speed

    def get_effective_spacing(self, default_spacing: float) -> float:
        # Inherit from cruise config, override with leg-specific  
        return self.distance_between_stations if self.distance_between_stations is not None else default_spacing

    def get_entry_point(self) -> tuple[float, float]:
        # Departure port coordinates
        return (self.departure_port.latitude, self.departure_port.longitude)

    def get_exit_point(self) -> tuple[float, float]:
        # Arrival port coordinates  
        return (self.arrival_port.latitude, self.arrival_port.longitude)
```

### Cluster Level (Operation Grouping)
- **Purpose**: Operation grouping with scheduling strategies
- **Strategies**: `sequential` (implemented), not implemented: `spatial_interleaved`, `day_night_split`
- **Boundary Management**: Entry/exit points for routing and sequencing

```python
  class Cluster:
      def get_entry_point(self) -> Optional[tuple[float, float]]:
          # First operation position in cluster
          if not self.operations:
              return None
          first_op = self.operations[0]
          return (first_op.position.latitude, first_op.position.longitude)

      def get_exit_point(self) -> Optional[tuple[float, float]]:
          # Last operation position in cluster
          if not self.operations:
              return None
          last_op = self.operations[-1]
          return (last_op.position.latitude, last_op.position.longitude)
```

**Note:** Activity generation is handled by scheduler, not cluster directly.

## Operation Type Abstractions

### BaseOperation (Abstract Interface)

All operation types inherit from a common abstract base:

```python
class BaseOperation(ABC):
    @abstractmethod
    def get_entry_point(self) -> tuple[float, float]:
        """Geographic entry point for routing (latitude, longitude)"""

    @abstractmethod  
    def get_exit_point(self) -> tuple[float, float]:
        """Geographic exit point for routing (latitude, longitude)"""

    @abstractmethod
    def calculate_duration(self, rules: Any) -> float:
          """Duration in minutes based on DurationCalculator rules
          
          Parameters:
          rules: DurationCalculator object containing cruise config and calculation methods
          """
```

### Point Operations (PointOperation)
- **Types**: CTD stations, moorings
- **Duration**: Depth-based for CTD, manual for moorings
- **Entry/Exit**: Same location for both points

```python
class PointOperation(BaseOperation):
    def get_entry_point(self) -> tuple[float, float]:
        return self.position  # (latitude, longitude) tuple

    def get_exit_point(self) -> tuple[float, float]:
        return self.position  # Same as entry for point operations

    def calculate_duration(self, rules: Any) -> float:
        # Uses manual duration if specified, otherwise calculates based on operation type
        if self.manual_duration > 0:
            return self.manual_duration

        # Uses DurationCalculator for CTD depth-based calculations
        duration_calc = DurationCalculator(rules.config)
        return duration_calc.calculate_ctd_time(self.depth, self.op_type)
```

For details on the CTD duration calculation, see  [calculations](calculations.rst).

### Line Operations (LineOperation)
- **Types**: Scientific transects, navigation transits
- **Duration**: Route distance ÷ vessel speed
- **Entry/Exit**: First/last waypoints of route

```python
class LineOperation(BaseOperation):
    def get_entry_point(self) -> tuple[float, float]:
        if not self.route:
            return (0.0, 0.0)
        return self.route[0]  # First waypoint

    def get_exit_point(self) -> tuple[float, float]:
        if not self.route:
            return (0.0, 0.0)
        return self.route[-1]  # Last waypoint

    def calculate_duration(self, rules: Any) -> float:
        # Calculate total route distance using haversine_distance
        total_route_distance_km = 0.0
        for i in range(len(self.route) - 1):
            segment_distance = haversine_distance(self.route[i], self.route[i + 1])
            total_route_distance_km += segment_distance

        # Convert to nautical miles (vessel speed is in knots)
        route_distance_nm = total_route_distance_km * 0.539957

        # Use operation speed or fallback to config default
        vessel_speed = self.speed or rules.config.default_vessel_speed
        duration_hours = route_distance_nm / vessel_speed
        return duration_hours * 60.0  # Convert to minutes
```

For details on the haversine distance calculation, see  [calculations](calculations.rst).


### Area Operations (AreaOperation)
- **Types**: Survey grids, mapping areas, but can also be used for any generic operation type
- **Duration**: Manual specification required
- **Entry/Exit**: Calculated center point for routing (note, fine for bulk estimates in planning, but will introduce error--especially if the region is large)

```python
class AreaOperation(BaseOperation):
    def get_entry_point(self) -> tuple[float, float]:
        return self.start_point  # First corner of polygon

    def get_exit_point(self) -> tuple[float, float]:
        return self.end_point    # Last corner of polygon

    def calculate_duration(self, rules: Any) -> float:
        # Area operations require manual duration specification
        if self.duration is None:
            raise ValueError(f"Area operation '{self.name}' requires user-specified duration")
        return self.duration

    # Entry/exit points set during creation from first/last polygon corners:
    # start_point = boundary_tuples[0]   # First corner
    # end_point = boundary_tuples[-1]    # Last corner
```

## Entry/Exit Point Abstraction System

The entry/exit point system provides a unified interface for routing calculations across all operation types and organizational levels.

### Problem Solved
Type-agnostic routing that works consistently whether calculating distances between:
- Point → Point operations
- Point → Line operations  
- Line → Area operations
- Leg → Leg boundaries
- Any combination of the above

### Implementation Architecture

**Abstract Interface**: Both operations and organizational levels implement `get_entry_point()` and `get_exit_point()`:

```python
# Operation level implementation
class PointOperation:
    def get_entry_point(self) -> tuple[float, float]:
        return self.position  # (latitude, longitude) tuple

class LineOperation:
    def get_entry_point(self) -> tuple[float, float]:
        return self.route[0]  # First waypoint

class AreaOperation:
    def get_entry_point(self) -> tuple[float, float]:
        return self.start_point  # First corner of polygon

# Organizational level implementation        
class Cluster:
    def get_entry_point(self) -> Optional[tuple[float, float]]:
        if not self.operations:
            return None
        first_op = self.operations[0]
        return (first_op.position.latitude, first_op.position.longitude)

class Leg:
    def get_entry_point(self) -> tuple[float, float]:
        return (self.departure_port.latitude, self.departure_port.longitude)
```

**Usage in Routing**:

```python
def calculate_transit_distance(from_entity, to_entity) -> float:
    """Works for any combination of operations, clusters, or legs"""
    start_point = from_entity.get_exit_point()
    end_point = to_entity.get_entry_point()
    return haversine_distance(start_point, end_point)
```

**Benefits**:
- **Future-proof**: New operation types automatically work with existing routing
- **Cleaner code**: No type checking or isinstance() calls in routing logic  
- **Consistent interface**: Same method calls work across all entity types

## FlexibleLocationModel System

Handles multiple coordinate input formats with consistent internal representation.

**⚠️ Note: This system is under review for simplification in a future release.**

### Supported Input Formats

```python
# Explicit fields (recommended)
station1 = StationDefinition(latitude=60.0, longitude=-30.0)

# String format (legacy support)
station2 = StationDefinition(coordinates="60.0, -30.0")

# Both formats are normalized to internal GeoPoint storage
# Current access: station.position.latitude, station.position.longitude
```

The current FlexibleLocationModel system adds complexity:
- Requires indirect access via `station.position.latitude` instead of `station.latitude`
- Intermediate GeoPoint objects for simple coordinate storage
- String parsing for coordinates that are rarely used in practice

**Future Direction:** This system is a candidate for simplification to direct latitude/longitude fields in a future version, which would provide cleaner API access and reduced complexity while maintaining the same YAML configuration format.

For complete source code details, see https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/validation.py.


### Internal Architecture

```python
class FlexibleLocationModel(BaseModel):
      position: Optional[GeoPoint] = None  # Internal storage

      @model_validator(mode="before")  
      @classmethod
      def unify_coordinates(cls, data: Any) -> Any:
          # Converts latitude/longitude fields or coordinate strings
          # into position: GeoPoint object

      # Current access pattern:
      # station.position.latitude  
      # station.position.longitude

      # Note: Convenience @property methods do not exist yet
```


## Distance & Duration Calculation Architecture

### Distance Calculations

CruisePlan uses great circle distance calculations for accurate routing at oceanographic scales.

**Architecture**:
- **Haversine formula**: Implemented in `cruiseplan/calculators/distance.py`
- **Type-agnostic interface**: Works with any objects having `get_entry_point()`/`get_exit_point()` methods
- **Automatic transit insertion**: Distance calculations between operations trigger transit generation

**For detailed calculation formulas and parameters, see [calculations](calculations.rst).**


### Duration Calculations

  **DurationCalculator**: Centralized duration logic with operation-type-specific methods:

```python
class DurationCalculator:
    def calculate_ctd_time(self, depth_m: float, operation_type: str) -> float:
        """Depth-based CTD timing with configurable descent/ascent rates"""

    def calculate_transit_time(self, distance_km: float, speed_knots: float) -> float:
        """Route-based transit timing with unit conversions"""

    def calculate_mooring_time(self, operation_type: str, action: str) -> float:
        """Manual duration required for mooring operations"""
```

Architecture: Operations call calculate_duration(rules) which dispatches to appropriate calculator methods based on operation type.

**For detailed formulas, rates, and parameters, see [calculations](calculations.rst).**


## Validation Architecture

### Multi-Layer Validation

1. **Syntax Validation**: Pydantic v2 model validation at YAML parse
2. **Field Validation**: Range checking, type validation, business rules
3. **Cross-Reference Validation**: Reference resolution, port lookups

```python
class StationDefinition(FlexibleLocationModel):
    name: str
    operation_type: OperationTypeEnum
    action: ActionEnum
    # Coordinates handled by FlexibleLocationModel parent class

    @field_validator("duration")
    def validate_duration_positive(cls, v):
        """Validate duration is positive, warn about placeholder values"""
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v

    @field_validator("operation_type")  
    def validate_operation_type(cls, v):
        """Validate operation_type against enum values"""
        # Enum validation happens automatically
        return v

class CruiseConfig(BaseModel):
    @field_validator("default_vessel_speed")
    def validate_speed(cls, v):
        """Validate vessel speed is within realistic bounds (1-30 knots)"""
        if not (1.0 <= v <= 30.0):
            raise ValueError("Vessel speed must be between 1-30 knots")
        return v
```

### Error Handling Strategy

**User-Friendly Messages**: Transform technical validation errors into actionable guidance through custom exception types and Pydantic error handling.

```python
class CruiseConfigurationError(Exception):
    """
    Exception raised when cruise configuration is invalid or cannot be processed.
    
    This exception is raised during configuration validation when the YAML
    file contains invalid data, missing required fields, or logical inconsistencies
    that prevent the cruise plan from being properly loaded.
    """
    pass

# Error handling in practice:
try:
    cruise = Cruise(config_path)
except ValidationError as e:
    # Pydantic validation errors are automatically user-friendly
    print(f"Configuration validation failed: {e}")
except CruiseConfigurationError as e:
    # Custom cruise-specific validation errors
    print(f"Cruise configuration error: {e}")
```

Error Sources:
- **Pydantic ValidationError:** Automatic field validation with clear error messages
- **CruiseConfigurationError:** Custom exceptions for cruise-specific validation logic
- **File I/O errors:** YAML parsing and file access issues

For complete error handling patterns, see the https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/cruise.py.

## Development Patterns & Best Practices

### Adding New Operation Types

1. **Create Pydantic Definition**: New `*Definition` class inheriting from `BaseModel`
2. **Implement Runtime Class**: New operation class inheriting from `BaseOperation`  
3. **Add Conversion Method**: `from_pydantic()` class method
4. **Implement Abstract Methods**: `get_entry_point()`, `get_exit_point()`, `calculate_duration()`
5. **Add Duration Calculator**: Type-specific duration logic
6. **Update Validation**: Add to operation type enums and validators

### Testing Strategy

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: End-to-end workflow testing
- **Fixtures**: Realistic cruise configurations for consistent testing
- **Property-Based Testing**: Coordinate validation, calculation accuracy

```python
# Example test pattern
def test_point_operation_entry_exit_consistency():
    station = PointOperation.from_pydantic(station_definition)
    assert station.get_entry_point() == station.get_exit_point()
```

### Performance Considerations

- **Lazy Loading**: 
    - Bathymetry datasets loaded on-demand via `BathymetryManager._dataset` property (see [`bathymetry.py`](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/data/bathymetry.py)) 
    - NetCDF files only opened when first depth lookup is needed, avoiding memory overhead
- **Caching**:
    - PANGAEA dataset metadata cached via `CacheManager` (see [`pangaea.py`](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/data/pangaea.py)),
    - Pickle-based file cache in `.cache/` directory,   (see [`cache.py`](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/data/cache.py)) 
    - Bathymetry data kept in memory after first load to avoid repeated NetCDF reads
- **Bulk Operations**:
    - Bathymetry grid subsets with configurable stride downsampling (`get_grid_subset()`) reduces data points for plotting efficiency
    - PANGAEA API calls batch-processed with configurable rate limiting (default 1.0 req/sec)
    - Haversine distance calculations (see [`distance.py`](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/calculators/distance.py)) for route segment optimization


### Error Handling Patterns

```python
# Custom exception hierarchy
class CLIError(Exception):
    """Command-line interface errors"""

class YAMLIOError(Exception):
    """YAML file I/O operation errors"""

class ReferenceError(Exception):
    """Configuration reference resolution failures"""

class CruiseConfigurationError(Exception):
    """Cruise configuration validation errors"""

# Uses Pydantic's ValidationError for data validation
from pydantic import ValidationError
```

See files such as:
- [cli/utils.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/cli/utils.py) - CLIError for command-line issues
- [utils/yaml_io.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/utils/yaml_io.py) - YAMLIOError for YAML I/O problems
- [core/cruise.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/cruise.py) - ReferenceError for unresolved references
- [core/validation.py](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/core/validation.py) - CruiseConfigurationError for configuration issues
- Multiple files import Pydantic's `ValidationError` for data validation

## Code Organization

### Module Structure

- `cruiseplan/core/`: Configuration management, validation models
- `cruiseplan/calculators/`: Distance, duration, routing algorithms  
- `cruiseplan/data/`: PANGAEA integration, bathymetry handling
- `cruiseplan/output/`: Multi-format output generation
- `cruiseplan/interactive/`: Station picker and GUI components
- `cruiseplan/utils/`: Coordinate conversion, common utilities

See the complete structure in [project_structure](project_structure.md)

### Dependencies

- **Core Dependencies**: Required for basic functionality (see [`requirements.txt`](https://github.com/ocean-uhh/cruiseplan/blob/main/requirements.txt))
- **Optional Dependencies**: Enhanced features for specialized outputs (defined in [`pyproject.toml`](https://github.com/ocean-uhh/cruiseplan/blob/main/pyproject.toml))  
- **Development Dependencies**: Testing, linting, documentation tools (see [`requirements-dev.txt`](https://github.com/ocean-uhh/cruiseplan/blob/main/requirements-dev.txt))

This architecture provides a solid foundation for extending CruisePlan while maintaining code quality, type safety, and user experience standards.