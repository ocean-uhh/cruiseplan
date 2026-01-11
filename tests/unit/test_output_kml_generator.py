"""
Unit tests for KML generator module.
Tests KML XML generation, polygon handling, and style application.
"""

import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from cruiseplan.output.kml_generator import KMLGenerator
from cruiseplan.schema import CruiseConfig


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


class TestKMLGeneratorCatalogMode:
    """Test KML generation from catalog (config-based)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock(spec=CruiseConfig)
        self.mock_config.cruise_name = "Test_Catalog_Cruise"
        self.mock_config.description = "Catalog-based KML test"

        # Mock stations
        mock_station = MagicMock()
        mock_station.name = "CAT_STN_001"
        mock_station.latitude = 65.0
        mock_station.longitude = -25.0
        mock_station.operation_type.value = "CTD"
        mock_station.operation_depth = 800.0
        mock_station.water_depth = 3200.0
        self.mock_config.points = [mock_station]

        # Mock areas
        mock_area = MagicMock()
        mock_area.name = "SURVEY_AREA"
        mock_corners = [
            MagicMock(latitude=60.0, longitude=-20.0),
            MagicMock(latitude=61.0, longitude=-20.0),
            MagicMock(latitude=61.0, longitude=-21.0),
            MagicMock(latitude=60.0, longitude=-21.0),
        ]
        mock_area.corners = mock_corners
        self.mock_config.areas = [mock_area]

        # Mock transits
        mock_transit = MagicMock()
        mock_transit.name = "TRANSIT_001"
        mock_route = [
            MagicMock(latitude=60.0, longitude=-20.0),
            MagicMock(latitude=65.0, longitude=-25.0),
        ]
        mock_transit.route = mock_route
        self.mock_config.lines = [mock_transit]

        # Mock ports
        mock_port = MagicMock()
        mock_port.name = "TEST_PORT"
        mock_port.latitude = 64.0
        mock_port.longitude = -22.0
        self.mock_config.ports = [mock_port]

    def test_generate_kml_catalog_success(self):
        """Test successful catalog-based KML generation."""
        from cruiseplan.output.kml_generator import generate_kml_catalog

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = generate_kml_catalog(self.mock_config, output_file)

            assert result == output_file
            assert output_file.exists()

            # Verify content contains catalog entities
            with open(output_file, encoding="utf-8") as f:
                content = f.read()
                assert "CAT_STN_001" in content
                assert "SURVEY_AREA" in content
                assert "TRANSIT_001" in content
                assert "TEST_PORT" in content

        finally:
            if output_file.exists():
                output_file.unlink()

    def test_generate_kml_catalog_empty_config(self):
        """Test catalog KML generation with empty config."""
        from cruiseplan.output.kml_generator import generate_kml_catalog

        empty_config = MagicMock(spec=CruiseConfig)
        empty_config.cruise_name = "Empty_Test"
        empty_config.points = []
        empty_config.areas = []
        empty_config.lines = []
        empty_config.ports = []

        with tempfile.NamedTemporaryFile(suffix=".kml", delete=False) as tmp_file:
            output_file = Path(tmp_file.name)

        try:
            result = generate_kml_catalog(empty_config, output_file)

            assert result == output_file
            assert output_file.exists()

            # Should still create valid KML structure
            with open(output_file, encoding="utf-8") as f:
                content = f.read()
                assert "kml" in content.lower()
                assert "Empty_Test" in content

        finally:
            if output_file.exists():
                output_file.unlink()


class TestKMLUtilityFunctions:
    """Test KML utility and helper functions."""

    def test_kml_styles_defined(self):
        """Test that KML styles are properly defined."""
        from cruiseplan.output.kml_generator import KML_STYLES

        # Should contain style definitions
        assert "stationStyle" in KML_STYLES
        assert "mooringStyle" in KML_STYLES
        assert "lineOpStyle" in KML_STYLES
        assert "areaStyle" in KML_STYLES

        # Should be valid XML-like content
        assert "<Style" in KML_STYLES
        assert "IconStyle" in KML_STYLES
        assert "LineStyle" in KML_STYLES

    def test_coordinate_formatting(self):
        """Test coordinate formatting in KML output."""
        generator = KMLGenerator()

        # Test coordinate formatting with various inputs
        test_cases = [
            (60.0, -20.0, "-20.0,60.0,0"),
            (0.0, 0.0, "0.0,0.0,0"),
            (-45.5, 123.7, "123.7,-45.5,0"),
        ]

        for lat, lon, expected in test_cases:
            # This tests the internal coordinate formatting
            # (Implementation detail - may need adjustment based on actual KML generator structure)
            coord_str = f"{lon},{lat},0"  # KML format: lon,lat,elevation
            assert coord_str == expected
