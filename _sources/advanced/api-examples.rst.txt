============
API Examples
============

This guide shows how to use CruisePlan's Python API for programmatic cruise planning.

Quick Start
===========

.. code-block:: python

    import cruiseplan
    
    # Download bathymetry data
    cruiseplan.bathymetry()
    
    # Search PANGAEA for historical data
    result = cruiseplan.pangaea("CTD", lat_bounds=[60, 70], lon_bounds=[-30, 0])
    
    # Load and process a cruise configuration
    cruise = cruiseplan.load_cruise("my_cruise.yaml")
    cruise.enrich()
    cruise.validate()

Core API Functions
==================

Data Acquisition
----------------

.. code-block:: python

    from cruiseplan.api.data import bathymetry, pangaea
    
    # Download bathymetry
    bathy_result = bathymetry(bathy_source="etopo2022", output_dir="data/bathymetry")
    print(f"Downloaded: {bathy_result.data_file}")
    
    # Search PANGAEA database
    pangaea_result = pangaea(
        query_terms="CTD temperature",
        lat_bounds=[60, 70],
        lon_bounds=[-30, 0],
        max_results=50
    )
    print(f"Found {len(pangaea_result.stations_data)} campaigns")

Cruise Configuration
--------------------

.. code-block:: python

    from cruiseplan.runtime.cruise import CruiseInstance
    
    # Load cruise from YAML file
    cruise = CruiseInstance("cruise_config.yaml")
    
    # Access configuration data
    print(f"Cruise: {cruise.config.cruise_name}")
    print(f"Start date: {cruise.config.start_date}")
    print(f"Number of points: {len(cruise.config.points or [])}")
    
    # Enrich with bathymetry data
    cruise.enrich_depths()
    
    # Add coordinate displays
    cruise.add_coordinate_displays()
    
    # Save processed configuration
    cruise.to_yaml("enriched_cruise.yaml")

Timeline Generation
-------------------

.. code-block:: python

    from cruiseplan.timeline.scheduler import generate_timeline
    
    # Generate cruise timeline
    timeline = generate_timeline(cruise)
    
    # Access timeline data
    print(f"Total duration: {timeline.total_duration_hours:.1f} hours")
    print(f"Number of operations: {len(timeline.operations)}")
    
    # Export timeline
    timeline.to_csv("cruise_timeline.csv")

Working with Operations
=======================

Creating Operations Programmatically
-------------------------------------

.. code-block:: python

    from cruiseplan.config.activities import PointDefinition, LineDefinition
    from cruiseplan.config.cruise_config import CruiseConfig
    
    # Create point operations
    points = [
        PointDefinition(
            name="CTD_001",
            latitude=60.0,
            longitude=-30.0,
            operation_type="ctd",
            duration=45
        ),
        PointDefinition(
            name="CTD_002", 
            latitude=61.0,
            longitude=-29.0,
            operation_type="ctd"
        )
    ]
    
    # Create cruise configuration
    config = CruiseConfig(
        cruise_name="API Generated Cruise",
        start_date="2025-06-15",
        points=points,
        legs=[{"name": "leg1", "activities": ["CTD_001", "CTD_002"]}]
    )
    
    # Create cruise instance
    cruise = CruiseInstance(config=config)

Distance and Duration Calculations
-----------------------------------

.. code-block:: python

    from cruiseplan.timeline.distance import haversine_distance
    from cruiseplan.timeline.duration import calculate_ctd_time, calculate_transit_time
    
    # Calculate distance between stations
    distance_km = haversine_distance(60.0, -30.0, 61.0, -29.0)
    print(f"Distance: {distance_km:.1f} km")
    
    # Calculate operation durations
    ctd_time = calculate_ctd_time(depth=3500, ctd_rate_m_s=1.0)
    transit_time = calculate_transit_time(distance_km, vessel_speed_kt=10.0)
    
    print(f"CTD time: {ctd_time:.0f} minutes")
    print(f"Transit time: {transit_time:.0f} minutes")

Output Generation
=================

HTML Timeline
-------------

.. code-block:: python

    from cruiseplan.output.html_generator import generate_html_timeline
    
    # Generate HTML timeline
    html_file = generate_html_timeline(
        timeline, 
        output_file="cruise_timeline.html",
        include_map=True
    )
    print(f"HTML timeline: {html_file}")

NetCDF Export
-------------

.. code-block:: python

    from cruiseplan.output.netcdf_generator import generate_netcdf
    
    # Export to NetCDF
    netcdf_file = generate_netcdf(
        cruise,
        timeline,
        output_file="cruise_data.nc"
    )
    print(f"NetCDF file: {netcdf_file}")

Maps and Visualizations
-----------------------

.. code-block:: python

    from cruiseplan.output.map_generator import generate_folium_map
    
    # Create interactive map
    map_file = generate_folium_map(
        cruise.get_all_positions(),
        output_file="cruise_map.html",
        include_bathymetry=True
    )

Working with PANGAEA Data
=========================

.. code-block:: python

    from cruiseplan.data.pangaea import PangaeaManager, load_campaign_data
    
    # Initialize PANGAEA manager
    manager = PangaeaManager()
    
    # Search for datasets
    datasets = manager.search(
        query="CTD North Atlantic",
        bbox=(-30, 60, 0, 70),  # min_lon, min_lat, max_lon, max_lat
        limit=20
    )
    
    # Load existing campaign data
    historical_data = load_campaign_data("data/historical_stations.pkl")
    print(f"Loaded {len(historical_data)} campaigns")

Error Handling
==============

.. code-block:: python

    from cruiseplan.config.exceptions import ValidationError, FileError
    
    try:
        cruise = CruiseInstance.from_yaml("cruise_config.yaml")
        cruise.validate()
        
    except ValidationError as e:
        print(f"Configuration error: {e}")
        
    except FileError as e:
        print(f"File error: {e}")
        
    except Exception as e:
        print(f"Unexpected error: {e}")

Integration Example
===================

Complete workflow using the API:

.. code-block:: python

    import cruiseplan
    from cruiseplan.runtime.cruise import CruiseInstance
    from cruiseplan.timeline.scheduler import generate_timeline
    
    # 1. Ensure bathymetry data is available
    cruiseplan.bathymetry()
    
    # 2. Load and process cruise configuration
    cruise = CruiseInstance.from_yaml("my_cruise.yaml")
    cruise.enrich()  # Add bathymetry depths
    cruise.validate()  # Check configuration
    
    # 3. Generate timeline
    timeline = generate_timeline(cruise)
    
    # 4. Create outputs
    cruiseplan.schedule_cruise(
        cruise_file="my_cruise.yaml",
        output_formats=["html", "netcdf", "csv"]
    )
    
    print(f"✅ Cruise '{cruise.config.cruise_name}' processed successfully!")
    print(f"Duration: {timeline.total_duration_hours:.1f} hours")

For complete API documentation, see :doc:`../api/modules`.