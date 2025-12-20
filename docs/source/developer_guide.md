# CruisePlan Developer Guide

## Introduction & Architecture Overview

CruisePlan is a comprehensive oceanographic cruise planning system built for extensibility, type safety, and separation of concerns. This guide provides developers with the architectural understanding needed to contribute effectively to the codebase.

### Design Principles

- **Separation of Concerns**: Clear boundaries between validation, calculation, and output generation
- **Type Safety**: Pydantic models with comprehensive validation at the YAML layer
- **Abstraction**: Common interfaces for different operation types and organizational levels
- **Extensibility**: Pluggable architecture for new operation types and output formats

### Technology Stack

- **Core**: Python 3.9+ with Pydantic for data validation
- **Geospatial**: GeoPandas, Shapely for coordinate handling
- **Scientific**: NumPy, xarray for data processing
- **Visualization**: Matplotlib, Cartopy for map generation
- **Data**: NetCDF4, Pandas for scientific data formats
- **Web**: HTML/CSS generation, KML for Google Earth

## Two-Layer Architecture System

CruisePlan implements a dual-layer architecture that separates YAML configuration validation from runtime operational calculations.

### YAML Layer (Validation Models)

The YAML layer uses Pydantic models for configuration parsing and validation:

```python
# Configuration container
class CruiseConfig(BaseModel):
    cruise_name: str
    legs: List[LegDefinition]
    stations: List[StationDefinition]
    
# Organizational definitions  
class LegDefinition(BaseModel):
    name: str
    departure_port: str
    stations: List[str]
    
# Operation definitions
class StationDefinition(BaseModel):
    name: str
    operation_type: OperationType
    latitude: float
    longitude: float
```

### Operations Layer (Runtime Classes)

The operations layer provides runtime objects optimized for scheduling calculations:

```python
# Runtime organizational classes
class Cruise:
    def __init__(self, config: CruiseConfig):
        self.legs = [Leg.from_definition(leg_def) for leg_def in config.legs]
        
class Leg:
    def get_effective_speed(self) -> float:
        # Parameter inheritance with defaults
        
# Runtime operation classes
class PointOperation(BaseOperation):
    def get_entry_point(self) -> GeoPoint:
        return self.location
        
    def calculate_duration(self) -> float:
        # CTD depth-based calculations
```

### Conversion Process

The system converts validation models to operational objects via factory methods:

```python
# Definition → Operation conversion
point_op = PointOperation.from_pydantic(station_definition, leg_context)
line_op = LineOperation.from_pydantic(transit_definition, leg_context)
area_op = AreaOperation.from_pydantic(area_definition, leg_context)

# Definition → Organizational conversion  
cruise = Cruise(cruise_config)  # Handles full hierarchy conversion
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
    def get_effective_speed(self) -> float:
        # Inherit from cruise config, override with leg-specific
        return self.speed or self.cruise.default_speed
        
    def get_entry_point(self) -> GeoPoint:
        return self.departure_port.coordinates
        
    def get_exit_point(self) -> GeoPoint:
        return self.arrival_port.coordinates
```

### Cluster Level (Operation Grouping)
- **Purpose**: Operation grouping with scheduling strategies
- **Strategies**: `sequential`, `spatial_interleaved`, `day_night_split`
- **Activities-Based Architecture**: Operations decomposed into scheduling activities

```python
class Cluster:
    def generate_activities(self) -> List[ActivityRecord]:
        if self.strategy == "sequential":
            return self._generate_sequential_activities()
        elif self.strategy == "spatial_interleaved":
            return self._generate_interleaved_activities()
```

## Operation Type Abstractions

### BaseOperation (Abstract Interface)

All operation types inherit from a common abstract base:

```python
class BaseOperation(ABC):
    @abstractmethod
    def get_entry_point(self) -> GeoPoint:
        """Geographic entry point for routing"""
        
    @abstractmethod  
    def get_exit_point(self) -> GeoPoint:
        """Geographic exit point for routing"""
        
    @abstractmethod
    def calculate_duration(self) -> float:
        """Duration in minutes"""
```

### Point Operations (PointOperation)
- **Types**: CTD stations, moorings, calibrations
- **Duration**: Depth-based for CTD, manual for moorings
- **Entry/Exit**: Same location for both points

```python
class PointOperation(BaseOperation):
    def get_entry_point(self) -> GeoPoint:
        return self.location
        
    def get_exit_point(self) -> GeoPoint:
        return self.location  # Same as entry
        
    def calculate_duration(self) -> float:
        if self.operation_type == OperationType.CTD:
            return CTDDurationCalculator.calculate(self.depth)
        return self.manual_duration  # Required for moorings
```

### Line Operations (LineOperation)
- **Types**: Scientific transects, navigation transits
- **Duration**: Route distance ÷ vessel speed
- **Entry/Exit**: First/last waypoints of route

```python
class LineOperation(BaseOperation):
    def get_entry_point(self) -> GeoPoint:
        return self.waypoints[0]
        
    def get_exit_point(self) -> GeoPoint:
        return self.waypoints[-1]
        
    def calculate_duration(self) -> float:
        distance_km = self.calculate_route_distance()
        speed_kmh = self.vessel_speed * KNOTS_TO_KMH
        return (distance_km / speed_kmh) * 60  # minutes
```

