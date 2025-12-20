.. _output-csv:

==========
CSV Output
==========

CSV format provides tabular data ideal for Excel analysis, operational planning, and integration with external systems. The output includes detailed operation schedules with all relevant parameters.

.. note::
   CSV output is only available from the **schedule command** (``cruiseplan schedule --format csv``). For configuration-based data, consider extracting station coordinates from YAML files.

Purpose and Use Cases
======================

**Primary Uses**:
  - Excel analysis and pivot tables
  - Operational planning spreadsheets
  - Integration with ship management systems
  - Custom analysis and reporting tools

**Target Audiences**:
  - Ship operations staff
  - Cruise coordinators and logistics personnel
  - Data analysts and researchers
  - Equipment managers and technicians

CSV Structure and Fields
========================

The CSV output contains comprehensive operational data with the following standard columns:

Core Fields
-----------

.. list-table:: Standard CSV Columns
   :widths: 25 15 60
   :header-rows: 1

   * - **Column Name**
     - **Data Type**
     - **Description**
   * - ``operation_name``
     - String
     - Unique identifier for each operation (e.g., "CTD_001", "MOOR_A_DEPLOY")
   * - ``operation_type``
     - String
     - Operation category (CTD, mooring, transit, calibration)
   * - ``action``
     - String
     - Specific action (profile, deployment, recovery, sampling)
   * - ``start_time``
     - ISO DateTime
     - Operation start time (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)
   * - ``end_time``
     - ISO DateTime
     - Operation end time (ISO 8601 format)
   * - ``duration_minutes``
     - Integer
     - Operation duration in minutes
   * - ``duration_hours``
     - Float
     - Operation duration in decimal hours

Geographic Fields
-----------------

.. list-table:: Geographic Data Columns
   :widths: 25 15 60
   :header-rows: 1

   * - **Column Name**
     - **Data Type**
     - **Description**
   * - ``latitude``
     - Float
     - Station latitude in decimal degrees (WGS84)
   * - ``longitude``
     - Float
     - Station longitude in decimal degrees (WGS84)
   * - ``coordinates_dmm``
     - String
     - Formatted coordinates in degrees-decimal minutes (e.g., "60°30.0'N")
   * - ``depth_meters``
     - Float
     - Water depth at station location (meters)
   * - ``operation_depth``
     - Float
     - Target operation depth (e.g., CTD cast depth, meters)

Transit and Distance Fields
---------------------------

.. list-table:: Transit Calculation Columns
   :widths: 25 15 60
   :header-rows: 1

   * - **Column Name**
     - **Data Type**
     - **Description**
   * - ``transit_distance_km``
     - Float
     - Route-based distance to this operation (kilometers)
   * - ``transit_distance_nm``
     - Float
     - Route-based distance to this operation (nautical miles)
   * - ``straight_line_distance_km``
     - Float
     - Great circle distance from previous operation (kilometers)
   * - ``route_complexity_factor``
     - Float
     - Ratio of route distance to straight-line distance (>1.0 indicates complex routing)
   * - ``transit_duration_hours``
     - Float
     - Transit time to reach this operation (hours)
   * - ``vessel_speed_knots``
     - Float
     - Vessel speed used for transit calculation (knots)

Operational Fields
------------------

.. list-table:: Operational Detail Columns
   :widths: 25 15 60
   :header-rows: 1

   * - **Column Name**
     - **Data Type**
     - **Description**
   * - ``leg_name``
     - String
     - Leg identifier for multi-leg expeditions
   * - ``cluster_name``
     - String
     - Cluster identifier if operation is part of a group
   * - ``equipment_required``
     - String
     - Primary equipment needed (semicolon-separated list)
   * - ``personnel_count``
     - Integer
     - Number of personnel required for operation
   * - ``weather_sensitivity``
     - String
     - Weather constraints (high/medium/low/none)
   * - ``day_night_preference``
     - String
     - Timing preference (day/night/any)

Example CSV Output
==================

Sample Data Structure
---------------------

.. code-block:: text

   operation_name,operation_type,action,start_time,end_time,duration_minutes,duration_hours,latitude,longitude,coordinates_dmm,depth_meters,operation_depth,transit_distance_km,transit_distance_nm,straight_line_distance_km,route_complexity_factor,transit_duration_hours,vessel_speed_knots,leg_name,cluster_name,equipment_required,personnel_count,weather_sensitivity,day_night_preference
   DEPART_REYKJAVIK,transit,departure,2024-07-01T08:00:00Z,2024-07-01T08:00:00Z,0,0.0,64.1466,-21.9426,"64°08.8'N 021°56.6'W",0,0,0.0,0.0,0.0,1.000,0.0,10.0,Atlantic_Survey,,vessel_systems,15,low,any
   TRANSIT_TO_STN001,transit,navigation,2024-07-01T08:00:00Z,2024-07-01T14:12:00Z,372,6.2,62.333,-28.167,"62°20.0'N 028°10.0'W",2847,0,187.3,101.2,187.3,1.000,6.2,10.0,Atlantic_Survey,,navigation,5,medium,any
   CTD_001,CTD,profile,2024-07-01T14:12:00Z,2024-07-01T17:00:00Z,168,2.8,62.333,-28.167,"62°20.0'N 028°10.0'W",2847,2847,0.0,0.0,0.0,1.000,0.0,0.0,Atlantic_Survey,North_Atlantic_Section,CTD_rosette;winch,8,high,day
   TRANSIT_TO_STN002,transit,navigation,2024-07-01T17:00:00Z,2024-07-01T20:06:00Z,186,3.1,61.500,-29.833,"61°30.0'N 029°50.0'W",3124,0,45.2,24.4,45.2,1.000,3.1,10.0,Atlantic_Survey,,navigation,5,medium,any

