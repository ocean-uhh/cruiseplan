"""
Unit tests for KML generator module.
Tests KML XML generation, polygon handling, and style application.
"""

import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from cruiseplan.core.validation import CruiseConfig
from cruiseplan.output.kml_generator import KMLGenerator, generate_kml_schedule


class TestKMLGenerator:
    """Test the KMLGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.generator = KMLGenerator()
        self.mock_config = MagicMock(spec=CruiseConfig)
        self.mock_config.cruise_name = "Test_Cruise_2024"
        self.mock_config.description = "Test cruise description"

    def test_init(self):
        """Test KMLGenerator initialization."""
        generator = KMLGenerator()
        assert generator is not None

    def test_empty_timeline(self):
        """Test KML generation with empty timeline."""
        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, [], output_file
            )

            assert result == output_file
            assert output_file.exists()

            # Parse and verify KML structure
            tree = ET.parse(output_file)
            root = tree.getroot()

            # Check namespace and basic structure
            assert root.tag.endswith("kml")
            document = root.find(".//{http://www.opengis.net/kml/2.2}Document")
            assert document is not None

            # Check document metadata
            name = document.find(".//{http://www.opengis.net/kml/2.2}name")
            assert name.text == "Test_Cruise_2024 - Schedule"

            description = document.find(
                ".//{http://www.opengis.net/kml/2.2}description"
            )
            assert description.text == "Test cruise description"

            # Should have styles but no placemarks
            styles = document.findall(".//{http://www.opengis.net/kml/2.2}Style")
            assert (
                len(styles) == 4
            )  # stationStyle, mooringStyle, lineOpStyle, areaStyle

            placemarks = document.findall(
                ".//{http://www.opengis.net/kml/2.2}Placemark"
            )
            assert len(placemarks) == 0

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_station_activity(self):
        """Test KML generation with station activity."""
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
                "action": "profile",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            # Parse and verify KML content
            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 1

            placemark = placemarks[0]
            name = placemark.find(".//{http://www.opengis.net/kml/2.2}name")
            assert name.text == "STN_001"

            description = placemark.find(
                ".//{http://www.opengis.net/kml/2.2}description"
            )
            assert "Activity: Station" in description.text
            assert "Duration: 120.0 min" in description.text
            assert "Depth: 1500.0 m" in description.text

            style_url = placemark.find(".//{http://www.opengis.net/kml/2.2}styleUrl")
            assert style_url.text == "#stationStyle"

            point = placemark.find(".//{http://www.opengis.net/kml/2.2}Point")
            assert point is not None

            coordinates = point.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            assert coordinates.text == "-123.654321,45.123456,0"

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_mooring_activity(self):
        """Test KML generation with mooring activity."""
        timeline = [
            {
                "activity": "Mooring",
                "label": "MOOR_001",
                "start_time": datetime(2024, 1, 1, 8, 0),
                "end_time": datetime(2024, 1, 1, 11, 0),
                "duration_minutes": 180.0,
                "lat": 50.0,
                "lon": -50.0,
                "depth": 3000.0,
                "action": "deployment",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 1

            placemark = placemarks[0]
            style_url = placemark.find(".//{http://www.opengis.net/kml/2.2}styleUrl")
            assert style_url.text == "#mooringStyle"

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_line_operation_transit(self):
        """Test KML generation with line operation (scientific transit)."""
        timeline = [
            {
                "activity": "Transit",
                "label": "Survey_Line_Alpha",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 18, 0),
                "duration_minutes": 360.0,
                "lat": 53.7,  # End point
                "lon": -50.1,
                "start_lat": 53.3,  # Start point
                "start_lon": -50.5,
                "operation_dist_nm": 28.5,
                "action": "ADCP",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 2  # Line + midpoint label

            # Find line placemark
            line_placemark = None
            point_placemark = None
            for placemark in placemarks:
                if (
                    placemark.find(".//{http://www.opengis.net/kml/2.2}LineString")
                    is not None
                ):
                    line_placemark = placemark
                elif (
                    placemark.find(".//{http://www.opengis.net/kml/2.2}Point")
                    is not None
                ):
                    point_placemark = placemark

            assert line_placemark is not None
            assert point_placemark is not None

            # Verify line placemark
            line_name = line_placemark.find(".//{http://www.opengis.net/kml/2.2}name")
            assert line_name.text == "Survey_Line_Alpha - ADCP"

            line_style = line_placemark.find(
                ".//{http://www.opengis.net/kml/2.2}styleUrl"
            )
            assert line_style.text == "#lineOpStyle"

            linestring = line_placemark.find(
                ".//{http://www.opengis.net/kml/2.2}LineString"
            )
            coordinates = linestring.find(
                ".//{http://www.opengis.net/kml/2.2}coordinates"
            )
            coord_text = coordinates.text.strip()
            assert "-50.5,53.3,0" in coord_text  # Start point
            assert "-50.1,53.7,0" in coord_text  # End point

            # Verify midpoint placemark
            point_name = point_placemark.find(".//{http://www.opengis.net/kml/2.2}name")
            assert point_name.text == "Survey_Line_Alpha"

            point_coords = point_placemark.find(
                ".//{http://www.opengis.net/kml/2.2}Point//{http://www.opengis.net/kml/2.2}coordinates"
            )
            # Midpoint should be approximately (-50.3, 53.5)
            assert "-50.3,53.5,0" in point_coords.text

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_area_operation_with_corners(self):
        """Test KML generation with area operation that has corner coordinates."""
        timeline = [
            {
                "activity": "Area",
                "label": "Bathy_survey",
                "start_time": datetime(2024, 1, 3, 12, 23),
                "end_time": datetime(2024, 1, 3, 14, 23),
                "duration_minutes": 120.0,
                "lat": 56.759477,  # Center point
                "lon": -46.607803,
                "action": "bathymetry",
                "corners": [
                    {"latitude": 59.0983, "longitude": -46.89092},
                    {"latitude": 55.48548, "longitude": -50.99612},
                    {"latitude": 55.69465, "longitude": -41.93637},
                ],
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 1

            placemark = placemarks[0]
            name = placemark.find(".//{http://www.opengis.net/kml/2.2}name")
            assert name.text == "Bathy_survey - bathymetry"

            description = placemark.find(
                ".//{http://www.opengis.net/kml/2.2}description"
            )
            assert "Activity: Area (bathymetry)" in description.text
            assert "Area: 3 corners" in description.text

            style_url = placemark.find(".//{http://www.opengis.net/kml/2.2}styleUrl")
            assert style_url.text == "#areaStyle"

            polygon = placemark.find(".//{http://www.opengis.net/kml/2.2}Polygon")
            assert polygon is not None

            coordinates = polygon.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            coord_text = coordinates.text.strip()

            # Verify all corners are present and polygon is closed
            assert "-46.89092,59.0983,0" in coord_text
            assert "-50.99612,55.48548,0" in coord_text
            assert "-41.93637,55.69465,0" in coord_text
            # Should be closed by repeating first coordinate
            assert coord_text.count("-46.89092,59.0983,0") == 2

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_area_operation_no_corners(self):
        """Test KML generation with area operation that has no corner coordinates."""
        timeline = [
            {
                "activity": "Area",
                "label": "Area_No_Corners",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 14, 0),
                "duration_minutes": 120.0,
                "lat": 45.0,
                "lon": -45.0,
                "action": "survey",
                "corners": [],  # No corners
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 1

            placemark = placemarks[0]

            # Should fall back to point representation
            point = placemark.find(".//{http://www.opengis.net/kml/2.2}Point")
            assert point is not None

            polygon = placemark.find(".//{http://www.opengis.net/kml/2.2}Polygon")
            assert polygon is None

            description = placemark.find(
                ".//{http://www.opengis.net/kml/2.2}description"
            )
            assert "Area - no corners defined" in description.text

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_area_operation_insufficient_corners(self):
        """Test KML generation with area operation that has insufficient corners."""
        timeline = [
            {
                "activity": "Area",
                "label": "Area_Two_Corners",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 14, 0),
                "duration_minutes": 120.0,
                "lat": 45.0,
                "lon": -45.0,
                "action": "survey",
                "corners": [
                    {"latitude": 44.0, "longitude": -44.0},
                    {"latitude": 46.0, "longitude": -46.0},
                ],  # Only 2 corners - insufficient for polygon
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 1

            # Should fall back to point representation since < 3 corners
            placemark = placemarks[0]
            point = placemark.find(".//{http://www.opengis.net/kml/2.2}Point")
            assert point is not None

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_mixed_activities(self):
        """Test KML generation with multiple activity types."""
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
                "action": "profile",
            },
            {
                "activity": "Transit",  # This should be filtered out (no action = navigation)
                "label": "Navigation_Transit",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 14, 0),
                "duration_minutes": 120.0,
                "lat": 46.0,
                "lon": -46.0,
                # No action field - pure navigation transit
            },
            {
                "activity": "Transit",
                "label": "Scientific_Transit",
                "start_time": datetime(2024, 1, 1, 14, 0),
                "end_time": datetime(2024, 1, 1, 18, 0),
                "duration_minutes": 240.0,
                "lat": 47.0,
                "lon": -47.0,
                "start_lat": 46.5,
                "start_lon": -46.5,
                "action": "ADCP",  # Scientific transit
            },
            {
                "activity": "Mooring",
                "label": "MOOR_001",
                "start_time": datetime(2024, 1, 2, 8, 0),
                "end_time": datetime(2024, 1, 2, 11, 0),
                "duration_minutes": 180.0,
                "lat": 48.0,
                "lon": -48.0,
                "depth": 3000.0,
                "action": "deployment",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            # Should have: STN_001 (1), Scientific_Transit line + midpoint (2), MOOR_001 (1) = 4 total
            # Navigation_Transit should be filtered out
            assert len(placemarks) == 4

            # Verify scientific operations are included, navigation transit is not
            names = [
                p.find(".//{http://www.opengis.net/kml/2.2}name").text
                for p in placemarks
            ]
            assert "STN_001" in names
            assert "Scientific_Transit - ADCP" in names
            assert "Scientific_Transit" in names  # Midpoint label
            assert "MOOR_001" in names
            assert "Navigation_Transit" not in names

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_coordinate_edge_cases(self):
        """Test KML generation with edge case coordinates."""
        timeline = [
            {
                "activity": "Station",
                "label": "Equator_Station",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "lat": 0.0,  # Equator
                "lon": 180.0,  # International Date Line
                "depth": 5000.0,
                "action": "profile",
            },
            {
                "activity": "Station",
                "label": "South_Pole_Station",
                "start_time": datetime(2024, 1, 1, 12, 0),
                "end_time": datetime(2024, 1, 1, 13, 0),
                "duration_minutes": 60.0,
                "lat": -90.0,  # South Pole
                "lon": 0.0,
                "depth": 100.0,
                "action": "profile",
            },
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            # Should generate valid KML without errors
            tree = ET.parse(output_file)
            root = tree.getroot()

            placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
            assert len(placemarks) == 2

            # Verify coordinates are properly formatted
            coordinates = [
                p.find(".//{http://www.opengis.net/kml/2.2}coordinates").text
                for p in placemarks
            ]
            assert "180.0,0.0,0" in coordinates
            assert "0.0,-90.0,0" in coordinates

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_missing_config_description(self):
        """Test KML generation when config has no description."""
        self.mock_config.description = None

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
                "action": "profile",
            }
        ]

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = self.generator.generate_schedule_kml(
                self.mock_config, timeline, output_file
            )

            tree = ET.parse(output_file)
            root = tree.getroot()

            document = root.find(".//{http://www.opengis.net/kml/2.2}Document")
            description = document.find(
                ".//{http://www.opengis.net/kml/2.2}description"
            )
            assert description.text == "Cruise schedule"  # Default fallback

        finally:
            if output_file.exists():
                output_file.unlink()


def test_generate_kml_schedule_convenience_function():
    """Test the convenience function generate_kml_schedule."""
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "Test_Cruise"
    mock_config.description = "Test description"

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
            "action": "profile",
        }
    ]

    with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
        output_file = Path(tmp_file.name)

    try:
        result = generate_kml_schedule(mock_config, timeline, output_file)

        assert result == output_file
        assert output_file.exists()

        # Verify content was written
        with open(output_file, encoding="utf-8") as f:
            content = f.read()
            assert "STN_001" in content
            assert "kml" in content

    finally:
        if output_file.exists():
            output_file.unlink()
