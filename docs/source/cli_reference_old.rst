CLI Command Reference
=====================

This document provides a comprehensive reference for the `cruiseplan` command-line interface, detailing available subcommands and their required and optional arguments.

General Usage
-------------

The `cruiseplan` CLI uses a "git-style" subcommand architecture.

.. code-block:: bash

    usage: cruiseplan [-h] [--version] {download,schedule,stations,enrich,validate,pandoi,map,pangaea} ...

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-h, --help``
     - Show the program's main help message and exit.
   * - ``--version``
     - Show the program's version number and exit.


**Workflow**

The general workflow follows these steps in order:

1. **Data preparation:** :ref:`subcommand-download` - Download bathymetry and external datasets
2. **Historical integration:** :ref:`subcommand-pandoi` - Search PANGAEA datasets by query and bounds  
3. **Historical integration:** :ref:`subcommand-pangaea` - Process PANGAEA DOI lists into campaign datasets
4. **Cruise configuration:** :ref:`subcommand-stations` - Interactive station planning interface
5. **Cruise configuration:** :ref:`subcommand-enrich` - Add depths, coordinates, and expand sections
6. **Cruise configuration:** :ref:`subcommand-validate` - Validate configuration files
7. **Cruise configuration:** :ref:`subcommand-map` - Generate standalone PNG cruise maps
8. **Schedule generation:** :ref:`subcommand-schedule` - Generate cruise timeline and outputs


**Examples:**

The command-line interface provides eight main subcommands for different aspects of cruise planning.

.. code-block:: bash

    $ cruiseplan download 
    $ cruiseplan pandoi "CTD" --lat 50 60 --lon -50 -40 --limit 20 -o data/cruise1/
    $ cruiseplan pangaea doi_list.txt -o data/cruise1/
    $ cruiseplan stations --lat 50 65 --lon -60 -30 -o data/cruise1/
    $ cruiseplan enrich -c data/cruise1/cruise.yaml --add-depths --add-coords
    $ cruiseplan validate -c cruise.yaml --check-depths
    $ cruiseplan map -c cruise.yaml --figsize 14 10
    $ cruiseplan schedule -c cruise.yaml -o results/


.. figure:: _static/screenshots/cli_help_overview.png
   :alt: CruisePlan CLI help overview showing all available commands
   :width: 700px
   :align: center
   
   Complete overview of CruisePlan CLI commands and their purposes




----

Subcommands
-----------

.. note:: For detailed help on any subcommand, use: ``cruiseplan <command> --help``

.. _subcommand-download:

`download` 
^^^^^^^^^^ 

Download and manage external data assets required by CruisePlan, such as bathymetry grids and other geospatial datasets.

.. code-block:: bash

    usage: cruiseplan download [-h] [--bathymetry-source {etopo2022,gebco2025}] 
                               [--citation] [-o OUTPUT_DIR]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-h, --help``
     - Show this help message and exit.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset to download (default: ``etopo2022``).
   * - ``--citation``
     - Show citation information for the bathymetry source without downloading.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory for bathymetry files (default: ``data/bathymetry``).

**Description:**

This command downloads bathymetry datasets required for depth calculations and bathymetric visualization in cruise planning. Two datasets are available:

- **ETOPO 2022**: Global bathymetry at 60-second resolution (~500MB) - suitable for most applications
- **GEBCO 2025**: High-resolution global bathymetry at 15-second resolution (~7.5GB) - provides enhanced detail for detailed planning

The datasets are cached locally in the ``data/bathymetry/`` directory.

**Available Sources:**

.. list-table::
   :widths: 20 20 20 40

   * - **Source**
     - **Resolution**
     - **File Size**
     - **Description**
   * - ``etopo2022``
     - 60 seconds
     - ~500MB
     - Standard resolution bathymetry (default)
   * - ``gebco2025``
     - 15 seconds
     - ~7.5GB
     - High-resolution bathymetry for detailed analysis

**Examples:**

