# CruisePlan Architecture

## Overview

CruisePlan organizes cruise operations using a hierarchical grouping system that reflects operational planning needs. This document describes the core architectural concepts for developers and advanced users working with the CruisePlan system.

For complete YAML field definitions and examples, see the :doc:`yaml_reference`. For practical workflows, see the :doc:`user_workflows`.

## Hierarchical Grouping System

CruisePlan uses a flexible multi-level grouping system to organize operations:

```
Cruise (expedition-level container)
  ↓ contains
Legs (operational segments with departure/arrival ports)
  ↓ can contain directly:
    - Activities (individual operations: stations, transits, areas, moorings)
  ↓ or organized into:
    - Clusters (geographic/organizational groupings of activities)
      ↓ which contain:
        - Activities (individual operations)
```

**Key Insight**: Each level serves a specific organizational purpose:
- **Cruise**: Overall expedition container with global parameter defaults
- **Leg**: Port-to-port segments for routing and logistics (can be auto-created for simple cruises)  
- **Cluster**: Optional geographic/organizational groupings (e.g., "Northern Sites", "Deep Water Stations")
- **Activities**: Individual scientific operations that actually get executed

**Simplified Configuration**: For simple single-leg cruises, you can omit the ``legs`` section entirely. When departure_port and arrival_port are specified at the cruise level along with activities, CruisePlan automatically creates a default leg (see :ref:`yaml-reference:simplified-leg-creation` for details).

## Design Principles

### 1. Hierarchical Organization
- **Cruise**: Top-level expedition container with global parameter defaults
- **Legs**: Port-to-port segments for routing and logistics (REQUIRED: `departure_port` + `arrival_port`; can be auto-created)
- **Clusters**: Optional geographic/organizational groupings of related activities  
- **Activities**: Individual scientific operations (stations, transits, areas, moorings)

### 2. Activities-Only Architecture
- Single `activities` field replaces confusing field overlap
- No ambiguity about where operations are defined
- Consistent naming across all container levels

### 3. Parameter Inheritance
Natural parameter flow down the hierarchy: **Cruise → Leg → Cluster → Operations**
- Cruise-level defaults (vessel speed, turnaround time, etc.)
- Leg-specific overrides (when explicitly defined in YAML)
- Cluster-specific overrides (planned future enhancement)
- Operation-specific overrides (when explicitly defined in YAML)

**Note**: Currently, only cruise-level and operation-level parameter overrides are implemented in the YAML configuration. Leg-level parameter inheritance is supported in the runtime classes but not yet exposed in YAML configuration.

### 4. Cluster Boundaries
- Define which operations can be shuffled together for optimization
- Provide strict boundaries for scheduling algorithms
- Enable advanced scheduling strategies (spatial, temporal, etc -- *not yet implemented*)

### 5. Default Behavior
- **Auto-created legs**: If no legs are defined but departure_port + arrival_port + activities exist at cruise level, auto-create default leg
- **Auto-created clusters**: If leg has no explicit clusters, create default cluster from leg activities  
- Simplifies common use cases while enabling complex scenarios

## Data Models

### LegDefinition (YAML Configuration)

```python
class LegDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    
    # REQUIRED: Maritime legs are always port-to-port
    departure_port: str  # Port reference (e.g., "port_reykjavik")
    arrival_port: str    # Port reference
    
    # Operational boundaries within the leg
    first_station: Optional[str] = None   # First operational station
    last_station: Optional[str] = None    # Last operational station
    
    # Parameter inheritance from cruise level
    vessel_speed: Optional[float] = None              # Leg-specific vessel speed (knots)
    distance_between_stations: Optional[float] = None # Station spacing (km)
    turnaround_time: Optional[float] = None           # Between operations (minutes)
    buffer_time: Optional[float] = None               # Leg contingency time (minutes)
    
    # Activities organization
    activities: Optional[List[str]] = None            # For default cluster if no explicit clusters
    clusters: Optional[List[ClusterDefinition]] = None # Explicit operational groupings
    ordered: bool = True                              # Whether default cluster is ordered
```

### ClusterDefinition (YAML Configuration)

```python
class ClusterDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    
    # Unified activities approach
    activities: List[str]  # Activity names from global catalog
    ordered: bool = True   # Whether activities can be shuffled
    strategy: StrategyEnum = StrategyEnum.SEQUENTIAL  # Scheduling strategy
```

