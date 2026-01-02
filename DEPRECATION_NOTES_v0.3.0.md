# Deprecation Notes for v0.3.0 Release

This document tracks deprecated CLI commands and test files that will be removed in v0.3.0.

## Commands to be Removed in v0.3.0

### 1. `cruiseplan download` → `cruiseplan bathymetry`
- **Status**: Deprecated in current version, shows warning
- **Replacement**: `cruiseplan bathymetry`
- **Migration**: `--bathymetry-source` → `--bathy-source`

**Example Migration:**
```bash
# Old (deprecated)
cruiseplan download --bathymetry-source gebco2025

# New
cruiseplan bathymetry --bathy-source gebco2025
```

### 1b. `cruiseplan bathymetry --source` → `--bathy-source`
- **Status**: Parameter name updated for consistency
- **Deprecated Parameter**: `--source` (in bathymetry command)
- **Replacement**: `--bathy-source`
- **Migration**: Consistent with process command naming

**Example Migration:**
```bash
# Old (deprecated)
cruiseplan bathymetry --source gebco2025

# New
cruiseplan bathymetry --bathy-source gebco2025
```

### 2. `cruiseplan pandoi` → `cruiseplan pangaea` (search mode)
- **Status**: Deprecated in current version, shows warning  
- **Replacement**: `cruiseplan pangaea` with search parameters
- **Migration**: Same parameters, different command name

**Example Migration:**
```bash
# Old (deprecated)
cruiseplan pandoi "CTD temperature" --lat 50 60 --lon -50 -30

# New
cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -30
```

### 3. `--output-file` parameter → `--output` base filename
- **Status**: Deprecated across multiple commands
- **Replacement**: `--output` (base filename) + `--output-dir` (directory)
- **Migration**: Base filename strategy instead of full paths

**Example Migration:**
```bash
# Old (deprecated)  
cruiseplan pangaea dois.txt --output-file /path/to/stations.pkl

# New
cruiseplan pangaea dois.txt --output-dir /path/to --output stations
# → Generates: /path/to/stations_stations.pkl
```

### 4. Bathymetry parameter consolidation in `cruiseplan process`
- **Status**: New command with shortened parameter names
- **Deprecated Parameters**: `--bathymetry-source`, `--bathymetry-dir`, `--bathymetry-stride`
- **Replacement Parameters**: `--bathy-source`, `--bathy-dir`, `--bathy-stride`
- **Migration**: Shorter parameter names for reduced typing

**Example Migration:**
```bash
# Old (deprecated)
cruiseplan process -c cruise.yaml --bathymetry-source gebco2025 --bathymetry-dir data/bathy --bathymetry-stride 5

# New
cruiseplan process -c cruise.yaml --bathy-source gebco2025 --bathy-dir data/bathy --bathy-stride 5
```

### 5. Coordinate format deprecation in `cruiseplan process`
- **Status**: Fixed coordinate format, no longer configurable
- **Deprecated Parameter**: `--coord-format`
- **Replacement**: Fixed to DMM format (degrees decimal minutes)
- **Migration**: Remove parameter, format automatically uses DMM

**Example Migration:**
```bash
# Old (deprecated)
cruiseplan process -c cruise.yaml --coord-format dmm

# New (coord format is always DMM)
cruiseplan process -c cruise.yaml
```

### 6. Bathymetry parameter consolidation in `cruiseplan map`
- **Status**: Parameter names updated for consistency with other commands
- **Deprecated Parameters**: `--bathymetry-source`, `--bathymetry-dir`, `--bathymetry-stride`, `--output-file`
- **Replacement Parameters**: `--bathy-source`, `--bathy-dir`, `--bathy-stride`, `--output`
- **Migration**: Shorter parameter names and base filename strategy

**Example Migration:**
```bash
# Old (deprecated)
cruiseplan map -c cruise.yaml --bathymetry-source gebco2025 --bathymetry-dir data/bathy --bathymetry-stride 3 --output-file /path/to/cruise_map.png

# New
cruiseplan map -c cruise.yaml --bathy-source gebco2025 --bathy-dir data/bathy --bathy-stride 3 --output-dir /path/to --output cruise_map
```

### 7. LegDefinition Deprecated Fields
- **Status**: Deprecated fields in YAML configuration, warnings issued when used
- **Deprecated Fields**: `sequence`, `stations`, `sections` in LegDefinition
- **Replacement**: `activities` field for unified activity management
- **Migration**: Convert leg definitions to use activities list

