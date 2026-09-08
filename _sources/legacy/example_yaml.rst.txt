Example CruisePlan YAML Configuration
=====================================

This example shows a complete CruisePlan configuration with all major components: cruise metadata, points (CTD stations/moorings), lines (scientific transects), areas (survey boxes), and operational legs with port definitions.

.. code-block:: yaml

    # CruisePlan YAML Configuration
    # This example demonstrates the current v0.3.6+ configuration format

    # ======================================================================================
    # CRUISE METADATA
    # ======================================================================================
    cruise_name: Example_Cruise_2024
    description: Example oceanographic cruise in North Atlantic
    default_vessel_speed: 10.0
    start_date: '2024-06-15T08:00:00Z'

    # ======================================================================================
    # POINTS - CTD stations, moorings, sampling locations
    # ======================================================================================
    points:
      - name: STN_001
        latitude: 60.46082
        longitude: -57.33108
        operation_type: ctd
        action: profile
        operation_depth: 2000.0
        water_depth: 2930.7
        comment: Deep CTD station on continental slope
        
      - name: STN_002
        latitude: 59.03237
        longitude: -52.36839
        operation_type: ctd
        action: profile
        operation_depth: 3000.0
        water_depth: 3499.6
        comment: Abyssal plain station
        
      - name: MOOR_A
        latitude: 59.75000
        longitude: -54.80000
        operation_type: mooring
        action: deployment
        duration: 120.0
        comment: Autonomous sensor deployment

    # ======================================================================================
    # LINES - Scientific transects, ADCP surveys
    # ======================================================================================
    lines:
      - name: Transit_Survey
        operation_type: underway
        action: adcp
        vessel_speed: 8.0
        comment: ADCP transect between stations
        route:
          - latitude: 60.11164
            longitude: -56.20857
          - latitude: 57.41345
            longitude: -51.39357

    # ======================================================================================
    # AREAS - Survey boxes, multibeam mapping
    # ======================================================================================
    areas:
      - name: Seamount_Survey
        operation_type: survey
        action: bathymetry
        duration: 480.0
        comment: High-resolution multibeam mapping
        corners:
          - latitude: 59.20696
            longitude: -49.05993
          - latitude: 61.34964
            longitude: -54.17032
          - latitude: 57.04840
            longitude: -55.02697

    # ======================================================================================
    # OPERATIONAL LEGS - Defines cruise segments and routing
    # ======================================================================================
    legs:
      - name: North_Atlantic_Survey
        departure_port:
          name: Reykjavik
          display_name: Reykjavik, Iceland
          operation_type: port
          action: mob
          latitude: 64.1466
          longitude: -21.9426
        arrival_port:
          name: St_Johns
          display_name: St. John's, Newfoundland
          operation_type: port
          action: demob
          latitude: 47.5615
          longitude: -52.7126
        first_activity: STN_001
        last_activity: Seamount_Survey
        activities:
          - STN_001
          - Transit_Survey
          - MOOR_A
          - STN_002
          - Seamount_Survey
