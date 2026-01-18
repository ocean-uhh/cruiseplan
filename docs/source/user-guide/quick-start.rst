===========
Quick Start
===========

Get started with CruisePlan in under 5 minutes.

Installation
============

.. code-block:: bash

   pip install cruiseplan
   
   # OR install from source
   pip install git+https://github.com/ocean-uhh/cruiseplan.git

Your First Cruise
==================

Create a simple 3-station CTD cruise in the North Atlantic:

.. code-block:: bash

   # 1. Download bathymetry data (one-time setup, ~500MB)
   cruiseplan bathymetry
   
   # 2. Create stations interactively (saves to data/ directory)
   cruiseplan stations --lat 60 62 --lon -30 -25
   
   # 3. Process the configuration (enriches and validates)
   cruiseplan process -c data/stations.yaml
   
   # 4. Generate timeline and outputs
   cruiseplan schedule -c data/{cruise_name}_enriched.yaml

That's it! You now have:

- **YAML configuration**: ``data/{cruise_name}_enriched.yaml``
- **Cruise map**: ``data/{cruise_name}_map.png``
- **Schedule**: ``data/{cruise_name}_schedule.html``

Interactive Station Placement
=============================

Step 2 opens an interactive map. Use these controls:

- **p**: Place point stations (CTD casts)
- **l**: Draw line transects 
- **a**: Define area surveys
- **u**: Undo last action
- **y**: Save and exit

**Tip**: Start with just 2-3 stations to learn the workflow.

What You Get
============

CruisePlan generates comprehensive outputs:

- **Maps**: PNG maps and KML files for Google Earth
- **Timelines**: HTML/LaTeX summaries or NetCDF/CSV complete schedules
- **LaTeX**: Professional proposal documents

Next Steps
==========

- **Edit your YAML**: Customize operation types, durations, and metadata
- **Add historical context**: Use ``cruiseplan pangaea`` to find existing stations
- **Multiple formats**: Generate different output types with ``cruiseplan schedule``

See :doc:`workflows` for detailed examples and :doc:`yaml-basics` for configuration options.