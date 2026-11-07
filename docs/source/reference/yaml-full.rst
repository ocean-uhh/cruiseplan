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
   ports: [...]         # Port definitions (optional; built-in ports such as
                        # port_reykjavik can be referenced without defining them)
   points: [...]        # Point operations
   lines: [...]         # Line operations  
   areas: [...]         # Area operations
   
   # 3. Schedule organization
   legs: [...]          # Execution phases

Coordinate Conventions
======================

- **Latitude**: -90.0 to 90.0 decimal degrees (negative = South)
- **Longitude**: -180.0 to 180.0 (negative = West) or 0.0 to 360.0 decimal degrees
- **Depth**: meters below sea level (positive values)
- **Distance**: kilometers
- **Duration**: minutes

Units Reference
===============

Every numeric key carries its unit in its name. Units are fixed and not
configurable. Keys written before 0.6.0 without the unit (``duration``,
``water_depth``, ...) are still read, with a warning, until 0.7.0; see
:doc:`../migrating_0_6_0`.

.. list-table::
   :header-rows: 1
   :widths: 34 14 52

   * - Key
     - Unit
     - Notes
   * - ``latitude``, ``longitude``
     - decimal degrees
     - WGS-84; negative = South / West
   * - ``water_depth_m``, ``operation_depth_m``
     - m
     - Positive below sea level (e.g., ``3500`` = 3500 m); ``-9999`` is the
       fill value written by ``enrich`` where no depth was found
   * - ``max_depth`` (line)
     - m
     - Cast depth for stations expanded from a CTD section
   * - ``distance_between_stations_km`` (leg, line)
     - km
     - Along-track spacing when expanding CTD sections
   * - ``default_distance_between_stations_km`` (cruise)
     - km
     - Default station spacing for section expansion
   * - ``default_vessel_speed_kt`` (cruise), ``vessel_speed_kt`` (leg, line)
     - knots
     - Transit speed; a line's own speed applies along the line
   * - ``ctd_descent_rate_m_s``, ``ctd_ascent_rate_m_s``
     - m/s
     - Used to compute CTD cast duration from depth
   * - ``duration_minutes`` (point, area, port)
     - minutes
     - Operation time; replaces the depth-based CTD time
   * - ``turnaround_time_minutes`` (cruise, leg)
     - minutes
     - Added to each depth-based CTD cast; a leg value replaces the cruise
       value for that leg's casts. Not a gap between other operations
   * - ``delay_start_minutes`` (point, port)
     - minutes
     - Changes the actual duration of the previous operation in the same
       leg (the nearest earlier one that is not a transit or buffer; the
       departure port when there is none): positive, it ran long; negative,
       it ended early. The transit between them keeps its length and moves
       in time. The duration never goes below zero; what a negative value
       cannot take off is dropped with a warning (at the start of a leg, the
       warning says how to start the leg earlier). ``planned_duration_minutes``
       in the outputs keeps the plan
   * - ``transit_minutes`` (point, port, line, area)
     - minutes
     - Actual duration of the transit into this operation, replacing
       distance / speed. Distance and positions are unchanged; the transit's
       ``planned_duration_minutes`` keeps the computed time, and the vessel
       speed shown for it in the outputs is distance / ``transit_minutes``.
       Ignored, with a warning, when there is no transit into the operation
   * - ``delay_start_minutes`` (leg)
     - minutes
     - Wait before the leg departs (e.g. port clearance); not negative
   * - ``buffer_time_minutes`` (leg)
     - minutes
     - Contingency block, applied once per leg: a stationary record at the
       position where the last operation ends, after it and before the
       transit to the arrival port
   * - ``day_start_hour``, ``day_end_hour``
     - hour (0-23)
     - Working-day window
   * - ``tolerance`` (validate)
     - percent
     - Allowable depth difference between planned and bathymetric depth

Use ``transit_minutes`` when a transit was faster or slower than planned; use
``delay_start_minutes`` when the previous operation ran long or ended early.

``delay_end`` is no longer read (it never changed the schedule): use
``delay_start_minutes`` on the next operation, ``buffer_time_minutes`` on the
leg, or a longer ``duration_minutes``. A key no model knows is reported with
a warning (one per key per file) and is rejected in the release after 0.6.0.

Cruise Metadata
===============

Root-level cruise configuration fields:

.. code-block:: yaml

   cruise_name: "North Atlantic Survey 2025"
   description: "Overflow monitoring survey"        # Optional free-text description
   start_date: "2025-06-15"                         # ISO format YYYY-MM-DD
   start_time: "08:00"                              # Cruise start time (default: "08:00")
   day_start_hour: 8                                # Start of working day (0-23); default: 8
   day_end_hour: 20                                 # End of working day (0-23); default: 20
   default_vessel_speed_kt: 10.0                       # Transit speed in knots; default: 10.0
   default_distance_between_stations_km: 15.0          # Station spacing in km; default: 15.0
   turnaround_time_minutes: 30                      # Added to each CTD cast in minutes; default: 30
   ctd_descent_rate_m_s: 1.0                            # CTD descent speed in m/s; default: 1.0
   ctd_ascent_rate_m_s: 1.0                             # CTD ascent speed in m/s; default: 1.0

