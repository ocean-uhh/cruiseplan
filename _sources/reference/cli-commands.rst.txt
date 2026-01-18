============
CLI Commands
============

Complete reference for all CruisePlan command-line tools.

Core Commands
=============

cruiseplan bathymetry
---------------------

Download bathymetry data (one-time setup).

.. code-block:: bash

   cruiseplan bathymetry [-h] [--citation] [-o OUTPUT_DIR] [--bathy-source {etopo2022,gebco2025}]

**Options:**

- ``--bathy-source {etopo2022,gebco2025}``: Data source (default: etopo2022)
- ``-o, --output-dir DIR``: Output directory (default: data/bathymetry)  
- ``--citation``: Show data citation information

**Examples:**

.. code-block:: bash

   # Download default ETOPO 2022 data (~500MB)
   cruiseplan bathymetry
   
   # Download high-resolution GEBCO 2025 (~7.5GB)
   cruiseplan bathymetry --bathy-source gebco2025

cruiseplan stations
-------------------

Interactive station placement tool.

.. code-block:: bash

   cruiseplan stations [-h] [-p PANGAEA_FILE] [--lat MIN MAX] [--lon MIN MAX] 
                       [--overwrite] [-o OUTPUT_DIR] [--bathy-source {etopo2022,gebco2025}] 
                       [--bathy-dir BATHY_DIR] [--high-resolution]

**Options:**

- ``--lat MIN MAX``: Latitude bounds for map view (default: 45 70)
- ``--lon MIN MAX``: Longitude bounds for map view (default: -65 -5)
- ``-o, --output-dir DIR``: Output directory (default: data)
- ``-p, --pangaea-file FILE``: PANGAEA historical data file

**Interactive Controls:**

- **p**: Place point stations
- **l**: Draw line transects
- **a**: Define area operations
- **u**: Undo last operation
- **y**: Save to YAML
- **Escape**: Exit without saving

**Examples:**

.. code-block:: bash

   # Basic station placement
   cruiseplan stations --lat 60 65 --lon -30 -20 --output-dir data
   
   # With historical PANGAEA context
   cruiseplan stations -p data/historical_stations.pkl --lat 60 65 --lon -30 -20

cruiseplan process  
------------------

Process and enrich cruise configuration.

.. code-block:: bash

   cruiseplan process [-h] -c CONFIG_FILE [--only-enrich] [--only-validate] 
                      [--only-map] [--no-enrich] [--no-validate] [--no-map] 
                      [--no-depths] [--no-coords] [--no-sections] [--no-ports] 
                      [--no-depth-check] [--tolerance TOLERANCE] [-o OUTPUT_DIR] 
                      [--output OUTPUT] [--format FORMAT] [--bathy-source {etopo2022,gebco2025}] 
                      [--bathy-dir BATHY_DIR] [--bathy-stride BATHY_STRIDE] 
                      [--figsize WIDTH HEIGHT] [--no-port-map] [--verbose] [--quiet]

**Options:**

- ``-c, --config-file FILE``: Input YAML configuration file (required)
- ``-o, --output-dir DIR``: Output directory (default: data)
- ``--output OUTPUT``: Base filename for outputs
- ``--no-enrich``: Skip enrichment step
- ``--no-validate``: Skip validation step
- ``--no-map``: Skip map generation step
- ``--figsize WIDTH HEIGHT``: Figure size for PNG maps in inches (default: 12 8)

**What it does:**

1. Loads YAML configuration
2. Adds bathymetry depths to stations
3. Validates configuration
4. Generates preview map
5. Saves enriched YAML

**Example:**

.. code-block:: bash

   cruiseplan process -c data/stations.yaml
   # Creates: data/{cruise_name}_enriched.yaml + data/{cruise_name}_map.png

cruiseplan schedule
-------------------

Generate cruise timeline and outputs.

