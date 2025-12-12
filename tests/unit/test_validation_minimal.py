# tests/unit/test_validation_minimal.py
from pathlib import Path

import pytest

from cruiseplan.core.cruise import Cruise, ReferenceError

# Path to the sample file
SAMPLE_YAML = Path("tests/data/cruise_example.yaml")


def test_load_and_validate_cruise():
    """
    Happy Path: Load a valid YAML and ensure Pydantic
    validates types and structure correctly.
    """
    assert SAMPLE_YAML.exists(), "Please create the YAML file first!"

    cruise = Cruise(SAMPLE_YAML)

    # 1. Check Global Headers
    assert cruise.config.cruise_name == "NE_Atlantic_Test_2025"
    assert cruise.config.start_date == "2025-06-01T08:00:00"

    # 2. Check Anchor Parsing (String -> Float)
    assert cruise.config.departure_port.position.latitude == 64.1466

    # 3. Check Catalog Loading
    assert "STN_Start_01" in cruise.station_registry
    assert "M_End_01" in cruise.station_registry

    # 4. Check Schedule Resolution (The Hybrid Pattern)
    leg1 = cruise.config.legs[0]
    cluster = leg1.clusters[0]

    # The 'stations' list in the cluster should now be FULL OBJECTS, not strings
    resolved_stations = cluster.stations
    assert len(resolved_stations) == 4  # Updated to 4 since mooring moved to stations

    # Item 0: Was a reference "STN_Start_01" -> Should resolve to object
    assert resolved_stations[0].name == "STN_Start_01"
    assert resolved_stations[0].depth == 500.0

    # Item 2: Was inline "STN_Inline_OneOff" -> Should be object
    assert resolved_stations[2].name == "STN_Inline_OneOff"
    assert resolved_stations[2].position.latitude == 62.25

    # Item 3: Should be the mooring "M_End_01"
    assert resolved_stations[3].name == "M_End_01"
    assert resolved_stations[3].operation_type.value == "mooring"


def test_missing_reference_raises_error(tmp_path):
    """
    Edge Case: Ensure the system throws an error if we schedule
    a mooring that doesn't exist in the catalog.
    """
    
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
cruise_name: "Bad Cruise"
start_date: "2025-01-01T00:00:00"
default_vessel_speed: 10
default_distance_between_stations: 10
calculate_transfer_between_sections: false
calculate_depth_via_bathymetry: false
departure_port: {name: P1, position: "0,0"}
arrival_port: {name: P1, position: "0,0"}
first_station: "STN_Existing"
last_station: "STN_Existing"

stations:
  - name: STN_Existing
    operation_type: CTD
    action: profile
    position: "0,0"

legs:
  - name: Leg1
    stations:
      - "GHOST_STATION"  # <--- This does not exist in catalog
    """
    )

    with pytest.raises(ReferenceError) as exc:
        Cruise(bad_yaml)

    assert "GHOST_STATION" in str(exc.value)
    assert "not found in Catalog" in str(exc.value)
