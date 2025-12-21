.. _subcommand-pandoi:

======
pandoi
======

.. warning::
   **DEPRECATED**: This command is deprecated and will be removed in v0.3.0. 
   Please use ``cruiseplan pangaea`` search mode instead: 
   ``cruiseplan pangaea "query" --lat MIN MAX --lon MIN MAX``

Search PANGAEA datasets by query terms and geographic bounding box, generating a DOI list for subsequent use with the ``pangaea`` command.

Usage
-----

.. code-block:: bash

    usage: cruiseplan pandoi [-h] [--lat MIN MAX] [--lon MIN MAX] [--limit LIMIT] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--verbose] query

Arguments
---------

.. list-table::
   :widths: 30 70

   * - ``query``
     - **Required.** Search query string (e.g., 'CTD', 'temperature', 'Arctic Ocean').

Options
-------

.. list-table::
   :widths: 30 70

   * - ``--lat MIN MAX``
     - Latitude bounds (e.g., ``--lat 50 70``).
   * - ``--lon MIN MAX``
     - Longitude bounds (e.g., ``--lon -60 -30``).
   * - ``--limit LIMIT``
     - Maximum number of results to return (default: ``10``).
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path (overrides ``-o``/``--output-dir``).
   * - ``--verbose, -v``
     - Enable verbose logging.

Description
-----------

This command searches the PANGAEA database for oceanographic datasets using text queries and optional geographic constraints. It outputs a text file containing DOI identifiers that can be used with the ``cruiseplan pangaea`` command to fetch and process the actual datasets.

Query Examples
--------------

.. list-table::
   :widths: 40 60
   
   * - **Query Type**
     - **Example**
   * - Instrument/Method
     - ``"CTD"``, ``"XBT"``, ``"ADCP"``, ``"Rosette"``
   * - Parameter
     - ``"temperature"``, ``"salinity"``, ``"oxygen"``, ``"nutrients"``
   * - Geographic Region
     - ``"Arctic Ocean"``, ``"North Atlantic"``, ``"Mediterranean Sea"``
   * - Campaign/Vessel
     - ``"Polarstern"``, ``"PS122"``, ``"Maria S. Merian"``
   * - Combined Terms
     - ``"CTD Arctic Ocean"``, ``"temperature Polarstern"``

Finding Query Terms
-------------------

PANGAEA uses flexible text search, so you can be generous with your search terms. For discovery of relevant terms:

- Visit https://www.pangaea.de/?t=Oceans to browse oceanographic datasets
- Check the left sidebar filters for common parameter names, regions, and methods
- PANGAEA doesn't enforce strict controlled vocabularies, so variations work:
  
  - ``"CTD"`` or ``"CTD/Rosette"`` or ``"conductivity temperature depth"``
  - ``"temp"`` or ``"temperature"`` or ``"sea water temperature"``
  - ``"North Atlantic"`` or ``"Nordic Seas"`` or ``"Labrador Sea"``

Search Strategy Tips
--------------------

- **Start broad**: Use general terms like ``"CTD"`` or ``"temperature"`` first
- **Refine geographically**: Add geographic bounds with ``--lat`` and ``--lon`` 
- **Combine terms**: ``"CTD temperature Arctic"`` finds datasets with all terms
- **Try variations**: If ``"nutrients"`` returns few results, try ``"nitrate"`` or ``"phosphate"``
- **Use quotes**: For exact phrases like ``"sea surface temperature"``
- **Iterate**: Start with ``--limit 10``, review results, then adjust terms and increase limit
- **Be generous**: PANGAEA's search is forgiving - ``"temp"`` will find temperature datasets

Geographic Bounds Format
-------------------------

The ``--lat`` and ``--lon`` parameters specify geographic search bounds:

- ``--lat MIN MAX``: Latitude bounds from MIN to MAX degrees (-90 to 90)
- ``--lon MIN MAX``: Longitude bounds supporting two coordinate systems:
  
  - **-180 to 180 format**: West longitudes negative, East positive (standard)
  - **0 to 360 format**: All longitudes positive, 0° = Prime Meridian, 180° = Date Line
  - **Cannot mix formats**: Both values must use the same system

- Examples: 
  
  - ``--lat 50 60 --lon -50 -40`` covers 50°N-60°N, 50°W-40°W (standard format)
  - ``--lat 50 60 --lon 310 320`` covers 50°N-60°N, 50°W-40°W (0-360 format)
  - ``--lat 50 60 --lon 350 10`` covers 50°N-60°N, crossing 0° meridian (valid in 0-360)

Examples
--------

.. code-block:: bash

    # Search for CTD data globally (saves to data/ directory)
    $ cruiseplan pandoi "CTD"
    
    # Search for temperature data in the North Atlantic
    $ cruiseplan pandoi "temperature" --lat 50 70 --lon -50 -10 --limit 25
    
    # Broad search with multiple terms
    $ cruiseplan pandoi "CTD temperature salinity" --lat 60 80 --lon -40 20 --limit 30
    
    # Search for Polarstern expedition data with custom output file
    $ cruiseplan pandoi "PS122" --output-file data/polarstern_ps122_dois.txt
    
    # Try different term variations if first search is too narrow
    $ cruiseplan pandoi "nutrients nitrate phosphate" --lat 45 65 --lon -60 -20
    
    # Detailed search with verbose output
    $ cruiseplan pandoi "Arctic Ocean CTD" --lat 70 90 --lon -180 180 --limit 50 --verbose

Workflow Integration
--------------------

The ``pandoi`` command is designed to work with the ``pangaea`` command:

.. code-block:: bash

    # Step 1: Search for datasets and save DOI list to specific file
    $ cruiseplan pandoi "CTD temperature" --lat 60 70 --lon -50 -30 --output-file data/arctic_ctd_dois.txt
    
    # Step 2: Fetch and process the datasets
    $ cruiseplan pangaea data/arctic_ctd_dois.txt --output-dir data/
    
    # Step 3: Use in station planning
    $ cruiseplan stations --pangaea-file data/arctic_ctd_dois_pangaea_data.pkl