"""
Tests for duplicate name handling and station name collision detection.

This module tests the duplicate name checking functionality and the collision
resolution logic in CTD section expansion that prevents duplicate station names
by auto-numbering with suffixes.
"""

from unittest.mock import MagicMock

from cruiseplan.core.validation import (
    check_complete_duplicates,
    check_duplicate_names,
    expand_ctd_sections,
)


class TestDuplicateNameCollisionResolution:
    """Test collision detection and auto-numbering in CTD expansion."""

    def test_single_collision_resolution(self):
        """Test resolution of single name collision during CTD expansion."""
        config = {
            "stations": [
                {
                    "name": "Test_Section_Stn001",
                    "operation_type": "CTD",
                    "action": "profile",
                }
            ],
            "transits": [
                {
                    "name": "Test Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 50.1, "longitude": -30.1},
                    ],
                    "distance_between_stations": 100.0,  # Will create 2 stations
                }
            ],
        }

        result_config, summary = expand_ctd_sections(config)

        # Should have original + 2 new stations (with collision resolved names)
        assert len(result_config["stations"]) == 3

        station_names = [s["name"] for s in result_config["stations"]]

        # Original station should remain unchanged
        assert "Test_Section_Stn001" in station_names

        # New stations should have collision-resolved names
        new_names = [name for name in station_names if name != "Test_Section_Stn001"]
        assert any(
            "Test_Section_Stn001_" in name for name in new_names
        ), f"No collision-resolved names found in: {new_names}"

        # All names should be unique
        assert len(station_names) == len(set(station_names))

    def test_multiple_collision_resolution(self):
        """Test resolution of multiple name collisions."""
        config = {
            "stations": [
                {"name": "Route_A_Stn001", "operation_type": "CTD"},
                {
                    "name": "Route_A_Stn001_01",
                    "operation_type": "CTD",
                },  # Existing collision resolution
                {"name": "Route_A_Stn002", "operation_type": "CTD"},
            ],
            "transits": [
                {
                    "name": "Route A",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 45.0, "longitude": -25.0},
                        {"latitude": 45.2, "longitude": -25.2},
                    ],
                    "distance_between_stations": 50.0,  # Will create multiple stations
                }
            ],
        }

        result_config, summary = expand_ctd_sections(config)

        station_names = [s["name"] for s in result_config["stations"]]

        # All names should be unique despite multiple collisions
        assert len(station_names) == len(set(station_names))

        # Should have appropriate collision-resolved names
        collision_names = [
            name
            for name in station_names
            if "_01" in name or "_02" in name or "_03" in name
        ]
        assert (
            len(collision_names) > 0
        ), f"No collision resolution found in: {station_names}"

        # Original stations should still exist
        assert "Route_A_Stn001" in station_names
        assert "Route_A_Stn001_01" in station_names  # Pre-existing collision resolution
        assert "Route_A_Stn002" in station_names

    def test_collision_counter_increments_correctly(self):
        """Test that collision counter increments properly."""
        # Create scenario with extensive existing names
        existing_stations = []
        for i in range(1, 6):  # _01 through _05
            existing_stations.append(
                {"name": f"Busy_Section_Stn001_{i:02d}", "operation_type": "CTD"}
            )

        config = {
            "stations": [
                {"name": "Busy_Section_Stn001", "operation_type": "CTD"}  # Original
            ]
            + existing_stations,
            "transits": [
                {
                    "name": "Busy Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 60.0, "longitude": -40.0},
                        {"latitude": 60.05, "longitude": -40.05},
                    ],
                    "distance_between_stations": 200.0,  # Will create 2 stations
                }
            ],
        }

        result_config, summary = expand_ctd_sections(config)

        station_names = [s["name"] for s in result_config["stations"]]

        # Should have new stations with _06 suffix for the colliding Stn001
        assert "Busy_Section_Stn001_06" in station_names
        # Second station (Stn002) should be unique, no suffix needed
        assert "Busy_Section_Stn002" in station_names

        # All names should be unique
        assert len(station_names) == len(set(station_names))

    def test_name_sanitization_prevents_collisions(self):
        """Test that name sanitization doesn't create unintended collisions."""
        config = {
            "stations": [
                {
                    "name": "Test_Route_Stn001",
                    "operation_type": "CTD",
                }  # Existing sanitized name
            ],
            "transits": [
                {
                    "name": "Test-Route!",  # Special chars will be sanitized to "Test_Route"
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 55.0, "longitude": -35.0},
                        {"latitude": 55.1, "longitude": -35.1},
                    ],
                    "distance_between_stations": 100.0,
                }
            ],
        }

        result_config, summary = expand_ctd_sections(config)

        station_names = [s["name"] for s in result_config["stations"]]

        # Should detect collision and resolve it
        assert "Test_Route_Stn001" in station_names  # Original
        assert any(
            "Test_Route_Stn001_" in name for name in station_names
        ), f"No collision resolution in: {station_names}"

        # All names unique
        assert len(station_names) == len(set(station_names))


