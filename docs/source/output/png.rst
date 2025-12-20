.. _output-png:

==========
PNG Output
==========

PNG format provides static map visualizations for cruise planning, documentation, and presentation. CruisePlan generates PNG maps through two distinct commands with different purposes and data sources.

Purpose and Use Cases
======================

**Primary Uses**:
  - Proposal and funding application documentation
  - Cruise plan visualization and review
  - Scientific presentation and publication figures
  - Field operation reference maps

**Target Audiences**:
  - Principal investigators preparing proposals
  - Ship operations staff and navigators
  - Scientific collaborators and reviewers
  - Funding agency reviewers

Command Comparison: Schedule vs Map
===================================

CruisePlan generates PNG maps through two commands with distinct characteristics:

.. list-table:: PNG Output Comparison
   :widths: 30 35 35
   :header-rows: 1

   * - **Feature**
     - **Schedule PNG** (``cruiseplan schedule``)
     - **Map PNG** (``cruiseplan map``)
   * - **Data Source**
     - Generated timeline with scheduling
     - YAML configuration only
   * - **Station Order**
     - Scheduled sequence (leg-based execution order)
     - Configuration order (definition sequence)
   * - **Timing Information**
     - Operation start times and durations
     - No timing information displayed
   * - **Cruise Track Lines**
     - Complete executed route between all operations
     - Port-to-station transit lines only
   * - **Station Visualization**
     - Uniform markers (operation type from timeline)
     - Differentiated markers (stations vs moorings)
   * - **Use Case**
     - Final schedule and execution planning
     - Initial planning and configuration review
   * - **Prerequisites**
     - Requires successful validation and scheduling
     - Works directly with YAML configuration
   * - **Performance**
     - Slower (includes scheduling calculations)
     - Faster (direct from configuration)

Schedule PNG Output (Timeline-Based)
=====================================

Generated via: ``cruiseplan schedule -c cruise.yaml --format png``

**Characteristics**:
  - Shows operations in scheduled execution order
  - Includes complete cruise track with all transits
  - Displays timing information and durations
  - Optimized routing between operations
  - Requires prior validation and scheduling success

**Visual Elements**:

.. list-table:: Schedule PNG Visual Elements
   :widths: 25 25 50
   :header-rows: 1

   * - **Element**
     - **Appearance**
     - **Information Displayed**
   * - **Stations**
     - Red circles
     - Operation name, scheduled start time
   * - **Moorings**
     - Gold stars
     - Operation name, deployment/recovery type
   * - **Transit Lines**
     - Colored lines
     - Route segments with timing
   * - **Timeline Track**
     - Connected polyline
     - Complete vessel path in execution order
   * - **Bathymetry**
     - Contour background
     - Depth context for operations

**Example Command Usage**:

.. code-block:: bash

   # Basic schedule PNG generation
   cruiseplan schedule -c cruise.yaml --format png
   
   # High-resolution output with custom bathymetry
   cruiseplan schedule -c cruise.yaml --format png --bathymetry-source gebco2025
   
   # Combined outputs for complete documentation
   cruiseplan schedule -c cruise.yaml --format png,html,latex

**Output File**: ``{cruise_name}_schedule.png``

Map PNG Output (Configuration-Based)
=====================================

Generated via: ``cruiseplan map -c cruise.yaml --format png``

**Characteristics**:
  - Shows stations in YAML configuration order
  - Displays differentiated station types (stations vs moorings)
  - Includes port connections and basic routing
  - No timing or scheduling information
  - Works with any valid YAML configuration

**Visual Elements**:

.. list-table:: Map PNG Visual Elements
   :widths: 25 25 50
   :header-rows: 1

   * - **Element**
     - **Appearance**
     - **Information Displayed**
   * - **Stations**
     - Red circles
     - Station name, coordinates
   * - **Moorings**
     - Gold stars
     - Mooring name, operation type
   * - **Port Connections**
     - Dashed lines
     - Direct connections to first/last stations
   * - **Configuration Order**
     - Numbered sequence
     - YAML definition order (not execution)
   * - **Bathymetry**
     - Contour background
     - Geographic and depth context

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

Visual Styling and Customization
=================================

Bathymetric Background
----------------------

Both PNG outputs include bathymetric background visualization:

**Bathymetry Sources**:
  - **GEBCO 2025**: High-resolution global bathymetry (default)
  - **ETOPO 2022**: Lower-resolution for faster generation

**Contour Styling**:
  - Depth contours at standard oceanographic intervals
  - Color-coded depth ranges from shallow (light) to deep (dark)
  - Automatic depth range selection based on operation area

**Configuration Options**:

.. code-block:: bash

   # High-detail bathymetry (slower generation)
   --bathymetry-source gebco2025 --bathymetry-stride 1
   
   # Fast bathymetry for quick previews
   --bathymetry-source etopo2022 --bathymetry-stride 10

Station and Operation Markers
-----------------------------

**Station Markers** (Red Circles):
  - Size proportional to operation importance
  - Labels with station names
  - Coordinate information in tooltips
  - Consistent styling across both command types

