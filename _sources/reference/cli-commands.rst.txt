============
CLI Commands
============

Complete reference for all CruisePlan command-line tools.

Core Commands
=============

cruiseplan bathymetry
---------------------

Download bathymetry data (one-time setup).

.. code-block:: bash

   cruiseplan bathymetry [-h] [--citation] [-o OUTPUT_DIR] [--bathy-source {etopo2022,gebco2025}]

**Options:**

- ``--bathy-source {etopo2022,gebco2025}``: Data source (default: etopo2022)
- ``-o, --output-dir DIR``: Output directory (default: data/bathymetry)  
- ``--citation``: Show data citation information

**Examples:**

.. code-block:: bash

   # Download default ETOPO 2022 data (~500MB)
   cruiseplan bathymetry
   
   # Download high-resolution GEBCO 2025 (~7.5GB)
   cruiseplan bathymetry --bathy-source gebco2025

cruiseplan stations
-------------------

Interactive station placement tool.

.. code-block:: bash

   cruiseplan stations [-h] [-p PANGAEA_FILE] [--lat MIN MAX] [--lon MIN MAX] 
                       [--overwrite] [-o OUTPUT_DIR] [--bathy-source {etopo2022,gebco2025}] 
                       [--bathy-dir BATHY_DIR] [--high-resolution]

**Options:**

- ``--lat MIN MAX``: Latitude bounds for map view (default: 45 70)
- ``--lon MIN MAX``: Longitude bounds for map view (default: -65 -5)
- ``-o, --output-dir DIR``: Output directory (default: data)
- ``-p, --pangaea-file FILE``: PANGAEA historical data file

**Interactive Controls:**

- **p**: Place point stations
- **l**: Draw line transects
- **a**: Define area operations
- **u**: Undo last operation
- **y**: Save to YAML
- **Escape**: Exit without saving

**Examples:**

.. code-block:: bash

   # Basic station placement
   cruiseplan stations --lat 60 65 --lon -30 -20 --output-dir data
   
   # With historical PANGAEA context
   cruiseplan stations -p data/historical_stations.pkl --lat 60 65 --lon -30 -20

cruiseplan process  
------------------

Process and enrich cruise configuration.

.. code-block:: bash

   cruiseplan process [-h] -c CONFIG_FILE [--only-enrich] [--only-validate] 
                      [--only-map] [--no-enrich] [--no-validate] [--no-map] 
                      [--no-depths] [--no-coords] [--no-sections] [--no-ports] 
                      [--no-depth-check] [--tolerance TOLERANCE] [-o OUTPUT_DIR] 
                      [--output OUTPUT] [--format FORMAT] [--bathy-source {etopo2022,gebco2025}] 
                      [--bathy-dir BATHY_DIR] [--bathy-stride BATHY_STRIDE] 
                      [--figsize WIDTH HEIGHT] [--no-port-map] [--verbose] [--quiet]

**Options:**

- ``-c, --config-file FILE``: Input YAML configuration file (required)
- ``-o, --output-dir DIR``: Output directory (default: data)
- ``--output OUTPUT``: Base filename for outputs
- ``--no-enrich``: Skip enrichment step
- ``--no-validate``: Skip validation step
- ``--no-map``: Skip map generation step
- ``--figsize WIDTH HEIGHT``: Figure size for PNG maps in inches (default: 12 8)

**What it does:**

1. Loads YAML configuration
2. Adds bathymetry depths to stations
3. Validates configuration
4. Generates preview map
5. Saves enriched YAML

**Example:**

.. code-block:: bash

   cruiseplan process -c data/stations.yaml
   # Creates: data/{cruise_name}_enriched.yaml + data/{cruise_name}_map.png

cruiseplan schedule
-------------------

Generate cruise timeline and outputs.

.. code-block:: bash

   cruiseplan schedule [-h] -c {cruise_name}_enriched.yaml [--leg LEG] [--derive-netcdf] 
                       [-o OUTPUT_DIR] [--output OUTPUT] [--format {html,latex,csv,netcdf,png,all}] 
                       [--bathy-source {etopo2022,gebco2025}] [--bathy-dir BATHY_DIR] 
                       [--bathy-stride BATHY_STRIDE] [--figsize WIDTH HEIGHT]

**Options:**

