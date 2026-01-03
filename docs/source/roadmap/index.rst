Development Roadmap
===================

This document outlines the planned improvements and fixes for CruisePlan, organized by priority and implementation phases.

.. contents:: Table of Contents
   :local:
   :depth: 2

**Overview**

CruisePlan is actively developed with a focus on data integrity, operational realism, and user experience. Our roadmap prioritizes critical fixes that affect scientific accuracy, followed by feature enhancements that improve workflow efficiency.

**Release Strategy**: CruisePlan is in active development with significant breaking changes planned. We use semantic versioning with 0.x releases to signal ongoing API evolution while maintaining clear migration paths.

Current Development Status
--------------------------

- **v0.3.0**: ✅ **Released** - Breaking changes, deprecated features removed
- **v0.3.1+**: 🚧 **Planning Phase** - Unified operations model and enhanced station picker

v0.3.0: Current Status
----------------------

- **Target**: Version 0.3.0 (Breaking Changes Release)  
- **Status**: ✅ **Completed**
- **Focus**: Data accuracy and routing consistency

Deprecated Features Removal ✅
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Priority**: Critical - Breaking Changes  
- **Status**: Completed in v0.3.0

**CLI Commands Deprecated**:

- ``cruiseplan download`` → ``cruiseplan bathymetry``
- ``cruiseplan pandoi`` → ``cruiseplan pangaea`` (search mode)

**Parameter Standardization**:

- ``--output-file`` → ``--output`` + ``--output-dir`` (across commands)
- ``--bathymetry-*`` → ``--bathy-*`` (shorter parameter names)
- ``--coord-format`` removed (fixed to DMM format)

**YAML Configuration**:

- LegDefinition: ``sequence``, ``stations``, ``sections`` → ``activities`` (unified field)

Station Coordinate Access ✅
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Status**: Completed in v0.2.3
- **Implementation**: Direct ``station.latitude`` and ``station.longitude`` attributes  
- **Previous Pattern**: ``station.position.latitude`` (removed)

Area Operation Routing Fix ✅
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Status**: Completed in v0.2.x
- **Solution**: Proper ``get_entry_point()`` and ``get_exit_point()`` usage in scheduler

---- 

v0.3.1: Unified Operations Model
--------------------------------

- **Target**: Version 0.3.1
- **Status**: 🚧 **Planning Phase**  
- **Focus**: Unified operations architecture and enhanced capabilities

.. toctree::
   :maxdepth: 1
   :caption: Unified Operations & Core Architecture

   v0.3.1-unified-operations

This phase establishes a unified operations model where all point-based activities (stations, moorings, ports, waypoints) use consistent PointOperation infrastructure, eliminating special-case handling and enabling extensible operation types.

**Key Features (All in v0.3.1)**:

- Unified port and waypoint operations
- Extended operation types (WP2_NET, BONGO_NET, etc.) 
- Extensible operation parameters system

---- 

v0.4.x: Station Picker Enhancements
----------------------------------- 

- **Target**: Future versions (post-v0.3.1)
- **Status**: 🔮 **Concept Phase**
- **Focus**: Abstraction of station picking - separate graphical UI from data management

.. toctree::
   :maxdepth: 1
   :caption: Future Feature Concepts

   v0.4.0-station-picker-architecture
   v0.4.1-yaml-round-trip
   v0.4.2-text-input
   v0.4.3-batch-input

These documents contain detailed design concepts that may inform future development directions. The actual implementation approach and versioning will be determined  after v0.3.1 is released.

v0.5.0: NetCDF and YAML Enhancements
------------------------------------

- **Target**: Version 0.5.0 (Quality Release)  
- **Focus**: Return conversion from netCDF to YAML

NetCDF Generator Refactoring 🟠
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Priority**: Medium - Code Quality  
- **Breaking Change**: No (internal refactoring)

- **Planned Improvements**:
   - Centralized metadata system
   - Standardized variable definitions
   - Single source of truth for CF convention compliance

NetCDF to YAML Roundtrip Validation 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Medium - Data Integrity  

**Implementation Plan**:
- Create ``cruiseplan convert`` command
- Validate roundtrip fidelity: ``YAML → NetCDF → YAML``
- Ensure complete cruise information preservation

Complete netCDF Reference 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: High - User Experience  

