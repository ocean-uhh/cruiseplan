Units and Defaults
==================

This reference covers units, formats, and defaults used throughout CruisePlan.

.. seealso::
   - :doc:`yaml_reference` for complete YAML syntax
   - :doc:`calculations` for calculation methods  
   - :doc:`user_workflows` for practical usage examples

.. contents:: Table of Contents
   :local:
   :depth: 3

Quick Reference
---------------

.. list-table:: **Core Units at a Glance**
   :widths: 25 25 50
   :header-rows: 1

   * - **Quantity**
     - **Unit**
     - **Notes**
   * - Vessel Speed
     - knots
     - Nautical miles per hour
   * - Duration/Time
     - minutes
     - All operation durations, delays, and timing fields
   * - Water Depth
     - meters
     - Positive values indicate depth below sea surface
   * - Distance
     - kilometers
     - Horizontal distances, station spacing, route planning
   * - Coordinates
     - decimal degrees
     - WGS84 datum, latitude/longitude

Standard Units
--------------

CruisePlan uses consistent units across all components to ensure compatibility and reduce conversion errors.

**Core Measurement Units**:

All calculations, YAML configuration, and output formats use these standardized units. Mixing units will cause validation errors or incorrect results.

**Unit Consistency Benefits**:

- **No conversion errors**: Single unit system eliminates unit mix-ups
- **Predictable calculations**: All duration and distance math uses same base units
- **Validation support**: CruisePlan warns about values outside expected ranges

Time and Duration Formats
--------------------------

**Timestamps: ISO 8601 Format**

All timestamps in YAML files use ISO 8601 format with timezone specification.

.. code-block:: yaml

    # Standard timestamp format
    start_date: "2025-06-01T08:00:00Z"
    
    # Examples with timezones
    departure_time: "2025-06-01T06:00:00-04:00"  # EDT timezone
    arrival_time: "2025-06-15T18:30:00+00:00"    # UTC timezone

**Duration Fields: Minutes as Decimal**

All duration fields are specified in minutes as floating-point values for consistent precision.

.. code-block:: yaml

    # Duration examples
    duration: 120.0          # 2 hours
    turnaround_time: 30.0    # 30 minutes
    delay_start: 240.0       # 4 hours for daylight operations
    delay_end: 60.0         # 1 hour equipment settling
    buffer_time: 480.0      # 8 hours weather contingency


Coordinate Systems
------------------

**Primary Format: Decimal Degrees (WGS84)**

.. code-block:: yaml

    position:
      latitude: 75.58333     # 75°35'N
      longitude: -15.25000   # 15°15'W

**Precision Standards**:

- **Storage**: 5 decimal places (±XX.XXXXX°) for ~1.1 meter accuracy at equator
- **Display**: 4 decimal places for readability  
- **Purpose**: Reduces rounding errors in calculations

**Available Coordinate Formats**

CruisePlan can generate coordinates in multiple formats for operational use:

- **Decimal Degrees**: ``75.58333, -15.25000`` (primary format)
- **DMM (Degrees, Decimal Minutes)**: ``75°35.000'N, 015°15.000'W`` (enrichment output)

**Enrichment Example**:

.. code-block:: yaml

    # Input (user specification)
    position:
      latitude: 60.5000
      longitude: -20.7500
      
    # After enrichment (DMM format added)
    coordinates_dmm: "60 30.00'N, 020 45.00'W"

Depth Convention
----------------

**Oceanographic Convention: Positive Down**

Water depth uses positive values to indicate depth below sea surface.

.. code-block:: yaml

    stations:
      - name: "Deep_Station"
        operation_depth: 500.0    # CTD cast to 500m
        water_depth: 4000.0       # Seafloor at 4000m
        
**Depth Field Semantics**:

- **operation_depth**: Target depth for operation (e.g., CTD cast depth)
- **water_depth**: Seafloor depth at location (bathymetric depth)

**Depth Precision**:

- **Bathymetry enrichment**: Rounded to nearest whole meter
- **User-specified depths**: Original precision preserved  
- **Configuration processing**: May round to 0.1 meter in some contexts

Default Configuration Values
----------------------------

CruisePlan applies sensible defaults for some of the parameters when values are not explicitly specified. These can be overridden at the cruise, leg, or individual operation level.  

CruisePlan applies non-sensical defaults to other operations (default mooring time is 999.0 hours) to ensure the user is forced to specify a value.

**Vessel and Operation Defaults**:

.. list-table:: **Configuration Defaults**
   :widths: 30 20 50
   :header-rows: 1

   * - **Parameter**
     - **Default Value**
     - **Description**
   * - ``default_vessel_speed``
     - 10.0 knots
     - Vessel transit speed for route calculations
   * - ``turnaround_time``
     - 30.0 minutes
     - Time between consecutive operations
   * - ``ctd_descent_rate``
     - 1.0 m/s
     - CTD instrument descent rate
   * - ``ctd_ascent_rate``
     - 2.0 m/s
     - CTD instrument ascent rate

**Timing and Buffer Defaults**:

.. list-table:: **Operation Defaults**
   :widths: 30 20 50
   :header-rows: 1

   * - **Parameter**
     - **Default Value**
     - **Description**
   * - ``delay_start``
     - 0.0 minutes
     - Pre-operation delay time
   * - ``delay_end``
     - 0.0 minutes
     - Post-operation delay time
   * - ``buffer_time``
     - 0.0 minutes
     - Leg-level contingency time

**Data Processing Defaults**:

.. list-table:: **Enrichment Defaults**
   :widths: 30 20 50
   :header-rows: 1

   * - **Parameter**
     - **Default Value**
     - **Description**
   * - ``bathymetry_source``
     - etopo2022
     - Bathymetry dataset for depth enrichment
   * - ``coord_format``
     - dmm
     - Coordinate format for enrichment output
   * - ``distance_between_stations``
     - 20.0 km
     - Default spacing for CTD section expansion

