# Phase 4: CLI Integration Implementation Plan

## Overview
Phase 4 implements a comprehensive CLI interface with modern subcommand architecture following git-style patterns. This phase is divided into three sub-phases to ensure systematic development and testing.

## Phase 4a: Data Acquisition Commands (Weeks 13-14)

### 4a.1: cruiseplan pangaea (cli/download.py)

**Purpose**: Process PANGAEA DOI lists into campaign datasets for background context

**Implementation Steps**:

1. **Create cli/download.py module**
   - Import existing PANGAEA functionality from cruiseplan.data.pangaea
   - Implement command-line argument parsing using argparse
   - Add progress indicators for API requests
   - Implement rate limiting controls

2. **Command Interface**:
   ```bash
   cruiseplan pangaea DOI_LIST_FILE [-o OUTPUT_DIR] [--output-file OUTPUT_FILE]
                      [--rate-limit REQUESTS_PER_SECOND]
   ```

3. **Key Features**:
   - DOI validation before processing
   - Progress bars for long API operations
   - Rate limiting to respect PANGAEA servers
   - Geographic filtering options
   - Campaign merging capabilities

4. **Error Handling**:
   - Invalid DOI format detection
   - Network connectivity issues
   - API rate limit exceeded warnings
   - Malformed response handling

### 4a.2: cruiseplan stations (cli/stations.py)

**Purpose**: Interactive station placement with PANGAEA background data and bathymetry

**Implementation Steps**:

1. **Create cli/stations.py module**
   - Import existing interactive functionality from cruiseplan.interactive
   - Integrate bathymetry rendering capabilities
   - Add PANGAEA data overlay features
   - Implement command-line configuration

2. **Command Interface**:
   ```bash
   cruiseplan stations [-p PANGAEA_FILE] [--lat MIN MAX] [--lon MIN MAX]
                      [-o OUTPUT_DIR] [--output-file OUTPUT_FILE]
   ```

3. **Key Features**:
   - Interactive map interface with station placement
   - PANGAEA campaign overlay for context
   - Bathymetry contour visualization
   - Real-time coordinate display
   - Station metadata input forms

4. **Output Generation**:
   - YAML station catalog generation
   - Coordinate validation and formatting
   - Depth estimation from bathymetry
   - Station naming and classification

**Testing Requirements for Phase 4a**:
- Unit tests for argument parsing and validation
- Integration tests with sample DOI lists
- Interactive testing with different geographic regions
- Performance testing for large PANGAEA datasets

## Phase 4b: Data Enhancement and Validation Commands (Weeks 14-15)

### 4b.1: cruiseplan enrich (cli/enrich.py)

**Purpose**: Add missing data to existing station configurations

**Implementation Steps**:

1. **Create cli/enrich.py module**
   - Import bathymetry functionality from cruiseplan.data.bathymetry
   - Import coordinate utilities from cruiseplan.utils.coordinates
   - Implement data addition functions with safe YAML handling

2. **Command Interface**:
   ```bash
   cruiseplan enrich -c INPUT_CONFIG [--add-depths] [--add-coords] 
                     [-o OUTPUT_DIR] [--output-file OUTPUT_FILE]
                     [--bathymetry-source DATASET] [--coord-format FORMAT]
   ```

3. **Key Features**:
   - `--add-depths`: Add missing depth values to stations using bathymetry data
   - `--add-coords`: Add formatted coordinate fields (DMM, DMS formats)
   - Composable operations (can combine multiple enhancements in one command)
   - Safe YAML modification with validation before writing
   - Multiple bathymetry dataset support (ETOPO, GEBCO)
   - Preserves existing data and structure

### 4b.2: cruiseplan validate (cli/validate.py)

**Purpose**: Comprehensive YAML configuration validation (read-only)

**Implementation Steps**:

1. **Create cli/validate.py module**
   - Import validation functionality from cruiseplan.core.validation
   - Import bathymetry functionality for depth checking
   - Add comprehensive error reporting with line numbers

2. **Command Interface**:
   ```bash
   cruiseplan validate -c INPUT_CONFIG [--check-depths] [--strict] [--warnings-only]
                       [--tolerance PERCENT] [--bathymetry-source DATASET]
   ```

3. **Key Features**:
   - Pydantic schema validation (structure, types, required fields)
   - `--check-depths`: Compare existing depths with bathymetry data
   - Cross-reference checking (station/transit references)
   - Geographic bounds validation
   - Timing and duration consistency checks
   - Read-only operation (no file modification)
   - Configurable tolerance levels for depth discrepancies

