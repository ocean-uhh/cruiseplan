API Usage Examples
==================

This guide provides comprehensive examples for using CruisePlan programmatically through its Python API. These examples demonstrate how to integrate CruisePlan functionality into custom scripts, workflows, and applications.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

CruisePlan provides both command-line and programmatic interfaces. The Python API allows you to:

- Load and manipulate cruise configurations programmatically
- Integrate cruise planning into larger scientific workflows
- Build custom analysis tools and visualizations
- Automate batch processing of multiple cruises
- Extend functionality with custom plugins

**Core API Modules:**

- ``cruiseplan.core.cruise``: Main Cruise class and configuration loading
- ``cruiseplan.calculators``: Distance, duration, and routing calculations
- ``cruiseplan.output``: Multi-format output generation (HTML, NetCDF, maps)
- ``cruiseplan.data``: Bathymetry and PANGAEA data access
- ``cruiseplan.interactive``: Station picker and visualization tools

Basic Usage
-----------

Loading and Accessing Cruise Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from pathlib import Path

    # Load a cruise configuration from YAML file
    cruise_file = Path("my_cruise.yaml")
    cruise = Cruise(cruise_file)

    # Access cruise metadata
    print(f"Cruise name: {cruise.config.cruise_name}")
    print(f"Number of stations: {len(cruise.station_registry)}")

    # Iterate through stations
    for station_name, station_def in cruise.station_registry.items():
        print(f"Station {station_name}: {station_def.latitude:.4f}°N, {station_def.longitude:.4f}°E")
        print(f"  Operation: {station_def.operation_type}")
        if hasattr(station_def, 'depth') and station_def.depth:
            print(f"  Depth: {station_def.depth:.0f}m")

Working with Station Data
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    import pandas as pd

    # Load cruise and extract station data
    cruise = Cruise("cruise.yaml")

    # Create DataFrame of station information
    station_data = []
    for name, station in cruise.station_registry.items():
        station_data.append({
            'name': name,
            'latitude': station.latitude,
            'longitude': station.longitude,
            'depth': getattr(station, 'depth', None),
            'operation_type': station.operation_type,
            'action': getattr(station, 'action', None)
        })

    df = pd.DataFrame(station_data)
    print(df)

    # Calculate basic statistics
    print(f"Latitude range: {df['latitude'].min():.2f}° to {df['latitude'].max():.2f}°")
    print(f"Longitude range: {df['longitude'].min():.2f}° to {df['longitude'].max():.2f}°")
    print(f"Average depth: {df['depth'].mean():.0f}m")

Advanced Configuration Manipulation
------------------------------------

Programmatic Station Creation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.validation import StationDefinition, CruiseConfig
    from cruiseplan.utils.yaml_io import save_yaml
    from pathlib import Path

    # Create stations programmatically
    stations = []

    # Generate CTD transect
    for i, lat in enumerate(range(60, 71, 2)):  # 60°N to 70°N every 2°
        station = StationDefinition(
            name=f"CTD_{i+1:03d}",
            latitude=float(lat),
            longitude=-30.0,  # Fixed longitude
            operation_type="CTD",
            action="profile",
            comment=f"Transect station {i+1}"
        )
        stations.append(station)

    # Create cruise configuration
    cruise_config = {
        'cruise_name': "Programmatic_Transect_2024",
        'description': "Generated CTD transect",
        'first_station': stations[0].name,
        'last_station': stations[-1].name,
        'stations': [station.dict() for station in stations],
        'legs': [{
            'name': 'North_Atlantic_Transect',
            'strategy': 'sequential',
            'stations': [s.name for s in stations]
        }]
    }

    # Save to YAML file
    output_file = Path("generated_transect.yaml")
    save_yaml(cruise_config, output_file)
    print(f"Generated cruise configuration: {output_file}")

