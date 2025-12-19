"""
Integration tests for the scheduler against real YAML fixture files.
"""

from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation import CruiseConfigurationError
from cruiseplan.utils.config import ConfigLoader


class TestSchedulerWithYAMLFixtures:
    """Integration tests for scheduler with actual YAML configurations."""




    def test_scheduler_handles_missing_fixtures_gracefully(self):
        """Test that scheduler handles missing files appropriately."""
        with pytest.raises(CruiseConfigurationError):
            loader = ConfigLoader("tests/fixtures/nonexistent.yaml")
            loader.load()