class TestNameSanitization:
    """Test robust name sanitization logic."""

    def test_special_character_replacement(self):
        """Test that special characters are properly replaced."""
        config = {
            "transits": [
                {
                    "name": "Test-Section #1 (North->South) @50°N",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0, "longitude": -30.0},
                        {"latitude": 51.0, "longitude": -31.0},
                    ],
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        station_names = [s["name"] for s in result_config["stations"]]

        for name in station_names:
            # Should only contain alphanumeric and underscores
            assert all(
                c.isalnum() or c == "_" for c in name
            ), f"Invalid characters in: {name}"
            # Should not start/end with underscore
            assert not name.startswith("_"), f"Name starts with underscore: {name}"
            assert not name.endswith("_"), f"Name ends with underscore: {name}"
            # Should not have consecutive underscores
            assert "__" not in name, f"Consecutive underscores in: {name}"

    def test_unicode_and_special_cases(self):
        """Test handling of unicode and edge case characters."""
        config = {
            "transits": [
                {
                    "name": "Ålesund→Bergen_Øresund",  # Unicode characters
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 62.0, "longitude": 6.0},
                        {"latitude": 60.0, "longitude": 5.0},
                    ],
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        station_names = [s["name"] for s in result_config["stations"]]

        # Should properly sanitize unicode characters
        for name in station_names:
            assert all(c.isascii() for c in name), f"Non-ASCII character in: {name}"
            assert all(
                c.isalnum() or c == "_" for c in name
            ), f"Invalid character in: {name}"

    def test_empty_name_after_sanitization(self):
        """Test handling when name becomes empty after sanitization."""
        config = {
            "transits": [
                {
                    "name": "!@#$%^&*()",  # Only special characters
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 45.0, "longitude": -25.0},
                        {"latitude": 46.0, "longitude": -26.0},
                    ],
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        # Should handle gracefully and create some valid names
        if "stations" in result_config:
            station_names = [s["name"] for s in result_config["stations"]]
            for name in station_names:
                assert len(name) > 0, "Empty station name created"
                assert name != "_", "Name is just underscore"


class TestDuplicateNameDetection:
    """Test the general duplicate name detection functions."""

    def test_check_duplicate_station_names(self):
        """Test detection of duplicate station names."""
        # Create mock cruise with duplicate station names
        cruise = MagicMock()

        station1 = MagicMock()
        station1.name = "DUPLICATE_STN"

        station2 = MagicMock()
        station2.name = "UNIQUE_STN"

        station3 = MagicMock()
        station3.name = "DUPLICATE_STN"  # Same as station1

        cruise.config.stations = [station1, station2, station3]
        cruise.config.legs = []
        cruise.config.sections = []
        cruise.config.moorings = []

        errors, warnings = check_duplicate_names(cruise)

        # Should detect the duplicate station name
        assert len(errors) == 1
        assert "DUPLICATE_STN" in errors[0]
        assert "found 2 times" in errors[0]

    def test_check_duplicate_leg_names(self):
        """Test detection of duplicate leg names."""
        cruise = MagicMock()

        leg1 = MagicMock()
        leg1.name = "DUPLICATE_LEG"

        leg2 = MagicMock()
        leg2.name = "DUPLICATE_LEG"

        cruise.config.stations = []
        cruise.config.legs = [leg1, leg2]
        cruise.config.sections = []
        cruise.config.moorings = []

        errors, warnings = check_duplicate_names(cruise)

        # Should detect the duplicate leg name
        assert len(errors) == 1
        assert "DUPLICATE_LEG" in errors[0]

    def test_check_complete_duplicates(self):
        """Test detection of completely identical stations."""
        cruise = MagicMock()

        # Create mock operation types and actions that compare equal
        ctd_op_type = MagicMock()
        profile_action = MagicMock()

        # Create stations with identical coordinates and operations
        station1 = MagicMock()
        station1.name = "STN_A"
        station1.position.latitude = 50.0
        station1.position.longitude = -30.0
        station1.operation_type = ctd_op_type  # Same object reference
        station1.action = profile_action  # Same object reference

        station2 = MagicMock()
        station2.name = "STN_B"
        station2.position.latitude = 50.0  # Same coordinates
        station2.position.longitude = -30.0
        station2.operation_type = ctd_op_type  # Same object reference
        station2.action = profile_action  # Same object reference

        station3 = MagicMock()
        station3.name = "STN_C"
        station3.position.latitude = 51.0  # Different coordinates
        station3.position.longitude = -31.0
        station3.operation_type = ctd_op_type
        station3.action = profile_action

        cruise.config.stations = [station1, station2, station3]

        errors, warnings = check_complete_duplicates(cruise)

        # Should warn about potential duplicates
        assert len(warnings) == 1
        assert "STN_A" in warnings[0] and "STN_B" in warnings[0]
        assert "identical coordinates and operations" in warnings[0]

    def test_no_duplicates_clean_config(self):
        """Test that clean configuration produces no duplicate errors."""
        cruise = MagicMock()

        station1 = MagicMock()
        station1.name = "UNIQUE_STN_001"

        station2 = MagicMock()
        station2.name = "UNIQUE_STN_002"

        leg1 = MagicMock()
        leg1.name = "LEG_001"

        cruise.config.stations = [station1, station2]
        cruise.config.legs = [leg1]
        cruise.config.sections = []
        cruise.config.moorings = []

        errors, warnings = check_duplicate_names(cruise)

        # Should have no errors or warnings
        assert len(errors) == 0
        assert len(warnings) == 0

        errors, warnings = check_complete_duplicates(cruise)
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_attribute_safety_in_duplicate_check(self):
        """Test that missing attributes are handled gracefully."""
        cruise = MagicMock()

        # Create cruise without some attributes
        cruise.config.stations = []
        # Remove other attributes to test hasattr checks
        if hasattr(cruise.config, "legs"):
            delattr(cruise.config, "legs")
        if hasattr(cruise.config, "sections"):
            delattr(cruise.config, "sections")
        if hasattr(cruise.config, "moorings"):
            delattr(cruise.config, "moorings")

        # Should not crash
        errors, warnings = check_duplicate_names(cruise)

        # May have empty results, but should not error
        assert isinstance(errors, list)
        assert isinstance(warnings, list)


class TestSphericalInterpolation:
    """Test the spherical interpolation improvements."""

    def test_great_circle_interpolation_accuracy(self):
        """Test that spherical interpolation follows great circle path."""
        config = {
            "transits": [
                {
                    "name": "Great_Circle_Test",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 0.0, "longitude": 0.0},  # Equator, Prime Meridian
                        {"latitude": 0.0, "longitude": 90.0},  # Equator, 90°E
                    ],
                    "distance_between_stations": 2000.0,  # Large spacing for few points
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        stations = result_config["stations"]

        # For great circle along equator, all intermediate points should have lat ≈ 0
        for station in stations:
            lat = station["latitude"]
            lon = station["longitude"]

            # Latitude should remain close to 0 (equator)
            assert abs(lat) < 1e-5, f"Station not on equator: lat={lat}, lon={lon}"

            # Longitude should be between start and end
            assert 0.0 <= lon <= 90.0, f"Longitude out of expected range: {lon}"

    def test_short_distance_interpolation(self):
        """Test interpolation for very short distances."""
        config = {
            "transits": [
                {
                    "name": "Short_Distance_Test",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 50.0000, "longitude": -30.0000},
                        {"latitude": 50.0001, "longitude": -30.0001},  # ~15m apart
                    ],
                    "distance_between_stations": 100.0,  # Forces minimum 2 stations
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        stations = result_config["stations"]

        # Should have at least 2 stations
        assert len(stations) >= 2

        # First station should be at start
        first = stations[0]
        assert abs(first["latitude"] - 50.0000) < 1e-6
        assert abs(first["longitude"] - (-30.0000)) < 1e-6

        # Last station should be at end
        last = stations[-1]
        assert abs(last["latitude"] - 50.0001) < 1e-6
        assert abs(last["longitude"] - (-30.0001)) < 1e-6

    def test_polar_region_interpolation(self):
        """Test interpolation near polar regions where spherical effects are more pronounced."""
        config = {
            "transits": [
                {
                    "name": "Arctic_Section",
                    "operation_type": "CTD",
                    "action": "section",
                    "route": [
                        {"latitude": 89.0, "longitude": 0.0},  # Near North Pole
                        {
                            "latitude": 89.0,
                            "longitude": 180.0,
                        },  # Same latitude, opposite longitude
                    ],
                    "distance_between_stations": 500.0,
                }
            ]
        }

        result_config, summary = expand_ctd_sections(config)

        stations = result_config["stations"]

        # Should create multiple stations
        assert len(stations) >= 2

        # All stations should have high latitude
        for station in stations:
            lat = station["latitude"]
            assert lat > 88.0, f"Station latitude too low for Arctic test: {lat}"

        # Longitudes should span from 0 to 180
        longitudes = [s["longitude"] for s in stations]
        assert min(longitudes) <= 5.0, "Starting longitude not near 0"
        assert max(longitudes) >= 175.0, "Ending longitude not near 180"
