from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from cruiseplan.core.validation import CruiseConfigurationError
from cruiseplan.utils.config import format_station_for_yaml, format_transect_for_yaml

# Mock the external dependencies (CruiseConfig, ValidationError, CruiseConfigurationError)
# Assuming FALLBACK_DEPTH is -9999.0 for testing the formatters.
FALLBACK_DEPTH = -9999.0

# Import the system under test
from cruiseplan.utils.config import ConfigLoader, save_cruise_config


def test_format_station_standard():
    """Test standard station formatting with depth."""
    input_data = {"lat": 47.1234567, "lon": -52.9876543, "depth": 250.55}
    index = 5

    result = format_station_for_yaml(input_data, index)

    expected = {
        "name": "STN_005",  # Padding check (03d)
        "latitude": 47.12346,  # Rounding check (5 decimals)
        "longitude": -52.98765,  # Rounding check (5 decimals)
        "depth": 250.6,  # Depth rounding (1 decimal)
        "comment": "Interactive selection",
        "operation_type": "CTD",
        "action": "profile",
    }

    assert result == expected


def test_format_station_missing_depth():
    """Test fallback when depth is missing (e.g. bathymetry failed)."""
    input_data = {"lat": 10.0, "lon": 10.0}  # No depth key
    index = 1

    result = format_station_for_yaml(input_data, index)

    # Should default to -9999
    assert result["depth"] == -9999


def test_format_transect_standard():
    """Test standard transect formatting."""
    input_data = {
        "start": {"lat": 10.12345678, "lon": 20.12345678},
        "end": {"lat": 30.98765432, "lon": 40.98765432},
    }
    index = 2

    result = format_transect_for_yaml(input_data, index)

    expected_structure = {
        "name": "Section_02",  # Padding check (02d)
        "comment": "Interactive transect",
        "operation_type": "underway",
        "action": "ADCP",
        "vessel_speed": "10.0",
        "route": [
            {
                "latitude": 10.12346,
                "longitude": 20.12346,
            },  # Rounding check (5 decimals)
            {"latitude": 30.98765, "longitude": 40.98765},
        ],
        "reversible": True,
    }

    assert result == expected_structure
    # Double check it matches the structure exactly
    assert result["route"][0]["latitude"] == 10.12346
    assert result["route"][1]["longitude"] == 40.98765


# --- Mocking Dependencies ---


# We need to simulate the Pydantic behavior for ConfigLoader tests
class MockCruiseConfig:
    """A mock class to simulate successful Pydantic parsing."""

    def __init__(self, **kwargs):
        self.data = kwargs
        if "raise_validation_error" in kwargs:
            # Simulation of a validation error (e.g., in a model validator)
            raise MockValidationError(
                [
                    {"loc": ("cruise_name",), "msg": "name missing"},
                    {"loc": ("legs", 0, "name"), "msg": "leg name invalid"},
                ]
            )

    # Mock behavior of the real CruiseConfig instance
    def __eq__(self, other):
        return isinstance(other, MockCruiseConfig) and self.data == other.data


class MockValidationError(Exception):
    """A mock class to simulate Pydantic's ValidationError."""

    def __init__(self, errors_list):
        self._errors = errors_list
        super().__init__("Mock Validation Error")

    def errors(self):
        return self._errors


