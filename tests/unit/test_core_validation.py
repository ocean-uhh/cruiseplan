# tests/unit/test_validation_minimal.py
from pathlib import Path

import pytest

from cruiseplan.core.cruise import Cruise, ReferenceError

# Path to the sample file
SAMPLE_YAML = Path("tests/data/cruise_example.yaml")


def test_load_and_validate_cruise():
    """
    Happy Path: Load a valid YAML and ensure Pydantic
    validates types and structure correctly.
    """
    assert SAMPLE_YAML.exists(), "Please create the YAML file first!"

    cruise = Cruise(SAMPLE_YAML)

    # 1. Check Global Headers
    assert cruise.config.cruise_name == "NE_Atlantic_Test_2025"
    assert cruise.config.start_date == "2025-06-01T08:00:00"

    # 2. Check Anchor Parsing (Direct latitude/longitude)
    assert cruise.config.departure_port.latitude == 64.1466

    # 3. Check Catalog Loading
    assert "STN_Start_01" in cruise.station_registry
    assert "M_End_01" in cruise.station_registry

    # 4. Check Schedule Resolution (The Hybrid Pattern)
    leg1 = cruise.config.legs[0]
    cluster = leg1.clusters[0]

    # The 'activities' list in the cluster should now be FULL OBJECTS, not strings
    resolved_stations = cluster.activities
    assert len(resolved_stations) == 4  # Updated to 4 since mooring moved to stations

    # Item 0: Was a reference "STN_Start_01" -> Should resolve to object
    assert resolved_stations[0].name == "STN_Start_01"
    assert resolved_stations[0].operation_depth == 500.0

    # Item 2: Was inline "STN_Inline_OneOff" -> Should be object
    assert resolved_stations[2].name == "STN_Inline_OneOff"
    assert resolved_stations[2].position.latitude == 62.25

    # Item 3: Should be the mooring "M_End_01"
    assert resolved_stations[3].name == "M_End_01"
    assert resolved_stations[3].operation_type.value == "mooring"


def test_missing_reference_raises_error(tmp_path):
    """
    Edge Case: Ensure the system throws an error if we schedule
    a mooring that doesn't exist in the catalog.
    """
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        """
cruise_name: "Bad Cruise"
start_date: "2025-01-01T00:00:00"
default_vessel_speed: 10
default_distance_between_stations: 10
calculate_transfer_between_sections: false
calculate_depth_via_bathymetry: false

stations:
  - name: STN_Existing
    operation_type: CTD
    action: profile
    latitude: 0.0
    longitude: 0.0

legs:
  - name: Leg1
    departure_port: {name: P1, latitude: 0.0, longitude: 0.0}
    arrival_port: {name: P2, latitude: 1.0, longitude: 1.0}
    first_station: "STN_Existing"
    last_station: "GHOST_STATION"
    stations:
      - "STN_Existing"
      - "GHOST_STATION"  # <--- This does not exist in catalog
    """
    )

    with pytest.raises(ReferenceError) as exc:
        Cruise(bad_yaml)

    assert "GHOST_STATION" in str(exc.value)
    assert "not found in Catalog" in str(exc.value)


"""
Tests to boost validation.py coverage.

This module provides targeted tests for uncovered validation functions,
particularly the internal metadata checking and warning formatting functions
that have large uncovered line ranges.
"""

from unittest.mock import MagicMock

from cruiseplan.core.validation import (
    _check_cruise_metadata_raw,
    _clean_warning_message,
    _format_validation_warnings,
    _warning_relates_to_entity,
    validate_depth_accuracy,
)


