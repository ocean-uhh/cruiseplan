.. _output-kml:

==========
KML Output
==========

KML format provides geographic visualization compatible with Google Earth, Google Maps, and other geographic information systems. The output focuses on positional data and cruise tracks for visualization and integration purposes.

.. note::
   KML output is only available from the **map command** (``cruiseplan map --format kml``). For timeline-based visualization, use :doc:`png` output from the schedule command.

Purpose and Use Cases
======================

**Primary Uses**:
  - Google Earth visualization and exploration
  - Geographic information system (GIS) integration
  - Public outreach and communication
  - Navigation system import and reference

**Target Audiences**:
  - Public and educational outreach coordinators
  - Navigation officers and marine pilots
  - GIS analysts and cartographers
  - Scientific communication specialists

KML Structure and Features
===========================

Generated KML files contain hierarchical geographic data organized for optimal visualization:

**1. Cruise Overview Folder**
  - Expedition summary and metadata
  - Total cruise statistics and objectives
  - Contact information and data sources
  - Temporal span and geographic coverage

**2. Station Points Folder**
  - Individual operation locations with detailed popups
  - Color-coded markers by operation type
  - Hierarchical organization by leg and cluster
  - Interactive information balloons

**3. Cruise Track Folder**
  - Vessel route lines between operations
  - Scientific transit routes with waypoints
  - Navigation transit direct connections
  - Time-stamped track segments

**4. Area Operations Folder**
  - Polygonal survey areas with boundaries
  - Area center points for routing reference
  - Coverage calculations and operational zones
  - Scientific objectives per area

Geographic Visualization
========================

Station Markers and Styling
----------------------------

**Operation Type Styling**:

.. list-table:: KML Station Markers
   :widths: 25 25 50
   :header-rows: 1

   * - **Operation Type**
   - **Icon Style**
     - **Description**
   * - CTD Stations
     - Blue circle icons
     - Size proportional to cast depth
   * - Mooring Operations
     - Yellow star icons
     - Different icons for deploy/recover
   * - Calibration Sites
     - Green triangle icons
     - Equipment-specific symbols
   * - Water Sampling
     - Purple square icons
     - Sample type indicators

**Information Popups**:
  Each station marker includes detailed HTML popup content:

.. code-block:: html

   <![CDATA[
   <h3>CTD Station: CTD_001</h3>
   <table border="1">
   <tr><td><b>Coordinates:</b></td><td>62°20.0'N, 028°10.0'W</td></tr>
   <tr><td><b>Water Depth:</b></td><td>2,847 meters</td></tr>
   <tr><td><b>Operation Type:</b></td><td>CTD Profile</td></tr>
   <tr><td><b>Estimated Duration:</b></td><td>2.8 hours</td></tr>
   <tr><td><b>Start Time:</b></td><td>2024-07-01 14:12 UTC</td></tr>
   <tr><td><b>Scientific Objective:</b></td><td>Deep water mass analysis</td></tr>
   </table>
   ]]>

Track Lines and Routes
----------------------

**Cruise Track Visualization**:
  - **Scientific Transits**: Blue lines with waypoint markers
  - **Navigation Transits**: Gray dashed lines for efficiency
  - **Port Approaches**: Green lines for departure/arrival
  - **Area Surveys**: Red boundary lines with filled polygons

**Route Complexity Indication**:
  - Line thickness proportional to route complexity
  - Waypoint density visualization
  - Speed variation color coding
  - Time stamp annotations along tracks

Area Operations Display
-----------------------

**Polygon Representation**:

.. code-block:: xml

   <Polygon>
     <extrude>0</extrude>
     <altitudeMode>clampToGround</altitudeMode>
     <outerBoundaryIs>
       <LinearRing>
         <coordinates>
           -40.0,50.0,0 -40.0,51.0,0 -39.0,51.0,0 -39.0,50.0,0 -40.0,50.0,0
         </coordinates>
       </LinearRing>
     </outerBoundaryIs>
   </Polygon>

**Area Styling**:
  - Semi-transparent fill colors by operation type
  - Distinct border colors and line styles
  - Center point markers for routing reference
  - Area calculation labels and statistics

Time-Based Animation
====================

Temporal KML Features
---------------------

**Time Stamps**:
  - Operation start and end times embedded
  - Time slider compatibility in Google Earth
  - Chronological operation sequence
  - Duration-based visibility controls

**Animation Controls**:

.. code-block:: xml

   <TimeSpan>
     <begin>2024-07-01T14:12:00Z</begin>
     <end>2024-07-01T17:00:00Z</end>
   </TimeSpan>

**Temporal Visualization**:
  - Progressive route revelation over time
  - Operation sequence animation
  - Real-time expedition tracking capability
  - Historical expedition replay

KML Structure Example
=====================

Complete File Organization
--------------------------

