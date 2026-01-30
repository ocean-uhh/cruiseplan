"""
Tests for config-based API functions.

This module tests the new *_with_config functions that use configuration objects
instead of many individual parameters.

Strategy: Test the configuration interface and parameter mapping, not the business logic
(which is already tested in the legacy function tests).
"""

from unittest.mock import patch

import cruiseplan
from cruiseplan.api.config import (
    BathymetryDownloadConfig,
    EnrichConfig,
    MapConfig,
    PangaeaConfig,
    ProcessConfig,
    ScheduleConfig,
    StationsConfig,
    ValidateConfig,
)


class TestConfigFunctionBasics:
    """Test basic functionality of config-based functions."""

    def test_config_functions_exist(self):
        """Test that all config-based functions are available."""
        config_functions = [
            "bathymetry_with_config",
            "enrich_with_config",
            "map_with_config",
            "pangaea_with_config",
            "process_with_config",
            "schedule_with_config",
            "stations_with_config",
            "validate_with_config",
        ]

        for func_name in config_functions:
            assert hasattr(cruiseplan, func_name), f"Missing function: {func_name}"
            func = getattr(cruiseplan, func_name)
            assert callable(func), f"{func_name} is not callable"

    def test_config_classes_creation(self):
        """Test that all config classes can be created with defaults."""
        config_classes = {
            "BathymetryDownloadConfig": BathymetryDownloadConfig,
            "EnrichConfig": EnrichConfig,
            "MapConfig": MapConfig,
            "PangaeaConfig": PangaeaConfig,
            "ProcessConfig": ProcessConfig,
            "ScheduleConfig": ScheduleConfig,
            "StationsConfig": StationsConfig,
            "ValidateConfig": ValidateConfig,
        }

        for name, config_class in config_classes.items():
            config = config_class()
            assert config is not None, f"Failed to create {name}"


class TestParameterMapping:
    """Test that config objects correctly map to legacy function parameters."""

    @patch("cruiseplan.api.data.bathymetry")
    def test_bathymetry_config_mapping(self, mock_bathymetry):
        """Test parameter mapping for bathymetry_with_config."""
        config = BathymetryDownloadConfig(
            source="gebco2025", output_dir="/custom/path", citation=True
        )

        cruiseplan.bathymetry_with_config(config)

        mock_bathymetry.assert_called_once_with(
            bathy_source="gebco2025", output_dir="/custom/path", citation=True
        )

    @patch("cruiseplan.api.process_cruise.enrich")
    def test_enrich_config_mapping(self, mock_enrich):
        """Test parameter mapping for enrich_with_config."""
        config = EnrichConfig(coord_format="dd", expand_sections=False)
        config.bathymetry.source = "gebco2025"
        config.output.verbose = True

        cruiseplan.enrich_with_config("test.yaml", config)

        call_args = mock_enrich.call_args[1]
        assert call_args["coord_format"] == "dd"
        assert call_args["expand_sections"] == False
        assert call_args["bathy_source"] == "gebco2025"
        assert call_args["verbose"] == True

    @patch("cruiseplan.api.data.pangaea")
    def test_pangaea_config_mapping(self, mock_pangaea):
        """Test parameter mapping for pangaea_with_config."""
        config = PangaeaConfig(lat_bounds=[-60.0, -40.0], limit=20, rate_limit=0.5)

        cruiseplan.pangaea_with_config("CTD", config)

        call_args = mock_pangaea.call_args[1]
        assert call_args["lat_bounds"] == [-60.0, -40.0]
        assert call_args["limit"] == 20
        assert call_args["rate_limit"] == 0.5


class TestNestedConfigInitialization:
    """Test that nested config objects are properly initialized."""

    def test_process_config_nested_init(self):
        """Test ProcessConfig creates nested configs automatically."""
        config = ProcessConfig()

        assert config.bathymetry is not None
        assert config.output is not None
        assert config.validation is not None
        assert config.visualization is not None

        # Check default values in nested configs
        assert config.bathymetry.source == "etopo2022"
        assert config.output.directory == "data"
        assert config.validation.run_validation == True
        assert config.visualization.include_ports == True

    def test_schedule_config_nested_init(self):
        """Test ScheduleConfig creates nested configs automatically."""
        config = ScheduleConfig()

        assert config.bathymetry is not None
        assert config.output is not None
        assert config.visualization is not None

        assert config.bathymetry.stride == 10
        assert config.output.format == "all"

    def test_map_config_nested_init(self):
        """Test MapConfig creates nested configs automatically."""
        config = MapConfig()

        assert config.bathymetry is not None
        assert config.output is not None
        assert config.visualization is not None

    def test_enrich_config_nested_init(self):
        """Test EnrichConfig creates nested configs automatically."""
        config = EnrichConfig()

        assert config.bathymetry is not None
        assert config.output is not None

    def test_validate_config_nested_init(self):
        """Test ValidateConfig creates nested configs automatically."""
        config = ValidateConfig()

        assert config.bathymetry is not None

    def test_pangaea_config_nested_init(self):
        """Test PangaeaConfig creates nested configs automatically."""
        config = PangaeaConfig()

        assert config.output is not None

    def test_stations_config_nested_init(self):
        """Test StationsConfig creates nested configs automatically."""
        config = StationsConfig()

        assert config.output is not None


class TestConfigDefaults:
    """Test that config objects provide sensible defaults."""

    def test_default_config_creation(self):
        """Test that all config functions work with None/default configs."""
        # Simple smoke test - functions should accept None and create defaults
        with patch("cruiseplan.api.data.bathymetry"):
            cruiseplan.bathymetry_with_config(None)  # Should not crash

        with patch("cruiseplan.api.process_cruise.enrich"):
            cruiseplan.enrich_with_config("test.yaml", None)  # Should not crash