Batch Processing Multiple Configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.calculators.scheduler import generate_cruise_schedule
    from pathlib import Path
    import glob

    # Process all YAML files in a directory
    cruise_directory = Path("cruise_configs/")
    results = []

    for cruise_file in cruise_directory.glob("*.yaml"):
        try:
            print(f"Processing {cruise_file.name}...")
            
            # Load cruise
            cruise = Cruise(cruise_file)
            
            # Generate schedule
            timeline = generate_cruise_schedule(cruise.config, cruise.station_registry)
            
            # Extract summary statistics
            total_stations = len(cruise.station_registry)
            total_time = sum(activity.get('duration_hours', 0) for activity in timeline)
            
            results.append({
                'cruise_name': cruise.config.cruise_name,
                'file': cruise_file.name,
                'stations': total_stations,
                'duration_hours': total_time,
                'status': 'success'
            })
            
        except Exception as e:
            results.append({
                'cruise_name': cruise_file.stem,
                'file': cruise_file.name,
                'error': str(e),
                'status': 'failed'
            })

    # Summary report
    import pandas as pd
    df = pd.DataFrame(results)
    print("\nBatch Processing Summary:")
    print(df)
    print(f"\nSuccess rate: {(df['status'] == 'success').mean():.1%}")

Calculations and Analysis
-------------------------

Distance and Duration Calculations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.calculators.distance import haversine_distance
    from cruiseplan.calculators.duration import calculate_ctd_time, calculate_transit_time
    from cruiseplan.core.cruise import Cruise

    # Load cruise data
    cruise = Cruise("cruise.yaml")

    # Calculate distances between consecutive stations
    station_list = list(cruise.station_registry.values())
    total_distance = 0
    
    for i in range(len(station_list) - 1):
        current = station_list[i]
        next_station = station_list[i + 1]
        
        distance = haversine_distance(
            current.latitude, current.longitude,
            next_station.latitude, next_station.longitude
        )
        
        print(f"{current.name} → {next_station.name}: {distance:.1f} km")
        total_distance += distance

    print(f"Total cruise track distance: {total_distance:.1f} km")

    # Calculate operation durations
    for station in station_list:
        if station.operation_type == "CTD":
            duration = calculate_ctd_time(
                depth=getattr(station, 'depth', 2000),
                cast_type=getattr(station, 'action', 'profile')
            )
            print(f"{station.name} CTD duration: {duration:.0f} minutes")

Bathymetric Analysis
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.data.bathymetry import BathymetryManager
    from cruiseplan.core.cruise import Cruise
    import numpy as np
    import matplotlib.pyplot as plt

    # Load bathymetry and cruise data
    bathy = BathymetryManager()
    cruise = Cruise("cruise.yaml")

    # Extract depths for all stations
    station_depths = []
    station_names = []

    for name, station in cruise.station_registry.items():
        depth = bathy.get_depth(station.latitude, station.longitude)
        station_depths.append(depth)
        station_names.append(name)

    # Bathymetric analysis
    depths = np.array(station_depths)
    print(f"Depth statistics:")
    print(f"  Mean depth: {depths.mean():.0f}m")
    print(f"  Depth range: {depths.min():.0f}m to {depths.max():.0f}m")
    print(f"  Standard deviation: {depths.std():.0f}m")

    # Plot depth profile
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(depths)), depths, 'o-')
    plt.xlabel('Station Index')
    plt.ylabel('Water Depth (m)')
    plt.title(f'Bathymetric Profile: {cruise.config.cruise_name}')
    plt.gca().invert_yaxis()  # Convention: deeper water at bottom
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('bathymetric_profile.png', dpi=300)
    print("Saved bathymetric profile to bathymetric_profile.png")

Custom Output Generation
------------------------

Generating Custom Reports
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.calculators.scheduler import generate_cruise_schedule
    from jinja2 import Template
    import json

    # Load cruise and generate schedule
    cruise = Cruise("cruise.yaml")
    timeline = generate_cruise_schedule(cruise.config, cruise.station_registry)

    # Create custom summary report
    report_template = Template('''
    # Cruise Planning Report: {{ cruise_name }}

    ## Summary Statistics
    - **Total Stations**: {{ n_stations }}
    - **Estimated Duration**: {{ total_hours:.1f }} hours ({{ total_days:.1f }} days)
    - **Geographic Bounds**: {{ lat_range }} lat, {{ lon_range }} lon
    - **Operation Types**: {{ operation_types|join(', ') }}

    ## Station List
    {% for station in stations %}
    ### {{ station.name }}
    - **Location**: {{ "%.4f°N, %.4f°E"|format(station.latitude, station.longitude) }}
    - **Operation**: {{ station.operation_type }} ({{ station.action }})
    {% if station.depth -%}
    - **Depth**: {{ "%.0f"|format(station.depth) }}m
    {% endif -%}
    {% if station.comment -%}
    - **Notes**: {{ station.comment }}
    {% endif %}
    {% endfor %}

    ## Timeline Summary
    {% for activity in timeline[:10] %}  {# Show first 10 activities #}
    - **{{ activity.get('start_time', 'TBD') }}**: {{ activity.get('activity', 'Unknown') }} ({{ activity.get('duration_hours', 0):.1f }}h)
    {% endfor %}
    ''')

    # Prepare template data
    stations = list(cruise.station_registry.values())
    lats = [s.latitude for s in stations]
    lons = [s.longitude for s in stations]

    report_data = {
        'cruise_name': cruise.config.cruise_name,
        'n_stations': len(stations),
        'total_hours': sum(a.get('duration_hours', 0) for a in timeline),
        'total_days': sum(a.get('duration_hours', 0) for a in timeline) / 24,
        'lat_range': f"{min(lats):.1f}° to {max(lats):.1f}°",
        'lon_range': f"{min(lons):.1f}° to {max(lons):.1f}°",
        'operation_types': list(set(s.operation_type for s in stations)),
        'stations': stations,
        'timeline': timeline
    }

    # Generate and save report
    report = report_template.render(**report_data)
    with open('cruise_report.md', 'w') as f:
        f.write(report)

    print("Generated custom cruise report: cruise_report.md")

