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

## Phase 4b: Data Enhancement Commands (Weeks 14-15)

### 4b.1: cruiseplan depths (cli/enhance.py)

**Purpose**: Validate and add bathymetry depths to existing station configurations

**Implementation Steps**:

1. **Create cli/enhance.py module**
   - Import bathymetry functionality from cruiseplan.data.bathymetry
   - Implement depth validation algorithms
   - Add tolerance checking and warning systems

2. **Command Interface**:
   ```bash
   cruiseplan depths -c INPUT_CONFIG [-o OUTPUT_DIR] [--output-file OUTPUT_FILE]
                     [--tolerance PERCENT] [--source DATASET]
   ```

3. **Key Features**:
   - Batch depth lookup for all stations
   - Tolerance checking against existing depths
   - Multiple bathymetry dataset support (ETOPO, GEBCO)
   - Warning system for significant depth differences
   - Automated depth addition for stations without depth values

### 4b.2: cruiseplan coords (cli/enhance.py)

**Purpose**: Add navigational coordinate formatting to YAML configurations

**Implementation Steps**:

1. **Extend cli/enhance.py module**
   - Implement coordinate format conversion functions
   - Add multiple format support (DD, DM, DMS)
   - Create field injection capabilities

2. **Command Interface**:
   ```bash
   cruiseplan coords -c INPUT_CONFIG [-o OUTPUT_DIR] [--output-file OUTPUT_FILE]
                     [--format FORMAT] [--field-name FIELD]
   ```

3. **Key Features**:
   - Multiple coordinate format options
   - Customizable output field names
   - Preservation of existing coordinate data
   - Validation of coordinate ranges and formats

### 4b.3: cruiseplan validate (cli/enhance.py)

**Purpose**: Comprehensive YAML configuration validation

**Implementation Steps**:

1. **Extend cli/enhance.py module**
   - Import validation functionality from cruiseplan.core.validation
   - Add comprehensive error reporting
   - Implement validation rule checking

2. **Command Interface**:
   ```bash
   cruiseplan validate -c INPUT_CONFIG [--strict] [--warnings-only]
   ```

3. **Key Features**:
   - Pydantic schema validation
   - Cross-reference checking (station/transit references)
   - Geographic bounds validation
   - Timing and duration consistency checks
   - Port accessibility validation

**Testing Requirements for Phase 4b**:
- Validation tests with malformed YAML files
- Accuracy testing for depth lookups
- Coordinate conversion accuracy testing
- Performance testing with large station catalogs

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