Manual Testing and Verification
===============================

This document provides systematic manual testing for validating CruisePlan functionality during development and before releases.  It relies on standardised test fixtures to ensure that: 

- Core CLI commands work correctly together
- Complex cruise configurations are processed accurately  
- Output generation functions as expected

The testing approach uses the ``test_all_fixtures.py`` script combined with structured test cases to verify cruise planning workflows systematically.

Run Tests
---------

**Test Fixtures Location:**

- **Test Files**: ``tests/fixtures/tc*.yaml``
- **Output Directory**: ``tests_output/fixtures/``  
- **Test Script**: ``test_all_fixtures.py`` (repository root)

To run all manual tests:

.. code-block:: bash

   # Run automated fixture testing
   python test_all_fixtures.py
   
   # Verify outputs
   ls tests_output/fixtures/

This generates **54** output files (9 per test case in `tests/fixtures/tc*.yaml`).

- **Automated Processing**: The ``test_all_fixtures.py`` script processes all ``tc*.yaml`` files automatically
- **Systematic Coverage**: Test cases progress from simple to complex scenarios
- **Workflow Validation**: Each test verifies the complete ``process`` → ``schedule`` workflow
- **Output Verification**: Generated files then need to be *manually* checked for existence and validity.  Specific verification steps are provided per test case below.


Test Case 1: Single Station (tc1_single.yaml)
---------------------------------------------

**Purpose**: Verify basic architecture with minimal complexity (enables manual checks)

**Configuration**:

- Single leg with one CTD station
- Check YAML enrichment and output generation
- Check CTD duration calculation


**TC1_Single_Test_enriched.yaml**
.................................

.. |uncheck| raw:: html

    <input type="checkbox">

1. |uncheck| Verify that in `STN_001` the coordinates were enriched as:

.. code-block:: yaml

   coordinates_ddm: 45 00.00'N, 045 00.00'W

2. |uncheck| Verify that the port got expanded, including

.. code-block:: yaml

   ports:
      - name: port_cadiz
        latitude: 36.5298
        longitude: -6.2923
        display_name: Cadiz, Spain

3. |uncheck| Verify that the defaults got added, including

.. code-block:: yaml

   turnaround_time: 30.0
   ctd_descent_rate: 1.0
   ctd_ascent_rate: 1.0


**TC1_Single_Test_schedule.html**
..................................

4. |uncheck| Verify that the CTD takes **2.1 hours**, based on a 30 minute "turnaround_time" (the default from constants.py) and a 2850m CTD (using mocked bathymetry) from `DEFAULT_CTD_RATE_M_S` in `constants.py`, which is 47.5 minutes down and 47.5 minutes up, plus 30 minutes turnaround = 125 minutes or 2.1 hours.

5. |uncheck| Verify that the total cruise duration is **262.4 hours / 10.9 days**.

6. |uncheck| Compare with the `HTML schedule output <_static/fixtures/TC1_Single_Test_schedule.html>`_ to verify CTD timing calculations.

**TC1_Single_Test_schedule.csv**
.................................

7. |uncheck| Verify that the first row, second to last entry is **-34.51** (Longitude minutes for -63.5752 degrees)

.. code-block:: csv
   
   activity,label,operation_action,start_time,end_time,Transit dist [nm],Vessel speed [kt],Duration [hrs],Depth [m],Lat [deg],Lon [deg],Lat [deg_rounded],Lat [min],Lon [deg_rounded],Lon [min],leg_name
   Port,port_halifax,Port mob,1970-01-01T00:00:00,1970-01-01T00:00:00,0.0,0,0.0,0,44.6488,-63.5752,44,38.93,-63,-34.51,Leg_Single
   Transit,Transit to STN_001,Transit,1970-01-01T00:00:00,1970-01-04T06:57:00,789.6,10.0,79.0,,44.6488,-63.5752,44,38.93,-63,-34.51,Leg_Single
   Station,STN_001,Station profile,1970-01-04T06:57:00,1970-01-04T09:02:00,0.0,0,2.1,2850,45.0,-45.0,45,0.0,-45,-0.0,Leg_Single
   Transit,Transit to port_cadiz,Transit,1970-01-04T09:02:00,1970-01-11T22:21:00,1813.1,10.0,181.3,,45.0,-45.0,45,0.0,-45,-0.0,Leg_Single
   Port,port_cadiz,Port mob,1970-01-11T22:21:00,1970-01-11T22:21:00,0.0,0,0.0,0,36.5298,-6.2923,36,31.79,-6,-17.54,Leg_Single


**TC1_Single_Test_stations.tex**
.................................

8. |uncheck| Verify that the LaTeX station table includes water depth **2850** 
9. |uncheck| Verify the Latex-formated coordinate includes **45$^\circ$00.00'N**:

.. code-block:: latex

   Station & STN-001 & 45$^\circ$00.00'N, 045$^\circ$00.00'W & 2850 \\

**TC1_Single_Test_work_days.tex**
.................................

10. |uncheck| Verify that the LaTeX work days table includes total cruise duration of **2.1** operation hours and **260.3** transit hours:

.. code-block:: latex

   \textbf{Total duration} & & \textbf{2.1} & \textbf{260.3} \\

**Figures _map.png and _schedule.png**
....................................

11. |uncheck| Verify that the map PNG shows no ports `TC1_Single_Test_map.png <_static/fixtures/TC1_Single_Test_map.png>`_
12. |uncheck| Verify that the schedule PNG shows ports `TC1_Single_Test_schedule.png <_static/fixtures/TC1_Single_Test_schedule.png>`_

