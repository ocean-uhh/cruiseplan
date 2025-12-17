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

CruisePlan uses YAML configuration files to define oceanographic cruises. The configuration consists of two main parts:

1. **Global Catalog**: Definitions of stations, transits, areas, and sections (reusable components)
2. **Schedule Organization**: Legs and clusters that organize catalog items into execution order

.. _configuration-structure:

Configuration Structure
=======================

.. code-block:: yaml

   # Root Configuration
   cruise_name: "Example Cruise 2025"
   description: "Oceanographic survey of the North Atlantic"
   
   # Global Catalog (Reusable Definitions)
   stations: [...]      # Point operations
   transits: [...]      # Line operations  
   areas: [...]         # Area operations
   sections: [...]      # CTD section templates (for expansion)
   
   # Schedule Organization
   legs: [...]          # Execution phases with clusters/stations/sequences

.. warning::
   **YAML Duplicate Key Limitation**: You cannot have multiple sections with the same name (e.g., multiple ``clusters:`` keys) in a single YAML file as they will overwrite each other. Instead, define multiple clusters as individual items within a single ``clusters:`` list.

.. _coordinate-conventions:

Coordinate and Data Conventions
===============================

Coordinate Formats
------------------

**Decimal Degrees**: All coordinates are stored internally as decimal degrees with **5 decimal places precision** (approximately 1.1 meter resolution).

**Input Formats Supported**:

.. code-block:: yaml

   # Option 1: Explicit lat/lon fields
   position:
     latitude: 47.5678
     longitude: -52.1234

   # Option 2: String format (backward compatibility)
   position: "47.5678, -52.1234"

**Longitude Range Consistency**: The entire cruise configuration must use **either** [-180°, 180°] **or** [0°, 360°] consistently. Mixing ranges will trigger validation errors.

Depth and Bathymetry
---------------------

- **Depth Convention**: Positive values represent depth below sea surface (meters)
- **Bathymetry Precision**: Depths from bathymetry are rounded to **nearest whole meter** (though 1 decimal place is acceptable)
- **Manual Depths**: Can be specified to any precision but will be validated as ≥ 0

.. _root-configuration:

Root Configuration Fields
=========================

.. _cruise-metadata:

Cruise Metadata
---------------

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

.. _operational-parameters:

Operational Parameters
----------------------

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

.. _ctd-parameters:

CTD Operation Parameters
------------------------

.. list-table:: CTD-Specific Settings
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``ctd_descent_rate``
     - float
     - 1.0
     - CTD descent rate in m/s (0.5-2.0)
   * - ``ctd_ascent_rate``
     - float
     - 1.0
     - CTD ascent rate in m/s (0.5-2.0)

.. _day-window:

Day Window Configuration
------------------------

.. list-table:: Operational Time Windows
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

.. _calculation-options:

Calculation Options
-------------------

.. list-table:: Automated Calculation Settings
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``calculate_transfer_between_sections``
     - bool
     - *required*
     - Whether to calculate transit times between sections
   * - ``calculate_depth_via_bathymetry``
     - bool
     - *required*
     - Whether to calculate depths using bathymetry data

.. _timing-schedule:

Timing and Schedule
-------------------

.. list-table:: Schedule Configuration
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``start_date``
     - str
     - "2025-01-01"
     - Cruise start date (ISO format)
   * - ``start_time``
     - str
     - "08:00"
     - Cruise start time (HH:MM format)
   * - ``station_label_format``
     - str
     - "C{:03d}"
     - Python format string for station labels
   * - ``mooring_label_format``
     - str
     - "M{:02d}"
     - Python format string for mooring labels

.. _ports-anchors:

Ports and Anchors
-----------------

.. list-table:: Departure and Arrival Points
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``departure_port``
     - PortDefinition
     - *required*
     - Port where the cruise begins
   * - ``arrival_port``
     - PortDefinition
     - *required*
     - Port where the cruise ends
   * - ``first_station``
     - str
     - *required*
     - Name of the first station in working area
   * - ``last_station``
     - str
     - *required*
     - Name of the last station in working area

