===========
YAML Basics
===========

CruisePlan uses YAML files to define cruise configurations. This guide covers the essential fields you need to know.

Basic Structure
===============

.. code-block:: yaml

   # Cruise metadata
   cruise_name: "North Atlantic Survey 2025"
   start_date: "2025-06-15"
   default_vessel_speed: 10.0
   turnaround_time: 30.0
   
   # Global catalog - define your operations
   points:
     - name: "STN_001"
       latitude: 60.0
       longitude: -30.0
       operation_type: CTD
       action: profile
       
   lines:
     - name: "ADCP_transect" 
       operation_type: underway
       action: ADCP
       route:
         - latitude: 60.0
           longitude: -30.0
         - latitude: 60.0
           longitude: -20.0
   
   # Schedule organization
   legs:
     - name: "leg1"
       departure_port: port_reykjavik
       arrival_port: port_bergen  
       activities: ["STN_001", "ADCP_transect"]

Essential Fields
================

Cruise Metadata
----------------

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Field**
     - **Required**
     - **Description**
   * - ``cruise_name``
     - Yes
     - Name of your cruise
   * - ``start_date``
     - Yes
     - Start date (ISO format)
   * - ``default_vessel_speed``
     - No
     - Ship speed in knots (default: 10)
   * - ``turnaround_time``
     - No
     - Time between operations in minutes

Point Operations
----------------

CTD stations, moorings, sample collection:

.. code-block:: yaml

   points:
     - name: "MOOR_001"
       operation_type: mooring
       action: deployment
       water_depth: 3500    # Optional - auto-added by 'process'
       duration: 45         # Optional - in minutes
       latitude: 60.0
       longitude: -30.0

Line Operations  
---------------

Transects, underway surveys:

.. code-block:: yaml

   lines:
     - name: "transect_north"
       operation_type: underway
       action: ADCP
       route:
         - latitude: 60.0
           longitude: -30.0
         - latitude: 62.0
           longitude: -25.0

Area Operations
---------------

Box surveys, mapping:

.. code-block:: yaml

   areas:
     - name: "survey_box"
       operation_type: survey
       action: bathymetry
       duration: 120        # minutes
       corners:
         - latitude: 60.5
           longitude: -28.0
         - latitude: 61.5
           longitude: -28.0
         - latitude: 61.5
           longitude: -27.0
         - latitude: 60.5
           longitude: -27.0

Schedule Organization
=====================

Legs organize your cruise into phases:

.. code-block:: yaml

   legs:
     - name: "leg 1"
       departure_port: port_reykjavik
       arrival_port: port_reykjavik
       first_waypoint: MOOR_001
       last_waypoint: survey_box
       activities: ["MOOR_001", "MOOR_002", "survey_box"]
       
     - name: "leg 2"
       departure_port: port_reykjavik            
       arrival_port: port_bergen
       first_waypoint: transect_north
       last_waypoint: transect_north
       activities: ["transect_north"]

Operation Types and Actions
============================

Valid combinations of ``operation_type`` and ``action`` for different activities:

**Point Operations**:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Operation Type**
     - **Valid Actions**
     - **Use Case**
   * - ``CTD``
     - ``profile``
     - Water column profiling with CTD/rosette
   * - ``water_sampling``
     - ``sampling``
     - Water sampling operations
   * - ``mooring``
     - ``deployment``, ``recovery``
     - Deploy/recover instruments (default: 999 hours)
   * - ``calibration``
     - ``calibration``
     - Equipment calibration
   * - ``port``
     - ``mob``, ``demob``
     - Departure (mobilization) / arrival (demobilization)
   * - ``waypoint``
     - ``profile``, ``sampling``
     - Navigation waypoints with optional operations

**Line Operations**:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Operation Type**
     - **Valid Actions**
     - **Use Case**
   * - ``underway``
     - ``ADCP``, ``bathymetry``, ``thermosalinograph``
     - Continuous measurements while in transit
   * - ``towing``
     - ``tow_yo``, ``seismic``, ``microstructure``
     - Towed instrument operations
   * - ``CTD``
     - ``section``
     - CTD sections (expandable to individual stations)

**Area Operations**:

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Operation Type**
     - **Valid Actions**
     - **Use Case**
   * - ``survey``
     - ``bathymetry``
     - Area surveys and mapping

Coordinates
===========

- **Latitude**: -90 to 90 (negative = South)
- **Longitude**: -180 to 180 OR 0 to 360 (negative = West)
- **Decimal degrees only** (e.g., 60.5, not 60°30')

Example: Atlantic stations
- Latitude: 60.0 (60°N)
- Longitude: -30.0 (30°W)

Common Workflow
===============

1. **Start with generated stub**: Run ``cruiseplan stations`` to create a basic file
2. **Edit operation types**: Add appropriate ``operation_type`` fields
3. **Adjust timing**: Modify ``duration`` if needed
4. **Organize legs**: Group activities into logical cruise phases
5. **Process**: Run ``cruiseplan process`` to validate and enrich

For complete field reference, see :doc:`../reference/yaml-full`.