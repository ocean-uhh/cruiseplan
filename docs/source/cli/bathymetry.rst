.. _subcommand-bathymetry:

==========
bathymetry
==========

Downloads bathymetry datasets for depth calculations and bathymetric analysis.

This command downloads global bathymetry datasets that are used by CruisePlan for:

* Automatic depth enrichment in station definitions
* Depth accuracy validation against real bathymetry
* Bathymetric background layers in map generation

Usage
-----

.. code-block:: bash

   cruiseplan bathymetry [OPTIONS]

The command will download the specified bathymetry dataset to the configured directory.

Options
-------

.. option:: --bathy-source {etopo2022,gebco2025}

   Bathymetry dataset to download (default: ``etopo2022``)
   
   * ``etopo2022``: ETOPO 2022 bathymetry (~500MB, 60s resolution)
   * ``gebco2025``: GEBCO 2025 bathymetry (~7.5GB, 15s resolution)

.. option:: --citation

   Show citation information for the bathymetry source without downloading

.. option:: -o OUTPUT_DIR, --output-dir OUTPUT_DIR

   Output directory for bathymetry files (default: ``data/bathymetry``)

.. option:: --verbose, -v

   Enable verbose logging output

.. option:: --help, -h

   Show help message and exit

Legacy Parameters (Deprecated)
-------------------------------

.. option:: --source

   **[DEPRECATED]** Use ``--bathy-source`` instead

.. option:: --bathymetry-source

   **[DEPRECATED]** Use ``--bathy-source`` instead

Examples
--------

**Basic Usage**

.. code-block:: bash

   # Download default ETOPO 2022 bathymetry
   cruiseplan bathymetry
   
   # Download high-resolution GEBCO 2025 bathymetry 
   cruiseplan bathymetry --bathy-source gebco2025
   
   # Download to custom directory
   cruiseplan bathymetry --output-dir /path/to/bathymetry

**Citation Information**

.. code-block:: bash

   # Show ETOPO 2022 citation without downloading
   cruiseplan bathymetry --bathy-source etopo2022 --citation
   
   # Show GEBCO 2025 citation without downloading
   cruiseplan bathymetry --bathy-source gebco2025 --citation

Dataset Information
-------------------

**ETOPO 2022**

* **Resolution**: 60 arc-second (~1.8 km)
* **Size**: ~500 MB
* **Coverage**: Global
* **Source**: NOAA National Centers for Environmental Information
* **Recommended for**: General cruise planning, initial depth estimates

**GEBCO 2025**

* **Resolution**: 15 arc-second (~450 m)
* **Size**: ~7.5 GB  
* **Coverage**: Global
* **Source**: General Bathymetric Chart of the Oceans
* **Recommended for**: High-precision planning, detailed bathymetric analysis

Output Files
------------

Downloaded bathymetry files are saved in NetCDF format:

* **ETOPO 2022**: ``ETOPO_2022_v1_60s_N90W180_bed.nc``
* **GEBCO 2025**: ``GEBCO_2025_15s.nc``

These files are automatically detected and used by other CruisePlan commands for depth calculations and map generation.

Notes
-----

* **First-time setup**: Run this command before using other CruisePlan features that require bathymetry
* **Network requirements**: Download requires internet connection and may take several minutes for large datasets
* **Storage requirements**: Ensure sufficient disk space, especially for GEBCO 2025 (~7.5 GB)
* **Automatic detection**: Downloaded files are automatically found by other commands when placed in standard locations

See Also
--------

* :doc:`enrich` - Add missing depths using bathymetry data
* :doc:`validate` - Validate depths against bathymetry
* :doc:`map` - Generate maps with bathymetric backgrounds