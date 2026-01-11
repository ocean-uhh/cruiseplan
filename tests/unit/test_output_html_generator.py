"""
Unit tests for HTML generator module.
Tests HTML generation, statistics calculation, and table formatting.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cruiseplan.calculators.scheduler import calculate_timeline_statistics
from cruiseplan.output.html_generator import (
    HTMLGenerator,
    _convert_decimal_to_deg_min_html,
    generate_html_schedule,
)
from cruiseplan.schema import CruiseConfig


class TestConversionFunctions:
    """Test utility conversion functions."""

    def test_convert_decimal_to_deg_min_html_positive(self):
        """Test coordinate conversion for positive coordinates."""
        result = _convert_decimal_to_deg_min_html(45.123456)
        assert result == "45 07.407"

    def test_convert_decimal_to_deg_min_html_negative(self):
        """Test coordinate conversion for negative coordinates."""
        result = _convert_decimal_to_deg_min_html(-123.987654)
        assert result == "-123 59.259"

    def test_convert_decimal_to_deg_min_html_zero(self):
        """Test coordinate conversion for zero."""
        result = _convert_decimal_to_deg_min_html(0.0)
        assert result == "00 00.000"

    def test_convert_decimal_to_deg_min_html_edge_cases(self):
        """Test coordinate conversion for edge cases."""
        # Exactly on degree boundary
        result = _convert_decimal_to_deg_min_html(45.0)
        assert result == "45 00.000"

        # Small fractional part
        result = _convert_decimal_to_deg_min_html(1.000001)
        assert result == "01 00.000"


@pytest.mark.skip(
    reason="Obsolete after scheduler refactor - _calculate_summary_statistics moved to scheduler.py"
)
class TestSummaryStatistics:
    """Test summary statistics calculation."""

    def test_calculate_summary_statistics_empty_timeline(self):
        """Test statistics calculation with empty timeline."""
        stats = calculate_timeline_statistics([])

        # All counts should be zero
        assert stats["moorings"]["count"] == 0
        assert stats["stations"]["count"] == 0
        assert stats["surveys"]["count"] == 0
        assert stats["areas"]["count"] == 0

        # All durations should be zero
        assert stats["moorings"]["total_duration_h"] == 0
        assert stats["stations"]["total_duration_h"] == 0
        assert stats["surveys"]["total_duration_h"] == 0
        assert stats["areas"]["total_duration_h"] == 0

    def test_calculate_summary_statistics_station_only(self):
        """Test statistics calculation with station activities only."""
        timeline = [
            {
                "activity": "STN_001",
                "duration_minutes": 120.0,
                "depth": 1000.0,
                "action": "profile",
                "operation_class": "PointOperation",
                "op_type": "station",
                "dist_nm": 0.0,
            },
            {
                "activity": "STN_002",
                "duration_minutes": 90.0,
                "depth": 1500.0,
                "action": "profile",
                "operation_class": "PointOperation",
                "op_type": "station",
                "dist_nm": 0.0,
            },
        ]

        stats = calculate_timeline_statistics(timeline)

        assert stats["stations"]["count"] == 2
        assert stats["stations"]["total_duration_h"] == 3.5  # (120 + 90) / 60
        assert stats["stations"]["avg_duration_h"] == 1.75
        assert stats["stations"]["avg_depth_m"] == 1250.0  # (1000 + 1500) / 2

        # Other categories should be zero
        assert stats["moorings"]["count"] == 0
        assert stats["surveys"]["count"] == 0

    def test_calculate_summary_statistics_mooring_only(self):
        """Test statistics calculation with mooring activities only."""
        timeline = [
            {"activity": "Mooring", "duration_minutes": 180.0, "action": "deployment"},
            {"activity": "Mooring", "duration_minutes": 240.0, "action": "recovery"},
        ]

        stats = calculate_timeline_statistics(timeline)

        assert stats["moorings"]["count"] == 2
        assert stats["moorings"]["total_duration_h"] == 7.0  # (180 + 240) / 60
        assert stats["moorings"]["avg_duration_h"] == 3.5

    def test_calculate_summary_statistics_area_operations(self):
        """Test statistics calculation with area operations."""
        timeline = [
            {"activity": "Area", "duration_minutes": 120.0, "action": "bathymetry"},
            {"activity": "Area", "duration_minutes": 180.0, "action": "survey"},
        ]

        stats = calculate_timeline_statistics(timeline)

        assert stats["areas"]["count"] == 2
        assert stats["areas"]["total_duration_h"] == 5.0  # (120 + 180) / 60
        assert stats["areas"]["avg_duration_h"] == 2.5

    def test_calculate_summary_statistics_scientific_transits(self):
        """Test statistics calculation with scientific transects."""
        timeline = [
            {
                "activity": "Transit",
                "duration_minutes": 240.0,
                "operation_dist_nm": 30.0,
                "action": "ADCP",  # Scientific transit
            },
            {
                "activity": "Transit",
                "duration_minutes": 180.0,
                "operation_dist_nm": 20.0,
                "action": "bathymetry",  # Scientific transit
            },
        ]

        stats = calculate_timeline_statistics(timeline)

        assert stats["surveys"]["count"] == 2
        assert stats["surveys"]["total_duration_h"] == 7.0  # (240 + 180) / 60
        assert stats["surveys"]["avg_duration_h"] == 3.5
        assert stats["surveys"]["total_distance_nm"] == 50.0  # 30 + 20
        assert stats["surveys"]["avg_distance_nm"] == 25.0

    def test_calculate_summary_statistics_navigation_transits(self):
        """Test statistics calculation with navigation transits."""
        timeline = [
            {
                "activity": "Transit",
                "duration_minutes": 120.0,
                "dist_nm": 15.0,
                # No action field - navigation transit
            },
            {
                "activity": "Transit",
                "duration_minutes": 180.0,
                "dist_nm": 25.0,
                # No action field - navigation transit
            },
            {
                "activity": "Transit",
                "duration_minutes": 240.0,
                "dist_nm": 35.0,
                # No action field - navigation transit
            },
        ]

        stats = calculate_timeline_statistics(timeline)

        # With new timeline-based categorization, all navigation transits go to within_area
        # unless they are explicitly Port_Departure/Port_Arrival activities
        assert (
            stats["port_area"]["total_duration_h"] == 0.0
        )  # No explicit port activities
        assert stats["port_area"]["total_distance_nm"] == 0.0
        assert stats["within_area"]["total_duration_h"] == 9.0  # (120 + 180 + 240) / 60
        assert stats["within_area"]["total_distance_nm"] == 75.0  # 15 + 25 + 35

    def test_calculate_summary_statistics_mixed_activities(self):
        """Test statistics calculation with mixed activity types."""
        timeline = [
            {
                "activity": "Station",
                "duration_minutes": 120.0,
                "depth": 1000.0,
                "action": "profile",
            },
            {"activity": "Mooring", "duration_minutes": 180.0, "action": "deployment"},
            {
                "activity": "Transit",
                "duration_minutes": 240.0,
                "operation_dist_nm": 30.0,
                "action": "ADCP",
            },
            {"activity": "Area", "duration_minutes": 150.0, "action": "bathymetry"},
            {
                "activity": "Transit",
                "duration_minutes": 90.0,
                "dist_nm": 10.0,
                # Navigation transit
            },
        ]

        stats = calculate_timeline_statistics(timeline)

        assert stats["stations"]["count"] == 1
        assert stats["moorings"]["count"] == 1
        assert stats["surveys"]["count"] == 1
        assert stats["areas"]["count"] == 1

        # Check that all durations are calculated correctly
        total_scientific_h = (120 + 180 + 240 + 150) / 60  # 11.5 hours
        total_navigation_h = 90 / 60  # 1.5 hours


class TestHTMLGenerator:
    """Test the HTMLGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = HTMLGenerator()
        self.mock_config = MagicMock(spec=CruiseConfig)
        self.mock_config.cruise_name = "Test_Cruise_2024"
        self.mock_config.description = "Test cruise description"

    def test_init(self):
        """Test HTMLGenerator initialization."""
        generator = HTMLGenerator()
        assert generator is not None

    def test_empty_timeline(self):
        """Test HTML generation with empty timeline."""
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, [], output_file
            )

            assert result == output_file
            assert output_file.exists()

            # Read and verify HTML content
            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            assert "Test_Cruise_2024" in content
            assert "Test cruise description" in content
            assert "<html>" in content
            assert "</html>" in content
            assert "Total Cruise" in content
            assert "0 operations" in content
            assert "No moorings defined" in content

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_station_activities_html(self):
        """Test HTML generation with station activities."""
        timeline = [
            {
                "activity": "Point",
                "label": "STN_001",
                "entry_lat": 45.0,
                "entry_lon": -45.0,
                "exit_lat": 45.0,
                "exit_lon": -45.0,
                "start_time": "2024-01-01T08:00:00",
                "end_time": "2024-01-01T10:00:00",
                "duration_minutes": 120.0,
                "dist_nm": 0.0,
                "vessel_speed_kt": 0.0,
                "leg_name": "TestLeg",
                "op_type": "CTD",
                "operation_class": "PointOperation",
                "action": "profile",
                "operation_depth": None,
                "water_depth": 1000.0,
            },
            {
                "activity": "Point",
                "label": "STN_002",
                "entry_lat": 46.0,
                "entry_lon": -46.0,
                "exit_lat": 46.0,
                "exit_lon": -46.0,
                "start_time": "2024-01-01T12:00:00",
                "end_time": "2024-01-01T13:30:00",
                "duration_minutes": 90.0,
                "dist_nm": 0.0,
                "vessel_speed_kt": 0.0,
                "leg_name": "TestLeg",
                "op_type": "CTD",
                "operation_class": "PointOperation",
                "action": "profile",
                "operation_depth": None,
                "water_depth": 1500.0,
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            assert "CTD Profiles" in content
            assert "2 stations" in content
            assert "avg depth 1250 m" in content  # (1000 + 1500) / 2
            assert "3.5" in content  # Total duration in hours

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_mooring_activities_html(self):
        """Test HTML generation with mooring activities and detail table."""
        timeline = [
            {
                "activity": "Mooring",
                "label": "MOOR_001",
                "duration_minutes": 180.0,
                "entry_lat": 45.123456,
                "entry_lon": -123.654321,
                "exit_lat": 45.123456,
                "exit_lon": -123.654321,
                "operation_depth": 3000.0,
                "action": "deployment",
                "comment": "Deep water mooring",
                "op_type": "mooring",
                "operation_class": "PointOperation",
            },
            {
                "activity": "Mooring",
                "label": "MOOR_002",
                "duration_minutes": 240.0,
                "entry_lat": 46.987654,
                "entry_lon": -124.123456,
                "exit_lat": 46.987654,
                "exit_lon": -124.123456,
                "operation_depth": 2500.0,
                "action": "recovery",
                "comment": "Shallow mooring recovery",
                "op_type": "mooring",
                "operation_class": "PointOperation",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            # Check summary table
            assert "Moorings" in content
            assert "2 operations" in content
            assert "avg 3.5 hrs each" in content

            # Check detailed moorings table
            assert "MOOR_001" in content
            assert "MOOR_002" in content
            assert "Deep water mooring" in content
            assert "Shallow mooring recovery" in content
            assert "45 07.407" in content  # Converted coordinate
            assert "-123 39.259" in content  # Converted coordinate
            assert "deployment" in content
            assert "recovery" in content

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_survey_operations_html(self):
        """Test HTML generation with survey operations."""
        timeline = [
            {
                "activity": "Transit",
                "duration_minutes": 240.0,
                "dist_nm": 30.0,
                "action": "ADCP",
                "op_type": "survey",
                "operation_class": "LineOperation",
            },
            {
                "activity": "Transit",
                "duration_minutes": 180.0,
                "dist_nm": 20.0,
                "action": "bathymetry",
                "op_type": "survey",
                "operation_class": "LineOperation",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            assert "Survey operations" in content
            assert "2 operations" in content
            assert "avg distance 25.0 nm" in content  # (30 + 20) / 2
            assert "avg 3.5 hrs each" in content  # (240 + 180) / 60 / 2

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_area_operations_html(self):
        """Test HTML generation with area operations."""
        timeline = [
            {
                "activity": "Area",
                "duration_minutes": 120.0,
                "action": "bathymetry",
                "op_type": "area",
                "operation_class": "AreaOperation",
            },
            {
                "activity": "Area",
                "duration_minutes": 180.0,
                "action": "survey",
                "op_type": "area",
                "operation_class": "AreaOperation",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            assert "Area operations" in content
            assert "2 operations" in content
            assert "avg 2.5 hrs each" in content  # (120 + 180) / 60 / 2

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_transit_operations_html(self):
        """Test HTML generation with transit operations."""
        timeline = [
            {
                "activity": "Transit",
                "duration_minutes": 120.0,
                "dist_nm": 15.0,
                # Navigation transit (no action)
            },
            {
                "activity": "Transit",
                "duration_minutes": 180.0,
                "dist_nm": 25.0,
                # Navigation transit (no action)
            },
            {
                "activity": "Transit",
                "duration_minutes": 240.0,
                "dist_nm": 35.0,
                # Navigation transit (no action)
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            # With new logic, all navigation transits are within area
            assert "Transit within area" in content
            assert "75.0 nm" in content  # All transits: 15 + 25 + 35

            # No port transits expected (no Port_Departure/Port_Arrival activities)
            assert "Transit to/from working area" not in content or "0.0 nm" in content

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_mixed_operations_html(self):
        """Test HTML generation with mixed operation types."""
        timeline = [
            {
                "activity": "Station",
                "duration_minutes": 120.0,
                "operation_depth": 1000.0,
                "action": "profile",
                "op_type": "station",
                "operation_class": "PointOperation",
            },
            {
                "activity": "Mooring",
                "label": "MOOR_001",
                "duration_minutes": 180.0,
                "entry_lat": 45.0,
                "entry_lon": -45.0,
                "exit_lat": 45.0,
                "exit_lon": -45.0,
                "operation_depth": 2000.0,
                "action": "deployment",
                "comment": "Test mooring",
                "op_type": "mooring",
                "operation_class": "PointOperation",
            },
            {
                "activity": "Transit",
                "duration_minutes": 240.0,
                "dist_nm": 30.0,
                "action": "ADCP",
                "op_type": "survey",
                "operation_class": "LineOperation",
            },
            {
                "activity": "Area",
                "duration_minutes": 150.0,
                "action": "bathymetry",
                "op_type": "area",
                "operation_class": "AreaOperation",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            # Check that all operation types are represented
            assert "CTD Profiles" in content
            assert "1 stations" in content

            assert "Moorings" in content
            assert "1 operations" in content

            assert "Survey operations" in content
            assert "1 operations" in content

            assert "Area operations" in content
            assert "1 operations" in content

            # Check total calculation
            assert "4 operations" in content  # Total count
            total_hours = (120 + 180 + 240 + 150) / 60  # 11.5
            assert "11.5" in content

            # Check mooring detail table
            assert "MOOR_001" in content
            assert "Test mooring" in content

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_no_description_config(self):
        """Test HTML generation when config has no description."""
        self.mock_config.description = None

        timeline = [
            {
                "activity": "Station",
                "duration_minutes": 60.0,
                "depth": 1000.0,
                "action": "profile",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            with open(output_file, encoding="utf-8") as f:
                content = f.read()

            # Should not have description paragraph when None
            assert 'class="description"' not in content

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_special_characters_in_cruise_name(self):
        """Test HTML generation with special characters in cruise name."""
        self.mock_config.cruise_name = 'Test_Cruise_2024_with&<>"quotes'

        timeline = [
            {
                "activity": "Station",
                "duration_minutes": 60.0,
                "depth": 1000.0,
                "action": "profile",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            # Should generate HTML without errors (though might need escaping)
            assert result == output_file
            assert output_file.exists()

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_zero_division_protection(self):
        """Test that zero division is handled gracefully."""
        # Timeline with activities but zero durations should not crash
        timeline = [
            {
                "activity": "Station",
                "duration_minutes": 0.0,  # Zero duration
                "depth": 1000.0,
                "action": "profile",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_report(
                self.mock_config, timeline, output_file
            )

            # Should complete without division by zero errors
            assert result == output_file
            assert output_file.exists()

        finally:
            if output_file.exists():
                output_file.unlink()


def test_generate_html_schedule_convenience_function():
    """Test the convenience function generate_html_schedule."""
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "Test_Cruise"
    mock_config.description = "Test description"

    timeline = [
        {
            "activity": "Station",
            "duration_minutes": 60.0,
            "depth": 1000.0,
            "action": "profile",
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp_file:
        output_file = Path(tmp_file.name)

    try:
        result = generate_html_schedule(mock_config, timeline, output_file)

        assert result == output_file
        assert output_file.exists()

        # Verify content was written
        with open(output_file, encoding="utf-8") as f:
            content = f.read()
            assert "Test_Cruise" in content
            assert "html" in content

    finally:
        if output_file.exists():
            output_file.unlink()
