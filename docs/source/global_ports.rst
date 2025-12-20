.. _global_ports_reference:

=====================
Global Ports Reference
=====================

CruisePlan includes a comprehensive registry of global research ports that can be referenced directly in YAML configurations. Instead of manually specifying coordinates for common ports, you can use their predefined identifiers.

Usage in YAML
==============

Reference global ports directly by their identifier:

.. code-block:: yaml

   legs:
     - name: "Atlantic_Survey"
       departure_port: "port_reykjavik"  # Reference to global port
       arrival_port: "port_bremerhaven"  # Reference to global port
       # No need to specify coordinates - they're looked up automatically

Available Global Ports
=======================

.. list-table:: Global Port Registry
   :widths: 25 25 25 25
   :header-rows: 1

   * - **Port Name**
     - **Port Key**
     - **Latitude (°N)**
     - **Longitude (°E)**
   * - Reykjavik
     - port_reykjavik
     - 64.1466
     - -21.9426
   * - Nuuk
     - port_nuuk
     - 64.1836
     - -51.7214
   * - Tromsø
     - port_tromso
     - 69.6496
     - 18.9553
   * - Trondheim
     - port_trondheim
     - 63.4305
     - 10.3951
   * - Bergen
     - port_bergen
     - 60.3913
     - 5.3221
   * - Southampton
     - port_southampton
     - 50.9097
     - -1.4044
   * - Bremerhaven
     - port_bremerhaven
     - 53.5395
     - 8.5809
   * - Hamburg
     - port_hamburg
     - 53.5511
     - 9.9937
   * - Emden
     - port_emden
     - 53.3594
     - 7.2067
   * - Rostock
     - port_rostock
     - 54.0887
     - 12.1308
   * - Kiel
     - port_kiel
     - 54.3233
     - 10.1394
   * - Brest
     - port_brest
     - 48.3905
     - -4.4860
   * - Nice
     - port_nice
     - 43.7102
     - 7.2620
   * - Vigo
     - port_vigo
     - 42.2406
     - -8.7207
   * - Cadiz
     - port_cadiz
     - 36.5298
     - -6.2923
   * - Malaga
     - port_malaga
     - 36.7196
     - -4.4204
   * - Heraklion
     - port_heraklion
     - 35.3387
     - 25.1442
   * - Catania
     - port_catania
     - 37.5079
     - 15.0830
   * - Limassol
     - port_limassol
     - 34.6823
     - 33.0464
   * - Las Palmas
     - port_las_palmas
     - 28.1248
     - -15.4300
   * - Ponta Delgada
     - port_ponta_delgada
     - 37.7412
     - -25.6756
   * - Funchal
     - port_funchal
     - 32.6669
     - -16.9241
   * - Mindelo
     - port_mindelo
     - 16.8864
     - -24.9811
   * - Walvis Bay
     - port_walvis_bay
     - -22.9576
     - 14.5052
   * - Durban
     - port_durban
     - -29.8587
     - 31.0218
   * - Halifax
     - port_halifax
     - 44.6488
     - -63.5752
   * - St. John's
     - port_st_johns
     - 47.5615
     - -52.7126
   * - Vancouver
     - port_vancouver
     - 49.2827
     - -123.1207
   * - Woods Hole
     - port_woods_hole
     - 41.5265
     - -70.6712
   * - San Diego
     - port_san_diego
     - 32.7157
     - -117.1611
   * - Astoria
     - port_astoria
     - 46.1879
     - -123.8313
   * - Honolulu
     - port_honolulu
     - 21.3099
     - -157.8581
   * - Ensenada
     - port_ensenada
     - 31.8444
     - -116.6197
   * - Balboa
     - port_balboa
     - 8.9823
     - -79.5661
   * - Bridgetown
     - port_bridgetown
     - 13.1939
     - -59.6161
   * - Rio de Janeiro
     - port_rio_de_janeiro
     - -22.9068
     - -43.1729
   * - Fortaleza
     - port_fortaleza
     - -3.7172
     - -38.5433
   * - Belem
     - port_belem
     - -1.4558
     - -48.5044
   * - Recife
     - port_recife
     - -8.0476
     - -34.8770
   * - Antofagasta
     - port_antofagasta
     - -23.6509
     - -70.3975
   * - Port Louis
     - port_port_louis_mauritius
     - -20.1654
     - 57.5074
   * - La Reunion
     - port_la_reunion
     - -21.1151
     - 55.5364
   * - Port Louis
     - port_port_louis_seychelles
     - -4.6796
     - 55.5274
   * - Colombo
     - port_colombo
     - 6.9271
     - 79.8612
   * - Singapore
     - port_singapore
     - 1.3521
     - 103.8198
   * - Yokohama
     - port_yokohama
     - 35.4437
     - 139.6380
   * - Fremantle
     - port_fremantle
     - -32.0569
     - 115.7439
   * - Wellington
     - port_wellington
     - -41.2865
     - 174.7762
   * - Auckland
     - port_auckland
     - -36.8485
     - 174.7633
   * - Papeete
     - port_papeete
     - -17.5516
     - -149.5585

Programmatic Access
===================

For Python users, you can also access the port registry programmatically:

.. code-block:: python

   # Import the function to list available ports  
   from cruiseplan.utils.global_ports import get_available_ports
   
   # Get all available ports with descriptions
   ports = get_available_ports()
   
   # Display them
   for port_id, description in ports.items():
       print(f"{port_id}: {description}")

Regional Filtering
==================

To find ports in a specific geographic region:

.. code-block:: python

   # Get ports in a specific geographic region
   from cruiseplan.utils.global_ports import list_ports_in_region
   
   # Example: Get North Atlantic ports (50-70°N, -30 to 20°E)
   north_atlantic_ports = list_ports_in_region(
       min_lat=50.0, max_lat=70.0, 
       min_lon=-30.0, max_lon=20.0
   )

Custom Port Definitions
=======================

You can also define custom ports directly in your YAML configuration:

.. code-block:: yaml

   legs:
     - name: "Custom_Survey"
       departure_port:
         name: "Custom Research Station"
         latitude: 65.0
         longitude: -25.0
         timezone: "GMT+0"
         description: "Project-specific research station"

Adding Custom Ports at Runtime
===============================

For projects requiring additional ports not in the global registry:

.. code-block:: python

   from cruiseplan.utils.global_ports import add_custom_port
   
   # Add a custom port to the registry
   add_custom_port("port_my_station", {
       "name": "My Research Station",
       "display_name": "My Research Station, Location", 
       "latitude": 60.0,
       "longitude": -20.0,
       "timezone": "GMT+0",
       "description": "Custom research station for this cruise"
   })