- ``-c, --config-file FILE``: YAML cruise configuration file (required)
- ``-o, --output-dir DIR``: Output directory (default: data)
- ``--output OUTPUT``: Base filename for outputs
- ``--format FORMAT``: Output format: html,latex,csv,netcdf,png,all (default: all)
- ``--figsize WIDTH HEIGHT``: Figure size for PNG maps in inches (default: 12 8)

**Examples:**

.. code-block:: bash

   # Generate all output formats
   cruiseplan schedule -c {cruise_name}_enriched.yaml
   
   # Generate specific formats only
   cruiseplan schedule -c {cruise_name}_enriched.yaml --format html

Data Commands
=============

cruiseplan pangaea
------------------

Search and download PANGAEA historical data.

.. code-block:: bash

   cruiseplan pangaea [-h] [--lat MIN MAX] [--lon MIN MAX] [--limit LIMIT] 
                      [-o OUTPUT_DIR] [--output OUTPUT] [--rate-limit RATE_LIMIT] 
                      [--merge-campaigns] [--verbose] query_or_file

**Search Options:**

- ``--lat MIN MAX``: Latitude bounds
- ``--lon MIN MAX``: Longitude bounds  
- ``--limit N``: Maximum results (default: 10)
- ``--output NAME``: Base filename for outputs

**Processing Options:**

- ``--rate-limit RATE``: API requests per second (default: 1.0)
- ``--merge-campaigns``: Combine datasets from same cruise

**Examples:**

.. code-block:: bash

   # Search for CTD data in region
   cruiseplan pangaea "CTD" --lat 60 70 --lon -30 0 --output arctic_ctd
   # Creates: arctic_ctd_dois.txt and arctic_ctd_stations.pkl
   
   # Process existing DOI list
   cruiseplan pangaea my_dois.txt --output processed_data

Cruise Operations
=================

Commands used at sea once a schedule NetCDF has been generated.
Run ``cruiseplan list`` first to see activity indices, then ``cruiseplan forecast``
to generate a rolling workplan from the current ship position.

cruiseplan list
---------------

Display all activities in a schedule with their indices.

.. code-block:: bash

   cruiseplan list SCHEDULE_FILE

**Arguments:**

- ``SCHEDULE_FILE``: NetCDF schedule file produced by ``cruiseplan schedule``

**Output:**

Prints a table of all activities with index, time offset, category, duration (hours),
and name. Use the printed indices as ``--start-index`` values for ``cruiseplan forecast``.

**Example:**

.. code-block:: bash

   cruiseplan list schedule/MSM142_schedule.nc

cruiseplan forecast
-------------------

Generate rolling station plan forecasts from a NetCDF schedule.

Two modes of operation:

- **Forecast mode** (``--start-index`` and ``--start-time`` both required): produce a
  workplan for the next N hours starting from a given activity at a new wall-clock time.
- **Static mode** (no start params): generate a full-schedule document (``--format tex``
  or ``--format waypoints`` only).

.. code-block:: bash

   cruiseplan forecast [-h] SCHEDULE_FILE
                       [--start-index N] [--start-time DATETIME]
                       [--duration HOURS] [--transit-speed KNOTS]
                       [--current-position LAT,LON]
                       [--format {text,tex,waypoints,kml,png}]
                       [-o OUTPUT_DIR] [--output FILENAME]
                       [--logo PATH] [--number TEXT] [--title TEXT]
                       [--bathy-source ...] [--bathy-dir ...] [--bathy-stride N]
                       [--lat MIN MAX] [--lon MIN MAX]
                       [--max-depth METRES] [--bathy-contours DEPTH [DEPTH ...]]
                       [--no-title] [--no-labels] [--no-legend]
                       [--verbose]

**Arguments:**

- ``SCHEDULE_FILE``: NetCDF schedule file produced by ``cruiseplan schedule``

**Forecast mode options:**

- ``--start-index N``: Activity index to start from (0-based; see ``cruiseplan list``)
- ``--start-time DATETIME``: Wall-clock start time for that activity, ISO format
  (e.g. ``"2026-08-30T14:00:00"``); required together with ``--start-index``
- ``--duration HOURS``: Forecast window in hours (default: 24)
- ``--transit-speed KNOTS``: Ship transit speed for text forecast (default: 10 kt)
- ``--current-position LAT,LON``: Current ship position in decimal degrees
  (e.g. ``"65.123,-30.456"``); used in waypoints output

