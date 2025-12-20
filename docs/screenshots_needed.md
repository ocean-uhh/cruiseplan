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

## Output Format Visualization Screenshots

### 28. PNG Map Command vs Schedule Command Comparison
- **File**: `png_output_comparison.png`
- **Content**: Side-by-side comparison showing:
  - Left: `cruiseplan map --format png` output (configuration-based)
  - Right: `cruiseplan schedule --format png` output (timeline-based)
- **Key differences to highlight**:
  - Station order (configuration vs scheduled sequence)
  - Track lines (basic vs complete routing)
  - Station markers (differentiated vs uniform)
- **Context**: PNG output format documentation

### 29. Schedule Command PNG Output Detail
- **File**: `schedule_png_detailed.png`
- **Content**: High-resolution example of schedule PNG showing:
  - Complete cruise track with all transit lines
  - Numbered stations in execution order
  - Timing annotations on track segments
  - Professional cartographic styling
- **Context**: Schedule PNG output documentation

### 30. Map Command PNG Output Detail
- **File**: `map_png_detailed.png`
- **Content**: High-resolution example of map PNG showing:
  - Stations and moorings with different symbols
  - Port connections (dashed lines)
  - Configuration order numbering
  - Geographic context without timing
- **Context**: Map PNG output documentation

### 31. HTML Output Full Page
- **File**: `html_output_fullpage.png`
- **Content**: Complete HTML output page showing:
  - Navigation header and cruise summary
  - Timeline table with operation details
  - Embedded cruise track map (PNG)
  - Station details section
  - Professional web formatting
- **Context**: HTML output format documentation

### 32. LaTeX Output Example
- **File**: `latex_output_example.png`
- **Content**: Compiled LaTeX PDF showing:
  - Working areas and profiles table
  - Work days at sea calculation
  - Station list with coordinates
  - Professional academic formatting
- **Context**: LaTeX output format documentation

### 33. CSV Output in Excel
- **File**: `csv_output_excel.png`
- **Content**: Excel spreadsheet showing CSV import:
  - Complete operation timeline
  - All data columns properly formatted
  - Example pivot table or analysis
  - Column headers and data types visible
- **Context**: CSV output format documentation

### 34. KML Output in Google Earth
- **File**: `kml_output_google_earth.png`
- **Content**: Google Earth displaying KML file showing:
  - 3D terrain visualization
  - Station markers with information popups
  - Cruise track overlay
  - Time slider interface (if applicable)
- **Context**: KML output format documentation

### 35. NetCDF File Structure
- **File**: `netcdf_output_structure.png`
- **Content**: Tool (like ncview, Panoply, or Python) showing:
  - NetCDF file structure and variables
  - CF convention compliance
  - Data dimensions and attributes
  - Variable metadata display
- **Context**: NetCDF output format documentation

### 36. Multiple Output Formats Directory
- **File**: `all_formats_directory.png`
- **Content**: File explorer showing complete output set:
  - All format files from `--format all` command
  - Specialized NetCDF files from `--derive-netcdf`
  - Proper naming conventions displayed
  - File sizes and timestamps visible
- **Context**: Output format overview

### 37. Command Format Selection Examples
- **File**: `format_selection_commands.png`
- **Content**: Terminal showing different format selection commands:
  - `cruiseplan schedule --format all`
  - `cruiseplan schedule --format png,html,csv`
  - `cruiseplan map --format png,kml`
  - Output confirmation messages
- **Context**: Format selection documentation

### 38. Output Quality Comparison
- **File**: `output_quality_comparison.png`
- **Content**: Side-by-side showing:
  - Publication-quality PNG (high DPI)
  - Web-optimized PNG (standard DPI)
  - Professional vs preview formatting
- **Context**: Quality assurance documentation

This comprehensive screenshot plan covers all major user interactions and output formats, significantly enhancing the usability and accessibility of the CruisePlan documentation.