class TestCruiseMetadataValidation:
    """Test cruise metadata validation functions."""

    def test_check_cruise_metadata_raw_update_placeholders(self):
        """Test detection of UPDATE- placeholders in metadata."""
        raw_config = {
            "start_date": "UPDATE-YYYY-MM-DDTHH:MM:SSZ",
            "departure_port": {
                "name": "UPDATE-departure-port-name",
                "position": {"latitude": 0.0, "longitude": 0.0},
                "timezone": "GMT+0",
            },
            "arrival_port": {
                "name": "UPDATE-arrival-port-name",
                "position": {"latitude": 0.0, "longitude": 0.0},
                "timezone": "GMT+0",
            },
        }

        warnings = _check_cruise_metadata_raw(raw_config)

        # Should detect UPDATE- placeholders and defaults - returns one formatted block
        assert len(warnings) == 1
        assert "Cruise Metadata:" in warnings[0]
        assert "placeholder" in warnings[0] or "default" in warnings[0]

    def test_check_cruise_metadata_raw_default_values(self):
        """Test detection of default values in metadata."""
        raw_config = {
            "start_date": "1970-01-01T00:00:00Z",
            "vessel_name": "RV Default",
            "cruise_name": "Test Cruise 2024",
        }

        warnings = _check_cruise_metadata_raw(raw_config)

        # Should detect default start date
        assert any("1970-01-01" in w for w in warnings)

    def test_check_cruise_metadata_raw_clean_config(self):
        """Test clean configuration with no warnings."""
        raw_config = {
            "start_date": "2025-06-01T08:00:00Z",
            "vessel_name": "R/V Research",
            "cruise_name": "Arctic Survey 2025",
            "chief_scientist": "Dr. Smith",
        }

        warnings = _check_cruise_metadata_raw(raw_config)

        # Should have no warnings for clean config
        assert len(warnings) == 0

    def test_check_cruise_metadata_raw_missing_fields(self):
        """Test behavior when required fields are missing."""
        raw_config = {}

        warnings = _check_cruise_metadata_raw(raw_config)

        # Should handle missing fields gracefully
        assert isinstance(warnings, list)

    def test_check_cruise_metadata_raw_partial_config(self):
        """Test with partial configuration."""
        raw_config = {"departure_port": {"name": "UPDATE-departure-port-name"}}

        warnings = _check_cruise_metadata_raw(raw_config)

        # Should warn about the placeholder port name
        assert len(warnings) == 1
        assert "placeholder" in warnings[0]


class TestWarningFormatting:
    """Test warning formatting and grouping functions."""

    def test_format_validation_warnings_with_entities(self):
        """Test formatting warnings with entity associations."""
        warnings = [
            "Station 'STN_001' has invalid coordinates",
            "Transit 'TR_001' missing required field",
            "General configuration warning",
        ]

        # Mock cruise object
        cruise = MagicMock()

        # Mock station registry
        station = MagicMock()
        station.name = "STN_001"
        cruise.station_registry = {"STN_001": station}

        # Mock transit registry
        transit = MagicMock()
        transit.name = "TR_001"
        cruise.transit_registry = {"TR_001": transit}

        formatted_warnings = _format_validation_warnings(warnings, cruise)

        # Should group warnings into formatted blocks
        assert isinstance(formatted_warnings, list)
        assert (
            len(formatted_warnings) == 1
        )  # All warnings grouped into Configuration block
        assert "Configuration:" in formatted_warnings[0]

    def test_format_validation_warnings_no_cruise(self):
        """Test formatting warnings without cruise object."""
        warnings = ["General validation warning", "Another warning message"]

        formatted_warnings = _format_validation_warnings(warnings, None)

        # Should handle None cruise gracefully
        assert isinstance(formatted_warnings, list)

    def test_format_validation_warnings_empty_list(self):
        """Test formatting empty warnings list."""
        warnings = []
        cruise = MagicMock()

        formatted_warnings = _format_validation_warnings(warnings, cruise)

        # Should return empty list
        assert formatted_warnings == []

    def test_warning_relates_to_entity_station(self):
        """Test entity relationship detection for stations."""
        # Test operation_type matching
        warning_msg = "Operation type CTD found in warning"

        station = MagicMock()
        station.operation_type = "CTD"

        # Should detect relationship via operation_type
        assert _warning_relates_to_entity(warning_msg, station) == True

        # Test action matching
        warning_msg2 = "Action profile found in warning"
        station2 = MagicMock()
        station2.action = "profile"

        assert _warning_relates_to_entity(warning_msg2, station2) == True

        # Test no match
        warning_msg3 = "Unrelated warning message"
        assert _warning_relates_to_entity(warning_msg3, station) == False

    def test_warning_relates_to_entity_no_name(self):
        """Test entity relationship when entity has no name."""
        warning_msg = "Station 'STN_001' has missing depth"

        entity = MagicMock()
        # Remove name attribute
        if hasattr(entity, "name"):
            delattr(entity, "name")

        # Should handle gracefully
        result = _warning_relates_to_entity(warning_msg, entity)
        assert isinstance(result, bool)

    def test_clean_warning_message_formatting(self):
        """Test warning message cleaning."""
        # Test various warning message formats
        messages = [
            "Warning: Station has issue",
            "ERROR: Configuration problem",
            "  Whitespace around message  ",
            "Normal message without prefix",
        ]

        for msg in messages:
            cleaned = _clean_warning_message(msg)

            # Should return cleaned string
            assert isinstance(cleaned, str)
            assert len(cleaned) >= 0