**KML: TC1_Single_Test_catalog.kml**
.................................

13. |uncheck| Verify that the KML file includes the station details

.. figure:: _static/fixtures/TC1_Single_Test_catalog_kml.png
   :alt: KML Output Screenshot
   :width: 400px

   KML output viewed in Google Earth showing station location and details.

----

Test Case 2: Two Legs (tc2_two_legs.yaml)  
-------------------------------------------

**Purpose**: Verify multi-leg routing with distinct operations

**Configuration**:

- Two legs with different departure/arrival ports
- CTD operation in first leg
- Mooring deployment in second leg

**Manual verification**:

1. |uncheck| Verify that the `*.html` shows total duration of **1440.4 hours** (because the default mooring time is **999.0 hours**)

2. |uncheck| Verify that two legs are generated with **277.2 hours** in Leg 1 and **1163.2 hours** in Leg 2.

3. |uncheck| Verify that the `_schedule.png` matches `TC2_TwoLegs_Test_schedule.png <_static/fixtures/TC2_TwoLegs_Test_schedule.png>`_

4. |uncheck| Verify that the `_work_days.tex` has a total duration with operations of **1000.0** hours and transit duration of **440.4** hours.

----

Test Case 3: Clusters (tc3_clusters.yaml)
-------------------------------------------

**Purpose**: Verify cluster-based organization and operation sequencing

**Configuration**:

- Multiple legs with cluster-based activity organization
- Sequential strategy testing
- Duplicate station handling
- Different routing strategies


**Manual verification**:

Check the `*.html` output for each routing strategy:

1. |uncheck| Verify that the `*.html` shows total duration of **754.2 hours**.

2. |uncheck| Verify that the average speed for the transit is **10.3 kts** 

3. |uncheck| Verify that `Leg_Survey_Faster` is faster than `Leg_Survey` by **20.8 hours** due to a default leg speed of 12 kts instead of 10 kts.

4. |uncheck| Verify that `3e. Leg_Survey_Duplicate4` repeats `STN_001`, adding a total of 0.5 hours to the duration (making it **128.4** hours).

5. |uncheck| Verify that the `3f. Leg_Survey_Reorder` does the stations in order of `STN_004` then `STN_003` then `STN_002` then `STN_001`.

See the HTML output `TC3_Clusters_Test_schedule.html <_static/fixtures/TC3_Clusters_Test_schedule.html>`_ for reference.

----

Test Case 4: Mixed Operations (tc4_mixed_ops.yaml)
-------------------------------------------------

**Purpose**: Verify handling of diverse operation types

**Configuration**:

- CTD, mooring, and other operation types
- Mixed durations and activities
- Complex scheduling scenarios

**Manual verification**:

1. |uncheck| Verify that the `*_map.png` shows a shaded area, a line and a station.  Compare to `TC4_Mixed_Test_map.png <_static/fixtures/TC4_Mixed_Test_map.png>`_

2. |uncheck| Verify that the `*_stations.tex` shows 3 lines with:

.. code-block:: latex

   Station & STN-001 & 45$^\circ$00.00'N, 050$^\circ$00.00'W & 58 \\
   Line (line) & ADCP-Survey & (46$^\circ$00.00'N, 050$^\circ$00.00'W) to (46$^\circ$00.00'N, 050$^\circ$00.00'W) & N/A \\
   Area (None) & Area-01 & Center: 47$^\circ$30.00'N, 050$^\circ$30.00'W & Variable \\

Compare with the `TC4_Mixed_Test_schedule.html <_static/fixtures/TC4_Mixed_Test_schedule.html>`_ for coordinates and depths.

3. |uncheck| Verify that the `*_schedule.html` shows total duration of **287.2 hours**.

4. |uncheck| Verify that the total cruise shows **3 operations** and the `3a. Mixed_Survey` leg shows **3 operations**.

5. |uncheck| Verify that the Transit to ADCP survey in `3a. Mixed_Survey` shows a distance of **60.0 nm** taking **6.0 hours**.

6. |uncheck| Verify that the ADCP survey shows an entry position of **46.0000, -50.0000** and an exit position of **47.0000, -50.0000**.

7. |uncheck| Verify that the `*_work_days.tex` shows total operation duration of **24.2** hours and transit duration of **258.5** hours.

.. code-block:: latex

   \textbf{Total duration} & & \textbf{24.2} & \textbf{258.5} \\

----

Test Case 5: Sections (tc5_sections.yaml)
----------------------------------------- 

**Purpose**: Verify section-based definitions and expansions

**Configuration**:

- Section expansion to individual stations

1. |uncheck| Verify that the `_enriched.yaml` contains individual stations instead of a section:

.. code-block:: yaml

   points:
   -  #  expanded by cruiseplan enrich --expand-sections
      name: SEC_001_Stn001
      coordinates_ddm: 45 00.00'N, 050 00.00'W
      water_depth: 58.0
      operation_type: CTD
      action: profile
      latitude: 45.0
      longitude: -50.0
      comment: Station 1/14 on SEC_001 section
      duration: 120.0

2. |uncheck| Verify that the `_map.png` shows all 14 stations from the section `TC5_Sections_Test_map.png <_static/fixtures/TC5_Sections_Test_map.png>`_

3. |uncheck| Verify that the `_schedule.html` shows a station spacing of **11.2 nm**.

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