"""Tests for cruiseplan.core.operations module."""

from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.core.operations import (
    AreaOperation,
    BaseOperation,
    LineOperation,
    PointOperation,
)


class TestBaseOperation:
    """Test the abstract BaseOperation class."""

    def test_base_operation_is_abstract(self):
        """Test that BaseOperation cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOperation("test_op", "test comment")

    def test_base_operation_abstract_methods(self):
        """Test that abstract methods are properly defined."""
        # Check that the required abstract methods exist
        assert hasattr(BaseOperation, "calculate_duration")
        assert hasattr(BaseOperation, "get_entry_point")
        assert hasattr(BaseOperation, "get_exit_point")

        # Check they are abstract
        assert getattr(BaseOperation.calculate_duration, "__isabstractmethod__", False)
        assert getattr(BaseOperation.get_entry_point, "__isabstractmethod__", False)
        assert getattr(BaseOperation.get_exit_point, "__isabstractmethod__", False)


class TestPointOperation:
    """Test PointOperation class for stations and moorings."""

    def test_point_operation_initialization(self):
        """Test basic PointOperation initialization."""
        op = PointOperation(
            name="STN_001",
            position=(60.0, -20.0),
            operation_depth=500.0,
            duration=120.0,
            comment="Test station",
            op_type="station",
            action=None,
        )

        assert op.name == "STN_001"
        assert op.position == (60.0, -20.0)
        assert op.operation_depth == 500.0
        assert op.manual_duration == 120.0
        assert op.comment == "Test station"
        assert op.op_type == "station"
        assert op.action is None

    def test_point_operation_defaults(self):
        """Test PointOperation with default values."""
        op = PointOperation(name="STN_001", position=(60.0, -20.0))

        assert op.water_depth == 0.0
        assert op.manual_duration == 0.0
        assert op.comment is None
        assert op.op_type == "station"
        assert op.action is None

    def test_calculate_duration_manual_override(self):
        """Test duration calculation with manual override."""
        op = PointOperation(
            name="STN_001", position=(60.0, -20.0), duration=150.0  # Manual duration
        )

        # Mock rules object
        mock_rules = MagicMock()

        duration = op.calculate_duration(mock_rules)
        assert duration == 150.0

    def test_calculate_duration_station_ctd(self):
        """Test duration calculation for CTD stations."""
        op = PointOperation(
            name="STN_001",
            position=(60.0, -20.0),
            operation_depth=1000.0,
            op_type="station",
        )

        # Mock rules and config
        mock_config = MagicMock()
        mock_rules = MagicMock()
        mock_rules.config = mock_config

        # The duration calculator is imported inside the method
        # So we'll mock it at the import source
        with patch(
            "cruiseplan.calculators.duration.DurationCalculator"
        ) as mock_calc_class:
            mock_calc = MagicMock()
            mock_calc.calculate_ctd_time.return_value = 180.0
            mock_calc_class.return_value = mock_calc

            duration = op.calculate_duration(mock_rules)
            assert duration == 180.0
            mock_calc.calculate_ctd_time.assert_called_once_with(1000.0)

    def test_calculate_duration_mooring(self):
        """Test duration calculation for moorings."""
        op = PointOperation(
            name="MOOR_001",
            position=(60.0, -20.0),
            op_type="mooring",
            action="deployment",
        )

        mock_config = MagicMock()
        mock_config.default_mooring_duration = 240.0
        mock_rules = MagicMock()
        mock_rules.config = mock_config

        duration = op.calculate_duration(mock_rules)
        assert duration == 240.0

    def test_calculate_duration_mooring_no_default(self):
        """Test duration calculation for moorings without default."""
        op = PointOperation(name="MOOR_001", position=(60.0, -20.0), op_type="mooring")

        mock_config = MagicMock()
        # No default_mooring_duration attribute
        del mock_config.default_mooring_duration
        mock_rules = MagicMock()
        mock_rules.config = mock_config

        duration = op.calculate_duration(mock_rules)
        assert duration == 60.0  # Fallback default

    def test_calculate_duration_no_rules(self):
        """Test duration calculation with invalid rules."""
        op = PointOperation(name="STN_001", position=(60.0, -20.0))

        # Rules without config attribute
        mock_rules = MagicMock()
        del mock_rules.config

        duration = op.calculate_duration(mock_rules)
        assert duration == 0.0

    def test_get_entry_point(self):
        """Test getting entry point for point operation."""
        op = PointOperation(name="STN_001", position=(60.0, -20.0))

        entry_point = op.get_entry_point()
        assert entry_point == (60.0, -20.0)

    def test_get_exit_point(self):
        """Test getting exit point for point operation."""
        op = PointOperation(name="STN_001", position=(60.0, -20.0))

        exit_point = op.get_exit_point()
        assert exit_point == (60.0, -20.0)

    def test_from_pydantic_station(self):
        """Test creating PointOperation from StationDefinition."""
        # Mock StationDefinition
        mock_operation_type = MagicMock()
        mock_operation_type.value = "CTD"

        mock_station = MagicMock()
        mock_station.name = "STN_002"
        mock_station.latitude = 65.0
        mock_station.longitude = -25.0
        mock_station.operation_type = mock_operation_type
        mock_station.action = None
        mock_station.operation_depth = 800.0
        mock_station.water_depth = 1200.0
        mock_station.duration = 0.0
        mock_station.comment = "Deep CTD cast"

        op = PointOperation.from_pydantic(mock_station)

        assert op.name == "STN_002"
        assert op.position == (65.0, -25.0)
        assert op.operation_depth == 800.0  # Uses operation_depth
        assert op.comment == "Deep CTD cast"
        assert op.op_type == "CTD"
        assert op.action is None

    def test_from_pydantic_mooring(self):
        """Test creating PointOperation from mooring definition."""
        mock_operation_type = MagicMock()
        mock_operation_type.value = "mooring"

        mock_action = MagicMock()
        mock_action.value = "deployment"

        mock_mooring = MagicMock()
        mock_mooring.name = "MOOR_001"
        mock_mooring.latitude = 70.0
        mock_mooring.longitude = -30.0
        mock_mooring.operation_type = mock_operation_type
        mock_mooring.action = mock_action
        mock_mooring.operation_depth = None
        mock_mooring.water_depth = 2000.0
        mock_mooring.duration = 180.0
        mock_mooring.comment = "Mooring deployment"

        op = PointOperation.from_pydantic(mock_mooring)

        assert op.name == "MOOR_001"
        assert op.position == (70.0, -30.0)
        assert op.operation_depth == 2000.0  # Falls back to water_depth
        assert op.manual_duration == 180.0
        assert op.op_type == "mooring"
        assert op.action == "deployment"


class TestLineOperation:
    """Test LineOperation class for transects."""

    def test_line_operation_initialization(self):
        """Test basic LineOperation initialization."""
        route = [(60.0, -20.0), (61.0, -21.0), (62.0, -22.0)]
        op = LineOperation(
            name="TRANS_001", route=route, speed=12.0, comment="Transit to station area"
        )

        assert op.name == "TRANS_001"
        assert op.route == route
        assert op.speed == 12.0
        assert op.comment == "Transit to station area"

    def test_line_operation_defaults(self):
        """Test LineOperation with default values."""
        route = [(60.0, -20.0), (61.0, -21.0)]
        op = LineOperation(name="TRANS_001", route=route)

        assert op.speed == 10.0
        assert op.comment is None

    def test_calculate_duration_valid_route(self):
        """Test duration calculation for valid route."""
        route = [(60.0, -20.0), (61.0, -20.0)]  # ~111 km apart
        op = LineOperation(name="TRANS_001", route=route, speed=10.0)

        with patch(
            "cruiseplan.calculators.distance.haversine_distance"
        ) as mock_distance:
            mock_distance.return_value = 111.0  # km

            duration = op.calculate_duration(None)

            # 111 km * 0.539957 nm/km = ~59.9 nm
            # 59.9 nm / 10 knots = ~6 hours = 360 minutes
            assert duration > 300  # Should be around 360 minutes

    def test_calculate_duration_empty_route(self):
        """Test duration calculation for empty route."""
        op = LineOperation(name="TRANS_001", route=[])

        duration = op.calculate_duration(None)
        assert duration == 0.0

    def test_calculate_duration_single_point_route(self):
        """Test duration calculation for single point route."""
        route = [(60.0, -20.0)]
        op = LineOperation(name="TRANS_001", route=route)

        duration = op.calculate_duration(None)
        assert duration == 0.0

    def test_calculate_duration_with_rules_config(self):
        """Test duration calculation using rules config for speed."""
        route = [(60.0, -20.0), (61.0, -20.0)]
        op = LineOperation(name="TRANS_001", route=route, speed=0.0)  # No speed set

        mock_config = MagicMock()
        mock_config.default_vessel_speed = 8.0
        mock_rules = MagicMock()
        mock_rules.config = mock_config

        with patch(
            "cruiseplan.calculators.distance.haversine_distance"
        ) as mock_distance:
            mock_distance.return_value = 80.0  # km

            duration = op.calculate_duration(mock_rules)
            assert duration > 0  # Should calculate based on 8 knot speed

    def test_calculate_duration_fallback_speed(self):
        """Test duration calculation with fallback speed."""
        route = [(60.0, -20.0), (61.0, -20.0)]
        op = LineOperation(name="TRANS_001", route=route, speed=0.0)

        with patch(
            "cruiseplan.calculators.distance.haversine_distance"
        ) as mock_distance:
            mock_distance.return_value = 100.0  # km

            duration = op.calculate_duration(None)  # No rules
            assert duration > 0  # Should use 10.0 knot fallback

    def test_get_entry_point(self):
        """Test getting entry point for line operation."""
        route = [(60.0, -20.0), (61.0, -21.0), (62.0, -22.0)]
        op = LineOperation(name="TRANS_001", route=route)

        entry_point = op.get_entry_point()
        assert entry_point == (60.0, -20.0)

    def test_get_entry_point_empty_route(self):
        """Test getting entry point for empty route."""
        op = LineOperation(name="TRANS_001", route=[])

        entry_point = op.get_entry_point()
        assert entry_point == (0.0, 0.0)

    def test_get_exit_point(self):
        """Test getting exit point for line operation."""
        route = [(60.0, -20.0), (61.0, -21.0), (62.0, -22.0)]
        op = LineOperation(name="TRANS_001", route=route)

        exit_point = op.get_exit_point()
        assert exit_point == (62.0, -22.0)

    def test_get_exit_point_empty_route(self):
        """Test getting exit point for empty route."""
        op = LineOperation(name="TRANS_001", route=[])

        exit_point = op.get_exit_point()
        assert exit_point == (0.0, 0.0)

    def test_from_pydantic(self):
        """Test creating LineOperation from TransitDefinition."""
        # Mock GeoPoint objects
        mock_point1 = MagicMock()
        mock_point1.latitude = 55.0
        mock_point1.longitude = -15.0

        mock_point2 = MagicMock()
        mock_point2.latitude = 56.0
        mock_point2.longitude = -16.0

        mock_transit = MagicMock()
        mock_transit.name = "TRANS_002"
        mock_transit.route = [mock_point1, mock_point2]
        mock_transit.vessel_speed = 14.0
        mock_transit.comment = "Transit between areas"

        op = LineOperation.from_pydantic(mock_transit, default_speed=10.0)

        assert op.name == "TRANS_002"
        assert op.route == [(55.0, -15.0), (56.0, -16.0)]
        assert op.speed == 14.0
        assert op.comment == "Transit between areas"

    def test_from_pydantic_no_speed(self):
        """Test creating LineOperation with no speed specified."""
        mock_point = MagicMock()
        mock_point.latitude = 55.0
        mock_point.longitude = -15.0

        mock_transit = MagicMock()
        mock_transit.name = "TRANS_003"
        mock_transit.route = [mock_point]
        mock_transit.vessel_speed = None
        mock_transit.comment = None

        op = LineOperation.from_pydantic(mock_transit, default_speed=12.0)

        assert op.speed == 12.0  # Uses default


class TestAreaOperation:
    """Test AreaOperation class for area-based operations."""

    def test_area_operation_initialization(self):
        """Test basic AreaOperation initialization."""
        boundary = [(60.0, -20.0), (61.0, -20.0), (61.0, -21.0), (60.0, -21.0)]
        start_point = (60.0, -20.0)
        end_point = (61.0, -21.0)

        op = AreaOperation(
            name="AREA_001",
            boundary_polygon=boundary,
            area_km2=12345.0,
            duration=480.0,
            start_point=start_point,
            end_point=end_point,
            sampling_density=1.5,
            comment="Grid survey area",
        )

        assert op.name == "AREA_001"
        assert op.boundary_polygon == boundary
        assert op.area_km2 == 12345.0
        assert op.duration == 480.0
        assert op.start_point == start_point
        assert op.end_point == end_point
        assert op.sampling_density == 1.5
        assert op.comment == "Grid survey area"

    def test_area_operation_defaults(self):
        """Test AreaOperation with default values."""
        boundary = [(60.0, -20.0), (61.0, -21.0)]
        op = AreaOperation(name="AREA_001", boundary_polygon=boundary, area_km2=100.0)

        assert op.duration is None
        assert op.start_point == (60.0, -20.0)  # First corner
        assert op.end_point == (61.0, -21.0)  # Last corner
        assert op.sampling_density == 1.0
        assert op.comment is None

    def test_area_operation_empty_boundary(self):
        """Test AreaOperation with empty boundary."""
        op = AreaOperation(name="AREA_001", boundary_polygon=[], area_km2=0.0)

        assert op.start_point == (0.0, 0.0)
        assert op.end_point == (0.0, 0.0)

    def test_calculate_duration_with_duration(self):
        """Test duration calculation with specified duration."""
        boundary = [(60.0, -20.0), (61.0, -21.0)]
        op = AreaOperation(
            name="AREA_001", boundary_polygon=boundary, area_km2=100.0, duration=360.0
        )

        duration = op.calculate_duration(None)
        assert duration == 360.0

    def test_calculate_duration_no_duration(self):
        """Test duration calculation without specified duration raises error."""
        boundary = [(60.0, -20.0), (61.0, -21.0)]
        op = AreaOperation(name="AREA_001", boundary_polygon=boundary, area_km2=100.0)

        with pytest.raises(ValueError) as exc_info:
            op.calculate_duration(None)

        assert "requires user-specified duration" in str(exc_info.value)
        assert "AREA_001" in str(exc_info.value)

    def test_get_entry_point(self):
        """Test getting entry point for area operation."""
        boundary = [(60.0, -20.0), (61.0, -21.0)]
        start_point = (59.0, -19.0)
        op = AreaOperation(
            name="AREA_001",
            boundary_polygon=boundary,
            area_km2=100.0,
            start_point=start_point,
        )

        entry_point = op.get_entry_point()
        assert entry_point == (59.0, -19.0)

    def test_get_exit_point(self):
        """Test getting exit point for area operation."""
        boundary = [(60.0, -20.0), (61.0, -21.0)]
        end_point = (62.0, -22.0)
        op = AreaOperation(
            name="AREA_001",
            boundary_polygon=boundary,
            area_km2=100.0,
            end_point=end_point,
        )

        exit_point = op.get_exit_point()
        assert exit_point == (62.0, -22.0)

    def test_calculate_polygon_area_triangle(self):
        """Test polygon area calculation for triangle."""
        coords = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]

        area = AreaOperation._calculate_polygon_area(coords)
        assert area > 0  # Should return positive area

    def test_calculate_polygon_area_too_few_points(self):
        """Test polygon area calculation with insufficient points."""
        coords = [(0.0, 0.0), (1.0, 0.0)]

        area = AreaOperation._calculate_polygon_area(coords)
        assert area == 0.0

    def test_calculate_polygon_area_empty(self):
        """Test polygon area calculation with no points."""
        coords = []

        area = AreaOperation._calculate_polygon_area(coords)
        assert area == 0.0

    def test_from_pydantic_success(self):
        """Test creating AreaOperation from AreaDefinition."""
        # Mock GeoPoint objects
        mock_point1 = MagicMock()
        mock_point1.latitude = 60.0
        mock_point1.longitude = -20.0

        mock_point2 = MagicMock()
        mock_point2.latitude = 61.0
        mock_point2.longitude = -20.0

        mock_point3 = MagicMock()
        mock_point3.latitude = 61.0
        mock_point3.longitude = -21.0

        mock_area = MagicMock()
        mock_area.name = "GRID_SURVEY"
        mock_area.corners = [mock_point1, mock_point2, mock_point3]
        mock_area.duration = 240.0
        mock_area.comment = "Systematic grid survey"

        op = AreaOperation.from_pydantic(mock_area)

        assert op.name == "GRID_SURVEY"
        assert op.boundary_polygon == [(60.0, -20.0), (61.0, -20.0), (61.0, -21.0)]
        assert op.duration == 240.0
        assert op.start_point == (60.0, -20.0)  # First corner
        assert op.end_point == (61.0, -21.0)  # Last corner
        assert op.comment == "Systematic grid survey"
        assert op.area_km2 > 0  # Should calculate area

    def test_from_pydantic_no_duration(self):
        """Test creating AreaOperation without duration raises error."""
        mock_point = MagicMock()
        mock_point.latitude = 60.0
        mock_point.longitude = -20.0

        mock_area = MagicMock()
        mock_area.name = "GRID_SURVEY"
        mock_area.corners = [mock_point]
        mock_area.duration = None
        mock_area.comment = None

        with pytest.raises(ValueError) as exc_info:
            AreaOperation.from_pydantic(mock_area)

        assert "requires user-specified duration" in str(exc_info.value)
        assert "GRID_SURVEY" in str(exc_info.value)

    def test_from_pydantic_empty_corners(self):
        """Test creating AreaOperation with empty corners."""
        mock_area = MagicMock()
        mock_area.name = "EMPTY_AREA"
        mock_area.corners = []
        mock_area.duration = 120.0
        mock_area.comment = None

        op = AreaOperation.from_pydantic(mock_area)

        assert op.name == "EMPTY_AREA"
        assert op.boundary_polygon == []
        assert op.start_point == (0.0, 0.0)
        assert op.end_point == (0.0, 0.0)
        assert op.area_km2 == 0.0
