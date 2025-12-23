"""Unit tests for scheduler.py helper functions.

Tests the smaller, focused functions in the scheduler module that can be
tested in isolation without complex integration setups.
"""

from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.calculators.scheduler import (
    _calculate_inter_operation_transit,
    _extract_activities_from_leg,
    _resolve_station_details,
    get_operation_entry_exit_points,
)
from cruiseplan.core.validation import (
    CruiseConfig,
)


class TestCalculateInterOperationTransit:
    """Test the _calculate_inter_operation_transit function."""

    def test_basic_transit_calculation(self):
        """Test basic transit calculation between two points."""
        # Positions approximately 100 nautical miles apart
        last_pos = (60.0, -20.0)  # Iceland area
        current_pos = (61.5, -20.0)  # ~90 nm north
        vessel_speed_kt = 10.0

        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            last_pos, current_pos, vessel_speed_kt
        )

        # Should be approximately 90 nm distance
        assert distance_nm == pytest.approx(90.0, abs=5.0)
        # Transit time should be ~9 hours = 540 minutes
        assert transit_time_min == pytest.approx(540.0, abs=30.0)

    def test_zero_distance_transit(self):
        """Test transit calculation when positions are the same."""
        same_pos = (60.0, -20.0)
        vessel_speed_kt = 10.0

        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            same_pos, same_pos, vessel_speed_kt
        )

        assert distance_nm == 0.0
        assert transit_time_min == 0.0

    def test_none_position_handling(self):
        """Test handling of None positions."""
        current_pos = (60.0, -20.0)
        vessel_speed_kt = 10.0

        # Test with None last position
        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            None, current_pos, vessel_speed_kt
        )
        assert transit_time_min == 0.0
        assert distance_nm == 0.0

        # Test with None current position
        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            current_pos, None, vessel_speed_kt
        )
        assert transit_time_min == 0.0
        assert distance_nm == 0.0

        # Test with both None
        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            None, None, vessel_speed_kt
        )
        assert transit_time_min == 0.0
        assert distance_nm == 0.0

    def test_zero_vessel_speed(self):
        """Test handling of zero vessel speed."""
        last_pos = (60.0, -20.0)
        current_pos = (61.0, -20.0)
        vessel_speed_kt = 0.0

        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            last_pos, current_pos, vessel_speed_kt
        )

        # Distance should still be calculated
        assert distance_nm > 0.0
        # Transit time should be 0 for zero speed
        assert transit_time_min == 0.0

    def test_negative_vessel_speed(self):
        """Test handling of negative vessel speed."""
        last_pos = (60.0, -20.0)
        current_pos = (61.0, -20.0)
        vessel_speed_kt = -5.0

        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            last_pos, current_pos, vessel_speed_kt
        )

        # Distance should still be calculated
        assert distance_nm > 0.0
        # Transit time should be 0 for negative speed
        assert transit_time_min == 0.0

    def test_long_distance_transit(self):
        """Test transit calculation for longer distances."""
        # Positions approximately 500 nautical miles apart (Iceland to Scotland)
        iceland_pos = (64.0, -22.0)
        scotland_pos = (58.0, -5.0)
        vessel_speed_kt = 12.0

        transit_time_min, distance_nm = _calculate_inter_operation_transit(
            iceland_pos, scotland_pos, vessel_speed_kt
        )

        # Should be roughly 500+ nm
        assert distance_nm > 400.0
        assert distance_nm < 700.0
        # Transit time should be reasonable (distance/speed * 60)
        expected_time = (distance_nm / vessel_speed_kt) * 60
        assert transit_time_min == pytest.approx(expected_time, abs=1.0)