.. code-block:: xml

   <?xml version="1.0" encoding="UTF-8"?>
   <kml xmlns="http://www.opengis.net/kml/2.2">
     <Document>
       <name>Arctic Survey 2024 - Cruise Schedule</name>
       <description>
         <![CDATA[
         Oceanographic research expedition to the North Atlantic.
         Generated by CruisePlan software.
         Total duration: 15.2 days at sea
         ]]>
       </description>
       
       <!-- Cruise metadata -->
       <ExtendedData>
         <Data name="cruise_name">
           <value>Arctic Survey 2024</value>
         </Data>
         <Data name="total_operations">
           <value>52</value>
         </Data>
         <Data name="total_distance_km">
           <value>3195</value>
         </Data>
       </ExtendedData>
       
       <!-- Station markers folder -->
       <Folder>
         <name>Station Operations</name>
         <Placemark>
           <name>CTD_001</name>
           <description>CTD Profile at North Atlantic Station</description>
           <Point>
             <coordinates>-28.167,62.333,0</coordinates>
           </Point>
         </Placemark>
       </Folder>
       
       <!-- Cruise track folder -->
       <Folder>
         <name>Vessel Track</name>
         <Placemark>
           <name>Transit to CTD_001</name>
           <LineString>
             <coordinates>
               -21.9426,64.1466,0 -28.167,62.333,0
             </coordinates>
           </LineString>
         </Placemark>
       </Folder>
       
     </Document>
   </kml>

Style Definitions
-----------------

**Marker Styles**:

.. code-block:: xml

   <Style id="ctd_station">
     <IconStyle>
       <Icon>
         <href>http://maps.google.com/mapfiles/kml/shapes/sailing.png</href>
       </Icon>
       <scale>1.2</scale>
       <color>ff0000ff</color>
     </IconStyle>
     <LabelStyle>
       <scale>0.8</scale>
       <color>ff000000</color>
     </LabelStyle>
   </Style>

**Line Styles**:

.. code-block:: xml

   <Style id="cruise_track">
     <LineStyle>
       <color>ff0000ff</color>
       <width>3</width>
     </LineStyle>
   </Style>

Integration Applications
========================

Google Earth Integration
-------------------------

**Viewing Features**:
  - 3D terrain visualization with bathymetric context
  - Time slider for expedition timeline animation
  - Layer control for selective data display
  - Measurement tools for distance and area calculations

**Advanced Capabilities**:
  - Historical imagery for site comparison
  - Weather overlay integration
  - Ocean current visualization
  - Collaborative annotation and markup

GIS System Import
-----------------

**Compatible Software**:
  - QGIS for advanced spatial analysis
  - ArcGIS for professional cartography
  - Marine navigation systems (ECDIS)
  - Web mapping platforms (OpenLayers, Leaflet)

**Data Conversion**:
  - Shapefile export for GIS analysis
  - GPX conversion for GPS systems
  - GeoJSON format for web applications
  - CSV extraction for database import

Navigation System Usage
=======================

Marine Navigation Integration
-----------------------------

**Waypoint Lists**:
  - Extract station coordinates for GPS systems
  - Format for Electronic Chart Display (ECDIS) import
  - Generate backup navigation references
  - Create approach and departure routes

**Route Planning**:
  - Import vessel tracks for autopilot systems
  - Provide reference tracks for manual navigation
  - Generate contingency route alternatives
  - Document safe approach parameters

**Safety and Compliance**:
  - Export for voyage data recorder (VDR) systems
  - Provide official position records
  - Document planned vs actual tracks
  - Support maritime safety investigations

Customization and Extensions
============================

Content Customization
----------------------

**Information Density**:
  - Detailed view for scientific analysis
  - Simplified view for public outreach
  - Operational view for vessel crews
  - Summary view for management overview

**Visual Styling**:
  - Institution-specific color schemes
  - Logo and branding integration
  - Custom marker icons and symbols
  - Thematic styling by research objectives

**Language Localization**:
  - Multi-language popup content
  - Translated operation descriptions
  - Local coordinate system references
  - Cultural and regional formatting

Advanced KML Features
---------------------

**Network Links**:
  - Real-time updates from vessel tracking
  - Dynamic content from cruise databases
  - Collaborative expedition sharing
  - Integration with live data feeds

**Balloon Styling**:
  - Custom HTML popup layouts
  - Interactive charts and graphs
  - Image galleries for station documentation
  - Video links for operational procedures

Quality Assurance
=================

KML Validation
--------------

**Standard Compliance**:
  - OGC KML 2.2 specification compliance
  - Google Earth compatibility testing
  - Web browser rendering verification
  - Mobile application compatibility

**Data Integrity**:
  - Coordinate accuracy validation
  - Time stamp consistency checking
  - Cross-reference verification
  - Metadata completeness assessment

**Performance Optimization**:
  - File size management for large expeditions
  - Loading time optimization
  - Memory usage considerations
  - Network bandwidth efficiency

Best Practices
==============

File Organization
-----------------

**Naming Conventions**:
  - Descriptive filenames with expedition identifiers
  - Version numbering for updates
  - Date stamps for temporal reference
  - Geographic identifiers for regional focus

**Distribution Methods**:
  - Web hosting for public access
  - Secure sharing for confidential expeditions
  - Version control for collaborative development
  - Archive management for historical reference

Usage Guidelines
---------------

**For Public Outreach**:
  - Simplified content suitable for general audiences
  - Educational context and scientific background
  - Visual appeal and engagement features
  - Clear contact information and data sources

**For Operational Use**:
  - Focus on essential navigation information
  - Minimize visual clutter and complexity
  - Provide accurate timing and position data
  - Include safety and contingency information

The KML output format provides versatile geographic visualization capabilities that serve diverse audiences from scientific researchers to the general public, while maintaining compatibility with standard geographic information systems and navigation tools.