**Example Migration:**
```yaml
# Old (deprecated) - will show warnings and be removed in v0.3.0
legs:
  - name: "Main_Survey"
    departure_port: "port_reykjavik"
    arrival_port: "port_bergen"
    sequence: [STN_001, Transit_01, STN_002]  # ← DEPRECATED
    stations: [STN_003, STN_004]             # ← DEPRECATED
    sections: [Section_01]                    # ← DEPRECATED

# New (recommended) - use activities field
legs:
  - name: "Main_Survey" 
    departure_port: "port_reykjavik"
    arrival_port: "port_bergen"
    activities: [STN_001, Transit_01, STN_002, STN_003, STN_004, Section_01]
```

**Implementation Status:**
- ✅ Deprecation warnings added in scheduler.py when deprecated fields are used
- ✅ Warning message indicates removal in v0.3.0
- ✅ Scheduler priority updated: leg.activities → leg.clusters → leg.sequence → leg.stations
- ❌ Full activities-only architecture not yet implemented (see CLAUDE-activities.md)

## Test Files to be Removed in v0.3.0

### ❌ Complete Removal Required

1. **`tests/unit/test_cli_download.py`**
   - **Reason**: Tests deprecated `cruiseplan download` command
   - **Replacement**: `tests/unit/test_cli_bathymetry.py` (already created)
   - **Action**: Delete entire file in v0.3.0

2. **`tests/unit/test_cli_pandoi.py`**
   - **Reason**: Tests deprecated `cruiseplan pandoi` command  
   - **Replacement**: Functionality moved to unified `tests/unit/test_cli_pangaea.py`
   - **Action**: Delete entire file in v0.3.0

3. **`cruiseplan/cli/download.py`**
   - **Reason**: Deprecated command implementation
   - **Replacement**: `cruiseplan/cli/bathymetry.py`
   - **Action**: Delete file in v0.3.0

4. **`cruiseplan/cli/pandoi.py`** 
   - **Reason**: Deprecated command implementation
   - **Replacement**: Functionality in unified `cruiseplan/cli/pangaea.py`
   - **Action**: Delete file in v0.3.0

5. **`cruiseplan/cli/pangaea_legacy.py`**
   - **Reason**: Backup of original pangaea.py before unification
   - **Replacement**: N/A (was temporary backup)
   - **Action**: Delete file in v0.3.0

### ⚠️ Modification Required

5. **`tests/unit/test_cli_pangaea.py`** (if exists)
   - **Reason**: Tests need updating for unified command
   - **Action**: Update tests to cover both search and DOI file modes
   - **Status**: Need to create comprehensive tests for unified pangaea command

6. **Integration tests referencing deprecated commands**
   - **Action**: Update any integration tests to use new command names
   - **Files to check**: `tests/integration/*.py`

## CLI Parser Updates for v0.3.0

### Remove Deprecated Subcommands from main.py

```python
# Remove these sections entirely:
# - download_parser (lines ~167-204)  
# - pandoi_parser (lines ~603-647)

# Remove these dispatch cases:
# - elif args.subcommand == "download": (lines ~570-577)
# - elif args.subcommand == "pandoi": (lines ~688-698)
```

### Remove Deprecated Parameters

```python
# Remove from pangaea_parser:
pangaea_parser.add_argument(
    "--output-file",  # ← Remove this entirely
    type=Path,
    help="[DEPRECATED] ...",
)

# Remove from process_parser (these will be legacy by v0.3.0):
process_parser.add_argument(
    "--bathymetry-source", dest="bathy_source_legacy",  # ← Remove entirely
    choices=["etopo2022", "gebco2025"],
    help="[DEPRECATED] Use --bathy-source instead"
)
process_parser.add_argument(
    "--bathymetry-dir", type=Path, dest="bathy_dir_legacy",  # ← Remove entirely
    help="[DEPRECATED] Use --bathy-dir instead"
)
process_parser.add_argument(
    "--bathymetry-stride", type=int, dest="bathy_stride_legacy",  # ← Remove entirely
    help="[DEPRECATED] Use --bathy-stride instead"
)
process_parser.add_argument(
    "--coord-format", dest="coord_format_legacy",  # ← Remove entirely
    choices=["dmm", "dms"],
    help="[DEPRECATED] Coordinate format fixed to DMM"
)

# Remove from map_parser (these will be legacy by v0.3.0):
map_parser.add_argument(
    "--bathymetry-source", dest="bathymetry_source_legacy",  # ← Remove entirely
    choices=["etopo2022", "gebco2025"],
    help="[DEPRECATED] Use --bathy-source instead"
)
map_parser.add_argument(
    "--bathymetry-dir", type=Path, dest="bathymetry_dir_legacy",  # ← Remove entirely
    help="[DEPRECATED] Use --bathy-dir instead"
)
map_parser.add_argument(
    "--bathymetry-stride", type=int, dest="bathymetry_stride_legacy",  # ← Remove entirely
    help="[DEPRECATED] Use --bathy-stride instead"
)
```

