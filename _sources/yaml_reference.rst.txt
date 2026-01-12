.. _yaml-reference:

============================
YAML Configuration Reference
============================

This document provides a comprehensive reference for all YAML configuration fields in CruisePlan, including validation rules, special behaviors, and conventions.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
========

CruisePlan uses YAML configuration files to define oceanographic cruises. The configuration consists of three main parts:

1. **:ref:`Cruise-wide metadata and settings <cruise-wide-metadata>`**: Cruise-level fields defining defaults and settings
2. **Global Catalog**: Definitions of activities: points, lines and areas (reusable components)
3. **Schedule Organization**: Legs and clusters that organize catalog items into execution order (see :ref:`simplified-leg-creation` for default leg behavior)

.. tip::
  **Comments in yamls:** While CruisePlan supports some comments (at the top of the file), it is recommended to avoid comments within YAML files as they may not be preserved during processing.  Instead, use the `comment` fields for documentation purposes.
  
.. _configuration-structure:

Configuration Structure
-----------------------

.. code-block:: yaml

   # Cruise-wide Metadata and Settings
   cruise_name: "Example Cruise 2025"
   description: "Oceanographic survey of the North Atlantic"
   
   # Global Catalog (Reusable Definitions)
   points: [...]        # Point definitions for station operations
   lines: [...]         # Line operation definitions for transects and sections
   areas: [...]         # Area operation definitions for survey regions
   
   # Schedule Organization
   legs: [...]          # Execution phases with clusters/activities/sequences

.. warning::
   **YAML Duplicate Key Limitation**: You cannot have multiple yaml sections with the same name (e.g., multiple ``clusters:`` keys) in a single YAML file as they will overwrite each other. Instead, define multiple clusters as individual items within a single ``clusters:`` list.

.. _coordinate-conventions:


Formats and data conventions
----------------------------

- **Depth Convention**: Positive values represent depth below sea surface (meters)
- **Bathymetry Precision**: Depths from bathymetry will be rounded to **nearest whole meter** (though 1 decimal place is acceptable)
- **Manual Depths**: Can be specified to any precision but will be validated as ≥ 0
- **Decimal Degrees**: All coordinates are stored internally as decimal degrees with **5 decimal places precision** (approximately 1.1 meter resolution).
- **Longitude Range Consistency**: The entire cruise configuration must use **either** [-180°, 180°] **or** [0°, 360°] consistently. Mixing ranges will trigger validation errors.

**Input Formats Supported**:

.. code-block:: yaml

    latitude: 47.5678
    longitude: -52.1234


See also :doc:`units_and_defaults` for detailed conventions on units and default values used throughout CruisePlan.

.. _simplified-leg-creation:

Simplified Leg Creation
-----------------------

For simple single-leg cruises, you can omit the ``legs`` section entirely.  In this case, **departure_port** and **arrival_port** are required at a cruise level.  During the enrichment process, a default leg will be created and the ports will be moved to the leg section.  

**Automatic Default Leg Creation**:

.. code-block:: yaml

   # Simple configuration - no legs required!
   cruise_name: "Simple Survey 2025"
   departure_port: "port_reykjavik"    # Allowed when no explicit legs
   arrival_port: "port_reykjavik"      # Allowed when no explicit legs
   default_vessel_speed: 8.0
   
   points:
     - name: "STN_001"
       latitude: 64.0
       longitude: -22.0
       operation_type: "CTD"
       action: "profile"
   
   # CruisePlan automatically creates:
   # legs:
   #   - name: "Main_Leg"
   #     description: "Main cruise leg"
   #     departure_port: "port_reykjavik"
   #     arrival_port: "port_reykjavik"
   #     activities: ["STN_001"]

**Port Restrictions**:

- **Cruise-level ports ALLOWED**: When no ``legs`` section is defined (enables automatic default leg creation)
- **Cruise-level ports FORBIDDEN**: When explicit ``legs`` are defined (prevents configuration conflicts)