Ports
-----

Ports are used as departure and arrival points for legs. They can be defined inline
or as named entries in a global ``ports`` catalog and referenced by name:

.. code-block:: yaml

   # Named port catalog (referenced by name in legs)
   ports:
     - name: "port_reykjavik"
       latitude: 64.15
       longitude: -21.95
       display_name: "Reykjavik"
     - name: "port_bergen"
       latitude: 60.39
       longitude: 5.32
       display_name: "Bergen"

   # For single-leg cruises, departure/arrival may be set at cruise level
   departure_port: port_reykjavik     # Named reference or inline PointDefinition
   arrival_port: port_bergen          # Required for single-leg cruises; forbidden for multi-leg

For multi-leg cruises, ``departure_port`` and ``arrival_port`` are set on each leg
(see :ref:`schedule-organization` below).

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
       water_depth_m: 3500            # Water depth at seafloor in metres (auto-filled by 'process')
       operation_depth_m: 2000        # Target cast depth in metres (default: full water column)
       duration_minutes: 45                 # Override cast time in minutes (suppresses depth-based calculation)
       delay_start_minutes: 60      # The previous operation took 60 min longer
       transit_minutes: 150         # The transit into this station took 150 min
       equipment: "SBE911plus"      # Equipment note (informational only, not used in scheduling)
       comment: "Deep water station"

Coordinate Formats
------------------

Coordinates may be given in decimal degrees (preferred) or degrees decimal minutes:

.. code-block:: yaml

   # Decimal degrees (preferred)
   points:
     - name: "STN_001"
       latitude: 60.2440
       longitude: -31.3177

   # Degrees decimal minutes (DDM) — both formats accepted
   points:
     - name: "STN_001"
       latitude_decmin: "60 14.640 N"
       longitude_decmin: "031 19.062 W"

Both formats produce identical internal representations. ``latitude`` and
``longitude_decmin`` cannot be mixed within the same definition.

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
       vessel_speed_kt: 8.0               # Speed during transect in knots
       distance_between_stations_km: 10.0 # Station spacing for CTD section expansion (km)
       max_depth: 2000                 # Maximum cast depth for expanded stations (metres)

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
       duration_minutes: 120               # Total survey time in minutes
       comment: "High-priority mapping area"

.. _schedule-organization:

Schedule Organization
=====================

Legs organize activities into cruise phases:

Basic Leg
---------

.. code-block:: yaml

   legs:
     - name: "leg1"
       departure_port: port_reykjavik   # Required
       arrival_port: port_bergen        # Required
       activities: ["STN_001", "STN_002", "transect_A"]

Advanced Leg Options
--------------------

.. code-block:: yaml

   legs:
     - name: "leg1"
       description: "Main science leg"
       departure_port: port_reykjavik     # Required: departure port name or inline definition
       arrival_port: port_bergen          # Required: arrival port name or inline definition
       first_activity: STN_001            # Routing hint: first activity (not executed separately)
       last_activity: transect_A          # Routing hint: last activity (not executed separately)
       activities: ["STN_001", "STN_002", "transect_A"]

       # Timing
       delay_start_minutes: 120     # Hold at departure port in minutes (e.g., port clearance)
       buffer_time_minutes: 60      # Contingency block after the last operation (minutes)

       # Ordering
       ordered: true                # Whether activities must run in listed order

       # Leg-level parameter overrides (cascade from cruise defaults)
       vessel_speed_kt: 12.0
       turnaround_time_minutes: 20
       distance_between_stations_km: 25.0

Clusters
--------

Group activities within legs for advanced scheduling:

.. code-block:: yaml

   legs:
     - name: "leg1"
       clusters:
         - name: "northern_stations"
           activities: ["CTD_001", "CTD_002"]
           strategy: "sequential"           # Only implemented strategy
         - name: "southern_stations"
           activities: ["CTD_003", "CTD_004"]
           strategy: "sequential"

Operation Types
===============

How duration is determined when ``duration_minutes`` is not set. The 999-hour fill
is large on purpose so it cannot be overlooked: the schedule log warns for each
operation that uses it, the NetCDF schedule sets ``duration_fill_flag = 1``,
and the CSV, HTML and TeX outputs mark it.

