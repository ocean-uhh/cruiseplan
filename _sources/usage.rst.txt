Usage Guide
===========

This guide provides a quick overview of how to use CruisePlan for oceanographic cruise planning.

Quick Start
-----------

After installation, you can use CruisePlan via the command line:

.. code-block:: bash

   # Get help / list available commands
   cruiseplan --help

Basic Workflow
--------------

CruisePlan follows a systematic workflow for cruise planning:

1. **Download bathymetry data** → 2. **Plan stations interactively** → 3. **Configure operations** → 4. **Enrich with metadata** → 5. **Validate configuration** → 6. **Generate schedule & outputs**

For detailed step-by-step instructions, see the :doc:`user_workflows` guide, which provides comprehensive workflows for different planning scenarios.

**Quick Start:**

.. code-block:: bash

   # 1. Download bathymetry data
   cruiseplan download
   
   # 2. Interactive station planning
   cruiseplan stations --output-file my_cruise.yaml
   
   # 3. Edit YAML to add operation types (CTD, mooring, etc.)
   # 4. Add depths and coordinates
   cruiseplan enrich -c my_cruise.yaml --add-depths --add-coords
   
   # 5. Validate configuration
   cruiseplan validate -c my_cruise.yaml
   
   # 6. Generate outputs
   cruiseplan schedule -c my_cruise.yaml

Configuration Files
-------------------

CruisePlan uses YAML configuration files to define cruise parameters. A basic configuration includes:

- Cruise metadata (name, dates, ports)
- Station definitions with coordinates and operations
- Leg definitions grouping stations
- Vessel parameters and operational constraints

See the API documentation for detailed configuration options, or look in the `tests/fixtures` directory for example YAML files.

Interactive Tools
-----------------

CruisePlan provides interactive tools for:

- **Station picking**: Click on maps to place oceanographic stations
- **Campaign selection**: Browse and select from PANGAEA datasets

Command Line Interface
----------------------

The CLI provides access to all major functionality:

.. code-block:: bash

   # Validate a cruise configuration
   cruiseplan validate -c config.yaml

   # Generate a cruise schedule
   cruiseplan schedule -c config.yaml

   # Export to different formats
   cruiseplan schedule -c config.yaml --format netcdf
   cruiseplan schedule -c config.yaml --format latex

Output Formats
--------------

CruisePlan generates professional outputs including:

- **NetCDF files**: (mostly) CF-compliant scientific data files
- **LaTeX tables**: For DFG-style cruise applications 
- **HTML summary**: An html summary of the planned working areas and stations
- **KML files**: Google Earth compatible exports with stations, transects, and areas
- **CSV data**: Tabular data exports

For detailed information about each output format, see the respective module documentation.