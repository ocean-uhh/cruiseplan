"""
Unit tests for CSV generator module.
Tests CSV formatting, coordinate conversion, and edge case handling.
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from cruiseplan.core.validation import CruiseConfig
from cruiseplan.output.csv_generator import CSVGenerator, generate_csv_schedule


class TestCSVGenerator:
    """Test the CSVGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = CSVGenerator()
        self.mock_config = MagicMock(spec=CruiseConfig)
        self.mock_config.cruise_name = "Test_Cruise_2024"

    def test_init(self):
        """Test CSVGenerator initialization."""
        generator = CSVGenerator()
        assert generator is not None

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

    def test_basic_station_activity(self):
        """Test CSV generation with basic station activity."""
        timeline = [
            {
                "activity": "Station",
                "label": "STN_001",
                "start_time": datetime(2024, 1, 1, 10, 0),
                "end_time": datetime(2024, 1, 1, 12, 0),
                "duration_minutes": 120.0,
                "lat": 45.123456,
                "lon": -123.654321,
                "depth": 1500.0,
                "transit_dist_nm": 25.5,
                "vessel_speed_kt": 0,  # Station operations have 0 vessel speed
                "operation_type": "station",
                "action": "profile",
                "leg_name": "Test_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            assert result == output_file

            # Read and verify CSV content
            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 1
            row = rows[0]

            assert row["activity"] == "Station"
            assert row["label"] == "STN_001"
            assert row["operation_action"] == "Station profile"
            assert row["Duration [hrs]"] == "2.0"
            assert row["Depth [m]"] == "1500"
            assert row["Vessel speed [kt]"] == "0"
            assert row["Transit dist [nm]"] == "25.5"
            assert row["Lat [deg]"] == "45.123456"
            assert row["Lon [deg]"] == "-123.654321"

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_transit_activity_with_speed(self):
        """Test CSV generation with transit activity that has vessel speed."""
        timeline = [
            {
                "activity": "Transit",
                "label": "Survey_Line_1",
                "start_time": datetime(2024, 1, 1, 8, 0),
                "end_time": datetime(2024, 1, 1, 14, 0),
                "duration_minutes": 360.0,
                "lat": 50.0,
                "lon": -50.0,
                "depth": 0.0,
                "transit_dist_nm": 0.0,
                "vessel_speed_kt": 5.5,  # Scientific transit with specific speed
                "operation_type": "underway",
                "action": "ADCP",
                "leg_name": "Survey_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["activity"] == "Transit"
            assert row["operation_action"] == "Underway ADCP"
            assert row["Vessel speed [kt]"] == "5.5"
            assert row["Duration [hrs]"] == "6.0"

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_area_activity(self):
        """Test CSV generation with area activity."""
        timeline = [
            {
                "activity": "Area",
                "label": "Survey_Area_1",
                "start_time": datetime(2024, 1, 2, 9, 0),
                "end_time": datetime(2024, 1, 2, 11, 0),
                "duration_minutes": 120.0,
                "lat": 55.0,  # Center point
                "lon": -45.0,
                "depth": 0.0,
                "transit_dist_nm": 15.0,
                "vessel_speed_kt": 0,  # Area operations have 0 vessel speed
                "operation_type": "survey",
                "action": "bathymetry",
                "leg_name": "Survey_Leg",
                "corners": [
                    {"latitude": 54.5, "longitude": -45.5},
                    {"latitude": 55.5, "longitude": -45.5},
                    {"latitude": 55.5, "longitude": -44.5},
                    {"latitude": 54.5, "longitude": -44.5},
                ],
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["activity"] == "Area"
            assert row["operation_action"] == "Survey bathymetry"
            assert (
                row["Vessel speed [kt]"] == "0"
            )  # Area operations have 0 vessel speed

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_coordinate_conversion_edge_cases(self):
        """Test coordinate conversion for edge cases."""
        timeline = [
            {
                "activity": "Station",
                "label": "Equator_Station",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "lat": 0.0,  # Equator
                "lon": 180.0,  # International date line
                "depth": 5000.0,
                "transit_dist_nm": 0.0,
                "vessel_speed_kt": 0,
                "operation_type": "station",
                "action": "profile",
                "leg_name": "Edge_Case_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["Lat [deg]"] == "0.0"
            assert row["Lon [deg]"] == "180.0"
            assert row["Lat [deg_rounded]"] == "0"
            assert row["Lat [min]"] == "0.0"
            assert row["Lon [deg_rounded]"] == "180"
            assert row["Lon [min]"] == "0.0"

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_negative_coordinates(self):
        """Test coordinate conversion for negative coordinates."""
        timeline = [
            {
                "activity": "Station",
                "label": "South_Station",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "lat": -45.123456,  # Southern hemisphere
                "lon": -123.987654,  # Western hemisphere
                "depth": 2000.0,
                "transit_dist_nm": 0.0,
                "vessel_speed_kt": 0,
                "operation_type": "station",
                "action": "profile",
                "leg_name": "South_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["Lat [deg]"] == "-45.123456"
            assert row["Lon [deg]"] == "-123.987654"
            # Verify that coordinate conversion handled negative values correctly
            assert int(row["Lat [deg_rounded]"]) == -45
            assert int(row["Lon [deg_rounded]"]) == -123

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_missing_optional_fields(self):
        """Test CSV generation with missing optional fields."""
        timeline = [
            {
                "activity": "Station",
                "label": "Minimal_Station",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "lat": 45.0,
                "lon": -45.0,
                # Missing: depth, transit_dist_nm, vessel_speed_kt, operation_type, action, leg_name
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["Depth [m]"] == "0"  # Default depth
            assert row["Transit dist [nm]"] == "0.0"  # Default transit distance
            assert row["Vessel speed [kt]"] == "0"  # Station has 0 speed
            assert row["operation_action"] == ""  # Empty when no operation_type/action
            assert row["leg_name"] == ""  # Empty when missing

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_special_characters_in_labels(self):
        """Test CSV generation with special characters in labels."""
        timeline = [
            {
                "activity": "Station",
                "label": 'STN_001_Test,With"Comma&Quote',
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "lat": 45.0,
                "lon": -45.0,
                "depth": 1000.0,
                "transit_dist_nm": 0.0,
                "vessel_speed_kt": 0,
                "operation_type": "station",
                "action": "profile",
                "leg_name": "Test_Leg",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            # Verify file was created and CSV parsing handles special characters
            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            row = rows[0]
            assert row["label"] == 'STN_001_Test,With"Comma&Quote'

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_multiple_activities(self):
        """Test CSV generation with multiple different activity types."""
        timeline = [
            {
                "activity": "Station",
                "label": "STN_001",
                "start_time": datetime(2024, 1, 1, 10, 0),
                "end_time": datetime(2024, 1, 1, 12, 0),
                "duration_minutes": 120.0,
                "lat": 45.0,
                "lon": -45.0,
                "depth": 1000.0,
                "transit_dist_nm": 0.0,
                "vessel_speed_kt": 0,
                "operation_type": "station",
                "action": "profile",
                "leg_name": "Leg1",
            },
            {
                "activity": "Transit",
                "label": "Survey_Line",
                "start_time": datetime(2024, 1, 1, 14, 0),
                "end_time": datetime(2024, 1, 1, 18, 0),
                "duration_minutes": 240.0,
                "lat": 46.0,
                "lon": -46.0,
                "depth": 0.0,
                "transit_dist_nm": 0.0,
                "vessel_speed_kt": 8.0,
                "operation_type": "underway",
                "action": "ADCP",
                "leg_name": "Leg1",
            },
            {
                "activity": "Mooring",
                "label": "MOOR_001",
                "start_time": datetime(2024, 1, 2, 8, 0),
                "end_time": datetime(2024, 1, 2, 11, 0),
                "duration_minutes": 180.0,
                "lat": 47.0,
                "lon": -47.0,
                "depth": 3000.0,
                "transit_dist_nm": 25.0,
                "vessel_speed_kt": 0,
                "operation_type": "mooring",
                "action": "deployment",
                "leg_name": "Leg1",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_csv(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == 3

            # Verify each activity type
            assert rows[0]["activity"] == "Station"
            assert rows[0]["Vessel speed [kt]"] == "0"

            assert rows[1]["activity"] == "Transit"
            assert rows[1]["Vessel speed [kt]"] == "8.0"

            assert rows[2]["activity"] == "Mooring"
            assert rows[2]["Vessel speed [kt]"] == "0"
            assert rows[2]["operation_action"] == "Mooring deployment"

        finally:
            if output_file.exists():
                output_file.unlink()


def test_generate_csv_schedule_convenience_function():
    """Test the convenience function generate_csv_schedule."""
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "Test_Cruise"

    timeline = [
        {
            "activity": "Station",
            "label": "STN_001",
            "start_time": datetime(2024, 1, 1, 12, 0),
            "end_time": datetime(2024, 1, 1, 13, 0),
            "duration_minutes": 60.0,
            "lat": 45.0,
            "lon": -45.0,
            "depth": 1000.0,
            "transit_dist_nm": 0.0,
            "vessel_speed_kt": 0,
            "operation_type": "station",
            "action": "profile",
            "leg_name": "Test_Leg",
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp_file:
        output_file = Path(tmp_file.name)

    try:
        result = generate_csv_schedule(mock_config, timeline, output_file)

        assert result == output_file
        assert output_file.exists()

        # Verify content was written
        with open(output_file, encoding="utf-8") as f:
            content = f.read()
            assert "STN_001" in content

    finally:
        if output_file.exists():
            output_file.unlink()