.. code-block:: bash

    # Download default ETOPO 2022 bathymetry
    $ cruiseplan download
    
    # Download ETOPO 2022 explicitly
    $ cruiseplan download --bathymetry-source etopo2022
    
    # Download high-resolution GEBCO 2025 bathymetry
    $ cruiseplan download --bathymetry-source gebco2025

.. figure:: _static/screenshots/download_bathymetry.png
   :alt: Bathymetry download progress with citation information
   :width: 600px
   :align: center
   
   Bathymetry download process showing progress bars
   
The download command shows progress information and provides proper citation details for the bathymetry datasets.

----

.. _subcommand-pandoi:

`pandoi` 
^^^^^^^^ 

Search PANGAEA datasets by query terms and geographic bounding box, generating a DOI list for subsequent use with the ``pangaea`` command.

.. code-block:: bash

    usage: cruiseplan pandoi [-h] [--lat MIN MAX] [--lon MIN MAX] [--limit LIMIT] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--verbose] query

**Arguments:**

.. list-table::
   :widths: 30 70

   * - ``query``
     - **Required.** Search query string (e.g., 'CTD', 'temperature', 'Arctic Ocean').

**Options:**

.. list-table::
   :widths: 30 70

   * - ``--lat MIN MAX``
     - Latitude bounds (e.g., ``--lat 50 70``).
   * - ``--lon MIN MAX``
     - Longitude bounds (e.g., ``--lon -60 -30``).
   * - ``--limit LIMIT``
     - Maximum number of results to return (default: ``10``).
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path (overrides ``-o``/``--output-dir``).
   * - ``--verbose, -v``
     - Enable verbose logging.

**Description:**

This command searches the PANGAEA database for oceanographic datasets using text queries and optional geographic constraints. It outputs a text file containing DOI identifiers that can be used with the ``cruiseplan pangaea`` command to fetch and process the actual datasets.

**Query Examples:**

.. list-table::
   :widths: 40 60
   
   * - **Query Type**
     - **Example**
   * - Instrument/Method
     - ``"CTD"``, ``"XBT"``, ``"ADCP"``, ``"Rosette"``
   * - Parameter
     - ``"temperature"``, ``"salinity"``, ``"oxygen"``, ``"nutrients"``
   * - Geographic Region
     - ``"Arctic Ocean"``, ``"North Atlantic"``, ``"Mediterranean Sea"``
   * - Campaign/Vessel
     - ``"Polarstern"``, ``"PS122"``, ``"Maria S. Merian"``
   * - Combined Terms
     - ``"CTD Arctic Ocean"``, ``"temperature Polarstern"``

**Finding Query Terms:**

PANGAEA uses flexible text search, so you can be generous with your search terms. For discovery of relevant terms:

- Visit https://www.pangaea.de/?t=Oceans to browse oceanographic datasets
- Check the left sidebar filters for common parameter names, regions, and methods
- PANGAEA doesn't enforce strict controlled vocabularies, so variations work:
  
  - ``"CTD"`` or ``"CTD/Rosette"`` or ``"conductivity temperature depth"``
  - ``"temp"`` or ``"temperature"`` or ``"sea water temperature"``
  - ``"North Atlantic"`` or ``"Nordic Seas"`` or ``"Labrador Sea"``

**Search Strategy Tips:**

- **Start broad**: Use general terms like ``"CTD"`` or ``"temperature"`` first
- **Refine geographically**: Add geographic bounds with ``--lat`` and ``--lon`` 
- **Combine terms**: ``"CTD temperature Arctic"`` finds datasets with all terms
- **Try variations**: If ``"nutrients"`` returns few results, try ``"nitrate"`` or ``"phosphate"``
- **Use quotes**: For exact phrases like ``"sea surface temperature"``
- **Iterate**: Start with ``--limit 10``, review results, then adjust terms and increase limit
- **Be generous**: PANGAEA's search is forgiving - ``"temp"`` will find temperature datasets

**Geographic Bounds Format:**

The ``--lat`` and ``--lon`` parameters specify geographic search bounds:

