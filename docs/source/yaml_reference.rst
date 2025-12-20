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
2. **Global Catalog**: Definitions of stations, transits, areas, and sections (reusable components)
3. **Schedule Organization**: Legs and clusters that organize catalog items into execution order

.. tip::
  **Comments in YAML are preserved**: CruisePlan uses ``ruamel.yaml`` which maintains comments when reading and writing files. You can rely on comments remaining in your YAML through the `cruiseplan enrich` command.
  
.. _configuration-structure:

Configuration Structure
-----------------------

.. code-block:: yaml

   # Cruise-wide Metadata and Settings
   cruise_name: "Example Cruise 2025"
   description: "Oceanographic survey of the North Atlantic"
   
   # Global Catalog (Reusable Definitions)
   stations: [...]      # Station definitions → converted to PointOperation objects for scheduling
   transits: [...]      # Transit definitions → converted to LineOperation objects for scheduling
   areas: [...]         # Area operation definitions
   
   # Schedule Organization
   legs: [...]          # Execution phases with clusters/stations/sequences

.. warning::
   **YAML Duplicate Key Limitation**: You cannot have multiple sections with the same name (e.g., multiple ``clusters:`` keys) in a single YAML file as they will overwrite each other. Instead, define multiple clusters as individual items within a single ``clusters:`` list.

.. _coordinate-conventions:


Formats and data conventions
----------------------------

- **Depth Convention**: Positive values represent depth below sea surface (meters)
- **Bathymetry Precision**: Depths from bathymetry are rounded to **nearest whole meter** (though 1 decimal place is acceptable)
- **Manual Depths**: Can be specified to any precision but will be validated as ≥ 0
- **Decimal Degrees**: All coordinates are stored internally as decimal degrees with **5 decimal places precision** (approximately 1.1 meter resolution).
- **Longitude Range Consistency**: The entire cruise configuration must use **either** [-180°, 180°] **or** [0°, 360°] consistently. Mixing ranges will trigger validation errors.

**Input Formats Supported**:

.. code-block:: yaml

   # Option 1: Explicit lat/lon fields
   position:
     latitude: 47.5678
     longitude: -52.1234

   # Option 2: String format (backward compatibility)
   position: "47.5678, -52.1234"


See also :doc:`units_and_defaults` for detailed conventions on units and default values used throughout CruisePlan.

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
     - "2025-01-01"
     - Cruise start date (ISO format)
   * - ``start_time``
     - str
     - "08:00"
     - Cruise start time (HH:MM format)



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
   * - ``calculate_transfer_between_sections``
     - bool
     - *required*
     - Whether to calculate transit times between sections
   * - ``calculate_depth_via_bathymetry``
     - bool
     - *required*
     - Whether to calculate depths using bathymetry data


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
   * - ``station_label_format``
     - str
     - "C{:03d}"
     - Python format string for station labels
   * - ``mooring_label_format``
     - str
     - "M{:02d}"
     - Python format string for mooring labels

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
   * - ``position``
     - GeoPoint
     - *required*
     - Geographic coordinates (see :ref:`coordinate-conventions`)
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
         position: "47.5678, -52.1234"
         timezone: "America/St_Johns"  # Optional, defaults to UTC
       arrival_port:
         name: "Reykjavik"
         position: "64.1355, -21.8954"
         timezone: "Atlantic/Reykjavik"



.. _global-catalog:

Global Catalog Definitions
===========================

The global catalog contains reusable definitions that can be referenced by legs and clusters.

.. note::
   **YAML ↔ Operations Architecture**
   
   CruisePlan uses a two-layer architecture:
   
   1. **YAML Layer**: Pydantic validation models (`StationDefinition`, `TransitDefinition`, `AreaDefinition`) validate and parse YAML configuration
   2. **Operations Layer**: Operational classes (`PointOperation`, `LineOperation`, `AreaOperation`) handle scheduling calculations
   
   During planning, definitions are converted:

   - `StationDefinition` → `PointOperation` (via `from_pydantic()`)
   - `TransitDefinition` → `LineOperation` (via `from_pydantic()`)
   - `AreaDefinition` → `AreaOperation` (via `from_pydantic()`)
   
   This separation allows complex validation rules in YAML while maintaining efficient calculation objects for scheduling.

