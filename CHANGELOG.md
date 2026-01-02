# Changelog

All notable changes to CruisePlan will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🚨 Breaking Changes (v0.3.0)

#### Removed Commands
- **REMOVED**: `cruiseplan download` command → Use `cruiseplan bathymetry`
- **REMOVED**: `cruiseplan pandoi` command → Use `cruiseplan pangaea`

#### Parameter Changes  
- **REMOVED**: `--bathymetry-source` → Use `--bathy-source`
- **REMOVED**: `--bathymetry-dir` → Use `--bathy-dir` 
- **REMOVED**: `--bathymetry-stride` → Use `--bathy-stride`
- **REMOVED**: `--output-file` → Use `--output` + `--output-dir`
- **REMOVED**: `--coord-format` → Fixed to DMM format

#### API Architecture Changes
- **BREAKING**: CLI commands now use API-first architecture
- **BREAKING**: Direct core module imports from CLI are deprecated
- **BREAKING**: Some internal function names changed (affects test mocking)

### 🎉 Added

#### New Commands
- **NEW**: `cruiseplan process` - Unified enrichment, validation, and map generation
- **ENHANCED**: `cruiseplan pangaea` - Unified command supporting both search and DOI file modes

#### New Features
- **NEW**: Smart parameter defaults in process command
- **NEW**: Comprehensive deprecation warning system
- **NEW**: Improved CLI error handling and user feedback
- **NEW**: Standardized output file naming conventions

#### Documentation
- **NEW**: Migration guide for v0.3.0 (`MIGRATION_v0.3.0.md`)
- **NEW**: Comprehensive deprecation notes (`DEPRECATION_NOTES_v0.3.0.md`)
- **NEW**: Updated CLI reference with deprecation warnings

### 🔧 Changed

#### CLI Architecture
- **CHANGED**: API-first architecture - CLI layer now delegates to API layer
- **CHANGED**: Standardized CLI initialization across all commands
- **CHANGED**: Improved parameter validation and error messages
- **CHANGED**: Consistent file output naming patterns

#### Parameter Names
- **CHANGED**: `bathymetry` command: `--source` → `--bathy-source` (for consistency)
- **CHANGED**: All commands: Shorter `--bathy-*` parameter names for reduced typing
- **CHANGED**: Output parameters: `--output-file` → `--output` (base filename) + `--output-dir`

#### Command Behavior  
- **CHANGED**: `cruiseplan pangaea` automatically detects search vs DOI file mode
- **CHANGED**: Coordinate format fixed to DMM (degrees decimal minutes)
- **CHANGED**: Improved bathymetry source fallback logic

### 🐛 Fixed

#### Output Naming & File Organization
- **FIXED**: PNG filename conflicts between `schedule` and `process` commands
  - Process command now generates `{cruise_name}_map.png`
  - Schedule command now generates `{cruise_name}_schedule.png`
- **FIXED**: Output naming conventions to consistently use cruise name from YAML
  - All CLI commands now extract cruise name from config file instead of using generic defaults
  - Fixed `_standardize_output_setup` function to properly read cruise names
- **FIXED**: KML filename inconsistency in test fixtures
  - Fixed `test_all_fixtures.py` to use cruise names consistently across all commands
- **FIXED**: HTML schedule files now correctly embed generated map images
  - Fixed map filename reference in HTML generator to match actual PNG output

#### CLI Parameter Handling
- **FIXED**: Parameter mismatch between CLI and API layers
  - Fixed `enrich` command passing `output_file` instead of `output` to API
  - Fixed parameter name mismatches in `process`, `pangaea`, and `map` commands
- **FIXED**: Coordinate validation to support both -180/180 and 0/360 longitude formats
  - Single validation function handles both formats without meridian crossing for 0/360
- **FIXED**: Cruise name extraction in CLI commands
  - Added proper cruise name reading from YAML files in `enrich.py` and `process.py`

#### Test Suite
- **FIXED**: 41 failing CLI tests after API-first refactor
- **FIXED**: Test output directory pollution (tests now use `tests_output/`)
- **FIXED**: Improved test coverage for process.py (67% → 85%+)
- **FIXED**: Test mocking patterns updated for new architecture
- **FIXED**: Integration test robustness issues with filesystem operations

#### CLI Issues
- **FIXED**: Logger configuration issues in CLI commands
- **FIXED**: Parameter validation edge cases
- **FIXED**: Error handling for missing directories

### 📝 Documentation Updates

#### CLI Documentation
- **UPDATED**: All CLI reference docs with new parameter names
- **UPDATED**: User workflow examples with v0.3.0 syntax
- **UPDATED**: Added deprecation warnings to all affected documentation

#### Migration Support
- **ADDED**: Step-by-step migration examples
- **ADDED**: Automated script migration tools
- **ADDED**: Common migration issue troubleshooting

---

## Previous Releases

### [0.2.0] - 2024-XX-XX

#### Major Refactoring
- **REFACTOR**: CLI module separation from API (#43)
- **REFACTOR**: Validation and scheduler utilities with expanded test coverage (#42)  
- **REFACTOR**: Position model simplification - `position.latitude` → `latitude` (#41)
- **FEATURE**: Support for cruises without explicit legs (#39)

#### Improvements
- **IMPROVED**: Documentation organization and cleanup (#40)
- **ENHANCED**: Test coverage across core modules
- **FIXED**: Various coordination and validation edge cases

### [0.1.0] - 2024-XX-XX

#### Initial Release
- **NEW**: Complete cruise planning pipeline
- **NEW**: Interactive station placement with bathymetry  
- **NEW**: PANGAEA historical data integration
- **NEW**: Multi-format output generation (NetCDF, LaTeX, PNG, KML, CSV)
- **NEW**: Comprehensive validation system
- **NEW**: Modern Python packaging with CI/CD

---

## Migration Notes

### v0.2.x → v0.3.0

**⚠️ Breaking Changes**: This release removes deprecated commands and parameters. 

**Migration Required**: Update scripts using deprecated commands:
- `cruiseplan download` → `cruiseplan bathymetry`  
- `cruiseplan pandoi` → `cruiseplan pangaea`
- `--bathymetry-*` → `--bathy-*`
- `--output-file` → `--output` + `--output-dir`

**Migration Tools**: See [MIGRATION_v0.3.0.md](MIGRATION_v0.3.0.md) for detailed migration guide with examples and automated scripts.

**Timeline**: 
- v0.2.x: Deprecation warnings (backward compatible)
- v0.3.0: Breaking changes take effect
- v0.3.0+: Only new syntax supported

### Compatibility Matrix

| Version | `download` | `pandoi` | `--bathymetry-*` | `--output-file` |
|---------|------------|----------|------------------|-----------------|
| v0.1.x  | ✅ Supported | ✅ Supported | ✅ Supported | ✅ Supported |
| v0.2.x  | ⚠️ Deprecated | ⚠️ Deprecated | ⚠️ Deprecated | ⚠️ Deprecated |
| v0.3.x+ | ❌ Removed   | ❌ Removed   | ❌ Removed    | ❌ Removed   |

---

## Development

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

### Release Process
1. Update version in `pyproject.toml`
2. Update changelog with release date
3. Create release tag: `git tag v0.X.Y`
4. Push tag: `git push origin v0.X.Y`
5. GitHub Actions automatically publishes to PyPI

### Versioning Strategy
- **MAJOR**: Breaking API changes, deprecated feature removal
- **MINOR**: New features, new CLI commands, non-breaking API changes  
- **PATCH**: Bug fixes, documentation updates, internal refactoring

---

*For older changes, see git history: `git log --oneline --graph`*