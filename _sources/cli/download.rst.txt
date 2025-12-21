.. _subcommand-download:

========
download
========

.. warning::
   **DEPRECATED**: This command is deprecated and will be removed in v0.3.0. 
   Please use :doc:`bathymetry` instead.

Download and manage external data assets required by CruisePlan, such as bathymetry grids and other geospatial datasets.

Usage
-----

.. code-block:: bash

    usage: cruiseplan download [-h] [--bathymetry-source {etopo2022,gebco2025}] 
                               [--citation] [-o OUTPUT_DIR]

Options
-------

.. list-table::
   :widths: 30 70

   * - ``-h, --help``
     - Show this help message and exit.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset to download (default: ``etopo2022``).
   * - ``--citation``
     - Show citation information for the bathymetry source without downloading.
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory for bathymetry files (default: ``data/bathymetry``).

Description
-----------

This command downloads bathymetry datasets required for depth calculations and bathymetric visualization in cruise planning. Two datasets are available:

- **ETOPO 2022**: Global bathymetry at 60-second resolution (~500MB) - suitable for most applications
- **GEBCO 2025**: High-resolution global bathymetry at 15-second resolution (~7.5GB) - provides enhanced detail for detailed planning

The datasets are cached locally in the ``data/bathymetry/`` directory.

Available Sources
-----------------

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

Examples
--------

.. code-block:: bash

    # Download default ETOPO 2022 bathymetry
    $ cruiseplan download
    
    # Download ETOPO 2022 explicitly
    $ cruiseplan download --bathymetry-source etopo2022
    
    # Download high-resolution GEBCO 2025 bathymetry
    $ cruiseplan download --bathymetry-source gebco2025

.. figure:: ../_static/screenshots/download_bathymetry.png
   :alt: Bathymetry download progress with citation information
   :width: 600px
   :align: center
   
   Bathymetry download process showing progress bars
   
The download command shows progress information and provides proper citation details for the bathymetry datasets.