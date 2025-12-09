# Phase 3 Implementation Instructions: Output Generation System

## Overview

Phase 3 implements the comprehensive output generation system for the oceanographic cruise planning system. This phase transforms the interactive station selections and YAML cruise configurations into professional outputs suitable for cruise proposals, operational planning, and scientific data management.

## Phase 3 Architecture

The output generation system consists of five integrated sub-phases:

- **Phase 3a**: LaTeX Table Generation (Cruise proposals)
- **Phase 3b**: Scheduling logic
- **Phase 3c**: NetCDF Output (Scientific data formats)
- **Phase 3d**: Interactive Web Maps (Building on existing map_generator.py)
- **Phase 3e**: HTML Summary Generation (Interactive reports)
- **Phase 3f**: KML Generation (Google Earth visualization)

## Test Data Requirements

Before implementation, create three comprehensive test YAML files in `tests/fixtures/`:

### Test File 1: cruise_simple.yaml
```yaml
# Simple 2-station cruise for basic functionality testing
cruise_name: "Simple_Test_Cruise_2028"
description: "Basic two-station test cruise"
default_vessel_speed: 10.0
default_distance_between_stations: 111.0  # ~1 degree latitude
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: true

# Ports (Atlantic crossing simulation)
departure_port:
  latitude: 47.5705
  longitude: -52.6979
  name: "St. Johns"
  timezone: "GMT-3.5"

arrival_port:
  latitude: 64.1466
  longitude: -21.9426
  name: "Reykjavik"
  timezone: "GMT+0"

# Station definitions (exactly 1 degree apart, 1000m depth)
stations:
  - name: "STN_001"
    latitude: 50.0000
    longitude: -40.0000
    depth: 1000.0
    comment: "First test station"

  - name: "STN_002"
    latitude: 51.0000
    longitude: -40.0000
    depth: 1000.0
    comment: "Second test station - 111km north"

first_station: "STN_001"
last_station: "STN_002"

# Simple single-leg cruise
legs:
  - name: "Test_Operations"
    strategy: "sequential"
    stations: ["STN_001", "STN_002"]
```

### Test File 2: cruise_mixed_ops.yaml
```yaml
# Mixed operations: station, mooring, and line section
cruise_name: "Mixed_Operations_Test_2028"
description: "Testing multiple operation types"
default_vessel_speed: 12.0
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: true

departure_port:
  latitude: 53.3321
  longitude: -60.4200
  name: "Labrador Sea Start"

arrival_port:
  latitude: 53.3321
  longitude: -60.4200
  name: "Labrador Sea End"

# Mixed catalog definitions
stations:
  - name: "CTD_Station_A"
    latitude: 53.5000
    longitude: -50.0000
    depth: 2500.0
    comment: "Deep CTD profile"

moorings:
  - name: "Mooring_K7_Recovery"
    latitude: 53.2000
    longitude: -50.2000
    action: "recovery"
    duration: 180.0  # 3 hours
    depth: 2800.0
    comment: "Recover deep mooring"
    equipment: "Full-depth array with ADCP"

transits:
  - name: "Survey_Line_Alpha"
    comment: "Acoustic survey transect"
    route:
      - latitude: 53.3000
        longitude: -50.5000
      - latitude: 53.7000
        longitude: -50.1000

first_station: "CTD_Station_A"
last_station: "Mooring_K7_Recovery"

# Single leg with mixed operations
legs:
  - name: "Labrador_Sea_Operations"
    strategy: "sequential"
    sequence: ["CTD_Station_A", "Survey_Line_Alpha", "Mooring_K7_Recovery"]
```