.. _port-definition:

Port Definition
===============

.. code-block:: yaml

   departure_port:
     name: "St. Johns"
     position: "47.5678, -52.1234"
     timezone: "America/St_Johns"  # Optional, defaults to UTC

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

.. _global-catalog:

Global Catalog Definitions
===========================

The global catalog contains reusable definitions that can be referenced by legs and clusters.

.. _station-definition:

Station Definition (Point Operations)
-------------------------------------

Stations represent point operations like CTD casts, water sampling, and mooring operations.

.. code-block:: yaml

   stations:
     - name: "STN_001"
       operation_type: "CTD"
       action: "profile"
       position: "50.0, -40.0"
       depth: 3000.0           # Optional: water depth in meters
       duration: 120.0         # Optional: manual override in minutes
       comment: "Deep water station"
       equipment: "SBE 911plus CTD"

.. _station-fields:

Station Fields
~~~~~~~~~~~~~~

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
   * - ``position``
     - GeoPoint
     - *required*
     - Geographic coordinates (see :ref:`coordinate-conventions`)
   * - ``depth``
     - float
     - None
     - Water depth in meters (≥0, positive = below surface)
   * - ``duration``
     - float
     - None
     - Manual duration override in minutes (≥0)
   * - ``delay_start``
     - float
     - None
     - Time to wait before operation begins in minutes (≥0)
   * - ``delay_end``
     - float
     - None
     - Time to wait after operation ends in minutes (≥0)
   * - ``comment``
     - str
     - None
     - Human-readable comment or description
   * - ``equipment``
     - str
     - None
     - Equipment required for the operation

.. _operation-types:

Operation Types
~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~

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

Duration Calculation Behavior
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Enhanced Buffer Time Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The enhanced timing system provides multiple levels of buffer time control for realistic operational scenarios:

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

Transit Definition (Line Operations)
------------------------------------

Transits represent line operations like ADCP surveys, bathymetry mapping, and towed instruments.

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

Transit Fields
~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~

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

CTD Section Special Case
~~~~~~~~~~~~~~~~~~~~~~~~

CTD sections are a special type of transit that can be expanded into individual stations:

.. code-block:: yaml

   transits:
     - name: "53N_CTD_Section"
       operation_type: "CTD"      # Special: CTD on transit
       action: "section"          # Special: section action
       route:
         - "53.0, -40.0"
         - "53.0, -30.0"
       comment: "CTD section for expansion"

**Expansion Behavior**:

- Use ``cruiseplan enrich --expand-sections`` to convert CTD sections into individual station sequences
- Each station gets coordinates interpolated along the route
- Depths are calculated from bathymetry data
- Station spacing uses ``default_distance_between_stations`` or section-specific spacing

.. warning::
   **Validation Warning**: The validate command will warn about unexpanded CTD sections and recommend using the enrich command with ``--expand-sections``.

.. _area-definition:

Area Definition (Area Operations)
---------------------------------

Areas represent operations covering defined geographic regions.

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
     - Corner points defining the area boundary
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
     - None
     - Duration in minutes (≥0)
   * - ``comment``
     - str
     - None
     - Human-readable description

.. _section-definition:

Section Definition (CTD Section Templates)
-------------------------------------------

Sections define CTD line templates that can be expanded into individual stations.

.. code-block:: yaml

   sections:
     - name: "53N_Section"
       start: "53.0, -40.0"
       end: "53.0, -30.0"
       distance_between_stations: 25.0  # km
       reversible: true
       stations: []  # Populated during expansion

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
   * - ``start``
     - GeoPoint
     - *required*
     - Starting point of the section
   * - ``end``
     - GeoPoint
     - *required*
     - Ending point of the section
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

.. _schedule-organization:

Schedule Organization
=====================

The schedule organization defines how catalog items are executed through legs and clusters.

.. _leg-definition:

Leg Definition
--------------

Legs represent phases of the cruise with distinct operational or geographic characteristics.

