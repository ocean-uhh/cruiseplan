# tests/unit/test_operations_phase1.py
from unittest.mock import Mock

import pytest

from cruiseplan.core.leg import Leg
from cruiseplan.core.operations import (
    AreaOperation,
    BaseOperation,
    CompositeOperation,
    PointOperation,
)
from cruiseplan.data.bathymetry import BathymetryManager


def test_point_operation_logic():
    """Verify PointOperation behaves as a domain object."""
    p = PointOperation(name="Test", position=(10, 20), duration=60)
    assert p.calculate_duration(None) == 60
    assert p.op_type == "station"


def test_bathymetry_mock_fallback():
    """Verify the system degrades gracefully to Mock mode."""
    # Point to a non-existent directory to force mock
    bathy = BathymetryManager(data_dir="/tmp/nonexistent")

    depth = bathy.get_depth_at_point(50.0, -20.0)

    # Check it returns a negative float (water)
    assert isinstance(depth, float)
    assert depth < 0
    # Check consistency (deterministic mock)
    assert depth == bathy.get_depth_at_point(50.0, -20.0)


class TestCompositeOperation:

    def setup_method(self):
        # Mock a BaseOperation that returns a fixed duration
        self.mock_op_duration = 10.0
        self.mock_op = Mock(spec=BaseOperation)
        self.mock_op.calculate_duration.return_value = self.mock_op_duration
        self.rules = Mock()  # Mock the rules object passed to duration calculations

    def test_composite_sequential_duration(self):
        """Test 'sequential' strategy: duration is the simple sum of children."""
        children = [self.mock_op, self.mock_op, self.mock_op]
        composite = CompositeOperation(
            name="TestComposite", children=children, scheduling_strategy="sequential"
        )
        expected_duration = len(children) * self.mock_op_duration
        assert composite.calculate_duration(self.rules) == expected_duration
        # Check that the duration method was called on each child
        assert self.mock_op.calculate_duration.call_count == 3

    def test_composite_spatial_interleaved_calls_optimizer(self):
        """Test 'spatial_interleaved' strategy returns simple sum via placeholder."""
        children = [self.mock_op, self.mock_op, self.mock_op]
        composite = CompositeOperation(
            name="TestComposite",
            children=children,
            scheduling_strategy="spatial_interleaved",
        )
        # Expected duration is now the simple sum, as defined in the placeholder function
        expected_duration = len(children) * self.mock_op_duration

        # This will now call the real, placeholder optimize_composite_route
        assert composite.calculate_duration(self.rules) == expected_duration

        # The children's calculate_duration should be called within the placeholder
        assert self.mock_op.calculate_duration.call_count == 3

    def test_composite_day_night_split_placeholder(self):
        """Test 'day_night_split' strategy uses the internal placeholder logic."""
        children = [self.mock_op, self.mock_op]
        composite = CompositeOperation(
            name="TestComposite",
            children=children,
            scheduling_strategy="day_night_split",
        )

        # Note: Since the internal method _calculate_day_night_duration is currently
        # a placeholder that just sums durations, the test should reflect that.
        expected_duration = len(children) * self.mock_op_duration
        assert composite.calculate_duration(self.rules) == expected_duration

    def test_composite_empty_children_duration(self):
        """Duration should be 0.0 if the children list is empty."""
        composite = CompositeOperation(name="Empty", children=[])
        assert composite.calculate_duration(self.rules) == 0.0