Data Types and Formatting
--------------------------

**Timestamp Format**:
  - ISO 8601 format: ``YYYY-MM-DDTHH:MM:SSZ``
  - UTC timezone for consistency
  - 24-hour time format
  - Sortable chronological order

**Coordinate Precision**:
  - Decimal degrees: 6 decimal places (±0.1m accuracy)
  - DMM format: 1 decimal place for minutes (±1.8m accuracy)
  - Consistent hemisphere indicators (N/S, E/W)

**Distance and Duration Values**:
  - Kilometers: 1 decimal place
  - Nautical miles: 1 decimal place
  - Hours: 1 decimal place
  - Minutes: Integer values

Excel Integration
=================

Spreadsheet Optimization
-------------------------

**Column Widths**:
  - Operation names: 15 characters
  - Coordinates: 12 characters
  - Times and durations: 10 characters
  - Descriptions: 25 characters

**Data Validation**:
  - Dropdown lists for operation types
  - Date/time formatting validation
  - Numeric range validation for coordinates
  - Conditional formatting for operational status

**Pivot Table Support**:
  - Operation type summaries
  - Duration totals by leg or cluster
  - Geographic distribution analysis
  - Equipment utilization tracking

Advanced Excel Features
-----------------------

**Formulas and Calculations**:

.. code-block:: excel

   # Total cruise duration
   =SUM(duration_hours:duration_hours)
   
   # Average vessel speed
   =AVERAGE(vessel_speed_knots:vessel_speed_knots)
   
   # Operations per day
   =COUNTIFS(start_time:start_time,">=DATE",start_time:start_time,"<DATE+1")

**Conditional Formatting Rules**:
  - High weather sensitivity operations (red highlighting)
  - Night operations (blue background)
  - Long-duration operations (>4 hours, bold text)
  - Complex routing (route_complexity_factor >1.2, orange highlight)

**Charts and Visualization**:
  - Timeline charts using start_time and duration_hours
  - Distance charts showing cumulative transit distances
  - Operation type distribution pie charts
  - Daily operation counts bar charts

Data Analysis Applications
==========================

Operational Planning
--------------------

**Resource Scheduling**:
  - Filter by equipment_required for deployment planning
  - Group by personnel_count for crew scheduling
  - Sort by weather_sensitivity for contingency planning
  - Analyze day_night_preference for shift planning

**Time and Motion Studies**:
  - Calculate setup and breakdown times
  - Analyze travel efficiency (route_complexity_factor)
  - Identify operational bottlenecks
  - Optimize vessel speed for fuel efficiency

**Geographic Analysis**:
  - Plot station positions on maps
  - Calculate operational density per region
  - Analyze transit efficiency between legs
  - Identify geographic clustering opportunities

Quality Control
---------------

**Data Validation Checks**:

.. code-block:: excel

   # Check for time sequence consistency
   =IF(B2>C2,"ERROR: End time before start time","OK")
   
   # Validate coordinate ranges
   =IF(OR(H2<-90,H2>90),"ERROR: Invalid latitude","OK")
   
   # Check duration calculations
   =IF(ABS(F2-(C2-B2)*24*60)>1,"WARNING: Duration mismatch","OK")

**Consistency Verification**:
  - Cross-check calculated vs provided durations
  - Verify distance calculations between operations
  - Validate coordinate format consistency
  - Check for duplicate operation names

Integration with External Systems
=================================

Ship Management Systems
-----------------------

**ECDIS Integration**:
  - Export waypoint lists for Electronic Chart Display systems
  - Format coordinates for navigation system import
  - Generate route files for autopilot systems
  - Create backup navigation data

**Equipment Management**:
  - Link to equipment databases via equipment_required field
  - Generate maintenance schedules based on operation types
  - Track equipment utilization across operations
  - Plan spare parts requirements

**Personnel Systems**:
  - Interface with crew scheduling systems
  - Generate watch schedules based on operation timing
  - Plan scientific party rotations
  - Calculate personnel hour requirements

Data Exchange Formats
---------------------

**Standard Exports**:

.. code-block:: bash

   # Export specific columns for navigation systems
   csvcut -c operation_name,latitude,longitude,start_time cruise_schedule.csv > waypoints.csv
   
   # Filter operations for equipment planning
   csvgrep -c operation_type -m "CTD" cruise_schedule.csv > ctd_operations.csv
   
   # Generate summary statistics
   csvstat cruise_schedule.csv

**API Integration**:
  - REST API endpoints for real-time updates
  - JSON conversion for web service integration
  - Database import formats (SQL, NoSQL)
  - Cloud storage synchronization

Best Practices
==============

File Management
---------------

**Version Control**:
  - Include timestamps in filenames
  - Maintain change logs for updates
  - Archive previous versions
  - Document calculation methodology changes

**Backup and Security**:
  - Regular backups of operational data
  - Access control for sensitive information
  - Data encryption for confidential cruises
  - Synchronization with vessel systems

Usage Guidelines
---------------

**For Operational Staff**:
  - Focus on time, location, and equipment columns
  - Use filters to show relevant operations only
  - Create custom views for different user roles
  - Generate daily/weekly operational summaries

**For Scientific Analysis**:
  - Utilize geographic and depth data
  - Analyze operation efficiency and timing
  - Calculate sampling density and coverage
  - Generate scientific productivity metrics

The CSV output format provides flexible, analyzable data that integrates seamlessly with existing operational and analytical workflows throughout the cruise planning and execution process.