.. code-block:: yaml

   legs:
     - name: "Western_Survey"
       description: "Deep water stations in western region"
       strategy: "sequential"
       stations: ["STN_001", "STN_002"]
       clusters:
         - name: "Mooring_Cluster"
           strategy: "spatial_interleaved"
           stations: ["MOOR_A", "MOOR_B"]
       sequence: ["STN_001", "Mooring_Cluster", "STN_002"]

.. _leg-fields:

Leg Fields
~~~~~~~~~~

.. list-table:: Leg Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the leg
   * - ``description``
     - str
     - None
     - Human-readable description
   * - ``strategy``
     - StrategyEnum
     - None
     - Default scheduling strategy for the leg
   * - ``ordered``
     - bool
     - None
     - Whether operations should maintain order
   * - ``buffer_time``
     - float
     - None
     - Contingency time for entire leg in minutes (≥0)
   * - ``stations``
     - List[str]
     - []
     - List of station names in this leg
   * - ``clusters``
     - List[ClusterDefinition]
     - []
     - List of operation clusters
   * - ``sections``
     - List[SectionDefinition]
     - []
     - List of sections in this leg
   * - ``sequence``
     - List[str]
     - []
     - Ordered execution sequence

.. _processing-priority:

Processing Priority
~~~~~~~~~~~~~~~~~~~

The scheduler processes leg components in this order:

1. **sequence**: If defined and non-empty, use this exact order
2. **clusters**: Process all clusters according to their strategies
3. **stations**: Process individual stations sequentially
4. **sections**: Process sections (if not expanded to stations)

.. _cluster-definition:

Cluster Definition
------------------

Clusters group operations with specific scheduling strategies.

.. code-block:: yaml

   clusters:
     - name: "Deep_Water_Cluster"
       strategy: "spatial_interleaved"
       ordered: true
       stations: ["STN_003", "STN_004", "STN_005"]
       sequence: ["STN_003", "ADCP_Line_A", "STN_004"]  # Optional: explicit order

.. _cluster-fields:

Cluster Fields
~~~~~~~~~~~~~~

.. list-table:: Cluster Definition Fields
   :widths: 20 15 15 50
   :header-rows: 1

   * - Field
     - Type
     - Default
     - Description
   * - ``name``
     - str
     - *required*
     - Unique identifier for the cluster
   * - ``strategy``
     - StrategyEnum
     - ``sequential``
     - Scheduling strategy for operations
   * - ``ordered``
     - bool
     - True
     - Whether operations should maintain order
   * - ``sequence``
     - List[Union[str, StationDefinition]]
     - None
     - Ordered sequence of operations
   * - ``stations``
     - List[Union[str, StationDefinition]]
     - []
     - List of stations in the cluster
   * - ``generate_transect``
     - GenerateTransect
     - None
     - Parameters for generating station transects
   * - ``activities``
     - List[dict]
     - []
     - List of activity definitions

.. _strategy-types:

Strategy Types
~~~~~~~~~~~~~~

.. list-table:: Available Scheduling Strategies
   :widths: 25 75
   :header-rows: 1

   * - Strategy
     - Description
   * - ``sequential``
     - Execute operations in defined order
   * - ``spatial_interleaved``
     - Optimize order based on spatial proximity
   * - ``day_night_split``
     - Separate day and night operations

.. _yaml-structure-notes:

YAML Structure Notes
====================

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
===================

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
================

For workflow information, see:

- :ref:`Basic Planning Workflow <basic-planning-workflow>` in :doc:`user_workflows`
- :ref:`PANGAEA-Enhanced Workflow <pangaea-enhanced-workflow>` in :doc:`user_workflows`
- :ref:`Configuration-Only Workflow <configuration-only-workflow>` in :doc:`user_workflows`

For command-line usage, see:

- :doc:`cli_reference` for complete command documentation
- :ref:`Enrichment Commands <enrichment-commands>` in :doc:`cli_reference`
- :ref:`Validation Commands <validation-commands>` in :doc:`cli_reference`

For development and API details, see:

- :doc:`api/cruiseplan.core` for validation models
- :doc:`api/cruiseplan.calculators` for duration and distance calculations
- :doc:`api/cruiseplan.output` for output generation