class TestAreaOperation:

    def setup_method(self):
        self.rules = Mock()

    def test_area_operation_initialization(self):
        """Verify all attributes are correctly initialized."""
        polygon = [(50.0, -10.0), (51.0, -10.0), (50.5, -9.0)]
        area_op = AreaOperation(
            name="TestGrid",
            boundary_polygon=polygon,
            area_km2=500.5,
            sampling_density=2.5,
            comment="Survey Area 1",
        )
        assert area_op.name == "TestGrid"
        assert area_op.area_km2 == 500.5
        assert area_op.sampling_density == 2.5
        assert area_op.comment == "Survey Area 1"
        assert len(area_op.boundary_polygon) == 3

    def test_area_operation_duration_calculation(self):
        """Verify duration calculation uses user-specified duration."""
        area_km2 = 1000.0
        sampling_density = 0.5
        user_duration = 480.0  # 8 hours
        area_op = AreaOperation(
            name="TestArea",
            boundary_polygon=[],
            area_km2=area_km2,
            sampling_density=sampling_density,
            duration=user_duration,  # User-specified duration required
        )
        # AreaOperation now requires user-specified duration
        assert area_op.calculate_duration(self.rules) == user_duration

    def test_area_operation_requires_duration(self):
        """Verify AreaOperation raises error when duration is not specified."""
        area_op = AreaOperation(
            name="TestArea",
            boundary_polygon=[],
            area_km2=1000.0,
            sampling_density=0.5,
            # duration=None  # No duration specified
        )
        # Should raise ValueError when duration is not provided
        with pytest.raises(
            ValueError,
            match="Area operation 'TestArea' requires user-specified duration",
        ):
            area_op.calculate_duration(self.rules)


class TestLeg:

    def setup_method(self):
        # Mock Operations
        self.mock_op_duration = 5.0
        self.mock_op = Mock(spec=BaseOperation)
        self.mock_op.calculate_duration.return_value = self.mock_op_duration

        # Mock Composite
        self.mock_comp_duration = 20.0
        self.mock_comp = Mock(spec=CompositeOperation)
        self.mock_comp.calculate_duration.return_value = self.mock_comp_duration
        self.mock_comp.children = [
            self.mock_op,
            self.mock_op,
        ]  # Used by get_all_operations

        # Mock Rules
        self.rules = Mock()
        # Ensure StrategyEnum is mockable (if it's not a real implementation yet)
        self.mock_strategy_enum = Mock(value="sequential")

    def test_leg_initialization(self):
        """Verify leg attributes are initialized correctly."""
        leg = Leg(name="L1", strategy=self.mock_strategy_enum, ordered=False)
        assert leg.name == "L1"
        assert leg.ordered is False
        assert leg.operations == []
        assert leg.composites == []

    def test_add_operations_and_composites(self):
        """Test adding both simple and composite operations."""
        leg = Leg(name="L1")
        leg.add_operation(self.mock_op)
        leg.add_composite(self.mock_comp)

        assert len(leg.operations) == 1
        assert len(leg.composites) == 1

    def test_calculate_total_duration(self):
        """Total duration should sum direct operations and composite operations."""
        leg = Leg(name="L1")
        # Add 2 direct ops (2 * 5.0 = 10.0)
        leg.add_operation(self.mock_op)
        leg.add_operation(self.mock_op)
        # Add 1 composite (1 * 20.0 = 20.0)
        leg.add_composite(self.mock_comp)

        expected_total = 10.0 + 20.0
        assert leg.calculate_total_duration(self.rules) == expected_total

        # Check that duration methods were called correctly
        assert self.mock_op.calculate_duration.call_count == 2
        assert self.mock_comp.calculate_duration.call_count == 1

    def test_get_all_operations_flattening(self):
        """Test that all operations, including children of composites, are flattened."""
        leg = Leg(name="L1")
        # Direct Ops: 1
        leg.add_operation(self.mock_op)
        # Composites: 1 (which has 2 children)
        leg.add_composite(self.mock_comp)

        # Total expected: 1 direct + 2 children = 3
        all_ops = leg.get_all_operations()
        assert len(all_ops) == 3

        # Ensure the list starts with direct ops, followed by composite children (as per implementation)
        assert all_ops[0] == self.mock_op  # The direct op
        # The next two are the children of the composite, which are also self.mock_op
        assert all_ops[1] == self.mock_op
        assert all_ops[2] == self.mock_op

    def test_get_effective_speed_inheritance(self):
        """Test Leg-specific speed overrides default speed."""
        leg = Leg(name="L1")
        default_speed = 10.0

        # Case 1: Leg-specific speed is set
        leg.vessel_speed = 12.5
        assert leg.get_effective_speed(default_speed) == 12.5

        # Case 2: Leg-specific speed is NOT set (fallback)
        leg.vessel_speed = None
        assert leg.get_effective_speed(default_speed) == default_speed
