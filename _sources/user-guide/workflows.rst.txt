=========
Workflows
=========

CruisePlan has 11 subcommands. Most users need only a handful:

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - **Command**
     - **Purpose**
     - **Output**
   * - ``bathymetry``
     - Download depth data (one-time setup)
     - NetCDF files in ``data/bathymetry/``
   * - ``stations``
     - Interactive station placement on a map
     - ``data/stations.yaml``
   * - ``process``
     - Enrich YAML: add depths, validate, generate map
     - ``*_enriched.yaml`` + PNG map
   * - ``schedule``
     - Generate timeline and output files
     - HTML, NetCDF, CSV, LaTeX, KML
   * - ``run``
     - ``process`` + ``schedule`` in one step
     - All of the above
   * - ``map``
     - Generate a map without scheduling
     - PNG map
   * - ``enrich``
     - Add depths and coordinates only
     - ``*_enriched.yaml``
   * - ``validate``
     - Check configuration only
     - Validation report
   * - ``forecast``
     - Generate a real-time workplan from a schedule
     - Waypoints file or LaTeX table
   * - ``list``
     - List operations in a schedule file
     - Terminal output
   * - ``pangaea``
     - Search PANGAEA for historical station data
     - Pickle file + map

.. note::
   ``cruiseplan run`` is the recommended starting point for most workflows —
   it chains ``process`` and ``schedule`` in a single enrichment pass.
   Use ``process`` and ``schedule`` separately only when you need to inspect
   or edit the enriched YAML between steps.

.. note::
   The 11-subcommand structure is under review. A future version may consolidate
   these into fewer commands with options to select specific outputs.

Three Common Workflows
======================

Workflow 1: Basic Planning
---------------------------

**Best for**: Simple cruises, first-time users

.. code-block:: bash

   cruiseplan bathymetry
   cruiseplan stations --lat 50 60 --lon -40 -20
   cruiseplan process data/stations.yaml
   cruiseplan schedule data/{cruise_name}_enriched.yaml

Workflow 2: With Historical Data
--------------------------------

**Best for**: Revisiting survey areas, comparative studies

.. code-block:: bash

   # Search for historical stations
   cruiseplan pangaea "CTD" --lat 50 60 --lon -40 -20 --output historic

   # Plan with historical context
   cruiseplan stations -p data/historic_stations.pkl --lat 50 60 --lon -40 -20
   cruiseplan process data/historic_stations.yaml
   cruiseplan schedule data/{cruise_name}_enriched.yaml

Workflow 3: Manual Control
--------------------------

**Best for**: Complex cruises, custom requirements

.. code-block:: bash

   cruiseplan stations --lat 50 60 --lon -40 -20

   # Edit YAML manually to add custom operations, timing, etc.
   # nano data/{cruise_name}_stations.yaml

   cruiseplan enrich data/{cruise_name}_stations.yaml      # Add depths
   cruiseplan validate data/{cruise_name}_enriched.yaml    # Check config
   cruiseplan map data/{cruise_name}_enriched.yaml         # Preview map
   cruiseplan schedule data/{cruise_name}_enriched.yaml    # Generate outputs

Interactive Station Picker
===========================

When you run ``cruiseplan stations``, an interactive map opens:

- **p**: Place point stations (CTD, moorings)
- **l**: Draw line transects 
- **a**: Define area surveys
- **u**: Undo last action
- **y**: Save and exit
- **Escape**: Exit without saving

Tips
====

1. **Start small**: Begin with a few stations to test the workflow
2. **Check outputs**: Always review the generated map before final scheduling
3. **Iterative**: You can re-run ``process`` and ``schedule`` as needed
4. **Backup**: Save your YAML files - they contain all your planning work

For detailed command options, see :doc:`../reference/cli-commands`.