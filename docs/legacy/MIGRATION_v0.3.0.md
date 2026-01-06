# Migration Guide: v0.3.0 Breaking Changes

This guide helps you migrate from CruisePlan v0.2.x to v0.3.0, which includes several breaking changes to improve consistency and remove deprecated functionality.

## 📋 Quick Summary

**What's changing:**
- 🗑️ Deprecated commands removed: `cruiseplan download`, `cruiseplan pandoi`
- 🔄 Parameter names shortened: `--bathymetry-*` → `--bathy-*`
- 📂 Output parameter restructured: `--output-file` → `--output` + `--output-dir`
- ⚙️ Configuration format fixed: `--coord-format` removed (always DMM)

**Migration time:** ~15 minutes for most users

## ✅ Recent Fixes (Completed in v0.3.0)

- **FIXED**: Output file naming consistency - all commands now use cruise names from YAML files
- **FIXED**: PNG filename conflicts between `schedule` and `process` commands
- **FIXED**: HTML schedule files now correctly embed generated map images
- **FIXED**: CLI-API parameter mismatches that caused runtime errors
- **FIXED**: KML filename inconsistency in test workflows

## 🚨 Breaking Changes

### 1. Command Replacements

| **Old Command (v0.2.x)** | **New Command (v0.3.0+)** | **Status** |
|---------------------------|----------------------------|------------|
| `cruiseplan download` | `cruiseplan bathymetry` | ✅ Direct replacement |
| `cruiseplan pandoi` | `cruiseplan pangaea` | ✅ Enhanced unified command |

**Migration Examples:**

```bash
# OLD (v0.2.x - will fail in v0.3.0)
cruiseplan download --bathymetry-source gebco2025
cruiseplan pandoi "CTD temperature" --lat 50 60 --lon -50 -30

# NEW (v0.3.0+)
cruiseplan bathymetry --bathy-source gebco2025
cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -30
```

### 2. Parameter Name Changes

| **Old Parameter** | **New Parameter** | **Affected Commands** |
|-------------------|-------------------|----------------------|
| `--bathymetry-source` | `--bathy-source` | `bathymetry`, `process`, `enrich`, `validate`, `map`, `schedule` |
| `--bathymetry-dir` | `--bathy-dir` | `bathymetry`, `process`, `enrich`, `validate`, `map` |
| `--bathymetry-stride` | `--bathy-stride` | `process`, `map`, `schedule` |

**Migration Examples:**

```bash
# OLD (v0.2.x - will fail in v0.3.0)
cruiseplan process -c cruise.yaml --bathymetry-source gebco2025 --bathymetry-dir data/bathy
cruiseplan map -c cruise.yaml --bathymetry-stride 5

# NEW (v0.3.0+)
cruiseplan process -c cruise.yaml --bathy-source gebco2025 --bathy-dir data/bathy
cruiseplan map -c cruise.yaml --bathy-stride 5
```

### 3. Output Parameter Restructuring

The `--output-file` parameter has been replaced with a combination of `--output` (base filename) and `--output-dir` (directory):

| **Old Parameter** | **New Parameters** | **Affected Commands** |
|-------------------|-------------------|----------------------|
| `--output-file /path/to/result.ext` | `--output result --output-dir /path/to` | `pangaea`, `stations`, `process`, `enrich`, `validate`, `map`, `schedule` |

**Migration Examples:**

```bash
# OLD (v0.2.x - will fail in v0.3.0)
cruiseplan enrich -c cruise.yaml --output-file results/enriched_cruise.yaml
cruiseplan map -c cruise.yaml --output-file maps/cruise_map.png

# NEW (v0.3.0+)
cruiseplan enrich -c cruise.yaml --output enriched_cruise --output-dir results/
cruiseplan map -c cruise.yaml --output cruise_map --output-dir maps/
```

### 4. Configuration Format Changes

The `--coord-format` parameter has been removed. Coordinate format is now fixed to DMM (degrees decimal minutes):

