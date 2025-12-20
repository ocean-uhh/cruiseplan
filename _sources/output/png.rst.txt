.. _output-png:

==========
PNG Output
==========

PNG format provides static map visualizations for cruise planning, documentation, and presentation. CruisePlan generates PNG maps in two ways, depending on whether you just want operational locations (``cruiseplan map``) or also scheduling/transit information (``cruiseplan schedule``) to be plotted.

Purpose and Use Cases
======================

**Primary Uses**:
  - Proposal and funding application documentation
  - Cruise plan visualization and review
  - Scientific presentation and publication figures
  - Field operation reference maps

Command Comparison: Schedule vs Map
===================================

CruisePlan generates PNG maps through two commands with distinct characteristics:

.. figure:: ../_static/screenshots/png_output_comparison.png
   :alt: Comparison of PNG outputs from map command vs schedule command
   :width: 100%
   
   **PNG Output Comparison**: Left shows ``cruiseplan map`` output (configuration-based), right shows ``cruiseplan schedule`` output (timeline-based). Note the key difference: schedule output includes departure/arrival ports and lines to show transits, while map output focuses purely on station configuration.

.. list-table:: PNG Output Comparison
   :widths: 30 35 35
   :header-rows: 1

   * - **Feature**
     - **Schedule PNG** (``cruiseplan schedule``)
     - **Map PNG** (``cruiseplan map``)
   * - **Data Source**
     - Generated timeline with scheduling
     - YAML configuration only
   * - **Port Visualization**
     - ✅ Shows departure and arrival ports
     - ❌ Ports not displayed
   * - **Station Order**
     - Scheduled sequence (leg-based execution order)
     - Configuration order (definition sequence)
   * - **Cruise Track Lines**
     - Complete executed route between all operations
     - Basic station connections only
   * - **Station Visualization**
     - Uniform markers (operation type from timeline)
     - Differentiated markers (stations vs moorings)
   * - **Use Case**
     - Schedule and execution planning
     - Proposals (port independent) and overview
   * - **Prerequisites**
     - Requires successful validation and scheduling
     - Works directly with YAML configuration
   * - **Performance**
     - Slower (includes scheduling calculations)
     - Faster (direct from configuration)

----

Schedule PNG Output (Timeline-Based)
-----------------------------------

Generated via: ``cruiseplan schedule -c cruise.yaml --format png``

**Characteristics**:

  - Shows operations in scheduled execution order
  - Includes complete cruise track with all transits
  - Requires prior validation and scheduling success

**Example Command Usage**:

.. code-block:: bash

   # Basic schedule PNG generation
   cruiseplan schedule -c cruise.yaml --format png
   
   # High-resolution output with custom bathymetry
   cruiseplan schedule -c cruise.yaml --format png --bathymetry-source gebco2025
   
   # Combined outputs for complete documentation
   cruiseplan schedule -c cruise.yaml --format png,html,latex

**Output File**: ``{cruise_name}_schedule.png``

.. figure:: ../_static/screenshots/schedule_png_detailed.png
   :alt: Map generated from cruiseplan schedule for tc1_mooring.yaml
   :width: 100%
   
   Shows a cruise track with a single operation (mooring) and two ports.

----

Map PNG Output (Configuration-Based)
-----------------------------------

Generated via: ``cruiseplan map -c cruise.yaml --format png``

**Characteristics**:

  - Shows stations in YAML configuration order
  - Displays differentiated station types (stations vs moorings)
  - Works with any valid YAML configuration

**Example Command Usage**:

.. code-block:: bash

   # Basic configuration map
   cruiseplan map -c cruise.yaml --format png
   
   # Custom figure size and bathymetry
   cruiseplan map -c cruise.yaml --figsize 14 10 --bathymetry-source etopo2022
   
   # Specific output file and directory
   cruiseplan map -c cruise.yaml -o maps/ --output-file planning_map.png
   
   # Interactive preview before saving
   cruiseplan map -c cruise.yaml --show-plot

**Output File**: ``{cruise_name}_map.png``


.. figure:: ../_static/screenshots/map_png_detailed.png
   :alt: Map generated from cruiseplan map for tc5_sections.yaml
   :width: 70%
   
   Shows the station naming for a section which has been expanded by ``cruiseplan enrich``.