### 4b.3: Design Philosophy

**Separation of Concerns**:
- `cruiseplan enrich`: Modifies configuration files by adding missing data
- `cruiseplan validate`: Validates configuration files without modification

**Typical Workflow**:
```bash
# Add missing data to configuration
cruiseplan enrich -c cruise.yaml --add-depths --add-coords

# Validate the enriched configuration
cruiseplan validate -c cruise.yaml --check-depths

# Generate schedule from validated configuration
cruiseplan schedule -c cruise.yaml
```

**Future Extensibility**:
- `enrich` can later add `--correct-depths` (auto-fix depth discrepancies)
- `validate` can add more validation types (ports, weather patterns, etc.)

### 4b.4: Architecture and Implementation Details

**Core Logic Placement**:
Following the principle that CLI modules should be lightweight wrappers, the actual validation and enrichment logic resides in `cruiseplan/core/validation.py`:

**`cruiseplan/core/validation.py`** (extend existing file):
```python
def enrich_configuration(
    config_path: Path, 
    add_depths: bool = False, 
    add_coords: bool = False,
    bathymetry_source: str = "etopo2022",
    coord_format: str = "dmm",
    output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Add missing data to cruise configuration.
    Returns summary of changes made.
    """

def validate_configuration_file(
    config_path: Path, 
    check_depths: bool = False,
    tolerance: float = 10.0,
    bathymetry_source: str = "etopo2022",
    strict: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """
    Comprehensive validation of YAML configuration file.
    Returns (success, errors, warnings).
    """

def validate_depth_accuracy(
    cruise: Cruise, 
    bathymetry_manager: BathymetryManager, 
    tolerance: float
) -> Tuple[int, List[str]]:
    """
    Compare station depths with bathymetry data.
    Returns (stations_checked, warning_messages).
    """
```

**`cruiseplan/cli/enrich.py`** (lightweight wrapper):
```python
def main(args: argparse.Namespace) -> None:
    """CLI wrapper that delegates to core validation functions."""
    # Setup logging, validate inputs
    from cruiseplan.core.validation import enrich_configuration
    
    result = enrich_configuration(
        config_path=args.config_file,
        add_depths=args.add_depths,
        add_coords=args.add_coords,
        bathymetry_source=args.bathymetry_source,
        coord_format=args.coord_format,
        output_path=determine_output_path(args)
    )
    
    # Handle result reporting and exit codes
```

**`cruiseplan/cli/validate.py`** (lightweight wrapper):
```python
def main(args: argparse.Namespace) -> None:
    """CLI wrapper that delegates to core validation functions."""
    # Setup logging, validate inputs
    from cruiseplan.core.validation import validate_configuration_file
    
    success, errors, warnings = validate_configuration_file(
        config_path=args.config_file,
        check_depths=args.check_depths,
        tolerance=args.tolerance,
        bathymetry_source=args.bathymetry_source,
        strict=args.strict
    )
    
    # Handle result reporting and exit codes
```

**Benefits of This Approach**:
- CLI modules remain lightweight and focused on argument parsing
- Core validation logic can be reused by other parts of the system
- Testing is easier (test core functions independently of CLI)
- Clear separation of concerns: CLI for interface, core for business logic
- Follows existing patterns in the codebase

**Implementation Steps**:

1. **Extend `cruiseplan/core/validation.py`**:
   - Add imports for bathymetry and coordinate utilities
   - Implement the three core functions: `enrich_configuration()`, `validate_configuration_file()`, `validate_depth_accuracy()`
   - Leverage existing Pydantic models and validation patterns
   - Handle file I/O, error collection, and result formatting

2. **Refactor CLI modules to be lightweight wrappers**:
   - Update `cruiseplan/cli/enrich.py` to call core validation functions
   - Update `cruiseplan/cli/validate.py` to call core validation functions  
   - Keep CLI responsibilities: argument parsing, logging setup, result reporting, exit codes
   - Remove business logic from CLI modules

3. **Testing Strategy**:
   - Unit tests for core functions in `tests/core/test_validation.py`
   - CLI integration tests in `tests/cli/test_enrich.py` and `tests/cli/test_validate.py`
   - Separate test data and mock strategies for core vs CLI testing

