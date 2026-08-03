=========
Workflows
=========

CruisePlan supports three different workflows depending on your needs and experience level.

Core Commands
=============

.. list-table:: 
   :header-rows: 1
   :widths: 20 40 40

   * - **Command**
     - **Purpose**
     - **Output**
   * - ``bathymetry``
     - Download depth data (one-time)
     - NetCDF files in ``data/``
   * - ``stations``
     - Interactive station placement
     - ``data/stations.yaml``
   * - ``process``
     - Add depths, validate config
     - ``*_enriched.yaml`` + map
   * - ``schedule``
     - Generate timeline & outputs
     - Multiple formats

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