```bash
# OLD (v0.2.x - will fail in v0.3.0)
cruiseplan process -c cruise.yaml --coord-format dmm

# NEW (v0.3.0+ - coord format is automatically DMM)
cruiseplan process -c cruise.yaml
```

## 🛠️ Migration Tools

### Automated Script Migration

You can use this sed script to automatically update your shell scripts:

```bash
#!/bin/bash
# migrate_scripts.sh - Update shell scripts for v0.3.0 compatibility

find . -name "*.sh" -exec sed -i.backup \
  -e 's/cruiseplan download/cruiseplan bathymetry/g' \
  -e 's/cruiseplan pandoi/cruiseplan pangaea/g' \
  -e 's/--bathymetry-source/--bathy-source/g' \
  -e 's/--bathymetry-dir/--bathy-dir/g' \
  -e 's/--bathymetry-stride/--bathy-stride/g' \
  -e 's/--coord-format [a-z]* //g' \
  -e 's/--coord-format [a-z]*$//g' \
  {} +

echo "✅ Shell scripts updated. Backups saved with .backup extension."
```

### Manual Migration Checklist

- [ ] **Scripts & Makefiles:** Update command names and parameters
- [ ] **Documentation:** Update README files and wikis  
- [ ] **CI/CD Pipelines:** Update automated workflows
- [ ] **Training Materials:** Update tutorials and examples
- [ ] **Dependencies:** Verify CruisePlan v0.3.0+ in requirements

## 📚 Step-by-Step Migration Examples

### Example 1: Basic Bathymetry Workflow

**Before (v0.2.x):**
```bash
# Download bathymetry
cruiseplan download --bathymetry-source etopo2022

# Process configuration  
cruiseplan process -c cruise.yaml --bathymetry-source etopo2022 --coord-format dmm

# Generate map
cruiseplan map -c cruise_enriched.yaml --bathymetry-stride 10 --output-file maps/track.png
```

**After (v0.3.0+):**
```bash
# Download bathymetry
cruiseplan bathymetry --bathy-source etopo2022

# Process configuration  
cruiseplan process -c cruise.yaml --bathy-source etopo2022

# Generate map
cruiseplan map -c cruise_enriched.yaml --bathy-stride 10 --output track --output-dir maps/
```

### Example 2: PANGAEA Data Integration

**Before (v0.2.x):**
```bash
# Search PANGAEA
cruiseplan pandoi "Arctic CTD" --lat 70 85 --lon -50 30 --output-file data/arctic_dois.txt

# Process DOI file  
cruiseplan pangaea data/arctic_dois.txt --output-file data/arctic_stations.pkl

# Plan stations
cruiseplan stations --lat 70 85 --lon -50 30 --pangaea-file data/arctic_stations.pkl --output-file data/cruise.yaml
```

**After (v0.3.0+):**
```bash
# Search PANGAEA (unified command)
cruiseplan pangaea "Arctic CTD" --lat 70 85 --lon -50 30 --output arctic_dois --output-dir data/

# Process DOI file (same command, detects file mode)
cruiseplan pangaea data/arctic_dois_dois.txt --output arctic_stations --output-dir data/

# Plan stations
cruiseplan stations --lat 70 85 --lon -50 30 --pangaea-file data/arctic_stations_stations.pkl --output cruise --output-dir data/
```

### Example 3: Complete Processing Pipeline

**Before (v0.2.x):**
```bash
#!/bin/bash
# complete_workflow_old.sh

cruiseplan download --bathymetry-source gebco2025
cruiseplan pandoi "temperature salinity" --lat 45 65 --lon -60 -40 --output-file data/search.txt
cruiseplan pangaea data/search.txt --output-file data/historical.pkl
cruiseplan stations --lat 45 65 --lon -60 -40 --pangaea-file data/historical.pkl --output-file data/cruise.yaml
cruiseplan process -c data/cruise.yaml --bathymetry-source gebco2025 --coord-format dmm --output-file data/final.yaml
cruiseplan schedule -c data/final.yaml --output-file results/schedule.html
```

