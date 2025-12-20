.. _subcommand-stations:

========
stations
========

Launch the interactive graphical interface for planning stations and transects with optional PANGAEA data background.

Usage
-----

.. code-block:: bash

    usage: cruiseplan stations [-h] [-p PANGAEA_FILE] [--lat MIN MAX] [--lon MIN MAX] [-o OUTPUT_DIR] [--output-file OUTPUT_FILE] [--bathymetry-source {etopo2022,gebco2025}] [--high-resolution] [--overwrite]

Options
-------

.. list-table::
   :widths: 30 70

   * - ``-p PANGAEA_FILE, --pangaea-file PANGAEA_FILE``
     - Path to the pickled PANGAEA campaigns file.
   * - ``--lat MIN MAX``
     - Latitude bounds for the map view (default: ``45 70``).
   * - ``--lon MIN MAX``
     - Longitude bounds for the map view (default: ``-65 -5``).
   * - ``-o OUTPUT_DIR, --output-dir OUTPUT_DIR``
     - Output directory for the generated station YAML (default: ``data``).
   * - ``--output-file OUTPUT_FILE``
     - Specific output file path for the generated YAML.
   * - ``--bathymetry-source {etopo2022,gebco2025}``
     - Bathymetry dataset to use for depth lookups (default: ``etopo2022``).
   * - ``--high-resolution``
     - Use full resolution bathymetry in the interactive interface (slower but more detailed).
   * - ``--overwrite``
     - Overwrite existing output file without prompting.

.. warning::
   **Performance Notice:** The combination of ``--bathymetry-source gebco2025`` with ``--high-resolution`` can be very slow for interactive use. GEBCO 2025 is a high-resolution dataset (~7.5GB) and processing it without downsampling creates significant lag during station placement and map interaction.
   
   **Recommended workflow:**
   - Use ``--bathymetry-source etopo2022`` (default) for initial interactive planning
   - Reserve GEBCO 2025 high-resolution for final detailed work only
   - Consider standard resolution (default) for GEBCO 2025 during interactive sessions