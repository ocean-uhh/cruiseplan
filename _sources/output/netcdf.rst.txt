.. _output-netcdf:

==============
NetCDF Output
==============

CruisePlan generates CF-aligned NetCDF files containing your cruise timeline and operation data. These files provide structured datasets compatible with ``xarray`` and suitable for onward analysis or sharing.

.. note::
   NetCDF output is  available from the **schedule command** (``cruiseplan schedule --format netcdf``). 

Generated Files
===============

**Master Schedule**: `cruiseplan schedule --format netcdf` generates:

- ✅ **Ship Schedule** (`{cruise_name}_schedule.nc`) - Complete timeline with all operations

**Specialized Files**: `cruiseplan schedule --format netcdf --derive-netcdf` additionally generates:

- 🔧 **Point Operations** (`{cruise_name}_points.nc`) - Stations and moorings only  
- 🔧 **Line Operations** (`{cruise_name}_lines.nc`) - Scientific transits only
- 🔧 **Area Operations** (`{cruise_name}_areas.nc`) - Empty placeholder

**⚠️ Note**: The specialized files are generated but have not yet been verified for full CF-1.8 compliance. This is planned for future development.

The specialized files are filtered views of the master schedule file, organized by operation type for convenient analysis.

Technical Overview
==================

These files follow CF-1.8 discrete sampling geometry conventions (see `CF Conventions <https://cfconventions.org/>`_) and organize cruise data by operation geometry while maintaining scientific data standards.

CF Convention Alignment
-----------------------

- **FeatureType "point"**: Discrete observations at fixed locations (stations, moorings)
- **FeatureType "trajectory"**: Sequential observations along paths (surveys, ship schedule)
- **Coordinate Requirements**: All data variables include `coordinates` attribute
- **Standard Names**: Use CF standard name table for oceanographic variables

Provenance Attributes
---------------------

Every file also carries these global attributes, so a schedule can be traced
to its inputs:

- ``cruiseplan_version``
- ``source_config``, ``source_config_sha256``: YAML file the schedule was computed from
- ``bathymetry_source`` (and ``bathymetry_depths_filled`` when depths were enriched)
- ``default_vessel_speed_kt``, ``ctd_descent_rate_m_s``, ``ctd_ascent_rate_m_s``,
  ``turnaround_time_min``, ``start_date``
- ``date_created``: UTC, ISO 8601 with ``Z``; ``creation_date`` holds the same value

The schedule file adds ``fill_duration_count``, ``fill_duration_hours``,
``schedule_format`` (``"0.6.0"``) and the variable ``duration_fill_flag`` (1
where the duration is the 999-hour fill value).

Units
-----

Every numeric variable has a ``units`` attribute in UDUNITS-2 form (a test
checks each one with ``cf_units``); flags such as ``duration_fill_flag`` and
text variables have none. Readers should take the unit from the attribute.

.. list-table::
   :header-rows: 1
   :widths: 28 20 52

   * - Variable
     - ``units``
     - Notes
   * - ``time``, ``end_time``
     - ``seconds since 1970-01-01``
     - CF-encoded UTC (``calendar = "standard"``); ``xarray`` decodes them to
       datetimes
   * - ``duration``
     - ``minute``
     - Actual duration, ``end_time - time``
   * - ``planned_duration``
     - ``minute``
     - From the planning rules; differs from ``duration`` for a transit set
       by ``transit_minutes`` or shortened by a negative ``delay_start``
       (whose ``vessel_speed`` is then distance / time), and for an operation
       a negative ``delay_start`` shortened. 0 for wait rows
   * - ``delay_start``
     - ``minute``
     - As set on the operation. Positive: the "Waiting before" row (type
       ``wait``, category ``other``) just before it; negative: already taken
       off the transit into it. NaN for transits, buffers and waits
   * - ``distance``, ``distance_to_next``
     - ``nautical_mile``
     - Distance covered by the row; distance to the next waypoint
   * - ``vessel_speed``
     - ``knot``
     -
   * - ``water_depth``, ``operation_depth``
     - ``m``
     - Positive down
   * - ``latitude``, ``longitude`` and the start, end and exit positions
     - ``degrees_north``, ``degrees_east``
     -

Schedules written by cruiseplan 0.5.0 store ``duration`` in hours and the
row distance as ``dist_nm``. ``cruiseplan list`` and ``cruiseplan forecast``
read them, converting durations by their ``units`` attribute, until 0.7.0.

Output File Structure
=====================

The following files organize cruise data by operation geometry:

1. Point Operations (`{cruise_name}_points.nc`)
------------------------------------------------

