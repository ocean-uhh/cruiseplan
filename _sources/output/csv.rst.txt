.. _output-csv:

==========
CSV Output
==========

CSV format provides tabular data ideal for Excel analysis, operational planning, and integration with external systems. The output includes detailed operation schedules with a relevant subset of parameters.

.. note::
   CSV output is available from the **schedule command** (``cruiseplan schedule --format csv``). For configuration-based data, consider extracting station coordinates from YAML files.

Purpose and Use Cases
======================

**Primary Uses**:
  - Excel-based on the fly updates to the cruise schedule
  - Operational planning spreadsheets
  - Integration with ship management systems (e.g. to provide waypoints)

CSV Structure and Fields
========================

The CSV output contains operational data with the following columns:

Core Fields
-----------

.. list-table:: Standard CSV Columns
   :widths: 25 15 60
   :header-rows: 1

   * - **Column Name**
     - **Data Type**
     - **Description**
   * - ``activity``
     - String
     - type of activty (e.g., "Port_Departure", "Station", "Transit", "Area")
   * - ``label``
     - String
     - Unique identifier for each operation (e.g., "CTD_001", "MOOR_A_DEPLOY")
   * - ``operation_action``
     - String
     - Operation category (CTD, mooring, transit, calibration) and action (deploy, recover, profile)
   * - ``start_time``
     - ISO DateTime
     - Operation start time (ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ)
   * - ``end_time``
     - ISO DateTime
     - Operation end time (ISO 8601 format)
   * - ``Transit dist [nm]``
     - Float
     - Route-based distance to this operation (nautical miles)
   * - ``Vessel speed [kt]``
     - Float
     - Vessel speed used for transit calculation (knots)
   * - ``Duration [hrs]``
     - Integer
     - Operation duration in minutes
   * - ``Depth [m]``
     - Float
     - Target operation depth (e.g., CTD cast depth, meters)
   * - ``Lat [deg]``
     - Float
     - Station latitude in decimal degrees (WGS84)
   * - ``Lon [deg]``
     - Float
     - Station longitude in decimal degrees (WGS84)
   * - ``Lat [deg_rounded]``
     - Float
     - Station latitude in integer (rounded) degrees (WGS84)
   * - ``Lat [min]``
     - Float
     - Station latitude in decimal minutes (WGS84)
   * - ``Lon [deg_rounded]``
     - Float
     - Station longitude in integer (rounded) degrees (WGS84)
   * - ``Lon [min]``
     - Float
     - Station longitude in decimal minutes (WGS84)
   * - ``leg_name``
     - String
     - Leg identifier for multi-leg expeditions


Example CSV Output
==================

Sample Data Structure
---------------------

.. code-block:: text

   activity,label,operation_action,start_time,end_time,Transit dist [nm],Vessel speed [kt],Duration [hrs],Depth [m],Lat [deg],Lon [deg],Lat [deg_rounded],Lat [min],Lon [deg_rounded],Lon [min],leg_name
  Port_Departure,Departure: Halifax to Operations,,1970-01-01T00:00:00,1970-01-03T09:46:00,577.8,10.0,57.8,0,44.6488,-63.5752,44,38.93,-63,34.51,Mixed_Survey
  Station,STN_001,Station profile,1970-01-03T09:46:00,1970-01-03T10:18:00,0.0,0,0.5,58,45.0,-50.0,45,0.0,-50,0.0,Mixed_Survey
  Transit,Transit to ADCP_Survey,Transit,1970-01-03T10:48:00,1970-01-03T16:49:00,60.0,10.0,6.0,0,46.0,-50.0,46,0.0,-50,0.0,Mixed_Survey
  Transit,ADCP_Survey,Transit (ADCP),1970-01-03T16:49:00,1970-01-04T04:49:00,60.0,5.0,12.0,0,46.0,-50.0,46,0.0,-50,0.0,Mixed_Survey
  Transit,Transit to Area_01,Transit,1970-01-04T05:19:00,1970-01-04T11:19:00,60.0,10.0,6.0,0,48.0,-50.0,48,0.0,-50,0.0,Mixed_Survey
  Area,Area_01,Area bathymetry,1970-01-04T11:19:00,1970-01-04T13:19:00,0.0,0,2.0,0,48.0,-50.0,48,0.0,-50,0.0,Mixed_Survey
  Port_Arrival,Arrival: Operations to Cadiz,Port_Arrival,1970-01-04T13:19:00,1970-01-13T00:14:00,2029.1,10.0,202.9,0,36.5298,-6.2923,36,31.79,-6,17.54,Mixed_Survey


Data Types and Formatting
--------------------------

**Timestamp Format**:
  - ISO 8601 format: ``YYYY-MM-DDTHH:MM:SS``
  - UTC timezone for consistency
  - 24-hour time format
  - Sortable chronological order

**Coordinate Precision**:
  - Decimal degrees: 5 decimal places (±1m accuracy)
  - DMM format: 2 decimal place for minutes (±.1m accuracy)
  - Signed values (no hemisphere indicators).  When degrees are negative, minutes are also negative allowing direct addition.
  
**Distance and Duration Values**:
  - Nautical miles: 1 decimal place
  - Hours: 1 decimal place

Excel Integration
=================

Example Excel Display
---------------------

.. figure:: ../_static/screenshots/csv_output_excel.png
   :alt: CSV output displayed in Excel showing cruise schedule data
   :align: center
   :width: 90%

   CSV schedule data from ``tc4_mixed_ops_enriched.yaml`` displayed in Excel, showing the complete timeline with activity types, coordinates, timing, and transit information organized in a spreadsheet format suitable for operational planning.

Note that as provided, the CSV file does not include any special formatting, formulas, or styling.  Users can apply their own Excel features as needed.  E.g., the timing can be updated using formulas and the duration column, and conditional formatting can be applied to highlight daytime vs nighttime operations, or specific types of operations.