**Output options:**

- ``--format``: ``text`` (default), ``tex``, ``waypoints``, ``kml``, ``png``
- ``-o, --output-dir DIR``: Output directory (default: current directory)
- ``--output FILENAME``: Output filename, relative to ``--output-dir``
  (default: stdout for text/waypoints)

**TeX output options** (``--format tex``):

- ``--logo PATH``: Logo image file (PNG, JPG, PDF)
- ``--number TEXT``: Workplan number (e.g. ``28``)
- ``--title TEXT``: Cruise title (e.g. ``MSM142``)

**PNG map options** (``--format png``):

- ``--lat MIN MAX``, ``--lon MIN MAX``: Map extent in decimal degrees
- ``--max-depth METRES``: Depth ceiling for bathymetry colour scale
- ``--bathy-contours DEPTH [DEPTH ...]``: Contour depths in metres
- ``--no-title``, ``--no-labels``, ``--no-legend``: Suppress map elements
- ``--bathy-source``, ``--bathy-dir``, ``--bathy-stride``: Bathymetry data

**Examples:**

.. code-block:: bash

   # Step 1: see activity indices
   cruiseplan list schedule/MSM142_schedule.nc

   # Step 2: generate a 24-hour text forecast from activity 18
   cruiseplan forecast schedule/MSM142_schedule.nc \
       --start-index 18 --start-time "2026-08-30T14:00:00"

   # Forecast with current position, output to file
   cruiseplan forecast schedule/MSM142_schedule.nc \
       --start-index 5 --start-time "2026-08-29T08:00:00" \
       --current-position "65.123,-30.456" --duration 36 \
       --output forecast.txt

   # Bridge waypoints file
   cruiseplan forecast schedule/MSM142_schedule.nc \
       --start-index 2 --start-time "2026-05-05 08:00" --duration 24 \
       --current-position "65.027,-31.370" \
       --format waypoints --output-dir route --output Stationsplan28.txt

   # TeX workplan with logo
   cruiseplan forecast schedule/MSM142_schedule.nc \
       --start-index 2 --start-time "2026-05-05 08:00" --duration 24 \
       --current-position "65.027,-31.370" \
       --format tex --logo config/images/logo.png \
       --title "MSM142" --number "28" \
       --output-dir route --output Stationsplan28.tex

   # Static full-schedule TeX table (no start params)
   cruiseplan forecast schedule/MSM142_schedule.nc --format tex --output station_plan.tex

Individual Processing Commands
==============================

For advanced workflows, you can run processing steps individually:

cruiseplan enrich
-----------------

Add bathymetry depths to stations.

.. code-block:: bash

   cruiseplan enrich [-h] -c CONFIG_FILE [--add-depths] [--add-coords] 
                  [--expand-sections] [-o OUTPUT_DIR] [--output OUTPUT] 
                  [--bathy-source {etopo2022,gebco2025}] [--bathy-dir BATHY_DIR] [--verbose]

cruiseplan validate
-------------------

Validate cruise configuration.

.. code-block:: bash

   cruiseplan validate [-h] -c CONFIG_FILE [--no-depth-check] [--tolerance TOLERANCE]

cruiseplan map
--------------

Generate cruise map.

.. code-block:: bash

   cruiseplan map [-h] -c CONFIG_FILE [--no-ports] [-o OUTPUT_DIR] [--output OUTPUT] 
               [--format {png,kml,all}] [--bathy-source {etopo2022,gebco2025}] 
               [--bathy-dir BATHY_DIR] [--bathy-stride BATHY_STRIDE] 
               [--figsize WIDTH HEIGHT] [--show-plot] [--verbose]

Global Options
==============

All commands support:

- ``-h, --help``: Show help message
- ``--version``: Show version information

Commands with verbose logging:

- ``cruiseplan process --verbose``: Enable detailed logging
- ``cruiseplan pangaea --verbose``: Enable detailed logging  
- ``cruiseplan enrich --verbose``: Enable detailed logging
- ``cruiseplan map --verbose``: Enable detailed logging

Exit Codes
==========

- **0**: Success
- **1**: Error (configuration, validation, file I/O, network, etc.)

For examples and workflows, see :doc:`../user-guide/workflows`.