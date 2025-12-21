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
- [ ] Remove deprecated command tests: `test_cli_download.py`, `test_cli_pandoi.py`
- [ ] Remove deprecated command modules: `download.py`, `pandoi.py`  
- [ ] Remove deprecated subcommand parsers from `main.py`
- [ ] Remove deprecated parameter support from commands
- [ ] Update documentation to remove deprecated examples
- [ ] Update CLI help text to remove deprecated options
- [ ] Test that deprecated commands return "command not found" errors

## Migration Documentation

When removing deprecated commands, ensure migration documentation includes:

1. **Clear before/after examples** for each deprecated command
2. **Parameter mapping tables** showing old → new parameter names
3. **Script migration guides** for automated conversion of existing workflows  
4. **Breaking changes changelog** with migration timeline
5. **Version compatibility matrix** showing supported features per version

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