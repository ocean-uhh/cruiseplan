# CruisePlan Developer Guide

This guide describes the internal architecture for contributors and developers
integrating directly with CruisePlan internals.

## Module structure

```
cruiseplan/
├── config/       # Pydantic models, field definitions, constants, exceptions
├── runtime/      # CruiseInstance, Leg, Cluster, operation classes
├── timeline/     # Scheduling, distance/duration calculators
├── api/          # High-level API functions (thin wrappers)
├── cli/          # Subcommand argument parsers and runners
├── data/         # Bathymetry and PANGAEA data handling
├── interactive/  # Interactive station picker
├── output/       # Output generators (LaTeX, HTML, PNG, KML, NetCDF, CSV)
└── utils/        # Coordinate conversion and shared utilities
```

Data flow: `YAML → CruiseInstance (runtime) → scheduler (timeline) → output files`.

## Two-layer architecture

### Config layer (`cruiseplan/config/`)

Pydantic models for parsing and validating YAML input:

```python
# cruiseplan/config/cruise_config.py
class CruiseConfig(BaseModel):
    cruise_name: str
    description: Optional[str] = None
    default_vessel_speed: float  # knots
    default_distance_between_stations: float  # km
    turnaround_time: float  # minutes
    departure_port: Optional[Union[str, PointDefinition]] = None
    arrival_port: Optional[Union[str, PointDefinition]] = None
    points: Optional[List[PointDefinition]] = None
    legs: Optional[List[LegDefinition]] = None
    # ... more fields; see cruise_config.py


class LegDefinition(BaseModel):
    name: str
    departure_port: Union[str, PointDefinition]  # required
    arrival_port: Union[str, PointDefinition]  # required
    activities: Optional[List[Union[str, dict]]] = None
    vessel_speed: Optional[float] = None  # knots; inherits from cruise
    delay_start: Optional[float] = None  # minutes
    buffer_time: Optional[float] = None  # minutes
    ordered: Optional[bool] = None
    clusters: Optional[List[ClusterDefinition]] = None


# cruiseplan/config/activities.py
class PointDefinition(FlexibleLocationModel):
    name: str
    operation_type: Optional[OperationTypeEnum] = None
    action: Optional[ActionEnum] = None
    operation_depth: Optional[float] = None  # metres
    water_depth: Optional[float] = None  # metres
    duration: Optional[float] = None  # minutes
    delay_start: Optional[float] = None  # minutes
    delay_end: Optional[float] = None  # minutes
    equipment: Optional[str] = None


class LineDefinition(BaseModel):
    name: str
    route: List[GeoPoint]
    vessel_speed: Optional[float] = None
    distance_between_stations: Optional[float] = None  # km
    max_depth: Optional[float] = None  # metres


class AreaDefinition(BaseModel):
    name: str
    corners: List[GeoPoint]
    duration: Optional[float] = None  # minutes; required for area ops
```

### Runtime layer (`cruiseplan/runtime/`)

Objects used during scheduling. Built from the config layer via factory methods.

```python
# cruiseplan/runtime/cruise.py
class CruiseInstance:
    def __init__(
        self, config_path: Union[str, Path]
    ): ...  # loads YAML, validates, builds runtime leg/cluster/operation tree


# cruiseplan/runtime/organizational.py
class Leg(BaseOrganizationUnit):
    @classmethod
    def from_definition(cls, leg_def: LegDefinition) -> "Leg": ...

    def get_vessel_speed(self, default_speed: float) -> float: ...
    def get_entry_point(self) -> tuple[float, float]: ...  # (lat, lon)
    def get_exit_point(self) -> tuple[float, float]: ...


class Cluster(BaseOrganizationUnit):
    @classmethod
    def from_definition(cls, cluster_def: ClusterDefinition) -> "Cluster": ...


# cruiseplan/runtime/operations.py
class PointOperation(BaseOperation):
    @classmethod
    def from_pydantic(cls, obj: PointDefinition) -> "PointOperation": ...


class LineOperation(BaseOperation):
    @classmethod
    def from_pydantic(
        cls, obj: LineDefinition, default_speed: float
    ) -> "LineOperation": ...


class AreaOperation(BaseOperation):
    @classmethod
    def from_pydantic(cls, obj: AreaDefinition) -> "AreaOperation": ...
```

### Timeline layer (`cruiseplan/timeline/`)