- ``--lat MIN MAX``: Latitude bounds from MIN to MAX degrees (-90 to 90)
- ``--lon MIN MAX``: Longitude bounds supporting two coordinate systems:
  
  - **-180 to 180 format**: West longitudes negative, East positive (standard)
  - **0 to 360 format**: All longitudes positive, 0° = Prime Meridian, 180° = Date Line
  - **Cannot mix formats**: Both values must use the same system

- Examples: 
  
  - ``--lat 50 60 --lon -50 -40`` covers 50°N-60°N, 50°W-40°W (standard format)
  - ``--lat 50 60 --lon 310 320`` covers 50°N-60°N, 50°W-40°W (0-360 format)
  - ``--lat 50 60 --lon 350 10`` covers 50°N-60°N, crossing 0° meridian (valid in 0-360)

**Examples:**

.. code-block:: bash

    # Search for CTD data globally (saves to data/ directory)
    $ cruiseplan pandoi "CTD"
    
    # Search for temperature data in the North Atlantic
    $ cruiseplan pandoi "temperature" --lat 50 70 --lon -50 -10 --limit 25
    
    # Broad search with multiple terms
    $ cruiseplan pandoi "CTD temperature salinity" --lat 60 80 --lon -40 20 --limit 30
    
    # Search for Polarstern expedition data with custom output file
    $ cruiseplan pandoi "PS122" --output-file data/polarstern_ps122_dois.txt
    
    # Try different term variations if first search is too narrow
    $ cruiseplan pandoi "nutrients nitrate phosphate" --lat 45 65 --lon -60 -20
    
    # Detailed search with verbose output
    $ cruiseplan pandoi "Arctic Ocean CTD" --lat 70 90 --lon -180 180 --limit 50 --verbose

**Workflow Integration:**

The ``pandoi`` command is designed to work with the ``pangaea`` command:

.. code-block:: bash

    # Step 1: Search for datasets and save DOI list to specific file
    $ cruiseplan pandoi "CTD temperature" --lat 60 70 --lon -50 -30 --output-file data/arctic_ctd_dois.txt
    
    # Step 2: Fetch and process the datasets
    $ cruiseplan pangaea data/arctic_ctd_dois.txt --output-dir data/
    
    # Step 3: Use in station planning
    $ cruiseplan stations --pangaea-file data/arctic_ctd_dois_pangaea_data.pkl


----

.. _subcommand-pangaea:

`pangaea` 
^^^^^^^^^^ 

Processes a list of PANGAEA DOIs, aggregates coordinates by campaign, and outputs a searchable dataset.

.. code-block:: bash

    usage: cruiseplan pangaea [-h] [-o OUTPUT_DIR] [--rate-limit RATE_LIMIT] [--merge-campaigns] [--output-file OUTPUT_FILE] doi_file

**Arguments:**

.. list-table::
   :widths: 30 70

   * - ``doi_file``
     - **Required.** Text file with PANGAEA DOIs (one per line).

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data/``).
   * - ``--rate-limit RATE_LIMIT``
     - API request rate limit (requests per second, default: ``1.0``).
   * - ``--merge-campaigns``
     - Merge campaigns with the same name.
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path for the pickled dataset.

**Examples:**

.. code-block:: bash

    # Process DOIs from file with default settings
    $ cruiseplan pangaea dois.txt

    # Process with custom output directory and rate limiting
    $ cruiseplan pangaea dois.txt -o data/pangaea --rate-limit 0.5

    # Merge campaigns and save to specific file
    $ cruiseplan pangaea dois.txt --merge-campaigns --output-file pangaea_stations.pkl

The command will create a pickled file containing processed PANGAEA station data that can be used with the ``cruiseplan stations`` command for interactive station planning.

----

.. _subcommand-stations:

`stations` 
^^^^^^^^^^ 

Launch the interactive graphical interface for planning stations and transects with optional PANGAEA data background.

