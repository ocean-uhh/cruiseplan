"""
Tests for CLI utilities module.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cruiseplan.cli.cli_utils import (
    CLIError,
    _handle_deprecated_params,
    format_coordinate_bounds,
    generate_output_filename,
)
from cruiseplan.data.pangaea import read_doi_list
from cruiseplan.utils.io import _setup_output_paths
from cruiseplan.utils.yaml_io import load_yaml, save_yaml


class TestYamlOperations:
    """Test YAML loading and saving."""

    def test_load_yaml(self, tmp_path):
        """Test loading valid YAML config."""
        config = {"cruise_name": "Test Cruise", "stations": []}
        yaml_file = tmp_path / "config.yaml"

        with open(yaml_file, "w") as f:
            yaml.dump(config, f)

        result = load_yaml(yaml_file)
        assert result == config

    def test_load_yaml_invalid(self, tmp_path):
        """Test loading invalid YAML."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        from cruiseplan.utils.yaml_io import YAMLIOError

        with pytest.raises(YAMLIOError, match="Invalid YAML syntax"):
            load_yaml(yaml_file)

    def test_load_yaml_empty(self, tmp_path):
        """Test loading empty YAML."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        from cruiseplan.utils.yaml_io import YAMLIOError

        with pytest.raises(YAMLIOError, match="YAML file is empty"):
            load_yaml(yaml_file)

    def test_save_yaml(self, tmp_path):
        """Test saving YAML config."""
        config = {"cruise_name": "Test Cruise"}
        yaml_file = tmp_path / "output.yaml"

        save_yaml(config, yaml_file, backup=False)

        assert yaml_file.exists()
        loaded = load_yaml(yaml_file)
        assert loaded == config

    def test_save_yaml_with_backup(self, tmp_path):
        """Test saving YAML with backup."""
        config1 = {"cruise_name": "Original"}
        config2 = {"cruise_name": "Updated"}
        yaml_file = tmp_path / "config.yaml"

        # Save original
        save_yaml(config1, yaml_file, backup=False)

        # Save updated with backup
        save_yaml(config2, yaml_file, backup=True)

        # New incremental backup naming scheme: config.yaml-1
        backup_file = yaml_file.with_name(f"{yaml_file.name}-1")
        assert backup_file.exists()

        original = load_yaml(backup_file)
        updated = load_yaml(yaml_file)

        assert original == config1
        assert updated == config2


class TestUtilityFunctions:
    """Test utility functions."""

    def test_generate_output_filename(self):
        """Test filename generation."""
        input_path = Path("test.yaml")
        result = generate_output_filename(input_path, "_processed")
        assert result == "test_processed.yaml"

    def test_generate_output_filename_with_extension(self):
        """Test filename generation with different extension."""
        input_path = Path("test.yaml")
        result = generate_output_filename(input_path, "_processed", ".json")
        assert result == "test_processed.json"

    def test_read_doi_list(self, tmp_path):
        """Test reading DOI list from file."""
        doi_file = tmp_path / "dois.txt"
        doi_content = """
        # This is a comment
        10.1594/PANGAEA.12345
        doi:10.1594/PANGAEA.67890
        https://doi.org/10.1594/PANGAEA.11111

        10.1594/PANGAEA.22222
        """
        doi_file.write_text(doi_content)

        result = read_doi_list(doi_file)
        expected = [
            "10.1594/PANGAEA.12345",
            "doi:10.1594/PANGAEA.67890",
            "https://doi.org/10.1594/PANGAEA.11111",
            "10.1594/PANGAEA.22222",
        ]
        assert result == expected

    def test_read_doi_list_empty(self, tmp_path):
        """Test reading empty DOI list."""
        doi_file = tmp_path / "empty_dois.txt"
        doi_file.write_text("# Only comments\n\n")

        with pytest.raises(ValueError, match="No valid DOIs found"):
            read_doi_list(doi_file)

    def test_format_coordinate_bounds(self):
        """Test coordinate bounds formatting."""
        result = format_coordinate_bounds((50.0, 60.0), (-10.0, 0.0))
        expected = "Lat: 50.00° to 60.00°, Lon: -10.00° to 0.00°"
        assert result == expected


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_cli_error_inheritance(self):
        """Test CLIError is proper exception."""
        error = CLIError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"


class TestParameterUtilities:
    """Test parameter handling utilities."""

    def test_handle_deprecated_params(self):
        """Test deprecated parameter handling."""
        args = argparse.Namespace()
        args.old_param = "value"
        args.new_param = None

        param_map = {"old_param": "new_param"}

        with patch("cruiseplan.cli.cli_utils.logger") as mock_logger:
            _handle_deprecated_params(args, param_map)

            # Should migrate value
            assert args.new_param == "value"
            # Should log warning
            mock_logger.warning.assert_called_once()
            assert "deprecated" in mock_logger.warning.call_args[0][0].lower()

    def test_handle_deprecated_params_no_migration_if_new_set(self):
        """Test that deprecated params don't override existing values."""
        args = argparse.Namespace()
        args.old_param = "old_value"
        args.new_param = "new_value"

        param_map = {"old_param": "new_param"}

        with patch("cruiseplan.cli.cli_utils.logger"):
            _handle_deprecated_params(args, param_map)

            # Should not override existing value
            assert args.new_param == "new_value"

    def test_setup_output_strategy(self, tmp_path):
        """Test output strategy setup."""
        config_file = tmp_path / "test_config.yaml"

        output_dir, base_name = _setup_output_paths(
            config_file=config_file,
            output_dir=str(tmp_path / "output"),
            output_base="custom",
        )

        assert output_dir == (tmp_path / "output").resolve()
        assert base_name == "custom"
        assert output_dir.exists()  # Should create directory

    def test_setup_output_strategy_defaults(self, tmp_path):
        """Test output strategy with default values."""
        config_file = tmp_path / "My Config.yaml"

        output_dir, base_name = _setup_output_paths(config_file=config_file)

        assert output_dir == Path("data").resolve()
        assert base_name == "My_Config"  # Should replace spaces
