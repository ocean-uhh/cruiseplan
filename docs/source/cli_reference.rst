CLI Command Reference
=====================

This document provides a comprehensive reference for the `cruiseplan` command-line interface, detailing available subcommands and their required and optional arguments.

General Usage
-------------

The `cruiseplan` CLI uses a "git-style" subcommand architecture.

.. code-block:: bash

    usage: cruiseplan [-h] [--version] {bathymetry,pangaea,stations,process,enrich,validate,map,schedule} ...

**Options:**

.. list-table::
   :widths: 30 70

   * - ``-h, --help``
     - Show the program's main help message and exit.
   * - ``--version``
     - Show the program's version number and exit.

**Workflow**

The general workflow follows these steps in order:

1. **Data preparation:** :doc:`cli/bathymetry` - Download bathymetry 
2. **Historical integration:** :doc:`cli/pangaea` - Search PANGAEA datasets by query & find stations
3. **Cruise configuration:** :doc:`cli/stations` - Interactive station planning interface
4. **Configuration processing:** :doc:`cli/process` - Unified enrichment, validation & map generation **OR** individual steps:

   * :doc:`cli/enrich` - Add depths, coordinates, and expand sections
   * :doc:`cli/validate` - Validate configuration files  
   * :doc:`cli/map` - Generate standalone PNG cruise maps

5. **Schedule generation:** :doc:`cli/schedule` - Generate cruise timeline and outputs
**Examples:**

The command-line interface provides subcommands for different aspects of cruise planning.

**Streamlined Processing (Recommended):**

.. code-block:: bash

    # Phase 1: Data preparation  
    $ cruiseplan bathymetry --bathy-source gebco2025
    $ cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -40 --limit 20 --output cruise1

    # Phase 2: Cruise configuration & processing
    $ cruiseplan stations --lat 50 65 --lon -60 -30 --output cruise1
    $ cruiseplan process -c data/cruise1.yaml --output expedition_2024

    # Phase 3: Schedule generation
    $ cruiseplan schedule -c data/expedition_2024_enriched.yaml --output expedition_schedule --output-dir results/

**Individual Step Processing (Advanced):**

The different steps of modifying the cruise configuration can also be accessed separately using ``cruiseplan enrich``, ``cruiseplan validate``, and ``cruiseplan map``. Of these, only ``cruiseplan enrich`` modifies the configuration file; the others generate reports and figures.

.. code-block:: bash

    # Phase 1: Data preparation
    $ cruiseplan bathymetry --bathy-source gebco2025
    $ cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -40 --limit 20 --output cruise1

    # Phase 2: Step-by-step cruise configuration
    $ cruiseplan stations --lat 50 65 --lon -60 -30 --output cruise1
    $ cruiseplan enrich -c data/cruise1.yaml --output expedition_2024
    $ cruiseplan validate -c data/expedition_2024_enriched.yaml --check-depths
    $ cruiseplan map -c data/expedition_2024_enriched.yaml --output expedition_map --figsize 14 10

    # Phase 3: Schedule generation
    $ cruiseplan schedule -c data/expedition_2024_enriched.yaml --output expedition_schedule --output-dir results/

.. figure:: _static/screenshots/cli_help_overview.png
   :alt: CruisePlan CLI help overview showing all available commands
   :width: 700px
   :align: center
   
   Complete overview of CruisePlan CLI commands and their purposes

----

Subcommands
-----------

.. note:: For detailed help on any subcommand, use: ``cruiseplan <command> --help``

.. toctree::
   :maxdepth: 1
   :caption: Current CLI Subcommands

   cli/bathymetry
   cli/pangaea
   cli/stations
   cli/process
   cli/schedule

.. toctree::
   :maxdepth: 1
   :caption: Individual process Subcommands
   
   cli/enrich
   cli/validate
   cli/map
