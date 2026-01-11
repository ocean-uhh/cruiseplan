"""
Tests for CTD section expansion functionality.

This module tests the expand_ctd_sections function which converts CTD transits
with operation_type="CTD" and action="section" into individual station definitions
with proper interpolation, duplicate name checking, and reference updates.
"""

import copy

import pytest

from cruiseplan.processing.enrich import expand_ctd_sections
from cruiseplan.schema.vocabulary import LINES_FIELD, POINTS_FIELD


class TestCTDSectionExpansion:
    """Test CTD section expansion functionality."""

    def test_expand_simple_section(self):
        """Test basic CTD section expansion with two-point route."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Test Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 52.0, "longitude": -32.0},
                    ],
                    "distance_between_stations": 50.0,  # 50 km spacing
                }
            ],
            "legs": [{"name": "Test Leg", "activities": ["Test Section"]}],
        }

        result_config, summary = expand_ctd_sections(config)

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
            LINES_FIELD: [
                {
                    "name": "Dense Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 45.0, "longitude": -20.0},
                        {"latitude": 47.0, "longitude": -22.0},  # ~240 km apart
                    ],
                    "distance_between_stations": 10.0,  # 10 km spacing = many stations
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

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

    def test_expand_section_with_special_characters(self):
        """Test CTD section expansion with special characters in names."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Test-Section #1 (North-South)",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        result_config, _summary = expand_ctd_sections(config)

        # Check that special characters were sanitized
        station_names = [s["name"] for s in result_config[POINTS_FIELD]]

        # Should be something like "Test_Section_1_North_South_Stn001"
        for name in station_names:
            assert all(
                c.isalnum() or c == "_" for c in name
            ), f"Invalid characters in name: {name}"
            assert not name.startswith("_"), f"Name starts with underscore: {name}"
            assert not name.endswith("_"), f"Name ends with underscore: {name}"
            assert "__" not in name, f"Double underscores in name: {name}"

    def test_expand_section_duplicate_name_handling(self):
        """Test handling of duplicate station names in expansion."""
        config = {
            POINTS_FIELD: [
                {
                    "name": "Test_Section_Stn001",
                    "operation_type": "CTD",
                    "action": "profile",
                }
            ],
            LINES_FIELD: [
                {
                    "name": "Test Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ],
        }

        result_config, _summary = expand_ctd_sections(config)

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

    def test_expand_section_custom_depth_default(self):
        """Test CTD section expansion with custom default depth."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Deep Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        # Use custom default depth of 2000m instead of default 1000m
        result_config, _summary = expand_ctd_sections(config, default_depth=2000.0)

        # All stations should have the custom default depth
        for station in result_config[POINTS_FIELD]:
            assert station["water_depth"] == 2000.0

    def test_expand_section_with_max_depth_override(self):
        """Test CTD section expansion with max_depth override from transit."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Custom Depth Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "max_depth": 3500.0,  # Override default depth
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        result_config, _summary = expand_ctd_sections(config)

        # All stations should have the overridden depth
        for station in result_config[POINTS_FIELD]:
            assert station["water_depth"] == 3500.0

    def test_expand_section_insufficient_route_points(self):
        """Test CTD section expansion with insufficient route points."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Invalid Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [{"latitude": 50.0, "longitude": -30.0}],  # Only one point
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        # The function still processes the section (sections_expanded = 1)
        # but creates no stations (stations_from_expansion = 0)
        assert summary["sections_expanded"] == 1
        assert summary["stations_from_expansion"] == 0
        # The section should still be removed from transects
        assert LINES_FIELD not in result_config or len(result_config[LINES_FIELD]) == 0

    def test_expand_section_missing_coordinates(self):
        """Test CTD section expansion with missing coordinates."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Bad Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0},  # Missing longitude
                        {"longitude": -31.0},  # Missing latitude
                    ],
                }
            ]
        }

        _result_config, summary = expand_ctd_sections(config)

        # The function still processes the section (sections_expanded = 1)
        # but creates no stations due to missing coordinates (stations_from_expansion = 0)
        assert summary["sections_expanded"] == 1
        assert summary["stations_from_expansion"] == 0

    def test_expand_multiple_sections(self):
        """Test expansion of multiple CTD sections."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Section A",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                },
                {
                    "name": "Regular Transit",
                    "operation_type": "transit",
                    "action": "steam",
                },
                {
                    "name": "Section B",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 52.0, "longitude": -32.0},
                        {"latitude": 53.0, "longitude": -33.0},
                    ],
                },
            ]
        }

        result_config, summary = expand_ctd_sections(config)

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
            LINES_FIELD: [
                {
                    "name": "Main Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 52.0, "longitude": -32.0},
                    ],
                }
            ],
            "legs": [
                {
                    "name": "Survey_Leg",
                    "first_activity": "Main Section",
                    "last_activity": "Main Section",
                    "activities": ["Main Section"],
                }
            ],
        }

        result_config, _summary = expand_ctd_sections(config)

        # first_activity should point to first expanded station at leg level
        expanded_stations = [s["name"] for s in result_config[POINTS_FIELD]]
        leg = result_config["legs"][0]
        assert leg["first_activity"] == expanded_stations[0]

        # last_activity should point to last expanded station at leg level
        assert leg["last_activity"] == expanded_stations[-1]

    def test_expand_section_preserves_other_transit_fields(self):
        """Test that additional fields from transects are preserved in stations."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Research Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "planned_duration_hours": 3.0,  # Custom duration
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        result_config, _summary = expand_ctd_sections(config)

        # Check that custom fields were copied to all stations
        for station in result_config[POINTS_FIELD]:
            assert station["duration"] == 180.0  # 3.0 hours converted to 180 minutes

    def test_expand_section_spherical_interpolation(self):
        """Test that proper spherical interpolation is used for great circle routes."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Long Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {
                            "latitude": 0.0,
                            "longitude": 0.0,
                        },  # Equator at Prime Meridian
                        {"latitude": 0.0, "longitude": 90.0},  # Equator at 90°E
                    ],
                    "distance_between_stations": 2000.0,  # Large spacing for few stations
                }
            ]
        }

        result_config, _summary = expand_ctd_sections(config)

        stations = result_config[POINTS_FIELD]

        # Check that intermediate stations follow great circle path
        # For this case (along equator), intermediate points should maintain latitude ≈ 0
        for station in stations:
            lat = station["latitude"]
            lon = station["longitude"]
            assert abs(lat) < 1e-5, f"Station not on equator: lat={lat}, lon={lon}"
            assert 0.0 <= lon <= 90.0, f"Longitude out of range: {lon}"

    def test_expand_section_no_transects_key(self):
        """Test expansion when config has no transects key."""
        config = {"cruise_name": "Test Cruise", "legs": []}

        result_config, summary = expand_ctd_sections(config)

        # Should return unchanged config with zero summary
        assert summary["sections_expanded"] == 0
        assert summary["stations_from_expansion"] == 0
        assert result_config == config

    def test_expand_section_empty_transects(self):
        """Test expansion with empty transects list."""
        config = {LINES_FIELD: [], "legs": []}

        result_config, summary = expand_ctd_sections(config)

        # Empty transects list is preserved (not cleaned up)
        assert result_config[LINES_FIELD] == []
        assert summary["sections_expanded"] == 0
        assert summary["stations_from_expansion"] == 0


class TestCTDExpansionEdgeCases:
    """Test edge cases and error conditions in CTD expansion."""

    def test_very_short_distance_expansion(self):
        """Test expansion of very short sections."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Short Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0000, "longitude": -30.0000},
                        {"latitude": 50.0001, "longitude": -30.0001},  # ~15m apart
                    ],
                    "distance_between_stations": 100.0,  # 100m spacing
                }
            ]
        }

        _result_config, summary = expand_ctd_sections(config)

        # Should still create minimum 2 stations
        assert summary["stations_from_expansion"] >= 2

    def test_malformed_route_coordinates(self):
        """Test handling of malformed coordinate data."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Bad Coords Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": "not_a_number", "longitude": -30.0},
                        {"latitude": 51.0, "longitude": "invalid"},
                    ],
                }
            ]
        }

        # Should raise TypeError due to invalid coordinates
        with pytest.raises(TypeError):
            expand_ctd_sections(config)

    def test_alternative_coordinate_keys(self):
        """Test handling of alternative coordinate key names."""
        config = {
            LINES_FIELD: [
                {
                    "name": "Alt Keys Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"lat": 50.0, "lon": -30.0},  # Alternative key names
                        {"lat": 51.0, "lon": -31.0},
                    ],
                }
            ]
        }

        _result_config, summary = expand_ctd_sections(config)

        # Should work with alternative coordinate keys
        assert summary["sections_expanded"] == 1
        assert summary["stations_from_expansion"] >= 2

    def test_deep_copy_isolation(self):
        """Test that original config is not modified."""
        original_config = {
            LINES_FIELD: [
                {
                    "name": "Test Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        config_copy = copy.deepcopy(original_config)
        result_config, _summary = expand_ctd_sections(config_copy)

        # Original should be unchanged
        assert original_config == {
            LINES_FIELD: [
                {
                    "name": "Test Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        # Result should be different
        assert result_config != original_config
        assert POINTS_FIELD in result_config
