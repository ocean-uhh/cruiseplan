.. _calculation-methods:

========================
Calculation Methods
========================

This document provides comprehensive documentation of all calculation methods used by CruisePlan, including distance calculations, duration algorithms, and coordinate transformations.

.. contents:: Table of Contents
   :local:
   :depth: 3

----

Distance Calculations
=====================

CruisePlan implements multiple distance calculation methods optimized for different operation types and routing scenarios.

.. _route-based-distance:

Route-Based Distance Calculations
--------------------------------- 

**Route-Based Calculations (Preferred)**:
  Scientific transits and line operations use cumulative distance calculations along the defined route waypoints for maximum accuracy.

.. code-block:: python

  def route_distance(points):
      total_distance_km = 0.0
      for i in range(len(points) - 1):
          total_distance_km += haversine_distance(points[i], points[i + 1])
      # Return distance in kilometers
      return total_distance_km

This allows complex paths not just straight-line distance, for improved timing calculations.  However, NetCDF outputs currently store only start/end points for line operations, not intermediate waypoints (**current limitation**: to be fixed in a later release).

**Point-Based Calculations (Fallback)**:
  Simple great circle distance between entry and exit points when detailed routing is not available.

.. code-block:: python

  # Point-based (direct distance) in kilometers
  distance = haversine_distance(entry_point, exit_point)
 



**Distance Calculation for Routing *Between* Operations**:

.. list-table:: Entry/Exit Points for **Inter-operation* Routing 
    :widths: 25 25 50
    :header-rows: 1

    * - Operation Type
      - Entry/Exit Points
      - Used For
    * - Point Operations (Stations)
      - Same coordinates for both
      - Distance calculations to/from station location
    * - Line Operations (Transits)
      - First/last waypoints of route
      - Distance calculations to transit start/end
    * - Area Operations
      - First/last polygon corners
      - Distance calculations to area start/end points

This is for inter-operation routing.  For within-operation routing of LineOperations, the full waypoint list is used.  This includes both scientific transits and navigation transits.

Haversine Distance Formula
--------------------------

All great circle distance calculations use the haversine formula for spherical earth approximation:

.. code-block:: python

  import math
  # From cruiseplan/calculators/distance.py
  def haversine_distance(start, end):
      """Calculate Great Circle distance using Haversine formula."""
      lat1, lon1 = to_coords(start)
      lat2, lon2 = to_coords(end)

      phi1, phi2 = math.radians(lat1), math.radians(lat2)
      dphi = math.radians(lat2 - lat1)
      dlambda = math.radians(lon2 - lon1)

      a = (math.sin(dphi / 2) ** 2
          + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
      c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

      return R_EARTH_KM * c

**Constants**: Earth radius and conversion factors are defined in `cruiseplan/utils/constants.py`

**Accuracy Considerations**:
  - **Earth Approximation**: Spherical model suitable for basic estimates of oceanographic distances without requiring more complex package dependencies
  - **Precision**: Accurate to ~0.5% for distances up to several thousand kilometers

----

.. _duration-calculations:

Duration Calculations
=====================

CruisePlan implements operation-specific duration algorithms based on oceanographic best practices.

CTD Profile Duration Calculator
-------------------------------

**Automatic Duration Calculation**:

CTD operations use depth-based duration calculations incorporating realistic descent/ascent rates and operational procedures:

.. code-block:: python

  # From cruiseplan/calculators/duration.py  
  def calculate_ctd_time(self, depth: float) -> float:
      """Calculate CTD profiling duration including descent, ascent, and turnaround."""
      if depth <= 0:
          return 0.0

      # Convert rates (m/s) to m/min using helper function
      descent_m_min = rate_per_second_to_rate_per_minute(self.config.ctd_descent_rate)
      ascent_m_min = rate_per_second_to_rate_per_minute(self.config.ctd_ascent_rate)
      
      # Calculate profile time
      profile_time = (depth / descent_m_min) + (depth / ascent_m_min)
      
      # Total operation duration in minutes
      return profile_time + self.config.turnaround_time

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
   * - Turnaround Time
     - 30 minutes
     - Station approach, deployment, recovery, departure

**Depth-Duration Examples**:

Based on the calculation, the following are example CTD profile durations at various depths.  Note, however, that in practice, the CTD speed is typically slower in the top 100 m and bottom 100m (to avoid hitting the bottom/let the altimeter kick in).  So our timing estimates will be inaccurate for many shallow profiles.  This can be adjusted by altering the descent/ascent rates in the cruise configuration (see :ref:`yaml-reference`) or the turnaround time.

Note: Weather and sea state, or equipment variations may require further adjustments not automatically included in these calculations.

.. list-table:: CTD Duration Calculation Examples
    :widths: 20 25 30
    :header-rows: 1

    * - Depth
      - Cast Time
      - Total Duration
    * - 100m
      - 3.3 min
      - 35.3 min
    * - 1000m
      - 33.3 min
      - 65.3 min
    * - 3000m
      - 100.0 min
      - 132.0 min
    * - 5000m
      - 166.7 min
      - 198.7 min

Transit Duration Calculator
---------------------------

**Speed-Based Calculations**:

Transit durations use distance and vessel speed with automatic unit conversions:

.. code-block:: python

   # From cruiseplan/calculators/duration.py
   def calculate_transit_time(distance_km, speed_knots=None):
       """Calculate vessel transit duration based on distance and speed."""
       # Convert kilometers to nautical miles
       distance_nm = km_to_nm(distance_km)
       
       # Calculate duration in hours
       duration_hours = distance_nm / speed_knots
       
       # Convert to minutes using helper function
       return hours_to_minutes(duration_hours)

.. _coordinate-calculations:


.. _calculation-accuracy:

----

Map Visualization vs Distance Calculations  
========================================== 

.. important::
   **Transit Route Representation**: Map visualization differs depending on data source. Maps generated from cruise configuration show **full routes** (same waypoints as calculations), while maps from timeline data show simplified **cruise tracks** connecting only activity positions.

**Data Source Differences**:

**Maps from Cruise Config** (`cruiseplan map`):
  - **Full route waypoints**: Same data as distance calculations
  - **Visual**: Straight line segments connecting all route waypoints  
  - **Calculation**: Great circle distance between same waypoints
  - **Correspondence**: High fidelity between visualization and calculation

**Maps from Timeline** (`cruiseplan schedule --format png`):
  - **Activity positions only**: Connects entry/exit points of operations
  - **Visual**: Simplified cruise track through activity locations
  - **Calculation**: Full route distance (more detailed than visualization)
  - **Correspondence**: Visualization simplified compared to calculations

**Rendering Considerations**:
  - **Straight line segments**: Maps render direct connections between waypoints
  - **Great circle math**: Calculations use spherical earth geometry for precision
  - **Map projection effects**: Visual distortion varies with projection and geographic region