- **Status**: ✅ Fully implemented - filtered view of stations and moorings from schedule  
- **Purpose**: All discrete scientific operations at fixed locations  
- **Data Source**: Filtered from ship schedule (`category == "point_operation"`)  
- **FeatureType**: `point` (CF discrete sampling geometry)  
- **Use Case**: Station lists, mooring inventories, sampling locations

.. code-block:: python

    # Dimensions
    obs = N_point_operations  # Total stations + moorings

    # Coordinate variables (spatial only)
    lon(obs): float32
        standard_name = "longitude"
        long_name = "longitude of the operation"
        units = "degrees_east"

    lat(obs): float32
        standard_name = "latitude"
        long_name = "latitude of the operation"
        units = "degrees_north"

    # Depth coordinates  
    waterdepth(obs): float32
        long_name = "water depth at operation location"
        standard_name = "sea_floor_depth_below_sea_surface"
        vocabulary = "http://vocab.nerc.ac.uk/collection/P07/current/CFV13N17/"
        units = "m"
        positive = "down"
        axis = "Z"
        _FillValue = -9999.0

    operation_depth(obs): float32
        long_name = "target operation depth"
        standard_name = "depth"
        units = "m"
        positive = "down"
        axis = "Z"
        _FillValue = -9999.0
        comment = "Target depth for operation (e.g., CTD cast depth), NaN if not specified"

    # Operation metadata
    name(obs): |S64
        long_name = "operation identifier from cruise plan"
        coordinates = "lat lon waterdepth"

    operation(obs): |S64
        long_name = "type of oceanographic operation"
        flag_values = "CTD_profile water_sampling calibration Mooring_deployment Mooring_recovery"
        coordinates = "lat lon waterdepth"

    duration(obs): float64
        long_name = "planned operation duration"
        units = "minute"
        coordinates = "lat lon waterdepth"

    comment(obs): |S256
        long_name = "operation comments from cruise plan"
        coordinates = "lat lon waterdepth"

    # Global attributes
    :featureType = "point"
    :title = "Point Operations: {cruise_name}"
    :institution = "Generated by CruisePlan software"
    :source = "YAML configuration file"
    :Conventions = "CF-1.8"
    :cruise_name = "{cruise_name}"
    :creation_date = "{iso_timestamp}"
    :coordinate_system = "WGS84"
    :depth_datum = "Mean Sea Level"

2. Line Operations (`{cruise_name}_lines.nc`)
-----------------------------------------------

- **Status**: ✅ Fully implemented - filtered view of scientific transits from schedule  
- **Purpose**: Scientific operations along defined paths  
- **Data Source**: Filtered from ship schedule (`category == "line_operation"`)  
- **FeatureType**: `trajectory` (CF discrete sampling geometry)  
- **Use Case**: ADCP surveys, tow-yo operations, bathymetry transects

.. code-block:: python

    # Dimensions
    operations = N_line_operations    # Number of discrete line operations
    endpoints = 2                    # Start and end points (0=start, 1=end)

    # Coordinate variables (2D arrays for start/end points)
    longitude(operations, endpoints): float32
        long_name = "longitude coordinates defining line operation"
        units = "degrees_east"
        comment = "endpoints dimension: 0=start point, 1=end point"

    latitude(operations, endpoints): float32
        long_name = "latitude coordinates defining line operation"
        units = "degrees_north"
        comment = "endpoints dimension: 0=start point, 1=end point"

    # Operation metadata
    operation_name(operations): |S64
        long_name = "line operation identifier"

    operation_type(operations): |S32
        long_name = "type of line operation"
        flag_values = "underway towing"
        flag_meanings = "underway_instruments towed_instruments"

    action(operations): |S32
        long_name = "specific survey instrument or method"
        flag_values = "ADCP bathymetry thermosalinograph tow_yo seismic microstructure"

    vessel_speed(operations): float32
        long_name = "planned vessel speed for operation"
        units = "knot"
        _FillValue = NaN

    duration(operations): float64
        long_name = "planned operation duration"
        units = "minute"
        _FillValue = NaN

    # Global attributes
    :featureType = "trajectory"
    :title = "Line Operations: {cruise_name}"
    :institution = "Generated by CruisePlan software"
    :source = "YAML configuration file"
    :Conventions = "CF-1.8"
    :cruise_name = "{cruise_name}"
    :creation_date = "{iso_timestamp}"

3. Area Operations (`{cruise_name}_areas.nc`)
-----------------------------------------------

- **Status**: ⚠️ Placeholder implementation - generates empty file  
- **Purpose**: Scientific operations over defined areas  
- **Data Source**: Filtered from ship schedule (`category == "area_operation"`)  
- **FeatureType**: `trajectory` (coverage patterns) or specialized  
- **Use Case**: Grid surveys, systematic mapping, search patterns

