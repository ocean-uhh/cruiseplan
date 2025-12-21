Overview
========

This guide provides step-by-step workflows for planning oceanographic cruises with CruisePlan, from initial setup through schedule generation.

CruisePlan follows a multi-step workflow where each command builds upon the previous step's outputs. The system is designed to separate concerns: data preparation, station planning, configuration details, and scheduling.

**Core Philosophy:**

- **Modular**: Each step has a specific purpose and clear inputs/outputs
- **Flexible**: Multiple workflow paths depending on your data needs
- **Manual Control**: Key decisions require explicit user input
- **Validation**: Built-in checks ensure data quality throughout

Quick Reference
---------------

.. list-table:: Command Flow Summary
   :widths: 15 25 25 25 15
   :header-rows: 1

   * - **Command**
     - **Purpose**
     - **Input**
     - **Output**
     - **File type**
   * - ``bathymetry``
     - Get bathymetry data
     - User choice (ETOPO, GEBCO)
     - NetCDF files in ``data/``
     - `*.nc`
   * - ``pangaea`` (search)
     - Search PANGAEA
     - Search terms + bounds
     - DOI list file
     - Text file
   * - ``pangaea``
     - Process historical station information
     - DOI list file
     - Pickled station database
     - `*.pkl`
   * - ``stations``
     - Interactive planning
     - Optional PANGAEA pickle
     - Stub YAML configuration
     - `*.yaml`
   * - ``enrich``
     - Add metadata
     - Stub YAML
     - Complete YAML with depths
     - `*.yaml`
   * - ``validate``
     - Check configuration
     - YAML file
     - Validation report
     - Text output     
   * - ``map``
     - Visualize cruise plan
     - YAML file
     - Map figure
     - `*.png`, `*.pdf`
   * - ``schedule``
     - Generate outputs
     - Valid YAML
     - Timeline & deliverables
     - Multiple formats

Prerequisites
-------------

Before starting any workflow, ensure you have:

1. **CruisePlan installed** with all dependencies
2. **Internet connection** for downloading bathymetry data
3. **Sufficient disk space**:

   - ETOPO 2022: ~500MB (recommended to start)
   - GEBCO 2025: ~7.5GB (high-resolution option)

  .. _download_bathymetry:

Download bathymetry
...................

.. code-block:: bash

   # Download default bathymetry (ETOPO 2022 - recommended)
   cruiseplan bathymetry
   
   # OR download high-resolution bathymetry (larger download)
   cruiseplan bathymetry --source gebco2025


**What this does:**

- Downloads global bathymetry dataset to ``data/bathymetry/`` (or specified directory, using `-o` flag)
- Enables depth lookups in subsequent steps

**Storage requirements:**

- ETOPO 2022 (~500MB): 1-arc-minute resolution, suitable for most open ocean work
- GEBCO 2025 (~7.5GB): 15-arc-second resolution, better for coastal/slope areas

.. figure:: _static/screenshots/download_bathymetry.png
   :alt: Bathymetry download progress with citation information
   :width: 600px
   :align: center
   
   Bathymetry download process showing progress bars


⚠️ **Important**: Having a valid bathymetry file is an important step for all workflows.  While it is possible to operate without, this is used for determining station depths for CTDs and makes using the station picker much more straightforward.

💡 **Smart Fallback**: Note that ETOPO 2022 is the default if not specified.   If you haven't downloaded ETOPO 2022  but have GEBCO 2025 available, CruisePlan will automatically detect and use the available bathymetry source.  

Workflow Paths
==============

.. tip::
   
  1. **Start simple:** Begin with basic CTD stations before adding complex operations
  2. **Use PANGAEA data:** Historical context improves station placement decisions  
  3. **Validate often:** Run validation after each major edit to catch issues early
  4. **Test scheduling:** Generate test schedules to check feasibility

.. toctree::
   :maxdepth: 1
   :caption: Choose your workflow based on your planning needs

   Path 1: General Usage - Cruise planning from scratch without historical context <workflow/path1.rst>
   Path 2: PANGAEA-Enhanced - Incorporate historical station positions when picking stations <workflow/path2.rst>
   Path 3: Configuration-Only - Iterate on existing YAML configurations <workflow/path3.rst>

Advanced Topics
===============

Multi-Leg Expeditions
---------------------

For complex cruises with multiple operational phases, these can be separated into "legs".  Each leg can have its own station sequence and strategy, and scheduling happens within a discrete leg.  This is also useful when combining main cruise activities with side user activities, to independently estimate timing.  (An alternative, if the stations are interspersed, is to create a schedule with only the main activities and then one with both main and side user activities.) 

.. code-block:: yaml

   legs:
     - name: "Northern_Survey"
       strategy: "sequential"
       stations: ["STN_001", "STN_002", "STN_003"]
       
     - name: "Mooring_Operations"
       strategy: "sequential"  
       stations: ["MOOR_A_RECOVERY", "MOOR_B_DEPLOYMENT"]
       
     - name: "Southern_Transect"
       strategy: "sequential"
       stations: ["STN_004", "STN_005"]

**Leg strategy options:**

- ``sequential``: Visit stations in specified order
- (Future: ``adaptive``, ``opportunistic`` strategies)

----

Bathymetry Source Selection
---------------------------

**When to use GEBCO 2025:**

- Coastal or slope areas (< 1500m depth)
- Small-scale survey areas
- Detailed bathymetric mapping

**When ETOPO 2022 is sufficient:**

