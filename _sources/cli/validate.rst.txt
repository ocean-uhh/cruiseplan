.. _subcommand-validate:

========
validate
========

Performs validation checks on a configuration file, including comparing stated depths against bathymetry data.

Usage
-----

.. code-block:: bash

    usage: cruiseplan validate [-h] -c CONFIG_FILE [--check-depths] [--strict] [--warnings-only] [--tolerance TOLERANCE] [...]

Options
-------

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

Validation Checks
-----------------

The validation process includes:

- **Schema Validation**: YAML structure and required fields
- **Reference Integrity**: Station, leg, and cluster cross-references  
- **Geographic Bounds**: Coordinate validity and reasonable geographic limits
- **Operational Feasibility**: Duration calculations and scheduling logic
- **Bathymetric Accuracy**: Depth consistency with global datasets (when ``--check-depths`` enabled)
- **Scientific Standards**: CF convention compliance for output formats