Custom Map Generation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.output.map_generator import generate_map_from_yaml
    from cruiseplan.data.bathymetry import BathymetryManager
    import matplotlib.pyplot as plt
    import numpy as np

    # Load cruise configuration
    cruise = Cruise("cruise.yaml")

    # Generate standard map
    map_file = generate_map_from_yaml(
        cruise,
        output_file="standard_cruise_map.png",
        bathymetry_source="gebco2025",
        figsize=(15, 10)
    )
    print(f"Generated standard map: {map_file}")

    # Create custom visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))

    # Panel 1: Geographic overview
    stations = list(cruise.station_registry.values())
    lats = [s.latitude for s in stations]
    lons = [s.longitude for s in stations]

    ax1.scatter(lons, lats, c='red', s=50, alpha=0.7)
    ax1.plot(lons, lats, 'b-', alpha=0.5, linewidth=1)
    ax1.set_xlabel('Longitude (°E)')
    ax1.set_ylabel('Latitude (°N)')
    ax1.set_title(f'Station Locations: {cruise.config.cruise_name}')
    ax1.grid(True, alpha=0.3)

    # Panel 2: Depth profile
    bathy = BathymetryManager()
    depths = [bathy.get_depth(s.latitude, s.longitude) for s in stations]

    ax2.plot(range(len(depths)), depths, 'o-', color='blue', linewidth=2)
    ax2.fill_between(range(len(depths)), depths, alpha=0.3, color='blue')
    ax2.set_xlabel('Station Index')
    ax2.set_ylabel('Water Depth (m)')
    ax2.set_title('Bathymetric Profile')
    ax2.invert_yaxis()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('custom_cruise_analysis.png', dpi=300, bbox_inches='tight')
    print("Generated custom analysis plot: custom_cruise_analysis.png")

Data Integration Examples
-------------------------

PANGAEA Data Integration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.data.pangaea import PangaeaStationProcessor
    from cruiseplan.core.cruise import Cruise
    import pandas as pd

    # Process PANGAEA data
    pangaea_processor = PangaeaStationProcessor()
    
    # Load historical data from DOI list
    doi_file = "historical_dois.txt"
    if Path(doi_file).exists():
        stations_db = pangaea_processor.process_doi_file(doi_file)
        print(f"Loaded {len(stations_db)} historical stations")
        
        # Convert to DataFrame for analysis
        historical_data = []
        for campaign_name, campaign_data in stations_db.items():
            for station in campaign_data.get('stations', []):
                historical_data.append({
                    'campaign': campaign_name,
                    'station': station.get('name', ''),
                    'latitude': station.get('latitude'),
                    'longitude': station.get('longitude'),
                    'depth': station.get('depth'),
                    'date': station.get('date')
                })
        
        historical_df = pd.DataFrame(historical_data)
        
        # Compare with current cruise plan
        cruise = Cruise("cruise.yaml")
        current_lats = [s.latitude for s in cruise.station_registry.values()]
        current_lons = [s.longitude for s in cruise.station_registry.values()]
        
        # Find historical stations near current planned locations
        tolerance = 0.1  # degrees
        nearby_historical = []
        
        for _, hist_station in historical_df.iterrows():
            for curr_lat, curr_lon in zip(current_lats, current_lons):
                distance = ((hist_station['latitude'] - curr_lat)**2 + 
                           (hist_station['longitude'] - curr_lon)**2)**0.5
                if distance <= tolerance:
                    nearby_historical.append({
                        'historical_campaign': hist_station['campaign'],
                        'historical_station': hist_station['station'],
                        'distance_degrees': distance,
                        'planned_location': f"{curr_lat:.3f}°N, {curr_lon:.3f}°E"
                    })
        
        if nearby_historical:
            nearby_df = pd.DataFrame(nearby_historical)
            print(f"\nFound {len(nearby_df)} historical stations near planned locations:")
            print(nearby_df)