- Deep ocean research (> 1500m depth)
- Large-scale surveys
- Storage space is limited
- Standard precision is adequate

.. warning::
   **Interactive Performance Considerations**
   
   Using ``cruiseplan stations`` with GEBCO 2025 and ``--high-resolution`` can significantly impact interactive performance:
   
   * **Slow response times** during station placement
   * **Laggy map interactions** when zooming/panning
   * **High memory usage** (GEBCO 2025 is ~7.5GB)
   
   **Recommended workflow for optimal performance:**
   
   1. **Initial planning**: Use ETOPO 2022 (default) for fast interactive station placement
   2. **Detailed refinement**: Switch to GEBCO 2025 with standard resolution (10x downsampling)  
   3. **Final validation**: Use GEBCO 2025 high-resolution only when necessary for precise depth requirements
   
   This staged approach maintains interactive responsiveness while ensuring access to high-quality bathymetry when needed.

GEBCO is generally considered to be more accurate.

**Switching between sources:**

.. code-block:: bash

   # Re-enrich with different bathymetry
   cruiseplan enrich -c cruise.yaml --add-depths --bathymetry-source gebco2025

----

Duration Calculation Rules
-------------------------

**Automatic calculations:**

.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - **Operation**
     - **Duration Formula**
     - **Typical Range**
   * - CTD Profile
     - Depth-dependent
     - 30-180 minutes
   * - Water Sampling
     - Fixed + depth component
     - 45-90 minutes
   * - Calibration
     - Equipment-dependent
     - 30-60 minutes

**Manual overrides:**

.. code-block:: yaml

   - name: "Deep_CTD"
     operation_type: "CTD"
     action: "profile"
     depth: 4000
     duration: 240  # Override: 4 hours for very deep station

**Mooring operations** (always manual):

.. code-block:: yaml

   - name: "Mooring_Recovery"
     operation_type: "mooring"
     action: "recovery"
     duration: 180  # 3 hours - REQUIRED for moorings

----

Common Configuration Patterns
-----------------------------

**Simple CTD Survey:**

.. code-block:: yaml

   cruise_name: "CTD_Survey_2024"
   
   stations:
     - name: "CTD_01"
       operation_type: "CTD"
       action: "profile"
       latitude: 60.0
       longitude: -30.0
   
   legs:
     - name: "Main_Survey"
       stations: ["CTD_01", "CTD_02", "CTD_03"]

**Mixed Operations:**

.. code-block:: yaml

   stations:
     - name: "Site_A_CTD"
       operation_type: "CTD"
       action: "profile"
       latitude: 60.0
       longitude: -30.0
       
     - name: "Site_A_Mooring"
       operation_type: "mooring"
       action: "deployment"
       latitude: 60.0
       longitude: -30.0
       duration: 240  # 4 hours
       equipment: "Full depth array with ADCP"

**Survey Transects:**

.. code-block:: yaml

   transits:
     - name: "Survey_Line_1"
       operation_type: "underway"
       action: "ADCP"
       vessel_speed: 8.0
       route:
         - latitude: 60.0
           longitude: -30.0
         - latitude: 60.5
           longitude: -29.5

Troubleshooting
===============

Common Issues and Solutions
---------------------------

**Installation and Setup:**

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - **Problem**
     - **Solution**
   * - "Command not found: cruiseplan"
     - Activate conda environment: ``conda activate cruiseplan``
   * - "ModuleNotFoundError"
     - Reinstall: ``pip install -e .`` in project directory
   * - "Permission denied" downloading
     - Check internet connection and disk space

**Bathymetry Issues:**

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - **Problem**
     - **Solution**
   * - "MOCK mode" warnings
     - Run ``cruiseplan bathymetry`` first
   * - "File too small" error
     - Redownload: ``cruiseplan bathymetry --source etopo2022``
   * - Depths seem incorrect
     - Check coordinate format (decimal degrees)

**Station Picker Issues:**

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - **Problem**
     - **Solution**
   * - GUI doesn't open
     - Install matplotlib: ``pip install matplotlib``
   * - Can't save YAML
     - Check output directory permissions
   * - Wrong map region
     - Use ``--lat`` and ``--lon`` flags to set bounds

**Configuration Errors:**

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - **Problem**
     - **Solution**
   * - "Invalid operation_type"
     - Use: CTD, mooring, water_sampling, calibration
   * - "Missing duration" for mooring
     - Add ``duration: 180`` (or appropriate minutes)
   * - "Station not found in leg"
     - Check exact spelling in leg station lists

**Scheduling Issues:**

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - **Problem**
     - **Solution**
   * - "No valid path" error
     - Check all stations have valid coordinates
   * - Unrealistic transit times
     - Verify vessel speed settings
   * - Missing output files
     - Check output directory permissions

Getting Help
------------

**Error message interpretation:**

- Read error messages carefully - they often contain specific solutions
- Check line numbers in YAML files for syntax errors
- Validate YAML syntax with online validators if needed

**Unrecognised arguments:**

- Check ``cruiseplan --help`` and ``cruiseplan <command> --help``

**Example configurations:**

- See ``tests/fixtures/`` directory for working examples
- Use ``cruise_simple.yaml`` as a minimal template
- See ``cruise_mixed_ops.yaml`` for complex operations

**Community support:**

- Report issues on GitHub
- Include error messages and configuration files
- Specify your operating system and Python version



----

**Next Steps:**

- See :doc:`cli_reference` for detailed command options
- Check :doc:`api/modules` for programmatic usage
- Review example configurations in ``tests/fixtures/``