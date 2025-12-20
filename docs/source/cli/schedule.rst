.. _subcommand-schedule:

========
schedule
========

Generate the cruise timeline and schedule outputs from a YAML configuration file.

Usage
-----

.. code-block:: bash

    usage: cruiseplan schedule [-h] -c CONFIG_FILE [-o OUTPUT_DIR] [--format {html,latex,csv,netcdf,png,all}] [--leg LEG] [--derive-netcdf]

Options
-------

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

Examples
--------

.. code-block:: bash

    # Generate all output formats
    cruiseplan schedule -c cruise.yaml -o results/

    # Generate only HTML and CSV
    cruiseplan schedule -c cruise.yaml --format html,csv

    # Generate NetCDF with specialized files
    cruiseplan schedule -c cruise.yaml --format netcdf --derive-netcdf

    # Process specific leg only
    cruiseplan schedule -c cruise.yaml --leg "Northern_Survey" --format all

NetCDF Output Options
---------------------

.. list-table::
   :widths: 40 60

   * - ``--format netcdf``
     - Generates master schedule file: ``cruise_schedule.nc``
   * - ``--format netcdf --derive-netcdf``
     - Generates specialized files: ``cruise_schedule.nc``, ``cruise_points.nc``, ``cruise_lines.nc``, ``cruise_areas.nc``