### Test File 3: cruise_multi_leg.yaml
```yaml
# Multi-leg cruise with multiple stations per leg
cruise_name: "Multi_Leg_Expedition_2028"
description: "Complex multi-area expedition"
default_vessel_speed: 11.0
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: true

departure_port:
  latitude: 47.5705
  longitude: -52.6979
  name: "St. Johns"

arrival_port:
  latitude: 64.1466
  longitude: -21.9426
  name: "Reykjavik"

# Station catalog (6 stations total)
stations:
  - name: "LEG1_STN_01"
    latitude: 48.5000
    longitude: -45.0000
    depth: 3200.0
  - name: "LEG1_STN_02"
    latitude: 49.0000
    longitude: -44.5000
    depth: 3100.0
  - name: "LEG1_STN_03"
    latitude: 49.5000
    longitude: -44.0000
    depth: 2900.0

  - name: "LEG2_STN_01"
    latitude: 58.0000
    longitude: -35.0000
    depth: 2200.0
  - name: "LEG2_STN_02"
    latitude: 58.5000
    longitude: -34.5000
    depth: 2000.0
  - name: "LEG2_STN_03"
    latitude: 59.0000
    longitude: -34.0000
    depth: 1800.0

first_station: "LEG1_STN_01"
last_station: "LEG2_STN_03"

# Two-leg structure
legs:
  - name: "Southern_Operations"
    description: "Deep water profiles in Labrador Basin"
    strategy: "sequential"
    stations: ["LEG1_STN_01", "LEG1_STN_02", "LEG1_STN_03"]

  - name: "Northern_Operations"
    description: "Shelf break stations near Greenland"
    strategy: "sequential"
    stations: ["LEG2_STN_01", "LEG2_STN_02", "LEG2_STN_03"]
```

---

## Phase 3a: LaTeX Table Generation

### Implementation Requirements

**File**: `cruiseplan/output/latex_generator.py`

**Core Function**: Generate professional LaTeX tables for cruise proposals that meet DFG (German Research Foundation) and NSF standards.

### Required Tables

#### 1. Working Area, Stations and Profiles Table
```latex
\begin{table}[htbp]
\caption{Working area, stations and profiles: [Cruise Name]}
\begin{tabular}{llrrc}
\toprule
Operation & Station & Position & Water depth (m) \\
\midrule
CTD profile & STN01 & 52°30.15'N, 051°20.23'W & 2847 \\
Mooring deployment & M02 & 53°07.20'N, 050°34.10'W & 2156 \\
\bottomrule
\end{tabular}
\end{table}
```

#### 2. Work Days at Sea Table
```latex
\begin{table}[htbp]
\caption{Work days at sea: [Cruise Name]}
\begin{tabular}{llrr}
\toprule
Area & Activity & Duration (h) & Transit (h) \\
\midrule
Transit to Area 1 & & & 35 \\
\midrule
Area 1 & CTD stations & 100 & \\
Area 1 & Mooring operations & 25 & \\
Transit within area & & 25 & \\
\midrule
Area 2 & CTD stations & 25 & \\
Transit within area & & 25 & \\
\midrule
Transit from working area & & & 25 \\
\midrule
\textbf{Total duration} & & \textbf{175} & \textbf{85} \\
\bottomrule
\end{tabular}
\end{table}
```

### Implementation Steps

1. **Create LaTeX Template System**:
   ```python
   from jinja2 import Environment, FileSystemLoader
   from pathlib import Path

   class LaTeXGenerator:
       def __init__(self):
           template_dir = Path(__file__).parent / "templates"
           self.env = Environment(
               loader=FileSystemLoader(template_dir),
               block_start_string='\\BLOCK{',
               block_end_string='}',
               variable_start_string='\\VAR{',
               variable_end_string='}',
               comment_start_string='\\#{',
               comment_end_string='}',
               line_statement_prefix='%%',
               line_comment_prefix='%#'
           )
   ```

2. **Coordinate Formatting Function**:
   ```python
   def format_position_latex(lat: float, lon: float) -> str:
       """Convert decimal degrees to LaTeX-formatted degrees and decimal minutes."""
       # Latitude
       lat_deg = int(abs(lat))
       lat_min = (abs(lat) - lat_deg) * 60
       lat_dir = "N" if lat >= 0 else "S"

       # Longitude
       lon_deg = int(abs(lon))
       lon_min = (abs(lon) - lon_deg) * 60
       lon_dir = "E" if lon >= 0 else "W"

       return f"{lat_deg:02d}$^\\circ${lat_min:05.2f}'${lat_dir}$, {lon_deg:03d}$^\\circ${lon_min:05.2f}'${lon_dir}$"
   ```

3. **Page Breaking Logic**:
   - Implement automatic page breaks for tables > 45 rows
   - Add "Continued" to caption on subsequent pages
   - Repeat header rows after page breaks

4. **Create Template Files**:
   - `templates/stations_table.tex.j2`
   - `templates/work_days_table.tex.j2`
   - `templates/complete_cruise.tex.j2`