Custom Workflow Automation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.calculators.scheduler import generate_cruise_schedule
    from cruiseplan.output.html_generator import generate_html_from_timeline
    from cruiseplan.output.netcdf_generator import generate_netcdf
    from pathlib import Path
    import shutil
    import logging

    def automated_cruise_processing(input_file: Path, output_dir: Path):
        """
        Complete automated processing workflow for a cruise configuration.
        """
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Load cruise
            logger.info(f"Loading cruise configuration: {input_file}")
            cruise = Cruise(input_file)
            
            # Generate timeline
            logger.info("Generating cruise timeline...")
            timeline = generate_cruise_schedule(cruise.config, cruise.station_registry)
            
            # Generate outputs
            outputs = {}
            
            # HTML schedule
            html_file = output_dir / f"{cruise.config.cruise_name}_schedule.html"
            generate_html_from_timeline(timeline, html_file)
            outputs['html'] = html_file
            logger.info(f"Generated HTML schedule: {html_file}")
            
            # NetCDF data
            netcdf_file = output_dir / f"{cruise.config.cruise_name}_data.nc"
            generate_netcdf(timeline, cruise.config, netcdf_file)
            outputs['netcdf'] = netcdf_file
            logger.info(f"Generated NetCDF data: {netcdf_file}")
            
            # Copy configuration
            config_copy = output_dir / f"{cruise.config.cruise_name}_config.yaml"
            shutil.copy2(input_file, config_copy)
            outputs['config'] = config_copy
            
            # Generate summary report
            summary = {
                'cruise_name': cruise.config.cruise_name,
                'total_stations': len(cruise.station_registry),
                'estimated_duration_hours': sum(a.get('duration_hours', 0) for a in timeline),
                'output_files': {k: str(v) for k, v in outputs.items()},
                'processing_status': 'success'
            }
            
            logger.info(f"Processing completed successfully for {cruise.config.cruise_name}")
            return summary
            
        except Exception as e:
            logger.error(f"Processing failed for {input_file}: {e}")
            return {
                'cruise_name': input_file.stem,
                'processing_status': 'failed',
                'error': str(e)
            }

    # Example usage
    if __name__ == "__main__":
        # Process multiple cruise configurations
        cruise_files = Path("input_cruises/").glob("*.yaml")
        results = []
        
        for cruise_file in cruise_files:
            output_dir = Path("processed_cruises") / cruise_file.stem
            result = automated_cruise_processing(cruise_file, output_dir)
            results.append(result)
        
        # Print summary
        print(f"\nProcessed {len(results)} cruise configurations:")
        for result in results:
            status = result['processing_status']
            name = result['cruise_name']
            if status == 'success':
                duration = result['estimated_duration_hours']
                print(f"✅ {name}: {duration:.1f} hours")
            else:
                error = result.get('error', 'Unknown error')
                print(f"❌ {name}: {error}")

Integration with External Tools
-------------------------------

Jupyter Notebook Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Example Jupyter notebook cell for interactive cruise analysis
    import ipywidgets as widgets
    from IPython.display import display, HTML
    from cruiseplan.core.cruise import Cruise
    from cruiseplan.interactive.station_picker import StationPicker
    import matplotlib.pyplot as plt

    # Interactive file selector
    cruise_files = list(Path(".").glob("*.yaml"))
    file_selector = widgets.Dropdown(
        options=[str(f) for f in cruise_files],
        description='Cruise file:'
    )

    # Analysis function
    def analyze_cruise(filename):
        cruise = Cruise(filename)
        
        # Display basic info
        print(f"Cruise: {cruise.config.cruise_name}")
        print(f"Stations: {len(cruise.station_registry)}")
        
        # Plot station map
        stations = list(cruise.station_registry.values())
        lats = [s.latitude for s in stations]
        lons = [s.longitude for s in stations]
        
        plt.figure(figsize=(10, 6))
        plt.scatter(lons, lats, c='red', s=50)
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title(f'Stations: {cruise.config.cruise_name}')
        plt.grid(True, alpha=0.3)
        plt.show()

    # Interactive widget
    interactive_plot = widgets.interact(analyze_cruise, filename=file_selector)

