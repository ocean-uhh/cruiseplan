Usage Overview
==============

This page provides a high-level overview of how to use CruisePlan for oceanographic cruise planning. For detailed step-by-step instructions, see the linked workflow guides below.

Three-Phase Workflow
--------------------

CruisePlan follows a systematic three-phase approach to cruise planning:

Phase 1: Data Preparation
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal**: Gather *external* datasets needed for planning

* **Download bathymetry**: ``cruiseplan download`` - Acquire global depth data (ETOPO/GEBCO)
* **Search historical data**: ``cruiseplan pandoi`` - Find relevant PANGAEA datasets by query and region  
* **Process historical data**: ``cruiseplan pangaea`` - Convert DOI lists into usable station databases

This phase provides the foundational data layers for informed station placement.

Phase 2: Cruise Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal**: Define your cruise plan and validate the configuration

* **Interactive planning**: ``cruiseplan stations`` - Place stations on interactive maps with bathymetry
* **Enrich metadata**: ``cruiseplan enrich`` - Add depths, coordinates, and expand sections automatically
* **Validate setup**: ``cruiseplan validate`` - Check configuration for errors and consistency
* **Generate maps**: ``cruiseplan map`` - Create standalone PNG maps from configuration

This phase creates and refines your complete cruise configuration file.

Within this phase, you should also expect to do some **manual editing** of the generated YAML configuration to choose operation types and actions, and to organise the leg/cluster structure of activities.

Phase 3: Schedule Generation  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Goal**: Generate final cruise timeline and professional outputs

* **Create schedule**: ``cruiseplan schedule`` - Calculate timing and generate deliverables
* **Multiple formats**: HTML summaries, LaTeX tables, NetCDF files, KML exports, PNG maps

This phase produces documentation in various formats for cruise proposals (png figure + latex tables) and onward manipulation in python (netCDF).

YAML Configuration Structure
-----------------------------

CruisePlan uses YAML files as the central configuration format. These files contain two main components:

**Catalog Section**
  Defines all available elements:
  
  * ``stations``: Geographic locations with operation types (CTD, mooring, etc.)
  * ``transits``: Movement between locations or survey patterns
  * ``areas``: Defined working regions
  * ``legs``: Groupings of operations for scheduling

**Schedule Section**  
  Defines the sequence:
  
  * ``legs``: Ordered list of operations to perform
  * ``clusters``: Strategic groupings and routing optimizations

The catalog acts as a "library" of all possible operations, while the schedule determines which ones to execute and in what order. This separation allows flexible reuse of station definitions across different cruise scenarios.

For complete YAML syntax and options, see the :doc:`yaml_reference`.

How to Get Started
------------------

Get started immediately with:

.. code-block:: bash

   cruiseplan --help

This displays all available commands with brief descriptions, helping you choose the right tool for your planning needs.

Or choose your preferred approach and follow the guides:

**Command Line Workflows**

Follow the comprehensive :doc:`User Workflows (CLI) <user_workflows>` guide for three different planning scenarios:
  
  * **Basic Planning**: Simple workflow without historical data
  * **PANGAEA-Enhanced**: Incorporating historical oceanographic data
  * **Configuration-Only**: Processing existing YAML files

**Jupyter Notebook Approach**  
  CruisePlan provides a Python API for programmatic usage:
  
  * Interactive Python API usage
  * Data analysis integration
  * Programmatic configuration generation
  * Custom visualization examples

**Configuration Reference**
  Consult the :doc:`yaml_reference` for:
  
  * Complete field documentation
  * Validation rules and constraints  
  * Example configurations
  * Best practices