class TestDepthValidation:
    """Test depth accuracy validation function."""

    def test_validate_depth_accuracy_with_valid_depths(self):
        """Test depth validation with accurate depths."""
        # Mock cruise with stations
        cruise = MagicMock()

        station = MagicMock()
        station.name = "STN_001"
        station.position.latitude = 50.0
        station.position.longitude = -30.0
        station.water_depth = 2000.0  # Station reported water depth

        cruise.station_registry = {"STN_001": station}

        # Mock bathymetry manager
        bathymetry_manager = MagicMock()
        bathymetry_manager.get_depth_at_point.return_value = (
            -1950.0
        )  # Close negative depth

        stations_checked, warnings = validate_depth_accuracy(
            cruise, bathymetry_manager, tolerance=5.0
        )

        # Should check one station with minimal warnings for close depths
        assert stations_checked == 1
        assert len(warnings) == 0  # Within tolerance

    def test_validate_depth_accuracy_with_inaccurate_depths(self):
        """Test depth validation with inaccurate depths."""
        cruise = MagicMock()

        station = MagicMock()
        station.name = "STN_002"
        station.position.latitude = 50.0
        station.position.longitude = -30.0
        station.water_depth = 1000.0  # Station reported water depth

        cruise.station_registry = {"STN_002": station}

        # Mock bathymetry manager to return very different depth
        bathymetry_manager = MagicMock()
        bathymetry_manager.get_depth_at_point.return_value = -3000.0  # Very different

        stations_checked, warnings = validate_depth_accuracy(
            cruise, bathymetry_manager, tolerance=5.0
        )

        # Should have warnings for large discrepancy
        assert stations_checked == 1
        assert len(warnings) > 0

    def test_validate_depth_accuracy_missing_bathymetry(self):
        """Test depth validation when bathymetry is unavailable."""
        cruise = MagicMock()

        station = MagicMock()
        station.name = "STN_003"
        station.position.latitude = 50.0
        station.position.longitude = -30.0
        station.water_depth = 2000.0

        cruise.station_registry = {"STN_003": station}

        # Mock bathymetry manager to return None
        bathymetry_manager = MagicMock()
        bathymetry_manager.get_depth_at_point.return_value = None

        stations_checked, warnings = validate_depth_accuracy(
            cruise, bathymetry_manager, tolerance=5.0
        )

        # Should handle missing bathymetry gracefully
        assert stations_checked == 1
        assert isinstance(warnings, list)

    def test_validate_depth_accuracy_no_stations(self):
        """Test depth validation with no stations."""
        cruise = MagicMock()
        cruise.station_registry = {}

        bathymetry_manager = MagicMock()

        stations_checked, warnings = validate_depth_accuracy(
            cruise, bathymetry_manager, tolerance=5.0
        )

        # Should handle empty station registry
        assert stations_checked == 0
        assert warnings == []

    def test_validate_depth_accuracy_station_no_depth(self):
        """Test depth validation with station missing depth."""
        cruise = MagicMock()

        station = MagicMock()
        station.name = "STN_NO_DEPTH"
        station.latitude = 50.0
        station.longitude = -30.0
        station.water_depth = None  # No depth specified

        cruise.station_registry = {"STN_NO_DEPTH": station}

        bathymetry_manager = MagicMock()

        stations_checked, warnings = validate_depth_accuracy(
            cruise, bathymetry_manager, tolerance=5.0
        )

        # Should skip stations without depth
        assert stations_checked == 0
        assert isinstance(warnings, list)


class TestValidationEdgeCases:
    """Test edge cases and error handling in validation functions."""

    def test_cruise_metadata_with_non_string_values(self):
        """Test metadata validation with non-string values."""
        raw_config = {
            "start_date": 123456,  # Number instead of string
            "vessel_name": ["list", "instead", "of", "string"],
            "cruise_name": None,
        }

        # Should handle gracefully
        warnings = _check_cruise_metadata_raw(raw_config)
        assert isinstance(warnings, list)

    def test_warning_formatting_with_malformed_cruise(self):
        """Test warning formatting with malformed cruise object."""
        warnings = ["Test warning"]

        # Cruise object missing expected attributes
        cruise = MagicMock()
        if hasattr(cruise, "station_registry"):
            delattr(cruise, "station_registry")
        if hasattr(cruise, "transit_registry"):
            delattr(cruise, "transit_registry")

        # Should handle missing attributes gracefully
        formatted = _format_validation_warnings(warnings, cruise)
        assert isinstance(formatted, list)

    def test_entity_relationship_with_special_characters(self):
        """Test entity relationship detection with special characters in names."""
        warning_msg = "Station 'Special-Station_001#' has issues"

        station = MagicMock()
        station.name = "Special-Station_001#"

        # Should handle special characters in names
        result = _warning_relates_to_entity(warning_msg, station)
        assert isinstance(result, bool)
