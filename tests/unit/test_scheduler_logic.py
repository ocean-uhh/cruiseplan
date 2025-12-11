from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Import the core scheduling function
from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation import CruiseConfig, GeoPoint, PortDefinition

# --- Fixtures and Mocks ---


# Mock Config - duplicate from test_calculators
@pytest.fixture
def mock_config():
    return CruiseConfig(
        cruise_name="Test",
        start_date="2025-01-01T08:00:00",
        default_vessel_speed=10,
        default_distance_between_stations=20,
        calculate_transfer_between_sections=True,
        calculate_depth_via_bathymetry=False,
        departure_port=PortDefinition(name="A", position="0,0"),
        arrival_port=PortDefinition(name="B", position="0,0"),
        first_station="S1",
        last_station="S1",
        legs=[],
        ctd_descent_rate=1.0,  # 60 m/min
        ctd_ascent_rate=1.0,  # 60 m/min
        turnaround_time=10,  # min
        # Day Window
        day_start_hour=8,
        day_end_hour=20,
    )


# Patching the external calculation functions to control test output
@pytest.fixture
def mock_calculations():
    """Mocks haversine_distance and DurationCalculator methods."""
    with (
        # Haversine distance mock (returns 111.12 km = 60 nm for simplicity)
        patch(
            "cruiseplan.calculators.scheduler.haversine_distance", return_value=111.12
        ) as mock_dist,
        # Duration Calculator mock (returns 120 minutes = 2 hours per station)
        patch(
            "cruiseplan.calculators.scheduler.DurationCalculator"
        ) as MockDurationCalcClass,
    ):
        # Configure the mock instance returned by the class constructor
        mock_duration_calc = MockDurationCalcClass.return_value
        # Ensure CTD time calculation returns 120 minutes
        mock_duration_calc.calculate_ctd_time.return_value = 120.0

        yield mock_dist, mock_duration_calc


# --- Configuration Fixtures (Based on your YAML files) ---


# Helper to create a GeoPoint structure for Ports
def create_mock_port(lat, lon, name):
    port_mock = MagicMock()
    port_mock.name = name
    # The scheduler expects config.port.position.latitude
    port_mock.position = GeoPoint(latitude=lat, longitude=lon)
    return port_mock


@pytest.fixture
def config_simple():
    """Returns a CruiseConfig object loaded from cruise_simple.yaml (2 stations)."""
    # NOTE: You must load the YAML and convert it to a CruiseConfig object.
    # For this test, we create a simplified mock config object that contains
    # only the necessary attributes for the scheduler to run.

    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "Simple_Test_Cruise_2028"
    mock_config.default_vessel_speed = 10.0  # kt
    mock_config.default_distance_between_stations = 111.0  # km
    mock_config.start_date = "2028-06-01"
    mock_config.start_time = "08:00"

    # Ports and Anchors
    mock_config.departure_port = create_mock_port(47.57, -52.69, "St. Johns")
    mock_config.arrival_port = create_mock_port(64.14, -21.94, "Reykjavik")
    mock_config.first_station = "STN_001"
    mock_config.last_station = "STN_002"

    # Station Catalog - properly mock objects with name attribute
    station1 = MagicMock()
    station1.name = "STN_001"
    station1.position = GeoPoint(latitude=50.0, longitude=-40.0)
    station1.depth = 1000.0
    station1.duration = 0.0
    # Add operation_type for the unified schema
    mock_operation_type1 = MagicMock()
    mock_operation_type1.value = "CTD"
    station1.operation_type = mock_operation_type1

    station2 = MagicMock()
    station2.name = "STN_002"
    station2.position = GeoPoint(latitude=51.0, longitude=-40.0)
    station2.depth = 1000.0
    station2.duration = 0.0
    # Add operation_type for the unified schema
    mock_operation_type2 = MagicMock()
    mock_operation_type2.value = "CTD"
    station2.operation_type = mock_operation_type2

    mock_config.stations = [station1, station2]
    # IMPORTANT: The scheduler uses getattr(match, 'depth', 0.0) which is fine for mocks.
    # The fix relies on MagicMock(name=...) ensuring the name attribute exists.
    mock_config.transits = []

    # Legs (Sequential order is essential here)
    leg_mock = MagicMock()
    leg_mock.stations = ["STN_001", "STN_002"]
    leg_mock.sequence = None  # Ensure sequence is None so it falls back to stations
    mock_config.legs = [leg_mock]

    return mock_config