.. code-block:: python

    # Dimensions
    operations = N_area_operations      # Number of area operations  
    max_vertices = 20                   # Maximum vertices in any polygon

    # Coordinate variables (2D arrays with ragged fill)
    longitude(operations, max_vertices): float32
        long_name = "longitude vertices of area boundary polygon"
        units = "degrees_east"
        _FillValue = NaN
        comment = "Vertices define closed polygon boundary, unused positions filled with NaN"

    latitude(operations, max_vertices): float32
        long_name = "latitude vertices of area boundary polygon"
        units = "degrees_north" 
        _FillValue = NaN
        comment = "Vertices define closed polygon boundary, unused positions filled with NaN"

    # Vertex count for each operation
    n_boundary_vertices(operations): int32
        long_name = "number of vertices in boundary polygon"
        valid_range = [3, 20]
        comment = "Actual number of vertices used (rest are NaN)"

    # Operation metadata
    area_name(operations): |S64
        long_name = "area operation identifier"

    pattern_type(operations): |S32
        long_name = "area survey pattern"
        flag_values = "grid_survey systematic_mapping search_pattern random_sampling"

    estimated_duration(operations): float32
        long_name = "estimated operation duration"
        units = "minute"
        _FillValue = NaN

    # Derived geometric properties (useful for analysis)
    area_extent_km2(operations): float32
        long_name = "approximate area coverage"
        units = "km^2"
        _FillValue = NaN

    # Global attributes
    :featureType = "trajectory"  # or specialized area type
    :title = "Area Operations: {cruise_name}"
    :institution = "Generated by CruisePlan software"
    :source = "YAML configuration file"
    :Conventions = "CF-1.8"
    :cruise_name = "{cruise_name}"
    :creation_date = "{iso_timestamp}"

4. Ship Schedule (`{cruise_name}_schedule.nc`) - *Master File*
---------------------------------------------------------------