**After (v0.3.0+):**
```bash
#!/bin/bash
# complete_workflow_new.sh

cruiseplan bathymetry --bathy-source gebco2025
cruiseplan pangaea "temperature salinity" --lat 45 65 --lon -60 -40 --output search --output-dir data/
cruiseplan pangaea data/search_dois.txt --output historical --output-dir data/
cruiseplan stations --lat 45 65 --lon -60 -40 --pangaea-file data/historical_stations.pkl --output cruise --output-dir data/
cruiseplan process -c data/cruise.yaml --bathy-source gebco2025 --output final --output-dir data/
cruiseplan schedule -c data/final_enriched.yaml --output schedule --output-dir results/
```

## ⚠️ Common Migration Issues

### Issue 1: Command Not Found

**Error:**
```
cruiseplan: 'download' is not a cruiseplan command. See 'cruiseplan --help'.
```

**Solution:**
```bash
# Replace download with bathymetry
cruiseplan bathymetry --bathy-source etopo2022
```

### Issue 2: Unknown Parameter

**Error:**
```
cruiseplan bathymetry: error: unrecognized arguments: --bathymetry-source
```

**Solution:**
```bash
# Use shortened parameter name
cruiseplan bathymetry --bathy-source etopo2022
```

### Issue 3: Output File Path Errors

**Error:**
```
cruiseplan map: error: unrecognized arguments: --output-file
```

**Solution:**
```bash
# Split into base filename and directory
# OLD: --output-file /path/to/map.png
# NEW: --output map --output-dir /path/to/
```

### Issue 4: Pipeline Scripts Breaking

**Problem:** Shell scripts with multiple commands fail after first deprecated command.

**Solution:** Update all commands in the script systematically:

```bash
# Use the migration script provided above, or update manually:
sed -i 's/cruiseplan download/cruiseplan bathymetry/g' your_script.sh
sed -i 's/--bathymetry-source/--bathy-source/g' your_script.sh
```

## 🔍 Validation After Migration

### 1. Test Basic Commands

```bash
# Verify commands exist and work
cruiseplan bathymetry --help
cruiseplan pangaea --help

# Test parameter recognition  
cruiseplan process --help | grep -E "(bathy-source|bathy-dir|bathy-stride)"
```

### 2. Run Existing Workflows

```bash
# Test with a simple configuration
cruiseplan process -c test_cruise.yaml --bathy-source etopo2022

# Verify no deprecation warnings
cruiseplan map -c test_cruise_enriched.yaml --output test_map 2>&1 | grep -i "deprecated" || echo "✅ No deprecation warnings"
```

### 3. Check Generated Files

```bash
# Ensure file naming follows new patterns
ls data/*_enriched.yaml  # Should exist
ls data/*_map.png        # Should exist with new naming
```

## 📞 Support & Resources

- **Documentation:** Updated [CLI Reference](https://ocean-uhh.github.io/cruiseplan/cli_reference.html)
- **Examples:** [User Workflows](https://ocean-uhh.github.io/cruiseplan/user_workflows.html)  
- **Issues:** [GitHub Issues](https://github.com/ocean-uhh/cruiseplan/issues)
- **Migration Questions:** Tag issues with `migration-v0.3.0`

## 📅 Timeline

- **v0.2.x (Current):** Deprecation warnings for old commands/parameters
- **v0.3.0 (Release):** Breaking changes take effect, old commands removed
- **v0.3.0+ (Future):** Only new command syntax supported

**Migration window:** Plan to update scripts during the v0.2.x → v0.3.0 transition period when both syntaxes show warnings but still work.

---

*For technical details about deprecated functionality, see [DEPRECATION_NOTES_v0.3.0.md](DEPRECATION_NOTES_v0.3.0.md).*