# --- Test Cases ---
def test_timeline_handles_mooring_manual_duration(mock_calculations):
    """Tests that manual duration for mooring operations takes precedence."""
    mock_dist, mock_duration_calc = mock_calculations

    # Setup: Create a minimal config with a mooring using manual duration
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.default_vessel_speed = 10.0
    mock_config.start_date = "2028-06-01"
    mock_config.start_time = "08:00"

    # Ports (FIXED)
    mock_config.departure_port = create_mock_port(47.0, -50.0, "Start Port")
    mock_config.arrival_port = create_mock_port(47.0, -50.0, "End Port")

    mock_config.first_station = "MOOR_A"
    mock_config.last_station = "MOOR_A"

    # Mooring definition with 180 minutes (3 hours) manual duration
    mock_mooring = MagicMock()
    mock_mooring.name = "MOOR_A"
    mock_mooring.position = GeoPoint(latitude=50.0, longitude=-40.0)
    mock_mooring.depth = 2800.0
    mock_mooring.action = "deploy"
    mock_mooring.duration = 180.0
    # Add operation_type for the unified schema
    mock_operation_type = MagicMock()
    mock_operation_type.value = "mooring"
    mock_mooring.operation_type = mock_operation_type

    mock_config.stations = [mock_mooring]  # Moorings are now in stations list
    mock_config.transits = []

    leg_mock = MagicMock()
    leg_mock.stations = ["MOOR_A"]
    leg_mock.sequence = None
    mock_config.legs = [leg_mock]

    # --- ACT ---
    timeline = generate_timeline(mock_config)

    # --- ASSERTIONS --- (The rest of the test logic)

    # The Mooring operation record is the second one (after mobilization)
    mooring_rec = timeline[1]

    # Assert manual duration (180 min) was used, NOT the mocked CTD time (120 min)
    assert mooring_rec["activity"] == "Mooring"
    assert mooring_rec["duration_minutes"] == 180.0

    # Assert CTD calculator was NOT called
    mock_duration_calc.calculate_ctd_time.assert_not_called()