class TestGetOperationEntryExitPoints:
    """Test the get_operation_entry_exit_points function."""

    def test_station_operation_found(self):
        """Test finding entry/exit points for a station operation."""
        # Create mock config with a station
        mock_config = MagicMock(spec=CruiseConfig)
        mock_station = MagicMock()
        mock_station.name = "STN_001"
        mock_config.stations = [mock_station]
        mock_config.transits = None
        mock_config.areas = None

        # Mock the PointOperation import
        with patch("cruiseplan.core.operations.PointOperation") as mock_point_op:
            mock_operation = MagicMock()
            mock_operation.get_entry_point.return_value = (60.0, -20.0)
            mock_operation.get_exit_point.return_value = (60.0, -20.0)
            mock_point_op.from_pydantic.return_value = mock_operation

            result = get_operation_entry_exit_points(mock_config, "STN_001")

            assert result == ((60.0, -20.0), (60.0, -20.0))
            mock_point_op.from_pydantic.assert_called_once_with(mock_station)

    def test_transit_operation_found(self):
        """Test finding entry/exit points for a transit operation."""
        # Create mock config with a transit
        mock_config = MagicMock(spec=CruiseConfig)
        mock_config.stations = None
        mock_transit = MagicMock()
        mock_transit.name = "TRANSIT_001"
        mock_config.transits = [mock_transit]
        mock_config.areas = None
        mock_config.default_vessel_speed = 10.0

        # Mock the LineOperation
        with patch("cruiseplan.core.operations.LineOperation") as mock_line_op:
            mock_operation = MagicMock()
            mock_operation.get_entry_point.return_value = (60.0, -20.0)
            mock_operation.get_exit_point.return_value = (61.0, -20.0)
            mock_line_op.from_pydantic.return_value = mock_operation

            result = get_operation_entry_exit_points(mock_config, "TRANSIT_001")

            assert result == ((60.0, -20.0), (61.0, -20.0))
            mock_line_op.from_pydantic.assert_called_once_with(mock_transit, 10.0)

    def test_area_operation_found(self):
        """Test finding entry/exit points for an area operation."""
        # Create mock config with an area
        mock_config = MagicMock(spec=CruiseConfig)
        mock_config.stations = None
        mock_config.transits = None
        mock_area = MagicMock()
        mock_area.name = "AREA_001"
        mock_config.areas = [mock_area]

        # Mock the AreaOperation
        with patch("cruiseplan.core.operations.AreaOperation") as mock_area_op:
            mock_operation = MagicMock()
            mock_operation.get_entry_point.return_value = (60.0, -20.0)
            mock_operation.get_exit_point.return_value = (62.0, -22.0)
            mock_area_op.from_pydantic.return_value = mock_operation

            result = get_operation_entry_exit_points(mock_config, "AREA_001")

            assert result == ((60.0, -20.0), (62.0, -22.0))
            mock_area_op.from_pydantic.assert_called_once_with(mock_area)

    def test_operation_not_found(self):
        """Test behavior when operation is not found."""
        # Create mock config with no matching operations
        mock_config = MagicMock(spec=CruiseConfig)
        mock_config.stations = []
        mock_config.transits = []
        mock_config.areas = []

        result = get_operation_entry_exit_points(mock_config, "NONEXISTENT")

        assert result is None

    def test_exception_handling(self):
        """Test exception handling in operation creation."""
        # Create mock config with a station that will cause an exception
        mock_config = MagicMock(spec=CruiseConfig)
        mock_station = MagicMock()
        mock_station.name = "STN_001"
        mock_config.stations = [mock_station]
        mock_config.transits = None
        mock_config.areas = None

        # Mock PointOperation to raise an exception
        with patch("cruiseplan.core.operations.PointOperation") as mock_point_op:
            mock_point_op.from_pydantic.side_effect = ValueError("Mock error")

            with patch("cruiseplan.calculators.scheduler.logger") as mock_logger:
                result = get_operation_entry_exit_points(mock_config, "STN_001")

                assert result is None
                mock_logger.warning.assert_called_once()

    def test_empty_config_sections(self):
        """Test handling of None config sections."""
        # Create mock config with None sections
        mock_config = MagicMock(spec=CruiseConfig)
        mock_config.stations = None
        mock_config.transits = None
        mock_config.areas = None

        result = get_operation_entry_exit_points(mock_config, "STN_001")

        assert result is None


