============
CLI Commands
============

Complete reference for all CruisePlan command-line tools.

Commands follow the typical cruise planning workflow:

1. **Setup** — download bathymetry data once before using the tool
2. **Pre-cruise planning** — collect historical data, place stations, process configuration, generate schedule
3. **Individual processing steps** — fine-grained control over enrichment, validation, and mapping
4. **At sea** — generate rolling workplans from a live schedule

---

Setup
=====

cruiseplan bathymetry
---------------------

Download a bathymetry dataset. Run this once before using any command that
draws maps or looks up water depths.

.. code-block:: bash

   cruiseplan bathymetry [-h] [--citation] [-o OUTPUT_DIR]
                         [--bathy-source SOURCE] [--verbose]

**Options:**

- ``--bathy-source SOURCE``: Dataset to download. Choices:

  - ``etopo2022`` — ETOPO 2022, 60 arc-second resolution (~500 MB)
  - ``gebco2023`` — GEBCO 2023, 15 arc-second resolution (~7.5 GB)
  - ``gebco2025`` — GEBCO 2025, 15 arc-second resolution (~7.5 GB) *(default)*

- ``-o, --output-dir DIR``: Save location (default: ``data/bathymetry``)
- ``--citation``: Print the data citation for the chosen source; does not download

**Examples:**

.. code-block:: bash

   # Download default GEBCO 2025 data
   cruiseplan bathymetry

   # Download the smaller ETOPO 2022 dataset
   cruiseplan bathymetry --bathy-source etopo2022

   # Show citation without downloading
   cruiseplan bathymetry --bathy-source gebco2025 --citation

---

Pre-cruise Planning
===================

cruiseplan pangaea
------------------

Search PANGAEA for historical station data in a geographic area, or process
an existing list of PANGAEA DOIs. Useful for finding prior cruise tracks in
your study region before planning new stations.

Two modes of operation:

- **Search mode** (``--lat`` and ``--lon`` required): query PANGAEA and download matching datasets
- **DOI file mode**: provide a ``.txt`` file of DOIs to download directly

.. code-block:: bash

   cruiseplan pangaea [-h] [--lat MIN MAX] [--lon MIN MAX] [--limit N]
                      [-o OUTPUT_DIR] [--output NAME]
                      [--rate-limit RATE] [--merge-campaigns] [--verbose]
                      query_or_file

**Arguments:**

- ``query_or_file``: Search query string (e.g. ``"CTD North Atlantic"``) or path to a ``.txt`` DOI file

**Options:**

- ``--lat MIN MAX``: Latitude bounds in decimal degrees N (required for search mode)
- ``--lon MIN MAX``: Longitude bounds in decimal degrees E (required for search mode)
- ``--limit N``: Maximum search results (default: 10; recommended maximum: 100)
- ``-o, --output-dir DIR``: Output directory (default: ``data``)
- ``--output NAME``: Base filename for outputs, without extension
- ``--rate-limit RATE``: PANGAEA API requests per second (default: 1.0)
- ``--merge-campaigns``: Combine datasets from the same campaign name (default: on)

**Outputs:** ``{name}_dois.txt`` (search mode) and ``{name}_stations.pkl``

**Examples:**

.. code-block:: bash

   # Search for CTD profiles in the subpolar North Atlantic
   cruiseplan pangaea "CTD" --lat 50 65 --lon -40 -10 --output north_atlantic

   # Process an existing DOI list
   cruiseplan pangaea my_dois.txt --output processed

cruiseplan stations
-------------------

Interactive station placement tool. Opens a map in the terminal where you can
place point stations, draw line transects, and define area operations. Saves
the result as a YAML cruise configuration file.

Optionally loads a PANGAEA ``.pkl`` file to show historical stations as
background context.

.. code-block:: bash

   cruiseplan stations [-h] [-p PANGAEA_FILE]
                       [--lat MIN MAX] [--lon MIN MAX] [--overwrite]
                       [-o OUTPUT_DIR]
                       [--bathy-source SOURCE] [--bathy-dir DIR]
                       [--bathy-stride N] [--bathy-contours DEPTH [DEPTH ...]]
                       [--max-depth METRES] [--verbose]
                       [CONFIG_FILE]

**Arguments:**

- ``CONFIG_FILE``: Existing YAML file to load and edit (optional; omit to start fresh)

**Options:**