def test_timeline_generation_simple_sequential(mock_calculations, config_simple):
    """
    Tests the scheduler's ability to process a simple 2-station sequence,
    including mobilization and demobilization transit legs.
    """
    mock_dist, mock_duration_calc = mock_calculations
    config = config_simple

    # Expected calculations (since distance is mocked to 111.12 km = 60 nm):
    # Transit Time: 60 nm / 10 kt = 6.0 hours (360 minutes)
    # Operation Time: 120 minutes (2.0 hours)

    # --- ACT ---
    timeline = generate_timeline(config)

    # --- ASSERTIONS ---

    # Expected Timeline Length: Mobilization + STN_001 + Inter-transit + STN_002 + Demobilization = 5
    assert len(timeline) == 5

    start_time = datetime(2028, 6, 1, 8, 0, 0)

    # 1. Transit to working area
    transit_to_rec = timeline[0]
    assert transit_to_rec["activity"] == "Transit"
    assert transit_to_rec["duration_minutes"] == pytest.approx(360.0)  # 6 hours
    assert transit_to_rec["start_time"] == start_time
    expected_end_time = start_time + timedelta(minutes=360)
    assert abs((transit_to_rec["end_time"] - expected_end_time).total_seconds()) < 0.01

    # 2. STN_001 (Activity)
    stn1_start = transit_to_rec["end_time"]
    stn1_rec = timeline[1]
    assert stn1_rec["activity"] == "Station"
    assert stn1_rec["duration_minutes"] == 120.0  # 2 hours (mocked duration)
    assert stn1_rec["transit_dist_nm"] == 0.0  # No transit (first station)
    assert (
        stn1_rec["start_time"] == stn1_start
    )  # Starts immediately after transit to working area
    expected_stn1_end = stn1_rec["start_time"] + timedelta(minutes=120)
    assert abs((stn1_rec["end_time"] - expected_stn1_end).total_seconds()) < 0.01

    # 3. Inter-operation Transit
    inter_transit_rec = timeline[2]
    assert inter_transit_rec["activity"] == "Transit"

    # 4. STN_002 (Activity)
    stn2_rec = timeline[3]
    assert stn2_rec["activity"] == "Station"
    assert stn2_rec["transit_dist_nm"] == pytest.approx(
        60.0, rel=1e-3
    )  # Transit from STN_001 to STN_002
    assert (
        stn2_rec["operation_dist_nm"] == 0.0
    )  # No operation distance for point operations
    # STN_002 starts after STN_001 ends + inter-operation transit time
    # The inter-operation transit time should be approximately 6 hours (360.24 minutes based on actual distance)
    expected_stn2_start_timedelta = timedelta(
        minutes=inter_transit_rec["duration_minutes"]
    )
    assert (
        abs(
            (
                stn2_rec["start_time"]
                - (stn1_rec["end_time"] + expected_stn2_start_timedelta)
            ).total_seconds()
        )
        < 1.0
    )

    # 5. Transit from working area
    transit_from_start = stn2_rec["end_time"]
    transit_from_rec = timeline[4]
    # Transit from working area starts immediately after last station
    assert transit_from_rec["start_time"] == transit_from_start
    assert transit_from_rec["duration_minutes"] == pytest.approx(
        360.0
    )  # 6 hours transit time
    assert transit_from_rec["activity"] == "Transit"

    # Distance calculations should be made for transit segments
    # The exact count depends on implementation details (direct haversine vs route_distance)
    # but should be at least 2 calls (mobilization and demobilization transits)
    assert mock_dist.call_count >= 2


def test_timeline_handles_empty_legs_gracefully(mock_calculations, config_simple):
    """Tests that an empty activities list does not crash the scheduler."""
    config = config_simple

    # Override legs to be empty
    config.legs = []

    # --- ACT ---
    timeline = generate_timeline(config)

    # --- ASSERTIONS ---
    # Should still include transit to and from working area if anchors exist
    assert len(timeline) == 2
    assert timeline[0]["activity"] == "Transit"
    assert timeline[1]["activity"] == "Transit"
    assert "Transit to working area" in timeline[0]["label"]