### PortDefinition (YAML Configuration)

```python
class PortDefinition(BaseModel):
    name: str           # Unique port identifier
    latitude: float     # Port latitude in decimal degrees
    longitude: float    # Port longitude in decimal degrees
    timezone: Optional[str] = None      # Port timezone (e.g., 'UTC')
    description: Optional[str] = None   # Human-readable description
    display_name: Optional[str] = None  # Pretty name for UI display
```

## Runtime Objects

### Leg Class

The runtime `Leg` class represents an actual cruise leg with resolved references:

```python
class Leg:
    def __init__(
        self,
        name: str,
        departure_port: Union[str, PortDefinition],  # REQUIRED
        arrival_port: Union[str, PortDefinition],    # REQUIRED
        first_station: Optional[str] = None,
        last_station: Optional[str] = None,
        description: Optional[str] = None,
        first_waypoint: Optional[str] = None,   # Navigation waypoint (not executed)
        last_waypoint: Optional[str] = None,    # Navigation waypoint (not executed)
    )
    
    # Parameter inheritance
    vessel_speed: Optional[float]              # Inherited from cruise or leg-specific
    distance_between_stations: Optional[float] # Inherited from cruise or leg-specific  
    turnaround_time: Optional[float]           # Inherited from cruise or leg-specific
    buffer_time: Optional[float]               # Leg-specific contingency time
    
    # Container for operations
    clusters: List[Cluster] = []
    
    def get_effective_speed(self, cruise_default: float) -> float:
        """Get effective vessel speed with inheritance."""
        return self.vessel_speed or cruise_default
        
    def get_effective_turnaround_time(self, cruise_default: float) -> float:
        """Get effective turnaround time with inheritance."""
        return self.turnaround_time or cruise_default
```

### Cluster Class

Runtime clusters contain resolved operations with boundary management:

```python
class Cluster:
    def __init__(
        self,
        name: str,
        activities: List[str],
        ordered: bool = True,
        strategy: StrategyEnum = StrategyEnum.SEQUENTIAL,
    )
    
    operations: List[BaseOperation] = []  # Resolved from activities
    
    def can_shuffle_operations(self) -> bool:
        """Whether operations in this cluster can be reordered."""
        return not self.ordered
        
    def apply_strategy(self) -> List[BaseOperation]:
        """Apply scheduling strategy to operations within cluster."""
        # Implementation varies by strategy type
```

## Port System

### Global Port Registry

CruisePlan includes a global registry of common research ports:

```python
# Pre-defined ports accessible via references
"port_reykjavik"     # Reykjavik, Iceland  
"port_bergen"        # Bergen, Norway
"port_singapore"     # Singapore
"port_honolulu"      # Honolulu, Hawaii
# ... 20+ additional research ports
```

### Port Resolution

Port references are resolved in this order:
1. **Custom ports catalog** in YAML configuration
2. **Global port registry** for standard references
3. **Error** if port reference not found

### Port Expansion

Use `cruiseplan enrich --expand-ports` to convert global port references into local catalog entries:

```bash
# Before enrichment
legs:
  - departure_port: port_reykjavik  # Global reference

# After enrichment
ports:
  - name: port_reykjavik
    latitude: 64.1466
    longitude: -21.9426
    display_name: "Reykjavik, Iceland"

legs:
  - departure_port: port_reykjavik  # Now resolves to catalog entry
```

## Scheduling Logic

### Port-to-Port Routing

The scheduler implements realistic maritime routing:

1. **Inter-leg routing**: `previous_leg.arrival_port → next_leg.departure_port`
2. **Pre-leg routing**: `departure_port → first_station` (if first_station exists)
3. **Post-leg routing**: `last_station → arrival_port` (if last_station exists)
4. **Within-leg routing**: Standard operation-to-operation transits

### Parameter Inheritance

Parameters flow down the hierarchy with closer definitions taking precedence:

```python
# Current implementation resolution order (highest precedence first):
1. Operation-specific parameter (in YAML operation definition)
2. Cruise-level default parameter
3. System default value

# Planned resolution order (future enhancement):
1. Operation-specific parameter
2. Cluster-specific parameter (if operation is in a cluster) 
3. Leg-specific parameter  
4. Cruise-level default parameter
5. System default value

# Current example for vessel_speed:
effective_speed = (
    operation.vessel_speed or 
    cruise.default_vessel_speed or 
    8.0  # system default
)

# Future example (when leg/cluster inheritance implemented):
effective_speed = (
    operation.vessel_speed or 
    cluster.vessel_speed or  # if operation is in a cluster
    leg.vessel_speed or 
    cruise.default_vessel_speed or 
    8.0  # system default
)
```

