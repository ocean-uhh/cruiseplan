"""
Integration tests for the scheduler against real YAML fixture files.
"""

import pytest

from cruiseplan.core.validation import CruiseConfigurationError
from cruiseplan.utils.config import ConfigLoader


class TestSchedulerWithYAMLFixtures:
    """Integration tests for scheduler with actual YAML configurations."""

    def test_scheduler_handles_missing_fixtures_gracefully(self):
        """Test that scheduler handles missing files appropriately."""
        with pytest.raises(CruiseConfigurationError):
            loader = ConfigLoader("tests/fixtures/nonexistent.yaml")
            loader.load()