- ``-p, --pangaea-file FILE``: PANGAEA stations pickle file (from ``cruiseplan pangaea``)
- ``--lat MIN MAX``: Initial map latitude extent in decimal degrees N (default: 45 70)
- ``--lon MIN MAX``: Initial map longitude extent in decimal degrees E (default: -65 -5)
- ``--overwrite``: Overwrite the output file without prompting
- ``-o, --output-dir DIR``: Output directory (default: ``data``)
- ``--bathy-stride N``: Bathymetry downsampling factor; higher is faster (default: 10)
- ``--max-depth METRES``: Depth ceiling for colour scale (useful for shelf seas)

**Interactive controls:**

- **p**: Place point stations
- **l**: Draw line transects
- **a**: Define area operations
- **u**: Undo last operation
- **y**: Save to YAML and exit
- **Escape**: Exit without saving

**Examples:**

.. code-block:: bash

   # New cruise, North Atlantic region
   cruiseplan stations --lat 58 65 --lon -35 -15 -o data/

   # Edit an existing configuration
   cruiseplan stations data/MSM142_draft.yaml

   # With PANGAEA historical context
   cruiseplan stations --lat 58 65 --lon -35 -15 \
       -p data/north_atlantic_stations.pkl

cruiseplan process
------------------

Unified configuration processing pipeline: enrichment + validation + map
generation in one command. This is the main pre-cruise processing step. Run it
after ``cruiseplan stations`` to add water depths, check the configuration for
errors, and produce a preview map.

.. code-block:: bash

   cruiseplan process [-h] [--no-enrich] [--no-validate] [--no-map]
                      [--no-depths] [--no-coords] [--no-sections]
                      [--no-depth-check] [--tolerance TOLERANCE]
                      [-o OUTPUT_DIR] [--output OUTPUT]
                      [--format FORMAT [FORMAT ...]]
                      [--bathy-source SOURCE] [--bathy-dir DIR]
                      [--bathy-stride N]
                      [--bathy-contours DEPTH [DEPTH ...]]
                      [--max-depth METRES]
                      [--lat MIN MAX] [--lon MIN MAX]
                      [--figsize WIDTH HEIGHT]
                      [--no-ports] [--no-title] [--no-labels] [--no-legend]
                      [--eez]
                      [--verbose] [--quiet]
                      CONFIG_FILE

**Arguments:**

- ``CONFIG_FILE``: Input YAML cruise configuration file

**Pipeline control:**

- ``--no-enrich``: Skip enrichment step
- ``--no-validate``: Skip validation step
- ``--no-map``: Skip map generation step

**Enrichment options** (used when ``--no-enrich`` is not set):

- ``--no-depths``: Skip adding bathymetry depths to stations
- ``--no-coords``: Skip adding formatted coordinate fields
- ``--no-sections``: Skip expanding CTD sections into individual stations

**Validation options:**

- ``--no-depth-check``: Skip checking whether existing depths match bathymetry
- ``--tolerance TOLERANCE``: Acceptable depth discrepancy in percent (default: 10.0)

**Output options:**

- ``-o, --output-dir DIR``: Output directory (default: ``data``)
- ``--output NAME``: Base filename for all outputs (default: derived from cruise name)
- ``--format FORMAT [FORMAT ...]``: Map formats to generate: ``png`` ``kml``
  (space-separated; omit to generate all)

**Map display options:**

- ``--figsize WIDTH HEIGHT``: Figure size in inches (default: 10 8.1)
- ``--lat MIN MAX``, ``--lon MIN MAX``: Map extent in decimal degrees
- ``--max-depth METRES``: Depth ceiling for bathymetry colour scale
- ``--bathy-contours DEPTH [DEPTH ...]``: Contour depths in metres
- ``--no-ports``, ``--no-title``, ``--no-labels``, ``--no-legend``: Suppress map elements
- ``--eez``: Overlay EEZ boundaries on PNG map (visualization only; data downloaded on first use)

**What it produces:**

- Enriched YAML: ``{name}_enriched.yaml``
- PNG map: ``{name}_map.png``
- KML file: ``{name}_map.kml``

**Examples:**

.. code-block:: bash

   # Full processing pipeline (recommended first run)
   cruiseplan process data/MSM142_stations.yaml

   # Skip map generation (faster; useful for validation only)
   cruiseplan process data/MSM142_stations.yaml --no-map

   # Custom output directory and filename
   cruiseplan process data/MSM142_stations.yaml -o results/ --output MSM142

   # Generate only PNG, not KML; restrict map extent
   cruiseplan process data/MSM142_stations.yaml --format png \
       --lat 58 68 --lon -35 -10