.. code-block:: yaml

   # ✅ VALID: Ports allowed for automatic leg creation
   cruise_name: "Auto Leg Example"
   departure_port: "port_halifax"      # OK - no explicit legs
   arrival_port: "port_st_johns"       # OK - no explicit legs
   points: [...]

   # ❌ INVALID: Ports forbidden with explicit legs
   cruise_name: "Manual Leg Example"
   departure_port: "port_halifax"      # ERROR - explicit legs defined
   arrival_port: "port_st_johns"       # ERROR - explicit legs defined
   legs:
     - name: "Custom_Leg"
       departure_port: "port_halifax"  # Use ports here instead
       arrival_port: "port_st_johns"

.. _cruise-wide-metadata:

Cruise-wide metadata
====================

.. _cruise-metadata:


.. list-table:: Basic Cruise Information
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``cruise_name``
     - str
     - *required*
     - Name of the cruise
   * - ``description``
     - str
     - None
     - Human-readable description of the cruise
   * - ``start_date``
     - str
     - "1970-01-01T00:00:00+00:00"
     - Cruise start date (ISO format "YYYY-MM-DD" or full ISO datetime "YYYY-MM-DDTHH:MM:SS")
   * - ``start_time``
     - Optional[str]
     - "08:00"
     - Cruise start time (HH:MM format). Only used if start_date is date-only format



.. list-table:: Vessel and Operations
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``default_vessel_speed``
     - float
     - *required*
     - Default vessel speed in knots (>0, <20; warns if <1)
   * - ``default_distance_between_stations``
     - float
     - 20.0
     - Default station spacing in km (>0, <150; warns if <4 or >50)
   * - ``turnaround_time``
     - float
     - 10.0
     - Station turnaround time in minutes (≥0; warns if >60)
   * - ``ctd_descent_rate``
     - float
     - 1.0
     - CTD descent rate in m/s (0.5-2.0)
   * - ``ctd_ascent_rate``
     - float
     - 1.0
     - CTD ascent rate in m/s (0.5-2.0)


.. list-table:: Operational choices
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``day_start_hour``
     - int
     - 8
     - Start hour for daytime operations (0-23)
   * - ``day_end_hour``
     - int
     - 20
     - End hour for daytime operations (0-23, must be > day_start_hour)

.. _ports-transfers:

Ports and Routing Waypoints
---------------------------

**Port Definition**: Ports are defined within legs and reference either global port definitions (see :ref:`global_ports_reference`) or inline port specifications.

.. list-table:: Port Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Name of the port
   * - ``latitude``
     - float
     - *required*
     - Latitude in decimal degrees (see :ref:`coordinate-conventions`)
   * - ``longitude``
     - float  
     - *required*
     - Longitude in decimal degrees (see :ref:`coordinate-conventions`)
   * - ``timezone``
     - str
     - "UTC"
     - Timezone identifier (e.g., "America/St_Johns")

**Example**: Port definitions within legs:

.. code-block:: yaml

   legs:
     - name: "Atlantic_Survey"
       departure_port:
         name: "St. Johns"
         latitude: 47.5678
         longitude: -52.1234
         timezone: "America/St_Johns"  # Optional, defaults to UTC
       arrival_port:
         name: "Reykjavik"
         latitude: 64.1355
         longitude: -21.8954
         timezone: "Atlantic/Reykjavik"



.. _global-catalog:

Global Catalog Definitions
===========================

The global catalog contains reusable definitions that can be referenced by legs and clusters.

.. note::
   **Configuration Architecture**
   
   CruisePlan uses a unified architecture centered on the `CruiseInstance` class:
   
   1. **YAML Configuration**: Validated and parsed using Pydantic models (`PointDefinition`, `LineDefinition`, `AreaDefinition`)
   2. **CruiseInstance**: Single source of truth containing the complete cruise configuration
   3. **Direct Processing**: Timeline generation and output creation work directly with the configuration objects
   
   This streamlined approach eliminates the need for conversion layers and maintains consistency between configuration and execution.

.. _point-definition:

Point Definition
-------------------

Point definitions specify point operations at fixed locations. They handle CTD casts, water sampling, mooring operations, and calibration activities with built-in duration calculations.

.. code-block:: yaml

   points:
     - name: "STN_001"
       operation_type: "CTD"
       action: "profile"
       latitude: 50
       longitude: -40
       operation_depth: 500.0  # CTD cast depth in meters
       water_depth: 3000.0     # Seafloor depth in meters (optional: will be enriched from bathymetry)
       duration: 120.0         # Optional: manual override in minutes
       comment: "Deep water station"