### Area Operations (AreaOperation)
- **Types**: Survey grids, mapping areas
- **Duration**: Manual specification required
- **Entry/Exit**: Calculated center point for routing

```python
class AreaOperation(BaseOperation):
    def get_entry_point(self) -> GeoPoint:
        return self.calculate_center_point()
        
    def get_exit_point(self) -> GeoPoint:
        return self.calculate_center_point()  # Same as entry
        
    def calculate_center_point(self) -> GeoPoint:
        # Geometric centroid of area polygon
        return GeoPoint(
            latitude=sum(p.latitude for p in self.corners) / len(self.corners),
            longitude=sum(p.longitude for p in self.corners) / len(self.corners)
        )
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
    def get_entry_point(self) -> GeoPoint:
        return self.location  # Same location
        
class LineOperation:
    def get_entry_point(self) -> GeoPoint:
        return self.waypoints[0]  # First waypoint
        
class AreaOperation:
    def get_entry_point(self) -> GeoPoint:
        return self.calculate_center_point()  # Geometric center

# Organizational level implementation        
class Leg:
    def get_entry_point(self) -> GeoPoint:
        return self.departure_port.coordinates
        
class Cluster:
    def get_entry_point(self) -> GeoPoint:
        return self.operations[0].get_entry_point()
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

### Supported Input Formats

```python
# Explicit fields
station1 = StationDefinition(latitude=60.0, longitude=-30.0)

# String format  
station2 = StationDefinition(coordinates="60.0, -30.0")

# Both formats are normalized to internal GeoPoint
```

### Internal Architecture

```python
class FlexibleLocationModel(BaseModel):
    position: GeoPoint = Field(default_factory=GeoPoint)
    
    @property
    def latitude(self) -> float:
        return self.position.latitude
        
    @property  
    def longitude(self) -> float:
        return self.position.longitude
```

### Benefits
- **User flexibility**: Accept coordinates in natural formats
- **Internal consistency**: Always work with validated GeoPoint objects
- **Property access**: Direct `.latitude` and `.longitude` properties

## Distance & Duration Calculation Architecture

### Distance Calculations

**Haversine Implementation**: Great circle distances for accuracy at oceanographic scales:

```python
def haversine_distance(point1: GeoPoint, point2: GeoPoint) -> float:
    """Returns distance in kilometers"""
    # Earth radius in km
    R = 6371.0
    # Haversine formula implementation
```

**Distance Assignment Strategy**:
- **Route distances**: Sum of segment distances for line operations
- **Inter-operation transits**: Automatic insertion between operations
- **Scientific vs navigation**: Different routing algorithms

### Duration Calculations

**DurationCalculator**: Centralized duration logic with type-specific implementations:

```python
class DurationCalculator:
    @staticmethod
    def calculate_ctd_duration(depth_m: float) -> float:
        """Depth-based CTD timing with descent/ascent rates"""
        descent_rate = 1.0  # m/s
        ascent_rate = 1.5   # m/s
        bottom_time = 5.0   # minutes
        
        total_time = (depth_m / descent_rate + depth_m / ascent_rate) / 60.0
        return total_time + bottom_time
        
    @staticmethod
    def calculate_transit_duration(distance_km: float, speed_knots: float) -> float:
        """Route-based transit timing"""
        speed_kmh = speed_knots * 1.852
        return (distance_km / speed_kmh) * 60.0  # minutes
```

## Validation Architecture

### Multi-Layer Validation

1. **Syntax Validation**: Pydantic model validation at YAML parse
2. **Semantic Validation**: Cross-field validation (coordinates, references)
3. **Cross-Reference Validation**: Station references, port lookups

```python
class StationDefinition(BaseModel):
    name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    
    @validator('operation_type')
    def validate_operation_type(cls, v, values):
        # Semantic validation logic
        
    @validator('duration')  
    def validate_duration_requirements(cls, v, values):
        # Cross-field validation logic
```

### Error Handling Strategy

**User-Friendly Messages**: Transform technical validation errors into actionable guidance:

```python
class ValidationError(Exception):
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.user_message = f"Configuration error in '{field}': {message}"
```

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

- **Lazy Loading**: Defer expensive calculations until needed
- **Caching**: Cache bathymetry lookups, distance calculations
- **Bulk Operations**: Batch coordinate transformations, database queries

### Error Handling Patterns

```python
# Custom exception hierarchy
class CruisePlanError(Exception):
    """Base exception for user-facing errors"""
    
class ValidationError(CruisePlanError):
    """Configuration validation failures"""
    
class CalculationError(CruisePlanError):
    """Runtime calculation failures"""
```

## Code Organization

### Module Structure

- `cruiseplan/core/`: Configuration management, validation models
- `cruiseplan/calculators/`: Distance, duration, routing algorithms  
- `cruiseplan/data/`: PANGAEA integration, bathymetry handling
- `cruiseplan/output/`: Multi-format output generation
- `cruiseplan/interactive/`: Station picker and GUI components
- `cruiseplan/utils/`: Coordinate conversion, common utilities

### Dependencies

- **Core Dependencies**: Required for basic functionality
- **Optional Dependencies**: Enhanced features (cartopy for maps)
- **Development Dependencies**: Testing, linting, documentation

This architecture provides a solid foundation for extending CruisePlan while maintaining code quality, type safety, and user experience standards.