GIS Integration Example
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.output.kml_generator import generate_kml
    import geopandas as gpd
    from shapely.geometry import Point, LineString

    # Load cruise and generate KML
    cruise = Cruise("cruise.yaml")
    kml_file = generate_kml(cruise.config, cruise.station_registry, "cruise_track.kml")

    # Create GeoDataFrame for GIS analysis
    stations = list(cruise.station_registry.values())
    
    # Station points
    station_points = [Point(s.longitude, s.latitude) for s in stations]
    stations_gdf = gpd.GeoDataFrame({
        'name': [s.name for s in stations],
        'operation_type': [s.operation_type for s in stations],
        'latitude': [s.latitude for s in stations],
        'longitude': [s.longitude for s in stations]
    }, geometry=station_points, crs='EPSG:4326')

    # Cruise track
    track_coords = [(s.longitude, s.latitude) for s in stations]
    track_line = LineString(track_coords)
    track_gdf = gpd.GeoDataFrame({
        'cruise_name': [cruise.config.cruise_name]
    }, geometry=[track_line], crs='EPSG:4326')

    # Save as shapefiles for GIS use
    stations_gdf.to_file("cruise_stations.shp")
    track_gdf.to_file("cruise_track.shp")

    print("Generated GIS files:")
    print("- cruise_stations.shp (station points)")
    print("- cruise_track.shp (cruise track)")
    print(f"- {kml_file} (Google Earth KML)")

Best Practices
--------------

Error Handling
~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    from cruiseplan.core.validation import ValidationError
    import logging

    # Setup logging for debugging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    def safe_cruise_loading(filename):
        """
        Safely load a cruise configuration with comprehensive error handling.
        """
        try:
            cruise = Cruise(filename)
            logger.info(f"Successfully loaded cruise: {cruise.config.cruise_name}")
            return cruise
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {filename}")
            return None
            
        except ValidationError as e:
            logger.error(f"Validation error in {filename}: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error loading {filename}: {e}")
            return None

    # Usage with error checking
    cruise = safe_cruise_loading("my_cruise.yaml")
    if cruise:
        # Proceed with processing
        print(f"Processing {len(cruise.station_registry)} stations")
    else:
        print("Failed to load cruise configuration")

Memory Management
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.core.cruise import Cruise
    import gc

    def memory_efficient_batch_processing(cruise_files):
        """
        Process multiple cruises with careful memory management.
        """
        results = []
        
        for i, cruise_file in enumerate(cruise_files):
            print(f"Processing {i+1}/{len(cruise_files)}: {cruise_file}")
            
            # Load and process cruise
            cruise = Cruise(cruise_file)
            
            # Extract only needed data
            summary = {
                'name': cruise.config.cruise_name,
                'stations': len(cruise.station_registry),
                'file': cruise_file
            }
            results.append(summary)
            
            # Explicit cleanup for large datasets
            del cruise
            gc.collect()
            
            # Progress indicator
            if i % 10 == 0:
                print(f"Processed {i} configurations...")
        
        return results

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from cruiseplan.data.bathymetry import BathymetryManager
    import numpy as np

    # Efficient batch depth lookups
    def batch_depth_lookup(coordinates, bathymetry_manager=None):
        """
        Efficiently look up depths for multiple coordinates.
        """
        if bathymetry_manager is None:
            bathymetry_manager = BathymetryManager()
        
        # Pre-allocate array for results
        depths = np.zeros(len(coordinates))
        
        # Batch processing
        for i, (lat, lon) in enumerate(coordinates):
            depths[i] = bathymetry_manager.get_depth(lat, lon)
        
        return depths

    # Example usage
    station_coords = [(60.0, -30.0), (61.0, -31.0), (62.0, -32.0)]
    depths = batch_depth_lookup(station_coords)
    print(f"Depths: {depths}")

This comprehensive API documentation provides the foundation for integrating CruisePlan into scientific workflows, building custom tools, and extending functionality for specific research needs.