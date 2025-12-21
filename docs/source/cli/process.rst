.. _subcommand-process:

``cruiseplan process``
======================

**Unified configuration processing command for enrichment, validation, and map generation.**

Synopsis
--------

.. code-block:: bash

   cruiseplan process -c CONFIG_FILE [options]

Description
-----------

The ``process`` command provides a unified interface for the complete configuration processing pipeline. It combines enrichment (adding missing data), validation (checking configuration integrity), and map generation into a single command with smart defaults and flexible control.

This command is designed to replace the need to run ``enrich``, ``validate``, and ``map`` separately, while still allowing granular control through various flags.

**Key Features:**

- **Smart defaults**: All enrichment options enabled by default
- **Flexible execution**: Control which steps run with ``--only-*`` and ``--no-*`` flags
- **Consistent output naming**: Use ``--output`` for base filename across all generated files
- **Modern parameter names**: Shorter ``--bathy-*`` parameters for reduced typing

Arguments
---------

**Required:**

.. option:: -c CONFIG_FILE, --config-file CONFIG_FILE

   Input YAML configuration file to process.

**Processing Mode Control (Mutually Exclusive):**

.. option:: --only-enrich

   Only run enrichment step. Skips validation and map generation.

.. option:: --only-validate  

   Only run validation step. Skips enrichment and map generation.

.. option:: --only-map

   Only run map generation step. Skips enrichment and validation.

**Processing Step Control (For Full Processing Mode):**

.. option:: --no-enrich

   Skip enrichment step in full processing mode.

.. option:: --no-validate

   Skip validation step in full processing mode.

.. option:: --no-map

   Skip map generation step in full processing mode.

**Enrichment Control (Smart Defaults):**

All enrichment operations are enabled by default. Use these flags to disable specific operations:

.. option:: --no-depths

   Skip adding missing depths from bathymetry data.

.. option:: --no-coords

   Skip adding formatted coordinate fields (DMM format).

.. option:: --no-sections

   Skip expanding CTD sections into individual stations.

.. option:: --no-ports

   Skip expanding global port references.

**Validation Options:**

.. option:: --no-depth-check

   Skip depth accuracy checking against bathymetry data.

.. option:: --strict

   Enable strict validation mode (treat warnings as errors).

.. option:: --tolerance FLOAT

   Depth difference tolerance in percent for validation (default: 10.0).

**Map Generation Options:**

These options only apply when map generation is enabled:

.. option:: --format FORMAT

   Map output formats: ``png``, ``kml``, ``all`` (default: ``all``).
   
   Cannot be used with ``--only-enrich`` or ``--only-validate``.

.. option:: --figsize WIDTH HEIGHT

   Figure size for PNG maps in inches (default: ``12 8``).
   
   Only applies when PNG format is selected.

**Output Options:**

.. option:: -o OUTPUT_DIR, --output-dir OUTPUT_DIR

   Output directory for all generated files (default: ``data``).

.. option:: --output BASENAME

   Base filename for outputs (without extension). Generates:
   
   - ``BASENAME_enriched.yaml`` (enriched configuration)
   - ``BASENAME_map.png`` (PNG map)
   - ``BASENAME_catalog.kml`` (KML catalog)

**Bathymetry Options:**

.. option:: --bathy-source {etopo2022,gebco2025}

   Bathymetry dataset to use (default: ``etopo2022``).

.. option:: --bathy-dir PATH

   Directory containing bathymetry data (default: ``data``).

.. option:: --bathy-stride INT

   Bathymetry contour stride for maps (default: ``10``).

**Legacy Parameters (Deprecated):**

.. option:: --bathymetry-source

   **[DEPRECATED]** Use ``--bathy-source`` instead.

.. option:: --bathymetry-dir

   **[DEPRECATED]** Use ``--bathy-dir`` instead.

.. option:: --bathymetry-stride

   **[DEPRECATED]** Use ``--bathy-stride`` instead.

.. option:: --coord-format

   **[DEPRECATED]** Coordinate format is now fixed to DMM.

**General Options:**

.. option:: --verbose, -v

   Enable verbose logging output.

.. option:: --quiet, -q

   Enable quiet mode (suppress non-essential output).

Flag Validation Rules
---------------------

The command validates flag combinations to prevent conflicts:

