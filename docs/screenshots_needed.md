# CruisePlan Documentation Screenshots List

This document outlines all screenshots needed for comprehensive user workflow documentation. Screenshots should be high-resolution (300 DPI minimum) and show realistic cruise planning scenarios.

## Installation & Setup Screenshots

### 1. Installation Process
- **File**: `installation_terminal.png`
- **Content**: Terminal showing successful installation with `pip install cruiseplan`
- **Context**: Installation documentation section

### 2. Download Command Output
- **File**: `download_bathymetry.png`
- **Content**: Terminal showing `cruiseplan download` command with progress bars
- **Context**: Prerequisites section, shows bathymetry download process

### 3. Download File Structure
- **File**: `data_directory_structure.png`
- **Content**: File explorer showing `data/bathymetry/` with downloaded NetCDF files
- **Context**: Verification that download worked correctly

## Interactive Station Planning Screenshots

### 4. Station Picker Initial Launch
- **File**: `station_picker_startup.png`
- **Content**: Initial three-panel station picker interface with empty map
- **Features to show**: Left panel (controls), center panel (map), right panel (info)
- **Context**: Step 2 of basic planning workflow

### 5. Station Picker with Bathymetry
- **File**: `station_picker_bathymetry.png`
- **Content**: Map showing bathymetric contours (depth colors/lines)
- **Geographic area**: Subpolar North Atlantic (default view)
- **Context**: Explain how depth information helps with station planning

### 6. Point Station Placement Mode
- **File**: `station_picker_point_mode.png`
- **Content**: Interface in point placement mode (p/w key pressed)
- **Visual indicators**: Cursor changes, mode indicator in interface
- **Context**: Interactive controls documentation

### 7. Placing First Station
- **File**: `station_picker_first_station.png`
- **Content**: Map after placing one station, showing:
  - Station marker on map
  - Real-time depth feedback
  - Station information in right panel
- **Context**: Demonstrate immediate feedback

### 8. Multiple Stations Placed
- **File**: `station_picker_multiple_stations.png`
- **Content**: Map with 5-7 stations placed showing:
  - Various station types (CTD, mooring markers)
  - Station labels/names
  - Depth information displayed
- **Context**: Show typical station layout

### 9. Line/Transect Planning Mode
- **File**: `station_picker_line_mode.png`
- **Content**: Interface showing line/transect placement mode
- **Features**: Line drawing in progress, distance measurements
- **Context**: Advanced station planning features

### 10. Area/Box Survey Mode
- **File**: `station_picker_area_mode.png`
- **Content**: Interface showing area selection for box surveys
- **Features**: Rectangle selection tool, area calculation
- **Context**: Survey pattern planning

### 11. Navigation Mode
- **File**: `station_picker_navigation.png`
- **Content**: Interface in navigation mode (zoomed view)
- **Purpose**: Show pan/zoom without accidentally placing stations
- **Context**: Explain safe exploration of map

### 12. PANGAEA Data Integration
- **File**: `station_picker_pangaea.png`  
- **Content**: Map showing historical stations from PANGAEA data
- **Features**: Different symbols for historical vs planned stations
- **Context**: Path 2 (PANGAEA-Enhanced) workflow

### 13. Station Picker Save Dialog
- **File**: `station_picker_save.png`
- **Content**: Save/export interface at end of station planning
- **Show**: File naming, format options
- **Context**: Completion of interactive planning

## Configuration File Examples

### 14. Generated YAML Structure
- **File**: `yaml_basic_structure.png`
- **Content**: Text editor showing basic generated YAML file
- **Highlight**: Station definitions, placeholder values to edit
- **Context**: Step 3 manual configuration editing

### 15. YAML Before/After Enrichment
- **File**: `yaml_enrichment_comparison.png`
- **Content**: Side-by-side comparison showing:
  - Left: Basic YAML with minimal fields
  - Right: Enriched YAML with depths, coordinates, metadata
- **Context**: Enrichment command documentation

## Command Line Interface Screenshots

### 16. Help Command Output
- **File**: `cli_help_overview.png`
- **Content**: `cruiseplan --help` showing all available subcommands
- **Context**: CLI reference introduction

### 17. Enrich Command Progress
- **File**: `enrich_command_progress.png`
- **Content**: Terminal showing enrichment progress with verbose output
- **Show**: Depth lookup progress, coordinate formatting, validation messages
- **Context**: Enrichment workflow step

### 18. Validation Command Output
- **File**: `validate_command_results.png`
- **Content**: Validation command showing:
  - Successful validations (green checkmarks)
  - Warning messages (yellow)
  - Error messages if any (red)
- **Context**: Validation commands documentation

### 19. Schedule Generation Progress
- **File**: `schedule_generation.png`
- **Content**: Terminal showing schedule generation with timing calculations
- **Context**: Final step of workflow

## Output Examples

### 20. HTML Output Preview
- **File**: `schedule_html_output.png`
- **Content**: Web browser showing generated HTML schedule
- **Features**: Summary tables, timeline, station details
- **Context**: Schedule output formats

### 21. Map Output PNG
- **File**: `schedule_map_output.png`
- **Content**: Generated cruise track map showing:
  - Station positions
  - Cruise tracks
  - Bathymetric background
  - Geographic context
- **Context**: Map generation functionality

### 22. Directory Structure After Processing
- **File**: `output_files_structure.png`
- **Content**: File explorer showing all generated outputs:
  - YAML files (original, enriched)
  - Schedule files (HTML, CSV, KML, NetCDF)
  - Map files (PNG)
- **Context**: Complete workflow deliverables

## Error Handling & Troubleshooting Screenshots

### 23. Configuration Error Example
- **File**: `validation_errors.png`
- **Content**: Terminal showing validation errors with helpful messages
- **Context**: Troubleshooting section

### 24. Missing Dependency Warning
- **File**: `dependency_warning.png`
- **Content**: Warning message about missing optional dependencies
- **Context**: Installation troubleshooting

### 25. Successful Workflow Completion
- **File**: `workflow_success.png`
- **Content**: Terminal showing successful completion of entire workflow
- **Show**: Summary of files created, processing time, next steps
- **Context**: Success confirmation for users

## API/Programmatic Usage Screenshots

### 26. Jupyter Notebook Example
- **File**: `api_notebook_example.png`
- **Content**: Jupyter notebook showing programmatic usage
- **Code examples**: Loading configurations, accessing station data
- **Context**: API documentation

### 27. Python Script Example
- **File**: `api_script_example.png`
- **Content**: Text editor showing Python script using CruisePlan API
- **Context**: Developer documentation

## Screenshot Guidelines

### Technical Requirements:
- **Resolution**: Minimum 300 DPI for print documentation
- **Format**: PNG for web, high-quality screenshots
- **Size**: Optimize for web viewing while maintaining clarity

### Content Guidelines:
- Use realistic data (oceanographic cruise scenarios)
- Show complete workflows, not isolated features
- Include representative geographic areas (North Atlantic, polar regions)
- Demonstrate both successful operations and common error scenarios
- Ensure text in screenshots is legible at documentation viewing size

### Geographic Areas to Feature:
- **Subpolar North Atlantic**: Default station picker region
- **Arctic Ocean**: Polar cruise planning example
- **Continental Shelf**: Coastal/bathymetric detail example
- **Deep Ocean**: Abyssal plain station spacing

### Naming Convention:
- Use descriptive filenames that match content
- Include sequence numbers for workflow steps
- Place in `docs/source/_static/screenshots/` directory
- Reference in documentation with proper captions

This comprehensive screenshot plan covers all major user interactions and will significantly enhance the usability and accessibility of the CruisePlan documentation.