**Mooring Markers** (Gold Stars):
  - Distinctive star shape for easy identification
  - Larger size for multi-day deployments
  - Deployment vs recovery differentiation
  - Equipment type annotations

**Area Operations** (when present):
  - Polygon outlines with semi-transparent fill
  - Corner point markers with coordinates
  - Center point routing anchors
  - Area calculations displayed

Figure Customization
--------------------

**Figure Size Options**:

.. code-block:: bash

   # Standard size (default)
   --figsize 12 10
   
   # Wide format for presentations
   --figsize 16 8
   
   # High-resolution for publications
   --figsize 14 12

**Output Quality**:
  - 300 DPI resolution for publication quality
  - Vector graphics where possible
  - Anti-aliased text and lines
  - Professional cartographic styling

Integration and Workflow
=========================

Planning Workflow Integration
-----------------------------

**Initial Planning Phase** (use ``cruiseplan map``):
  1. Create initial YAML configuration
  2. Generate configuration-based PNG for review
  3. Iteratively refine station positions and operations
  4. Share planning maps with collaborators

**Final Planning Phase** (use ``cruiseplan schedule``):
  1. Validate and enrich configuration
  2. Generate timeline-based PNG with scheduling
  3. Review execution order and timing
  4. Generate final documentation set

**Documentation Generation**:

.. code-block:: bash

   # Complete documentation package
   cruiseplan schedule -c cruise.yaml --format png,html,latex,csv
   
   # Initial planning maps
   cruiseplan map -c cruise.yaml --format png,kml

Comparison with Other Formats
-----------------------------

**PNG vs HTML**:
  - PNG: Static, publication-ready, embedded in documents
  - HTML: Interactive, web-shareable, includes detailed tables

**PNG vs KML**:
  - PNG: Fixed visualization, document embedding, print-ready
  - KML: Interactive Google Earth, dynamic exploration, GPS integration

**PNG vs LaTeX**:
  - PNG: Geographic visualization, spatial relationships
  - LaTeX: Tabular data, numerical information, proposal formatting

File Management and Organization
================================

Naming Conventions
------------------

**Schedule PNG Files**:
  - Format: ``{cruise_name}_schedule.png``
  - Example: ``Arctic_Survey_2024_schedule.png``

**Map PNG Files**:
  - Format: ``{cruise_name}_map.png`` (or custom via ``--output-file``)
  - Example: ``Arctic_Survey_2024_map.png``

**Version Control**:
  - Include generation timestamp in metadata
  - Maintain separate directories for different planning phases
  - Archive previous versions for comparison

Output Directory Organization
-----------------------------

**Recommended Structure**:

.. code-block:: text

   cruise_outputs/
   ├── planning/
   │   ├── initial_map.png          # Early configuration maps
   │   └── planning_iterations/
   ├── schedules/
   │   ├── schedule_map.png         # Final timeline-based maps
   │   ├── schedule.html
   │   ├── schedule.csv
   │   └── schedule.tex
   └── presentations/
       ├── proposal_map.png         # Publication-ready figures
       └── presentation_slides.png

**Command Examples for Organization**:

.. code-block:: bash

   # Planning phase outputs
   cruiseplan map -c cruise.yaml -o planning/ --output-file initial_config.png
   
   # Final schedule outputs
   cruiseplan schedule -c cruise.yaml -o schedules/ --format all
   
   # Presentation-ready outputs
   cruiseplan schedule -c cruise.yaml --format png -o presentations/

Quality Assurance and Best Practices
=====================================

Visual Quality Checks
----------------------

**Review Checklist**:
  - All stations clearly visible and labeled
  - Bathymetric context appropriate for operation depths
  - Track lines connect logically between operations
  - No overlapping labels or markers
  - Proper scaling and geographic projection

**Common Issues and Solutions**:

.. list-table:: PNG Quality Issues
   :widths: 30 70
   :header-rows: 1

   * - **Issue**
     - **Solution**
   * - Overlapping station labels
     - Use custom figure size: ``--figsize 16 10``
   * - Unclear bathymetry
     - Reduce stride: ``--bathymetry-stride 3``
   * - Slow generation
     - Use ETOPO: ``--bathymetry-source etopo2022``
   * - Missing geographic context
     - Check coordinate validity and map projection

Performance Considerations
--------------------------

**Generation Speed**:
  - Map command: ~5-15 seconds for typical configurations
  - Schedule command: ~10-30 seconds including scheduling calculations
  - High-resolution bathymetry adds ~10-20 seconds

**Optimization Tips**:

.. code-block:: bash

   # Fast preview generation
   cruiseplan map -c cruise.yaml --bathymetry-stride 8 --show-plot
   
   # Production quality (slower)
   cruiseplan schedule -c cruise.yaml --format png --bathymetry-stride 2

PNG output provides essential visualization capabilities for cruise planning, from initial configuration review through final documentation. The dual command approach supports both rapid planning iterations and final presentation-quality outputs for complete oceanographic research workflows.