# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- Missing, partial or unreadable bathymetry file: depth lookups return the fill value `-9999.0` (`DEFAULT_DEPTH`) with a WARNING naming the file and the `cruiseplan bathymetry` command, instead of formula ("mock") depths. Maps are drawn without bathymetry. Mock mode removed.
- `determine_bathymetry_source` no longer switches to another dataset; it returns the requested source and warns if its file is missing.
- `cruiseplan bathymetry --bathy-source gebco2023` downloaded ETOPO 2022. `gebco2023` is no longer a download choice (no download location); `download_bathymetry` raises `ValueError` for it and for unknown sources. It stays a lookup source for a hand-placed `GEBCO_2023.nc`.
- Enriched YAML dropped `start_date`, `start_time`, `default_vessel_speed`, `default_distance_between_stations`, CTD rates and day hours, so `run` scheduled from defaults (e.g. a 1970 start). It also wrote the ports catalog under `port:`.
- Mooring or yo-yo cast without `duration` got 60 min in `schedule` (from a config field that does not exist) and 999 h in `enrich`. A CTD without a usable depth and an operation type without a duration rule got 0 min. All now get the 999 h fill (`DEFAULT_MOORING_DURATION_MIN`), with one WARNING per operation.
- Degrees-decimal-minutes output did not carry (`59°60.00'`). One `utils.coordinates.ddm_parts` with carry is used by LaTeX, HTML, CSV, bridge waypoints, forecast text, YAML decmin fields and the station picker.
- LaTeX letsgo table chose the depth column by label text (`ctd`, `fd-`, `ds-`, …); it now uses the record kind.
- HTML report put activities with an unknown leg into the first leg; they are listed under an "Unassigned" heading with a WARNING.
- `Leg.get_operational_entry_point` / `get_operational_exit_point` imported a removed module; they resolve through `OperationFactory`.
- Depth validation treated `-9999` from the bathymetry as a 9999 m depth; the fill value is reported as unverifiable.
- Missing-bathymetry messages referred to a `cruiseplan download` command that does not exist.
- `data/pycnmix-2026-v1.yaml` referenced seven activities by site name; they now name the `_recovery` / `_deployment` points.

### Added

- `water_depth` accepts the fill value `-9999.0`; `enrich --add-depths` writes it where no depth can be looked up and retries it on the next run. The enriched YAML records `bathymetry_provenance` (source, file, found, depths from source, depths filled).
- Provenance in outputs: NetCDF global attributes (all files) `cruiseplan_version`, `source_config`, `source_config_sha256`, `bathymetry_source`, planning parameters and `date_created` (UTC, `Z`); the same fields as `%` comments at the top of the TeX tables and in a Provenance section of the HTML report.
- Fill-duration markers: `ActivityRecord.duration_is_fill`; NetCDF `duration_fill_flag` with `fill_duration_count`; CSV `Duration note` column; `(fill)` in HTML and TeX durations.
- `utils.coordinates.ddm_parts`, `utils.coordinates.distance_nm` (one haversine; the KML, LaTeX and timeline distances use it).
- `data.bathymetry.shared_bathymetry` and `get_bathymetry_manager`: `run` opens each bathymetry file once.

### Changed

- NetCDF `creation_date` is UTC with `Z` (was naive local time).

## [0.5.0] - 2026-11-02

### Breaking changes

- Python 3.10 is no longer supported; minimum is 3.11. Classifiers list 3.11–3.13.

### Added

- `CHANGELOG.md`; breaking-change notes moved here from the README.
- `test` optional-dependency group (pytest, pytest-cov, pyyaml); `dev` includes it.
- `cruiseplan.runtime.operations.DurationRules`: protocol for the rules object passed to `calculate_duration`.

### Changed