.. _station-definition:

Station Definition
-------------------

Station definitions specify point operations at fixed locations. During scheduling, they are converted to `PointOperation` objects for duration calculations. Covers CTD casts, water sampling, mooring operations, and calibration activities.

.. code-block:: yaml

   stations:
     - name: "STN_001"
       operation_type: "CTD"
       action: "profile"
       latitude: 50
       longitude: -40
       operation_depth: 500.0  # CTD cast depth in meters
       water_depth: 3000.0     # Seafloor depth in meters (optional: will be enriched from bathymetry)
       duration: 120.0         # Optional: manual override in minutes
       comment: "Deep water station"
       equipment: "SBE 911plus CTD"

.. _station-fields:

Fields, Operations & Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Station Definition Fields
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
   * - ``equipment``
     - str
     - None
     - Equipment required for the operation
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

**Note:** that the operation_depth only affects timing for the CTD profile calculation.  Mooring timing must be specified manually via the duration field.

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
3. **Mooring Operations**: Uses manual duration (required for moorings)
4. **Other Operations**: Falls back to turnaround time if no manual duration specified

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

   stations:
     - name: "Mooring_Deploy" 
       operation_type: "mooring"
       action: "deployment"
       position: "53.0, -40.0"
       duration: 240.0         # 4 hours deployment time
       delay_start: 120.0      # Wait 2h for daylight
       delay_end: 60.0         # Wait 1h for anchor settling
   
   legs:
     - name: "Deep_Water_Survey"
       buffer_time: 480.0      # 8h weather contingency for entire leg
       stations: ["Mooring_Deploy", "STN_001", "STN_002"]

**Buffer Time Types**:

- **delay_start**: Time to wait before operation begins (e.g., daylight requirements, weather windows)
- **delay_end**: Time to wait after operation ends (e.g., equipment settling, safety checks)  
- **buffer_time**: Leg-level contingency time applied at leg completion (e.g., weather delays)

.. _transit-definition:

Transit Definition
------------------

Transit definitions specify movement routes with waypoints. During scheduling, they are converted to `LineOperation` objects for distance and timing calculations. When `operation_type` and `action` are specified, they become scientific line operations (ADCP, bathymetry, etc.).

.. code-block:: yaml

   transits:
     - name: "ADCP_Line_A"
       route:
         - "50.0, -40.0"
         - "51.0, -40.0"
         - "52.0, -40.0"
       operation_type: "underway"  # Optional: makes this a scientific transit
       action: "ADCP"              # Required if operation_type specified
       vessel_speed: 8.0           # Optional: override default speed
       comment: "Deep water ADCP transect"

.. _transit-fields:

Fields, Operations & Actions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Transit Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the transit
   * - ``route``
     - List[GeoPoint]
     - *required*
     - Waypoints defining the transit route
   * - ``operation_type``
     - LineOperationTypeEnum
     - None
     - Type of line operation (``underway``, ``towing``)
   * - ``action``
     - ActionEnum
     - None
     - Specific scientific action (required if operation_type set)
   * - ``vessel_speed``
     - float
     - None
     - Speed override for this transit in knots
   * - ``comment``
     - str
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

CTD sections are a special type of transit that can be expanded into individual stations:

.. code-block:: yaml

   transits:
     - name: "53N_Section"
       distance_between_stations: 25.0  # km
       reversible: true
       stations: []  # Populated during expansion
       operation_type: "CTD"
       action: "section"
       route:
         - "53.0, -40.0"
         - "53.0, -30.0"

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
     - Starting point of the section
   * - ``distance_between_stations``
     - float
     - None
     - Spacing between stations in km
   * - ``reversible``
     - bool
     - True
     - Whether section can be traversed in reverse
   * - ``stations``
     - List[str]
     - []
     - Station names (populated during expansion)



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
  vessel_speed = transit.vessel_speed or config.default_vessel_speed  # knots
  duration_hours = route_distance_nm / vessel_speed
  duration_minutes = duration_hours * 60