.. code-block:: bash

   cruiseplan schedule [-h] -c {cruise_name}_enriched.yaml [--leg LEG] [--derive-netcdf] 
                       [-o OUTPUT_DIR] [--output OUTPUT] [--format {html,latex,csv,netcdf,png,all}] 
                       [--bathy-source {etopo2022,gebco2025}] [--bathy-dir BATHY_DIR] 
                       [--bathy-stride BATHY_STRIDE] [--figsize WIDTH HEIGHT]

**Options:**

- ``-c, --config-file FILE``: YAML cruise configuration file (required)
- ``-o, --output-dir DIR``: Output directory (default: data)
- ``--output OUTPUT``: Base filename for outputs
- ``--format FORMAT``: Output format: html,latex,csv,netcdf,png,all (default: all)
- ``--figsize WIDTH HEIGHT``: Figure size for PNG maps in inches (default: 12 8)

**Examples:**

.. code-block:: bash

   # Generate all output formats
   cruiseplan schedule -c {cruise_name}_enriched.yaml
   
   # Generate specific formats only
   cruiseplan schedule -c {cruise_name}_enriched.yaml --format html

Data Commands
=============

cruiseplan pangaea
------------------

Search and download PANGAEA historical data.

.. code-block:: bash

   cruiseplan pangaea [-h] [--lat MIN MAX] [--lon MIN MAX] [--limit LIMIT] 
                      [-o OUTPUT_DIR] [--output OUTPUT] [--rate-limit RATE_LIMIT] 
                      [--merge-campaigns] [--verbose] query_or_file

**Search Options:**

- ``--lat MIN MAX``: Latitude bounds
- ``--lon MIN MAX``: Longitude bounds  
- ``--limit N``: Maximum results (default: 10)
- ``--output NAME``: Base filename for outputs

**Processing Options:**

- ``--rate-limit RATE``: API requests per second (default: 1.0)
- ``--merge-campaigns``: Combine datasets from same cruise

**Examples:**

.. code-block:: bash

   # Search for CTD data in region
   cruiseplan pangaea "CTD" --lat 60 70 --lon -30 0 --output arctic_ctd
   # Creates: arctic_ctd_dois.txt and arctic_ctd_stations.pkl
   
   # Process existing DOI list
   cruiseplan pangaea my_dois.txt --output processed_data

Individual Processing Commands
==============================

For advanced workflows, you can run processing steps individually:

cruiseplan enrich
-----------------

Add bathymetry depths to stations.

.. code-block:: bash

   cruiseplan enrich [-h] -c CONFIG_FILE [--add-depths] [--add-coords] 
                  [--expand-sections] [-o OUTPUT_DIR] [--output OUTPUT] 
                  [--bathy-source {etopo2022,gebco2025}] [--bathy-dir BATHY_DIR] [--verbose]

cruiseplan validate
-------------------

Validate cruise configuration.

.. code-block:: bash

   cruiseplan validate [-h] -c CONFIG_FILE [--check-depths] [--tolerance TOLERANCE]

cruiseplan map
--------------

Generate cruise map.

.. code-block:: bash

   cruiseplan map [-h] -c CONFIG_FILE [--no-ports] [-o OUTPUT_DIR] [--output OUTPUT] 
               [--format {png,kml,all}] [--bathy-source {etopo2022,gebco2025}] 
               [--bathy-dir BATHY_DIR] [--bathy-stride BATHY_STRIDE] 
               [--figsize WIDTH HEIGHT] [--show-plot] [--verbose]

Global Options
==============

All commands support:

- ``-h, --help``: Show help message
- ``--version``: Show version information

Commands with verbose logging:

- ``cruiseplan process --verbose``: Enable detailed logging
- ``cruiseplan pangaea --verbose``: Enable detailed logging  
- ``cruiseplan enrich --verbose``: Enable detailed logging
- ``cruiseplan map --verbose``: Enable detailed logging

Exit Codes
==========

- **0**: Success
- **1**: Error (configuration, validation, file I/O, network, etc.)

For examples and workflows, see :doc:`../user-guide/workflows`.