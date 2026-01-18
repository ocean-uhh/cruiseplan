=================
Output Formats
=================

CruisePlan generates outputs in multiple formats for different use cases.

Timeline Formats
================

HTML Schedule
-------------

**File**: ``{cruise_name}_schedule.html``

HTML timeline with:

- Operation details and timing
- Detailed scheduling information
- Expandable sections for each leg
- Responsive design for mobile/desktop

**Best for**: Sharing with collaborators, project presentations

NetCDF Data File
----------------

**File**: ``{cruise_name}_schedule.nc``

CF-1.8 compliant NetCDF with:

- Station coordinates and metadata
- Operation timing and durations
- Cruise track as trajectory data
- Compatible with scientific analysis tools

**Best for**: Data analysis, archival storage

CSV Schedule
------------

**File**: ``{cruise_name}_schedule.csv``

Tabular format with columns:

- Operation name, type, start/end times
- Coordinates and water depths
- Duration and distance information

**Best for**: Spreadsheet analysis, custom processing

Map Outputs
===========

PNG Maps
--------

**Files**: 
- ``{cruise_name}_map.png`` - Station overview
- ``{cruise_name}_bathymetry_map.png`` - With depth contours

Static maps showing:

- Station locations and labels
- Bathymetry contours (optional)
- Cruise track connections
- Scale bar and coordinate grid

**Best for**: Reports, presentations, printing

KML/KMZ Files
-------------

**File**: ``{cruise_name}.kml``

Google Earth format with:

- 3D visualization of stations
- Bathymetry-draped seafloor
- Interactive station information
- Cruise track animation

**Best for**: 3D visualization, Google Earth

Document Formats
================

LaTeX/PDF Report
----------------

**Files**: 
- ``{cruise_name}_cruise_plan.tex`` - LaTeX source
- ``{cruise_name}_cruise_plan.pdf`` - Compiled PDF

Professional cruise planning document with:

- Executive summary and metadata
- Detailed station tables
- Maps and bathymetry profiles
- Timeline and logistics summary

**Best for**: Formal proposals, ship time applications

Working Files
=============

YAML Configuration
------------------

**Files**:
- ``stations.yaml`` - Initial configuration from station picker
- ``{cruise_name}_enriched.yaml`` - Enriched configuration with depths and validation

Human-readable configuration containing:

- All station definitions and metadata
- Cruise logistics and timing parameters
- Comments and documentation fields
- Complete specification for reproducibility

**Best for**: Configuration management, version control

Pickle Files
------------

**Files**:
- ``{cruise_name}_stations.pkl`` - Processed station data
- ``historical_stations.pkl`` - PANGAEA historical data

Binary data files for:

- Fast loading of complex datasets
- Preserving exact coordinate precision
- Efficient storage of large station catalogs

**Best for**: Internal processing, caching

Output Selection
================

Choose formats based on your needs:

**For Proposals**:
.. code-block:: bash

   cruiseplan schedule cruise.yaml --formats latex,html

**For Analysis**:  
.. code-block:: bash

   cruiseplan schedule cruise.yaml --formats netcdf,csv

**For Visualization**:
.. code-block:: bash

   cruiseplan schedule cruise.yaml --formats html,kml

**Everything**:
.. code-block:: bash

   cruiseplan schedule cruise.yaml  # All formats

File Naming
===========

All outputs use consistent naming:

- Base name from YAML cruise_name field
- Format-specific extensions
- No spaces (replaced with underscores)
- Timestamps preserved in metadata

Example for ``cruise_name: "North Atlantic Survey 2025"``:

- ``North_Atlantic_Survey_2025_timeline.html``
- ``North_Atlantic_Survey_2025.nc``
- ``North_Atlantic_Survey_2025_map.png``

For detailed format specifications, see the individual format pages below:

.. toctree::
   :maxdepth: 1
   :caption: Detailed Format Specifications
   
   ../output/html
   ../output/netcdf
   ../output/csv
   ../output/png
   ../output/kml
   ../output/latex