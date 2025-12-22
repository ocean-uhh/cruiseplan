# Release Notes - CruisePlan v0.2.1

## Bug Fixes

### LaTeX Generator Duration Calculation Fix
- **Fixed**: Corrected duration calculation logic in LaTeX table generator that was causing incorrect total durations
- **Issue**: The `total_navigation_transit_h` calculation was incorrectly including within-area navigation transits, leading to inflated totals in LaTeX output tables
- **Solution**: Modified logic in `latex_generator.py` lines 289-291 to exclude `transit_within_area_h` from navigation transit totals
- **Impact**: LaTeX-generated tables now show accurate duration totals that match HTML (and CSV) outputs with a new test for the Latex<->HTML match

## Feature

### CLI Enhancements  
- **Added**: New `cruiseplan process` wrapper command for streamlined workflow execution
- **Added**: New `cruiseplan bathymetry` to replace `cruiseplan download` in v0.3.0 (for clarity)
- **Updated**: Now `cruiseplan pangaea` combines the old `cruiseplan pangaea` and `cruiseplan pandoi`, with backwards compatibility.
- **Improved**: Consistent parameter naming across CLI commands (`--bathy-source` standardization)
- **Enhanced**: Output path handling with `--output` base filename support across commands

## Internal Improvements

### Code Quality
- **Enhanced**: Cluster resolution logic now properly handles both legacy `stations` field and new `activities` field
- **Added**: Inline definition resolution for clusters, allowing dictionary definitions to be converted to proper Pydantic objects
- **Improved**: Error handling and validation for cruise configuration loading

## Migration Notes

- **Clusters**: The `stations` field in cluster definitions is deprecated. Use `activities` instead. Both are currently supported for backward compatibility.
- **CLI Parameters**: Some parameter names have been standardized (e.g., `--bathymetry-source` → `--bathy-source`). Old names still work with deprecation warnings.

## Compatibility

- **Python**: 3.9+
- **Breaking Changes**: None - all changes are backward compatible
- **Dependencies**: No new dependencies added

---

**Full Changelog**: https://github.com/anthropics/cruiseplan/compare/v0.2.0...v0.2.1