.. _point-fields:

Fields, Operations & Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Point Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the station
   * - ``operation_type``
     - OperationTypeEnum
     - *required*
     - Type of scientific operation (see :ref:`operation-types`)
   * - ``action``
     - ActionEnum
     - *required*
     - Specific action for the operation (see :ref:`action-types`)
   * - ``latitude``
     - GeoPoint
     - *required*
     - Geographic coordinates (see :ref:`coordinate-conventions`)
   * - ``longitude``
     - GeoPoint
     - *required*
     - Geographic coordinates (see :ref:`coordinate-conventions`)
   * - ``operation_depth``
     - float
     - None
     - Target operation depth (e.g., CTD cast depth) in meters (≥0). Used for duration calculations.
   * - ``water_depth`` 
     - float
     - None
     - Water depth at location (seafloor depth) in meters (≥0). Used for bathymetry validation and routing.
   * - ``duration``
     - float
     - None
     - Manual duration override in minutes (≥0)
   * - ``comment``
     - str
     - None
     - Human-readable comment or description
   * - ``history``
      - List[str]
      - []
      - List of historical notes or changes
   * - ``delay_start``
     - float
     - None
     - Time to wait before operation begins in minutes (≥0)
   * - ``delay_end``
     - float
     - None
     - Time to wait after operation ends in minutes (≥0)

**Depth Field Semantics:**

The distinction between ``operation_depth`` and ``water_depth`` meaningfully impacts duration calculations in the scheduler:

- **``operation_depth``**: How deep the operation goes (e.g., CTD cast depth)
  
  - Used for duration calculations (deeper operations take longer)
  - Can be less than, equal to, or greater than water_depth
  - Examples: 500m CTD cast in 3000m water

- **``water_depth``**: Actual seafloor depth at the location
  
  - Used for bathymetric validation and route planning
  - Automatically enriched from bathymetry data if missing
  - Should represent true seafloor depth for the coordinates

**Note:** that the `operation_depth` only affects timing for the CTD profile calculation.  Mooring timing must be specified manually via the `duration` field.

.. _operation-types:

Operation Types
...............

.. list-table:: Valid Operation Types
   :widths: 25 75
   :header-rows: 1

   * - Operation Type
     - Description
   * - ``CTD``
     - Conductivity-Temperature-Depth profiling
   * - ``water_sampling``
     - Water sample collection (bottles, etc.)
   * - ``mooring``
     - Mooring deployment or recovery operations
   * - ``calibration``
     - Equipment calibration or validation

.. _action-types:

Action Types
...............

.. list-table:: Valid Actions by Operation Type
   :widths: 20 25 55
   :header-rows: 1

   * - Operation Type
     - Valid Actions
     - Description
   * - ``CTD``
     - ``profile``
     - Standard CTD cast operation
   * - ``water_sampling``
     - ``sampling``
     - Water sample collection
   * - ``mooring``
     - ``deployment``, ``recovery``
     - Deploy new mooring or recover existing
   * - ``calibration``
     - ``calibration``
     - Equipment calibration procedure

.. _duration-calculation:

Duration Calculation
~~~~~~~~~~~~~~~~~~~~

The duration calculation depends on operation type and manual overrides:

1. **Manual Duration**: If ``duration`` field is specified, this value is used directly
2. **CTD Operations**: Duration calculated based on depth, descent/ascent rates, and turnaround time  
3. **Mooring Operations**: Uses manual duration or falls back to default mooring duration (60 minutes)
4. **Port/Waypoint Operations**: Returns 0.0 minutes (no operation time)
5. **Other Operations**: Returns 0.0 minutes if no manual duration specified

**CTD Duration Formula**:

.. code-block:: python

   # CTD duration calculation
   descent_time = depth / ctd_descent_rate  # seconds
   ascent_time = depth / ctd_ascent_rate    # seconds
   total_duration = (descent_time + ascent_time) / 60 + turnaround_time  # minutes

.. _enhanced-timing:

Buffer Time Configuration
.........................

The buffer time system provides multiple levels of buffer time control for realistic operational scenarios:

.. code-block:: yaml

   points:
     - name: "Mooring_Deploy" 
       operation_type: "mooring"
       action: "deployment"
       latitude: 53.0
       longitude: -40.0
       duration: 240.0         # 4 hours deployment time
       delay_start: 120.0      # Wait 2h for daylight
       delay_end: 60.0         # Wait 1h for anchor settling
   
   legs:
     - name: "Deep_Water_Survey"
       buffer_time: 480.0      # 8h weather contingency for entire leg
       activities: ["Mooring_Deploy", "STN_001", "STN_002"]

**Buffer Time Types**:

- **delay_start**: Time to wait before operation begins (e.g., daylight requirements, weather windows)
- **delay_end**: Time to wait after operation ends (e.g., equipment settling, safety checks)  
- **buffer_time**: Leg-level contingency time applied at leg completion (e.g., weather delays)

.. _line-definition:

Line Definition
-------------------

Line definitions specify movement routes with waypoints, handling distance and timing calculations directly. When `operation_type` and `action` are specified, they become scientific line operations (ADCP, bathymetry, etc.). Without these fields, lines remain user-defined operations with timing calculated purely from route distance and vessel speed.

.. code-block:: yaml

   lines:
     - name: "ADCP_Line_A"
       route:
         - latitude: 50.0
           longitude: -40.0
         - latitude: 51.0
           longitude: -40.0
         - latitude: 52.0
           longitude: -40.0
       operation_type: "underway"   
       action: "ADCP"               
       vessel_speed: 8.0           # Optional: override default speed
       comment: "Deep water ADCP transect"

.. _transit-fields:

Fields, Operations & Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Transect Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the transect
   * - ``route``
     - List[GeoPoint]
     - *required*
     - Waypoints defining the transect route
   * - ``operation_type``
     - Optional[LineOperationTypeEnum]
     - None
     - Type of line operation (``underway``, ``towing``)
   * - ``action``
     - Optional[ActionEnum]
     - None
     - Specific scientific action (required if operation_type set)
   * - ``vessel_speed``
     - Optional[float]
     - None
     - Speed override for this transect in knots
   * - ``comment``
     - Optional[str]
     - None
     - Human-readable description

.. _line-operation-types:

Line Operation Types
....................

.. list-table:: Valid Line Operations
   :widths: 20 25 55
   :header-rows: 1

   * - Operation Type
     - Valid Actions
     - Description
   * - ``underway``
     - ``ADCP``, ``bathymetry``, ``thermosalinograph``
     - Underway data collection
   * - ``towing``
     - ``tow_yo``, ``seismic``, ``microstructure``
     - Towed instrument operations

.. _ctd-sections:
.. _section-definition:


CTD Section Special Case
~~~~~~~~~~~~~~~~~~~~~~~~

CTD sections are a special type of transect (line operation) that can be expanded into individual stations (point operations):

.. code-block:: yaml

   lines:
     - name: "53N_Section"
       distance_between_stations: 25.0  # km
       reversible: true
       points: []  # Populated during expansion
       operation_type: "CTD"
       action: "section"
       route:
         - latitude: 53.0
           longitude: -40.0
         - latitude: 53.0
           longitude: -30.0

.. list-table:: Section Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the section
   * - ``operation_type``
     - OperationTypeEnum
     - *required*
     - Must be ``CTD`` for sections
   * - ``action``
     - ActionEnum
     - *required*
     - Must be ``section`` for sections
   * - ``route``
     - List[GeoPoint]
     - *required*
     - Waypoints defining the section route
   * - ``distance_between_stations``
     - Optional[float]
     - None
     - Spacing between stations in km
   * - ``reversible``
     - bool
     - True
     - Whether section can be traversed in reverse (**not yet implemented**)



**Expansion Behavior**:

- Use ``cruiseplan enrich --expand-sections`` to convert CTD sections into individual station sequences
- Each station gets coordinates interpolated along the route
- Depths are calculated from bathymetry data
- Station spacing uses ``default_distance_between_stations`` or section-specific spacing

.. warning::
   **Validation Warning**: The validate command will warn about unexpanded CTD sections and recommend using the enrich command with ``--expand-sections``.


Duration Calculation
~~~~~~~~~~~~~~~~~~~~

Transit operations (scientific transits and vessel movements) calculate duration based on route distance and vessel speed using the `LineOperation.calculate_duration()` method:

.. code-block:: python

  # Transit duration calculation (in LineOperation.calculate_duration())
  total_route_distance_km = sum(
     haversine_distance(p1, p2) for p1, p2 in zip(route, route[1:])
  )
  route_distance_nm = total_route_distance_km * 0.539957  # km -> nautical miles
  vessel_speed = transect.vessel_speed or config.default_vessel_speed  # knots
  duration_hours = route_distance_nm / vessel_speed
  duration_minutes = duration_hours * 60

**Key Points:**

- **Route Distance**: Sum of haversine distances between all consecutive waypoints in the route
- **Vessel Speed**: Uses transect-specific `vessel_speed` if specified, otherwise falls back to cruise-level `default_vessel_speed`
- **Operation Classification**: Transects with `operation_type` and `action` become scientific operations (ADCP surveys, bathymetry mapping, etc.), while those without these fields remain simple route definitions
- **Duration Calculation**: All transects calculate duration using the same route distance and vessel speed formula, regardless of whether they have scientific operation types

**CTD Section Expansion**: When CTD sections are expanded using `cruiseplan enrich --expand-sections`, the resulting stations are treated as regular CTD stations with standard CTD duration calculations based on depth, descent/ascent rates, and turnaround time.

**Note**: The scheduler also automatically generates NavigationalTransit objects (not visible in YAML) to handle vessel movement between non-adjacent operations (> 0.1 nautical miles apart).


.. _area-definition:

Area Definition
----------------

Areas represent operations covering defined geographic regions. Areas can also serve as routing anchors in legs using ``first_activity`` and ``last_activity`` fields, where the area entry point is used for ``first_activity`` routing and the exit point for ``last_activity`` routing.

.. code-block:: yaml

   areas:
     - name: "Survey_Grid_A"
       corners:
         - latitude: 50.0
           longitude: -40.0
         - latitude: 51.0
           longitude: -40.0
         - latitude: 51.0
           longitude: -39.0
         - latitude: 50.0
           longitude: -39.0
       operation_type: "survey"
       action: "bathymetry"       # Optional
       duration: 480.0           # 8 hours
       comment: "Multibeam survey grid"

.. list-table:: Area Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the area
   * - ``corners``
     - List[GeoPoint]
     - *required*
     - Corner points defining the area boundary (minimum 3 points for valid polygon)
   * - ``operation_type``
     - Optional[AreaOperationTypeEnum]
     - ``survey``
     - Type of area operation
   * - ``action``
     - Optional[ActionEnum]
     - None
     - Specific action for the area
   * - ``duration``
     - Optional[float]
     - None
     - Duration in minutes (≥0, typically specified by user)
   * - ``comment``
     - Optional[str]
     - None
     - Human-readable description

.. _area-routing-anchors:

Area Entry and Exit Points
~~~~~~~~~~~~~~~~~~~~~~~~~~~

When areas are used as routing anchors (``first_activity`` or ``last_activity`` in legs), CruisePlan uses entry and exit points for navigation:

- **Entry Point**: First corner coordinate (used for ``first_activity`` routing)
- **Exit Point**: Last corner coordinate (used for ``last_activity`` routing) 
- **Routing Distance**: Calculated from ship position to/from the appropriate entry or exit point

.. code-block:: python

   # Area entry/exit point determination
   entry_point = corners[0]   # First corner as entry point
   exit_point = corners[-1]   # Last corner as exit point

.. code-block:: yaml

   # Example: Using areas as routing waypoints
   areas:
     - name: "Survey_Grid_Alpha"
       corners:
         - latitude: 50.0
           longitude: -40.0
         - latitude: 51.0
           longitude: -40.0
         - latitude: 51.0
           longitude: -39.0
         - latitude: 50.0
           longitude: -39.0
       operation_type: "survey"
       action: "bathymetry"
       duration: 480.0
   
   legs:
     - name: "Survey_Operations"
       first_activity: "STN_001"        # Start at station
       last_activity: "Survey_Grid_Alpha"  # End at area exit point (50.0, -39.0)
       activities: ["STN_001", "Survey_Grid_Alpha"]


**Routing Benefits**:

- **Simplified navigation**: No need to manually calculate area center points
- **Flexible area operations**: Areas work seamlessly with other operation types in leg planning
- **Automatic distance calculations**: Transit times computed using standard distance formulas to/from center point