.. list-table::
   :header-rows: 1
   :widths: 25 25 50

   * - **Type**
     - **Default Duration**
     - **Description**
   * - ``CTD`` (point)
     - Depth-based
     - Descent + ascent at ``ctd_descent_rate_m_s`` / ``ctd_ascent_rate_m_s``, plus ``turnaround_time_minutes``.
       Without a usable depth (missing, zero or the fill value ``-9999``): 999 hours fill
   * - ``underway``, ``towing``, ``CTD`` (line)
     - Transit time
     - Route length at the line's ``vessel_speed_kt`` (or the leg/cruise default)
   * - ``survey`` (area)
     - None
     - ``duration_minutes`` is required
   * - ``mooring``
     - 999 hours
     - Fill value, the same in ``enrich`` and ``schedule``; set ``duration_minutes`` explicitly
   * - ``water_sampling``, ``calibration``
     - Depth-based
     - As ``CTD`` when ``operation_depth_m`` or ``water_depth_m`` is set; otherwise 999 hours fill
   * - ``port``, ``waypoint``
     - 0
     - No operation time
   * - ``net_tow`` *(planned)*
     - 90 min
     - Biological sampling — not yet implemented
   * - ``grab_sample`` *(planned)*
     - 30 min
     - Sediment/water sampling — not yet implemented
   * - ``adcp`` *(planned)*
     - Transit time
     - Current profiling — not yet implemented
   * - ``xbt`` *(planned)*
     - 15 min
     - Expendable temperature probe — not yet implemented

Overriding Calculated Duration
------------------------------

Setting ``duration_minutes: <value>`` (in **minutes**) on any point operation overrides
the depth-based cast time calculation entirely.  This is useful when a station
requires a non-standard instrument configuration, a fixed time budget, or
must match a pre-agreed slot in a joint cruise plan:

.. code-block:: yaml

   points:
     - name: "STN_001"
       latitude: 60.0
       longitude: -30.0
       operation_type: CTD
       action: profile
       duration_minutes: 120     # 2-hour cast regardless of water depth

When ``duration_minutes`` is set, the enrichment step will not overwrite it.  Omitting
``duration_minutes`` (or setting it to 0) restores depth-based calculation.

All time fields in YAML are in **minutes**: ``duration_minutes``, ``turnaround_time_minutes``,
``delay_start_minutes``, and ``buffer_time_minutes``.

Repeat Stations
---------------

The same activity name may appear more than once in a leg (in its
``activities`` list or across its clusters). Each occurrence is scheduled as
a separate operation, and the configuration loader logs a warning naming the
activity and where it is listed, so an unintended duplicate is visible.
Back-to-back repeats require no extra configuration:

.. code-block:: yaml

   legs:
     - name: "leg1"
       activities: ["STN_001", "STN_001"]   # two consecutive casts at the same location

For time-series stations where a wait between occupations is needed, define
separate entries with the same coordinates and set ``delay_start_minutes`` on the
later ones: the earlier occupation then lasts that much longer (the ship waits
on station).  ``delay_start_minutes`` is part of the point definition and is shared
by every reference to that name, so a gap can only be expressed by giving
each occupation a distinct name:

.. code-block:: yaml

   points:
     - name: "STN_001_t0"
       latitude: 60.0
       longitude: -20.0
       operation_type: CTD
       # no delay_start_minutes: starts on arrival

     - name: "STN_001_t6"
       latitude: 60.0
       longitude: -20.0
       operation_type: CTD
       delay_start_minutes: 360    # STN_001_t0 lasts 6 hours longer (wait on station)

   legs:
     - name: "leg1"
       activities: ["STN_001_t0", "STN_001_t6"]

Validation Rules
================

CruisePlan validates configurations with these rules:

- **Unique names**: All point, line, and area definitions must have unique
  names within their catalog.  The same name *may* appear multiple times in
  an ``activities`` list (see Repeat Stations above).
- **Valid coordinates**: Lat/lon within valid ranges
- **Date format**: ISO format YYYY-MM-DD
- **Positive durations**: Times must be > 0
- **Referenced activities**: All leg activities must exist in catalog

Parameter Inheritance
=====================

Parameters cascade from cruise → leg → operation. Clusters do not carry
speed or spacing parameters, and point definitions have no ``vessel_speed_kt``;
a per-operation speed is set on a line:

.. code-block:: yaml

   # Cruise level (applied to all legs)
   default_vessel_speed_kt: 10.0

   legs:
     - name: "leg1"
       vessel_speed_kt: 12.0      # Overrides cruise default
       activities:
         - "CTD_001"           # Transit to this station uses leg speed: 12.0 kt
         - "transect_A"

   lines:
     - name: "transect_A"
       vessel_speed_kt: 8.0       # Overrides leg speed along this line

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
       description: "Main science operations in Denmark Strait"
       activities: ["CTD_001"]

File Processing
===============

CruisePlan processes files in this sequence:

1. **Parse YAML**: Load and validate syntax
2. **Validate structure**: Check required fields and references
3. **Enrich data**: Add depths, distances, durations
4. **Generate outputs**: Create timeline and deliverables

For examples and workflows, see :doc:`../user-guide/workflows`.