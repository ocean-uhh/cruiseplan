.. _output-formats:

==============
Output Formats
==============

CruisePlan generates multiple output formats from two main commands: ``cruiseplan schedule`` (timeline-based) and ``cruiseplan map`` (configuration-based). Each format serves specific purposes in the oceanographic research workflow from initial planning through final execution.

.. contents:: Table of Contents
   :local:
   :depth: 3

Command Overview
================

CruisePlan provides outputs through two distinct command workflows:

**Schedule Command** (``cruiseplan schedule``):
  Generates timeline-based outputs showing scheduled operations in execution order with timing calculations, durations, and optimized routing.

**Map Command** (``cruiseplan map``): 
  Generates visualization-focused outputs directly from YAML configuration for initial planning, configuration review, and standalone mapping.

Output Format Summary
=====================

.. list-table:: Output Formats by Command
   :widths: 15 25 25 35
   :header-rows: 1

   * - **Format**
     - **Schedule Command**
     - **Map Command**
     - **Primary Use Cases**
   * - **PNG**
     - ✅ Timeline-based maps
     - ✅ Configuration maps
     - Visualization, documentation, proposals
   * - **HTML**
     - ✅ Interactive summaries
     - ❌ Not available
     - Review, documentation, web sharing
   * - **LaTeX**
     - ✅ Professional tables
     - ❌ Not available
     - Cruise proposals, funding applications
   * - **CSV**
     - ✅ Operation timelines
     - ❌ Not available
     - Analysis, operational planning
   * - **NetCDF**
     - ✅ Scientific datasets
     - ❌ Not available
     - Scientific analysis, data sharing
   * - **KML**
     - ❌ Not available
     - ✅ Configuration tracks
     - Google Earth, navigation systems

Map Generation Features
=======================

Transit Lines and Area Polygon Visualization
---------------------------------------------

CruisePlan's map generation includes enhanced visualization capabilities for all operation types:

**Transit Line Visualization**:
  - **Scientific Transits**: Detailed route lines showing waypoint sequences for underway surveys
  - **Navigation Transits**: Direct lines between operations for vessel movement
  - **Vessel Track**: Complete cruise track showing actual vessel path through all operations
  - **Color Coding**: Different colors for transit types (scientific vs navigation)

**Area Polygon Visualization**:
  - **Survey Areas**: Filled polygons showing area operation boundaries
  - **Center Points**: Marked center points used for routing calculations
  - **Corner Markers**: Individual corner coordinates with labels
  - **Area Labels**: Operation names and area calculations displayed

Point/Line/Area Extraction and Styling
---------------------------------------

**Operation Type Styling**:

.. list-table:: Map Styling by Operation Type
   :widths: 25 25 50
   :header-rows: 1

   * - **Operation Type**
     - **Map Symbol**
     - **Visual Characteristics**
   * - Point Operations (Stations)
     - Red circles
     - Radius proportional to operation duration
   * - Point Operations (Moorings)
     - Gold stars
     - Larger symbols for multi-day deployments
   * - Line Operations (Transits)
     - Colored lines
     - Scientific (blue), Navigation (gray)
   * - Area Operations
     - Filled polygons
     - Semi-transparent with boundary outlines

**Extraction Methods**:
  - **Point Operations**: Extracted using station coordinates with operation-specific markers
  - **Line Operations**: Route waypoints connected with styled polylines
  - **Area Operations**: Corner coordinates formed into closed polygons with center point markers

Catalog Summary Display
-----------------------

Maps include comprehensive catalog summaries showing operation counts and statistics:

**Summary Panel Features**:
  - **Station Count**: Total point operations by type (CTD, mooring, calibration)
  - **Transit Count**: Line operations with total distance calculations
  - **Area Count**: Polygonal operations with total area coverage
  - **Duration Summary**: Total operational time by category
  - **Distance Summary**: Total cruise distance and navigation statistics

**Example Summary Display**:

.. code-block:: text

   CRUISE SUMMARY: Arctic Survey 2024
   ===================================
   Point Operations:
     • CTD Stations: 45 (avg depth: 2,847m, total time: 52.3 hours)
     • Moorings: 6 deployments, 4 recoveries (total time: 18.0 hours)
     • Calibrations: 3 (total time: 3.0 hours)
   
   Line Operations:
     • Scientific Transits: 8 (total distance: 892 km, 89.2 hours)
     • Navigation Transits: 12 (total distance: 1,456 km, 145.6 hours)
   
   Area Operations:
     • Survey Areas: 3 (total coverage: 2,847 km², total time: 24.0 hours)
   
   Total Cruise: 15.2 days at sea, 3,195 km total distance