**Key Points:**

- **Route Distance**: Sum of haversine distances between all consecutive waypoints in the route
- **Vessel Speed**: Uses transit-specific `vessel_speed` if specified, otherwise falls back to `config.default_vessel_speed`
- **Scientific vs Navigation**: When `operation_type` and `action` are specified, the transit becomes a scientific line operation (ADCP, bathymetry) but uses the same duration calculation
- **Architectural Consistency**: Like `PointOperation` and `AreaOperation`, the `LineOperation` calculates its own duration

**CTD Section Expansion**: When CTD sections are expanded using `cruiseplan enrich --expand-sections`, the resulting stations are treated as regular CTD stations with standard CTD duration calculations based on depth, descent/ascent rates, and turnaround time.

**Inter-operation Transits**: The scheduler automatically calculates and adds transit time between operations when they are not geographically adjacent (> 0.1 nautical miles apart).


.. _area-definition:

Area Definition
----------------

Areas represent operations covering defined geographic regions. Areas can also serve as routing anchors in legs using ``first_waypoint`` and ``last_waypoint`` fields, where the area center point is used for navigation calculations.

.. code-block:: yaml

   areas:
     - name: "Survey_Grid_A"
       corners:
         - "50.0, -40.0"
         - "51.0, -40.0"
         - "51.0, -39.0"
         - "50.0, -39.0"
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
     - AreaOperationTypeEnum
     - ``survey``
     - Type of area operation
   * - ``action``
     - ActionEnum
     - None
     - Specific action for the area
   * - ``duration``
     - float
     - *required*
     - Duration in minutes (≥0, must be specified by user)
   * - ``comment``
     - str
     - None
     - Human-readable description

.. _area-routing-anchors:

Area Center Point Calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When areas are used as routing anchors (``first_waypoint`` or ``last_waypoint`` in legs), CruisePlan calculates the center point of the area for navigation purposes:

- **Center Point**: Calculated as the average of all corner coordinates
- **Routing Distance**: Calculated from ship position to/from the area center point
- **Entry/Exit Points**: The scheduler treats the center point as both entry and exit point for routing calculations

.. code-block:: python

   # Area center point calculation
   center_lat = sum(corner.latitude for corner in corners) / len(corners)
   center_lon = sum(corner.longitude for corner in corners) / len(corners)

.. code-block:: yaml

   # Example: Using areas as routing waypoints
   areas:
     - name: "Survey_Grid_Alpha"
       corners:
         - "50.0, -40.0"
         - "51.0, -40.0" 
         - "51.0, -39.0"
         - "50.0, -39.0"
       operation_type: "survey"
       action: "bathymetry"
       duration: 480.0
   
   legs:
     - name: "Survey_Operations"
       first_waypoint: "STN_001"        # Start at station
       last_waypoint: "Survey_Grid_Alpha"  # End at area center point
       activities: ["STN_001", "Survey_Grid_Alpha"]

**Advanced Routing Examples**:

.. code-block:: yaml

   areas:
     - name: "Northern_Grid"
       corners: ["60.0, -50.0", "62.0, -50.0", "62.0, -48.0", "60.0, -48.0"]
       operation_type: "survey"
       action: "bathymetry"
       duration: 240.0  # 4-hour survey
       
     - name: "Southern_Box"
       corners: ["58.0, -52.0", "59.0, -52.0", "59.0, -51.0", "58.0, -51.0"]
       operation_type: "survey"
       action: "mapping"
       duration: 180.0  # 3-hour mapping
   
   stations:
     - name: "CTD_01"
       latitude: 61.0
       longitude: -49.0
       operation_type: "CTD"
       action: "profile"
   
   legs:
     - name: "Survey_Campaign"
       first_waypoint: "CTD_01"         # Start at station coordinates
       last_waypoint: "Northern_Grid"   # End at area center (61.0°N, 49.0°W)
       activities: ["CTD_01", "Northern_Grid"]
       
     - name: "Mapping_Phase"
       first_waypoint: "Northern_Grid"  # Start at area center from previous leg  
       last_waypoint: "Southern_Box"    # End at area center (58.5°N, 51.5°W)
       activities: ["Southern_Box"]

