Manual Testing and Verification
===============================

This document provides systematic manual testing procedures for validating CruisePlan functionality during development and before releases.

Overview
--------

Manual testing focuses on end-to-end workflow validation using standardized test fixtures. This ensures that:

- Core CLI commands work correctly together
- Complex cruise configurations are processed accurately  
- Output generation functions as expected
- Regression issues are caught before release

The testing approach uses the ``test_all_fixtures.py`` script combined with structured test cases to verify cruise planning workflows systematically.

Quick Start
-----------

To run all manual tests:

.. code-block:: bash

   # Run automated fixture testing
   python test_all_fixtures.py
   
   # Manual verification (optional)
   ls tests_output/fixtures/

Test Architecture
-----------------

Testing Strategy
~~~~~~~~~~~~~~~~

- **Automated Processing**: The ``test_all_fixtures.py`` script processes all ``tc*.yaml`` files automatically
- **Systematic Coverage**: Test cases progress from simple to complex scenarios
- **Workflow Validation**: Each test verifies the complete ``process`` → ``schedule`` workflow
- **Output Verification**: Generated files are checked for existence and basic validity

Test Fixtures Location
~~~~~~~~~~~~~~~~~~~~~~

- **Test Files**: ``tests/fixtures/tc*.yaml``
- **Output Directory**: ``tests_output/fixtures/``  
- **Test Script**: ``test_all_fixtures.py`` (repository root)

Test Case Definitions
---------------------

