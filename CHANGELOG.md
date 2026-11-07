# Changelog

All notable changes to this project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Breaking changes

Old names keep working until 0.7.0, with a warning. See the migration page, `docs/source/migrating_0_6_0.rst` ("Upgrading from 0.5 to 0.6" in the documentation), for every renamed name.

- YAML keys name their unit: `duration_minutes`, `delay_start_minutes`, `buffer_time_minutes`, `turnaround_time_minutes`, `water_depth_m`, `operation_depth_m`, `vessel_speed_kt`, `default_vessel_speed_kt`, `distance_between_stations_km`, `default_distance_between_stations_km`, `ctd_descent_rate_m_s`, `ctd_ascent_rate_m_s`. The old keys are read with one warning per key per file until 0.7.0; `enrich` writes the new keys.
- `delay_end` is removed: it was never read. It is ignored with a warning naming `delay_start_minutes`, `buffer_time_minutes` and `duration_minutes`.
- Timelines are lists of frozen `ActivityRecord` objects (`cruiseplan.Timeline`), not dictionaries; reading a record like a dictionary warns until 0.7.0. `CruiseSchedule` is a deprecated alias of `Timeline`. Records have `kind`, `planned_duration_minutes`, and `water_depth_m`, `operation_depth_m`, `delay_start_minutes` (renamed).
- NetCDF schedule: `duration` in minutes (was hours, now the actual duration) plus `planned_duration`; `dist_nm` renamed `distance`; times CF-encoded UTC seconds; every numeric variable has a UDUNITS-2 `units`. Files written by 0.5.0 still read in `list` and `forecast` until 0.7.0.
- Unknown YAML keys warn (one warning per key per file); they are rejected in the release after 0.6.0. An activity listed twice in a leg warns (it is still scheduled twice).
- `forecast` anchored on a transit row starts that transit at `--start-time` (it started the operation after it).

### Fixed