Examples by Use Case
--------------------

**Basic Station Definition**

Complete station with all standard units clearly identified:

.. code-block:: yaml

    stations:
      - name: "CTD_001"
        position:
          latitude: 50.5000        # decimal degrees (WGS84)
          longitude: -30.2500      # decimal degrees (WGS84)
        operation_type: "CTD"
        action: "profile"
        operation_depth: 500.0     # meters (cast depth)
        water_depth: 2000.0        # meters (seafloor depth)
        duration: 180.0            # minutes (3 hours)

**Complex Operational Timing**

Station with advanced timing controls:

.. code-block:: yaml

    stations:
      - name: "Mooring_Deploy"
        operation_type: "mooring"
        action: "deployment"
        duration: 240.0           # minutes (4 hours deployment)
        delay_start: 120.0        # minutes (wait for daylight)
        delay_end: 60.0          # minutes (anchor settling time)

**Cruise-Level Configuration Overrides**

Override system defaults for specific cruise requirements:

.. code-block:: yaml

    # Override system defaults
    default_vessel_speed: 12.0    # knots (faster vessel)
    turnaround_time: 45.0         # minutes (longer equipment changes)
    
    # Timing parameters
    start_date: "2025-06-01T08:00:00Z"    # ISO 8601 format


Advanced Topics
-------------------------

Unit Conversion Functions
~~~~~~~~~~~~~~~~~~~~~~~~~

**Helper Function Strategy**

CruisePlan uses centralized helper functions in [`utils/constants.py`](https://github.com/ocean-uhh/cruiseplan/blob/main/cruiseplan/utils/constants.py) instead of magic numbers:

.. code-block:: python

   # From cruiseplan/utils/constants.py
   # Geographic constants
   R_EARTH_KM = 6371.0
   NM_PER_KM = 0.539957  
   KM_PER_NM = 1.852
   SECONDS_PER_MINUTE = 60.0
   MINUTES_PER_HOUR = 60.0
   
   # Conversion helper functions
   def km_to_nm(km: float) -> float:
       return km * NM_PER_KM
       
   def nm_to_km(nm: float) -> float:
       return nm * KM_PER_NM
       
   def hours_to_minutes(hours: float) -> float:
       return hours * MINUTES_PER_HOUR
       
   def minutes_to_hours(minutes: float) -> float:
       return minutes / MINUTES_PER_HOUR
       
   def rate_per_second_to_rate_per_minute(rate_per_sec: float) -> float:
       """Convert rate per second to rate per minute (e.g., m/s → m/min)."""
       return rate_per_sec * SECONDS_PER_MINUTE
       
   def hours_to_days(hours: float) -> float:
       """Convert hours to days."""
       return hours / HOURS_PER_DAY
       
   def minutes_to_days(minutes: float) -> float:
       """Convert minutes to days."""
       return minutes / (MINUTES_PER_HOUR * HOURS_PER_DAY)

**Available Conversion Functions**:

.. list-table:: Standard Unit Conversions with Helper Functions
   :widths: 40 25 35
   :header-rows: 1

   * - Conversion
     - Helper Function
     - Usage
   * - Kilometers ↔ Nautical Miles
     - ``km_to_nm()``, ``nm_to_km()``
     - Distance calculations for vessel speeds
   * - Hours ↔ Minutes
     - ``hours_to_minutes()``, ``minutes_to_hours()``
     - Duration format conversions
   * - Rate per Second → Rate per Minute
     - ``rate_per_second_to_rate_per_minute()``
     - CTD descent/ascent rate conversions
   * - Hours ↔ Days
     - ``hours_to_days()``
     - Long duration formatting for reports
   * - Minutes ↔ Days
     - ``minutes_to_days()``
     - Duration format conversions


Best Practices and Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Precision Standards**:

Match precision to operational requirements and avoid false precision:

- **Coordinates**: 5 decimal places for ~1.1 meter accuracy, display 4 decimal places
- **Durations**: 1 decimal place (6-second precision) 
- **Depths**: Whole meters for bathymetry, preserve user-specified precision
- **Speeds**: 1 decimal place for vessel speeds

**Using Helper Functions**:

Always use the provided helper functions instead of manual calculations to avoid magic numbers and ensure consistency:

.. code-block:: python

   # Good: Use helper functions
   from cruiseplan.utils.constants import hours_to_minutes, km_to_nm
   
   duration_min = hours_to_minutes(3.5)      # Convert 3.5 hours
   distance_nm = km_to_nm(185.2)             # Convert 185.2 km
   
   # Avoid: Manual calculations with magic numbers
   duration_min = 3.5 * 60                   # Magic number!
   distance_nm = 185.2 * 0.539957            # Magic number!

**Unit Consistency Guidelines**:

1. **Always use standard units**: Prevents conversion errors and calculation mistakes
2. **Use descriptive naming**: Make units obvious in field names and comments
3. **Leverage validation**: CruisePlan warns about unusual values and unit mismatches
4. **Reference this guide**: When in doubt about units or precision requirements

.. code-block:: yaml

    # Good: Clear, unambiguous values following standards
    duration: 240.0                  # Always minutes in CruisePlan
    operation_depth: 500.0           # Always meters below surface
    default_vessel_speed: 12.0       # Always knots
    
    # Avoid: Ambiguous or non-standard values  
    duration: 4                      # Hours? Minutes? Unclear!
    speed: 22                        # km/h? knots? m/s? Unknown!

.. note::
   When in doubt about units, refer to this page or check the field validation messages in CruisePlan's error output, which will specify expected units for each parameter.