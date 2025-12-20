.. _subcommand-enrich:

======
enrich
======

Adds missing or computed data (like depth or formatted coordinates) to a configuration file. Can also expand CTD sections into individual station definitions.

Usage
-----

.. code-block:: bash

    usage: cruiseplan enrich [-h] -c CONFIG_FILE [--add-depths] [--add-coords] [--expand-sections] [--expand-ports] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [...]

Options
-------

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

CTD Section Expansion
---------------------

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

Key Features
------------

- Uses great circle interpolation for accurate positioning along curved Earth surface
- Automatically generates unique station names with sequential numbering
- Preserves original transit metadata (max_depth becomes station depth)
- Handles name collisions by appending incremental suffixes
- Updates leg definitions to reference the newly created stations
- **Automatic Anchor Resolution**: Updates ``first_waypoint`` and ``last_waypoint`` fields in legs to reference the first and last generated stations from the expanded section

Leg-Level Anchor Field Updates
-------------------------------

When ``--expand-sections`` processes a CTD section transit, it automatically updates any leg definitions that reference the transit name:

- ``first_waypoint``: Updated to reference the first generated station (e.g., "OVIDE_Section" → "OVIDE_Section_001")  
- ``last_waypoint``: Updated to reference the last generated station (e.g., "OVIDE_Section" → "OVIDE_Section_040")
- ``activities``: Expanded to include all generated stations in sequential order

This ensures that leg routing and scheduling work correctly with the newly created individual station definitions, maintaining the original intent while providing the detailed station-by-station planning required for cruise execution.

Port Expansion
--------------

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

Port Expansion Benefits
-----------------------

- Simplifies configuration by eliminating external port references
- Makes leg definitions self-contained and portable
- Reduces configuration complexity for single-leg cruises
- Preserves all port metadata (coordinates, timezone, etc.)