.. _schedule-organization:

Schedule Organization
=====================

The schedule organization defines how catalog items are executed through legs and clusters using a unified **activities-based architecture**.

.. note::
   **Scheduling Architecture**
   
   CruisePlan uses a streamlined architecture for legs and clusters:
   
   1. **Configuration**: Pydantic validation models (`LegDefinition`, `ClusterDefinition`) validate and parse YAML configuration
   2. **Execution**: The scheduler works directly with configuration objects, applying parameter inheritance and strategy-specific logic
   
   This unified approach allows flexible YAML configuration while enabling runtime parameter inheritance and complex scheduling strategies without additional conversion layers.

.. _leg-definition:

Leg & Cluster Definitions
-------------------------

We have two organisational structures within a cruise.  The "Leg" is the highest level structure, representing a phase of the cruise with distinct operational or geographic characteristics.  Each leg contains a list of **activities** (references to items in the global catalog) that can be executed either in order or as an unordered set.  It can be useful, for instance, if a cruise is separated by two port calls.

A cluster is a sub-division within a leg that groups related operations with specific scheduling strategies.  Like legs, clusters use an **activities list** to reference catalog items.  Clusters are useful for grouping operations that share common characteristics or sub-regions of the cruise area.

.. code-block:: yaml

   legs:
     - name: "Western_Survey"
       description: "Deep water activities in western region"
       strategy: "sequential"
       ordered: true
       activities: ["STN_001", "STN_002", "MOOR_A"]
       clusters:
         - name: "Deep_Water_Cluster"
           strategy: "spatial_interleaved"
           ordered: false
           activities: ["STN_003", "STN_004", "ADCP_Line_A"]

.. code-block:: yaml

   clusters:
     - name: "Deep_Water_Cluster"
       strategy: "spatial_interleaved"
       ordered: false  # Unordered set - optimizer chooses order
       activities: ["STN_003", "STN_004", "STN_005"]
     
     - name: "Mooring_Sequence"
       strategy: "sequential"  
       ordered: true  # Ordered sequence - maintain exact order
       activities: ["MOOR_Deploy", "Trilateration_Survey", "MOOR_Release"]


**Duplicate Activity Support**

Clusters support intentional duplication of activities for repeated operations:

.. code-block:: yaml

   clusters:
     - name: "Calibration_Sequence"
       activities: ["STN_001", "CALIB_STN", "STN_001"]  # Repeat STN_001 for validation
       
     - name: "Deep_Sampling"  
       activities: ["STN_DEEP", "STN_DEEP", "STN_DEEP"]  # Triple sampling for statistics

⚠️ **Duplicate Activity Warning**: When duplicate activities are detected, CruisePlan issues a warning but proceeds with execution:

.. code-block:: text

   ⚠️ Duplicate activity names in cluster: STN_001. These activities will be executed multiple times as specified.

**Waypoint vs Activity Execution**

.. important::
   **Navigation waypoints do NOT execute operations**. Waypoints (``first_activity``, ``last_activity``) are used only for routing calculations. To execute an operation at a waypoint location, you must explicitly include it in the ``activities`` list.

.. code-block:: yaml

   legs:
     - name: "Survey_Leg"
       first_activity: "STN_001"    # Navigation only - NO execution
       last_activity: "STN_005"     # Navigation only - NO execution
       activities: ["STN_002", "STN_003", "STN_004"]  # Only these execute
       
   # To execute operations at waypoint locations:
   legs:
     - name: "Survey_Leg_With_Execution"
       first_activity: "STN_001"    # Navigation waypoint
       last_activity: "STN_005"     # Navigation waypoint  
       activities: ["STN_001", "STN_002", "STN_003", "STN_004", "STN_005"]  # Explicit execution



.. _leg-fields:

Leg & Cluster Fields
~~~~~~~~~~~~~~~~~~~~