----

Integration and workflows
=================================

Visualisation and Customization
-------------------------------

Both PNG outputs include bathymetric background visualization.  For ``cruiseplan map``, the bathymetry source can be selected, while for ``cruiseplan schedule``, GEBCO 2025 is always used.

**Bathymetry Sources**:
  - **GEBCO 2025**: High-resolution global bathymetry (default)
  - **ETOPO 2022**: Lower-resolution for faster generation

**Contour Styling**:
  - Depth contours at standard oceanographic intervals
  - Color-coded depth ranges from land (yellow) and water (blues) ranging from shallow (light) to deep (dark)

**Configuration Options** for ``cruiseplan map`` only:

.. code-block:: bash

   # High-detail bathymetry (slower generation)
   --bathymetry-source gebco2025 --bathymetry-stride 1
   
   # Fast bathymetry for quick previews
   --bathymetry-source etopo2022 --bathymetry-stride 10

Default Operation Markers
-----------------------------

**Station Markers** (Red Circles):
  - Labels with station names

**Mooring Markers** (Gold Stars):
  - Distinctive star shape for easy identification

**Line Operations** (orange lines):
  - Represent underway operations (e.g., ADCP surveys)

**Area Operations** (when present):
  - Polygon outlines with semi-transparent fill
  - Center point routing anchors

These are not user-configurable unless you clone the repository and edit ``cruiseplan/utils/plot_config.py``. See the file on GitHub: `cruiseplan/utils/plot_config.py on GitHub <https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/utils/plot_config.py>`_.

Figure Customization
--------------------

**Figure Size Options** for ``cruiseplan map`` only:

.. code-block:: bash

   # Standard size (default)
   --figsize 12 10

Note that making the figure size smaller will increase the relative size of the fonts, so if you want fonts to be more legible, make the figure size smaller.

**Output Quality**:
  - 300 DPI resolution for publication quality (not configurable)
  - PNG for lossless compression and clarity



Workflow Integration
--------------------

**Initial Planning Phase** (use ``cruiseplan map``):
  1. Create initial YAML configuration
  2. Generate configuration-based PNG for review
  3. Iteratively refine station positions and operations
  4. Share planning maps with collaborators

**Final Planning Phase** or for cruise reports (use ``cruiseplan schedule``):
  1. Validate and enrich configuration
  2. Generate timeline-based PNG
  3. Review execution order and timing
  4. Generate final documentation set



File-Naming Conventions
------------------------

**Schedule PNG Files**:
  - Format: ``{cruise_name}_schedule_map.png`` 
  - Example: ``Arctic_Survey_2024_schedule_map.png``

**Map PNG Files**:
  - Format: ``{cruise_name}_map.png`` (or custom via ``--output-file``)
  - Example: ``Arctic_Survey_2024_map.png``


**Command Examples for Organization**:

.. code-block:: bash

   # Planning phase outputs
   cruiseplan map -c cruise.yaml -o planning/ --output-file initial_config.png
   
   # Final schedule outputs
   cruiseplan schedule -c cruise.yaml -o schedules/ --format all
   


Visual Quality Checks
====================== 

**Review Checklist**:
  - All stations visible and labeled
  - Bathymetric context appropriate for operation depths
  - Track lines connect logically between operations
  - Proper scaling and geographic projection


**Common Issues and Solutions**:

.. list-table:: Figure Issues
   :widths: 30 70
   :header-rows: 1

   * - **Issue**
     - **Solution**
   * - Overlapping station labels
     - Use custom figure size: ``--figsize 16 10``
   * - Unclear bathymetry
     - Reduce stride: ``--bathymetry-stride 3``
   * - Slow generation
     - Use ETOPO: ``--bathymetry-source etopo2022`` (cruiseplan map only)
   * - Missing geographic context
     - Check coordinate validity and map projection


PNG output provides  visualization capabilities for cruise planning, helping you to review the initial configuration and the routing.  If you use and update the yaml during a cruise, then the final yaml can be used to generate the actual cruise track with the schedule command---useful for cruise reports.