def test_vessel_speed_uses_operation_specific_speed_when_provided(mock_calculations):
    """Tests that operation-specific vessel speeds override default speeds in timeline records."""
    mock_dist, mock_duration_calc = mock_calculations

    # Setup config with default vessel speed
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.default_vessel_speed = 12.0  # Default speed
    mock_config.start_date = "2024-01-01"
    mock_config.start_time = "00:00"

    # Ports
    mock_config.departure_port = create_mock_port(53.0, -60.0, "Start Port")
    mock_config.arrival_port = create_mock_port(53.0, -60.0, "End Port")
    mock_config.first_station = "SURVEY_LINE"
    mock_config.last_station = "SURVEY_LINE"

    # Create a scientific transit with operation-specific vessel speed
    mock_transit = MagicMock()
    mock_transit.name = "SURVEY_LINE"
    mock_transit.position = GeoPoint(latitude=53.5, longitude=-50.0)  # End position
    mock_transit.depth = 0.0
    mock_transit.vessel_speed = 5.0  # Operation-specific speed (slower for survey)

    # Add operation type and action to make it scientific
    mock_operation_type = MagicMock()
    mock_operation_type.value = "underway"
    mock_transit.operation_type = mock_operation_type
    mock_action = MagicMock()
    mock_action.value = "ADCP"
    mock_transit.action = mock_action

    # Route with start and end points for line operation
    mock_route_point1 = MagicMock()
    mock_route_point1.latitude = 53.3
    mock_route_point1.longitude = -50.5
    mock_route_point2 = MagicMock()
    mock_route_point2.latitude = 53.7
    mock_route_point2.longitude = -50.1
    mock_transit.route = [mock_route_point1, mock_route_point2]

    mock_config.stations = []
    mock_config.transits = [mock_transit]

    # Single leg with the survey operation
    leg_mock = MagicMock()
    leg_mock.sequence = ["SURVEY_LINE"]
    leg_mock.stations = []
    mock_config.legs = [leg_mock]

    mock_config.areas = []

    # --- ACT ---
    timeline = generate_timeline(mock_config)

    # --- ASSERTIONS ---

    # Find the survey operation in the timeline
    survey_record = None
    for record in timeline:
        if record["label"] == "SURVEY_LINE":
            survey_record = record
            break

    assert survey_record is not None, "Survey operation not found in timeline"
    assert survey_record["activity"] == "Transit"

    # The key assertion: operation-specific vessel speed should be used
    assert (
        survey_record["vessel_speed_kt"] == 5.0
    ), f"Expected 5.0 kt, got {survey_record['vessel_speed_kt']}"

    # Also verify navigation transits still use default speed
    navigation_transits = [
        r
        for r in timeline
        if r["activity"] == "Transit" and r["label"] != "SURVEY_LINE"
    ]
    for transit in navigation_transits:
        assert (
            transit["vessel_speed_kt"] == 12.0
        ), f"Navigation transit should use default speed of 12.0 kt, got {transit['vessel_speed_kt']}"


def test_vessel_speed_uses_default_when_no_operation_specific_speed(mock_calculations):
    """Tests that default vessel speed is used when no operation-specific speed is provided."""
    mock_dist, mock_duration_calc = mock_calculations

    # Setup config with default vessel speed
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.default_vessel_speed = 10.0  # Default speed
    mock_config.start_date = "2024-01-01"
    mock_config.start_time = "00:00"

    # Ports
    mock_config.departure_port = create_mock_port(53.0, -60.0, "Start Port")
    mock_config.arrival_port = create_mock_port(53.0, -60.0, "End Port")
    mock_config.first_station = "STN_001"
    mock_config.last_station = "STN_001"

    # Create a regular station (no vessel_speed attribute)
    mock_station = MagicMock()
    mock_station.name = "STN_001"
    mock_station.position = GeoPoint(latitude=53.5, longitude=-50.0)
    mock_station.depth = 1000.0
    mock_station.duration = 0.0
    # Explicitly ensure vessel_speed attribute does not exist
    if hasattr(mock_station, "vessel_speed"):
        delattr(mock_station, "vessel_speed")

    mock_operation_type = MagicMock()
    mock_operation_type.value = "CTD"
    mock_station.operation_type = mock_operation_type

    mock_config.stations = [mock_station]
    mock_config.transits = []

    # Single leg with the station
    leg_mock = MagicMock()
    leg_mock.sequence = ["STN_001"]
    leg_mock.stations = []
    mock_config.legs = [leg_mock]

    # --- ACT ---
    timeline = generate_timeline(mock_config)

    # --- ASSERTIONS ---

    # Find the station operation in the timeline
    station_record = None
    for record in timeline:
        if record["label"] == "STN_001":
            station_record = record
            break

    assert station_record is not None, "Station operation not found in timeline"
    assert station_record["activity"] == "Station"

    # Should use default vessel speed since no operation-specific speed provided
    assert (
        station_record["vessel_speed_kt"] == 10.0
    ), f"Expected default speed of 10.0 kt, got {station_record['vessel_speed_kt']}"
