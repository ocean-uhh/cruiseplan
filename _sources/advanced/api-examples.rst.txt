============
API Examples
============

This guide shows how to use CruisePlan's Python API for programmatic cruise planning.

Quick Start
===========

The simplest workflow: process a YAML configuration and generate a schedule.

.. code-block:: python

    import cruiseplan

    # Process configuration (enrich + validate + map)
    process_result = cruiseplan.process("my_cruise.yaml")

    # Generate schedule from the enriched config
    schedule_result = cruiseplan.schedule(process_result.config)

    print(f"Files created: {schedule_result.files_created}")

Or combine both steps with ``cruiseplan.run``:

.. code-block:: python

    import cruiseplan

    process_result, schedule_result = cruiseplan.run("my_cruise.yaml")

    print(f"Process files: {process_result.files_created}")
    print(f"Schedule files: {schedule_result.files_created}")

Top-Level API
=============

All public functions are importable directly from ``cruiseplan``.

Bathymetry
----------

.. code-block:: python

    import cruiseplan

    # Download bathymetry data (gebco2025 by default)
    result = cruiseplan.bathymetry(bathy_source="gebco2025", output_dir="data/bathymetry")
    print(f"Downloaded: {result.data_file}")

PANGAEA Search
--------------

.. code-block:: python

    import cruiseplan

    result = cruiseplan.pangaea(
        query_terms="CTD temperature",
        lat_bounds=[60, 70],
        lon_bounds=[-30, 0],
        max_results=50,
    )
    print(f"Found {len(result.stations_data)} campaigns")

Enrich
------

.. code-block:: python

    import cruiseplan

    result = cruiseplan.enrich(
        config_file="cruise.yaml",
        add_depths=True,
        add_coords=True,
        expand_sections=True,
    )
    print(f"Enriched config: {result.output_file}")

Validate
--------

.. code-block:: python

    import cruiseplan

    result = cruiseplan.validate("cruise_enriched.yaml")
    if result.success:
        print("Configuration is valid")
    else:
        print(f"Errors: {result.errors}")

Process
-------

.. code-block:: python

    import cruiseplan

    result = cruiseplan.process(
        config_file="cruise.yaml",
        output_dir="data",
        add_depths=True,
        add_coords=True,
    )
    print(f"Enriched config: {result.config}")
    print(f"Files: {result.files_created}")

Schedule
--------

.. code-block:: python

    import cruiseplan

    result = cruiseplan.schedule(
        config_file="cruise_enriched.yaml",
        output_dir="data",
    )
    print(f"Timeline entries: {len(result.timeline)}")
    print(f"Files: {result.files_created}")

Run (process + schedule)
------------------------

.. code-block:: python

    import cruiseplan

    process_result, schedule_result = cruiseplan.run(
        config_file="cruise.yaml",
        output_dir="data",
        bathy_source="gebco2025",
        include_eez=True,
    )

Map
---

.. code-block:: python

    import cruiseplan

    result = cruiseplan.map(
        config_file="cruise.yaml",
        output_dir="data",
        figsize=[14, 10],
        include_eez=True,
    )
    print(f"Map files: {result.files_created}")

Result Types
============

Each API function returns a typed result object:

.. code-block:: python

    from cruiseplan.api.types import ProcessResult, ScheduleResult, EnrichResult

    process_result: ProcessResult = cruiseplan.process("cruise.yaml")
    process_result.config          # Path to enriched YAML, or None if process failed
    process_result.files_created   # list[Path]
    process_result.summary         # dict with run metadata

    schedule_result: ScheduleResult = cruiseplan.schedule("cruise_enriched.yaml")
    schedule_result.timeline        # list[dict] — one entry per activity
    schedule_result.files_created   # list[Path]
    schedule_result.summary         # dict with run metadata

Advanced: CruiseInstance
========================

For direct access to the enrichment and scheduling machinery:

.. code-block:: python

    from cruiseplan.runtime.cruise import CruiseInstance

    # Load from YAML
    cruise = CruiseInstance("cruise_config.yaml")

    # Access configuration data
    print(f"Cruise: {cruise.config.cruise_name}")
    print(f"Start date: {cruise.config.start_date}")

    # Add bathymetry depths to stations
    cruise.enrich_depths()

    # Add formatted coordinate fields (DDM)
    cruise.add_coordinate_displays()

    # Save processed configuration
    cruise.to_yaml("enriched_cruise.yaml")

Timeline Generation
-------------------

.. code-block:: python

    from cruiseplan.timeline import generate_timeline

    # Returns list[dict] — one dict per scheduled activity
    timeline = generate_timeline(cruise)

    # Inspect individual activities
    for entry in timeline:
        print(entry.get("name"), entry.get("start_time"), entry.get("duration_hours"))

Distance Calculations
=====================

.. code-block:: python

    from cruiseplan.timeline.distance import haversine_distance

    # Distance between two points in kilometres
    distance_km = haversine_distance((60.0, -30.0), (61.0, -29.0))
    print(f"Distance: {distance_km:.1f} km")

Working with PANGAEA Data
=========================

.. code-block:: python

    from cruiseplan.data.pangaea import PangaeaManager, load_campaign_data

    # Search for datasets
    manager = PangaeaManager()
    datasets = manager.search(
        query="CTD North Atlantic",
        bbox=(-30, 60, 0, 70),  # min_lon, min_lat, max_lon, max_lat
        limit=20,
    )

    # Load previously downloaded campaign data
    historical_data = load_campaign_data("data/historical_stations.pkl")
    print(f"Loaded {len(historical_data)} campaigns")

Error Handling
==============

.. code-block:: python

    from cruiseplan.config.exceptions import ValidationError, FileError
    from cruiseplan.runtime.cruise import CruiseInstance

    try:
        cruise = CruiseInstance("cruise_config.yaml")

    except ValidationError as e:
        print(f"Configuration error: {e}")

    except FileError as e:
        print(f"File error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")

For complete API documentation, see :doc:`../api/modules`.
