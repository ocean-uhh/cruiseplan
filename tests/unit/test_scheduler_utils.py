"""
Unit tests for scheduler utilities.

Tests the extracted utility functions from scheduler.py refactoring.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from cruiseplan.calculators.scheduler_utils import (
    PositionTracker,
    _calculate_port_to_operations_transit,
    _create_operation_activity_record,
    _create_runtime_legs,
    _extract_activity_delays,
    _extract_leg_buffer_time,
    _initialize_timeline_state,
    _parse_start_datetime,
    _resolve_operation_details,
)
from cruiseplan.core.validation import GeoPoint


class TestExtractLegBufferTime:
    """Test buffer time extraction with various leg types."""

    def test_leg_with_valid_buffer_time(self):
        """Test extracting valid buffer time from leg."""

        class MockLeg:
            def __init__(self):
                self.buffer_time = 30.0

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 30.0

    def test_leg_with_integer_buffer_time(self):
        """Test extracting integer buffer time."""

        class MockLeg:
            def __init__(self):
                self.buffer_time = 45

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 45.0

    def test_leg_without_buffer_time_attribute(self):
        """Test leg without buffer_time attribute."""

        class MockLeg:
            pass

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 0.0

    def test_leg_with_none_buffer_time(self):
        """Test leg with None buffer_time."""

        class MockLeg:
            def __init__(self):
                self.buffer_time = None

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 0.0

    def test_leg_with_magicmock_buffer_time(self):
        """Test leg with MagicMock buffer_time (should be ignored)."""

        class MockLeg:
            def __init__(self):
                self.buffer_time = MagicMock()
                self.buffer_time._mock_name = "mock_buffer_time"

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 0.0

    def test_leg_with_invalid_buffer_time_type(self):
        """Test leg with invalid buffer_time type."""

        class MockLeg:
            def __init__(self):
                self.buffer_time = "invalid"

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 0.0

    def test_leg_with_exception_during_access(self):
        """Test leg that raises exception during buffer_time access."""

        class MockLeg:
            @property
            def buffer_time(self):
                raise ValueError("Test exception")

        leg = MockLeg()
        result = _extract_leg_buffer_time(leg)
        assert result == 0.0


class TestExtractActivityDelays:
    """Test activity delay extraction."""

    def test_activity_with_valid_delays(self):
        """Test extracting valid delays from activity."""
        activity = {"delay_start": 10.0, "delay_end": 15.0}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 10.0
        assert end_delay == 15.0

    def test_activity_with_integer_delays(self):
        """Test extracting integer delays."""
        activity = {"delay_start": 5, "delay_end": 8}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 5.0
        assert end_delay == 8.0

    def test_activity_without_delay_fields(self):
        """Test activity without delay fields."""
        activity = {"name": "test_activity"}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 0.0
        assert end_delay == 0.0

    def test_activity_with_none_delays(self):
        """Test activity with None delays."""
        activity = {"delay_start": None, "delay_end": None}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 0.0
        assert end_delay == 0.0

    def test_activity_with_magicmock_delays(self):
        """Test activity with MagicMock delays (should be ignored)."""
        mock_start = MagicMock()
        mock_start._mock_name = "mock_start"
        mock_end = MagicMock()
        mock_end._mock_name = "mock_end"

        activity = {"delay_start": mock_start, "delay_end": mock_end}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 0.0
        assert end_delay == 0.0

    def test_activity_with_invalid_delay_types(self):
        """Test activity with invalid delay types."""
        activity = {"delay_start": "invalid", "delay_end": ["invalid", "list"]}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 0.0
        assert end_delay == 0.0

    def test_activity_with_mixed_valid_invalid_delays(self):
        """Test activity with one valid and one invalid delay."""
        activity = {"delay_start": 12.5, "delay_end": "invalid"}

        start_delay, end_delay = _extract_activity_delays(activity)
        assert start_delay == 12.5
        assert end_delay == 0.0


class TestParseStartDatetime:
    """Test start datetime parsing."""

    def test_parse_iso_format_with_z_suffix(self):
        """Test parsing ISO format with Z suffix."""
        config = Mock()
        config.start_date = "2024-01-15T08:30:00Z"

        result = _parse_start_datetime(config)
        expected = datetime(2024, 1, 15, 8, 30, 0)
        assert result == expected

    def test_parse_iso_format_with_timezone(self):
        """Test parsing ISO format with timezone."""
        config = Mock()
        config.start_date = "2024-01-15T08:30:00+00:00"

        result = _parse_start_datetime(config)
        expected = datetime(2024, 1, 15, 8, 30, 0)
        assert result == expected

    def test_parse_separate_date_and_time(self):
        """Test parsing separate date and time fields."""
        config = Mock()
        config.start_date = "2024-01-15"
        config.start_time = "08:30"

        result = _parse_start_datetime(config)
        expected = datetime(2024, 1, 15, 8, 30, 0)
        assert result == expected

    def test_parse_different_time_format(self):
        """Test parsing different time format."""
        config = Mock()
        config.start_date = "2024-12-25"
        config.start_time = "14:45"

        result = _parse_start_datetime(config)
        expected = datetime(2024, 12, 25, 14, 45, 0)
        assert result == expected

    def test_parse_invalid_date_format(self):
        """Test parsing invalid date format raises ValueError."""
        config = Mock()
        config.start_date = "invalid-date"
        config.start_time = "08:30"

        with pytest.raises(ValueError):
            _parse_start_datetime(config)

    def test_parse_invalid_time_format(self):
        """Test parsing invalid time format raises ValueError."""
        config = Mock()
        config.start_date = "2024-01-15"
        config.start_time = "invalid-time"

        with pytest.raises(ValueError):
            _parse_start_datetime(config)

    def test_parse_missing_start_time_attribute(self):
        """Test parsing when start_time attribute is missing."""
        config = Mock()
        config.start_date = "2024-01-15"
        del config.start_time  # Remove attribute

        with pytest.raises(AttributeError):
            _parse_start_datetime(config)


class TestResolveOperationDetails:
    """Test operation details resolution."""

    @patch("cruiseplan.calculators.scheduler._resolve_station_details")
    def test_resolve_station_success(self, mock_station_resolver):
        """Test successful station resolution."""
        mock_config = Mock()
        mock_station_resolver.return_value = {
            "name": "STN_001",
            "lat": 60.0,
            "lon": 5.0,
        }

        result = _resolve_operation_details(mock_config, "STN_001")

        assert result == {"name": "STN_001", "lat": 60.0, "lon": 5.0}
        mock_station_resolver.assert_called_once_with(mock_config, "STN_001")

    @patch("cruiseplan.calculators.scheduler._resolve_mooring_details")
    @patch("cruiseplan.calculators.scheduler._resolve_station_details")
    def test_resolve_mooring_fallback(
        self, mock_station_resolver, mock_mooring_resolver
    ):
        """Test fallback to mooring resolver when station fails."""
        mock_config = Mock()
        mock_station_resolver.return_value = None
        mock_mooring_resolver.return_value = {
            "name": "MOORING_001",
            "lat": 60.0,
            "lon": 5.0,
        }

        result = _resolve_operation_details(mock_config, "MOORING_001")

        assert result == {"name": "MOORING_001", "lat": 60.0, "lon": 5.0}
        mock_station_resolver.assert_called_once()
        mock_mooring_resolver.assert_called_once_with(mock_config, "MOORING_001")

    @patch("cruiseplan.calculators.scheduler._resolve_port_details")
    @patch("cruiseplan.calculators.scheduler._resolve_transit_details")
    @patch("cruiseplan.calculators.scheduler._resolve_area_details")
    @patch("cruiseplan.calculators.scheduler._resolve_mooring_details")
    @patch("cruiseplan.calculators.scheduler._resolve_station_details")
    def test_resolve_all_resolvers_fail(
        self, mock_station, mock_mooring, mock_area, mock_transit, mock_port
    ):
        """Test when all resolvers fail."""
        mock_config = Mock()
        mock_station.return_value = None
        mock_mooring.return_value = None
        mock_area.return_value = None
        mock_transit.return_value = None
        mock_port.return_value = None

        result = _resolve_operation_details(mock_config, "UNKNOWN")

        assert result is None
        # Verify all resolvers were called in order
        mock_station.assert_called_once()
        mock_mooring.assert_called_once()
        mock_area.assert_called_once()
        mock_transit.assert_called_once()
        mock_port.assert_called_once()


class TestPositionTracker:
    """Test position tracking functionality."""

    def test_initialize_without_start_position(self):
        """Test initializing tracker without start position."""
        tracker = PositionTracker()
        assert tracker.current_position is None

    def test_initialize_with_start_position(self):
        """Test initializing tracker with start position."""
        start_pos = GeoPoint(latitude=60.0, longitude=5.0)
        tracker = PositionTracker(start_pos)
        assert tracker.current_position == start_pos

    def test_update_from_station_activity(self):
        """Test updating position from station activity."""
        tracker = PositionTracker()
        activity = {"lat": 61.0, "lon": 6.0, "op_type": "station"}

        tracker.update_from_activity(activity)

        assert tracker.current_position.latitude == 61.0
        assert tracker.current_position.longitude == 6.0

    def test_update_from_transit_activity_with_end_position(self):
        """Test updating position from transit with end coordinates."""
        tracker = PositionTracker()
        activity = {
            "lat": 61.0,
            "lon": 6.0,
            "op_type": "transit",
            "end_lat": 62.0,
            "end_lon": 7.0,
        }

        tracker.update_from_activity(activity)

        # Should use end position for transit
        assert tracker.current_position.latitude == 62.0
        assert tracker.current_position.longitude == 7.0

    def test_update_from_transit_activity_without_end_position(self):
        """Test updating position from transit without end coordinates."""
        tracker = PositionTracker()
        activity = {"lat": 61.0, "lon": 6.0, "op_type": "transit"}

        tracker.update_from_activity(activity)

        # Should use main position when end position not available
        assert tracker.current_position.latitude == 61.0
        assert tracker.current_position.longitude == 6.0

    def test_get_current_position(self):
        """Test getting current position."""
        start_pos = GeoPoint(latitude=60.0, longitude=5.0)
        tracker = PositionTracker(start_pos)

        result = tracker.get_position()
        assert result == start_pos

    def test_get_position_when_none(self):
        """Test getting position when not set."""
        tracker = PositionTracker()
        result = tracker.get_position()
        assert result is None


class TestCalculatePortToOperationsTransit:
    """Test port to operations transit calculation."""

    def setup_method(self):
        """Set up common test fixtures."""
        self.mock_config = Mock()
        self.mock_config.default_vessel_speed = 10.0

        self.mock_runtime_leg = Mock()
        self.mock_runtime_leg.name = "Test_Leg"
        self.mock_runtime_leg.vessel_speed = None
        self.mock_runtime_leg.departure_port.name = "Test_Port"
        self.mock_runtime_leg.departure_port.display_name = "Test Port Display"
        self.mock_runtime_leg.departure_port.latitude = 60.0
        self.mock_runtime_leg.departure_port.longitude = 5.0

        self.mock_leg_def = Mock()
        self.mock_leg_def.activities = ["STN_001"]
        self.mock_leg_def.first_waypoint = None

    @patch("cruiseplan.calculators.scheduler_utils._resolve_operation_details")
    @patch("cruiseplan.calculators.scheduler._extract_activities_from_leg")
    @patch("cruiseplan.calculators.scheduler._calculate_inter_port_transit")
    @patch("cruiseplan.calculators.scheduler_utils.haversine_distance")
    @patch("cruiseplan.calculators.scheduler_utils.km_to_nm")
    def test_successful_transit_calculation(
        self,
        mock_km_to_nm,
        mock_haversine,
        mock_calculate_transit,
        mock_extract_activities,
        mock_resolve_operation,
    ):
        """Test successful transit calculation."""
        # Setup mocks
        mock_extract_activities.return_value = ["STN_001"]
        mock_resolve_operation.return_value = {
            "name": "STN_001",
            "lat": 61.0,
            "lon": 6.0,
        }
        mock_haversine.return_value = 100.0  # km
        mock_km_to_nm.return_value = 54.0  # nm
        mock_calculate_transit.return_value = 324.0  # minutes (5.4 hours)

        current_time = datetime(2024, 1, 15, 8, 0, 0)

        result_activity, result_position = _calculate_port_to_operations_transit(
            self.mock_config, self.mock_runtime_leg, self.mock_leg_def, current_time
        )

        # Verify result
        assert result_activity is not None
        assert result_activity["activity"] == "Port_Departure"
        assert result_activity["lat"] == 60.0
        assert result_activity["lon"] == 5.0
        assert result_activity["duration_minutes"] == 324.0
        assert result_activity["transit_dist_nm"] == 54.0

        assert result_position is not None
        assert result_position.latitude == 61.0
        assert result_position.longitude == 6.0

    @patch("cruiseplan.calculators.scheduler._extract_activities_from_leg")
    def test_no_activities_returns_none(self, mock_extract_activities):
        """Test returns None when leg has no activities."""
        self.mock_leg_def.activities = []
        mock_extract_activities.return_value = []

        current_time = datetime(2024, 1, 15, 8, 0, 0)

        result_activity, result_position = _calculate_port_to_operations_transit(
            self.mock_config, self.mock_runtime_leg, self.mock_leg_def, current_time
        )

        assert result_activity is None
        assert result_position is None

    @patch("cruiseplan.calculators.scheduler_utils._resolve_operation_details")
    @patch("cruiseplan.calculators.scheduler._extract_activities_from_leg")
    def test_operation_resolution_fails(
        self, mock_extract_activities, mock_resolve_operation
    ):
        """Test returns None when operation resolution fails."""
        mock_extract_activities.return_value = ["STN_001"]
        mock_resolve_operation.return_value = None

        current_time = datetime(2024, 1, 15, 8, 0, 0)

        result_activity, result_position = _calculate_port_to_operations_transit(
            self.mock_config, self.mock_runtime_leg, self.mock_leg_def, current_time
        )

        assert result_activity is None
        assert result_position is None

    @patch("cruiseplan.calculators.scheduler_utils._resolve_operation_details")
    @patch("cruiseplan.calculators.scheduler._extract_activities_from_leg")
    @patch("cruiseplan.calculators.scheduler._calculate_inter_port_transit")
    @patch("cruiseplan.calculators.distance.haversine_distance")
    @patch("cruiseplan.calculators.distance.km_to_nm")
    def test_uses_first_waypoint_priority(
        self,
        mock_km_to_nm,
        mock_haversine,
        mock_calculate_transit,
        mock_extract_activities,
        mock_resolve_operation,
    ):
        """Test prioritizes first_waypoint over activities."""
        # Setup leg with first_waypoint
        self.mock_leg_def.first_waypoint = "PRIORITY_STN"
        self.mock_leg_def.activities = ["STN_001", "STN_002"]

        mock_extract_activities.return_value = ["STN_001", "STN_002"]
        mock_resolve_operation.return_value = {
            "name": "PRIORITY_STN",
            "lat": 61.0,
            "lon": 6.0,
        }
        mock_haversine.return_value = 100.0
        mock_km_to_nm.return_value = 54.0
        mock_calculate_transit.return_value = 324.0

        current_time = datetime(2024, 1, 15, 8, 0, 0)

        _calculate_port_to_operations_transit(
            self.mock_config, self.mock_runtime_leg, self.mock_leg_def, current_time
        )

        # Verify it tried to resolve the first_waypoint, not the first activity
        mock_resolve_operation.assert_called_with(self.mock_config, "PRIORITY_STN")


class TestCreateOperationActivityRecord:
    """Test activity record creation."""

    def test_create_basic_activity_record(self):
        """Test creating basic activity record."""
        details = {
            "name": "STN_001",
            "lat": 60.0,
            "lon": 5.0,
            "depth": 100.0,
            "op_type": "station",
            "action": "profile",
        }
        current_time = datetime(2024, 1, 15, 8, 0, 0)
        duration_min = 120.0

        result = _create_operation_activity_record(
            details, current_time, duration_min, leg_name="Test_Leg"
        )

        assert result["activity"] == "Station"
        assert result["label"] == "STN_001"
        assert result["lat"] == 60.0
        assert result["lon"] == 5.0
        assert result["depth"] == 100.0
        assert result["start_time"] == current_time
        assert result["end_time"] == current_time + timedelta(minutes=120)
        assert result["duration_minutes"] == 120.0
        assert result["leg_name"] == "Test_Leg"
        assert result["op_type"] == "station"
        assert result["action"] == "profile"

    def test_create_transit_activity_with_route_distance(self):
        """Test creating transit activity with route distance."""
        details = {
            "name": "ADCP_Survey",
            "lat": 60.0,
            "lon": 5.0,
            "op_type": "transit",
            "action": "ADCP",
            "route_distance_nm": 25.0,
        }
        current_time = datetime(2024, 1, 15, 8, 0, 0)
        duration_min = 300.0  # 5 hours

        result = _create_operation_activity_record(details, current_time, duration_min)

        assert result["activity"] == "Transit"
        assert result["operation_dist_nm"] == 25.0
        assert result["duration_minutes"] == 300.0

    def test_create_activity_with_default_values(self):
        """Test creating activity with missing optional fields."""
        details = {"name": "STN_002", "lat": 61.0, "lon": 6.0}
        current_time = datetime(2024, 1, 15, 9, 0, 0)
        duration_min = 60.0

        result = _create_operation_activity_record(details, current_time, duration_min)

        assert result["activity"] == "Station"  # Default op_type
        assert result["depth"] == 0.0  # Default depth
        assert result["action"] is None  # No action provided
        assert result["transit_dist_nm"] == 0.0
        assert result["operation_dist_nm"] == 0.0


class TestCreateRuntimeLegs:
    """Test runtime leg creation."""

    def test_create_basic_runtime_legs(self):
        """Test creating basic runtime legs."""
        mock_leg_def1 = Mock()
        mock_leg_def1.name = "Leg_1"
        mock_leg_def1.departure_port = "port_bergen"
        mock_leg_def1.arrival_port = "port_cadiz"
        mock_leg_def1.description = "Test leg 1"
        mock_leg_def1.first_waypoint = "STN_001"
        mock_leg_def1.last_waypoint = "STN_010"
        mock_leg_def1.vessel_speed = 12.0
        mock_leg_def1.turnaround_time = 30.0
        mock_leg_def1.distance_between_stations = 20.0

        mock_config = Mock()
        mock_config.legs = [mock_leg_def1]

        with patch("cruiseplan.core.leg.Leg") as mock_leg_class:
            mock_leg_instance = Mock()
            mock_leg_class.return_value = mock_leg_instance

            result = _create_runtime_legs(mock_config)

            assert len(result) == 1
            assert result[0] == mock_leg_instance

            # Verify Leg constructor was called with correct parameters
            mock_leg_class.assert_called_once_with(
                name="Leg_1",
                departure_port="port_bergen",
                arrival_port="port_cadiz",
                description="Test leg 1",
                first_waypoint="STN_001",
                last_waypoint="STN_010",
            )

            # Verify leg-specific parameters were set
            assert mock_leg_instance.vessel_speed == 12.0
            assert mock_leg_instance.turnaround_time == 30.0
            assert mock_leg_instance.distance_between_stations == 20.0

    def test_create_runtime_legs_with_exception(self):
        """Test runtime leg creation when Leg constructor raises exception."""
        mock_leg_def = Mock()
        mock_leg_def.name = "Failing_Leg"

        mock_config = Mock()
        mock_config.legs = [mock_leg_def]

        with patch("cruiseplan.core.leg.Leg") as mock_leg_class:
            # Create instances to be returned
            mock_leg_instance = Mock()
            mock_leg_instance.name = "Failing_Leg"

            # First call raises exception, second call (fallback) succeeds
            mock_leg_class.side_effect = [
                Exception("Leg creation failed"),
                mock_leg_instance,
            ]

            result = _create_runtime_legs(mock_config)

            # Should still create a leg (fallback leg)
            assert len(result) == 1
            assert result[0].name == "Failing_Leg"

    def test_create_runtime_legs_empty_config(self):
        """Test creating runtime legs with empty config."""
        mock_config = Mock()
        mock_config.legs = []

        result = _create_runtime_legs(mock_config)
        assert result == []

    def test_create_runtime_legs_none_legs(self):
        """Test creating runtime legs when legs is None."""
        mock_config = Mock()
        mock_config.legs = None

        result = _create_runtime_legs(mock_config)
        assert result == []


class TestInitializeTimelineState:
    """Test timeline initialization."""

    @patch("cruiseplan.calculators.scheduler_utils._parse_start_datetime")
    @patch("cruiseplan.calculators.duration.DurationCalculator")
    def test_initialize_timeline_state(
        self, mock_duration_calc_class, mock_parse_datetime
    ):
        """Test timeline state initialization."""
        mock_config = Mock()
        expected_datetime = datetime(2024, 1, 15, 8, 0, 0)
        mock_parse_datetime.return_value = expected_datetime

        mock_duration_calc = Mock()
        mock_duration_calc_class.return_value = mock_duration_calc

        current_time, duration_calc, current_position = _initialize_timeline_state(
            mock_config
        )

        assert current_time == expected_datetime
        assert duration_calc == mock_duration_calc
        assert current_position is None

        mock_parse_datetime.assert_called_once_with(mock_config)
        mock_duration_calc_class.assert_called_once_with(mock_config)