### Cluster Processing

Within each leg, clusters are processed in order:

1. **Cluster boundaries respected**: Operations cannot be moved between clusters
2. **Within-cluster shuffling**: Depends on `ordered` flag
3. **Strategy application**: `SEQUENTIAL`, `SPATIAL`, etc.
4. **Operation resolution**: Activity names converted to operation objects

## Configuration Examples

### Simple Single-Leg Cruise (Auto-Created Leg)

```yaml
# Simplified configuration - no legs required!
cruise_name: "Iceland Survey 2024"
departure_port: "port_reykjavik"    # Allowed when no explicit legs
arrival_port: "port_reykjavik"      # Allowed when no explicit legs
default_vessel_speed: 8.0

points:
  - name: "STN_001"
    latitude: 64.1
    longitude: -21.9
    operation_type: "CTD"
    action: "profile"

# CruisePlan automatically creates:
# legs:
#   - name: "Iceland Survey 2024_DefaultLeg"
#     departure_port: "port_reykjavik"
#     arrival_port: "port_reykjavik"
#     activities: ["STN_001"]
```

### Explicit Single-Leg Cruise

```yaml
# Basic cruise with explicit leg and default cluster
ports:
  - name: "port_reykjavik"
    latitude: 64.1466
    longitude: -21.9426
    display_name: "Reykjavik, Iceland"

legs:
  - name: "Iceland_Survey_2024"
    departure_port: "port_reykjavik"
    arrival_port: "port_reykjavik" 
    vessel_speed: 8.0
    activities: ["STN_001", "STN_002", "STN_003"]  # Creates default cluster
```

### Multi-Leg Expedition

```yaml
# Complex expedition with port calls
ports:
  - name: "port_reykjavik"
    latitude: 64.1466
    longitude: -21.9426
    display_name: "Reykjavik, Iceland"
  - name: "port_longyearbyen"
    latitude: 78.2232
    longitude: 15.6267
    display_name: "Longyearbyen, Svalbard"

legs:
  - name: "Transit_to_Svalbard"
    departure_port: "port_reykjavik"
    arrival_port: "port_longyearbyen"
    vessel_speed: 12.0  # Higher speed for transit
    first_station: "TRANS_001"
    last_station: "TRANS_005"
    activities: ["TRANS_001", "TRANS_002", "TRANS_003", "TRANS_004", "TRANS_005"]
    
  - name: "Svalbard_Operations"
    departure_port: "port_longyearbyen"
    arrival_port: "port_longyearbyen"
    vessel_speed: 8.0   # Slower speed for operations
    first_station: "SVL_001"
    last_station: "SVL_020"
    clusters:
      - name: "Western_Transect"
        activities: ["SVL_001", "SVL_002", "SVL_003"]
        ordered: false  # Can shuffle for efficiency
      - name: "Eastern_Transect"
        activities: ["SVL_018", "SVL_019", "SVL_020"]
        ordered: false
        
  - name: "Return_Transit"
    departure_port: "port_longyearbyen"
    arrival_port: "port_reykjavik"
    vessel_speed: 12.0
    activities: ["RTN_001", "RTN_002", "RTN_003"]
```

### Advanced Cluster Organization

```yaml
# Complex cluster boundaries and strategies
legs:
  - name: "Arctic_Survey_2024"
    departure_port: "port_tromso"
    arrival_port: "port_tromso"
    vessel_speed: 8.0
    buffer_time: 480  # 8 hours weather contingency
    clusters:
      - name: "Deep_Water_CTD"
        activities: ["ARC_001", "ARC_002", "ARC_003"] 
        ordered: false  # Spatial optimization allowed
        strategy: "spatial_interleaved"
        
      - name: "Mooring_Deployment"
        activities: ["MOOR_A_Deploy", "Trilateration_Survey", "MOOR_A_Release"]
        ordered: true   # Strict sequence required
        strategy: "sequential"
        
      - name: "Shallow_Survey"
        activities: ["ARC_045", "ARC_046", "ARC_047", "ARC_048", "ARC_049", "ARC_050"]
        ordered: false  # Efficiency optimization
        strategy: "spatial_interleaved"
```