Detailed Format Documentation
=============================

.. toctree::
   :maxdepth: 1
   :caption: Output Format Details

   output/png
   output/html
   output/latex
   output/csv
   output/netcdf
   output/kml

Format Selection
================

Choosing Output Formats
------------------------

**For Cruise Proposals**:
  Use LaTeX format for professional tables suitable for funding applications (DFG, NSF, etc.)

**For Operational Planning**:
  Combine HTML (overview) + CSV (detailed planning) + KML (navigation)

**For Scientific Analysis**:
  Use NetCDF format with ``--derive-netcdf`` for specialized analysis files

**For Visualization & Outreach**:
  Use HTML (web sharing) + KML (Google Earth integration)

Command Examples
----------------

.. code-block:: bash

   # Generate all formats
   cruiseplan schedule -c cruise.yaml --format all
   
   # Proposal preparation
   cruiseplan schedule -c cruise.yaml --format latex
   
   # Operational planning
   cruiseplan schedule -c cruise.yaml --format html,csv
   
   # Scientific analysis
   cruiseplan schedule -c cruise.yaml --format netcdf --derive-netcdf
   
   # Custom output directory
   cruiseplan schedule -c cruise.yaml --format all -o schedule/
   
   # Map outputs (PNG and KML)
   cruiseplan map -c cruise.yaml --format all
   cruiseplan map -c cruise.yaml --format kml  # KML only available from map command

Output File Naming
==================

Standard Naming Convention
--------------------------

CruisePlan uses consistent naming patterns for all output files, based on the cruise name ``{cruise_name}`` specified in the YAML configuration.:

.. list-table:: File Naming Patterns
   :widths: 20 30 50
   :header-rows: 1

   * - **Format**
     - **File Pattern**
     - **Example: "Arctic Survey 2024"**
   * - HTML
     - ``{cruise_name}_schedule.html``
     - ``Arctic_Survey_2024_schedule.html``
   * - LaTeX
     - ``{cruise_name}_schedule.tex``
     - ``Arctic_Survey_2024_schedule.tex``
   * - CSV
     - ``{cruise_name}_schedule.csv``
     - ``Arctic_Survey_2024_schedule.csv``
   * - NetCDF (Standard)
     - ``{cruise_name}_schedule.nc``
     - ``Arctic_Survey_2024_schedule.nc``
   * - NetCDF (Derived)
     - ``{cruise_name}_{type}.nc``
     - ``Arctic_Survey_2024_points.nc``
   * - KML
     - ``{cruise_name}_map.kml``
     - ``Arctic_Survey_2024_map.kml``

Specialized NetCDF Files
-------------------------

When using ``--derive-netcdf`` flag, additional specialized files are generated:

.. list-table:: Derived NetCDF Files
   :widths: 30 70
   :header-rows: 1

   * - **File**
     - **Contents**
   * - ``{cruise_name}_points.nc``
     - Point operations only (stations, moorings, calibrations)
   * - ``{cruise_name}_lines.nc``
     - Line operations only (scientific transits, surveys)
   * - ``{cruise_name}_areas.nc``
     - Area operations only (polygonal surveys, monitoring regions)

Quality Assurance
=================

Output Validation
-----------------

**Automatic Checks**: Future expansion - does not exist yet
  - CF convention compliance for NetCDF files
  - Valid KML structure for Google Earth compatibility
  - LaTeX compilation verification
  - HTML link and reference validation

**Manual Verification**:
  - Review HTML output for completeness and accuracy
  - Test KML files in Google Earth
  - Compile LaTeX files to verify table formatting
  - Import CSV files into Excel/analysis tools

Performance Considerations
--------------------------

**Large Expeditions**:
  - HTML generation may be slow for >100 operations
  - NetCDF files scale well with large datasets
  - KML files may be large for complex cruises
  - LaTeX compilation time increases with operation count

**Optimization Tips**:
  - Use ``--leg`` flag with ``schedule`` command to generate outputs for specific legs only
  - Use ``--derive-netcdf`` when specialized analysis is needed

This comprehensive output format system ensures that CruisePlan delivers professional, analysis-ready results for all aspects of oceanographic cruise planning and execution.