**Planned Content**:
- Complete field reference tables for all definition types
- Operation type and action combination matrix
- Validation rules and constraints documentation

v0.6.0: Route optimization
--------------------------

- **Target**: Version 0.6.0 (Feature Release)
- **Focus**: Advanced routing algorithms and performance improvements
- **Priority**: High - Feature Enhancement
- **Planned Features**:

   - Implement TSP-based route optimization
   - User-configurable optimization parameters
   - Performance benchmarking and tuning

v1.0.0: Stable Release
----------------------

**Target**: Version 1.0.0 (Stable Release)  
**Focus**: Architectural improvements and performance optimization

Scheduler Architecture Refactoring 🟠
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Medium - Architecture & Maintainability  

**Current Issues**:
- Early conversion to dictionaries loses abstraction
- Manual coordinate extraction throughout scheduler
- Duplicated logic between operations and scheduler

**Proposed Solution**:
- Maintain operation objects throughout scheduling process
- Use object methods consistently for calculations
- Convert to dictionaries only at output stage

Testing Infrastructure Improvements 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Low - Infrastructure Enhancement  

**Planned Improvements**:
- Centralized test output directory configuration
- Standardized test isolation and cleanup
- Easier CI/CD integration

Implementation Notes
====================

CLI Design Pattern
------------------

All CLI commands follow a consistent pattern where CLI functions are thin wrappers around underlying API classes:

.. code-block:: python

   # CLI wrapper pattern
   def cli_command(config_file, **kwargs):
       """CLI wrapper for functionality."""
       from cruiseplan.api.command_api import CommandAPI
       api = CommandAPI(config_file)
       return api.run_command(**kwargs)

This ensures:
- Clean separation between CLI and business logic
- Testable API classes independent of CLI
- Consistent error handling and parameter validation
- Easy integration with other interfaces (GUI, web, etc.)

File Structure Evolution
------------------------

The roadmap introduces new modules following established patterns:

::

   cruiseplan/
   ├── core/                        # Core data models (existing)
   │   ├── operations.py             # PointOperation, LineOperation, etc.
   │   ├── validation.py             # Enhanced with unified operations
   │   └── operation_config.py       # NEW: Extensible operation registry
   ├── interactive/                  # NEW: Interactive tools
   │   ├── station_picker_api.py     # Main API class
   │   ├── data_manager.py           # Data orchestration
   │   ├── input_handlers.py         # Input method abstraction
   │   ├── yaml_context.py           # YAML round-trip management
   │   ├── text_input_widgets.py     # Text coordinate entry
   │   ├── batch_parser.py           # Multi-format batch import
   │   └── plancampanha_converter.py # PlanCampanha format support
   ├── outputs/                      # Enhanced output formats
   │   └── marine_facilities_planning.py  # NEW: MFP CSV export
   └── cli/                          # CLI wrappers (existing)
       └── stations.py               # Enhanced as thin wrapper

Risk Assessment
===============

**High Risk Items**:
- **Station picker architecture**: Major refactoring - needs phased implementation

**Medium Risk Items**:
- **YAML round-trip editing**: Complex state management - extensive testing required
- **Batch format conversion**: Data integrity during conversion - validation critical

**Low Risk Items**:
- **Text input widgets**: Self-contained UI components - minimal system impact
- **Output format additions**: Additive features - no existing functionality affected

**Mitigation Strategies**:
- Maintain backward compatibility throughout v0.3.x series
- Implement comprehensive test coverage for all new features
- Phased rollout with clear migration documentation
- Community feedback integration during planning phases

Contributing
============

This roadmap reflects current development priorities and is updated based on user feedback and development progress.

**Community Input**: We welcome feedback on priorities and feature requests through:

- **GitHub Issues**: https://github.com/ocean-uhh/cruiseplan/issues
- **Discussions**: Feature requests and technical discussions

**Development Process**: All major changes follow our contribution guidelines with code review, testing requirements, and documentation updates.

.. seealso::
   - :doc:`../developer_guide` for technical implementation details
   - `Contributing Guidelines <https://github.com/ocean-uhh/cruiseplan/blob/main/CONTRIBUTING.md>`_ for development workflow
   - `GitHub Repository <https://github.com/ocean-uhh/cruiseplan>`_ for latest development status