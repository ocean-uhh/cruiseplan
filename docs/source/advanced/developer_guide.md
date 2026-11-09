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
    description: str | None = None
    default_vessel_speed_kt: float  # knots
    default_distance_between_stations_km: float  # km
    turnaround_time_minutes: float  # minutes
    departure_port: str | PointDefinition | None = None
    arrival_port: str | PointDefinition | None = None
    points: list[PointDefinition] | None = None
    legs: list[LegDefinition] | None = None
    # ... more fields; see cruise_config.py


class LegDefinition(BaseModel):
    name: str
    departure_port: str | PointDefinition  # required
    arrival_port: str | PointDefinition  # required
    activities: list[str | dict] | None = None
    vessel_speed_kt: float | None = None  # knots; inherits from cruise
    delay_start_minutes: float | None = None  # minutes
    buffer_time_minutes: float | None = None  # minutes
    ordered: bool | None = None
    clusters: list[ClusterDefinition] | None = None


# cruiseplan/config/activities.py
class PointDefinition(FlexibleLocationModel):
    name: str
    operation_type: OperationTypeEnum | None = None
    action: ActionEnum | None = None
    operation_depth_m: float | None = None  # metres
    water_depth_m: float | None = None  # metres
    duration_minutes: float | None = None  # minutes
    delay_start_minutes: float | None = None  # minutes
    equipment: str | None = None


class LineDefinition(BaseModel):
    name: str
    route: list[GeoPoint]
    vessel_speed_kt: float | None = None
    distance_between_stations_km: float | None = None  # km
    max_depth: float | None = None  # metres


class AreaDefinition(BaseModel):
    name: str
    corners: list[GeoPoint]
    duration_minutes: float | None = None  # minutes; required for area ops
```

### Runtime layer (`cruiseplan/runtime/`)

Objects used during scheduling. Built from the config layer via factory methods.

```python
# cruiseplan/runtime/cruise.py
class CruiseInstance:
    def __init__(
        self, config_path: str | Path
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
) -> Timeline: ...


# cruiseplan/timeline/record.py
@dataclass(frozen=True, kw_only=True, slots=True)
class ActivityRecord:
    kind: str  # station, mooring, line, area, transit, port, buffer, wait
    label: str
    start_time: datetime  # UTC, no zone attached
    end_time: datetime
    duration_minutes: float  # actual (end - start)
    planned_duration_minutes: float  # from the planning rules
    dist_nm: float
    vessel_speed_kt: float
    water_depth_m: float | None = None
    operation_depth_m: float | None = None
    delay_start_minutes: float | None = None
    # ... more fields; see record.py


Timeline = list[ActivityRecord]
```

Writers (CSV, HTML, LaTeX, KML, NetCDF, maps) and the forecast take records
and read attributes. `record.kind` replaces classification by label text.

## Deprecations

Renamed YAML keys and API names live in one table each in
`cruiseplan/_deprecated.py`, with the release that removes them
(`REMOVED_IN`). The configuration loader (`cruiseplan/config/loader.py`)
renames old keys before validation and warns once per key per file. A test
fails once the package version reaches `REMOVED_IN`, and another checks the
migration page against the tables.

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

## Code conventions

`ruff check .` and `ruff format --check .` are the CI lint job; the rule set in
`pyproject.toml` covers numpy docstrings, annotations, import order and Python
3.11 syntax (`list[str]`, `T | None`).

- **Docstrings**: numpy style on every public function and class, with typed
  `Parameters`, `Returns` and `Raises` sections. A private helper (leading
  underscore) has a one-line docstring and a typed signature; a reason the code
  cannot show goes in a `#` comment at the line it explains.
- **Logging**: library modules log through `logging.getLogger(__name__)` and
  never configure logging (no `logging.basicConfig`, no handlers) or `print`.
  The `cruiseplan` command line configures logging once. An API function's
  `verbose=True` sets the `cruiseplan` logger to DEBUG for that call only.
  Log messages are plain text, without emoji. Results meant for the terminal
  (tables, summaries) are printed by the modules in `cruiseplan/cli/`.

### Naming

Public names are spelling-neutral: never a word spelled differently in British
and American English (`-ise`/`-ize`, `-isation`/`-ization`). Say what the
function makes instead:

| Pattern | Returns | Example |
|---|---|---|
| `to_<form>(obj)` | the object converted to another form | `to_canonical_units(ds)`, not `canonicalise_units` |
| `canonical_<thing>(value)` | the one accepted form of a string | `canonical_role(value)`, not `normalize_role` |
| noun | a computed result | `warning_summary(…)`, not `summarise_warnings` |

Private names follow the same rule; where no neutral word exists the spelling is
American, as in Python and matplotlib (`color` and `gray` are never renamed).
Prefer naming the job over finding a synonym (`_rename_`, `_fix_`,
`_canonical_` rather than `_normalize_`, `_sanitize_`). A private helper's name
says what comes back, with one verb per job:

| Verb | Returns |
|---|---|
| `_read_<what>(path)` | an object read from a file |
| `_parse_<what>(text)` | a typed value from a string in hand, no I/O |
| `_resolve_<what>(…)` | the one value that applies, from several sources by precedence |
| `_format_<what>(value)` | a display string |
| `_build_<what>(…)` | rows, a dict or a dataset |
| `_render_<what>(…)` | an HTML or LaTeX fragment |
| `_draw_<what>(…)` | a matplotlib Figure (public: `draw_<what>`) |
| `_has_<what>` / `_is_<what>` | a bool |
| `_apply_<what>(obj, …)` | the object after one processing step |
| `_add_<what>(…)` | the target with fields or attributes added |
| noun (`_positive_depth`) | a computed result |

Module names say what the module holds or does (`scheduler.py`,
`bathymetry.py`, `kml_generator.py`). Do not add modules named for a grade of
code (`*_utils.py`, `helpers.py`, `misc.py`); the existing `*_utils.py` modules
are not a pattern to copy.

## Testing

Tests write only into `tmp_path` (or the `temp_output_dir` fixture): a test run
leaves the repository tree unchanged. Pass an explicit output directory to any
API call that writes files, since the default is `data/`.

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
