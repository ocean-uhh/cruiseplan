.. _calculation-methods:

========================
Calculation Methods
========================

This document provides comprehensive documentation of all calculation methods used by CruisePlan, including distance calculations, duration algorithms, and coordinate transformations.

.. contents:: Table of Contents
   :local:
   :depth: 3

Distance Calculations
=====================

CruisePlan implements multiple distance calculation methods optimized for different operation types and routing scenarios.

.. _route-based-distance:

Route-Based vs Point-Based Distance Calculations
-------------------------------------------------

**Route-Based Calculations (Preferred)**:
  Scientific transits and line operations use cumulative distance calculations along the defined route waypoints for maximum accuracy.

**Point-Based Calculations (Fallback)**:
  Simple great circle distance between entry and exit points when detailed routing is not available.

Scientific Transit Distance Improvements
-----------------------------------------

**Enhanced Route Accuracy**:

For scientific transits (line operations), distance calculations now use the full route waypoint sequence rather than simple point-to-point measurements:

.. code-block:: python

   # Route-based distance calculation
   def calculate_route_distance(waypoints):
       total_distance = 0.0
       for i in range(len(waypoints) - 1):
           segment_distance = haversine_distance(
               waypoints[i], waypoints[i+1]
           )
           total_distance += segment_distance
       return total_distance

**Benefits**:
  - **Realistic Transit Times**: Accounts for actual vessel path, not just straight-line distance
  - **Route Complexity**: Handles multi-waypoint scientific transits accurately
  - **Navigation Planning**: Provides precise distance estimates for fuel and timing calculations

**Distance Calculation Matrix**:

.. list-table:: Distance Method by Operation Type
   :widths: 25 25 50
   :header-rows: 1

   * - Operation Type
     - Distance Method
     - Description
   * - Point Operations (Stations)
     - Point-to-point great circle
     - Entry/exit at same coordinates
   * - Line Operations (Transits)
     - Route-based cumulative
     - Sum of distances between consecutive waypoints
   * - Area Operations
     - Point-to-center great circle
     - Distance to/from calculated center point
   * - Cluster Operations
     - Composite routing
     - Uses contained operation distance methods

Haversine Distance Formula
--------------------------

All great circle distance calculations use the haversine formula for spherical earth approximation:

.. code-block:: python

   import math
   
   def haversine_distance(coord1, coord2):
       """
       Calculate great circle distance between two points on Earth.
       
       Parameters:
       - coord1, coord2: (latitude, longitude) in decimal degrees
       
       Returns:
       - Distance in kilometers
       """
       R = 6371.0  # Earth radius in kilometers
       
       lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
       lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
       
       dlat = lat2 - lat1
       dlon = lon2 - lon1
       
       a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
       c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
       
       return R * c

**Accuracy Considerations**:
  - **Earth Approximation**: Spherical model suitable for oceanographic distances
  - **Precision**: Accurate to ~0.5% for distances up to several thousand kilometers
  - **Alternative**: For extremely high precision requirements, consider ellipsoidal models

.. _duration-calculations:

Duration Calculations
=====================

CruisePlan implements operation-specific duration algorithms based on oceanographic best practices.

CTD Profile Duration Calculator
-------------------------------

**Automatic Duration Calculation**:

CTD operations use depth-based duration calculations incorporating realistic descent/ascent rates and operational procedures:

.. code-block:: python

   def calculate_ctd_duration(depth_meters, turnaround_time_minutes=30.0):
       """
       Calculate CTD profile duration based on depth.
       
       Parameters:
       - depth_meters: Target cast depth in meters
       - turnaround_time_minutes: Station setup/breakdown time
       
       Returns:
       - Total duration in minutes
       """
       # Standard CTD operational parameters
       descent_rate = 1.0  # meters per second
       ascent_rate = 1.0   # meters per second
       bottom_time = 2.0   # minutes for bottom observations
       
       # Calculate cast times
       descent_time_seconds = depth_meters / descent_rate
       ascent_time_seconds = depth_meters / ascent_rate
       cast_time_minutes = (descent_time_seconds + ascent_time_seconds) / 60.0
       
       # Total operation duration
       total_duration = cast_time_minutes + bottom_time + turnaround_time_minutes
       
       return total_duration

**Duration Components**:

.. list-table:: CTD Duration Components
   :widths: 30 20 50
   :header-rows: 1

   * - Component
     - Typical Value
     - Description
   * - Descent Rate
     - 1.0 m/s
     - Standard CTD descent speed for data quality
   * - Ascent Rate  
     - 1.0 m/s
     - Controlled ascent for continuous sampling
   * - Bottom Time
     - 2 minutes
     - Near-bottom observations and instrument stabilization
   * - Turnaround Time
     - 30 minutes
     - Station approach, deployment, recovery, departure

**Depth-Duration Examples**:

.. code-block:: text

   Depth    | Cast Time | Total Duration
   ---------|-----------|---------------
   100m     | 3.3 min   | 35.3 min
   1000m    | 33.3 min  | 65.3 min  
   3000m    | 100.0 min | 132.0 min
   5000m    | 166.7 min | 198.7 min

Transit Duration Calculator
---------------------------

**Speed-Based Calculations**:

Transit durations use distance and vessel speed with automatic unit conversions:

.. code-block:: python

   def calculate_transit_duration(distance_km, vessel_speed_knots):
       """
       Calculate transit duration between operations.
       
       Parameters:
       - distance_km: Distance in kilometers
       - vessel_speed_knots: Vessel speed in knots
       
       Returns:
       - Duration in minutes
       """
       # Convert kilometers to nautical miles
       distance_nm = distance_km * 0.539957
       
       # Calculate duration in hours
       duration_hours = distance_nm / vessel_speed_knots
       
       # Convert to minutes
       duration_minutes = duration_hours * 60.0
       
       return duration_minutes

**Speed Considerations**:
  - **Transit Speed**: Typically 10-12 knots for research vessels
  - **Scientific Speed**: Reduced to 6-8 knots during data collection
  - **Weather Factors**: Not automatically included - use manual overrides for extreme conditions

.. _coordinate-calculations:

Coordinate Calculations  
=======================

Area Center Point Calculation
------------------------------

**Polygon Center Algorithm**:

Area operations use the arithmetic mean of corner coordinates to determine the center point for routing calculations:

.. code-block:: python

   def calculate_area_center_point(corner_coordinates):
       """
       Calculate center point of polygonal area.
       
       Parameters:
       - corner_coordinates: List of (latitude, longitude) tuples
       
       Returns:
       - (center_latitude, center_longitude) tuple
       """
       if not corner_coordinates:
           raise ValueError("Area must have at least one corner point")
       
       # Calculate arithmetic mean of coordinates
       total_lat = sum(coord[0] for coord in corner_coordinates)
       total_lon = sum(coord[1] for coord in corner_coordinates)
       
       center_lat = total_lat / len(corner_coordinates)
       center_lon = total_lon / len(corner_coordinates)
       
       return (center_lat, center_lon)

**Center Point Applications**:

.. list-table:: Center Point Usage
   :widths: 30 70
   :header-rows: 1

   * - Application
     - Description
   * - Distance Calculations
     - Entry/exit point for routing to/from areas
   * - Navigation Waypoints
     - Target coordinate when area serves as leg waypoint
   * - Transit Planning
     - Simplified routing for schedule calculations
   * - Map Visualization
     - Representative point for area display

**Important Limitations**:

.. warning::
   **Center Point Accuracy**: The arithmetic mean center point may fall outside the actual operational area for irregular polygons. This is acceptable for routing calculations but should not be used for operational navigation within the area.

**Example Calculations**:

.. code-block:: yaml

   # Rectangular area example
   corners: ["50.0, -40.0", "52.0, -40.0", "52.0, -38.0", "50.0, -38.0"]
   # Center: (51.0°N, 39.0°W)
   
   # Triangular area example  
   corners: ["60.0, -50.0", "61.0, -48.0", "59.0, -47.0"]
   # Center: (60.0°N, 48.33°W)

Coordinate Format Conversions
-----------------------------

**Decimal Degrees to Degrees-Decimal Minutes**:

.. code-block:: python

   def decimal_to_dmm(decimal_degrees, is_longitude=False):
       """
       Convert decimal degrees to degrees-decimal minutes format.
       
       Parameters:
       - decimal_degrees: Coordinate in decimal degrees
       - is_longitude: True for longitude, False for latitude
       
       Returns:
       - Formatted string (e.g., "60°30.0'N")
       """
       abs_degrees = abs(decimal_degrees)
       degrees = int(abs_degrees)
       minutes = (abs_degrees - degrees) * 60.0
       
       if is_longitude:
           direction = 'E' if decimal_degrees >= 0 else 'W'
       else:
           direction = 'N' if decimal_degrees >= 0 else 'S'
       
       return f"{degrees}°{minutes:04.1f}'{direction}"