## Development Guidelines

### Adding New Ports

1. **For global ports**: Add to `cruiseplan/utils/global_ports.py`
2. **For project-specific ports**: Add to YAML `ports:` section
3. **Always include**: `latitude`, `longitude`, `display_name`
4. **Consider**: timezone information for international expeditions

### Extending Operation Types

1. **Add to validation models**: Extend `OperationTypeEnum` in `cruiseplan/core/validation.py`
2. **Add resolver function**: Create `_resolve_[type]_details()` in scheduler
3. **Add operation class**: Extend `BaseOperation` in `cruiseplan/core/operations.py`
4. **Update duration calculator**: Add duration logic in `cruiseplan/calculators/duration.py`

### Custom Scheduling Strategies

1. **Extend StrategyEnum**: Add new strategy types
2. **Implement strategy logic**: In `Cluster.apply_strategy()`
3. **Consider cluster boundaries**: Strategies only operate within clusters
4. **Test edge cases**: Empty clusters, single operations, etc.

### Entry/Exit Point Abstraction

**Core Routing Principle**: 
Scheduling creates a continuous expedition path by connecting exit points to entry points between operations

**Implementation Concept**:

```python
def generate_cruise_track(operations: List[Operation]):
    """
    Connect exit point of one operation to entry point of next operation
    to create complete cruise track
    """
    cruise_track = []
    for i in range(len(operations) - 1):
        current_op = operations[i]
        next_op = operations[i+1]
        
        # Connect exit of current operation to entry of next operation
        transit = create_transit(
            start=current_op.get_exit_point(), 
            end=next_op.get_entry_point()
        )
        
        cruise_track.extend([
            current_op,
            transit,
            next_op
        ])
    
    return cruise_track
```

**Key Characteristics**:
- **Seamless Transitions**: Automatic connection between operations
- **Flexible Path Generation**: Works across different operation types
- **Predictable Routing**: Clear method for determining cruise track

**Benefits**:
- Enables complex expedition routing
- Works across different operation types
- Provides a standardized way to generate cruise tracks

## Migration from Legacy Architecture

### Deprecated Fields

The following fields are deprecated and will be removed in v0.3.0:

**LegDefinition deprecated fields**:
- `sequence` → Use `activities` field
- `stations` → Use `activities` field  
- `sections` → Use `activities` field

**ClusterDefinition deprecated fields**:
- `sequence` → Use `activities` field
- `stations` → Use `activities` field
- `generate_transect` → Use `activities` field

### Migration Strategy

1. **Update field names**: Replace deprecated fields with `activities`
2. **Add port requirements**: Ensure all legs have `departure_port` and `arrival_port`
3. **Test with warnings**: Run existing configs to see deprecation warnings
4. **Use enrichment tools**: `cruiseplan enrich --expand-ports` for port catalog

### Backward Compatibility

- **Current version**: All deprecated fields functional with warnings
- **v0.3.0**: Deprecated fields will be removed (breaking change)
- **Migration period**: Deprecation warnings guide users to new format

## Architecture Benefits

✅ **Maritime Accuracy**: Legs correctly represent port-to-port segments  
✅ **Clear Hierarchy**: Unambiguous container relationships  
✅ **Parameter Inheritance**: Natural flow from cruise to operation level  
✅ **Flexible Organization**: Simple default clusters and complex explicit clusters  
✅ **Operational Reality**: Reflects actual maritime cruise operations  
✅ **Validation**: Clear rules about required fields and references  
✅ **Extensibility**: Easy to add new operation types and scheduling strategies  
✅ **Port Management**: Consistent global and custom port handling  

## Performance Considerations

### Memory Usage
- **Reference resolution**: Activity names resolved to operation objects during timeline generation
- **Port object creation**: Each port reference creates a new PortDefinition object (no sharing)
- **Cluster boundaries**: Limit search space for optimization algorithms

### Scheduling Performance
- **Cluster isolation**: Optimization algorithms work within cluster boundaries
- **Parameter resolution**: Inherited parameters resolved on-demand via simple conditionals
- **Port lookups**: Global port registry optimized for fast access

### Large Expeditions
- **Leg separation**: Multi-leg cruises process independently  
- **Cluster parallelization**: Unordered clusters can be processed in parallel
- **Memory efficient**: Timeline generation streams through activities

This architecture provides a solid foundation for complex maritime cruise planning while maintaining simplicity for common use cases.