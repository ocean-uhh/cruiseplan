.. _subcommand-pangaea:

=======
pangaea
=======

Processes a list of PANGAEA DOIs, aggregates coordinates by campaign, and outputs a searchable dataset.

Usage
-----

.. code-block:: bash

    usage: cruiseplan pangaea [-h] [-o OUTPUT_DIR] [--rate-limit RATE_LIMIT] [--merge-campaigns] [--output-file OUTPUT_FILE] doi_file

Arguments
---------

.. list-table::
   :widths: 30 70

   * - ``doi_file``
     - **Required.** Text file with PANGAEA DOIs (one per line).

Options
-------

.. list-table::
   :widths: 30 70

   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory (default: ``data/``).
   * - ``--rate-limit RATE_LIMIT``
     - API request rate limit (requests per second, default: ``1.0``).
   * - ``--merge-campaigns``
     - Merge campaigns with the same name.
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path for the pickled dataset.

Examples
--------

.. code-block:: bash

    # Process DOIs from file with default settings
    $ cruiseplan pangaea dois.txt

    # Process with custom output directory and rate limiting
    $ cruiseplan pangaea dois.txt -o data/pangaea --rate-limit 0.5

    # Merge campaigns and save to specific file
    $ cruiseplan pangaea dois.txt --merge-campaigns --output-file pangaea_stations.pkl

The command will create a pickled file containing processed PANGAEA station data that can be used with the ``cruiseplan stations`` command for interactive station planning.