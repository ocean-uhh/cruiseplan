.. _operation-types-reference:

========================
Operation Types Reference  
========================

This document provides comprehensive documentation of all operation types supported by CruisePlan, including their valid actions, duration calculations, and routing behaviors.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
========

CruisePlan supports three categories of operations:

1. **Point Operations** (stations): Operations at fixed geographic locations
2. **Line Operations** (transits): Operations along defined routes  
3. **Area Operations** (areas): Operations covering defined geographic regions

Each operation type has specific validation rules, duration calculation methods, and routing behaviors that determine how they integrate into cruise schedules.

.. _point-operations:

Point Operations (Stations)
============================

Point operations represent activities conducted at fixed geographic locations. They are defined in the ``stations`` catalog and converted to ``PointOperation`` objects during scheduling.

Supported Operation Types
-------------------------

.. list-table:: Point Operation Types
   :widths: 20 20 60
   :header-rows: 1

   * - Operation Type
     - Valid Actions  
     - Description
   * - ``CTD``
     - ``profile``
     - Conductivity-Temperature-Depth profiling operations
   * - ``water_sampling``
     - ``sampling``
     - Water sample collection (bottles, etc.)
   * - ``mooring``
     - ``deployment``, ``recovery``
     - Mooring deployment or recovery operations
   * - ``calibration``
     - ``calibration``
     - Equipment calibration or validation

Duration Calculation
--------------------

Point operations use different duration calculation methods based on operation type:

**CTD Operations**:
  Calculated automatically based on depth, descent/ascent rates, and turnaround time:

  .. code-block:: python

     # CTD duration calculation  
     descent_time = operation_depth / ctd_descent_rate  # seconds
     ascent_time = operation_depth / ctd_ascent_rate    # seconds
     total_duration = (descent_time + ascent_time) / 60 + turnaround_time  # minutes

**Mooring Operations**:
  Require manual duration specification in the ``duration`` field. No automatic calculation available.

**Other Operations**:
  Use turnaround time if no manual duration specified.

**Manual Override**:
  All operations can use a manual ``duration`` field to override automatic calculations.

Routing Behavior
----------------

Point operations serve as precise navigation targets with the following routing characteristics:

- **Entry/Exit Points**: Both entry and exit use the exact station coordinates
- **Distance Calculations**: Standard great circle distance to/from station position
- **Routing Anchors**: Can serve as ``first_waypoint`` and ``last_waypoint`` in legs

.. _line-operations:

Line Operations (Transits)
===========================

Line operations represent movement or data collection along defined routes. They are defined in the ``transits`` catalog and converted to ``LineOperation`` objects during scheduling.

Supported Operation Types
-------------------------

.. list-table:: Line Operation Types
   :widths: 20 20 60
   :header-rows: 1

   * - Operation Type
     - Valid Actions
     - Description
   * - ``underway``
     - ``ADCP``, ``bathymetry``, ``thermosalinograph``
     - Underway data collection during vessel movement
   * - ``towing``
     - ``tow_yo``, ``seismic``, ``microstructure``
     - Towed instrument operations

**Navigation-Only Transits**:
  When no ``operation_type`` is specified, transits represent pure vessel movement with no scientific activities.

Duration Calculation  
--------------------

Line operations calculate duration based on route distance and vessel speed:

.. code-block:: python

   # Line operation duration calculation
   total_route_distance_km = sum(
      haversine_distance(p1, p2) for p1, p2 in zip(route, route[1:])
   )
   route_distance_nm = total_route_distance_km * 0.539957  # km -> nautical miles
   vessel_speed = transit.vessel_speed or config.default_vessel_speed  # knots
   duration_hours = route_distance_nm / vessel_speed
   duration_minutes = duration_hours * 60

**Speed Override**:
  Individual transits can specify ``vessel_speed`` to override the default cruise speed.

Routing Behavior
----------------

Line operations provide flexible routing with the following characteristics:

- **Entry Point**: First waypoint in the route
- **Exit Point**: Last waypoint in the route  
- **Distance Calculations**: Sum of distances between all consecutive waypoints
- **Routing Anchors**: Can serve as ``first_waypoint`` and ``last_waypoint`` using route endpoints

.. _area-operations:

Area Operations
===============

Area operations represent activities conducted over defined geographic regions. They are defined in the ``areas`` catalog and converted to ``AreaOperation`` objects during scheduling.

Supported Operation Types
-------------------------

