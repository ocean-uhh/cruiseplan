"""
Tests for CTD section expansion functionality.

This module tests the expand_ctd_sections function which converts CTD transits
with operation_type="CTD" and action="section" into individual station definitions
with proper interpolation, duplicate name checking, and reference updates.
"""

import pytest
from pydantic import ValidationError

from cruiseplan.core.cruise import CruiseInstance
from cruiseplan.schema.fields import (
    ACTION_FIELD,
    ACTIVITIES_FIELD,
    ARRIVAL_PORT_FIELD,
    DEPARTURE_PORT_FIELD,
    FIRST_ACTIVITY_FIELD,
    LAST_ACTIVITY_FIELD,
    LEGS_FIELD,
    LINE_VERTEX_FIELD,
    LINES_FIELD,
    OP_TYPE_FIELD,
    POINTS_FIELD,
    STATION_SPACING_FIELD,
)


class TestCTDSectionExpansion:
    """Test CTD section expansion functionality."""

    def test_expand_simple_section(self):
        """Test basic CTD section expansion with two-point route."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Test Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 52.0, "longitude": -32.0},
                    ],
                    STATION_SPACING_FIELD: 50.0,  # 50 km spacing
                }
            ],
            LEGS_FIELD: [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Test Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # Check summary
        assert summary["sections_expanded"] == 1
        assert summary["stations_from_expansion"] >= 2

        # Check waypoints were created
        assert POINTS_FIELD in result_config
        station_names = [s["name"] for s in result_config[POINTS_FIELD]]

        # Should have stations like Test_Section_Stn001, Test_Section_Stn002, etc.
        assert any("Test_Section_Stn" in name for name in station_names)

        # Check transects were cleaned up
        assert LINES_FIELD not in result_config or len(result_config[LINES_FIELD]) == 0

        # Check leg references were updated
        leg_stations = result_config["legs"][0]["activities"]
        assert all(name in station_names for name in leg_stations)
        assert "Test Section" not in leg_stations

    def test_expand_section_with_custom_spacing(self):
        """Test CTD section expansion with custom station spacing."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Dense Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 45.0, "longitude": -20.0},
                        {"latitude": 47.0, "longitude": -22.0},  # ~240 km apart
                    ],
                    STATION_SPACING_FIELD: 10.0,  # 10 km spacing = many stations
                }
            ],
            "legs": [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Dense Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # Should create many stations with tight spacing
        assert summary["stations_from_expansion"] >= 20  # At least 20 stations

        # Check proper interpolation
        stations = result_config[POINTS_FIELD]
        first_station = next(s for s in stations if "Stn001" in s["name"])
        last_station = stations[-1]

        # First station should be at start point
        assert abs(first_station["latitude"] - 45.0) < 1e-5
        assert abs(first_station["longitude"] - (-20.0)) < 1e-5

        # Last station should be at end point
        assert abs(last_station["latitude"] - 47.0) < 1e-5
        assert abs(last_station["longitude"] - (-22.0)) < 1e-5

    def test_expand_section_duplicate_name_handling(self):
        """Test handling of duplicate station names in expansion."""
        config = {
            "cruise_name": "Test Cruise",
            POINTS_FIELD: [
                {
                    "name": "Test_Section_Stn001",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "profile",
                }
            ],
            LINES_FIELD: [
                {
                    "name": "Test Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ],
            "legs": [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Test Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        _summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # Check that duplicate names were handled
        station_names = [s["name"] for s in result_config[POINTS_FIELD]]
        unique_names = set(station_names)

        # All names should be unique
        assert len(station_names) == len(unique_names)

        # Should have original station plus new ones with suffixes
        assert "Test_Section_Stn001" in station_names  # Original
        assert any(
            "Test_Section_Stn001_" in name for name in station_names
        ), "No collision-resolved names found"

    def test_expand_section_with_max_depth_override(self):
        """Test CTD section expansion with max_depth override from transit."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Custom Depth Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    "max_depth": 3500.0,  # Override default depth
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ],
            "legs": [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Custom Depth Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        _summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # All stations should have the overridden depth
        for station in result_config[POINTS_FIELD]:
            assert station["water_depth"] == 3500.0

    def test_expand_section_insufficient_route_points(self):
        """Test CTD section expansion with insufficient route points."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Invalid Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0}
                    ],  # Only one point
                }
            ],
            LEGS_FIELD: [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Invalid Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # With only 1 point, no expansion should occur (sections_expanded = 0)
        assert summary["sections_expanded"] == 0
        assert summary["stations_from_expansion"] == 0
        # The section should remain in the lines since it wasn't processed
        assert LINES_FIELD in result_config and len(result_config[LINES_FIELD]) == 1

    def test_expand_section_missing_coordinates(self):
        """Test CTD section expansion with missing coordinates."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Bad Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0},  # Missing longitude
                        {"longitude": -31.0},  # Missing latitude
                    ],
                }
            ],
            LEGS_FIELD: [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Bad Section"],
                }
            ],
        }

        # Modern validation should reject missing coordinates during creation
        with pytest.raises(ValidationError):
            CruiseInstance.from_dict(config)

    def test_expand_multiple_sections(self):
        """Test expansion of multiple CTD sections."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Section A",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                },
                {
                    "name": "Regular Transit",
                    OP_TYPE_FIELD: "underway",
                    ACTION_FIELD: "ADCP",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 51.5, "longitude": -31.5},
                        {"latitude": 52.5, "longitude": -32.5},
                    ],
                },
                {
                    "name": "Section B",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 52.0, "longitude": -32.0},
                        {"latitude": 53.0, "longitude": -33.0},
                    ],
                },
            ],
            LEGS_FIELD: [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Section A", "Regular Transit", "Section B"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # Should expand both CTD sections but leave regular transit
        assert summary["sections_expanded"] == 2
        assert len(result_config[LINES_FIELD]) == 1
        assert result_config[LINES_FIELD][0]["name"] == "Regular Transit"

        # Should have stations from both sections
        station_names = [s["name"] for s in result_config[POINTS_FIELD]]
        assert any("Section_A_Stn" in name for name in station_names)
        assert any("Section_B_Stn" in name for name in station_names)

    def test_expand_section_updates_first_last_station_refs(self):
        """Test that first_activity and last_activity references are updated at leg level."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Main Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 52.0, "longitude": -32.0},
                    ],
                }
            ],
            "legs": [
                {
                    "name": "Survey_Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    FIRST_ACTIVITY_FIELD: "Main Section",
                    LAST_ACTIVITY_FIELD: "Main Section",
                    ACTIVITIES_FIELD: ["Main Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        _summary = cruise.expand_sections()
        result_config = cruise.to_commented_dict()

        # first_activity should point to first expanded station at leg level
        expanded_stations = [s["name"] for s in result_config[POINTS_FIELD]]
        leg = result_config["legs"][0]
        assert leg[FIRST_ACTIVITY_FIELD] == expanded_stations[0]

        # last_activity should point to last expanded station at leg level
        assert leg[LAST_ACTIVITY_FIELD] == expanded_stations[-1]


class TestCTDExpansionEdgeCases:
    """Test edge cases and error conditions in CTD expansion."""

    def test_very_short_distance_expansion(self):
        """Test expansion of very short sections."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Short Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0000, "longitude": -30.0000},
                        {"latitude": 50.0001, "longitude": -30.0001},  # ~15m apart
                    ],
                    STATION_SPACING_FIELD: 100.0,  # 100m spacing
                }
            ],
            LEGS_FIELD: [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Short Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        summary = cruise.expand_sections()

        # Should still create minimum 2 stations
        assert summary["stations_from_expansion"] >= 2

    def test_standard_coordinate_keys(self):
        """Test expansion with standard coordinate key names."""
        config = {
            "cruise_name": "Test Cruise",
            LINES_FIELD: [
                {
                    "name": "Alt Keys Section",
                    OP_TYPE_FIELD: "CTD",
                    ACTION_FIELD: "section",
                    LINE_VERTEX_FIELD: [
                        {"latitude": 50.0, "longitude": -30.0},  # Standard key names
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ],
            LEGS_FIELD: [
                {
                    "name": "Test Leg",
                    DEPARTURE_PORT_FIELD: "test_port",
                    ARRIVAL_PORT_FIELD: "test_port",
                    ACTIVITIES_FIELD: ["Alt Keys Section"],
                }
            ],
        }

        # Create CruiseInstance and expand sections using modern approach
        cruise = CruiseInstance.from_dict(config)
        summary = cruise.expand_sections()

        # Should work with standard coordinate keys
        assert summary["sections_expanded"] == 1
        assert summary["stations_from_expansion"] >= 2