cruiseplan schedule
-------------------

Generate a cruise schedule from an enriched YAML configuration. Produces a
NetCDF schedule file (required for ``cruiseplan list`` and ``cruiseplan forecast``)
plus optional HTML, LaTeX, CSV, and PNG outputs.

Run ``cruiseplan process`` first to produce the enriched YAML input.

.. code-block:: bash

   cruiseplan schedule [-h] [--leg LEG] [--derive-netcdf]
                       [-o OUTPUT_DIR] [--output OUTPUT]
                       [--format FORMAT [FORMAT ...]]
                       [--bathy-source SOURCE] [--bathy-dir DIR]
                       [--bathy-stride N]
                       [--bathy-contours DEPTH [DEPTH ...]]
                       [--max-depth METRES]
                       [--lat MIN MAX] [--lon MIN MAX]
                       [--figsize WIDTH HEIGHT]
                       [--no-ports] [--no-title] [--no-labels] [--no-legend]
                       [--eez]
                       [--verbose]
                       CONFIG_FILE

**Arguments:**

- ``CONFIG_FILE``: Enriched YAML cruise configuration file (from ``cruiseplan process``)

**Options:**

- ``--leg LEG``: Process a single named leg only
- ``--derive-netcdf``: Also generate per-type NetCDF files
  (``_points.nc``, ``_lines.nc``, ``_areas.nc``)
- ``-o, --output-dir DIR``: Output directory (default: ``data``)
- ``--output NAME``: Base filename (default: derived from cruise name in config)
- ``--format FORMAT [FORMAT ...]``: Outputs to generate: ``html`` ``latex`` ``csv``
  ``netcdf`` ``png`` (space-separated; omit to generate all)

**Map display options** (same as ``cruiseplan process``):

- ``--figsize WIDTH HEIGHT``: Figure size in inches (default: 10 8.1)
- ``--lat MIN MAX``, ``--lon MIN MAX``: Map extent
- ``--max-depth METRES``, ``--bathy-contours DEPTH [DEPTH ...]``
- ``--no-ports``, ``--no-title``, ``--no-labels``, ``--no-legend``
- ``--eez``: Overlay EEZ boundaries on PNG map

**What it produces** (all formats):

- ``{name}_schedule.nc`` — NetCDF schedule (required for ``forecast`` and ``list``)
- ``{name}_schedule.html`` — Interactive HTML timeline
- ``{name}_schedule.tex`` — LaTeX station table
- ``{name}_schedule.csv`` — Tabular schedule
- ``{name}_schedule.png`` — PNG map with timeline

**Examples:**

.. code-block:: bash

   # Generate all output formats
   cruiseplan schedule data/MSM142_enriched.yaml

   # Generate only the NetCDF and HTML
   cruiseplan schedule data/MSM142_enriched.yaml --format netcdf html

   # Single leg, custom output directory
   cruiseplan schedule data/MSM142_enriched.yaml --leg leg_2 -o results/

---

Individual Processing Steps
============================

These commands run individual steps of the ``cruiseplan process`` pipeline.
Use them when you need finer control — for example, to re-validate after
manually editing the YAML, or to regenerate the map without re-enriching.

cruiseplan enrich
-----------------

Add computed fields to a cruise YAML: bathymetry depths, coordinate strings,
and CTD section expansion. Does not validate or generate maps.

.. code-block:: bash

   cruiseplan enrich [-h] [--add-depths] [--add-coords] [--expand-sections]
                     [-o OUTPUT_DIR]
                     [--bathy-source SOURCE] [--bathy-dir DIR] [--verbose]
                     CONFIG_FILE

**Arguments:**

- ``CONFIG_FILE``: Input YAML cruise configuration file

**Options:**

- ``--add-depths``: Look up water depths from bathymetry and add to each station
- ``--add-coords``: Add formatted coordinate fields (decimal minutes)
- ``--expand-sections``: Expand CTD section lines into individual station definitions
- ``-o, --output-dir DIR``: Output directory (default: ``data``)
- ``--bathy-source SOURCE``: Bathymetry dataset (default: ``gebco2025``)
- ``--bathy-dir DIR``: Local bathymetry data directory (default: ``data/bathymetry``)

**Example:**

.. code-block:: bash

   cruiseplan enrich data/MSM142_stations.yaml --add-depths --expand-sections

cruiseplan validate
-------------------

Check a cruise YAML configuration for errors and inconsistencies. Read-only:
does not modify any files.