**Center Point Calculations for Examples**:

- ``Northern_Grid`` center: (60+62+62+60)/4 = 61.0°N, (-50-50-48-48)/4 = -49.0°W
- ``Southern_Box`` center: (58+59+59+58)/4 = 58.5°N, (-52-52-51-51)/4 = -51.5°W

**Routing Benefits**:

- **Simplified navigation**: No need to manually calculate area center points
- **Flexible area operations**: Areas work seamlessly with other operation types in leg planning
- **Automatic distance calculations**: Transit times computed using standard distance formulas to/from center point



.. _schedule-organization:

Schedule Organization
=====================

The schedule organization defines how catalog items are executed through legs and clusters using a unified **activities-based architecture**.

.. note::
   **YAML ↔ Scheduling Architecture**
   
   CruisePlan uses a two-layer architecture for legs and clusters:
   
   1. **YAML Layer**: Pydantic validation models (`LegDefinition`, `ClusterDefinition`) validate and parse YAML configuration
   2. **Scheduling Layer**: Runtime classes (`Leg`, `Cluster`) handle execution with parameter inheritance
   
   During scheduling, definitions are converted:

   - `LegDefinition` → `Leg` (with inheritance of cruise-level parameters like ``vessel_speed``)
   - `ClusterDefinition` → `Cluster` (with strategy-specific ordering logic)
   
   This separation allows flexible YAML configuration while enabling runtime parameter inheritance and complex scheduling strategies.

.. _leg-definition:

Leg & Cluster Definitions
-------------------------

We have two organisational structures within a cruise.  The "Leg" is the highest level structure, representing a phase of the cruise with distinct operational or geographic characteristics.  Each leg contains a list of **activities** (references to items in the global catalog) that can be executed either in order or as an unordered set.  It can be useful, for instance, if a cruise is separated by two port calls or for main user and secondary user operations.

A cluster is a sub-division within a leg that groups related operations with specific scheduling strategies.  Like legs, clusters use an **activities list** to reference catalog items.  Clusters are useful for grouping operations that share common characteristics, such as spatial interleaving or specific operational constraints.

.. code-block:: yaml

   legs:
     - name: "Western_Survey"
       description: "Deep water stations in western region"
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
   * - ``strategy``
     - StrategyEnum
     - None
     - Both
     - Default scheduling strategy for the leg or cluster
   * - ``ordered``
     - bool
     - None
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
   * - ``clusters``
     - List[ClusterDefinition]
     - []
     - Leg only
     - List of operation clusters

.. _planned-leg-enhancements:

Planned Leg Enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
   **PLANNED FEATURES**: The following leg capabilities are planned for future implementation and will extend the current activities-based architecture.

**Inheritable Cruise Parameters & Boundary Management**
   Legs will be able to override cruise-level operational parameters for specific requirements:

   .. list-table:: Planned Inheritable Parameter Fields & Waypoint Definition
      :widths: 15 15 12 57
      :header-rows: 1

      * - Field
        - Type  
        - Default
        - Description
      * - ``vessel_speed``
        - float
        - None
        - Leg-specific vessel speed override (knots, must be >0)
      * - ``distance_between_stations``
        - float
        - None  
        - Leg-specific station spacing override (nautical miles, must be >0)
      * - ``turnaround_time``
        - float
        - None
        - Leg-specific turnaround time override (minutes, must be ≥0)
      * - ``first_waypoint``
        - str
        - None
        - Entry point for this leg (station, area, or transit endpoint; must exist in catalog). **Executes the defined activity by default**. For areas, routing uses calculated center point from corner coordinates. To use as waypoint only, define with ``duration: 0``. Formerly ``first_station``.
      * - ``last_waypoint``
        - str
        - None
        - Exit point for this leg (station, area, or transit endpoint; must exist in catalog). **Executes the defined activity by default**. For areas, routing uses calculated center point from corner coordinates. To use as waypoint only, define with ``duration: 0``. Formerly ``last_station``.

