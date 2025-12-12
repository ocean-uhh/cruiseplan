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

1. **Download bathymetry**: Use `cruiseplan download` to download ETOPO bathymetry 
2. **Load PANGAEA past cruises (Optional)**: Use `cruiseplan pangaea` to browse and select from PANGAEA datasets.
3. **Pick stations, transects and areas**: Use the interactive station picker, `cruiseplan stations` to choose waypoints and working areas.  This generates a cruiseplan configuration file (YAML).
4. **Enrich YAML**: The station picker only choses locations.  But the scheduler needs to know how deep they are (for CTDs).  Use `cruiseplan enrich` to add depth and other metadata to the YAML config.
5. **Validate configuration**: Use `cruiseplan validate` to check the configuration file for errors.
6. **Generate schedule**: Use `cruiseplan schedule` to create a detailed cruise schedule and generate outputs.

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