.. code-block:: bash

    usage: cruiseplan stations [-h] [-p PANGAEA_FILE] [--lat MIN MAX] [--lon MIN MAX] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--bathymetry-source {etopo2022,gebco2025}] [--high-resolution] [--overwrite]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-p PANGAEA_FILE, --pangaea-file PANGAEA_FILE``
     - Path to the pickled PANGAEA campaigns file.
   * - ``--lat MIN MAX``
     - Latitude bounds for the map view (default: ``45 70``).
   * - ``--lon MIN MAX``
     - Longitude bounds for the map view (default: ``-65 -5``).
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory for the generated station YAML (default: ``data``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path for the generated YAML.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset to use for depth lookups (default: ``etopo2022``).
   * - ``--high-resolution``
     - Use full resolution bathymetry in the interactive interface (slower but more detailed).
   * - ``--overwrite``
     - Overwrite existing output file without prompting.

.. warning::
   **Performance Notice:** The combination of ``--bathymetry-source gebco2025`` with ``--high-resolution`` can be very slow for interactive use. GEBCO 2025 is a high-resolution dataset (~7.5GB) and processing it without downsampling creates significant lag during station placement and map interaction.
   
   **Recommended workflow:**
   - Use ``--bathymetry-source etopo2022`` (default) for initial interactive planning
   - Reserve GEBCO 2025 high-resolution for final detailed work only
   - Consider standard resolution (default) for GEBCO 2025 during interactive sessions

----

.. _subcommand-enrich:

`enrich` 
^^^^^^^^ 

Adds missing or computed data (like depth or formatted coordinates) to a configuration file. Can also expand CTD sections into individual station definitions.

.. code-block:: bash

    usage: cruiseplan enrich [-h] -c CONFIG_FILE [--add-depths] [--add-coords] [--expand-sections] [--expand-ports] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [...]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** Input YAML configuration file.
   * - ``--add-depths``
     - Add missing ``water_depth`` values to stations using bathymetry data. Only adds depths to stations that lack depth information - does not overwrite existing depth values. Skipping this flag (``add_depths=False``) is unnecessary if your configuration already contains depth information.
   * - ``--add-coords``
     - Add formatted coordinate fields (currently DMM; DMS not yet implemented).
   * - ``--expand-sections``
     - Expand CTD sections defined in ``transits`` into individual station definitions with spherical interpolation.
   * - ``--expand-ports``
     - Expand global port references into inline port definitions within legs.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset (default: ``etopo2022``).
   * - ``--coord-format {dmm,dms}``
     - Format for adding coordinates (default: ``dmm``).
   * - ``--backup``
     - Create backup of original file before enriching.
   * - ``-v, --verbose``
     - Enable verbose logging output.

**CTD Section Expansion:**

The ``--expand-sections`` option processes CTD section transits and converts them into individual station definitions:

.. code-block:: yaml

    # Input: CTD section definition
    transits:
      - name: "Arctic_Section_1"
        operation_type: "ctd_section"
        spacing_km: 25.0
        max_depth: 4000.0
        route:
          - latitude: 75.0
            longitude: -15.0
          - latitude: 78.0  
            longitude: -8.0

    # Output: Individual stations created
    stations:
      - name: "Arctic_Section_1_001"
        position:
          latitude: 75.0
          longitude: -15.0
        operation_type: "CTD"
        action: "profile"
        depth: 4000.0
      - name: "Arctic_Section_1_002"
        position:
          latitude: 75.59  # Spherical interpolation
          longitude: -13.68
        operation_type: "CTD" 
        action: "profile"
        depth: 4000.0
      # ... additional stations along the route

**Key Features:**

- Uses great circle interpolation for accurate positioning along curved Earth surface
- Automatically generates unique station names with sequential numbering
- Preserves original transit metadata (max_depth becomes station depth)
- Handles name collisions by appending incremental suffixes
- Updates leg definitions to reference the newly created stations
- **Automatic Anchor Resolution**: Updates ``first_waypoint`` and ``last_waypoint`` fields in legs to reference the first and last generated stations from the expanded section

**Leg-Level Anchor Field Updates:**

When ``--expand-sections`` processes a CTD section transit, it automatically updates any leg definitions that reference the transit name:

- ``first_waypoint``: Updated to reference the first generated station (e.g., "OVIDE_Section" → "OVIDE_Section_001")  
- ``last_waypoint``: Updated to reference the last generated station (e.g., "OVIDE_Section" → "OVIDE_Section_040")
- ``activities``: Expanded to include all generated stations in sequential order

This ensures that leg routing and scheduling work correctly with the newly created individual station definitions, maintaining the original intent while providing the detailed station-by-station planning required for cruise execution.

**Port Expansion:**

The ``--expand-ports`` option converts global port references into inline port definitions within each leg:

.. code-block:: yaml

    # Input: Global port references
    ports:
      port_reykjavik:
        name: "Reykjavik"
        latitude: 64.1466
        longitude: -21.9426
        timezone: "Atlantic/Reykjavik"
    
    legs:
      - name: "Atlantic_Survey"
        departure_port: port_reykjavik  # Reference to global port
        arrival_port: port_reykjavik
        
    # Output: Inline port definitions
    legs:
      - name: "Atlantic_Survey"
        departure_port:
          name: "Reykjavik"
          latitude: 64.1466
          longitude: -21.9426
          timezone: "Atlantic/Reykjavik"
        arrival_port:
          name: "Reykjavik"
          latitude: 64.1466
          longitude: -21.9426
          timezone: "Atlantic/Reykjavik"

**Port Expansion Benefits:**

- Simplifies configuration by eliminating external port references
- Makes leg definitions self-contained and portable
- Reduces configuration complexity for single-leg cruises
- Preserves all port metadata (coordinates, timezone, etc.)

----

.. _subcommand-validate:

`validate` 
^^^^^^^^^^ 

Performs validation checks on a configuration file, including comparing stated depths against bathymetry data.

.. code-block:: bash

    usage: cruiseplan validate [-h] -c CONFIG_FILE [--check-depths] [--strict] [--warnings-only] [--tolerance TOLERANCE] [...]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** Input YAML configuration file.
   * - ``--check-depths``
     - Compare existing depths with bathymetry data.
   * - ``--strict``
     - Enable strict validation mode (fail on warnings).
   * - ``--warnings-only``
     - Show warnings but do not fail the exit code.
   * - ``--tolerance TOLERANCE``
     - Depth difference tolerance in percent (default: ``10.0``).
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset (default: ``etopo2022``).
   * - ``--output-format {text,json}``
     - Output format for validation results (default: ``text``).
   * - ``-v, --verbose``
     - Enable verbose logging with detailed validation progress.

**Validation Checks:**

The validation process includes:

- **Schema Validation**: YAML structure and required fields
- **Reference Integrity**: Station, leg, and cluster cross-references  
- **Geographic Bounds**: Coordinate validity and reasonable geographic limits
- **Operational Feasibility**: Duration calculations and scheduling logic
- **Bathymetric Accuracy**: Depth consistency with global datasets (when ``--check-depths`` enabled)
- **Scientific Standards**: CF convention compliance for output formats

----

.. _subcommand-map:

`map`
^^^^^

Generate standalone maps (PNG, KML) directly from YAML configuration files, independent of scheduling.  

.. code-block:: bash

    usage: cruiseplan map [-h] -c CONFIG_FILE [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--format {png,kml,all}] [--bathymetry-source {etopo2022,gebco2025}] [--bathymetry-stride BATHYMETRY_STRIDE] [--figsize WIDTH HEIGHT] [--show-plot] [--verbose]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** YAML cruise configuration file.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``current`` directory).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path (overrides auto-generated name).
   * - ``--format {png,kml,all}``
     - Output format to generate (default: ``all``). Can generate PNG maps, KML files, or both.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset (default: ``gebco2025``).
   * - ``--bathymetry-stride BATHYMETRY_STRIDE``
     - Bathymetry downsampling factor (default: ``5``, higher=faster/less detailed).
   * - ``--figsize WIDTH HEIGHT``
     - Figure size in inches (default: ``12 10``).
   * - ``--show-plot``
     - Display plot interactively instead of saving to file.
   * - ``--verbose, -v``
     - Enable verbose logging.