Distance and duration calculations, schedule generation.

```python
# cruiseplan/timeline/distance.py
def haversine_distance(start: tuple[float, float], end: tuple[float, float]) -> float:
    """Returns distance in kilometres (great circle)."""


# cruiseplan/timeline/duration.py
class DurationCalculator:
    def calculate_ctd_time(self, depth: float) -> float:
        """Depth-based CTD timing: descent + ascent + turnaround."""

    def calculate_transit_time(
        self, distance_km: float, speed_knots: float | None = None
    ) -> float:
        """Route-based transit timing with unit conversion."""


# cruiseplan/timeline/scheduler.py
def generate_timeline(
    cruise: CruiseInstance, legs: list[Leg] | None = None
) -> list[dict]: ...
```

## Entry/exit point interface

All operation types and organisational levels implement `get_entry_point()` and
`get_exit_point()`, returning `(latitude, longitude)` tuples. This lets the
scheduler calculate transit distances without knowing the operation type:

```python
def calculate_transit_distance(from_entity, to_entity) -> float:
    start = from_entity.get_exit_point()
    end = to_entity.get_entry_point()
    return haversine_distance(start, end)
```

`PointOperation`: entry == exit (same location).
`LineOperation`: entry = first waypoint, exit = last waypoint.
`AreaOperation`: entry = first corner, exit = last corner.
`Leg`: entry = departure port, exit = arrival port.

## Adding a new operation type

1. Add a Pydantic definition class in `cruiseplan/config/activities.py` (inherit `BaseModel`).
2. Add a runtime class in `cruiseplan/runtime/operations.py` (inherit `BaseOperation`).
3. Implement `from_pydantic()`, `get_entry_point()`, `get_exit_point()`, `calculate_duration()`.
4. Add duration logic to `DurationCalculator` in `cruiseplan/timeline/duration.py`.
5. Add the new type to `OperationTypeEnum` in `cruiseplan/config/values.py`.

## Coordinate input formats

`FlexibleLocationModel` (in `cruiseplan/config/activities.py`) normalises multiple
input formats to internal decimal-degree fields:

```yaml
# Decimal degrees (preferred)
latitude: 60.2440
longitude: -31.3177

# Degrees decimal minutes
latitude_decmin: "60 14.640 N"
longitude_decmin: "031 19.062 W"
```

Both produce the same `latitude`/`longitude` after `model_validator` runs.

## Exceptions

```python
# cruiseplan/config/exceptions.py
class ValidationError(Exception): ...  # YAML field validation failures


class FileError(Exception): ...  # File I/O problems


class BathymetryError(Exception): ...  # Bathymetry data issues


# cruiseplan/config/yaml_io.py
class YAMLIOError(Exception): ...  # YAML read/write errors


# cruiseplan/runtime/organizational.py
class ReferenceError(Exception): ...  # Unresolved port or activity references
```

## FlexibleLocationModel

`FlexibleLocationModel` stores `latitude` and `longitude` as plain float fields;
`latitude_decmin` / `longitude_decmin` are converted to them in a `before`
model validator. `GeoPoint` is used only for line routes and area corners.
A legacy `position: "lat, lon"` string is still accepted and is scheduled for
removal.

## Testing

```bash
pip install -e ".[test]"  # test dependencies only (as in CI)
pytest tests/unit/        # fast unit tests
pytest tests/integration/ # end-to-end workflow tests
pytest -m "not slow" --cov=cruiseplan --cov-fail-under=70  # CI coverage gate
ruff check . && ruff format --check .                      # CI lint job
```

Coverage reporting is on by default (`addopts` in `pyproject.toml`). CI runs
the tests on Ubuntu with Python 3.11, 3.12 and 3.13, plus macOS and Windows
with Python 3.11.

Test fixtures (realistic YAML configs) live in `tests/fixtures/`.

## Dependencies

- Core: Python 3.11+, Pydantic v2, ruamel.yaml, numpy, scipy, xarray, netCDF4, pandas, requests, pangaeapy
- Maps: matplotlib (PNG maps and the interactive station picker), folium, geopandas (EEZ overlays)
- Testing: pytest, pytest-cov — the `test` extra (`pip install -e ".[test]"`)
- Development: the `test` extra plus ruff, mypy, sphinx and notebook tooling — the `dev` extra (`pip install -e ".[dev]"`)
