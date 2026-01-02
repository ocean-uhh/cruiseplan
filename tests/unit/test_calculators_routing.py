"""Tests for cruiseplan.calculators.routing module."""

from unittest.mock import Mock

from cruiseplan.calculators.routing import (
    calculate_route_distance,
    optimize_composite_route,
)


class TestOptimizeCompositeRoute:
    """Test suite for optimize_composite_route function."""

    def test_empty_children_list(self):
        """Test with empty list of children operations."""
        result = optimize_composite_route([], {})
        assert result == 0.0

    def test_single_child_operation(self):
        """Test with single operation."""
        mock_child = Mock()
        mock_child.calculate_duration.return_value = 30.0
        rules = {}

        result = optimize_composite_route([mock_child], rules)

        assert result == 30.0
        mock_child.calculate_duration.assert_called_once_with(rules)

    def test_multiple_child_operations(self):
        """Test with multiple child operations."""
        mock_child1 = Mock()
        mock_child2 = Mock()
        mock_child3 = Mock()

        mock_child1.calculate_duration.return_value = 15.0
        mock_child2.calculate_duration.return_value = 25.0
        mock_child3.calculate_duration.return_value = 10.0

        rules = {"some": "rule"}
        children = [mock_child1, mock_child2, mock_child3]

        result = optimize_composite_route(children, rules)

        assert result == 50.0
        mock_child1.calculate_duration.assert_called_once_with(rules)
        mock_child2.calculate_duration.assert_called_once_with(rules)
        mock_child3.calculate_duration.assert_called_once_with(rules)

    def test_with_complex_rules(self):
        """Test that rules object is passed correctly to children."""
        mock_child = Mock()
        mock_child.calculate_duration.return_value = 42.0

        complex_rules = {
            "ship_speed": 12.0,
            "operation_type": "CTD",
            "depth_limit": 1000,
        }

        result = optimize_composite_route([mock_child], complex_rules)

        assert result == 42.0
        mock_child.calculate_duration.assert_called_once_with(complex_rules)

    def test_zero_duration_operations(self):
        """Test with operations that have zero duration."""
        mock_child1 = Mock()
        mock_child2 = Mock()

        mock_child1.calculate_duration.return_value = 0.0
        mock_child2.calculate_duration.return_value = 0.0

        result = optimize_composite_route([mock_child1, mock_child2], {})

        assert result == 0.0


class TestCalculateRouteDistance:
    """Test suite for calculate_route_distance function."""

    def test_placeholder_returns_zero(self):
        """Test that the placeholder function returns 0.0."""
        result = calculate_route_distance((50.0, -50.0), (51.0, -49.0))
        assert result == 0.0

    def test_with_none_points(self):
        """Test with None values for coordinates."""
        result = calculate_route_distance(None, None)
        assert result == 0.0

    def test_with_various_coordinate_formats(self):
        """Test with different coordinate input formats."""
        # Test different point formats (all should return 0.0 for now)
        assert calculate_route_distance([50.0, -50.0], [51.0, -49.0]) == 0.0
        assert calculate_route_distance((50.0, -50.0), (51.0, -49.0)) == 0.0
        assert calculate_route_distance("point1", "point2") == 0.0
        assert calculate_route_distance(123, 456) == 0.0