**Unit Conversions**:

.. list-table:: Standard Unit Conversions
   :widths: 40 20 40
   :header-rows: 1

   * - Conversion
     - Factor
     - Usage
   * - Kilometers to Nautical Miles
     - × 0.539957
     - Distance calculations for vessel speeds
   * - Nautical Miles to Kilometers  
     - × 1.852
     - Converting vessel distances to metric
   * - Knots to km/h
     - × 1.852
     - Speed unit conversions
   * - Minutes to Hours
     - ÷ 60
     - Duration format conversions

.. _calculation-accuracy:

Calculation Accuracy and Limitations
====================================

Map Visualization vs Distance Calculations  
-------------------------------------------

.. important::
   **Transit Line Display**: In map plotting utilities, transits are displayed as straight lines between waypoints for visual clarity. These straight-line visualizations **do not correspond** to the actual distance calculations used in scheduling, which may follow more complex routing.

**Visualization Considerations**:
  - **Straight Lines**: Maps show direct connections for readability
  - **Great Circle Routes**: Actual routing follows spherical earth geometry
  - **Multi-Waypoint Routes**: Complex transits simplified to key waypoints in visualization
  - **Scale Dependency**: Distortion effects vary with map projection and geographic region

Distance Calculation Accuracy
-----------------------------

**Spherical Earth Model**:
  - **Typical Accuracy**: ±0.5% for distances up to 1000 km
  - **Maximum Error**: ~1-2% for transcontinental distances
  - **Suitable For**: All oceanographic cruise planning applications

**Error Sources**:
  - Earth ellipsoid approximation
  - Local gravity variations
  - Atmospheric effects (not included)
  - Tidal effects (not included)

Duration Calculation Reliability
--------------------------------

**CTD Profile Accuracy**:
  - **Standard Conditions**: ±10% typical accuracy
  - **Deep Water**: Higher accuracy for >1000m casts
  - **Environmental Factors**: Weather, sea state not automatically included
  - **Equipment Variations**: Different CTD systems may require parameter adjustment

**Transit Duration Factors**:
  - **Weather Delays**: Not automatically included
  - **Current Effects**: Simplified ocean current model
  - **Fuel Considerations**: Not included in time calculations
  - **Operational Delays**: Use turnaround time for buffer

CSV Output Field Documentation
=============================

Transit Distance Fields
-----------------------

**Standard CSV Output Columns**:

.. list-table:: CSV Distance Output Fields
   :widths: 25 25 50
   :header-rows: 1

   * - Field Name
     - Units
     - Description
   * - ``transit_distance_km``
     - kilometers
     - Route-based distance calculation for line operations
   * - ``transit_distance_nm``
     - nautical miles
     - Same distance converted for maritime navigation
   * - ``straight_line_distance_km``
     - kilometers
     - Great circle distance between entry/exit points
   * - ``route_complexity_factor``
     - ratio
     - Route distance / straight-line distance (>1.0 indicates complex routing)

**Field Usage Examples**:

.. code-block:: text

   operation_name,transit_distance_km,transit_distance_nm,straight_line_distance_km,route_complexity_factor
   OVIDE_Section,2847.3,1538.2,2650.1,1.074
   Simple_Transit,185.6,100.2,185.6,1.000
   Complex_Survey,892.4,482.1,445.8,2.002

**Distance Field Interpretation**:
  - **Complex Routing**: ``route_complexity_factor > 1.2`` indicates significant waypoint deviations
  - **Navigation Planning**: Use ``transit_distance_nm`` for vessel fuel and timing calculations  
  - **Survey Efficiency**: Compare route vs straight-line distances for optimization opportunities

Performance Considerations
==========================

Calculation Optimization
------------------------

**Caching Strategies**:
  - Distance calculations cached between identical coordinate pairs
  - CTD duration parameters cached per cruise configuration
  - Area center points calculated once per area definition

**Computational Complexity**:
  - **Point Operations**: O(1) for distance calculations
  - **Line Operations**: O(n) where n = number of waypoints
  - **Area Operations**: O(1) for center point calculation  
  - **Cluster Operations**: O(m) where m = number of contained operations

**Large Dataset Handling**:
  - Batch processing for multi-leg expeditions
  - Parallel calculation support for independent operations
  - Memory-efficient processing for extensive station lists

This comprehensive calculation methods documentation ensures accurate understanding and implementation of all distance, duration, and coordinate algorithms used throughout CruisePlan.