class TestResolveStationDetails:
    """Test the _resolve_station_details function."""

    def test_ctd_station_resolution(self):
        """Test resolving a CTD station."""
        # Create mock config with a CTD station
        mock_config = MagicMock(spec=CruiseConfig)
        mock_station = MagicMock()
        mock_station.name = "CTD_001"
        mock_station.latitude = 60.0
        mock_station.longitude = -20.0
        mock_station.operation_type.value = "CTD"
        mock_station.depth = 1500.0
        mock_station.duration = 180.0  # 3 hours
        mock_station.action = None  # No action
        # Explicitly set attributes that getattr() might look for
        mock_station.operation_depth = None
        mock_station.delay_start = 0.0
        mock_station.delay_end = 0.0
        mock_config.stations = [mock_station]
        mock_config.areas = []  # Add required areas attribute
        mock_config.transits = []  # Add required transits attribute

        result = _resolve_station_details(mock_config, "CTD_001")

        assert result == {
            "name": "CTD_001",
            "lat": 60.0,
            "lon": -20.0,
            "depth": 1500.0,
            "op_type": "station",  # CTD maps to "station"
            "manual_duration": 180.0,
            "delay_start": 0.0,
            "delay_end": 0.0,
            "action": None,
        }

    def test_mooring_station_resolution(self):
        """Test resolving a mooring station."""
        # Create mock config with a mooring station
        mock_config = MagicMock(spec=CruiseConfig)
        mock_station = MagicMock()
        mock_station.name = "MOORING_A"
        mock_station.latitude = 61.0
        mock_station.longitude = -21.0
        mock_station.operation_type.value = "mooring"
        mock_station.depth = 2500.0
        mock_station.duration = 360.0  # 6 hours
        mock_station.delay_start = 60.0
        mock_station.delay_end = 30.0
        mock_station.action = None
        # Explicitly set operation_depth to None to use depth instead
        mock_station.operation_depth = None
        mock_config.stations = [mock_station]
        mock_config.areas = []
        mock_config.transits = []

        result = _resolve_station_details(mock_config, "MOORING_A")

        assert result == {
            "name": "MOORING_A",
            "lat": 61.0,
            "lon": -21.0,
            "depth": 2500.0,
            "op_type": "mooring",  # mooring maps to "mooring"
            "manual_duration": 360.0,
            "delay_start": 60.0,
            "delay_end": 30.0,
            "action": None,
        }

    def test_station_not_found(self):
        """Test behavior when station is not found."""
        # Create mock config with no matching stations
        mock_config = MagicMock(spec=CruiseConfig)
        mock_config.stations = []
        mock_config.areas = []
        mock_config.transits = []

        result = _resolve_station_details(mock_config, "NONEXISTENT")

        assert result is None

    def test_station_without_coordinates(self):
        """Test handling station without latitude/longitude."""
        # Create mock config with station missing coordinates
        mock_config = MagicMock(spec=CruiseConfig)
        mock_station = MagicMock()
        mock_station.name = "BAD_STATION"
        # Make hasattr checks fail for latitude and position
        mock_station.configure_mock(
            **{
                "latitude": MagicMock(side_effect=AttributeError),
                "position": MagicMock(side_effect=AttributeError),
            }
        )
        mock_config.stations = [mock_station]
        mock_config.areas = []
        mock_config.transits = []

        # Mock hasattr to return False for both latitude and position
        with patch(
            "builtins.hasattr",
            side_effect=lambda obj, attr: attr not in ["latitude", "position"],
        ):
            result = _resolve_station_details(mock_config, "BAD_STATION")

        assert result is None

    def test_none_stations_list(self):
        """Test handling of None stations list."""
        # Create mock config with None stations
        mock_config = MagicMock(spec=CruiseConfig)
        mock_config.stations = None
        mock_config.areas = None
        mock_config.transits = None

        result = _resolve_station_details(mock_config, "STN_001")

        assert result is None

    def test_operation_depth_priority(self):
        """Test that operation_depth takes priority over depth."""
        # Create mock config with station having both operation_depth and depth
        mock_config = MagicMock(spec=CruiseConfig)
        mock_station = MagicMock()
        mock_station.name = "CTD_001"
        mock_station.latitude = 60.0
        mock_station.longitude = -20.0
        mock_station.operation_type.value = "CTD"
        mock_station.operation_depth = 500.0  # Cast to 500m
        mock_station.depth = 2000.0  # Water depth 2000m
        mock_station.duration = 120.0
        mock_config.stations = [mock_station]

        result = _resolve_station_details(mock_config, "CTD_001")

        # Should use operation_depth (500.0) not depth (2000.0)
        assert result["depth"] == 500.0

    def test_default_values_handling(self):
        """Test handling of missing optional attributes."""
        # Create mock config with minimal station
        mock_config = MagicMock(spec=CruiseConfig)

        # Create a more controlled mock with spec_set to prevent auto-creation
        class MinimalStation:
            def __init__(self):
                self.name = "MIN_STATION"
                self.latitude = 60.0
                self.longitude = -20.0
                self.operation_type = MagicMock()
                self.operation_type.value = "CTD"
                self.action = None
                self.depth = None
                self.operation_depth = None
                self.duration = None
                # delay_start and delay_end are intentionally NOT set

        mock_station = MinimalStation()
        mock_config.stations = [mock_station]
        mock_config.areas = []
        mock_config.transits = []

        result = _resolve_station_details(mock_config, "MIN_STATION")

        assert result == {
            "name": "MIN_STATION",
            "lat": 60.0,
            "lon": -20.0,
            "depth": 0.0,  # Default when no depth provided
            "op_type": "station",
            "manual_duration": 0.0,  # Default when no duration
            "delay_start": 0.0,
            "delay_end": 0.0,
            "action": None,
        }

    def test_operation_type_mapping(self):
        """Test operation type mapping to legacy op_type."""
        mock_config = MagicMock(spec=CruiseConfig)

        # Test different operation types
        test_cases = [
            ("CTD", "station"),
            ("water_sampling", "station"),
            ("calibration", "station"),
            ("mooring", "mooring"),
            ("survey", "area"),
        ]

        for operation_type, expected_op_type in test_cases:
            mock_station = MagicMock()
            mock_station.name = f"TEST_{operation_type}"
            mock_station.latitude = 60.0
            mock_station.longitude = -20.0
            mock_station.operation_type.value = operation_type
            mock_config.stations = [mock_station]

            result = _resolve_station_details(mock_config, f"TEST_{operation_type}")

            assert result["op_type"] == expected_op_type, f"Failed for {operation_type}"