## Backward Compatibility Testing

### Pre-v0.3.0 Testing Checklist
- [ ] `cruiseplan download` shows deprecation warning
- [ ] `cruiseplan download` functionally equivalent to `cruiseplan bathymetry`
- [ ] `cruiseplan pandoi` shows deprecation warning  
- [ ] `cruiseplan pandoi` functionally equivalent to `cruiseplan pangaea` search mode
- [ ] `--output-file` shows deprecation warning across commands
- [ ] All deprecated functionality still works during transition

### v0.3.0 Release Checklist
- [x] Remove deprecated command tests: `test_cli_download.py`, `test_cli_pandoi.py`  
- [x] Remove deprecated command modules: `download.py`, `pandoi.py`  
- [x] Remove deprecated subcommand parsers from `main.py`
- [x] Remove deprecated parameter support from commands
- [x] Fixed output naming conventions and filename conflicts  
- [x] Fixed CLI-API parameter mismatches
- [x] Fixed HTML schedule map embedding
- [x] Updated documentation to remove deprecated examples and command references
- [x] Removed deprecated command documentation files
- [x] Verified deprecated commands return proper "command not found" errors
- [ ] Update CLI help text to remove deprecated options (main help updated automatically)

## Migration Documentation

When removing deprecated commands, ensure migration documentation includes:

1. **Clear before/after examples** for each deprecated command
2. **Parameter mapping tables** showing old → new parameter names
3. **Script migration guides** for automated conversion of existing workflows  
4. **Breaking changes changelog** with migration timeline
5. **Version compatibility matrix** showing supported features per version

## v0.3.0 Implementation Checklist

### Code Removal Tasks
- [x] Remove `cruiseplan/cli/download.py` module
- [x] Remove `cruiseplan/cli/pandoi.py` module
- [x] Remove `cruiseplan/cli/pangaea_legacy.py` module (if exists)
- [x] Remove deprecated parsers from `cruiseplan/cli/main.py`:
  - [x] Remove `download_parser` section
  - [x] Remove `pandoi_parser` section
  - [x] Remove dispatch cases for deprecated commands
- [x] Remove deprecated parameter support from all commands:
  - [x] Remove `--bathymetry-*` parameters (use `--bathy-*`)
  - [x] Remove `--output-file` parameters (use `--output`)
  - [x] Remove `--coord-format` parameter (fixed to DMM)
- [x] Remove test files:
  - [x] Remove `tests/unit/test_cli_download.py`
  - [x] Remove `tests/unit/test_cli_pandoi.py`

### Documentation Updates
- [x] Update `docs/PROJECT_SPECS.md` to remove deprecated commands/parameters
- [x] Update `CLAUDE-old.md` to remove deprecated commands
- [x] Update `CLAUDE-testing.md` to remove deprecated commands  
- [x] Update `docs/screenshots_needed.md` to remove download command
- [x] Fixed HTML schedule map embedding (HTML generator now correctly links to PNG files)
- [x] Updated CHANGELOG.md with all recent fixes and improvements
- [x] Updated output naming conventions documentation
- [x] Removed deprecated command documentation files (`cli/download.rst`, `cli/pandoi.rst`)
- [x] Updated CLI reference to remove deprecated commands and examples
- [x] Updated workflow examples to use v0.3.0 syntax with current parameter names
- [ ] Update CLI reference for KML command move (schedule → map)
- [ ] Update user workflows for breaking changes
- [ ] Complete CRITICAL documentation updates from CLAUDE-docs-update.md
- [ ] **Comprehensive documentation scan for v0.3.0 updates**:
  - [ ] Check all files in `docs/source/api/` for deprecated parameter references
  - [x] Check all files in `docs/source/cli/` for deprecated command references
  - [x] Update any remaining references to removed commands (`cruiseplan download`, `cruiseplan pandoi`)
  - [x] Update examples and code snippets to use current v0.3.0 syntax
  - [ ] Update any remaining parameter references (`--output-file`, `--bathymetry-*`, `--coord-format`)
  - [ ] Verify workflow diagrams or command flow documentation