.. code-block:: bash

   cruiseplan validate [-h] [--no-depth-check] [--tolerance TOLERANCE]
                       [--bathy-source SOURCE] [--bathy-dir DIR]
                       [--warnings-only] [--verbose]
                       CONFIG_FILE

**Arguments:**

- ``CONFIG_FILE``: Input YAML cruise configuration file

**Options:**

- ``--no-depth-check``: Skip comparing existing depth values against bathymetry
- ``--tolerance TOLERANCE``: Maximum acceptable depth discrepancy in percent (default: 10.0)
- ``--bathy-source SOURCE``: Bathymetry dataset for depth checks (default: ``gebco2025``)
- ``--bathy-dir DIR``: Local bathymetry data directory (default: ``data/bathymetry``)
- ``--warnings-only``: Report warnings but exit with code 0

**Example:**

.. code-block:: bash

   cruiseplan validate data/MSM142_enriched.yaml --tolerance 15.0

cruiseplan map
--------------

Generate a PNG map and/or KML file from a cruise YAML configuration.

.. code-block:: bash

   cruiseplan map [-h] [--no-ports] [--no-title] [--no-labels] [--no-legend]
                  [-o OUTPUT_DIR] [--output OUTPUT]
                  [--format FORMAT [FORMAT ...]]
                  [--bathy-source SOURCE] [--bathy-dir DIR] [--bathy-stride N]
                  [--figsize WIDTH HEIGHT] [--show-plot]
                  [--lat MIN MAX] [--lon MIN MAX]
                  [--bathy-contours DEPTH [DEPTH ...]] [--max-depth METRES]
                  [--eez]
                  [--verbose]
                  CONFIG_FILE

**Arguments:**

- ``CONFIG_FILE``: YAML cruise configuration file

**Options:**

- ``--format FORMAT [FORMAT ...]``: Outputs to generate: ``png`` ``kml``
  (space-separated; omit to generate all)
- ``-o, --output-dir DIR``: Output directory (default: ``data``)
- ``--output NAME``: Base filename (default: derived from config filename)
- ``--figsize WIDTH HEIGHT``: Figure size in inches (default: 10 8.1)
- ``--lat MIN MAX``, ``--lon MIN MAX``: Map extent in decimal degrees
- ``--max-depth METRES``: Depth ceiling for bathymetry colour scale
- ``--bathy-contours DEPTH [DEPTH ...]``: Contour depths in metres; replaces defaults
- ``--bathy-stride N``: Bathymetry downsampling factor; higher is faster (default: 5)
- ``--no-ports``, ``--no-title``, ``--no-labels``, ``--no-legend``: Suppress map elements
- ``--eez``: Overlay EEZ boundaries on PNG map (visualization only; data downloaded on first use)
- ``--show-plot``: Display the figure interactively instead of saving to file

**Examples:**

.. code-block:: bash

   # Generate both PNG and KML (default)
   cruiseplan map data/MSM142_enriched.yaml

   # PNG only, custom extent and contours
   cruiseplan map data/MSM142_enriched.yaml --format png \
       --lat 58 68 --lon -35 -10 --bathy-contours 500 1000 2000 3000

   # Large figure for printing
   cruiseplan map data/MSM142_enriched.yaml --figsize 20 16 -o figures/

---

At Sea
=======

These commands are used during the cruise once a NetCDF schedule has been
generated with ``cruiseplan schedule``. Run ``cruiseplan list`` to find activity
indices, then ``cruiseplan forecast`` to generate a rolling workplan from the
current ship position.

cruiseplan list
---------------

Print all activities in a schedule with their indices. Use the index values
as ``--start-index`` input to ``cruiseplan forecast``.

.. code-block:: bash

   cruiseplan list SCHEDULE_FILE

**Arguments:**

- ``SCHEDULE_FILE``: NetCDF schedule file produced by ``cruiseplan schedule``

**Output:** Table of index, time offset from start, category, duration (hours), and name.

**Example:**

.. code-block:: bash

   cruiseplan list data/MSM142_schedule.nc

cruiseplan forecast
-------------------

Generate a rolling station plan from a NetCDF schedule, starting from a given
activity at a new wall-clock time. Useful for updating the workplan at sea
as the ship's position changes.

Two modes of operation:

- **Forecast mode** (``--start-index`` and ``--start-time`` both provided): rolling
  workplan for the next N hours, re-anchored to a new start time
- **Static mode** (neither provided): full-schedule document (``--format tex`` or
  ``--format waypoints`` only)