**Testing Requirements for Phase 4b**:
- Core function unit tests with various YAML configurations
- Validation tests with malformed YAML files
- Accuracy testing for depth lookups against bathymetry data
- Coordinate conversion accuracy testing
- Performance testing with large station catalogs
- CLI integration tests verifying argument parsing and output formatting
- Error handling tests for file I/O operations

## Phase 4c: Schedule Generation Command (Week 15-16)

### 4c.1: cruiseplan schedule (cli/schedule.py)

**Purpose**: Generate comprehensive cruise schedules from YAML configuration

**Implementation Steps**:

1. **Create cli/schedule.py module**
   - Import scheduling functionality from cruiseplan.calculators.scheduler
   - Import output generation from cruiseplan.output
   - Implement format selection and processing

2. **Command Interface**:
   ```bash
   cruiseplan schedule -c INPUT_CONFIG [-o OUTPUT_DIR] [--format FORMATS]
                       [--validate-depths] [--leg LEGNAME]
   ```

3. **Key Features**:
   - Multiple output format generation (HTML, LaTeX, CSV, KML, NetCDF)
   - Selective leg processing
   - Integrated depth validation during scheduling
   - Comprehensive schedule validation

4. **Output Management**:
   - Organized output directory structure
   - Format-specific file naming conventions
   - Progress reporting for complex schedules
   - Error reporting with line numbers and context

**Testing Requirements for Phase 4c**:
- End-to-end workflow testing
- Multi-format output validation
- Large cruise configuration performance testing
- Error handling and recovery testing

## Phase 4: Infrastructure Components

### 4.1: CLI Framework (cli/main.py)

**Purpose**: Unified command interface with subcommand routing

**Implementation Steps**:

1. **Create cli/main.py module**
   - Implement main command parser with subcommands
   - Add global options (--verbose, --quiet, --help)
   - Create subcommand registration system
   - Implement consistent error handling patterns

2. **Key Features**:
   - Git-style subcommand architecture
   - Comprehensive help system with examples
   - Consistent parameter validation across subcommands
   - Global configuration and logging setup

### 4.2: Common Utilities (cli/utils.py)

**Purpose**: Shared functionality across CLI modules

**Implementation Steps**:

1. **Create cli/utils.py module**
   - File path validation and resolution
   - Output directory creation and management
   - Progress bar utilities
   - Error message formatting
   - YAML file loading and saving utilities

### 4.3: Testing Infrastructure

**Implementation Steps**:

1. **Create tests/cli/ directory structure**
   - Unit tests for each CLI module
   - Integration tests for complete workflows
   - Mock data for testing without external dependencies
   - Performance benchmarking tests

2. **Key Testing Areas**:
   - Argument parsing and validation
   - File I/O operations
   - Error handling and recovery
   - Progress reporting accuracy
   - Output format correctness

## Success Criteria

### Phase 4a Success Criteria:
- [ ] PANGAEA DOI processing works with real DOI lists
- [ ] Interactive station placement generates valid YAML configurations
- [ ] Geographic filtering and bounds checking work correctly
- [ ] Progress indicators provide accurate feedback

### Phase 4b Success Criteria:
- [ ] Depth validation identifies discrepancies accurately
- [ ] Coordinate formatting supports all specified formats
- [ ] YAML validation catches all configuration errors
- [ ] Enhancement commands preserve existing data integrity

### Phase 4c Success Criteria:
- [ ] Schedule generation produces all required output formats
- [ ] Large configuration files process within reasonable time
- [ ] Error messages provide actionable feedback
- [ ] CLI interface feels intuitive and responsive

### Overall Phase 4 Success Criteria:
- [ ] Complete end-to-end workflow: PANGAEA → stations → validate → schedule
- [ ] Comprehensive help documentation for all commands
- [ ] Consistent error handling and user feedback
- [ ] Performance meets requirements for typical cruise configurations
- [ ] CLI passes all integration and regression tests

## Implementation Notes

### Development Priorities:
1. Core functionality first (argument parsing, basic operations)
2. Error handling and validation second
3. Progress indicators and UX polish third
4. Performance optimization last

### Code Organization:
- Keep CLI modules focused and single-purpose
- Extract complex logic to existing core modules
- Maintain clear separation between CLI interface and business logic
- Use consistent patterns across all subcommands

### Documentation Requirements:
- Comprehensive docstrings for all CLI functions
- Usage examples in help text
- Error message suggestions for common issues
- Integration examples in main project documentation