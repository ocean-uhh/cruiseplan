"""
Tests for CLI utilities module.
"""

from pathlib import Path

import pytest
import yaml

from cruiseplan.cli.utils import (
    CLIError,
    format_coordinate_bounds,
    generate_output_filename,
    load_yaml_config,
    read_doi_list,
    save_yaml_config,
    validate_input_file,
    validate_output_path,
)


class TestFileValidation:
    """Test file path validation functions."""

    def test_validate_input_file_exists(self, tmp_path):
        """Test validation of existing input file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        result = validate_input_file(test_file)
        assert result == test_file.resolve()

    def test_validate_input_file_not_exists(self, tmp_path):
        """Test validation fails for non-existent file."""
        test_file = tmp_path / "nonexistent.txt"

        with pytest.raises(CLIError, match="Input file not found"):
            validate_input_file(test_file)

    def test_validate_input_file_directory(self, tmp_path):
        """Test validation fails for directory."""
        with pytest.raises(CLIError, match="Path is not a file"):
            validate_input_file(tmp_path)

    def test_validate_input_file_empty(self, tmp_path):
        """Test validation fails for empty file."""
        test_file = tmp_path / "empty.txt"
        test_file.touch()

        with pytest.raises(CLIError, match="Input file is empty"):
            validate_input_file(test_file)


class TestOutputPath:
    """Test output path validation."""

    def test_validate_output_path_with_file(self, tmp_path):
        """Test output path with specific file."""
        output_file = tmp_path / "output.txt"
        result = validate_output_path(output_file=output_file)

        assert result == output_file.resolve()
        assert output_file.parent.exists()

    def test_validate_output_path_with_dir(self, tmp_path):
        """Test output path with directory only."""
        result = validate_output_path(output_dir=tmp_path)
        assert result == tmp_path.resolve()

    def test_validate_output_path_with_filename(self, tmp_path):
        """Test output path with directory and default filename."""
        result = validate_output_path(output_dir=tmp_path, default_filename="test.yaml")
        assert result == tmp_path / "test.yaml"


class TestYamlOperations:
    """Test YAML loading and saving."""

    def test_load_yaml_config(self, tmp_path):
        """Test loading valid YAML config."""
        config = {"cruise_name": "Test Cruise", "stations": []}
        yaml_file = tmp_path / "config.yaml"

        with open(yaml_file, "w") as f:
            yaml.dump(config, f)

        result = load_yaml_config(yaml_file)
        assert result == config

    def test_load_yaml_config_invalid(self, tmp_path):
        """Test loading invalid YAML."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: [")

        with pytest.raises(CLIError, match="Invalid YAML syntax"):
            load_yaml_config(yaml_file)

    def test_load_yaml_config_empty(self, tmp_path):
        """Test loading empty YAML."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        with pytest.raises(CLIError, match="YAML file is empty"):
            load_yaml_config(yaml_file)

    def test_save_yaml_config(self, tmp_path):
        """Test saving YAML config."""
        config = {"cruise_name": "Test Cruise"}
        yaml_file = tmp_path / "output.yaml"

        save_yaml_config(config, yaml_file, backup=False)

        assert yaml_file.exists()
        loaded = load_yaml_config(yaml_file)
        assert loaded == config

    def test_save_yaml_config_with_backup(self, tmp_path):
        """Test saving YAML with backup."""
        config1 = {"cruise_name": "Original"}
        config2 = {"cruise_name": "Updated"}
        yaml_file = tmp_path / "config.yaml"

        # Save original
        save_yaml_config(config1, yaml_file, backup=False)

        # Save updated with backup
        save_yaml_config(config2, yaml_file, backup=True)

        # New incremental backup naming scheme: config.yaml-1
        backup_file = yaml_file.with_name(f"{yaml_file.name}-1")
        assert backup_file.exists()

        original = load_yaml_config(backup_file)
        updated = load_yaml_config(yaml_file)

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

        with pytest.raises(CLIError, match="No valid DOIs found"):
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
