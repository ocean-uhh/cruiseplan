"""Tests for cruiseplan.utils.global_ports module - Global port registry system."""

import warnings

import pytest

from cruiseplan.core.validation import PortDefinition
from cruiseplan.utils.global_ports import (
    GLOBAL_PORTS,
    get_available_ports,
    resolve_port_reference,
)


class TestGlobalPorts:
    """Test the global port registry and resolution system."""

    def test_global_ports_registry_structure(self):
        """Test that GLOBAL_PORTS has expected structure."""
        assert isinstance(GLOBAL_PORTS, dict)
        assert len(GLOBAL_PORTS) > 0

        # Check that known ports exist
        assert "port_reykjavik" in GLOBAL_PORTS
        assert "port_bergen" in GLOBAL_PORTS
        assert "port_southampton" in GLOBAL_PORTS

        # Check port structure
        reykjavik = GLOBAL_PORTS["port_reykjavik"]
        assert "name" in reykjavik
        assert "latitude" in reykjavik
        assert "longitude" in reykjavik
        assert isinstance(reykjavik["latitude"], (int, float))
        assert isinstance(reykjavik["longitude"], (int, float))

    def test_resolve_port_reference_global_port(self):
        """Test resolving reference to global port."""
        # Test with proper port_ prefix
        port = resolve_port_reference("port_reykjavik")

        assert isinstance(port, PortDefinition)
        assert port.name == "Reykjavik"
        assert port.latitude == 64.1466
        assert port.longitude == -21.9426

    def test_resolve_port_reference_port_definition(self):
        """Test resolving PortDefinition object directly."""
        original_port = PortDefinition(
            name="Custom_Port",
            latitude=70.0,
            longitude=30.0,
            timezone="GMT+1",
        )

        resolved_port = resolve_port_reference(original_port)

        assert resolved_port == original_port
        assert resolved_port.name == "Custom_Port"
        assert resolved_port.latitude == 70.0
        assert resolved_port.longitude == 30.0

    def test_resolve_port_reference_dict_format(self):
        """Test resolving port from dictionary format."""
        port_dict = {
            "name": "Dict_Port",
            "latitude": 55.0,
            "longitude": -15.0,
        }

        port = resolve_port_reference(port_dict)

        assert isinstance(port, PortDefinition)
        assert port.name == "Dict_Port"
        assert port.latitude == 55.0
        assert port.longitude == -15.0

    def test_resolve_port_reference_string_warning(self):
        """Test that string without port_ prefix generates warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            port = resolve_port_reference("Reykjavik")

            # Should generate warning about missing port_ prefix
            assert len(w) > 0
            warning_message = str(w[0].message)
            assert "port_" in warning_message
            assert "Reykjavik" in warning_message

            # Should still create a basic port
            assert isinstance(port, PortDefinition)
            assert port.name == "Reykjavik"

    def test_resolve_port_reference_invalid_type(self):
        """Test error for invalid port reference type."""
        with pytest.raises(ValueError, match="Invalid port reference type"):
            resolve_port_reference(12345)  # Invalid type

    def test_resolve_port_reference_unknown_global_port(self):
        """Test error for unknown global port reference."""
        with pytest.raises(ValueError, match="not found in global registry"):
            resolve_port_reference("port_unknown_location")

    def test_get_available_ports(self):
        """Test getting dictionary of available global ports."""
        available_ports = get_available_ports()

        assert isinstance(available_ports, dict)
        assert len(available_ports) > 0
        # Verify structure contains port IDs as keys and descriptions as values
        for port_id, description in available_ports.items():
            assert isinstance(port_id, str)
            assert isinstance(description, str)
            assert port_id.startswith("port_")

        # Should include known ports
        assert "port_reykjavik" in available_ports
        assert "port_halifax" in available_ports


class TestPortValidation:
    """Test port validation and error handling."""

    def test_resolve_incomplete_dict_port(self):
        """Test error for incomplete port dictionary."""
        incomplete_port = {
            "name": "Incomplete_Port",
            "latitude": 60.0,
            # Missing longitude
        }

        with pytest.raises(ValueError, match="Port dictionary missing required fields"):
            resolve_port_reference(incomplete_port)

    def test_resolve_dict_port_invalid_coordinates(self):
        """Test error for invalid coordinates in port dictionary."""
        invalid_port = {
            "name": "Invalid_Port",
            "latitude": "not_a_number",  # Invalid
            "longitude": -20.0,
        }

        with pytest.raises(ValueError):
            resolve_port_reference(invalid_port)

    def test_global_ports_coordinate_ranges(self):
        """Test that global ports have valid coordinate ranges."""
        for port_id, port_data in GLOBAL_PORTS.items():
            lat = port_data["latitude"]
            lon = port_data["longitude"]

            # Latitude should be between -90 and 90
            assert -90 <= lat <= 90, f"Port {port_id} has invalid latitude: {lat}"

            # Longitude should be between -180 and 180 (or 0 and 360)
            assert (-180 <= lon <= 180) or (
                0 <= lon <= 360
            ), f"Port {port_id} has invalid longitude: {lon}"

    def test_port_definition_creation_from_global(self):
        """Test that PortDefinition is created correctly from global port data."""
        # Test multiple global ports
        test_ports = ["port_reykjavik", "port_bergen", "port_southampton"]

        for port_ref in test_ports:
            port = resolve_port_reference(port_ref)

            assert isinstance(port, PortDefinition)
            assert isinstance(port.name, str)
            assert len(port.name) > 0
            assert isinstance(port.latitude, (int, float))
            assert isinstance(port.longitude, (int, float))

            # Optional fields should be strings if present
            if port.timezone is not None:
                assert isinstance(port.timezone, str)
            if port.description is not None:
                assert isinstance(port.description, str)


class TestPortRegistry:
    """Test the port registry functionality."""

    def test_port_registry_completeness(self):
        """Test that port registry has expected research ports."""
        # Key research ports that should be available
        expected_ports = [
            "port_reykjavik",
            "port_bergen",
            "port_southampton",
            "port_tromso",
        ]

        for port_id in expected_ports:
            assert port_id in GLOBAL_PORTS, f"Missing expected research port: {port_id}"

    def test_port_data_consistency(self):
        """Test that all ports have consistent data structure."""
        required_fields = {"name", "latitude", "longitude"}
        optional_fields = {"timezone", "description", "display_name"}

        for port_id, port_data in GLOBAL_PORTS.items():
            # Check required fields
            for field in required_fields:
                assert (
                    field in port_data
                ), f"Port {port_id} missing required field: {field}"
                assert (
                    port_data[field] is not None
                ), f"Port {port_id} has None value for: {field}"

            # Check that only known fields are present
            all_fields = required_fields | optional_fields
            for field in port_data:
                assert field in all_fields, f"Port {port_id} has unknown field: {field}"