.. list-table:: Leg Definition Fields  
   :widths: 15 15 12 15 45
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Leg/Cluster
     - Description
   * - ``name``
     - str
     - *required*
     - Both
     - Unique identifier for the leg or cluster
   * - ``description``
     - str
     - None
     - Both
     - Human-readable description
   * - ``departure_port``
     - str
     - *required*
     - Leg only
     - Starting port for the leg
   * - ``arrival_port``
     - str
     - *required*
     - Leg only
     - Ending port for the leg
   * - ``first_activity``
     - str
     - None
     - Leg only
     - First navigation waypoint (routing only)
   * - ``last_activity``
     - str
     - None
     - Leg only
     - Last navigation waypoint (routing only)
   * - ``strategy``
     - StrategyEnum
     - None (Leg), SEQUENTIAL (Cluster)
     - Both
     - Default scheduling strategy for the leg or cluster
   * - ``ordered``
     - bool
     - None (Leg), True (Cluster)
     - Both
     - Whether activities list should maintain order
   * - ``activities``
     - List[str]
     - []
     - Both
     - List of activity names from the global catalog
   * - ``buffer_time``
     - float
     - None
     - Leg only
     - Contingency time for entire leg in minutes (≥0)
   * - ``vessel_speed``
     - float
     - None
     - Leg only
     - Leg-specific vessel speed override (knots, >0)
   * - ``distance_between_stations``
     - float
     - None
     - Leg only
     - Leg-specific station spacing override (km, >0)
   * - ``turnaround_time``
     - float
     - None
     - Leg only
     - Leg-specific turnaround time override (minutes, ≥0)
   * - ``clusters``
     - List[ClusterDefinition]
     - []
     - Leg only
     - List of operation clusters




.. _processing-priority:

Processing Priority
~~~~~~~~~~~~~~~~~~~

The scheduler processes leg components in this simplified order:

1. **activities**: If defined and non-empty, process these activities (respecting ``ordered`` flag)
2. **clusters**: Process all clusters according to their strategies and ordering

**Note**: Legs must specify either ``activities`` or ``clusters`` (or both). Empty legs are not permitted.


.. _routing-anchor-behavior:

Routing Anchor Behavior (first_activity & last_activity)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``first_activity`` and ``last_activity`` fields serve as **routing anchors only**. These fields can reference any catalog item (points, areas, or line endpoints) but are used exclusively for geographic positioning and route calculations.

**Navigation Only - No Execution**:

By default, ``first_activity`` and ``last_activity`` do **not execute operations**. They provide entry and exit points for routing calculations within the leg. To execute an operation at a waypoint location, you must explicitly include it in the ``activities`` list.

.. code-block:: yaml

   points:
     - name: "ENTRY_CTD"
       operation_type: CTD
       latitude: 44.5
       longitude: -63.5
       
     - name: "EXIT_POINT"  
       operation_type: mooring
       action: deployment
       latitude: 44.7
       longitude: -63.3
   
   legs:
     - name: "Survey_Leg"
       departure_port: "halifax"
       arrival_port: "sydney"
       first_activity: "ENTRY_CTD"      # Navigation only - provides entry coordinates
       last_activity: "EXIT_POINT"      # Navigation only - provides exit coordinates
       activities: ["ENTRY_CTD", "STN_002", "STN_003", "EXIT_POINT"]  # Explicit execution

**To Execute Operations at Waypoints**:

To actually perform operations at waypoint locations, explicitly include them in the ``activities`` list:

.. code-block:: yaml

   legs:
     - name: "Survey_Leg"
       departure_port: "halifax"
       arrival_port: "sydney"
       first_activity: "ENTRY_CTD"      # Navigation waypoint
       last_activity: "EXIT_POINT"      # Navigation waypoint
       activities: [
         "ENTRY_CTD",    # Actually executes CTD operation
         "STN_002", 
         "STN_003", 
         "EXIT_POINT"    # Actually executes mooring deployment
       ]

**Benefits of Explicit Activity Control**:

- **Clear separation**: Navigation routing vs operational execution are explicitly controlled
- **Flexible workflows**: Waypoints can serve purely navigational roles or be explicitly executed
- **Predictable behavior**: Operations only occur when explicitly listed in activities

.. _activity-types:

Activity Types
~~~~~~~~~~~~~~

Activities in ``legs`` and ``clusters`` reference items from the global catalog by name. Any catalog item can be referenced as an activity:

