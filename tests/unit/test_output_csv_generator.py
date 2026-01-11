"""
Unit tests for CSV generator module.
Tests CSV formatting, field mapping, and edge case handling.
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from cruiseplan.output.csv_generator import CSVGenerator, generate_csv_schedule
from cruiseplan.schema import CruiseConfig


class TestCSVGenerator:
    """Test the CSVGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = CSVGenerator()
        self.mock_config = MagicMock(spec=CruiseConfig)
        self.mock_config.cruise_name = "Test_Cruise_2024"

    def test_empty_timeline(self):
        """Test CSV generation with empty timeline."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, [], output_file
            )

            assert result == output_file
            assert output_file.exists()

            # Check that file has header but no data rows
            with open(output_file, encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

            assert len(rows) == 1  # Only header
            assert "activity" in rows[0]  # Header contains expected fields

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_basic_field_formatting(self):
        """Test CSV generation formats fields correctly."""
        timeline = [
            {
                "activity": "Station",
                "label": "TEST_STN",
                "start_time": datetime(2024, 1, 1, 10, 30),
                "end_time": datetime(2024, 1, 1, 12, 45),
                "duration_minutes": 135.6,  # Should become 2.3 hours
                "entry_lat": 45.123456,
                "entry_lon": -123.987654,
                "exit_lat": 45.123456,
                "exit_lon": -123.987654,
                "operation_depth": 1500.7,  # Should round to 1501
                "dist_nm": 0.0,
                "vessel_speed_kt": 0,
                "op_type": "station",
                "action": "profile",
                "leg_name": "Test_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            row = rows[0]

            # Test basic field mapping
            assert row["activity"] == "Station"
            assert row["label"] == "TEST_STN"
            assert row["leg_name"] == "Test_Leg"

            # Test formatting
            assert row["Duration [hrs]"] == "2.3"  # 135.6 / 60 rounded to 1 decimal
            assert row["Depth [m]"] == "1501"  # Rounded from 1500.7
            assert row["Vessel speed [kt]"] == "0"  # Station has 0 speed
            assert row["Transit dist [nm]"] == "0.0"
            assert row["operation_action"] == "Station profile"

            # Test coordinate formatting
            assert row["Lat [deg]"] == "45.123456"
            assert row["Lon [deg]"] == "-123.987654"

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_missing_fields_defaults(self):
        """Test CSV generation with missing optional fields."""
        timeline = [
            {
                "activity": "Station",
                "label": "Minimal_Station",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "entry_lat": 45.0,
                "entry_lon": -45.0,
                "exit_lat": 45.0,
                "exit_lon": -45.0,
                # Missing: operation_depth, water_depth, dist_nm, op_type, action, leg_name
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]

            # Test default values
            assert row["Depth [m]"] == "0"  # Default depth when missing
            assert row["Transit dist [nm]"] == "0.0"  # Default distance
            assert row["Vessel speed [kt]"] == "0"  # Station default speed
            assert row["operation_action"] == ""  # Empty when no op_type/action
            assert row["leg_name"] == ""  # Empty when missing

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_transit_formatting(self):
        """Test CSV generation for transit activities."""
        timeline = [
            {
                "activity": "Transit",
                "label": "Test_Transit",
                "start_time": datetime(2024, 1, 1, 8, 0),
                "end_time": datetime(2024, 1, 1, 12, 0),
                "duration_minutes": 240.0,
                "entry_lat": 50.0,
                "entry_lon": -50.0,
                "exit_lat": 51.0,
                "exit_lon": -49.0,
                "dist_nm": 25.5,
                "vessel_speed_kt": 8.0,
                "op_type": "transit",
                "leg_name": "Test_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["activity"] == "Transit"
            assert row["Vessel speed [kt]"] == "8.0"  # Transit has actual speed
            assert row["Transit dist [nm]"] == "25.5"
            assert row["Duration [hrs]"] == "4.0"

        finally:
            if output_file.exists():
                output_file.unlink()


def test_convenience_function():
    """Test the convenience function generate_csv_schedule."""
    mock_config = MagicMock(spec=CruiseConfig)
    timeline = [
        {
            "activity": "Station",
            "label": "STN_001",
            "start_time": datetime(2024, 1, 1, 12, 0),
            "end_time": datetime(2024, 1, 1, 13, 0),
            "duration_minutes": 60.0,
            "entry_lat": 45.0,
            "entry_lon": -45.0,
            "exit_lat": 45.0,
            "exit_lon": -45.0,
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
        output_file = Path(tmp_file.name)

    try:
        result = generate_csv_schedule(mock_config, timeline, output_file)
        assert result == output_file
        assert output_file.exists()

    finally:
        if output_file.exists():
            output_file.unlink()