**Description:**

This command generates static PNG maps from cruise configuration files, showing stations, ports, and bathymetric background. Unlike ``schedule --format png``, this command creates maps directly from the YAML configuration without requiring scheduling calculations.

**Key Differences from Schedule PNG Output:**

.. list-table::
   :widths: 40 60

   * - **Feature**
     - **Map Command**
   * - **Data Source**
     - YAML configuration only
   * - **Station Order**
     - Configuration order (not scheduled sequence)
   * - **Cruise Track Lines**
     - Only port-to-station transit lines
   * - **Station Types**
     - Stations (red circles) vs Moorings (gold stars)
   * - **Use Case**
     - Initial planning and configuration review

Compare this to ``cruiseplan schedule --format png``:

.. list-table::
   :widths: 40 60

   * - **Feature**
     - **Schedule PNG**
   * - **Data Source**
     - Generated timeline with scheduling
   * - **Station Order**
     - Scheduled sequence (leg-based)
   * - **Cruise Track Lines**
     - Full cruise track between all operations
   * - **Station Types**
     - All shown as stations (operation type from timeline)
   * - **Use Case**
     - Final schedule visualization and execution planning

**Examples:**

.. code-block:: bash

    # Generate PNG map with default settings
    $ cruiseplan map -c cruise.yaml
    
    # Generate KML file for Google Earth
    $ cruiseplan map -c cruise.yaml --format kml
    
    # Generate both PNG and KML
    $ cruiseplan map -c cruise.yaml --format all
    
    # Custom output directory and figure size
    $ cruiseplan map -c cruise.yaml -o maps/ --figsize 14 10
    
    # High-resolution bathymetry with custom output file
    $ cruiseplan map -c cruise.yaml --bathymetry-source gebco2025 --output-file track_map.png
    
    # Fast preview with coarse bathymetry
    $ cruiseplan map -c cruise.yaml --bathymetry-source etopo2022 --bathymetry-stride 10
    
    # Interactive display instead of file output
    $ cruiseplan map -c cruise.yaml --show-plot