- A leg's `turnaround_time_minutes` was read but CTD casts always used the cruise value; the leg value now applies to its casts.
- The schedule total (CLI, HTML, result summary) left out waiting from positive `delay_start_minutes`; it is the elapsed time.
- CSV times were truncated to the minute; they are rounded to the nearest minute (TeX plans keep 10 minutes).
- Line records reported the cruise speed instead of the line's own speed.
- An operation's positive `delay_start_minutes` is waiting before it: a row "Waiting before <name>" (kind `wait`) at the operation's position, so no other record gets longer. A negative one means the operation started earlier: it comes out of the transit into it, then out of the operation before that transit, never below 0 min, and always warns that it is a quick fix (`transit_minutes` or `duration_minutes` on the record that was shorter says what happened). When the leg start is reached, the leg is not moved and the warning says how to start the leg earlier (the cruise `start_date`/`start_time` for the first leg; otherwise the leg's `delay_start_minutes` or the end of the previous leg). Records neither overlap nor leave gaps (`duration_minutes` actual, `planned_duration_minutes` planned), the durations add up to the elapsed time apart from leg delays, and the forecast uses the same records. Schedules written before 0.6.0 keep their rows: a positive delay stays a gap, a negative one shortens the transit before the operation.
- Enriched values (`bathymetry_source`, decimal-minute strings, `bathymetry_provenance`) are declared model fields; enrich no longer writes through `__dict__`.

- `forecast --current-position` changed only the waypoints header line. It now adds a transit from that position to the anchored operation at the leg speed, so the times change in every format (text, tex, waypoints, kml, png); the ship position itself is marked in the text and waypoints outputs only.
- `forecast --current-position -74.62,164.30` (negative first coordinate after a space) was rejected as an unknown option; that form, `lat lon` as two values of any sign (`65.0 -30.0`, `65.0 30.0`) and the `=` form all parse.
- TeX plan: a time rounded past midnight (23:56 → 00:00) is printed under the next day.
- Waypoints without `--start-time` at 23:55 or later started at 00:00 of the same day; the rounding carries into the date.
- Forecast rows overlapped where an operation has a negative `delay_start`; the transit before the operation is now shorter instead, as in the schedule.
- KML forecast had no placemarks (records lacked the fields the KML writer reads).
- A forecast window with no operation in it (only a transit) wrote an empty plan; every format now stops with an error naming the window.
- `--current-position` within 0.05 nm of the anchored operation inserted a zero-length transit; it is skipped.
- Times in the TeX, waypoints, KML and CSV outputs are rounded on the full time, halves up (12:05 → 12:10 in the 10-minute TeX tables; 12:00:30 → 12:01 elsewhere). Before, seconds were dropped and Python's half-to-even rounding was used, so regenerated tables of an unchanged schedule can differ by one step. The TeX time column is labelled UTC.
- `forecast --format tex` prints ship time when `--start-time` carries the ship's zone (`2026-08-30T14:00+03:00`): the rows are in that local time and the time column reads `LT (UTC+03:00)`. Without a zone the table is in UTC and says so (it said `LT` whatever the times were).
- `forecast --start-time` is UTC: a time with a zone is converted, a time without one is taken as UTC; waypoints without `--start-time` start from the current UTC time. Forecast times are whole seconds (no "Discarding nonzero nanoseconds" warning).
- NetCDF schedule stores `delay_start` (minutes) so it round-trips; files without it still read.

- Missing, partial or unreadable bathymetry file: depth lookups return the fill value `-9999.0` (`DEFAULT_DEPTH`) with a WARNING naming the file and the `cruiseplan bathymetry` command, instead of formula ("mock") depths. Maps are drawn without bathymetry. Mock mode removed.
- A requested bathymetry source is never silently switched for another dataset. When its file is missing the WARNING names the other sources present in the directory and the `--bathy-source` value to use one of them.
- A station over land (bathymetry elevation `>= 0`) was stored as a positive depth via `abs(elevation)`; it now gets the fill value `-9999.0` and a WARNING. Ocean depth is `-elevation`.
- Bathymetry grids stored north-to-south (descending latitude) returned the fill value for every point; the coordinate axes are flipped to ascending on load and indices are mapped back to the file on read.
- A fill-value depth printed as `-9999 m`/`-9999` in the LaTeX letsgo table and the HTML mooring table; both now show `fill`, as the other tables already did.
- `get_depth` returned a fill-value `operation_depth` in preference to a valid `water_depth`, and a mooring carrying an `operation_depth` was timed as a CTD cast; the fill value is skipped and moorings take the mooring-duration path.
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

- `cruiseplan.Timeline`, `cruiseplan.ActivityRecord` (`cruiseplan.timeline.record`): one frozen record type with `kind`, used by every writer and the forecast.
- `cruiseplan._deprecated`: one table each of renamed YAML keys, removed keys, record keys and API names, with the removal release; `cruiseplan.config.loader.prepare_config` applies it before validation.
- `transit_minutes` on a point, port, line or area: the actual minutes of the transit into it, replacing distance / speed (distance and positions unchanged; the transit's planned minutes are kept, and its vessel speed is shown as distance / `transit_minutes`). Ignored with a warning when there is no transit into the operation.
- Text and TeX forecasts state the anchoring rule applied (`% Anchor =` line, a line under the TeX title).

- `water_depth` accepts the fill value `-9999.0`; `enrich --add-depths` writes it where no depth can be looked up and retries it on the next run. The enriched YAML records `bathymetry_provenance` (source, file, found, depths from source, depths filled).
- Provenance in outputs: NetCDF global attributes (all files) `cruiseplan_version`, `source_config`, `source_config_sha256`, `bathymetry_source`, planning parameters and `date_created` (UTC, `Z`); the same fields as `%` comments at the top of the TeX tables and in a Provenance section of the HTML report.
- Fill-duration markers: `ActivityRecord.duration_is_fill`; NetCDF `duration_fill_flag` with `fill_duration_count`; CSV `Duration note` column; `(fill)` in HTML and TeX durations.
- `utils.coordinates.ddm_parts`, `utils.coordinates.distance_nm` (one haversine; the KML, LaTeX and timeline distances use it).
- `data.bathymetry.shared_bathymetry` and `get_bathymetry_manager`: `run` opens each bathymetry file once.
- Stations expanded from a line operation carry a `history` field recording their origin (the point model now has a `history` field).
- Fill-duration summary line (count, `N x 999 h`, and the schedule total excluding fills) in the WARNING log and at the top of the HTML and TeX reports, so the inflated fill hours do not hide the real total.

### Changed

- Documentation: units table in the YAML reference; `buffer_time_minutes` is applied (one block per leg after the last operation, before the transit to the arrival port), not "stored only"; `turnaround_time_minutes` is added to depth-based CTD casts only; migration page for 0.6.0.
- Test fixture `coldsnap-2028-newformat.yaml` (every activity listed twice) is kept as `coldsnap-2028-newformat_old.yaml`; `mooring_sequence_greenland.yaml` lists each activity once (84 rows, 377 h).
- `forecast --start-index`: the row at the index starts at `--start-time` (UTC). On an operation row the transit into it is not included; on a transit row the ship is starting that transit now (it is kept, starting at `--start-time`). With `--current-position` the position wins: a transit row moves to the operation it leads to, and `--start-time` is the time at that position. The text and TeX headers state the rule applied.

- NetCDF `creation_date` is UTC with `Z` (was naive local time).
- The library no longer configures logging: API functions do not call `logging.basicConfig` (it reset the caller's root handlers). The `cruiseplan` command line configures logging; `verbose=True` sets the `cruiseplan` logger to DEBUG for that call only. Scripts and notebooks that want the INFO messages configure logging themselves (`logging.basicConfig(level=logging.INFO)`).
- Bathymetry download and station-picker status messages go through `logging` instead of `print`. Log messages carry no emoji.

### Removed

- `CoordConverter.decimal_degrees_to_ddm` (did not carry 60 minutes into the degrees); use `utils.coordinates.ddm_parts`.
- `cruiseplan.timeline.routing` (`optimize_composite_route`, never called).
- `cruiseplan.utils.logging.configure_logging` and `get_logger`.
- `CONVENTIONS.md`; code conventions and naming are in the developer guide.

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
