Units and Defaults
==================

This page documents the standard units, formats, and default values used throughout CruisePlan.

Standard Units
--------------

CruisePlan uses consistent units across all components to ensure compatibility and reduce conversion errors.

.. list-table:: **Core Measurement Units**
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

Time Formats
------------

**ISO 8601 Format**: All timestamps in YAML files use ISO 8601 format with timezone specification.

.. code-block:: yaml

    # Standard timestamp format
    start_date: "2025-06-01T08:00:00Z"
    
    # Examples
    departure_time: "2025-06-01T06:00:00-04:00"  # EDT timezone
    arrival_time: "2025-06-15T18:30:00+00:00"    # UTC timezone

**Duration Fields**: Specified in minutes as floating-point values.

.. code-block:: yaml

    # Duration examples
    duration: 120.0          # 2 hours
    turnaround_time: 30.0    # 30 minutes
    delay_start: 240.0       # 4 hours
    delay_end: 60.0         # 1 hour
    buffer_time: 480.0      # 8 hours

Depth Convention
----------------

**Water Depth**: Positive values indicate depth below sea surface (oceanographic convention).

.. code-block:: yaml

    stations:
      - name: "Deep_Station"
        depth: 4000.0      # 4000 meters below sea surface
        
    transits:
      - name: "Section_A"
        max_depth: 2500.0  # Maximum cast depth

**Rounding**: Depth values are rounded to preserve meaningful precision while avoiding false accuracy.

- **Bathymetry data**: Rounded to nearest meter
- **Station depths**: User-specified precision preserved
- **Calculated depths**: Rounded to 0.1 meter precision

Coordinate Formats
------------------

**Primary Format**: Decimal degrees (WGS84)

.. code-block:: yaml

    position:
      latitude: 75.58333     # 75°35'N
      longitude: -15.25000   # 15°15'W

**Output Formats**: CruisePlan can generate coordinates in multiple formats for operational use:

- **DMM (Degrees, Decimal Minutes)**: ``75°35.000'N, 015°15.000'W``
- **DMS (Degrees, Minutes, Seconds)**: ``75°35'00"N, 015°15'00"W`` (not yet implemented)

**Coordinate Precision Details**:

CruisePlan stores coordinates with 5 decimal place precision:

- **Latitude**: ±XX.XXXXX° (e.g., ``75.58333``)
- **Longitude**: ±XXX.XXXXX° (e.g., ``-15.25000``)
- **Accuracy**: ~1.1 meter precision at equator - avoid calculation errors due to rounding
- **Display formats**: Show 4 decimal places for readability

Default Values
--------------

CruisePlan applies sensible defaults when values are not explicitly specified. These can be overridden at the cruise, leg, or individual operation level.

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

Examples in YAML
----------------

For more complete examples, see the :doc:`YAML Configuration Reference <yaml_reference>`.

**Complete Station Definition with Units**:

.. code-block:: yaml

    stations:
      - name: "CTD_001"
        position:
          latitude: 50.5000        # decimal degrees
          longitude: -30.2500      # decimal degrees
        operation_type: "CTD"
        action: "profile"
        depth: 2000.0             # meters (positive down)
        duration: 180.0           # minutes (3 hours)
        delay_start: 120.0        # minutes (2 hours for daylight)
        delay_end: 60.0           # minutes (1 hour settling time)


**Cruise-Level Defaults**:

.. code-block:: yaml

    # Override system defaults
    default_vessel_speed: 12.0    # knots (faster vessel)
    turnaround_time: 45.0         # minutes (longer equipment changes)
    
    # Timing parameters
    start_date: "2025-06-01T08:00:00Z"    # ISO 8601 format

Unit Conversion Reference
-------------------------

**Common Conversions**:

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - **Conversion**
     - **Formula**
   * - Hours ↔ Minutes
     - ``hours × 60 = minutes``
   * - Knots ↔ km/h
     - ``knots × 1.852 = km/h``
   * - Nautical Miles ↔ Kilometers
     - ``nm × 1.852 = km``
   * - Decimal Degrees ↔ DMM
     - ``DD.dddd → DD°MM.mmm'``

**Precision Guidelines**:

- **Coordinates**: 5 decimal places (stored/computed precision, ~1 meter accuracy)
- **Durations**: 1 decimal place (6-second precision) 
- **Depths**: Whole numbers for routine operations, decimals for precision work
- **Speeds**: 1 decimal place for vessel speeds



Best Practices
--------------

1. **Consistency**: Always use the standard units to avoid conversion errors
2. **Precision**: Match precision to operational requirements  
3. **Validation**: CruisePlan validates some units and will warn about unusual values
4. **Clear Naming**: Use descriptive field names and values that make units obvious

.. code-block:: yaml

    # Good: Unambiguous values following standard units
    duration: 240.0           # Always minutes in CruisePlan
    depth: 3500.0            # Always meters below surface
    default_vessel_speed: 12.0   # Always knots
    
    # Avoid: Ambiguous or non-standard values
    duration: 4              # Could be hours, minutes, unclear!
    speed: 22                # km/h? knots? m/s? Unknown!



.. note::
   When in doubt about units, refer to this page or check the field validation messages in CruisePlan's error output, which will specify expected units for each parameter.