# Patch the imports inside the ConfigLoader to use our mocks
@patch("cruiseplan.utils.config.CruiseConfig", MockCruiseConfig)
@patch("cruiseplan.utils.config.ValidationError", MockValidationError)
class TestConfigLoader:

    def setup_method(self):
        self.mock_path = Path("test_config.yaml")
        self.valid_yaml = "cruise_name: Test\ndefault_vessel_speed: 10.0"
        self.valid_data = {"cruise_name": "Test", "default_vessel_speed": 10.0}

    # --- load_raw_data tests ---

    @patch.object(Path, "exists", return_value=False)
    def test_load_raw_data_file_not_found(self, mock_exists):
        """Tests the file not found exception path."""
        loader = ConfigLoader(self.mock_path)
        with pytest.raises(CruiseConfigurationError, match="not found"):
            loader.load_raw_data()

    @patch.object(Path, "exists", return_value=True)
    @patch("builtins.open", mock_open(read_data=""))
    @patch(
        "cruiseplan.utils.config.yaml.safe_load", side_effect=yaml.YAMLError("Bad YAML")
    )
    def test_load_raw_data_yaml_error(self, mock_load, mock_exists):
        """Tests the generic YAML parsing error path."""
        loader = ConfigLoader(self.mock_path)
        with pytest.raises(CruiseConfigurationError, match="Failed to load or parse"):
            loader.load_raw_data()

    @patch.object(Path, "exists", return_value=True)
    @patch(
        "cruiseplan.utils.config.yaml.safe_load", return_value=[]
    )  # Invalid root structure
    def test_load_raw_data_invalid_root_structure(self, mock_load, mock_exists):
        """Tests the path where the YAML file root is not a dict."""
        with patch("builtins.open", mock_open(read_data=self.valid_yaml)):
            loader = ConfigLoader(self.mock_path)
            with pytest.raises(
                CruiseConfigurationError, match="not a valid dictionary"
            ):
                loader.load_raw_data()

    @patch.object(Path, "exists", return_value=True)
    @patch("cruiseplan.utils.config.yaml.safe_load")
    def test_load_raw_data_success(self, mock_load, mock_exists):
        """Tests successful loading of raw data."""
        mock_load.return_value = self.valid_data
        with patch("builtins.open", mock_open(read_data=self.valid_yaml)):
            loader = ConfigLoader(self.mock_path)
            data = loader.load_raw_data()
            assert data == self.valid_data
            assert loader.raw_data == self.valid_data

    # --- validate_and_parse tests ---

    def test_validate_and_parse_success(self):
        """Tests successful parsing into the CruiseConfig mock object."""
        loader = ConfigLoader(self.mock_path)
        config = loader.validate_and_parse(self.valid_data)
        assert isinstance(config, MockCruiseConfig)
        assert config.data == self.valid_data
        assert loader.cruise_config is config

    def test_validate_and_parse_validation_failure(self):
        """Tests that Pydantic's ValidationError is caught and re-raised."""
        loader = ConfigLoader(self.mock_path)
        invalid_data = self.valid_data.copy()
        invalid_data["raise_validation_error"] = True  # Trigger the mock error

        with pytest.raises(CruiseConfigurationError, match="Validation Failed"):
            loader.validate_and_parse(invalid_data)

    @patch.object(ConfigLoader, "load_raw_data", return_value=None)
    def test_validate_and_parse_no_raw_data(self, mock_load_raw):
        """Tests that load_raw_data is called if raw_data is None."""
        # Use a real ConfigLoader instance, but mock the internal load_raw_data call
        loader = ConfigLoader(self.mock_path)
        loader.load_raw_data.return_value = self.valid_data

        # Test calling validate_and_parse without data
        config = loader.validate_and_parse(raw_data=None)
        mock_load_raw.assert_called_once()
        assert isinstance(config, MockCruiseConfig)

    # --- load (full workflow) tests ---

    @patch.object(ConfigLoader, "load_raw_data")
    @patch.object(ConfigLoader, "validate_and_parse")
    def test_load_full_workflow(self, mock_parse, mock_load_raw):
        """Tests the public .load() method calls the correct sequence."""
        loader = ConfigLoader(self.mock_path)
        loader.load()
        mock_load_raw.assert_called_once()
        mock_parse.assert_called_once()


# --- Test Utility Functions (Outside ConfigLoader) ---


class TestConfigUtils:

    @patch("cruiseplan.utils.config.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("cruiseplan.utils.config.yaml.dump")
    def test_save_cruise_config_success(self, mock_dump, mock_file, mock_mkdir):
        """Tests successful file saving and correct yaml.dump parameters."""
        data = {"key": "value"}
        filepath = Path("output/test.yaml")

        save_cruise_config(data, filepath)

        mock_mkdir.assert_called_once()
        mock_file.assert_called_once_with(filepath, "w")
        mock_dump.assert_called_once_with(
            data,
            mock_file(),
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )

    @patch("cruiseplan.utils.config.Path.mkdir")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_save_cruise_config_io_error(self, mock_file, mock_mkdir):
        """Tests that file saving exceptions are caught and raised."""
        with pytest.raises(IOError, match="Permission denied"):
            save_cruise_config({}, Path("output/test.yaml"))

    def test_format_station_for_yaml(self):
        """Tests correct formatting and coordinate/depth rounding."""
        station_data = {"lat": 50.1234567, "lon": -10.9876543, "depth": 2000.123}
        formatted = format_station_for_yaml(station_data, 1)

        assert formatted["name"] == "STN_001"
        assert formatted["latitude"] == 50.12346  # Rounded to 5 places
        assert formatted["longitude"] == -10.98765  # Rounded to 5 places
        assert formatted["depth"] == 2000.1  # Rounded to 1 place
        assert formatted["comment"] == "Interactive selection"

    def test_format_station_for_yaml_missing_depth(self):
        """Tests fallback depth handling."""
        station_data = {"lat": 50.0, "lon": -10.0}
        formatted = format_station_for_yaml(station_data, 2)

        # Test for the hardcoded depth fallback used in the formatter code
        assert formatted["depth"] == -9999.0

    def test_format_transect_for_yaml(self):
        """Tests correct formatting for transect data."""
        transect_data = {
            "start": {"lat": 50.123456, "lon": -10.987654},
            "end": {"lat": 51.555555, "lon": -11.444444},
        }
        formatted = format_transect_for_yaml(transect_data, 5)

        assert formatted["name"] == "Section_05"
        assert formatted["route"][0]["latitude"] == 50.12346
        assert formatted["route"][1]["longitude"] == -11.44444
        assert formatted["reversible"] is True
