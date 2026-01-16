"""Tests for cruiseplan.core.cruise module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.core.cruise import CruiseInstance
from cruiseplan.core.organizational import ReferenceError


class TestReferenceError:
    """Test the ReferenceError exception class."""

    def test_reference_error_creation(self):
        """Test that ReferenceError can be created and raised."""
        with pytest.raises(ReferenceError):
            raise ReferenceError("Test reference not found")


class TestCruise:
    """Test the main CruiseInstance class."""

    def setup_method(self):
        """Set up common test data."""
        self.test_yaml_data = {
            "cruise_name": "Test Cruise 2024",
            "default_vessel_speed": 10.0,
            "calculate_transfer_between_sections": True,
            "calculate_depth_via_bathymetry": True,
            "turnaround_time": 30.0,
            "points": [
                {
                    "name": "STN_001",
                    "latitude": 60.0,
                    "longitude": -20.0,
                    "operation_type": "CTD",
                    "action": "profile",
                    "operation_depth": 1000.0,
                    "water_depth": 1200.0,
                },
                {
                    "name": "STN_002",
                    "latitude": 61.0,
                    "longitude": -21.0,
                    "operation_type": "CTD",
                    "action": "profile",
                    "operation_depth": 1500.0,
                    "water_depth": 1800.0,
                },
                {
                    "name": "STN_003",
                    "latitude": 62.0,
                    "longitude": -22.0,
                    "operation_type": "mooring",
                    "action": "deployment",
                },
            ],
            "lines": [
                {
                    "name": "TRANS_001",
                    "route": [
                        {"latitude": 60.0, "longitude": -20.0},
                        {"latitude": 61.0, "longitude": -21.0},
                    ],
                    "vessel_speed": 10.0,
                }
            ],
            "areas": [
                {
                    "name": "SURVEY_001",
                    "corners": [
                        {"latitude": 60.0, "longitude": -20.0},
                        {"latitude": 61.0, "longitude": -20.0},
                        {"latitude": 61.0, "longitude": -21.0},
                    ],
                    "duration": 480.0,
                }
            ],
            "ports": [
                {"name": "REYKJAVIK", "latitude": 64.1466, "longitude": -21.9426}
            ],
            "legs": [
                {
                    "name": "Leg_1",
                    "departure_port": "REYKJAVIK",
                    "arrival_port": "REYKJAVIK",
                    "activities": ["STN_001", "STN_002"],
                    "clusters": [
                        {
                            "name": "CTD_Cluster",
                            "strategy": "sequential",
                            "activities": ["STN_003"],
                            "ordered": True,
                        }
                    ],
                }
            ],
        }

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_cruise_initialization_success(self, mock_load_yaml):
        """Test successful cruise initialization."""
        mock_load_yaml.return_value = self.test_yaml_data

        # Create a mock port object for resolution
        mock_port = MagicMock()
        mock_port.name = "REYKJAVIK"
        mock_port.latitude = 64.1466
        mock_port.longitude = -21.9426
        mock_port.display_name = "Reykjavik, Iceland"

        with patch("cruiseplan.core.cruise.resolve_port_reference") as mock_resolve:
            mock_resolve.return_value = mock_port

            cruise = CruiseInstance("test_config.yaml")

            assert cruise.config_path == Path("test_config.yaml")
            assert cruise.raw_data == self.test_yaml_data
            assert cruise.config.cruise_name == "Test Cruise 2024"

            # Check registries were built
            assert len(cruise.point_registry) == 3
            assert "STN_001" in cruise.point_registry
            assert "STN_002" in cruise.point_registry
            assert "STN_003" in cruise.point_registry

            assert len(cruise.line_registry) == 1
            assert "TRANS_001" in cruise.line_registry

            assert len(cruise.area_registry) == 1
            assert "SURVEY_001" in cruise.area_registry

            assert len(cruise.port_registry) == 1
            assert "REYKJAVIK" in cruise.port_registry

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_load_yaml_called(self, mock_load_yaml):
        """Test that _load_yaml method is called during initialization."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            _cruise = CruiseInstance("test_config.yaml")

            mock_load_yaml.assert_called_once_with(Path("test_config.yaml"))

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_cruise_with_minimal_config(self, mock_load_yaml):
        """Test cruise with minimal configuration."""
        minimal_config = {
            "cruise_name": "Minimal Test",
            "default_vessel_speed": 10.0,
            "calculate_transfer_between_sections": True,
            "calculate_depth_via_bathymetry": True,
            "points": [
                {
                    "name": "STN_001",
                    "latitude": 60.0,
                    "longitude": -20.0,
                    "operation_type": "CTD",
                    "action": "profile",
                }
            ],
            "ports": [{"name": "TEST_PORT", "latitude": 64.0, "longitude": -22.0}],
            "legs": [
                {
                    "name": "Test_Leg",
                    "departure_port": "TEST_PORT",
                    "arrival_port": "TEST_PORT",
                    "activities": ["STN_001"],
                }
            ],
        }
        mock_load_yaml.return_value = minimal_config

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("minimal_config.yaml")

            assert cruise.config.cruise_name == "Minimal Test"
            assert len(cruise.point_registry) == 1
            assert len(cruise.line_registry) == 0
            assert len(cruise.area_registry) == 0
            assert len(cruise.port_registry) == 1  # TEST_PORT is defined

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_cruise_empty_registries(self, mock_load_yaml):
        """Test cruise with None values for optional lists."""
        config_with_nones = {
            "cruise_name": "Empty Test",
            "default_vessel_speed": 10.0,
            "calculate_transfer_between_sections": True,
            "calculate_depth_via_bathymetry": True,
            "points": None,
            "lines": None,
            "areas": None,
            "ports": [{"name": "EMPTY_PORT", "latitude": 64.0, "longitude": -22.0}],
            "legs": [
                {
                    "name": "Empty_Leg",
                    "departure_port": "EMPTY_PORT",
                    "arrival_port": "EMPTY_PORT",
                    "activities": [],
                }
            ],
        }
        mock_load_yaml.return_value = config_with_nones

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("empty_config.yaml")

            # Should handle None gracefully
            assert len(cruise.point_registry) == 0
            assert len(cruise.line_registry) == 0
            assert len(cruise.area_registry) == 0
            assert len(cruise.port_registry) == 1  # EMPTY_PORT is defined

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_references_success(self, mock_load_yaml):
        """Test successful reference resolution."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            # References should have been resolved
            leg = cruise.config.legs[0]
            assert len(leg.activities) == 2
            # After resolution, these should be StationDefinition objects
            assert hasattr(leg.activities[0], "name")
            assert hasattr(leg.activities[1], "name")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_references_invalid_station(self, mock_load_yaml):
        """Test reference resolution with invalid station reference."""
        invalid_config = self.test_yaml_data.copy()
        invalid_config["legs"] = [
            {
                "name": "Bad_Leg",
                "departure_port": "REYKJAVIK",
                "arrival_port": "REYKJAVIK",
                "activities": ["STN_001", "INVALID_STATION"],
            }
        ]
        mock_load_yaml.return_value = invalid_config

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            with pytest.raises(ReferenceError):
                CruiseInstance("invalid_config.yaml")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_mixed_list_stations(self, mock_load_yaml):
        """Test resolving mixed list with stations."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            # Test the _resolve_mixed_list method
            mixed_items = ["STN_001", "TRANS_001", "SURVEY_001"]
            resolved = cruise._resolve_mixed_list(mixed_items)

            assert len(resolved) == 3
            # Should have resolved to actual definition objects
            assert hasattr(resolved[0], "name")  # StationDefinition
            assert hasattr(resolved[1], "name")  # TransitDefinition
            assert hasattr(resolved[2], "name")  # AreaDefinition

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_mixed_list_invalid_reference(self, mock_load_yaml):
        """Test resolving mixed list with invalid reference."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            # Test with invalid reference
            mixed_items = ["STN_001", "INVALID_REF"]
            with pytest.raises(ReferenceError):
                cruise._resolve_mixed_list(mixed_items)

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_config_ports_success(self, mock_load_yaml):
        """Test successful port resolution within leg definitions."""
        config_with_ports = self.test_yaml_data.copy()
        # Ports are now defined within legs, not at cruise level
        mock_load_yaml.return_value = config_with_ports

        # Create a mock port object for resolution
        mock_port = MagicMock()
        mock_port.name = "REYKJAVIK"
        mock_port.latitude = 64.1466
        mock_port.longitude = -21.9426
        mock_port.display_name = "Reykjavik, Iceland"

        with patch("cruiseplan.core.cruise.resolve_port_reference") as mock_resolve:
            mock_resolve.return_value = mock_port

            cruise = CruiseInstance("config_with_ports.yaml")

            # Port "REYKJAVIK" is already defined in ports registry, so no resolution needed
            # Test that the cruise loaded successfully and ports are in registry
            assert "REYKJAVIK" in cruise.port_registry
            assert len(cruise.runtime_legs) == 1

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_config_ports_global_lookup(self, mock_load_yaml):
        """Test port resolution with global port lookup for leg ports."""
        config_with_global_port = self.test_yaml_data.copy()
        # Test still uses existing leg structure which has valid ports
        mock_load_yaml.return_value = config_with_global_port

        # Mock global port definition
        mock_global_port = MagicMock()
        mock_global_port.name = "REYKJAVIK"
        mock_global_port.latitude = 64.1466
        mock_global_port.longitude = -21.9426

        with patch("cruiseplan.core.cruise.resolve_port_reference") as mock_resolve:
            mock_resolve.return_value = mock_global_port

            cruise = CruiseInstance("config_with_global_port.yaml")

            # Should have added the global port to registry
            assert "REYKJAVIK" in cruise.port_registry

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_config_ports_not_found(self, mock_load_yaml):
        """Test port resolution when port is not found in legs."""
        config_with_missing_port = self.test_yaml_data.copy()
        # Modify leg to reference a missing port
        config_with_missing_port["legs"][0]["departure_port"] = "DEFINITELY_NOT_A_PORT"
        mock_load_yaml.return_value = config_with_missing_port

        with patch("cruiseplan.core.cruise.resolve_port_reference") as mock_resolve:
            mock_resolve.side_effect = ValueError(
                "Port reference 'DEFINITELY_NOT_A_PORT' not found"
            )

            with pytest.raises((ValueError, ReferenceError)):
                CruiseInstance("config_with_missing_port.yaml")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_convert_leg_definitions_to_legs(self, mock_load_yaml):
        """Test conversion of LegDefinition to runtime Leg objects."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            assert len(cruise.runtime_legs) == 1
            leg = cruise.runtime_legs[0]
            assert leg.name == "Leg_1"
            assert hasattr(
                leg, "operations"
            )  # Runtime legs have 'operations', not 'stations'
            assert hasattr(leg, "clusters")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_anchor_exists_in_catalog_station(self, mock_load_yaml):
        """Test anchor existence check for stations."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            assert cruise._anchor_exists_in_catalog("STN_001") is True
            assert cruise._anchor_exists_in_catalog("NONEXISTENT") is False

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_anchor_exists_in_catalog_area(self, mock_load_yaml):
        """Test anchor existence check for areas."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            assert cruise._anchor_exists_in_catalog("SURVEY_001") is True

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_anchor_exists_in_catalog_transect(self, mock_load_yaml):
        """Test anchor existence check for lines."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            assert cruise._anchor_exists_in_catalog("TRANS_001") is True

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_list_with_objects(self, mock_load_yaml):
        """Test resolving list that contains objects instead of strings."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            # Test with a list containing actual objects (not strings)
            station_obj = cruise.point_registry["STN_001"]
            mixed_list = ["STN_002", station_obj]  # String and object

            resolved = cruise._resolve_list(
                mixed_list, cruise.point_registry, "Station"
            )
            assert len(resolved) == 2
            assert resolved[1] == station_obj  # Object should be kept as-is

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_resolve_list_invalid_reference(self, mock_load_yaml):
        """Test resolving list with invalid reference."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("test_config.yaml")

            # Test with invalid station reference
            invalid_list = ["STN_001", "INVALID_STATION"]

            with pytest.raises(ReferenceError):
                cruise._resolve_list(invalid_list, cruise.point_registry, "Station")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_cluster_modern_activities_field(self, mock_load_yaml):
        """Test handling of modern 'activities' field in clusters."""
        config_with_modern = self.test_yaml_data.copy()
        config_with_modern["legs"] = [
            {
                "name": "Modern_Leg",
                "departure_port": "REYKJAVIK",
                "arrival_port": "REYKJAVIK",
                "clusters": [
                    {
                        "name": "Modern_Cluster",
                        "activities": ["STN_001", "STN_002"],  # Modern field
                    }
                ],
            }
        ]
        mock_load_yaml.return_value = config_with_modern

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            cruise = CruiseInstance("config_with_modern.yaml")

            # Should work with modern field
            cluster = cruise.config.legs[0].clusters[0]
            assert len(cluster.activities) == 2

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_cruise_pathlib_path_input(self, mock_load_yaml):
        """Test cruise initialization with pathlib.Path input."""
        mock_load_yaml.return_value = self.test_yaml_data

        with patch("cruiseplan.core.cruise.resolve_port_reference"):
            path_input = Path("test_path_config.yaml")
            cruise = CruiseInstance(path_input)

            assert cruise.config_path == path_input
            assert isinstance(cruise.config_path, Path)

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_file_not_found_error(self, mock_load_yaml):
        """Test handling of FileNotFoundError during YAML loading."""
        mock_load_yaml.side_effect = FileNotFoundError("File not found")

        with pytest.raises(FileNotFoundError):
            CruiseInstance("nonexistent.yaml")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_yaml_parsing_error(self, mock_load_yaml):
        """Test handling of YAML parsing errors."""
        from cruiseplan.schema.yaml_io import YAMLIOError

        mock_load_yaml.side_effect = YAMLIOError("Invalid YAML")

        with pytest.raises(YAMLIOError):
            CruiseInstance("invalid.yaml")

    @patch("cruiseplan.core.cruise.load_yaml")
    def test_validation_error(self, mock_load_yaml):
        """Test handling of Pydantic validation errors."""
        from pydantic import ValidationError

        invalid_config = {"invalid_field": "invalid_value"}
        mock_load_yaml.return_value = invalid_config

        with pytest.raises(ValidationError):
            CruiseInstance("invalid_schema.yaml")