### Output Interface
```python
def generate_latex_tables(cruise_data: Dict, output_dir: Path) -> List[Path]:
    """
    Generate LaTeX tables for cruise proposal.

    Returns:
        List of generated .tex files
    """
    files_created = []

    # Generate individual tables
    stations_table = generate_stations_table(cruise_data)
    work_days_table = generate_work_days_table(cruise_data)

    # Write to files
    output_dir.mkdir(exist_ok=True)

    stations_file = output_dir / f"{cruise_data['cruise_name']}_stations.tex"
    work_days_file = output_dir / f"{cruise_data['cruise_name']}_work_days.tex"

    stations_file.write_text(stations_table)
    work_days_file.write_text(work_days_table)

    return [stations_file, work_days_file]
```

---

## Phase 3b: HTML Summary Generation

### Implementation Requirements

**File**: `cruiseplan/output/html_generator.py`

**Core Function**: Generate comprehensive HTML reports with interactive navigation and detailed breakdowns.

### HTML Structure Requirements

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Schedule for {{cruise_name}}</title>
    <style>
        /* Professional styling with responsive tables */
        table { border-collapse: collapse; width: 100%; margin: 1em 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f5f5f5; font-weight: bold; }
        .summary { background-color: #e8f4fd; }
        .total-row { font-weight: bold; background-color: #f0f8ff; }
    </style>
</head>
<body>
    <h1>{{cruise_name}}</h1>
    <p><strong>Description:</strong> {{description}}</p>

    <!-- Navigation Links -->
    <h2>Output Files</h2>
    <ul>
        <li><a href="{{cruise_name}}_plot.html">Interactive Cruise Map</a></li>
        <li><a href="{{cruise_name}}.kml">KML file (Google Earth)</a></li>
        <li><a href="{{cruise_name}}.csv">CSV Spreadsheet</a></li>
        <li><a href="{{cruise_name}}.nc">NetCDF Dataset</a></li>
        <li><a href="{{cruise_name}}_stations.tex">LaTeX Stations Table</a></li>
        <li><a href="{{cruise_name}}_work_days.tex">LaTeX Work Days Table</a></li>
    </ul>

    <!-- 1. Cruise Schedule Summary -->
    <h2>1. Cruise Schedule Summary</h2>
    <table>
        <tr>
            <th>Task Category</th>
            <th>Description</th>
            <th>Total Hours</th>
            <th>Total Days</th>
        </tr>
        <!-- Dynamic content based on cruise data -->
        <tr>
            <td>Total Stations</td>
            <td>{{station_count}} stations, Avg depth: {{avg_depth}}m, Avg duration: {{avg_station_duration}}h</td>
            <td>{{total_station_hours}}</td>
            <td>{{total_station_days}}</td>
        </tr>
        <tr class="total-row">
            <td><strong>TOTAL CRUISE</strong></td>
            <td>{{total_operations}} total operations</td>
            <td><strong>{{total_hours}}</strong></td>
            <td><strong>{{total_days}}</strong></td>
        </tr>
    </table>

    <!-- Detailed sections follow... -->
</body>
</html>
```

### Implementation Steps

1. **Create HTML Template System**:
   ```python
   class HTMLGenerator:
       def __init__(self):
           self.env = Environment(loader=FileSystemLoader("templates"))

       def calculate_summary_statistics(self, cruise_data: Dict) -> Dict:
           """Calculate summary statistics for HTML template."""
           stats = {
               'station_count': len(cruise_data.get('stations', [])),
               'mooring_count': len(cruise_data.get('moorings', [])),
               'total_operations': 0,
               'total_hours': 0.0,
               'total_days': 0.0,
               'avg_depth': 0.0,
               'avg_station_duration': 0.0
           }

           # Calculate detailed statistics
           return stats
   ```

2. **Data Aggregation Logic**:
   ```python
   def aggregate_cruise_data(self, cruise_data: Dict) -> Dict:
       """Perform deep flattening operation for HTML rendering."""
       # Flatten: Global_Stations + Legs->Clusters->Stations + Legs->Sections->Stations
       all_stations = []
       all_moorings = []
       all_transfers = []

       # Process legs and clusters
       for leg in cruise_data.get('legs', []):
           # Extract stations, moorings, transfers from each leg
           pass

       return {
           'stations': all_stations,
           'moorings': all_moorings,
           'transfers': all_transfers
       }
   ```

3. **Generate Detailed Breakdown Tables**:
   - Sections/Clusters detail table
   - Moorings manifest table
   - Transfers summary table
   - Miscellaneous activities table

### Output Interface
```python
def generate_html_summary(cruise_data: Dict, output_dir: Path) -> Path:
    """
    Generate comprehensive HTML cruise summary.

    Returns:
        Path to generated index.html file
    """
    aggregated_data = self.aggregate_cruise_data(cruise_data)
    summary_stats = self.calculate_summary_statistics(aggregated_data)

    template_data = {
        'cruise_name': cruise_data['cruise_name'],
        'description': cruise_data.get('description', ''),
        **summary_stats,
        **aggregated_data
    }

    template = self.env.get_template('cruise_summary.html.j2')
    html_content = template.render(**template_data)

    output_file = output_dir / 'index.html'
    output_file.write_text(html_content)

    return output_file
```

---

## Phase 3c: NetCDF Output Generation

### Implementation Requirements

**File**: `cruiseplan/output/netcdf_generator.py`

**Core Function**: Generate CF-compliant NetCDF datasets for scientific data management and analysis.

### NetCDF Structure Requirements

```python
# Primary cruise dataset structure
cruise.nc:
  dimensions:
    station = UNLIMITED  # Number of operations

  variables:
    # Coordinate variables
    longitude(station): float64
      units = "degrees_east"
      standard_name = "longitude"
      long_name = "Station longitude"

    latitude(station): float64
      units = "degrees_north"
      standard_name = "latitude"
      long_name = "Station latitude"

    # Data variables
    water_depth(station): float32
      units = "m"
      standard_name = "sea_floor_depth_below_sea_surface"
      long_name = "Water depth at station"
      _FillValue = -9999.0

    operation_duration(station): float32
      units = "minutes"
      long_name = "Operation duration"

    distance_from_start(station): float32
      units = "nautical_miles"
      long_name = "Cumulative distance from cruise start"

    operation_type(station): |S32
      long_name = "Type of oceanographic operation"
      flag_values = "ctd_profile mooring_deployment mooring_recovery transfer waypoint"

    leg_assignment(station): int32
      long_name = "Cruise leg number assignment"

  global_attributes:
    title = "Oceanographic Cruise Plan: {cruise_name}"
    institution = "Generated by CruisePlan software"
    source = "Cruise planning system"
    history = "{timestamp}: Generated from YAML configuration"
    conventions = "CF-1.8"
    cruise_name = "{cruise_name}"
    vessel_speed_knots = {vessel_speed}
    total_duration_days = {total_days}
    creation_date = "{iso_timestamp}"
    coordinate_system = "WGS84"
    depth_datum = "Mean Sea Level"
```

### Implementation Steps

1. **NetCDF Creation Function**:
   ```python
   import netCDF4 as nc
   import numpy as np
   from datetime import datetime

   class NetCDFGenerator:
       def __init__(self):
           self.cf_conventions = "CF-1.8"

       def create_cruise_dataset(self, cruise_data: Dict, output_path: Path) -> None:
           """Create primary cruise NetCDF dataset."""

           # Process cruise data to extract all operations
           operations = self.extract_all_operations(cruise_data)
           n_operations = len(operations)

           # Create NetCDF file
           with nc.Dataset(output_path, 'w', format='NETCDF4') as ds:
               # Create dimensions
               ds.createDimension('station', n_operations)

               # Create coordinate variables
               lon_var = ds.createVariable('longitude', 'f8', ('station',))
               lat_var = ds.createVariable('latitude', 'f8', ('station',))

               # Create data variables
               depth_var = ds.createVariable('water_depth', 'f4', ('station',),
                                           fill_value=-9999.0)
               duration_var = ds.createVariable('operation_duration', 'f4', ('station',))
               distance_var = ds.createVariable('distance_from_start', 'f4', ('station',))
               op_type_var = ds.createVariable('operation_type', 'S32', ('station',))
               leg_var = ds.createVariable('leg_assignment', 'i4', ('station',))

               # Set variable attributes
               self.set_variable_attributes(lon_var, lat_var, depth_var,
                                          duration_var, distance_var,
                                          op_type_var, leg_var)

               # Fill with data
               self.populate_variables(operations, lon_var, lat_var, depth_var,
                                     duration_var, distance_var, op_type_var, leg_var)

               # Set global attributes
               self.set_global_attributes(ds, cruise_data)
   ```

2. **Specialized Dataset Generation**:
   ```python
   def create_specialized_datasets(self, cruise_data: Dict, output_dir: Path) -> List[Path]:
       """Create specialized NetCDF datasets for different operation types."""

       files_created = []

       # CTD stations dataset
       stations_file = output_dir / f"{cruise_data['cruise_name']}_stations.nc"
       self.create_stations_dataset(cruise_data, stations_file)
       files_created.append(stations_file)

       # Moorings dataset
       moorings_file = output_dir / f"{cruise_data['cruise_name']}_moorings.nc"
       self.create_moorings_dataset(cruise_data, moorings_file)
       files_created.append(moorings_file)

       # Transfers dataset
       transfers_file = output_dir / f"{cruise_data['cruise_name']}_transfers.nc"
       self.create_transfers_dataset(cruise_data, transfers_file)
       files_created.append(transfers_file)

       return files_created
   ```

3. **CF Compliance Validation**:
   ```python
   def validate_cf_compliance(self, netcdf_file: Path) -> bool:
       """Validate CF conventions compliance."""
       try:
           with nc.Dataset(netcdf_file, 'r') as ds:
               # Check required global attributes
               required_attrs = ['Conventions', 'title', 'institution']
               for attr in required_attrs:
                   if not hasattr(ds, attr):
                       return False

               # Check coordinate variables have required attributes
               for var_name in ['longitude', 'latitude']:
                   if var_name in ds.variables:
                       var = ds.variables[var_name]
                       if not hasattr(var, 'units') or not hasattr(var, 'standard_name'):
                           return False

               return True
       except Exception:
           return False
   ```

### Output Interface
```python
def generate_netcdf_outputs(cruise_data: Dict, output_dir: Path) -> List[Path]:
    """
    Generate all NetCDF outputs for cruise data.

    Returns:
        List of generated NetCDF file paths
    """
    output_dir.mkdir(exist_ok=True)
    files_created = []

    # Primary cruise dataset
    main_file = output_dir / f"{cruise_data['cruise_name']}.nc"
    self.create_cruise_dataset(cruise_data, main_file)
    files_created.append(main_file)

    # Specialized datasets
    specialized_files = self.create_specialized_datasets(cruise_data, output_dir)
    files_created.extend(specialized_files)

    # Validate all files
    for file_path in files_created:
        if not self.validate_cf_compliance(file_path):
            logging.warning(f"CF compliance validation failed for {file_path}")

    return files_created
```

---

## Phase 3d: KML Generation

### Implementation Requirements

**File**: `cruiseplan/output/kml_generator.py`

**Core Function**: Generate Google Earth-compatible KML files with cruise tracks, stations, and metadata.

### KML Structure Requirements

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Cruise Plan: {{cruise_name}}</name>
    <description>{{description}}</description>

    <!-- Styles for different operation types -->
    <Style id="station-shallow">
      <IconStyle>
        <color>ff0000ff</color>
        <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
      </IconStyle>
    </Style>

    <Style id="station-deep">
      <IconStyle>
        <color>ffff0000</color>
        <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
      </IconStyle>
    </Style>

    <Style id="mooring">
      <IconStyle>
        <color>ff00ff00</color>
        <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_square.png</href></Icon>
      </IconStyle>
    </Style>

    <Style id="cruise-track">
      <LineStyle>
        <color>ff0000ff</color>
        <width>3</width>
      </LineStyle>
    </Style>

    <!-- Station Folder -->
    <Folder>
      <name>CTD Stations</name>
      <description>CTD profile locations</description>

      <Placemark>
        <name>{{station_name}}</name>
        <description>
          <![CDATA[
            <b>Station:</b> {{station_name}}<br/>
            <b>Position:</b> {{formatted_position}}<br/>
            <b>Water Depth:</b> {{depth}}m<br/>
            <b>Operation:</b> CTD Profile<br/>
            <b>Duration:</b> {{duration}} minutes
          ]]>
        </description>
        <styleUrl>#station-{{depth_category}}</styleUrl>
        <Point>
          <coordinates>{{longitude}},{{latitude}},0</coordinates>
        </Point>
      </Placemark>
    </Folder>

    <!-- Cruise Track -->
    <Placemark>
      <name>Cruise Track</name>
      <description>Complete cruise route</description>
      <styleUrl>#cruise-track</styleUrl>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>
          {{track_coordinates}}
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>
```

### Implementation Steps

1. **KML Generation Class**:
   ```python
   import simplekml
   from typing import Dict, List, Tuple

   class KMLGenerator:
       def __init__(self):
           self.depth_thresholds = {
               'shallow': 200,    # < 200m
               'medium': 1000,    # 200-1000m
               'deep': float('inf')  # > 1000m
           }

           self.colors = {
               'shallow': simplekml.Color.blue,
               'medium': simplekml.Color.yellow,
               'deep': simplekml.Color.red,
               'mooring': simplekml.Color.green,
               'track': simplekml.Color.red
           }

       def classify_depth(self, depth: float) -> str:
           """Classify depth for styling purposes."""
           if depth < self.depth_thresholds['shallow']:
               return 'shallow'
           elif depth < self.depth_thresholds['medium']:
               return 'medium'
           else:
               return 'deep'
   ```

2. **Station Placemark Generation**:
   ```python
   def create_station_placemark(self, kml_doc, station_data: Dict) -> None:
       """Create KML placemark for a CTD station."""

       # Create placemark
       placemark = kml_doc.newpoint(
           name=station_data['name'],
           coords=[(station_data['longitude'], station_data['latitude'])]
       )

       # Format description with HTML
       description = f"""
       <b>Station:</b> {station_data['name']}<br/>
       <b>Position:</b> {self.format_position_dms(station_data['latitude'], station_data['longitude'])}<br/>
       <b>Water Depth:</b> {station_data['depth']:.0f}m<br/>
       <b>Operation:</b> CTD Profile<br/>
       <b>Duration:</b> {station_data.get('duration', 'TBD')} minutes
       """
       placemark.description = description

       # Set style based on depth
       depth_category = self.classify_depth(station_data['depth'])
       placemark.style.iconstyle.color = self.colors[depth_category]
       placemark.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png"
   ```

3. **Cruise Track Generation**:
   ```python
   def create_cruise_track(self, kml_doc, cruise_data: Dict) -> None:
       """Create KML linestring for complete cruise track."""

       # Extract all coordinates in cruise order
       track_coords = self.extract_cruise_track(cruise_data)

       # Create linestring
       linestring = kml_doc.newlinestring(
           name="Cruise Track",
           description="Complete cruise route including transfers",
           coords=track_coords
       )

       # Style the track
       linestring.style.linestyle.color = self.colors['track']
       linestring.style.linestyle.width = 3
       linestring.tessellate = 1
   ```

4. **Folder Organization**:
   ```python
   def organize_into_folders(self, kml_doc, cruise_data: Dict) -> None:
       """Organize placemarks into logical folders."""

       # Create folders
       stations_folder = kml_doc.newfolder(name="CTD Stations")
       moorings_folder = kml_doc.newfolder(name="Moorings")
       transfers_folder = kml_doc.newfolder(name="Transfer Routes")

       # Populate folders with placemarks
       self.populate_stations_folder(stations_folder, cruise_data)
       self.populate_moorings_folder(moorings_folder, cruise_data)
       self.populate_transfers_folder(transfers_folder, cruise_data)
   ```

### Output Interface
```python
def generate_kml(cruise_data: Dict, output_dir: Path) -> Path:
    """
    Generate Google Earth KML file for cruise visualization.

    Returns:
        Path to generated KML file
    """
    # Create KML document
    kml_doc = simplekml.Kml()
    kml_doc.name = f"Cruise Plan: {cruise_data['cruise_name']}"
    kml_doc.description = cruise_data.get('description', '')

    # Organize content into folders
    self.organize_into_folders(kml_doc, cruise_data)

    # Create cruise track
    self.create_cruise_track(kml_doc, cruise_data)

    # Save KML file
    output_file = output_dir / f"{cruise_data['cruise_name']}.kml"
    kml_doc.save(str(output_file))

    return output_file
```

---

## Phase 3e: Interactive Web Maps

### Implementation Requirements

**File**: `cruiseplan/output/map_generator.py` (Enhancement of existing)

**Core Function**: Build upon the existing map generator to create interactive Leaflet-based web maps with enhanced functionality.

### Enhancement Requirements

1. **Current State Assessment**:
   ```python
   # First, analyze existing map_generator.py to understand:
   # - Current functionality and API
   # - Data input formats
   # - Output capabilities
   # - Integration points
   ```

2. **Interactive Features to Add**:
   ```python
   class InteractiveMapGenerator:
       def __init__(self):
           self.base_layers = {
               'OpenStreetMap': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
               'ESRI Ocean': 'https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
               'Satellite': 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'
           }

       def create_interactive_map(self, cruise_data: Dict, output_dir: Path) -> Path:
           """Create interactive Leaflet map with enhanced functionality."""

           # Generate HTML with embedded Leaflet map
           # Add station clustering for dense operations
           # Implement route animation capabilities
           # Add popup information windows
           # Include layer toggle controls
   ```

3. **Bathymetry Overlay Integration**:
   ```python
   def add_bathymetry_overlay(self, map_obj, bounds: Tuple[float, float, float, float]) -> None:
       """Add bathymetry contours as map overlay."""

       # Integration with existing bathymetry system
       from cruiseplan.data.bathymetry import bathymetry

       # Extract contour lines for the cruise area
       # Convert to GeoJSON format
       # Add as overlay layer with toggle control
   ```

4. **Export Functionality**:
   ```python
   def add_export_controls(self, map_obj) -> None:
       """Add export functionality for static images."""

       # Implement Leaflet.EasyPrint plugin
       # Add screenshot/PDF export capabilities
       # Include scale bar and north arrow
   ```

### Integration Requirements

1. **Maintain Backward Compatibility**: Ensure existing `generate_cruise_map()` function continues to work
2. **Enhance API**: Add new optional parameters for interactive features
3. **Template System**: Create HTML templates with embedded Leaflet maps
4. **Asset Management**: Handle CSS/JS dependencies efficiently

---

## Testing Strategy for Phase 3

### Unit Tests

Create comprehensive unit tests in `tests/unit/test_output_generators.py`:

```python
import pytest
from pathlib import Path
from cruiseplan.output import latex_generator, html_generator, netcdf_generator, kml_generator

class TestLaTeXGenerator:
    def test_coordinate_formatting(self):
        """Test LaTeX coordinate formatting."""
        formatted = latex_generator.format_position_latex(52.5025, -51.3369)
        expected = "52$^\\circ$30.15'$N$, 051$^\\circ$20.21'$W$"
        assert formatted == expected

    def test_stations_table_generation(self):
        """Test stations table LaTeX generation."""
        cruise_data = load_test_cruise('cruise_simple.yaml')
        table = latex_generator.generate_stations_table(cruise_data)

        # Verify table structure
        assert "\\begin{table}" in table
        assert "\\toprule" in table
        assert "\\bottomrule" in table
        assert "STN_001" in table

class TestHTMLGenerator:
    def test_summary_statistics_calculation(self):
        """Test HTML summary statistics calculation."""
        cruise_data = load_test_cruise('cruise_mixed_ops.yaml')
        generator = html_generator.HTMLGenerator()
        stats = generator.calculate_summary_statistics(cruise_data)

        assert stats['station_count'] == 1
        assert stats['mooring_count'] == 1
        assert 'total_hours' in stats

class TestNetCDFGenerator:
    def test_cf_compliance(self):
        """Test CF conventions compliance."""
        cruise_data = load_test_cruise('cruise_simple.yaml')
        generator = netcdf_generator.NetCDFGenerator()

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "test.nc"
            generator.create_cruise_dataset(cruise_data, output_path)

            assert generator.validate_cf_compliance(output_path)

class TestKMLGenerator:
    def test_depth_classification(self):
        """Test depth-based styling classification."""
        generator = kml_generator.KMLGenerator()

        assert generator.classify_depth(150) == 'shallow'
        assert generator.classify_depth(500) == 'medium'
        assert generator.classify_depth(2500) == 'deep'
```

### Integration Tests

Create integration tests in `tests/integration/test_phase3_integration.py`:

```python
class TestPhase3Integration:
    def test_complete_output_generation(self):
        """Test generation of all output formats for each test cruise."""

        test_cruises = [
            'cruise_simple.yaml',
            'cruise_mixed_ops.yaml',
            'cruise_multi_leg.yaml'
        ]

        for cruise_file in test_cruises:
            with tempfile.TemporaryDirectory() as output_dir:
                cruise_data = load_test_cruise(cruise_file)
                output_path = Path(output_dir)

                # Generate all outputs
                latex_files = generate_latex_tables(cruise_data, output_path)
                html_file = generate_html_summary(cruise_data, output_path)
                netcdf_files = generate_netcdf_outputs(cruise_data, output_path)
                kml_file = generate_kml(cruise_data, output_path)
                map_file = generate_interactive_map(cruise_data, output_path)

                # Verify all files exist and are valid
                for file_path in latex_files + netcdf_files + [html_file, kml_file, map_file]:
                    assert file_path.exists()
                    assert file_path.stat().st_size > 0

    def test_data_consistency_across_formats(self):
        """Test that coordinate and metadata are consistent across all output formats."""

        cruise_data = load_test_cruise('cruise_simple.yaml')

        # Extract reference coordinates from original data
        ref_station = cruise_data['stations'][0]
        ref_lat, ref_lon = ref_station['latitude'], ref_station['longitude']

        with tempfile.TemporaryDirectory() as output_dir:
            output_path = Path(output_dir)

            # Generate outputs
            html_file = generate_html_summary(cruise_data, output_path)
            netcdf_files = generate_netcdf_outputs(cruise_data, output_path)
            kml_file = generate_kml(cruise_data, output_path)

            # Verify coordinates match across formats
            # (Implementation specific to each format)
            self.verify_html_coordinates(html_file, ref_lat, ref_lon)
            self.verify_netcdf_coordinates(netcdf_files[0], ref_lat, ref_lon)
            self.verify_kml_coordinates(kml_file, ref_lat, ref_lon)
```

---

## CLI Integration

### Update CLI Module

Enhance `cruiseplan/cli/schedule.py` to support all Phase 3 outputs:

```python
def schedule_command(
    config_file: Path,
    output_dir: Path,
    formats: List[str],
    validate_depths: bool = False,
    leg: Optional[str] = None
) -> None:
    """Generate comprehensive cruise schedule from YAML configuration."""

    # Load and validate cruise configuration
    cruise_data = load_cruise_config(config_file)

    if validate_depths:
        validate_station_depths(cruise_data)

    # Filter by leg if specified
    if leg:
        cruise_data = filter_by_leg(cruise_data, leg)

    # Generate outputs based on format selection
    output_dir.mkdir(exist_ok=True)

    if 'all' in formats or 'latex' in formats:
        latex_files = generate_latex_tables(cruise_data, output_dir)
        print(f"Generated LaTeX tables: {[f.name for f in latex_files]}")

    if 'all' in formats or 'html' in formats:
        html_file = generate_html_summary(cruise_data, output_dir)
        print(f"Generated HTML summary: {html_file.name}")

    if 'all' in formats or 'netcdf' in formats:
        netcdf_files = generate_netcdf_outputs(cruise_data, output_dir)
        print(f"Generated NetCDF datasets: {[f.name for f in netcdf_files]}")

    if 'all' in formats or 'kml' in formats:
        kml_file = generate_kml(cruise_data, output_dir)
        print(f"Generated KML file: {kml_file.name}")

    if 'all' in formats or 'map' in formats:
        map_file = generate_interactive_map(cruise_data, output_dir)
        print(f"Generated interactive map: {map_file.name}")

    print(f"\nAll outputs saved to: {output_dir}")
```

---

## Success Criteria

### Phase 3a Success Criteria
- [ ] LaTeX tables generate with proper booktabs formatting
- [ ] Coordinate formatting matches oceanographic standards (DD MM.mmm format)
- [ ] Page breaking works correctly for long tables
- [ ] Tables compile successfully in LaTeX engines
- [ ] All test cruises generate valid LaTeX output

### Phase 3b Success Criteria
- [ ] HTML reports display correctly in all major browsers
- [ ] Summary statistics calculate accurately for all test cases
- [ ] Navigation links function properly
- [ ] Tables are responsive and readable
- [ ] All cruise data aggregation works correctly

### Phase 3c Success Criteria
- [ ] NetCDF files pass CF-1.8 compliance validation
- [ ] All coordinate and depth data preserve precision
- [ ] Specialized datasets contain correct operation-specific data
- [ ] Files load successfully in common scientific software (xarray, Panoply)
- [ ] Global attributes contain complete metadata

### Phase 3d Success Criteria
- [ ] KML files display correctly in Google Earth
- [ ] Station icons use appropriate depth-based styling
- [ ] Cruise track shows complete route with transfers
- [ ] Popup descriptions contain all relevant information
- [ ] Folder organization improves navigation

### Phase 3e Success Criteria
- [ ] Interactive maps load and display correctly
- [ ] Bathymetry overlays integrate properly
- [ ] Station clustering works for dense operations
- [ ] Export functionality produces quality static images
- [ ] Backward compatibility maintained with existing API

### Overall Phase 3 Success
- [ ] All three test cruises generate outputs in all formats
- [ ] Data consistency maintained across all output formats
- [ ] CLI integration works seamlessly
- [ ] Performance meets requirements (< 30 seconds for complex cruises)
- [ ] Documentation updated with examples and usage
- [ ] Test coverage >= 85% for all output generators

---

This comprehensive implementation plan provides detailed specifications for building a complete output generation system that meets the professional standards required for oceanographic cruise planning. Each sub-phase builds upon the previous ones while maintaining data consistency and quality across all output formats.
