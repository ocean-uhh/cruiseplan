# tests/unit/test_operations_phase1.py
import pytest
from cruiseplan.core.operations import PointOperation, LineOperation
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
