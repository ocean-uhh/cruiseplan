Development Roadmap
===================

This document outlines the planned improvements and fixes for CruisePlan, organized by priority and implementation phases.

.. contents:: Table of Contents
   :local:
   :depth: 2

**Overview**

CruisePlan is actively developed with a focus on data integrity, operational realism, and user experience. Our roadmap prioritizes critical fixes that affect scientific accuracy, followed by feature enhancements that improve workflow efficiency.

**Release Strategy**: CruisePlan is in active development with significant breaking changes planned. We use semantic versioning with 0.x releases to signal ongoing API evolution while maintaining clear migration paths.

Phase 1: Critical Data Integrity 
--------------------------------

**Target**: Version 0.3.0 (Breaking Changes Release)  
**Focus**: Data accuracy and routing consistency

Station Coordinate Access ✅
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Medium - Developer Experience  
**Status**: Completed in v0.2.x

**Implementation**: Direct ``station.latitude`` and ``station.longitude`` attributes  
**Previous Pattern**: ``station.position.latitude`` (removed)

**Benefits**: Improved code readability throughout calculation and enrichment functions

Area Operation Routing Fix 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: High - Routing Consistency  
**Breaking Change**: Potentially - Timeline output coordinates change

**Current Problem**:
The scheduler calculates artificial center points for area operations instead of using proper entry/exit points, causing routing inconsistencies.

**Impact**:
- Incorrect distance calculations between area operations and adjacent activities
- Timeline coordinates don't match actual operational flow
- Inconsistent with point and line operation routing logic

**Planned Solution**:
Replace center point calculations with proper ``get_entry_point()`` and ``get_exit_point()`` method usage in scheduler functions.

**Files Affected**: ``cruiseplan/calculators/scheduler.py``

Phase 2: Core Feature Completion
--------------------------------

**Target**: Version 0.4.0 (Feature Release)  
**Focus**: Missing functionality and operational realism

PNG Map Generation 🔴
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Critical - Major Missing Feature  
**Breaking Change**: No

**Current Gap**: 
No static map visualization capability for reports and documentation.

**Planned Implementation**:
- **Module**: ``cruiseplan/output/map_generator.py``
- **Features**: Bathymetric backgrounds, station markers, cruise tracks, publication-quality output
- **CLI Integration**: 
  
  .. code-block:: bash
  
     # Generate map as part of schedule output
     cruiseplan schedule --format png,html,latex
     
     # Standalone map generation  
     cruiseplan map -c cruise.yaml --output-file cruise_track.png

Enhanced Timing Controls 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: High - Operational Realism  
**Breaking Change**: No (additive only)

**Current Limitations**:
- No activity-level timing controls for operational constraints
- Missing weather delay allocation capabilities
- Limited buffer time options

**Planned Features**:

.. code-block:: yaml

   stations:
     - name: "Mooring_Deploy"
       duration: 240.0           # 4 hours deployment
       delay_start: 120.0        # Wait for daylight
       delay_end: 60.0          # Equipment settling time
       
   legs:
     - name: "Deep_Survey"
       buffer_time: 480.0        # 8 hours weather contingency

**Use Cases**:
- Daylight-dependent operations (mooring deployments)
- Equipment stabilization periods
- Weather delay planning

Complete YAML Reference 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: High - User Experience  
**Breaking Change**: No

**Current Gap**: 
Users lack comprehensive documentation of all YAML configuration options, leading to trial-and-error configuration.

**Planned Content**:
- Complete field reference tables for all definition types
- Operation type and action combination matrix
- Validation rules and constraints documentation
- Strategy and clustering options with examples

Phase 3: Code Quality and Polish
--------------------------------

**Target**: Version 0.5.0 (Quality Release)  
**Focus**: Maintainability and developer experience

NetCDF Generator Refactoring 🟠
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Medium - Code Quality  
**Breaking Change**: No (internal refactoring)

**Current Issues**:
- Code duplication in global attributes and variable definitions
- Inconsistent metadata handling across output types
- Difficult to maintain CF compliance

**Planned Improvements**:
- Centralized metadata system in ``cruiseplan/output/netcdf_metadata.py``
- Standardized variable definitions and coordinate templates
- Single source of truth for CF convention compliance

NetCDF to YAML Roundtrip Validation 🟡
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Medium - Data Integrity  
**Breaking Change**: No (additive)

**Requirement**: 
Implement bidirectional conversion between NetCDF output and YAML configuration to validate completeness of exported data.

**Implementation Plan**:
- Create ``cruiseplan netcdf-to-yaml`` command to reverse-engineer YAML from NetCDF
- Validate that all critical cruise planning information is preserved in NetCDF export
- Ensure roundtrip fidelity: ``YAML → NetCDF → YAML`` produces equivalent configurations
- Identify any data loss during NetCDF export process

