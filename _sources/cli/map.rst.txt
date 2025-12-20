.. _subcommand-map:

===
map
===

Generate standalone maps (PNG, KML) directly from YAML configuration files, independent of scheduling.

Usage
-----

.. code-block:: bash

    usage: cruiseplan map [-h] -c CONFIG_FILE [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--format {png,kml,all}] [--bathymetry-source {etopo2022,gebco2025}] [--bathymetry-stride BATHYMETRY_STRIDE] [--figsize WIDTH HEIGHT] [--show-plot] [--verbose]

Options
-------

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

Description
-----------

This command generates static PNG maps from cruise configuration files, showing stations, ports, and bathymetric background. Unlike ``schedule --format png``, this command creates maps directly from the YAML configuration without requiring scheduling calculations.

Key Differences from Schedule PNG Output
-----------------------------------------

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

Examples
--------

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