.. list-table:: Area Operation Types
   :widths: 20 20 60
   :header-rows: 1

   * - Operation Type
     - Valid Actions
     - Description
   * - ``survey``
     - ``bathymetry``, ``seismic``, ``biological``
     - Systematic surveys covering the defined area
   * - ``mapping``
     - ``multibeam``, ``sidescan``, ``acoustic``
     - High-resolution mapping operations
   * - ``sampling``
     - ``sediment``, ``biological``, ``water``
     - Area-based sampling operations

Area Definition Requirements
----------------------------

Areas must be properly defined with the following constraints:

**Corner Points**:
  - **Minimum**: 3 corner points required for a valid polygon
  - **Recommended**: 4+ points for rectangular/complex areas
  - **Coordinate Order**: Points should define a logical polygon boundary
  - **Closure**: Areas are automatically closed (no need to repeat first point)

**Corner Coordinate Requirements**:
  - **Format**: "latitude, longitude" string format (decimal degrees)
  - **Precision**: Standard decimal degrees precision (typically 4-6 decimal places)
  - **Valid Ranges**: Latitude [-90, 90], Longitude [-180, 180]
  - **Consistency**: All corners must use consistent coordinate system and precision

**Example Area Definition**:

.. code-block:: yaml

   areas:
     - name: "Multibeam_Grid_A"
       operation_type: "mapping"
       action: "multibeam"
       duration: 480.0  # 8 hours
       corners:
         - "50.0000, -40.0000"  # Southwest corner - High precision
         - "51.0000, -40.0000"  # Southeast corner  
         - "51.0000, -39.0000"  # Northeast corner
         - "50.0000, -39.0000"  # Northwest corner
       comment: "High-resolution bathymetry survey"
       
     - name: "Triangular_Survey_Zone"
       operation_type: "survey" 
       action: "biological"
       duration: 360.0  # 6 hours
       corners:
         - "52.5, -41.2"   # Point A - Standard precision
         - "53.0, -40.8"   # Point B
         - "52.2, -40.5"   # Point C
       comment: "Biological sampling area - minimum 3 points"

**Center Point Calculations for Examples**:
- **Multibeam_Grid_A**: Center = (50.5°N, 39.5°W)  
- **Triangular_Survey_Zone**: Center = (52.57°N, 40.83°W)

Duration Calculation
--------------------

Area operations require manual duration specification:

**Required Duration Field**:
  Areas must specify ``duration`` in minutes as there is no automatic calculation method for complex area operations.

**Duration Planning Considerations**:
  - Survey line spacing and coverage patterns
  - Vessel speed during survey operations
  - Equipment deployment and recovery time
  - Weather and sea state factors

.. _area-center-point-calculation:

Area Center Point Calculation
------------------------------

For routing purposes, CruisePlan calculates the geographic center point of each area:

**Center Point Formula**:

.. code-block:: python

   # Area center point calculation
   center_latitude = sum(corner.latitude for corner in corners) / len(corners)
   center_longitude = sum(corner.longitude for corner in corners) / len(corners)

**Routing Applications**:

The calculated center point is used for:

- **Distance calculations** to/from other operations
- **Transit time estimation** when routing to/from the area
- **Navigation waypoints** when areas serve as ``first_waypoint`` or ``last_waypoint``

**Important Notes**:

- The center point is for routing calculations only; actual area operations may follow complex survey patterns
- Areas with irregular shapes may have center points outside the operational area
- For precise navigation within areas, define explicit waypoints or station sequences
- **Routing Integration**: Area center points are used seamlessly with station coordinates and transit endpoints for distance calculations
- **Waypoint Compatibility**: When areas serve as ``first_waypoint`` or ``last_waypoint`` in legs, the center point provides a consistent navigation target

Routing Behavior as Anchors
----------------------------

Areas can serve as routing anchors in legs with the following behavior:

**As ``first_waypoint``**:
  - Vessel routes to the area center point  
  - Area operation begins upon arrival
  - Entry point calculation uses center coordinates

**As ``last_waypoint``**:  
  - Area operation executes at the defined location
  - Exit point calculation uses center coordinates
  - Next leg routing begins from center point

**Example Routing Usage**:

.. code-block:: yaml

   legs:
     - name: "Survey_Phase"
       first_waypoint: "CTD_Entry"     # Start with station operation
       last_waypoint: "Mapping_Area"   # End with area survey
       activities: [
         "CTD_Entry",      # Point operation
         "Transit_Line",   # Line operation
         "Mapping_Area"    # Area operation (routed to center point)
       ]

**Benefits**:

- **Seamless integration**: Areas work with stations and transits in unified workflows
- **Automatic routing**: No manual center point calculations required  
- **Flexible operations**: Support for complex multi-operation legs

.. _operation-validation:

Operation Validation Rules
===========================