**Use Cases**:
- **Data Integrity Validation**: Verify NetCDF exports contain complete cruise information
- **Configuration Recovery**: Reconstruct YAML configs from archived NetCDF files
- **Format Migration**: Enable users to recover configurations from legacy NetCDF outputs
- **Quality Assurance**: Automated testing of export completeness

**Success Criteria**: Generated YAML produces identical schedule and station information when re-processed


Phase 4: Architecture and Performance
--------------------------------------

**Target**: Version 1.0.0 (Stable Release)  
**Focus**: Architectural improvements and performance optimization

Scheduler Architecture Refactoring 🟠
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Priority**: Medium - Architecture & Maintainability  
**Breaking Change**: No (internal refactoring)

**Current Architecture Issues**:

The scheduler currently follows a two-phase conversion pattern that introduces unnecessary complexity:

1. **Early Conversion to Dictionaries**: Operation objects (PointOperation, LineOperation, AreaOperation) are converted to dictionary-based ActivityRecord structures early in the scheduling process
2. **Loss of Abstraction**: Once converted, the scheduler works with raw dictionaries containing fields like ``"lat"``, ``"lon"``, ``"start_lat"``, ``"end_lat"``, etc.
3. **Manual Coordinate Extraction**: Code must explicitly know dictionary field names and manually construct coordinate tuples throughout the scheduling logic
4. **Duplicated Logic**: Entry/exit point logic exists both in operation objects (``get_entry_point()``, ``get_exit_point()``) and separately in scheduler helper functions

**Problems This Creates**:

- **Maintenance Burden**: Changes to coordinate representation require updates in multiple places
- **Error-Prone**: Manual field access with string keys (``activity["start_lat"]``) is susceptible to typos and refactoring issues  
- **Loss of Type Safety**: Dictionary access provides no IDE support or type checking
- **Conceptual Gap**: Developers must understand both the operation object model AND the internal dictionary structure

**Proposed Solution**:

Maintain operation objects throughout the scheduling process:

- Keep operations as typed objects (PointOperation, LineOperation, etc.) during scheduling
- Use object methods (``get_entry_point()``, ``get_exit_point()``, ``calculate_duration()``) consistently
- Only convert to ActivityRecord dictionaries at the final output stage
- Leverage polymorphism for operation-specific behavior

**Implementation Approach**:

1. Create an enhanced ActivityRecord class that wraps operation objects
2. Add scheduling-specific attributes (start_time, end_time) to the wrapper
3. Use operation methods for all coordinate and duration calculations
4. Convert to dictionary format only for serialization/output

**Benefits**:

- **Single Source of Truth**: Coordinate access logic lives only in operation classes
- **Type Safety**: Full IDE support and type checking throughout scheduling
- **Cleaner Code**: Replace ``activity["start_lat"]`` with ``operation.get_entry_point()``
- **Easier Testing**: Mock operation objects instead of constructing complex dictionaries
- **Future-Proof**: Changes to operation structure don't ripple through scheduler code

**Migration Strategy**:

For backward compatibility, the refactoring can be done incrementally:

1. Current helper functions (``_get_activity_entry_position()``, etc.) provide an abstraction layer
2. Gradually replace dictionary creation with operation object retention
3. Update scheduler functions one at a time to work with objects
4. Final step: remove dictionary conversion until the output stage

This architectural improvement will significantly reduce code complexity and improve maintainability while maintaining full backward compatibility with existing cruise configurations and output formats.


Risk Assessment
----------------

**High Risk Items**:
- **Depth semantics**: Affects all duration calculations - requires comprehensive testing
- **Breaking changes**: User migration support critical for adoption

**Medium Risk Items**:
- **Area coordinates**: Affects inter-operation routing - validate against existing cruise plans
- **PNG generation**: New dependency requirements - ensure installation compatibility

**Mitigation Strategies**:
- Extensive test coverage for critical changes
- Staged rollout with release candidates
- Clear migration documentation and examples
- Backward compatibility maintenance

Contributing
------------

This roadmap reflects current development priorities.

**Community Input**: We welcome feedback on priorities and feature requests through:

- **GitHub Issues**: https://github.com/ocean-uhh/cruiseplan/issues
- **Discussions**: Feature requests and technical discussions

**Development Process**: All major changes follow our contribution guidelines with code review, testing requirements, and documentation updates.

.. seealso::
   - :doc:`developer_guide` for technical implementation details
   - `Contributing Guidelines <https://github.com/ocean-uhh/cruiseplan/blob/main/CONTRIBUTING.md>`_ for development workflow
   - `GitHub Repository <https://github.com/ocean-uhh/cruiseplan>`_ for latest development status