.. list-table:: Supported Activity Types
   :widths: 25 75
   :header-rows: 1

   * - Activity Type
     - Description  
   * - **Station Operations**
     - CTD casts, water sampling, instrument deployments (``points`` catalog with various ``operation_type`` including ``CTD``, ``water_sampling``, ``calibration``)
   * - **Mooring Operations**
     - Mooring deployments, releases, surveys (``points`` catalog with ``operation_type: mooring``)
   * - **Area Surveys**
     - Gridded sampling, multibeam mapping (``areas`` catalog)
   * - **Line Transects**
     - ADCP transects, towed instrument lines (``lines`` catalog with ``operation_type``)

**Examples**:

.. code-block:: yaml

   # Mixed activity types in a single leg
   legs:
     - name: "Multi_Operation_Leg"
       activities: [
         "CTD_Station_001",      # Station operation
         "MOOR_A_Deploy",        # Mooring deployment  
         "Multibeam_Area_1",     # Area survey
         "ADCP_Transect_Line_A"  # Line operation
       ]

.. _strategy-types:

Optimization **Strategy** and (Un-)Ordered
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``ordered`` flag specifies whether a list of activities should be treated as an exact sequence (``ordered: true``) or an unordered set (``ordered: false``).  Generally, if the flag is set to True, the scheduler will respect the specified order, whereas if set to False, the scheduler may optimize the execution order based on the selected ``strategy``.

.. list-table:: Available Scheduling Strategies
   :widths: 25 75
   :header-rows: 1

   * - Strategy
     - Description
   * - ``sequential``
     - Execute activities in defined order (respects ``ordered`` flag)
   * - ``spatial_interleaved``
     - Optimize order based on spatial proximity (ignores ``ordered`` flag)
   * - ``day_night_split``
     - Separate day and night operations based on activity characteristics

.. _ordering-behavior:


The interaction between ``strategy`` and ``ordered`` determines execution order:

.. list-table:: Strategy vs Ordering Behavior
   :widths: 20 20 60
   :header-rows: 1

   * - Strategy
     - Ordered
     - Behavior
   * - ``sequential``
     - True
     - Execute activities in exact list order
   * - ``sequential``  
     - False
     - Execute activities sequentially but allow strategy to reorder
   * - ``spatial_interleaved``
     - True/False
     - Always optimize based on spatial proximity (ignores ordered flag)
   * - ``day_night_split``
     - True
     - Maintain order within day/night groups
   * - ``day_night_split``
     - False  
     - Allow reordering within day/night groups




.. _yaml-structure-notes:

Validation Notes
================

Multiple Definitions
--------------------

**Correct**: Single list with multiple items

.. code-block:: yaml

   clusters:
     - name: "Cluster_A"
       points: [...]
     - name: "Cluster_B" 
       points: [...]

**Incorrect**: Multiple sections (overwrites)

.. code-block:: yaml

   clusters:
     - name: "Cluster_A"
       points: [...]
   
   clusters:  # This overwrites the previous clusters section!
     - name: "Cluster_B"
       points: [...]

.. _validation-behavior:

Validation Behavior
--------------------

The validation system provides three levels of feedback:

**Errors**: Configuration issues that prevent processing
  - Missing required fields
  - Invalid enumeration values
  - Coordinate range consistency violations

**Warnings**: Potential issues that should be reviewed
  - Unusual vessel speeds (<1 kt or >20 kt)
  - Large station spacing (>50 km)
  - Unexpanded CTD sections
  - Placeholder duration values (0.0 or 9999.0)

**Info**: Helpful guidance
  - Suggestions for using enrichment commands
  - Cross-references to relevant documentation

.. _cross-references:

Cross-References
--------------------

For workflow information, see:

- :ref:`Basic Planning Workflow <user_workflow_path_1>` in :doc:`user_workflows`
- :ref:`PANGAEA-Enhanced Workflow <user_workflow_path_2>` in :doc:`user_workflows`
- :ref:`Configuration-Only Workflow <user_workflow_path_3>` in :doc:`user_workflows`

For command-line usage, see:

- :doc:`cli_reference` for complete command documentation
- :ref:`Enrich subcommand <subcommand-enrich>` in :doc:`cli/enrich`
- :ref:`Validate subcommand <subcommand-validate>` in :doc:`cli/validate`

For development and API details, see:

- :doc:`api/cruiseplan.core` for validation models
- :doc:`api/cruiseplan.calculators` for duration and distance calculations
- :doc:`api/cruiseplan.output` for output generation