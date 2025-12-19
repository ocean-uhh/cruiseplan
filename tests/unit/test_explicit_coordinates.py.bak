# tests/unit/test_explicit_coordinates.py
from cruiseplan.core.cruise import Cruise


def test_fully_explicit_yaml(tmp_path):
    """
    Verifies that EVERY coordinate field in the system can be
    parsed from explicit 'latitude'/'longitude' keys,
    instead of comma-separated strings.
    """
    explicit_yaml = tmp_path / "explicit_full.yaml"
    explicit_yaml.write_text(
        """
cruise_name: "Explicit Coordinates Test"
start_date: "2025-06-01"
default_vessel_speed: 10
default_distance_between_stations: 20
calculate_transfer_between_sections: true
calculate_depth_via_bathymetry: true

# 1. PORTS (Top Level explicit)
departure_port:
  name: "Port A"
  latitude: 50.0
  longitude: -10.0

arrival_port:
  name: "Port B"
  latitude: 52.0
  longitude: -8.0

first_station: "S1"
last_station: "M1"

# 2. STATIONS (unified schema with operations)
stations:
  - name: S1
    operation_type: CTD
    action: profile
    latitude: 60.0
    longitude: -20.0
    depth: 1000

  - name: M1
    operation_type: mooring
    action: recovery
    latitude: 61.0
    longitude: -19.0
    duration: 120

# 4. TRANSITS (List of explicit objects)
transits:
  - name: "Detailed_Route"
    route:
      - latitude: 55.0
        longitude: -15.0
      - latitude: 56.0
        longitude: -14.0

legs:
  - name: "Leg 1"

    # 5. SECTIONS (Nested explicit start/end)
    sections:
      - name: "Explicit_Section"
        start:
          latitude: 62.0
          longitude: -18.0
        end:
          latitude: 63.0
          longitude: -17.0

    # 6. GENERATORS (Nested explicit start/end)
    clusters:
      - name: "Generator_Cluster"
        generate_transect:
          id_pattern: "Gen_{:02d}"
          spacing: 10
          start:
            latitude: 64.0
            longitude: -16.0
          end:
            latitude: 65.0
            longitude: -15.0
    """
    )

    # Attempt to load
    cruise = Cruise(explicit_yaml)

    # --- VERIFICATION ---

    # 1. Port
    assert cruise.config.departure_port.position.latitude == 50.0

    # 2. Station
    s1 = cruise.station_registry["S1"]
    assert s1.position.latitude == 60.0
    assert s1.position.longitude == -20.0

    # 3. Mooring (now in stations registry)
    m1 = cruise.station_registry["M1"]
    assert m1.position.latitude == 61.0

    # 4. Transit
    t1 = cruise.transit_registry["Detailed_Route"]
    assert t1.route[0].latitude == 55.0
    assert t1.route[1].longitude == -14.0

    # 5. Section (Inside Leg)
    section = cruise.config.legs[0].sections[0]
    assert section.start.latitude == 62.0
    assert section.end.longitude == -17.0

    # 6. Generator (Inside Cluster)
    gen = cruise.config.legs[0].clusters[0].generate_transect
    assert gen.start.latitude == 64.0
    assert gen.end.longitude == -15.0