Type-Action Combinations
-------------------------

CruisePlan enforces strict validation rules for operation type and action combinations:

**Valid Combinations by Category**:

.. list-table:: Operation Type Validation Matrix
   :widths: 25 25 25 25
   :header-rows: 1

   * - Category
     - Operation Type
     - Valid Actions
     - Notes
   * - Point Operations
     - ``CTD``
     - ``profile``
     - Automatic duration calculation available
   * - Point Operations
     - ``water_sampling``
     - ``sampling``
     - Manual duration required
   * - Point Operations
     - ``mooring``
     - ``deployment``, ``recovery``
     - Manual duration required
   * - Point Operations
     - ``calibration``
     - ``calibration``
     - Manual duration required
   * - Line Operations
     - ``underway``
     - ``ADCP``, ``bathymetry``, ``thermosalinograph``
     - Duration based on route and speed
   * - Line Operations
     - ``towing``
     - ``tow_yo``, ``seismic``, ``microstructure``
     - Duration based on route and speed
   * - Area Operations
     - ``survey``
     - ``bathymetry``, ``seismic``, ``biological``
     - Manual duration required
   * - Area Operations
     - ``mapping``
     - ``multibeam``, ``sidescan``, ``acoustic``
     - Manual duration required
   * - Area Operations
     - ``sampling``
     - ``sediment``, ``biological``, ``water``
     - Manual duration required

**Validation Errors**:

Invalid type-action combinations will result in validation errors with specific guidance on correct combinations.

Duration Requirements
---------------------

**Automatic Calculation Available**:
  - CTD operations (based on depth and rates)
  - Line operations (based on route and speed)

**Manual Duration Required**:
  - Mooring operations (deployment/recovery complexity varies)
  - Area operations (survey patterns and coverage vary)
  - Water sampling operations (sample collection methods vary)
  - Calibration operations (procedure complexity varies)

**Manual Override Always Available**:
  All operations can specify manual ``duration`` to override automatic calculations when needed.

.. _best-practices:

Best Practices
==============

Operation Planning
------------------

**Point Operations**:
  - Use CTD automatic duration for standard profiles
  - Specify manual duration for complex mooring operations  
  - Include buffer time for equipment setup/breakdown

**Line Operations**:
  - Define realistic vessel speeds for scientific operations
  - Consider sea state and weather impacts on towed operations
  - Plan waypoint spacing for instrument performance

**Area Operations**:
  - Plan duration based on survey line spacing and coverage requirements
  - Consider equipment deployment/recovery time in duration estimates
  - Define corner points to clearly encompass the operational area

Routing and Integration
-----------------------

**Mixed Operation Workflows**:
  - Use areas as natural leg boundaries for survey phases
  - Combine point and line operations efficiently within legs
  - Plan logical operational sequences considering setup/breakdown time

**Distance Optimization**:
  - Consider area center points when planning approach routes
  - Use line operations for efficient transit between distant point operations
  - Plan area operations to minimize vessel repositioning

**Timing Considerations**:
  - Account for weather windows in area operation planning
  - Use buffer time fields for operational flexibility
  - Consider day/night operation constraints for equipment limitations

.. _troubleshooting:

Troubleshooting
===============

Common Validation Errors
-------------------------

**Invalid Type-Action Combinations**:
  
.. code-block:: text

   Error: Operation type 'CTD' must use action: profile. Got 'deployment'
   
**Solution**: Use correct action for operation type (see validation matrix above)

**Missing Duration for Area Operations**:

.. code-block:: text

   Error: Area operations require manual duration specification
   
**Solution**: Add ``duration`` field with estimated operation time in minutes

**Invalid Area Geometry**:

.. code-block:: text

   Error: Area requires minimum 3 corner points for valid polygon
   
**Solution**: Add sufficient corner points to define area boundary

**Routing Issues**:

.. code-block:: text

   Warning: Area center point falls outside operational boundary
   
**Solution**: Review corner point order to ensure logical polygon definition

Performance Considerations
--------------------------

**Large Area Operations**:
  - Consider breaking large areas into smaller sections
  - Plan for fuel consumption and crew endurance
  - Account for equipment maintenance requirements

**Complex Route Planning**:
  - Limit line operation waypoints to essential navigation points
  - Use area operations instead of dense point grids when appropriate
  - Consider automatic optimization algorithms for complex sequences

**Duration Estimation Accuracy**:
  - Validate CTD duration estimates against historical operations
  - Include safety margins for weather delays in manual durations
  - Test area operation estimates with representative survey patterns

This comprehensive operation types reference ensures proper planning and validation of all supported CruisePlan operation categories.