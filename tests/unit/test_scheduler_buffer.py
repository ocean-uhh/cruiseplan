"""Unit tests for scheduler buffer_time (contingency) block insertion."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from cruiseplan.timeline.scheduler import TimelineGenerator


def _make_generator():
    """Create a minimal TimelineGenerator with mocked config."""
    gen = TimelineGenerator.__new__(TimelineGenerator)
    gen.config = MagicMock()
    gen.config.default_vessel_speed = 10.0
    gen.current_time = datetime(2028, 6, 1, 12, 0)
    return gen


def _make_leg(name="Leg 1", buffer_time=None):
    leg = MagicMock()
    leg.name = name
    leg.buffer_time = buffer_time
    return leg


def _make_operation(lat=70.0, lon=-10.0):
    op = MagicMock()
    entry = MagicMock()
    exit_ = MagicMock()
    entry.latitude = lat
    entry.longitude = lon
    exit_.latitude = lat + 0.1
    exit_.longitude = lon + 0.1
    op.get_coordinates.return_value = (entry, exit_)
    return op


class TestCreateBufferActivity:
    def test_duration_matches_input(self):
        gen = _make_generator()
        result = gen._create_buffer_activity(_make_leg(), _make_operation(), 360.0)
        assert result.duration_minutes == 360.0

    def test_op_type_is_buffer(self):
        gen = _make_generator()
        result = gen._create_buffer_activity(_make_leg(), _make_operation(), 60.0)
        assert result.op_type == "buffer"
        assert result.activity == "Buffer"

    def test_position_taken_from_operation_exit(self):
        gen = _make_generator()
        op = _make_operation(lat=72.5, lon=-15.3)
        result = gen._create_buffer_activity(_make_leg(), op, 60.0)
        # Position is exit point of last operation (lat+0.1, lon+0.1)
        assert result.entry_lat == pytest.approx(72.6)
        assert result.entry_lon == pytest.approx(-15.2)
        assert result.exit_lat == result.entry_lat
        assert result.exit_lon == result.entry_lon

    def test_zero_distance(self):
        gen = _make_generator()
        result = gen._create_buffer_activity(_make_leg(), _make_operation(), 60.0)
        assert result.dist_nm == 0.0

    def test_advances_current_time(self):
        gen = _make_generator()
        t0 = gen.current_time
        gen._create_buffer_activity(_make_leg(), _make_operation(), 120.0)
        assert gen.current_time == t0 + timedelta(minutes=120.0)

    def test_start_and_end_times(self):
        gen = _make_generator()
        t0 = gen.current_time
        result = gen._create_buffer_activity(_make_leg(), _make_operation(), 90.0)
        assert result.start_time == t0
        assert result.end_time == t0 + timedelta(minutes=90.0)

    def test_leg_name_on_record(self):
        gen = _make_generator()
        result = gen._create_buffer_activity(
            _make_leg(name="Mooring Leg"), _make_operation(), 60.0
        )
        assert result.leg_name == "Mooring Leg"
