"""
Tests for CLI utilities module.
"""

import argparse
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from cruiseplan.cli.cli_utils import (
    CLIError,
    _collect_generated_files,
    _format_duration_seconds,
    _format_error_message,
    _format_progress_header,
    _format_success_message,
    _handle_deprecated_params,
    _parse_format_options,
    _setup_cli_logging,
    _setup_output_strategy,
    _validate_bathymetry_params,
    capture_and_format_warnings,
    confirm_operation,
    count_individual_warnings,
    determine_output_path,
    display_user_warnings,
    format_coordinate_bounds,
    generate_output_filename,
    load_cruise_with_pretty_warnings,
    load_yaml_config,
    read_doi_list,
    save_yaml_config,
    setup_logging,
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


class TestLogging:
    """Test logging setup functions."""

    def test_setup_logging_default(self):
        """Test default logging setup."""
        with patch("logging.basicConfig") as mock_basic:
            setup_logging()
            mock_basic.assert_called_once_with(
                level=logging.INFO,
                format="%(message)s",
                stream=pytest.importorskip("sys").stdout,
            )

    def test_setup_logging_verbose(self):
        """Test verbose logging setup."""
        with patch("logging.basicConfig") as mock_basic:
            setup_logging(verbose=True)
            mock_basic.assert_called_once_with(
                level=logging.DEBUG,
                format="%(message)s",
                stream=pytest.importorskip("sys").stdout,
            )

    def test_setup_logging_quiet(self):
        """Test quiet logging setup."""
        with patch("logging.basicConfig") as mock_basic:
            setup_logging(quiet=True)
            mock_basic.assert_called_once_with(
                level=logging.WARNING,
                format="%(message)s",
                stream=pytest.importorskip("sys").stdout,
            )

    def test_setup_cli_logging_verbose(self):
        """Test enhanced CLI logging with verbose mode."""
        with (
            patch("cruiseplan.cli.cli_utils.setup_logging") as mock_setup,
            patch("logging.getLogger") as mock_get_logger,
        ):

            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            _setup_cli_logging(verbose=True)

            mock_setup.assert_called_once_with(True, False)
            mock_get_logger.assert_called_with("cruiseplan")
            mock_logger.setLevel.assert_called_with(logging.DEBUG)

    def test_setup_cli_logging_default(self):
        """Test enhanced CLI logging default mode."""
        with patch("cruiseplan.cli.cli_utils.setup_logging") as mock_setup:
            _setup_cli_logging()
            mock_setup.assert_called_once_with(False, False)


class TestUserInteraction:
    """Test user interaction functions."""

    def test_confirm_operation_default_yes(self):
        """Test confirmation with default yes."""
        with patch("builtins.input", return_value=""):
            result = confirm_operation("Continue?", default=True)
            assert result is True

    def test_confirm_operation_default_no(self):
        """Test confirmation with default no."""
        with patch("builtins.input", return_value=""):
            result = confirm_operation("Continue?", default=False)
            assert result is False

    def test_confirm_operation_explicit_yes(self):
        """Test explicit yes response."""
        with patch("builtins.input", return_value="y"):
            result = confirm_operation("Continue?")
            assert result is True

    def test_confirm_operation_explicit_no(self):
        """Test explicit no response."""
        with patch("builtins.input", return_value="n"):
            result = confirm_operation("Continue?")
            assert result is False

    def test_confirm_operation_keyboard_interrupt(self):
        """Test keyboard interrupt handling."""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = confirm_operation("Continue?")
            assert result is False


class TestWarningUtilities:
    """Test warning handling utilities."""

    def test_count_individual_warnings(self):
        """Test counting individual warnings."""
        warnings = ["Group 1:\n- Warning 1\n- Warning 2", "Group 2:\n- Warning 3"]
        count = count_individual_warnings(warnings)
        assert count == 3

    def test_count_individual_warnings_empty(self):
        """Test counting warnings with empty list."""
        count = count_individual_warnings([])
        assert count == 0

    def test_display_user_warnings(self):
        """Test warning display."""
        warnings = ["Warning group 1\n- Item 1", "Warning group 2\n- Item 2"]

        with patch("cruiseplan.cli.cli_utils.logger") as mock_logger:
            display_user_warnings(warnings, "Test Warnings")

            # Should call warning logger
            assert mock_logger.warning.call_count > 0
            # First call should include title
            mock_logger.warning.assert_any_call("⚠️ Test Warnings:")

    def test_display_user_warnings_empty(self):
        """Test warning display with empty list."""
        with patch("cruiseplan.cli.cli_utils.logger") as mock_logger:
            display_user_warnings([])

            # Should not call logger for empty warnings
            mock_logger.warning.assert_not_called()

    def test_capture_and_format_warnings(self):
        """Test warning capture context manager."""
        import warnings

        with capture_and_format_warnings() as captured:
            warnings.warn("Test warning message")

        assert len(captured) == 1
        assert "Test warning message" in captured[0]

    def test_load_cruise_with_pretty_warnings_success(self, tmp_path):
        """Test loading cruise with warning capture."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("cruise_name: Test")

        mock_cruise = MagicMock()

        with patch(
            "cruiseplan.core.cruise.Cruise", return_value=mock_cruise
        ) as mock_cruise_class:
            result = load_cruise_with_pretty_warnings(config_file)

            mock_cruise_class.assert_called_once_with(config_file)
            assert result == mock_cruise

    def test_load_cruise_with_pretty_warnings_error(self, tmp_path):
        """Test loading cruise with error handling."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("invalid: yaml: [")

        with patch(
            "cruiseplan.core.cruise.Cruise", side_effect=Exception("Load error")
        ):
            with pytest.raises(CLIError, match="Failed to load cruise configuration"):
                load_cruise_with_pretty_warnings(config_file)


class TestOutputUtilities:
    """Test output path and filename utilities."""

    def test_determine_output_path_with_output_arg(self):
        """Test output path determination with --output argument."""
        args = argparse.Namespace(output="myfile", output_dir=Path("results"))

        result = determine_output_path(args, "default", "_suffix", ".ext")
        expected = Path("results/myfile_suffix.ext")

        assert result == expected

    def test_determine_output_path_default_basename(self):
        """Test output path with default basename."""
        args = argparse.Namespace(output=None, output_dir=Path("data"))

        result = determine_output_path(args, "My Cruise", "_schedule", ".csv")
        expected = Path("data/My_Cruise_schedule.csv")

        assert result == expected

    def test_determine_output_path_no_output_dir(self):
        """Test output path without output_dir set."""
        args = argparse.Namespace(output="test")
        # Remove output_dir attribute entirely
        if hasattr(args, "output_dir"):
            delattr(args, "output_dir")

        result = determine_output_path(args, "default", "", ".yaml")
        expected = Path("data/test.yaml")

        assert result == expected


class TestFormatUtilities:
    """Test formatting utility functions."""

    def test_parse_format_options_all(self):
        """Test parsing 'all' format option."""
        valid_formats = ["html", "csv", "netcdf"]
        result = _parse_format_options("all", valid_formats)
        assert result == valid_formats

    def test_parse_format_options_comma_separated(self):
        """Test parsing comma-separated formats."""
        valid_formats = ["html", "csv", "netcdf"]
        result = _parse_format_options("html,csv", valid_formats)
        assert result == ["html", "csv"]

    def test_parse_format_options_single(self):
        """Test parsing single format."""
        valid_formats = ["html", "csv", "netcdf"]
        result = _parse_format_options("html", valid_formats)
        assert result == ["html"]

    def test_parse_format_options_invalid(self):
        """Test parsing invalid format."""
        valid_formats = ["html", "csv", "netcdf"]

        with pytest.raises(CLIError, match="Invalid format"):
            _parse_format_options("invalid", valid_formats)

    def test_parse_format_options_invalid_in_list(self):
        """Test parsing invalid format in comma-separated list."""
        valid_formats = ["html", "csv", "netcdf"]

        with pytest.raises(CLIError, match="Invalid formats"):
            _parse_format_options("html,invalid", valid_formats)

    def test_format_duration_seconds(self):
        """Test duration formatting."""
        assert _format_duration_seconds(30.5) == "30.5s"
        assert _format_duration_seconds(120.0) == "2.0m"
        assert _format_duration_seconds(3660.0) == "1.0h"

    def test_format_success_message(self, tmp_path):
        """Test success message formatting."""
        test_files = [tmp_path / "file1.txt", tmp_path / "file2.txt"]

        with patch("cruiseplan.cli.cli_utils.logger") as mock_logger:
            _format_success_message("test operation", test_files)

            # Should log multiple lines including operation name
            assert mock_logger.info.call_count > 0
            # Check that success message is included
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("test operation Complete" in call for call in calls)
            assert any("✅ test operation successful!" in call for call in calls)

    def test_format_success_message_with_duration(self):
        """Test success message with duration."""
        with (
            patch("cruiseplan.cli.cli_utils.logger") as mock_logger,
            patch(
                "cruiseplan.cli.cli_utils._format_duration_seconds", return_value="1.5m"
            ) as mock_duration,
        ):

            _format_success_message("test", [], duration=90.0)

            mock_duration.assert_called_once_with(90.0)
            # Should include duration in output
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Duration: 1.5m" in call for call in calls)

    def test_format_error_message(self):
        """Test error message formatting."""
        error = Exception("Test error")
        suggestions = ["Try again", "Check input"]

        with patch("cruiseplan.cli.cli_utils.logger") as mock_logger:
            _format_error_message("test operation", error, suggestions)

            # Should log error details
            assert mock_logger.error.call_count > 0
            calls = [call[0][0] for call in mock_logger.error.call_args_list]
            assert any("test operation Failed" in call for call in calls)
            assert any("Test error" in call for call in calls)
            assert any("Try again" in call for call in calls)

    def test_format_progress_header(self, tmp_path):
        """Test progress header formatting."""
        config_file = tmp_path / "test.yaml"

        with patch("cruiseplan.cli.cli_utils.logger") as mock_logger:
            _format_progress_header(
                "Test Operation", config_file, format="html", leg="leg1"
            )

            # Should log header information
            assert mock_logger.info.call_count > 0
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("Test Operation" in call for call in calls)
            assert any(str(config_file) in call for call in calls)


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

    def test_validate_bathymetry_params_default(self):
        """Test bathymetry parameter validation with defaults."""
        args = argparse.Namespace()

        result = _validate_bathymetry_params(args)

        assert result["bathy_source"] == "etopo2022"
        assert result["bathy_dir"] == "data"
        assert result["bathy_stride"] == 10

    def test_validate_bathymetry_params_custom(self):
        """Test bathymetry parameter validation with custom values."""
        args = argparse.Namespace(
            bathy_source="gebco2025", bathy_dir="custom_dir", bathy_stride=5
        )

        result = _validate_bathymetry_params(args)

        assert result["bathy_source"] == "gebco2025"
        assert result["bathy_dir"] == "custom_dir"
        assert result["bathy_stride"] == 5

    def test_validate_bathymetry_params_invalid_source(self):
        """Test bathymetry parameter validation with invalid source."""
        args = argparse.Namespace(bathy_source="invalid")

        with pytest.raises(CLIError, match="Invalid bathymetry source"):
            _validate_bathymetry_params(args)

    def test_validate_bathymetry_params_invalid_stride(self):
        """Test bathymetry parameter validation with invalid stride."""
        args = argparse.Namespace(bathy_stride=0)

        with pytest.raises(
            CLIError, match="Bathymetry stride must be a positive integer"
        ):
            _validate_bathymetry_params(args)

    def test_setup_output_strategy(self, tmp_path):
        """Test output strategy setup."""
        config_file = tmp_path / "test_config.yaml"
        args = argparse.Namespace(output_dir=tmp_path / "output", output="custom")

        output_dir, base_name = _setup_output_strategy(config_file, args)

        assert output_dir == (tmp_path / "output").resolve()
        assert base_name == "custom"
        assert output_dir.exists()  # Should create directory

    def test_setup_output_strategy_defaults(self, tmp_path):
        """Test output strategy with default values."""
        config_file = tmp_path / "My Config.yaml"
        args = argparse.Namespace()

        output_dir, base_name = _setup_output_strategy(config_file, args)

        assert output_dir == Path("data").resolve()
        assert base_name == "My_Config"  # Should replace spaces


class TestFileCollectionUtilities:
    """Test file collection and handling utilities."""

    def test_collect_generated_files_path(self):
        """Test collecting single Path object."""
        test_path = Path("test.txt")
        result = _collect_generated_files(test_path)
        assert result == [test_path]

    def test_collect_generated_files_list(self):
        """Test collecting list of paths."""
        test_paths = [Path("file1.txt"), Path("file2.txt")]
        result = _collect_generated_files(test_paths)
        assert result == test_paths

    def test_collect_generated_files_tuple(self):
        """Test collecting from tuple response."""
        test_data = "some_data"
        test_files = [Path("output.txt"), None, Path("other.txt")]
        test_tuple = (test_data, test_files)

        result = _collect_generated_files(test_tuple)
        expected = [Path("output.txt"), Path("other.txt")]  # None filtered out
        assert result == expected

    def test_collect_generated_files_empty(self):
        """Test collecting from empty or invalid input."""
        result = _collect_generated_files("invalid")
        assert result == []

    def test_collect_generated_files_mixed_list(self):
        """Test collecting from mixed list with non-paths."""
        test_list = [Path("file.txt"), "string", 123, Path("other.txt")]
        result = _collect_generated_files(test_list)
        expected = [Path("file.txt"), Path("other.txt")]
        assert result == expected