- **Status**: ✅ Fully implemented - master file containing all cruise data  
- **Purpose**: Complete ship trajectory including all operations and transits  
- **Data Source**: Timeline from scheduler (`List[ActivityRecord]`)  
- **FeatureType**: `trajectory` (ship's continuous path)  
- **Use Case**: Operational timeline, logistics, voyage tracking, source for specialized files

.. code-block:: python

    # Dimensions
    obs = N_timeline_events  # All scheduled activities in time order

    # Coordinate variables (CF required)
    time(obs): float64
        standard_name = "time"
        long_name = "activity start time (UTC)"
        units = "seconds since 1970-01-01"
        calendar = "standard"

    lon(obs): float32
        standard_name = "longitude"
        long_name = "ship longitude"
        units = "degrees_east"

    lat(obs): float32
        standard_name = "latitude"
        long_name = "ship latitude"
        units = "degrees_north"

    # Depth coordinates (available for point operations only)
    waterdepth(obs): float32
        long_name = "water depth at operation location"
        standard_name = "sea_floor_depth_below_sea_surface"
        units = "m"
        positive = "down"
        axis = "Z"
        _FillValue = -9999.0
        comment = "Available for point operations only, NaN for transits and line operations"

    operation_depth(obs): float32
        long_name = "target operation depth"
        standard_name = "depth"
        units = "m"
        positive = "down"
        axis = "Z"
        _FillValue = -9999.0
        comment = "Target depth for operation (e.g., CTD cast depth), NaN if not specified"

    # Start/end coordinates for line operations (NaN for other activities)
    start_latitude(obs): float32
        standard_name = "latitude"
        long_name = "line operation start latitude"
        units = "degrees_north"
        _FillValue = NaN

    start_longitude(obs): float32
        standard_name = "longitude"
        long_name = "line operation start longitude"
        units = "degrees_east"
        _FillValue = NaN

    end_latitude(obs): float32
        standard_name = "latitude"
        long_name = "line operation end latitude"
        units = "degrees_north"
        _FillValue = NaN

    end_longitude(obs): float32
        standard_name = "longitude"
        long_name = "line operation end longitude"
        units = "degrees_east"
        _FillValue = NaN

    # Schedule metadata
    name(obs): |S64
        long_name = "activity identifier"
        coordinates = "time latitude longitude waterdepth"

    category(obs): |S32
        long_name = "activity category"
        flag_values = "point_operation line_operation area_operation transit"
        coordinates = "time latitude longitude waterdepth"

    type(obs): |S64
        long_name = "specific type of activity"
        coordinates = "time latitude longitude waterdepth"

    action(obs): |S64
        long_name = "specific action or method"
        coordinates = "time latitude longitude waterdepth"

    comment(obs): |S256
        long_name = "activity comments"
        coordinates = "time latitude longitude waterdepth"

    leg_assignment(obs): |S32
        long_name = "cruise leg identifier"
        coordinates = "time latitude longitude waterdepth"

    duration(obs): float64
        long_name = "activity duration (actual: end_time - time)"
        units = "minute"
        coordinates = "time latitude longitude waterdepth"

    planned_duration(obs): float64
        long_name = "planned activity duration"
        units = "minute"
        coordinates = "time latitude longitude waterdepth"

    delay_start(obs): float32
        long_name = "delay before the operation starts"
        units = "minute"
        coordinates = "time latitude longitude water_depth"

    vessel_speed(obs): float32
        long_name = "vessel speed"
        units = "knot"
        coordinates = "time latitude longitude waterdepth"

    distance(obs): float64
        long_name = "activity distance"
        units = "nautical_mile"

    distance_to_next(obs): float64
        long_name = "distance to next waypoint"
        units = "nautical_mile"

    end_time(obs): float64
        standard_name = "time"
        long_name = "activity end time (UTC)"
        units = "seconds since 1970-01-01"

    # Global attributes
    :featureType = "trajectory"
    :title = "Ship Schedule: {cruise_name}"
    :institution = "Generated by CruisePlan software"
    :source = "Scheduler computation from YAML configuration"
    :Conventions = "CF-1.8"
    :cruise_name = "{cruise_name}"
    :total_duration_days = {total_days}
    :creation_date = "{iso_timestamp}"
    :comment = "Master file containing all cruise data - specialized files derived from this"


CF Alignment (not compliance)
=============================

1. **FeatureType Specification**: Each file must have exactly one `featureType` global attribute. The ``_schedule.nc`` file violates this because we have a mix of line and point operations.
2. **Coordinate Variables**: Must include proper `units`, `standard_name`, and `long_name` attributes
3. **Coordinates Attribute**: All data variables must include `coordinates = "time lat lon ..."` attribute
4. **Time Variables**: Use CF-standard time encoding (UTC, `seconds since 1970-01-01`)
5. **Global Attributes**: Include mandatory CF attributes (`Conventions`, `title`, `institution`, `featureType`)
6. **Standard Names**: Use CF standard name table for oceanographic variables
7. **Fill Values**: Use appropriate `_FillValue` for missing or optional data

Data Type Specifications
------------------------

- **Coordinates**: `float64` for time precision, `float32` for spatial coordinates
- **Time**: `float64` (seconds since the epoch, UTC)
- **Durations and distances**: `float64` (minutes, nautical miles); speeds `float32`
- **Strings**: Unicode strings with maximum length (`<U32`, `<U64`, `<U256`)





Cross-Reference System
----------------------

**Operation Linking:**

- Use operation `name` fields as primary keys between files
- Ship schedule `operation_file_ref` links to catalog files
- Maintain naming consistency across all files

**File Relationships:**

  - **Master file**: `{cruise_name}_schedule.nc` contains all cruise operations and timeline
  - **Filtered views**: Point/line/area files contain subsets filtered by operation category
  - **Common identifier**: `name` field serves as primary key across all files for the same operations



Using NetCDF Files
==================

The generated NetCDF files can be used with standard scientific tools:

**Python/xarray:**

.. code-block:: python

    import xarray as xr

    # Load the master schedule file
    ds = xr.open_dataset('cruise_name_schedule.nc')

    # View all variables
    print(ds)

    # Access station data
    stations = ds.where(ds.category == 'point_operation', drop=True)
    print(stations.name.values)

    # Plot ship track
    import matplotlib.pyplot as plt
    ds.plot.scatter(x='longitude', y='latitude', hue='category')

**MATLAB:**

.. code-block:: matlab

    % Read schedule data
    schedule = ncread('cruise_name_schedule.nc');
    times = ncread('cruise_name_schedule.nc', 'time');
    lats = ncread('cruise_name_schedule.nc', 'latitude');
    lons = ncread('cruise_name_schedule.nc', 'longitude');

    % Plot ship track
    plot(lons, lats, 'o-');

**R:**

.. code-block:: r

    library(ncdf4)

    # Open file
    nc <- nc_open('cruise_name_schedule.nc')

    # Read variables
    lats <- ncvar_get(nc, 'latitude')
    lons <- ncvar_get(nc, 'longitude')
    names <- ncvar_get(nc, 'name')

    # Plot
    plot(lons, lats, type='o')

This provides a complete foundation for CF-1.8 compliant NetCDF outputs that properly separate operation types by geometry while maintaining scientific data standards and enabling cross-file analysis.