.. code-block:: bash

   cruiseplan forecast [-h] [--start-index N] [--start-time DATETIME]
                       [--duration HOURS] [--transit-speed KNOTS]
                       [--current-position LAT,LON]
                       [--format {text,tex,waypoints,kml,png}]
                       [-o OUTPUT_DIR] [--output FILENAME]
                       [--logo PATH] [--number TEXT] [--title TEXT]
                       [--bathy-source SOURCE] [--bathy-dir DIR]
                       [--bathy-stride N]
                       [--figsize WIDTH HEIGHT]
                       [--max-depth METRES]
                       [--bathy-contours DEPTH [DEPTH ...]]
                       [--no-title] [--no-labels] [--no-legend]
                       [--lat MIN MAX] [--lon MIN MAX]
                       [--verbose]
                       SCHEDULE_FILE

**Arguments:**

- ``SCHEDULE_FILE``: NetCDF schedule file produced by ``cruiseplan schedule``

**Forecast mode options:**

- ``--start-index N``: Activity index to start from (0-based; see ``cruiseplan list``);
  required together with ``--start-time``
- ``--start-time DATETIME``: Wall-clock start time for that activity, ISO format
  (e.g. ``"2026-08-30T14:00:00"`` or ``"2026-08-30 14:00"``); required together
  with ``--start-index``
- ``--duration HOURS``: Forecast window in hours (default: 24)
- ``--transit-speed KNOTS``: Ship transit speed for text forecast (default: 10 kt)
- ``--current-position LAT,LON``: Current ship position in decimal degrees
  (e.g. ``"65.123,-30.456"``); used in waypoints output

**Output options:**

- ``--format``: ``text`` (default), ``tex``, ``waypoints``, ``kml``, ``png``
- ``-o, --output-dir DIR``: Output directory (default: current directory)
- ``--output FILENAME``: Output filename, relative to ``--output-dir``
  (default: stdout for text and waypoints)

**TeX output options** (``--format tex``):

- ``--logo PATH``: Logo image file for the workplan header (PNG, JPG, or PDF)
- ``--number TEXT``: Workplan number (e.g. ``28``)
- ``--title TEXT``: Cruise name (e.g. ``MSM142``)

**PNG map options** (``--format png``):

- ``--lat MIN MAX``, ``--lon MIN MAX``: Map extent in decimal degrees
- ``--max-depth METRES``: Depth ceiling for bathymetry colour scale
- ``--bathy-contours DEPTH [DEPTH ...]``: Contour depths in metres
- ``--no-title``, ``--no-labels``, ``--no-legend``: Suppress map elements
- ``--bathy-stride N``: Downsampling factor (default: 10)

**Examples:**

.. code-block:: bash

   # Step 1: find activity indices
   cruiseplan list data/MSM142_schedule.nc

   # Step 2: plain-text 24-hour forecast from activity 18
   cruiseplan forecast data/MSM142_schedule.nc \
       --start-index 18 --start-time "2026-08-30T14:00:00"

   # 36-hour forecast written to file
   cruiseplan forecast data/MSM142_schedule.nc \
       --start-index 5 --start-time "2026-08-29T08:00:00" \
       --duration 36 --output forecast.txt

   # Bridge waypoints with current ship position
   cruiseplan forecast data/MSM142_schedule.nc \
       --start-index 2 --start-time "2026-05-05 08:00" --duration 24 \
       --current-position "65.027,-31.370" \
       --format waypoints --output-dir route/ --output Stationsplan28.txt

   # TeX workplan with logo
   cruiseplan forecast data/MSM142_schedule.nc \
       --start-index 2 --start-time "2026-05-05 08:00" --duration 24 \
       --format tex --logo config/images/logo.png \
       --title "MSM142" --number "28" \
       --output-dir route/ --output Stationsplan28.tex

   # Static full-schedule TeX table (no start params)
   cruiseplan forecast data/MSM142_schedule.nc \
       --format tex --output station_plan.tex

---

Global Options
==============

All commands support:

- ``-h, --help``: Show help message and exit
- ``-V, --version``: Show version and exit (top-level ``cruiseplan -V`` only)

Commands with ``--verbose`` / ``-v``: ``bathymetry``, ``enrich``, ``forecast``,
``map``, ``pangaea``, ``process``, ``schedule``, ``stations``, ``validate``

Exit Codes
==========

- **0**: Success
- **1**: Error (configuration, validation, file I/O, network, etc.)

For worked examples see :doc:`../user-guide/workflows`.