### YAML Configuration Changes
- [ ] Clarify global field usage rules:
  - [ ] Global fields are permitted and some are required (cruise_name, vessel, etc.)
  - [ ] Global fields like `departure_port`, `arrival_port`, `first_waypoint`, `last_waypoint` are allowed for single-leg cruises
  - [ ] Multi-leg cruises require these fields to be specified at the leg level for each leg
  - [ ] Update validation to enforce this single-leg vs multi-leg distinction
- [ ] Update examples to show both single-leg (global fields OK) and multi-leg (leg-level required) patterns

### Testing & Validation
- [x] Run full test suite after each removal
- [x] Update integration tests to use new commands
- [x] Verify error messages for removed commands
- [x] Test migration examples work correctly (`test_all_fixtures.py` updated)
- [x] Fixed output file naming consistency across all CLI commands
- [x] Fixed parameter mismatch issues between CLI and API layers
- [ ] **Achieve 80% test coverage across the board before v0.3.0 release**
  - [ ] Combination of unit tests and integration tests to reach coverage target
  - [ ] Focus on critical CLI functionality and API endpoints
  - [ ] Document any uncovered code that is intentionally excluded

### Demo and Documentation Enhancements
- [ ] **Consider implementing demo.py CLI demonstration script**
  - [ ] Pattern after demo.ipynb but adapted for command-line usage
  - [ ] Showcase complete workflow: bathymetry → stations → enrich → validate → schedule
  - [ ] Include realistic data examples and output generation
  - [ ] Demonstrate both single-leg and multi-leg cruise scenarios
  - [ ] **Location**: Root directory alongside demo.ipynb
  - [ ] **Purpose**: Easy CLI workflow demonstration without Jupyter dependency

### Refactoring Opportunities Identified
- [x] Consolidate CLI parameter handling utilities (completed via `_resolve_cli_to_api_params`)
- [x] Standardize output path logic across commands (completed via `_standardize_output_setup`) 
- [x] Remove duplicate bathymetry parameter validation (consolidated in `input_validation.py`)
- [x] Unify error message formatting (completed via `_format_cli_error`)
- [x] Fixed cruise name extraction for consistent naming across commands
- [ ] Standardize CLI flag ordering in help output across all commands

### CLI Flag Ordering Standardization
- [ ] Implement consistent flag ordering in `cruiseplan <subcommand> --help` output
- [ ] Follow argparse conventions or establish consistent relative order
- [ ] **Files to update for flag ordering**:
  - [ ] `cruiseplan/cli/main.py` - All subcommand parsers (lines ~120-750)
  - [ ] `cruiseplan/cli/enrich.py` - Standalone parser (lines ~290-312)
  - [ ] `cruiseplan/cli/stations.py` - Standalone parser (lines ~250-280)
  - [ ] `cruiseplan/cli/pangaea.py` - Argument processing (if any custom ordering)
- [ ] **Suggested ordering convention**:
  1. Required positional arguments
  2. Required named arguments (-c, --config-file)
  3. Primary options (-o, --output-dir, --output)
  4. Feature flags (--expand-ports, --add-depths, etc.)
  5. Behavioral options (--format, --algorithm, etc.)
  6. Source/input options (--bathy-source, --bathy-dir, etc.)
  7. Advanced/debugging options (--verbose, --quiet, --rate-limit)
  8. Help option (--help) - handled automatically by argparse

### Roadmap Updates
- [ ] Update `roadmap.rst` to mark v0.3.0 items as completed
- [ ] Add note about conftest.py output paths for future testing improvements

## Timeline

- **Current Version**: Deprecated commands show warnings but remain functional
- **v0.3.0 Release**: Complete removal of deprecated commands and test files
- **v0.3.0+**: Only new command names and parameters supported

## Notes for Maintainers

- Always run full test suite before removing any files
- Ensure new unified tests provide equivalent or better coverage than removed tests
- Update CI/CD pipelines to reflect removed test files
- Check documentation build process for references to deprecated commands
- Verify example scripts in documentation use new command syntax