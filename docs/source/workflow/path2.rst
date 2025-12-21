.. _user_workflow_path_2:

Path 2: PANGAEA-Enhanced Workflow
==================================

**Best for:** Research cruises that benefit from historical data context, repeat surveys, comparative studies

**Time required:** 1-2 hours (including PANGAEA data collection)

This workflow incorporates historical oceanographic station data from the PANGAEA database to inform your station planning.

----

Step 1: Download Bathymetry Data
---------------------------------

**Purpose:** Provides depth information for station planning and automatic depth enrichment.

Essential first step:  :ref:`download_bathymetry`.  You've succeeeded when you have the file ``data/bathymetry/ETOPO_2022_v1_60s_N90W180_bed.nc`` available.  When in doubt, start with the ETOPO (default) only. 

.. figure:: ../_static/screenshots/data_directory_structure.png
   :alt: Bathymetry data directory structure showing downloaded files
   :width: 600px
   :align: center
   
   Directory structure (Mac OS Finder) showing bathymetry files in ``data/bathymetry/``

.. note::
  See :ref:`Download subcommand CLI reference <subcommand-download>` in :doc:`../cli/download` for full options and examples.

----

Step 2: Collect PANGAEA Dataset Information
--------------------------------------------

**Purpose:** Identify relevant historical cruises and datasets for your region.

**Option A: Automated Search (Recommended):**

Use the ``pandoi`` command to query the PANGAEA database:

.. code-block:: bash

   # Basic search by instrument/parameter (saves to data/ directory by default)
   cruiseplan pangaea "CTD" --lat 50 70 --lon -60 -20
   
   # Geographic search with lat/lon bounds and higher limit
   cruiseplan pangaea "CTD" --lat 50 70 --lon -60 -20 --limit 25
   
   # Combined search terms with custom output name
   cruiseplan pangaea "CTD temperature North Atlantic" --lat 50 70 --lon -60 -20 --limit 50 --output north_atlantic_ctd

**Search Examples by Use Case:**

.. list-table::
   :widths: 30 70
   :header-rows: 1
   
   * - **Research Focus**
     - **Search Command**
   * - Arctic physical oceanography
     - ``cruiseplan pangaea "CTD Arctic Ocean" --lat 70 90 --lon -180 180 --limit 30``
   * - North Atlantic deep water
     - ``cruiseplan pangaea "CTD deep water" --lat 50 70 --lon -50 -10 --limit 40``
   * - Specific expedition data
     - ``cruiseplan pangaea "Polarstern PS122" --lat 70 90 --lon -180 180 --limit 20``

**Geographic Bounds Format:**

Use ``--lat MIN MAX`` and ``--lon MIN MAX`` to specify search regions:

- West longitudes are negative (e.g., -50°W = -50)
- East longitudes are positive (e.g., 20°E = 20)
- South latitudes are negative (e.g., -30°S = -30)
- North latitudes are positive (e.g., 60°N = 60)

**Common Regional Bounds:**

.. code-block:: bash

   # North Atlantic subpolar gyre
   --lat 50 70 --lon -60 -10
   
   # Nordic Seas  
   --lat 60 80 --lon -10 20
   
   # Arctic Ocean
   --lat 70 90 --lon -180 180

.. note::
  See :ref:`Pandoi subcommand CLI reference <subcommand-pandoi>` in :doc:`../cli/pandoi` for full options and examples.


**Option B: Manual Collection (Alternative):**

1. **Visit PANGAEA database:** https://www.pangaea.de
2. **Search by criteria:**

   - Geographic region (lat/lon bounding box)
   - Parameter keywords (e.g., "CTD", "temperature", "salinity")
   - Date ranges
   - Research projects

3. **Collect DOI identifiers** from relevant datasets
4. **Create a DOI list file:**

.. code-block:: text

   # Example: north_atlantic_dois.txt
   10.1594/PANGAEA.12345
   10.1594/PANGAEA.67890
   10.1594/PANGAEA.11111
   10.1594/PANGAEA.22222

**Tips for PANGAEA searching:**

- Use narrow geographic bounds initially
- Focus on similar research objectives (physical oceanography vs biogeochemistry)

----

Step 3: Process PANGAEA Data
----------------------------

**Purpose:** Convert PANGAEA datasets into a searchable station database.

.. code-block:: bash

   # Using file from automated search
   cruiseplan pangaea north_atlantic_ctd_dois.txt -o pangaea_data/
   
   # Or using manually created DOI list
   cruiseplan pangaea north_atlantic_dois.txt -o pangaea_data/

**Options:**

- ``-o OUTPUT_DIR``: Directory for output files (default: ``data/``)
- ``--rate-limit 0.5``: Slower API requests for large datasets
- ``--merge-campaigns``: Combine stations from cruises with same name
- ``--output-file specific_name.pickle``: Custom output filename

**What this does:**

- Downloads metadata for each DOI
- Extracts station coordinates and event information
- Groups stations by campaign/cruise
- Creates a pickled database file: ``campaigns.pickle``

**Output files:**

- ``campaigns.pickle``: Station database for interactive picker

⚠️ **Note**: This process can be slow for large DOI lists due to API rate limiting. Consider running overnight for extensive datasets.

.. note::
  See :ref:`Pangaea subcommand CLI reference <subcommand-pangaea>` in :doc:`../cli/pangaea` for full options and examples.

----

Step 4: Interactive Station Planning with PANGAEA Context
---------------------------------------------------------

**Purpose:** Plan new stations while viewing historical data locations.

.. code-block:: bash

   cruiseplan stations -p pangaea_data/campaigns.pickle --lat 55 70 --lon -60 -20 -o output_dir/
   
**Enhanced interface features:**

- Historical stations displayed as background points
- Campaign information available on hover/click
- Filter historical data by cruise or time period
- Context for avoiding over-sampled areas or finding gaps


.. figure:: ../_static/screenshots/station_picker_pangaea.png
   :alt: Station picker interface with PANGAEA historical data overlay
   :width: 600px
   :align: center
   
   Station picker interface showing PANGAEA historical data overlay (left panel + markers)


**Same interactive controls as Path 1:**

Four modes of inputs:

- ``p`` or ``w``: Place point stations (CTD stations, moorings)
- ``l`` or ``s``: Draw line transects (underway surveys)
- ``a``: Define area operations (box surveys)
- ``n``: Navigation mode (pan/zoom)

Additional commands can be used anytime:

- ``u``: Undo last operation
- ``r``: Remove operation (click to select)
- ``y``: Save to YAML file
- ``Escape``: Exit without saving

**Benefits:** Including PANGAEA historical stations allows you to revisit identical locations, if desired, rather than selecting new positions blindly.

----


Step 5-7: Complete Configuration and Scheduling
-----------------------------------------------

*Same as Path 1, Steps 3-6*

1. :ref:`Manual editing <manual_editing_configuration>` to add operation types and cruise metadata
2. :ref:`Enrichment <enrich_configuration>` to add depths and coordinates
3. :ref:`Validation <subcommand-validate>` to check for errors
4. :ref:`Schedule generation <generate_schedule_outputs>` to create outputs

The PANGAEA-enhanced workflow follows the same final steps but benefits from the historical context during station selection.
