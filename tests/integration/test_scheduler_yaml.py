"""
Integration tests for the scheduler against real YAML fixture files.
"""

import pytest

from cruiseplan.core.cruise import CruiseInstance


class TestSchedulerWithYAMLFixtures:
    """Integration tests for scheduler with actual YAML configurations."""

    def test_scheduler_handles_missing_fixtures_gracefully(self):
        """Test that scheduler handles missing files appropriately."""
        from cruiseplan.schema.yaml_io import YAMLIOError

        with pytest.raises(YAMLIOError, match="YAML file not found"):
            CruiseInstance("tests/fixtures/nonexistent.yaml")