----

.. _subcommand-schedule:

`schedule`
^^^^^^^^^^

Generate the cruise timeline and schedule outputs from a YAML configuration file.

.. code-block:: bash

    usage: cruiseplan schedule [-h] -c CONFIG_FILE [-o OUTPUT_DIR] [--format {html,latex,csv,netcdf,png,all}] [--leg LEG] [--derive-netcdf]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** YAML cruise configuration file.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data``).
   * - ``--format {html,latex,csv,netcdf,png,all}``
     - Output formats to generate (default: ``all``).
   * - ``--leg LEG``
     - Process specific leg only (e.g., ``--leg Northern_Operations``).
   * - ``--derive-netcdf``
     - Generate specialized NetCDF files (_points.nc, _lines.nc, _areas.nc) in addition to master schedule. Only works with NetCDF format.

**Examples:**

.. code-block:: bash

    # Generate all output formats
    cruiseplan schedule -c cruise.yaml -o results/

    # Generate only HTML and CSV
    cruiseplan schedule -c cruise.yaml --format html,csv

    # Generate NetCDF with specialized files
    cruiseplan schedule -c cruise.yaml --format netcdf --derive-netcdf

    # Process specific leg only
    cruiseplan schedule -c cruise.yaml --leg "Northern_Survey" --format all

**NetCDF Output Options:**

.. list-table::
   :widths: 40 60

   * - ``--format netcdf``
     - Generates master schedule file: ``cruise_schedule.nc``
   * - ``--format netcdf --derive-netcdf``
     - Generates specialized files: ``cruise_schedule.nc``, ``cruise_points.nc``, ``cruise_lines.nc``, ``cruise_areas.nc``



