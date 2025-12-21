.. _subcommand-pangaea:

=======
pangaea
=======

Unified PANGAEA data command that supports both searching PANGAEA datasets and processing DOI files. Automatically detects workflow mode based on input.

Usage
-----

.. code-block:: bash

    # Search mode: Search PANGAEA database and process results
    usage: cruiseplan pangaea [-h] [--lat MIN MAX] [--lon MIN MAX] [--limit LIMIT] 
                              [-o OUTPUT_DIR] [--output OUTPUT] [--rate-limit RATE_LIMIT] 
                              [--merge-campaigns] [--verbose] query
    
    # DOI file mode: Process existing DOI list file
    usage: cruiseplan pangaea [-h] [-o OUTPUT_DIR] [--output OUTPUT] [--rate-limit RATE_LIMIT] 
                              [--merge-campaigns] doi_file

Arguments
---------

.. list-table::
   :widths: 30 70

   * - ``query_or_file``
     - **Required.** Search query (e.g., 'CTD temperature') OR path to DOI file.

Options
-------

.. list-table::
   :widths: 30 70

   * - ``--lat MIN MAX``
     - **Search mode only.** Latitude bounds (e.g., ``--lat 50 70``).
   * - ``--lon MIN MAX``
     - **Search mode only.** Longitude bounds (e.g., ``--lon -60 -30``).
   * - ``--limit LIMIT``
     - **Search mode only.** Maximum search results (default: ``10``).
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data/``).
   * - ``--output OUTPUT``
     - Base filename for outputs (default: derived from query/DOI filename).
   * - ``--rate-limit RATE_LIMIT``
     - API request rate limit (requests per second, default: ``1.0``).
   * - ``--merge-campaigns``
     - Merge campaigns with the same name.
   * - ``--verbose, -v``
     - **Search mode only.** Enable verbose logging.

Workflow Modes
---------------

The command automatically detects the workflow mode:

- **Search Mode**: If the input looks like a search query and geographic bounds are provided
- **DOI File Mode**: If the input is an existing .txt file with DOI identifiers

Search Mode Examples
--------------------

.. code-block:: bash

    # Basic search with geographic bounds
    $ cruiseplan pangaea "CTD temperature" --lat 50 70 --lon -60 -20
    
    # Search with custom output directory and base filename
    $ cruiseplan pangaea "Arctic Ocean CTD" --lat 70 90 --lon -180 180 --limit 25 -o data/cruise1/ --output arctic_data
    
    # Combined search terms with rate limiting
    $ cruiseplan pangaea "Polarstern PS122" --lat 80 90 --lon -180 180 --rate-limit 0.5 --verbose

DOI File Mode Examples
----------------------

.. code-block:: bash

    # Process existing DOI file
    $ cruiseplan pangaea data/arctic_dois.txt
    
    # Process with custom output directory and base filename
    $ cruiseplan pangaea dois.txt -o data/processed/ --output processed_stations --merge-campaigns
    
    # Process with rate limiting for large DOI lists
    $ cruiseplan pangaea large_doi_list.txt --rate-limit 0.5

Output Files
------------

Both modes generate output files using the base filename:

- ``{output}_dois.txt``: DOI list (search mode only)
- ``{output}_stations.pkl``: Pickled station database for use with ``cruiseplan stations``

Complete Workflow Example
-------------------------

.. code-block:: bash

    # Complete PANGAEA-enhanced workflow
    $ cruiseplan pangaea "CTD temperature" --lat 60 70 --lon -50 -30 --output north_atlantic
    $ cruiseplan stations --pangaea-file north_atlantic_stations.pkl --lat 60 70 --lon -50 -30
    
    # Process existing DOI file workflow  
    $ cruiseplan pangaea existing_dois.txt --output processed_data
    $ cruiseplan stations --pangaea-file processed_data_stations.pkl