- **Cannot specify multiple** ``--only-*`` **flags together**
- **Cannot specify** ``--only-X`` **with** ``--no-X`` **for the same operation**
- **Cannot specify** ``--no-map`` **with** ``--format`` (map generation disabled but format specified)
- **Cannot specify** ``--only-enrich`` **with** ``--format`` (enrichment doesn't generate maps)  
- **Cannot specify** ``--only-validate`` **with** ``--format`` (validation doesn't generate maps)
- **figsize warning**: ``--figsize`` only applies when PNG format is selected

Processing Modes
-----------------

**Full Processing Mode (Default)**

Runs enrichment → validation → map generation with smart defaults:

.. code-block:: bash

   cruiseplan process -c cruise.yaml

Equivalent to:

.. code-block:: bash

   cruiseplan enrich -c cruise.yaml --add-depths --add-coords --expand-sections --expand-ports
   cruiseplan validate -c cruise_enriched.yaml --check-depths
   cruiseplan map -c cruise_enriched.yaml --format all

**Selective Step Control**

.. code-block:: bash

   # Skip map generation
   cruiseplan process -c cruise.yaml --no-map
   
   # Skip enrichment, only validate and map
   cruiseplan process -c cruise.yaml --no-enrich
   
   # Only enrichment with selective options
   cruiseplan process -c cruise.yaml --only-enrich --no-sections

**Exclusive Mode Control**

.. code-block:: bash

   # Only enrichment
   cruiseplan process -c cruise.yaml --only-enrich
   
   # Only validation (great for regenerating maps without changing YAML)
   cruiseplan process -c cruise.yaml --only-validate
   
   # Only map generation
   cruiseplan process -c cruise.yaml --only-map --format png --figsize 16 10

Examples
--------

**Basic Usage**

.. code-block:: bash

   # Full processing with smart defaults
   cruiseplan process -c cruise.yaml
   
   # With custom base filename
   cruiseplan process -c cruise.yaml --output expedition_2024
   
   # With high-resolution bathymetry
   cruiseplan process -c cruise.yaml --bathy-source gebco2025

**Selective Processing**

.. code-block:: bash

   # Only enrichment with custom options
   cruiseplan process -c cruise.yaml --only-enrich --no-sections --no-ports
   
   # Validation only (useful for checking existing enriched files)
   cruiseplan process -c cruise_enriched.yaml --only-validate --tolerance 5.0
   
   # Map generation only with custom settings
   cruiseplan process -c cruise_enriched.yaml --only-map --format png --figsize 20 12

**Full Processing with Customization**

.. code-block:: bash

   # Skip specific enrichment operations
   cruiseplan process -c cruise.yaml --no-sections --output final_cruise
   
   # Custom validation tolerance and KML only
   cruiseplan process -c cruise.yaml --tolerance 15.0 --format kml
   
   # No map generation, strict validation
   cruiseplan process -c cruise.yaml --no-map --strict

**Output Examples**

With ``--output expedition_2024``:

- Enriched config: ``data/expedition_2024_enriched.yaml``
- PNG map: ``data/expedition_2024_map.png``
- KML catalog: ``data/expedition_2024_catalog.kml``

Without ``--output`` (uses cruise name from config):

- Enriched config: ``data/My_Cruise_Name_enriched.yaml``
- PNG map: ``data/My_Cruise_Name_map.png``
- KML catalog: ``data/My_Cruise_Name_catalog.kml``

**Error Examples**

.. code-block:: bash

   # These will produce errors:
   cruiseplan process -c cruise.yaml --only-enrich --only-map    # Multiple --only-* flags
   cruiseplan process -c cruise.yaml --no-map --format png      # Conflicting map settings
   cruiseplan process -c cruise.yaml --only-validate --format all  # Validation doesn't generate maps

Comparison with Individual Commands
-----------------------------------

The ``process`` command replaces the need to run multiple commands:

**Before (Individual Commands):**

.. code-block:: bash

   cruiseplan enrich -c cruise.yaml --add-depths --add-coords --expand-sections --expand-ports
   cruiseplan validate -c cruise_enriched.yaml --check-depths --tolerance 10.0  
   cruiseplan map -c cruise_enriched.yaml --figsize 12 8 --format all

**After (Unified Command):**

.. code-block:: bash

   cruiseplan process -c cruise.yaml

**Benefits of Unified Command:**

- **Fewer commands to remember** and type
- **Consistent output naming** across all generated files
- **Smart defaults** eliminate need to specify common options
- **Automatic file chaining** (enriched file feeds into validation/maps)
- **Better error handling** with comprehensive flag validation
- **Modern parameter names** (``--bathy-*`` instead of ``--bathymetry-*``)

**When to Use Individual Commands:**

- **Learning the system**: Individual commands help understand each step
- **Debugging specific steps**: Isolate issues in enrichment, validation, or mapping
- **Integration with scripts**: Fine-grained control in automated workflows
- **Backward compatibility**: Existing scripts using individual commands

Notes
-----

- **Smart Defaults**: All enrichment operations are enabled by default (depths, coordinates, sections, ports)
- **File Chaining**: When running multiple steps, the enriched configuration automatically feeds into validation and mapping
- **Coordinate Format**: Fixed to DMM (degrees decimal minutes) format - no longer configurable
- **Legacy Support**: Deprecated parameters show warnings but still function for backward compatibility
- **Performance**: Map generation can be slow with large datasets - use ``--no-map`` to skip when only processing configuration

See Also
--------

- :doc:`enrich` - Individual enrichment command
- :doc:`validate` - Individual validation command  
- :doc:`map` - Individual map generation command
- :doc:`schedule` - Generate cruise timeline and outputs
- :doc:`../user_workflows` - Complete workflow examples