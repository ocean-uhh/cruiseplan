"""
Tests for CLI utilities that are still in use.
"""

from pathlib import Path

from cruiseplan.api.stations_api import generate_output_filename
from cruiseplan.schema.yaml_io import load_yaml, save_yaml


class TestYamlOperations:
    """Test YAML loading and saving."""

    def test_load_yaml(self, tmp_path):
        """Test loading valid YAML config."""
        import yaml

        config = {"cruise_name": "Test Cruise", "waypoints": []}
        yaml_file = tmp_path / "config.yaml"

        with open(yaml_file, "w") as f:
            yaml.dump(config, f)

        result = load_yaml(yaml_file)
        assert result == config

    def test_save_yaml(self, tmp_path):
        """Test saving YAML config."""
        config = {"cruise_name": "Test Cruise"}
        yaml_file = tmp_path / "output.yaml"

        save_yaml(config, yaml_file, backup=False)

        assert yaml_file.exists()
        loaded = load_yaml(yaml_file)
        assert loaded == config


class TestUtilityFunctions:
    """Test utility functions."""

    def test_generate_output_filename(self):
        """Test filename generation."""
        input_path = Path("test.yaml")
        result = generate_output_filename(input_path, "_processed")
        assert result == "test_processed.yaml"

    def test_generate_output_filename_with_extension(self):
        """Test filename generation with custom extension."""
        input_path = Path("test.yaml")
        result = generate_output_filename(input_path, "_processed", ".json")
        assert result == "test_processed.json"