Test Case 1: Single Station (tc1_single.yaml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Verify basic maritime architecture with minimal complexity

**Configuration**:
- Single leg with one station
- Basic CTD operation
- Halifax → Cadiz routing

**Key Features Tested**:
- Port-to-port routing
- Single operation scheduling
- Basic timeline generation

**Expected Results**:
- ✅ Process command creates enriched YAML
- ✅ Schedule command generates timeline
- ✅ Port expansion creates ports catalog
- ✅ Schedule shows: port departure → station operations → port arrival

Test Case 2: Two Legs (tc2_two_legs.yaml)  
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Verify multi-leg routing with distinct operations

**Configuration**:
- Two legs with different departure/arrival ports
- CTD operation in first leg
- Mooring deployment in second leg

**Key Features Tested**:
- Multi-leg cruise structure
- Different operation types (CTD vs mooring)
- Inter-leg routing and timing

**Expected Results**:
- ✅ Each leg processed independently
- ✅ Correct port-to-port routing between legs
- ✅ Different operation types scheduled correctly

Test Case 3: Clusters (tc3_clusters.yaml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Verify cluster-based organization and operation sequencing

**Configuration**:
- Multiple legs with cluster-based activity organization
- Sequential strategy testing
- Duplicate station handling
- Different routing strategies

**Key Features Tested**:
- Cluster sequence processing
- Station duplication handling  
- Strategy-based optimization
- Complex leg routing

**Expected Results**:
- ✅ Clusters processed in defined order
- ✅ Sequential strategy maintains station order
- ✅ Duplicate stations handled correctly
- ✅ Multiple legs with different timings

Test Case 4: Mixed Operations (tc4_mixed_ops.yaml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Verify handling of diverse operation types

**Configuration**:
- CTD, mooring, and other operation types
- Mixed durations and activities
- Complex scheduling scenarios

**Key Features Tested**:
- Multiple operation types
- Duration calculations  
- Operation-specific parameters

Test Case 5: Sections (tc5_sections.yaml)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Verify section-based definitions and expansions

**Configuration**:
- Section definitions with waypoints
- Section expansion to individual stations

**Key Features Tested**:
- Section processing
- Waypoint expansion
- Linear station generation

Additional Test Files
~~~~~~~~~~~~~~~~~~~~~

**Mooring-focused**: ``tc1_mooring.yaml``  
- Mooring-specific operation testing
- Extended duration operations

Running Manual Tests
--------------------

Automated Testing
~~~~~~~~~~~~~~~~~

The primary method for running all tests:

.. code-block:: bash

   # From repository root
   python test_all_fixtures.py

This script:

1. **Finds all test fixtures**: Processes all ``tc*.yaml`` files in ``tests/fixtures/``
2. **Runs process command**: Creates enriched configurations with depths and coordinates  
3. **Runs schedule command**: Generates complete cruise schedules
4. **Validates outputs**: Checks that expected files are created
5. **Reports results**: Provides summary of successes and failures

Individual Test Execution
~~~~~~~~~~~~~~~~~~~~~~~~~

For detailed testing of specific scenarios:

.. code-block:: bash

   # Test a specific fixture
   cruiseplan process -c tests/fixtures/tc1_single.yaml --output-dir tests_output/manual
   cruiseplan schedule -c tests_output/manual/TC1_Single_Test_enriched.yaml --output-dir tests_output/manual
   
   # Verify outputs
   ls tests_output/manual/

Manual Verification Steps
~~~~~~~~~~~~~~~~~~~~~~~~~

After running automated tests, manually verify:

**1. File Generation**:

.. code-block:: bash

   ls tests_output/fixtures/
   # Should show:
   # - *_enriched.yaml files
   # - *_timeline.html files  
   # - *_timeline.csv files
   # - *_map.png files (if map generation enabled)

**2. Content Validation**:

Here, I am currently manually checking against offline calculations, especially for speeds and durations.

**3. Error Checking**:

.. code-block:: bash

   # Run with verbose output to check for warnings
   cruiseplan process -c tests/fixtures/tc1_single.yaml --verbose

Development Workflow Integration
-------------------------------

Pre-Commit Testing
~~~~~~~~~~~~~~~~~~

Before committing changes that affect core functionality:

.. code-block:: bash

   # Run full test suite
   python test_all_fixtures.py
   
   # Check for any new warnings or errors
   cruiseplan process -c tests/fixtures/tc3_clusters.yaml --verbose

Release Testing
~~~~~~~~~~~~~~~

Before creating releases:

1. **Run all automated tests**: ``python test_all_fixtures.py``
2. **Manual verification**: Check complex scenarios manually
3. **Performance testing**: Time execution of large configurations
4. **Documentation sync**: Ensure test results match documented behavior

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Missing Bathymetry Data**:

.. code-block:: bash

   # Download required bathymetry
   cruiseplan bathymetry --bathy-source etopo2022

**Output Directory Permissions**:

.. code-block:: bash

   # Ensure output directory is writable
   mkdir -p tests_output/fixtures
   chmod 755 tests_output/fixtures

**Fixture File Issues**:

.. code-block:: bash

   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('tests/fixtures/tc1_single.yaml'))"

Test Results Interpretation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Success Criteria**:
- All ``tc*.yaml`` files process without errors
- Enriched YAML files are created with expected structure
- Schedule generation completes for all fixtures
- Output files contain expected content

**Warning Evaluation**:
- Deprecation warnings are acceptable during transition periods
- Missing bathymetry warnings are expected without data downloads
- Port reference warnings are normal for test fixtures

**Failure Investigation**:
- Check recent code changes affecting failing components
- Verify test fixture validity  
- Review error messages for specific issues
- Test individual commands to isolate problems

Extending the Test Suite
-----------------------

Adding New Test Cases
~~~~~~~~~~~~~~~~~~~~

To add new manual test scenarios:

1. **Create fixture file**: ``tests/fixtures/tcX_description.yaml``
2. **Follow naming convention**: Use ``tc`` prefix with descriptive name
3. **Test automatically**: New files are included in ``test_all_fixtures.py`` automatically  
4. **Document purpose**: Add description to this document

Test Case Design Guidelines
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Progressive Complexity**:
- Start with simple scenarios
- Add one complexity dimension per test case
- Build on previous test case concepts

**Feature Coverage**:
- Each major feature should have dedicated test coverage
- Edge cases and error conditions should be represented
- Real-world scenarios should be included

**Maintainability**:
- Use clear, descriptive names
- Include comments explaining test purpose
- Keep configurations as simple as possible while testing target features

This manual testing framework ensures that CruisePlan maintains reliability and functionality across development cycles while providing clear procedures for validation and troubleshooting.