**Planned Usage Example**:

.. code-block:: yaml

   legs:
     - name: "Transit_Leg"
       vessel_speed: 12.0              # Fast transit speed
       turnaround_time: 15.0           # Quick turnarounds  
       first_waypoint: "PORT_START"    # Clear entry point
       last_waypoint: "SURVEY_ENTRY"   # Hand-off to next leg
       activities: ["PORT_START", "WAYPOINT_1", "SURVEY_ENTRY"]
       
     - name: "Survey_Leg"
       vessel_speed: 8.0                     # Slower survey speed
       distance_between_stations: 5.0        # Close station spacing
       turnaround_time: 45.0                 # Science operations
       first_waypoint: "SURVEY_ENTRY"        # Pick up from transit
       last_waypoint: "MAPPING_AREA"         # Define survey boundary (area center point)
       activities: ["CTD_001", "CTD_002", "MAPPING_AREA"]

**Benefits**:

- **Parameter inheritance**: Legs inherit cruise defaults but override for specific operational needs
- **Boundary management**: Clear routing between legs with defined entry/exit points  
- **Multi-leg support**: Enhanced routing logic for complex multi-leg cruises
- **Operational flexibility**: Different speeds/timing for transit vs survey legs

.. note::
   **Current Implementation**: The runtime `Leg` class already supports parameter inheritance through ``get_effective_speed()`` and ``get_effective_spacing()`` methods. These planned enhancements will extend this capability to the YAML configuration layer.



.. _processing-priority:

Processing Priority
~~~~~~~~~~~~~~~~~~~

The scheduler processes leg components in this simplified order:

1. **activities**: If defined and non-empty, process these activities (respecting ``ordered`` flag)
2. **clusters**: Process all clusters according to their strategies and ordering

**Note**: Legs must specify either ``activities`` or ``clusters`` (or both). Empty legs are not permitted.


.. _routing-anchor-behavior:

Routing Anchor Behavior (first_waypoint & last_waypoint)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``first_waypoint`` and ``last_waypoint`` fields (formerly ``first_station`` and ``last_station``) serve dual purposes as routing anchors and operational activities. These fields can reference any catalog item: stations, areas, or transit endpoints.

**Default Behavior - Execute Activities**:

By default, ``first_waypoint`` and ``last_waypoint`` **execute their defined activities** (CTD casts, mooring deployments, area surveys, etc.) in addition to serving as routing waypoints. This provides a complete operational workflow where legs begin and end with actual scientific operations.

.. code-block:: yaml

   stations:
     - name: "ENTRY_CTD"
       operation_type: CTD
       # No explicit duration → normal CTD operation will be performed
       
     - name: "EXIT_MOORING"  
       operation_type: mooring
       action: deployment
       # No explicit duration → full mooring deployment will be performed
   
   areas:
     - name: "SURVEY_AREA_A"
       operation_type: survey
       action: bathymetry
       duration: 360.0  # 6 hour survey
       corners: ["50.0, -40.0", "51.0, -40.0", "51.0, -39.0", "50.0, -39.0"]
   
   legs:
     - name: "Survey_Leg"
       first_waypoint: "ENTRY_CTD"      # Executes CTD cast at leg start
       last_waypoint: "SURVEY_AREA_A"   # Executes area survey at leg end (routed to center point)
       clusters: [...]

**Waypoint-Only Behavior - Zero Duration**:

To use ``first_waypoint`` and ``last_waypoint`` as routing waypoints only (without executing activities), define them with ``duration: 0``:

.. code-block:: yaml

   stations:
     - name: "WAYPOINT_START"
       operation_type: CTD  
       duration: 0  # ← Zero duration = waypoint only, no CTD operation
       
     - name: "WAYPOINT_END"
       operation_type: mooring
       duration: 0  # ← Zero duration = waypoint only, no mooring operation
   
   areas:
     - name: "WAYPOINT_AREA"
       operation_type: survey
       duration: 0  # ← Zero duration = navigation waypoint only, no area survey
       corners: ["52.0, -35.0", "53.0, -35.0", "53.0, -34.0", "52.0, -34.0"]
   
   legs:
     - name: "Transit_Leg"
       first_waypoint: "WAYPOINT_START"  # Navigation waypoint only
       last_waypoint: "WAYPOINT_AREA"    # Navigation to area center point only

**Cluster Integration**:

It is completely normal for ``first_waypoint`` and ``last_waypoint`` to also appear in cluster activities. They will execute once as routing anchors and may execute additional times if included in cluster activities:

.. code-block:: yaml

   legs:
     - name: "Survey_Leg"
       first_waypoint: "STN_001"    # Executes CTD cast as routing anchor
       last_waypoint: "AREA_001"    # Executes area survey as routing anchor (routed to center)
       clusters:
         - name: "Repeat_Survey"
           activities: ["STN_001", "STN_002", "AREA_001", "STN_001"]  # STN_001 and AREA_001 executed again in cluster

**Benefits of Default Activity Execution**:

- **Complete workflow coverage**: Legs naturally begin and end with scientific operations
- **Natural leg boundaries**: Clear operational transitions between legs
- **Flexibility**: Zero-duration override available when waypoint-only behavior is needed

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
     - CTD casts, water sampling, instrument deployments (``stations`` catalog with various ``operation_type`` including ``CTD``, ``water_sampling``, ``calibration``)
   * - **Mooring Operations**
     - Mooring deployments, releases, surveys (``stations`` catalog with ``operation_type: mooring``)
   * - **Area Surveys**
     - Gridded sampling, multibeam mapping (``areas`` catalog)
   * - **Line Transects**
     - ADCP transects, towed instrument lines (``transits`` catalog with ``operation_type``)

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

.. _deprecated-fields:

Deprecated Fields
~~~~~~~~~~~~~~~~~

The following fields are **deprecated** and will be removed in future versions:

.. list-table:: Deprecated Leg/Cluster Fields
   :widths: 25 75
   :header-rows: 1

   * - Deprecated Field
     - Replacement
   * - ``stations``
     - Use ``activities`` with station names
   * - ``sequence``
     - Use ``activities`` with ``ordered: true``
   * - ``sections``
     - Expand sections to individual stations first with ``cruiseplan enrich --expand-sections``
   * - ``generate_transect``
     - Create explicit stations in catalog and reference via ``activities``

**Migration Example**:

.. code-block:: yaml

   # OLD (deprecated)
   legs:
     - name: "Survey_Leg"
       sequence: ["STN_001", "STN_002", "STN_003"]
       stations: ["STN_004", "STN_005"]
   
   # NEW (recommended)
   legs:  
     - name: "Survey_Leg"
       ordered: true
       activities: ["STN_001", "STN_002", "STN_003", "STN_004", "STN_005"]

.. _yaml-structure-notes:

Validation Notes
================

Multiple Definitions
--------------------

**Correct**: Single list with multiple items

.. code-block:: yaml

   clusters:
     - name: "Cluster_A"
       stations: [...]
     - name: "Cluster_B" 
       stations: [...]

**Incorrect**: Multiple sections (overwrites)

.. code-block:: yaml

   clusters:
     - name: "Cluster_A"
       stations: [...]
   
   clusters:  # This overwrites the previous clusters section!
     - name: "Cluster_B"
       stations: [...]

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