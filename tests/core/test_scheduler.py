"""
Tests for core schedule generation functions.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.calculators.scheduler import generate_cruise_schedule


class TestGenerateCruiseSchedule:
    """Test the main cruise schedule generation function."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    @patch("cruiseplan.calculators.scheduler.generate_timeline")
    @patch("cruiseplan.core.cruise.Cruise")
    def test_generate_cruise_schedule_basic(
        self, mock_cruise_class, mock_generate_timeline, tmp_path
    ):
        """Test basic schedule generation."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise

        mock_config = MagicMock()
        mock_config.cruise_name = "Test Cruise"
        mock_config.description = "Test description"
        mock_config.legs = []
        mock_cruise.config = mock_config

        # Mock timeline with all required fields
        mock_timeline = [
            {
                "activity": "Station",
                "label": "STN_001",
                "duration_minutes": 60.0,
                "transit_dist_nm": 10.0,
                "operation_dist_nm": 0.0,
                "start_time": datetime(2028, 6, 1, 8, 0),
                "end_time": datetime(2028, 6, 1, 9, 0),
                "lat": 50.0,
                "lon": -40.0,
                "depth": 1000.0,
                "vessel_speed_kt": 10.0,
                "leg_name": "Test_Leg",
                "operation_type": "CTD",
                "action": "profile",
            },
            {
                "activity": "Transit",
                "label": "Transit to STN_002",
                "duration_minutes": 30.0,
                "transit_dist_nm": 5.0,
                "operation_dist_nm": 0.0,
                "start_time": datetime(2028, 6, 1, 9, 0),
                "end_time": datetime(2028, 6, 1, 9, 30),
                "lat": 51.0,
                "lon": -40.0,
                "depth": 0.0,
                "vessel_speed_kt": 10.0,
                "leg_name": "Test_Leg",
                "operation_type": "Transit",
                "action": None,
            },
        ]
        mock_generate_timeline.return_value = mock_timeline

        # Test
        result = generate_cruise_schedule(
            config_path="test.yaml",
            output_dir=tmp_path,
            formats=["csv"],
            validate_depths=False,
        )

        # Verify
        assert result["success"] is True
        assert result["total_activities"] == 2
        assert result["total_duration_hours"] == 1.5  # 90 minutes
        assert result["total_distance_nm"] == 15.0
        assert "csv" in result["formats_generated"]
        assert result["cruise_name"] == "Test Cruise"

    @patch("cruiseplan.core.validation.validate_configuration_file")
    @patch("cruiseplan.calculators.scheduler.generate_timeline")
    @patch("cruiseplan.core.cruise.Cruise")
    def test_generate_cruise_schedule_with_validation(
        self, mock_cruise_class, mock_generate_timeline, mock_validate, tmp_path
    ):
        """Test schedule generation with depth validation."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise

        mock_config = MagicMock()
        mock_config.cruise_name = "Test Cruise"
        mock_config.description = None
        mock_config.legs = []
        mock_cruise.config = mock_config

        mock_generate_timeline.return_value = []
        mock_validate.return_value = (True, [], ["Some depth warning"])

        # Test
        result = generate_cruise_schedule(
            config_path="test.yaml",
            output_dir=tmp_path,
            formats=["html"],
            validate_depths=True,
        )

        # Verify validation was called
        mock_validate.assert_called_once()
        assert "Some depth warning" in result["warnings"]

    @patch("cruiseplan.calculators.scheduler.generate_timeline")
    @patch("cruiseplan.core.cruise.Cruise")
    def test_generate_cruise_schedule_selected_leg(
        self, mock_cruise_class, mock_generate_timeline, tmp_path
    ):
        """Test schedule generation for selected leg."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise

        mock_config = MagicMock()
        mock_config.cruise_name = "Test Cruise"
        mock_config.description = None

        # Mock legs
        mock_leg1 = MagicMock()
        mock_leg1.name = "Leg1"
        mock_leg2 = MagicMock()
        mock_leg2.name = "Leg2"
        mock_config.legs = [mock_leg1, mock_leg2]

        mock_cruise.config = mock_config

        # Mock timeline with mixed leg activities
        mock_timeline = [
            {
                "activity": "Station",
                "leg_name": "Leg1",
                "duration_minutes": 60.0,
                "transit_dist_nm": 0,
                "operation_dist_nm": 0,
            },
            {
                "activity": "Station",
                "leg_name": "Leg2",
                "duration_minutes": 60.0,
                "transit_dist_nm": 0,
                "operation_dist_nm": 0,
            },
        ]
        mock_generate_timeline.return_value = mock_timeline

        # Test
        result = generate_cruise_schedule(
            config_path="test.yaml",
            output_dir=tmp_path,
            formats=["csv"],
            selected_leg="Leg1",
        )

        # Verify only Leg1 activities are included
        assert result["total_activities"] == 1
        assert result["selected_leg"] == "Leg1"

    @patch("cruiseplan.core.cruise.Cruise")
    def test_generate_cruise_schedule_nonexistent_leg(
        self, mock_cruise_class, tmp_path
    ):
        """Test error handling for nonexistent leg."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise

        mock_config = MagicMock()
        mock_config.cruise_name = "Test Cruise"
        mock_leg = MagicMock()
        mock_leg.name = "ExistingLeg"
        mock_config.legs = [mock_leg]
        mock_cruise.config = mock_config

        # Test
        with pytest.raises(ValueError, match="Leg 'NonexistentLeg' not found"):
            generate_cruise_schedule(
                config_path="test.yaml",
                output_dir=tmp_path,
                formats=["csv"],
                selected_leg="NonexistentLeg",
            )

    @patch("cruiseplan.core.validation.validate_configuration_file")
    @patch("cruiseplan.core.cruise.Cruise")
    def test_generate_cruise_schedule_validation_error(
        self, mock_cruise_class, mock_validate, tmp_path
    ):
        """Test error handling for validation failures."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise
        mock_cruise.config = MagicMock()

        mock_validate.return_value = (False, ["Validation error"], [])

        # Test
        with pytest.raises(RuntimeError, match="Configuration validation failed"):
            generate_cruise_schedule(
                config_path="test.yaml",
                output_dir=tmp_path,
                formats=["csv"],
                validate_depths=True,
            )


if __name__ == "__main__":
    pytest.main([__file__])