- Documentation updates: developer guide, YAML reference, workflows (#159).
- Dependencies declared in `pyproject.toml` only; CI gates coverage at 70 %; `CITATION.cff` at v0.4.0 (#169).
- CI: Ubuntu tests Python 3.11–3.13; macOS and Windows test 3.11 only; separate lint (`ruff check`, `ruff format --check`) and coverage jobs.
- Ruff ruleset aligned with the sibling packages (ctdcast): annotations, numpy docstrings with all parameters documented, pathlib, bugbear, blind-except. `cruiseplan/output` is now linted (an unanchored `output/` in `.gitignore` had excluded it).
- Re-raised errors carry the original exception as `__cause__`. Some broad `except Exception` blocks are narrowed (`OSError` for directory checks; `ValueError`/`TypeError` for NetCDF value and `start_time` parsing); other exception types from those calls now propagate instead of being wrapped or ignored.

### Removed

- `requirements.txt` and `requirements-dev.txt` (#169).
- Invalid `schedule.day` in the Dependabot config (#169).
- CI workaround for building `ruamel.yaml.clibz`; ruamel.yaml 0.19 only pulls it in through an optional extra.
- `environment.yml`; the docs workflows create their environment (Python, pip, pandoc) inline and install `.[dev]`.

## [0.4.0] - 2026-08-04

### Added

- `cruiseplan run` (#157), `cruiseplan list` (#149).
- Station plan for use on board, later renamed `forecast` (#82, #93); glider and yo-yo operations (#93).
- EEZ boundaries on interactive (#94) and static PNG maps (#154, #156).
- Map options `--max-depth`, `--no-title`, `--no-legend`, `--no-labels` (#108, #117).
- Multi-segment section expansion (#122).

### Changed

- Breaking: `cruiseplan stationplan` renamed to `cruiseplan forecast` (#149).
- Breaking: modules renamed `cruiseplan.schema` → `cruiseplan.config`, `cruiseplan.core` → `cruiseplan.runtime`, `cruiseplan.calculators` → `cruiseplan.timeline` (#66). Earlier README notes listed this under v0.3.6, which was never tagged.
- Breaking: package `__init__` modules no longer re-export; import from the defining module (#67).
- Breaking: minimum Python is 3.10 (#118).
- CLI rebuilt around `build_parser` + `run` with a positional config argument (#146); CLI and API defaults made consistent (#119, #120); shared error handler and verbose logging (#121); CLI output and `--format` cleanup (#145).
- CLI reference rewritten (#151, #153).

### Fixed

- Custom ports and leg-only schedules (#70).
- `distance_to_next` in the scheduler (#94).
- `buffer_time` handling (#152).

## [0.3.5] - 2026-01-17

### Changed

- `__init__.py` contents moved into the `cruiseplan.api` module (#63).
- `schema/` files renamed (#64).
- `cruiseplan stations` has an API counterpart (#65).

## [0.3.4] - 2026-01-12

### Changed

- Breaking: point/line/area keys and defaults extracted into `vocabulary.py` (#61).
- Canonical YAML structure (#62).

## [0.3.3] - 2026-01-11

### Changed

- Breaking: YAML uses `transects:` (was `transits:`) for line operations (#59) and `waypoints:` (was `stations:`) for point operations (#60).

## [0.3.2] - 2026-01-10

### Changed

- `enrich` and `validate` processing reorganized (#58); utils module reorganized (#56); further CLI abstraction (#55); validation module refactored (#53); ruff cleanup (#54).

## [0.3.1] - 2026-01-04

### Changed

- Unified point operation; outputs updated (#52).

### Fixed

- Scheduler bugs (#52).

## [0.3.0] - 2026-01-04

### Changed

- CLI separated from the API (#43, #44); validation and scheduler utilities refactored (#42).
- `position.latitude` replaced by `latitude`; `GeoPoint` / `FlexibleLocationModel` (#41).
- Breaking: bathymetry flags shortened `--bathymetry-*` → `--bathy-*` (#45).

### Removed

- Breaking: `cruiseplan download` and `cruiseplan pandoi` (#45).

## [0.2.2] - 2025-12-22

### Added

- Python API for notebook use, parallel to the CLI (#38).
- Cruises without explicit legs (#39).

## [0.2.1] - 2025-12-21

### Added

- `cruiseplan process` (#37).

### Fixed

- LaTeX generator bug (#37).

## [0.2.0] - 2025-12-20

### Added

- GEBCO 2025 bathymetry (#22); CTD section expansion (#24); buffer time (#25); DOI search (#28); map generators and demo notebook (#29, #34).

### Changed

- YAML handling switched from PyYAML to ruamel.yaml to preserve comments (#26).
- Timeline, activities and maps reworked (#30, #31).

## [0.1.0] - 2025-12-12

First release on PyPI.

[Unreleased]: https://github.com/ocean-uhh/cruiseplan/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/ocean-uhh/cruiseplan/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/ocean-uhh/cruiseplan/compare/v0.3.5...v0.4.0
[0.3.5]: https://github.com/ocean-uhh/cruiseplan/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/ocean-uhh/cruiseplan/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/ocean-uhh/cruiseplan/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/ocean-uhh/cruiseplan/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/ocean-uhh/cruiseplan/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/ocean-uhh/cruiseplan/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/ocean-uhh/cruiseplan/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/ocean-uhh/cruiseplan/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/ocean-uhh/cruiseplan/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ocean-uhh/cruiseplan/releases/tag/v0.1.0