class TestExtractActivitiesFromLeg:
    """Test the _extract_activities_from_leg function."""

    def test_leg_with_direct_activities(self):
        """Test extracting activities from leg with direct activities (Priority 1)."""
        mock_leg = MagicMock()
        mock_leg.activities = [
            "STN_001",
            "TRANSIT_001",
            "STN_002",
        ]  # Priority 1 (preferred)
        mock_leg.clusters = ["CLUSTER_001"]  # Should be ignored
        mock_leg.sequence = ["SEQ_001"]  # Should be ignored
        mock_leg.stations = ["STATION_001"]  # Should be ignored

        result = _extract_activities_from_leg(mock_leg)

        # Should only use activities, ignore all other fields
        assert result == ["STN_001", "TRANSIT_001", "STN_002"]

    def test_leg_with_activities_as_objects(self):
        """Test extracting activities from leg with activity objects having names."""
        mock_leg = MagicMock()

        # Create mock activity objects with name attributes
        mock_activity1 = MagicMock()
        mock_activity1.name = "ACT_001"
        mock_activity2 = {"name": "ACT_002"}  # Dict format

        mock_leg.activities = [
            mock_activity1,
            mock_activity2,
            "ACT_003",
        ]  # Mixed formats
        mock_leg.clusters = None
        mock_leg.sequence = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == ["ACT_001", "ACT_002", "ACT_003"]

    def test_leg_with_empty_activities(self):
        """Test that empty activities list falls back to lower priorities."""
        mock_leg = MagicMock()
        mock_leg.activities = []  # Empty activities list

        # Create cluster that should be used (Priority 2)
        mock_cluster = MagicMock()
        mock_cluster.name = "TestCluster"
        mock_cluster.activities = ["CLUSTER_ACT_001"]
        mock_cluster.sequence = None
        mock_cluster.stations = None
        mock_leg.clusters = [mock_cluster]

        mock_leg.sequence = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        # Should fall back to cluster activities
        assert result == ["CLUSTER_ACT_001"]

    def test_leg_with_direct_sequence(self):
        """Test extracting activities from leg with direct sequence (deprecated priority)."""
        mock_leg = MagicMock()
        mock_leg.name = "TestLeg"  # Add name for deprecation warning
        mock_leg.activities = None  # No activities (Priority 1)
        mock_leg.clusters = None  # No clusters (Priority 2)
        mock_leg.sequence = [
            "STN_001",
            "STN_002",
            "MOORING_A",
        ]  # Priority 3 (deprecated)
        mock_leg.stations = None

        with pytest.warns(DeprecationWarning, match="uses deprecated 'sequence' field"):
            result = _extract_activities_from_leg(mock_leg)

        assert result == ["STN_001", "STN_002", "MOORING_A"]

    def test_leg_with_object_sequence(self):
        """Test extracting activities from sequence with objects having names (deprecated priority)."""
        mock_leg = MagicMock()
        mock_leg.name = "TestLeg"  # Add name for deprecation warning

        # Create mock objects with name attributes
        mock_obj1 = MagicMock()
        mock_obj1.name = "OBJ_001"
        mock_obj2 = MagicMock()
        mock_obj2.name = "OBJ_002"

        mock_leg.activities = None  # No activities (Priority 1)
        mock_leg.clusters = None  # No clusters (Priority 2)
        mock_leg.sequence = [mock_obj1, mock_obj2]  # Priority 3 (deprecated)
        mock_leg.stations = None

        with pytest.warns(DeprecationWarning, match="uses deprecated 'sequence' field"):
            result = _extract_activities_from_leg(mock_leg)

        assert result == ["OBJ_001", "OBJ_002"]

    def test_leg_with_mixed_sequence(self):
        """Test extracting activities from sequence with mixed strings and objects (deprecated priority)."""
        mock_leg = MagicMock()
        mock_leg.name = "TestLeg"  # Add name for deprecation warning

        mock_obj = MagicMock()
        mock_obj.name = "OBJ_001"

        mock_leg.activities = None  # No activities (Priority 1)
        mock_leg.clusters = None  # No clusters (Priority 2)
        mock_leg.sequence = ["STN_001", mock_obj, "STN_003"]  # Priority 3 (deprecated)
        mock_leg.stations = None

        with pytest.warns(DeprecationWarning, match="uses deprecated 'sequence' field"):
            result = _extract_activities_from_leg(mock_leg)

        assert result == ["STN_001", "OBJ_001", "STN_003"]

    def test_leg_with_cluster_sequences(self):
        """Test extracting activities from clusters with deprecated sequence fields."""
        mock_leg = MagicMock()
        mock_leg.activities = None  # No direct activities

        # Create clusters with deprecated sequence fields
        mock_cluster1 = MagicMock()
        mock_cluster1.name = "Cluster1"  # Add names for deprecation warnings
        mock_cluster1.activities = None  # No cluster activities
        mock_cluster1.sequence = ["STN_001", "STN_002"]  # Deprecated
        mock_cluster1.stations = None

        mock_cluster2 = MagicMock()
        mock_cluster2.name = "Cluster2"
        mock_cluster2.activities = None
        mock_cluster2.sequence = ["STN_003"]  # Deprecated
        mock_cluster2.stations = None

        mock_leg.clusters = [mock_cluster1, mock_cluster2]
        mock_leg.sequence = None
        mock_leg.stations = None

        with pytest.warns(DeprecationWarning, match="uses deprecated 'sequence' field"):
            result = _extract_activities_from_leg(mock_leg)

        assert result == ["STN_001", "STN_002", "STN_003"]

    def test_leg_with_empty_sequence(self):
        """Test handling of empty sequence."""
        mock_leg = MagicMock()
        mock_leg.sequence = []  # Empty sequence
        mock_leg.clusters = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_leg_with_none_sequence(self):
        """Test handling of None sequence."""
        mock_leg = MagicMock()
        mock_leg.sequence = None
        mock_leg.clusters = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_leg_without_sequence_attribute(self):
        """Test handling leg without sequence attribute."""
        mock_leg = MagicMock()
        # Remove sequence attribute
        del mock_leg.sequence
        mock_leg.clusters = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_leg_with_empty_clusters(self):
        """Test handling of empty clusters list."""
        mock_leg = MagicMock()
        mock_leg.sequence = None
        mock_leg.clusters = []  # Empty clusters
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_leg_with_none_clusters(self):
        """Test handling of None clusters."""
        mock_leg = MagicMock()
        mock_leg.sequence = None
        mock_leg.clusters = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_cluster_with_empty_sequence(self):
        """Test handling cluster with empty sequence."""
        mock_leg = MagicMock()
        mock_leg.sequence = None

        mock_cluster = MagicMock()
        mock_cluster.sequence = []  # Empty cluster sequence
        mock_leg.clusters = [mock_cluster]
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_cluster_without_sequence_attribute(self):
        """Test handling cluster without sequence attribute."""
        mock_leg = MagicMock()
        mock_leg.sequence = None

        mock_cluster = MagicMock()
        # Remove sequence attribute
        del mock_cluster.sequence
        mock_leg.clusters = [mock_cluster]
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        assert result == []

    def test_priority_clusters_over_sequence(self):
        """Test that clusters take priority over direct sequence (new priority order)."""
        mock_leg = MagicMock()
        mock_leg.activities = None  # No activities (Priority 1)

        # Create cluster that should be used (Priority 2)
        mock_cluster = MagicMock()
        mock_cluster.name = "TestCluster"  # Add name for potential warnings
        mock_cluster.activities = ["CLUSTER_001"]  # Use new activities field
        mock_cluster.sequence = None
        mock_cluster.stations = None
        mock_leg.clusters = [mock_cluster]

        mock_leg.sequence = ["SEQ_001"]  # Should be ignored due to lower priority
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        # Should use cluster activities, ignore direct sequence
        assert result == ["CLUSTER_001"]

    def test_priority_activities_over_all(self):
        """Test that leg.activities takes priority over all other fields."""
        mock_leg = MagicMock()
        mock_leg.activities = ["PRIORITY_1"]  # Should be used (Priority 1)

        # Create cluster with activities (would be Priority 2)
        mock_cluster = MagicMock()
        mock_cluster.activities = ["CLUSTER_ACT"]
        mock_cluster.sequence = ["CLUSTER_SEQ"]
        mock_cluster.stations = ["CLUSTER_STN"]
        mock_leg.clusters = [mock_cluster]

        mock_leg.sequence = ["SEQ_001"]  # Priority 3
        mock_leg.stations = ["STN_001"]  # Priority 4

        result = _extract_activities_from_leg(mock_leg)

        # Should only use leg.activities, ignore everything else
        assert result == ["PRIORITY_1"]

    def test_priority_cluster_activities_over_deprecated(self):
        """Test that cluster.activities takes priority over cluster deprecated fields."""
        mock_leg = MagicMock()
        mock_leg.activities = None  # No leg activities

        # Create cluster with mixed fields
        mock_cluster = MagicMock()
        mock_cluster.name = "TestCluster"
        mock_cluster.activities = ["NEW_ACT"]  # Should be used (cluster priority 1)
        mock_cluster.sequence = ["OLD_SEQ"]  # Should be ignored (cluster priority 2)
        mock_cluster.stations = ["OLD_STN"]  # Should be ignored (cluster priority 3)
        mock_leg.clusters = [mock_cluster]

        mock_leg.sequence = None
        mock_leg.stations = None

        result = _extract_activities_from_leg(mock_leg)

        # Should only use cluster.activities
        assert result == ["NEW_ACT"]
