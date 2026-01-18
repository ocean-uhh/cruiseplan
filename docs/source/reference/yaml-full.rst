============================
YAML Configuration Reference
============================

Complete reference for all YAML configuration fields in CruisePlan.

.. contents:: Contents
   :local:
   :depth: 2

Configuration Structure
=======================

CruisePlan YAML files have three main sections:

.. code-block:: yaml

   # 1. Cruise-wide metadata and settings
   cruise_name: "Example Cruise 2025"
   description: "Oceanographic survey"
   start_date: "2025-06-15"
   
   # 2. Global catalog (reusable definitions)
   points: [...]        # Point operations
   lines: [...]         # Line operations  
   areas: [...]         # Area operations
   
   # 3. Schedule organization
   legs: [...]          # Execution phases

Coordinate Conventions
======================

- **Latitude**: -90.0 to 90.0 decimal degrees (negative = South)
- **Longitude**: -180.0 to 180.0 decimal degrees (negative = West)
- **Depth**: meters below sea level (positive values)
- **Distance**: kilometers
- **Duration**: minutes

Cruise Metadata
===============

Root-level cruise configuration fields:

.. code-block:: yaml

   cruise_name: "North Atlantic Survey 2025"
   start_date: "2025-06-15"           # ISO format
   day_start_hour: 6                  # Start of working day (0-23)
   day_end_hour: 22                   # End of working day (0-23)
   default_vessel_speed: 10.0         # Transit speed in knots
   turnaround_time: 15                # Time between operations in minutes
   ctd_descent_rate: 1.0              # CTD descent speed in m/s
   ctd_ascent_rate: 1.0               # CTD ascent speed in m/s

Point Operations
================

Individual station operations (CTD, moorings, sampling):

Required Fields
---------------

.. code-block:: yaml

   points:
     - name: "STN_001"               # Unique identifier
       latitude: 60.0               # Decimal degrees
       longitude: -30.0             # Decimal degrees

Optional Fields  
---------------

.. code-block:: yaml

   points:
     - name: "STN_001"
       latitude: 60.0
       longitude: -30.0
       operation_type: CTD          # Operation category
       action: profile              # Specific action
       water_depth: 3500            # Water depth (auto-filled by 'process')
       duration: 45                 # Time for operation in minutes
       comment: "Deep water station"

Line Operations
===============

Transect and underway survey operations:

Required Fields
---------------

.. code-block:: yaml

   lines:
     - name: "transect_A"
       route:                       # List of waypoints
         - latitude: 60.0
           longitude: -30.0
         - latitude: 60.0  
           longitude: -20.0

Optional Fields
---------------

.. code-block:: yaml

   lines:
     - name: "transect_A"
       operation_type: underway
       action: ADCP
       route:
         - latitude: 60.0
           longitude: -30.0
         - latitude: 60.0
           longitude: -20.0
       comment: "Cross-slope section"
       vessel_speed: 8.0            # Speed during transect

Area Operations
===============

Box surveys and mapping operations:

Required Fields
---------------

.. code-block:: yaml

   areas:
     - name: "survey_box"
       corners:                     # Polygon corners (min 3)
         - latitude: 60.5
           longitude: -28.0
         - latitude: 61.5
           longitude: -28.0
         - latitude: 61.5
           longitude: -27.0
         - latitude: 60.5
           longitude: -27.0

Optional Fields
---------------

.. code-block:: yaml

   areas:
     - name: "survey_box"
       operation_type: survey
       action: bathymetry
       corners:
         - latitude: 60.5
           longitude: -28.0
         - latitude: 61.5
           longitude: -28.0
         - latitude: 61.5
           longitude: -27.0
         - latitude: 60.5
           longitude: -27.0
       duration: 120               # Total survey time in minutes
       comment: "High-priority mapping area"

Schedule Organization
=====================

Legs organize activities into cruise phases:

Basic Leg
---------

.. code-block:: yaml

   legs:
     - name: "leg1"
       activities: ["STN_001", "STN_002", "transect_A"]

Advanced Leg Options
--------------------

.. code-block:: yaml

   legs:
     - name: "leg1"
       description: "Main science leg"
       departure_port: port_reykjavik     # Departure port
       arrival_port: port_bergen          # Arrival port
       first_activity: STN_001
       last_activity: transect_A
       activities: ["STN_001", "STN_002", "transect_A"] 
       
       # Leg-level parameter overrides
       vessel_speed: 12.0
       turnaround_time: 20
       distance_between_stations: 25.0

Clusters
--------

Group activities within legs for advanced scheduling:

.. code-block:: yaml

   legs:
     - name: "leg1"
       clusters:
         - name: "northern_stations"
           activities: ["CTD_001", "CTD_002"]
           strategy: "optimize_distance"    # Reorder for efficiency
         - name: "southern_stations" 
           activities: ["CTD_003", "CTD_004"]
           strategy: "preserve_order"       # Keep original order

Operation Types
===============

Standard operation types with default durations:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Type**
     - **Default Duration**
     - **Description**
   * - ``ctd``
     - 45 min
     - CTD/rosette operations
   * - ``underway``
     - Transit time
     - Continuous measurements
   * - ``multibeam``
     - 2 hours
     - Seafloor mapping
   * - ``mooring``
     - 4 hours
     - Mooring operations
   * - ``net_tow``
     - 90 min
     - Biological sampling
   * - ``grab_sample``
     - 30 min
     - Sediment/water sampling
   * - ``adcp``
     - Transit time
     - Current profiling
   * - ``xbt``
     - 15 min
     - Expendable temperature probe

Validation Rules
================

CruisePlan validates configurations with these rules:

- **Unique names**: All operation names must be unique
- **Valid coordinates**: Lat/lon within valid ranges
- **Date format**: ISO format YYYY-MM-DD
- **Positive durations**: Times must be > 0
- **Referenced activities**: All leg activities must exist in catalog

Parameter Inheritance
=====================

Parameters cascade from cruise → leg → cluster → operation:

.. code-block:: yaml

   # Cruise level (applied to all)
   vessel_speed_kt: 10.0
   
   legs:
     - name: "leg1"
       vessel_speed_kt: 12.0      # Overrides cruise default
       activities:
         - "CTD_001"              # Uses leg speed: 12.0 kt
         
   points:
     - name: "CTD_001"
       vessel_speed_kt: 8.0       # Overrides leg speed for this operation

Comments and Documentation
==========================

Add comments to document your configuration:

.. code-block:: yaml

   points:
     - name: "CTD_001"
       latitude: 60.0
       longitude: -30.0
       comment: "Deep water station for overflow monitoring"
       
   legs:
     - name: "leg1"
       comment: "Main science operations in Denmark Strait"
       activities: ["CTD_001"]

File Processing
===============

CruisePlan processes files in this sequence:

1. **Parse YAML**: Load and validate syntax
2. **Validate structure**: Check required fields and references
3. **Enrich data**: Add depths, distances, durations
4. **Generate outputs**: Create timeline and deliverables

For examples and workflows, see :doc:`../user-guide/workflows`.