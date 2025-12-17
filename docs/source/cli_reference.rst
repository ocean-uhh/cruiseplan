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

**Examples:**

.. code-block:: bash

    $ cruiseplan schedule -c cruise.yaml -o results/
    $ cruiseplan stations --lat 50 65 --lon -60 -30
    $ cruiseplan enrich -c cruise.yaml --add-depths --add-coords
    $ cruiseplan validate -c cruise.yaml --check-depths
    $ cruiseplan pandoi "CTD" --lat 50 60 --lon -50 -40 --limit 20
    $ cruiseplan map -c cruise.yaml --figsize 14 10
    $ cruiseplan pangaea doi_list.txt -o pangaea_data/

---

Subcommands
-----------

.. note:: For detailed help on any subcommand, use: ``cruiseplan <command> --help``

download
^^^^^^^^

Download and manage external data assets required by CruisePlan, such as bathymetry grids and other geospatial datasets.

.. code-block:: bash

    usage: cruiseplan download [-h] [--bathymetry-source {etopo2022,gebco2025}]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-h, --help``
     - Show this help message and exit.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset to download (default: ``etopo2022``).

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


schedule
^^^^^^^^

Generate the cruise timeline and schedule outputs from a YAML configuration file.

.. code-block:: bash

    usage: cruiseplan schedule [-h] -c CONFIG_FILE [-o OUTPUT_DIR] [--format {html,latex,csv,kml,netcdf,png,all}] [--leg LEG]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** YAML cruise configuration file.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``current`` directory).
   * - ``--format {html,latex,csv,kml,netcdf,png,all}``
     - Output formats to generate (default: ``all``). PNG format generates timeline-based maps showing scheduled sequence.
   * - ``--leg LEG``
     - Process specific leg only (e.g., ``--leg Northern_Operations``).

stations
^^^^^^^^

Launch the interactive graphical interface for planning stations and transects with optional PANGAEA data background.

.. code-block:: bash

    usage: cruiseplan stations [-h] [-p PANGAEA_FILE] [--lat MIN MAX] [--lon MIN MAX] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--bathymetry-source {etopo2022,gebco2025}] [--high-resolution]

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
     - Output directory for the generated station YAML (default: ``current``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path for the generated YAML.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset to use for depth lookups (default: ``etopo2022``).
   * - ``--high-resolution``
     - Use full resolution bathymetry in the interactive interface (slower but more detailed).

enrich
^^^^^^

Adds missing or computed data (like depth or formatted coordinates) to a configuration file. Can also expand CTD sections into individual station definitions.

.. code-block:: bash

    usage: cruiseplan enrich [-h] -c CONFIG_FILE [--add-depths] [--add-coords] [--expand-sections] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [...]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** Input YAML configuration file.
   * - ``--add-depths``
     - Add missing ``depth`` values to stations using bathymetry data.
   * - ``--add-coords``
     - Add formatted coordinate fields (currently DMM; DMS not yet implemented).
   * - ``--expand-sections``
     - Expand CTD sections defined in ``transits`` into individual station definitions with spherical interpolation.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset (default: ``etopo2022``).
   * - ``--coord-format {dmm,dms}``
     - Format for adding coordinates.

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

validate
^^^^^^^^

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

pandoi
^^^^^^

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
    $ cruiseplan pangaea arctic_ctd_dois.txt --output-dir data/
    
    # Step 3: Use in station planning
    $ cruiseplan stations --pangaea-file data/pangaea_campaigns.pkl

map
^^^

Generate standalone PNG cruise track maps directly from YAML configuration files, independent of scheduling.

.. code-block:: bash

    usage: cruiseplan map [-h] -c CONFIG_FILE [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--bathymetry-source {etopo2022,gebco2025}] [--bathymetry-stride BATHYMETRY_STRIDE] [--figsize WIDTH HEIGHT] [--show-plot] [--verbose]

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-c CONFIG_FILE, --config-file CONFIG_FILE``
     - **Required.** YAML cruise configuration file.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``current`` directory).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path (overrides auto-generated name).
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

    # Generate map with default settings
    $ cruiseplan map -c cruise.yaml
    
    # Custom output directory and figure size
    $ cruiseplan map -c cruise.yaml -o maps/ --figsize 14 10
    
    # High-resolution bathymetry with custom output file
    $ cruiseplan map -c cruise.yaml --bathymetry-source gebco2025 --output-file track_map.png
    
    # Fast preview with coarse bathymetry
    $ cruiseplan map -c cruise.yaml --bathymetry-source etopo2022 --bathymetry-stride 10
    
    # Interactive display instead of file output
    $ cruiseplan map -c cruise.yaml --show-plot

pangaea
^^^^^^^

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
   - ``--output-file OUTPUT_FILE``
     - Specific output file path for the pickled dataset.