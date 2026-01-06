"""
Tests for input validation utility functions.

This module tests all validation functions in cruiseplan.utils.input_validation
to ensure proper parameter validation and error handling across CLI commands.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.utils.input_validation import (
    _apply_cli_defaults,
    _detect_pangaea_mode,
    _handle_deprecated_cli_params,
    _validate_bathymetry_params,
    _validate_choice_param,
    _validate_cli_config_file,
    _validate_config_file,
    _validate_coordinate_args,
    _validate_coordinate_bounds,
    _validate_directory_writable,
    _validate_file_extension,
    _validate_format_list,
    _validate_format_options,
    _validate_numeric_range,
    _validate_output_params,
    _validate_positive_int,
)


class TestConfigFileValidation:
    """Test config file validation functions."""

    def test_validate_config_file_existing_valid(self, tmp_path):
        """Test validation of existing valid config file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("cruise_name: Test\n")

        with patch("cruiseplan.utils.yaml_io.load_yaml") as mock_load:
            mock_load.return_value = {"cruise_name": "Test"}
            result = _validate_config_file(config_file)
            assert result == config_file.resolve()

    def test_validate_config_file_not_found(self, tmp_path):
        """Test validation of non-existent config file."""
        config_file = tmp_path / "missing.yaml"

        with pytest.raises(ValueError, match="Configuration file not found"):
            _validate_config_file(config_file)

    def test_validate_config_file_is_directory(self, tmp_path):
        """Test validation when path is a directory."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        with pytest.raises(ValueError, match="Path is not a file"):
            _validate_config_file(config_dir)

    def test_validate_config_file_empty(self, tmp_path):
        """Test validation of empty config file."""
        config_file = tmp_path / "empty.yaml"
        config_file.touch()

        with pytest.raises(ValueError, match="Configuration file is empty"):
            _validate_config_file(config_file)

    def test_validate_config_file_invalid_yaml(self, tmp_path):
        """Test validation of invalid YAML file."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with patch("cruiseplan.utils.yaml_io.load_yaml") as mock_load:
            mock_load.side_effect = Exception("Invalid YAML")
            with pytest.raises(ValueError, match="Invalid YAML configuration"):
                _validate_config_file(config_file)

    def test_validate_config_file_must_exist_false(self, tmp_path):
        """Test validation with must_exist=False."""
        config_file = tmp_path / "new.yaml"

        result = _validate_config_file(config_file, must_exist=False)
        assert result == config_file.resolve()


class TestDirectoryValidation:
    """Test directory validation functions."""

    def test_validate_directory_writable_existing(self, tmp_path):
        """Test validation of existing writable directory."""
        result = _validate_directory_writable(tmp_path)
        assert result == tmp_path.resolve()

    def test_validate_directory_writable_create_missing(self, tmp_path):
        """Test validation with directory creation."""
        new_dir = tmp_path / "new_dir"

        result = _validate_directory_writable(new_dir, create_if_missing=True)
        assert result == new_dir.resolve()
        assert new_dir.exists()

    def test_validate_directory_writable_no_create(self, tmp_path):
        """Test validation without directory creation."""
        missing_dir = tmp_path / "missing"

        with pytest.raises(ValueError, match="Output directory does not exist"):
            _validate_directory_writable(missing_dir, create_if_missing=False)

    def test_validate_directory_writable_is_file(self, tmp_path):
        """Test validation when path is a file."""
        file_path = tmp_path / "file.txt"
        file_path.touch()

        with pytest.raises(ValueError, match="Path is not a directory"):
            _validate_directory_writable(file_path, create_if_missing=False)

    @patch("pathlib.Path.touch")
    def test_validate_directory_writable_permission_error(self, mock_touch, tmp_path):
        """Test validation with write permission error."""
        mock_touch.side_effect = PermissionError("Permission denied")

        with pytest.raises(ValueError, match="Directory is not writable"):
            _validate_directory_writable(tmp_path)


class TestCoordinateValidation:
    """Test coordinate validation functions."""

    def test_validate_coordinate_bounds_valid(self):
        """Test validation of valid coordinate bounds."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [-10.0, 10.0]

        result = _validate_coordinate_bounds(lat_bounds, lon_bounds)
        assert result == (-10.0, 50.0, 10.0, 60.0)

    def test_validate_coordinate_bounds_invalid_lat_format(self):
        """Test validation with invalid latitude format."""
        lat_bounds = [50.0]  # Missing max lat
        lon_bounds = [-10.0, 10.0]

        with pytest.raises(
            ValueError, match="lat_bounds must be a list of exactly 2 values"
        ):
            _validate_coordinate_bounds(lat_bounds, lon_bounds)

    def test_validate_coordinate_bounds_invalid_lon_format(self):
        """Test validation with invalid longitude format."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [-10.0, 10.0, 20.0]  # Too many values

        with pytest.raises(
            ValueError, match="lon_bounds must be a list of exactly 2 values"
        ):
            _validate_coordinate_bounds(lat_bounds, lon_bounds)

    def test_validate_coordinate_bounds_lat_out_of_range(self):
        """Test validation with latitude out of range."""
        lat_bounds = [-100.0, 60.0]  # Invalid min lat
        lon_bounds = [-10.0, 10.0]

        with pytest.raises(ValueError, match="Invalid minimum latitude"):
            _validate_coordinate_bounds(lat_bounds, lon_bounds)

    def test_validate_coordinate_bounds_lon_out_of_range(self):
        """Test validation with longitude out of range."""
        lat_bounds = [50.0, 60.0]
        lon_bounds = [-200.0, 10.0]  # Invalid min lon

        with pytest.raises(ValueError, match="Invalid minimum longitude"):
            _validate_coordinate_bounds(lat_bounds, lon_bounds)

    def test_validate_coordinate_bounds_invalid_range(self):
        """Test validation with invalid coordinate range."""
        lat_bounds = [60.0, 50.0]  # Min > Max
        lon_bounds = [-10.0, 10.0]

        with pytest.raises(
            ValueError, match=r"Minimum latitude .* must be less than maximum"
        ):
            _validate_coordinate_bounds(lat_bounds, lon_bounds)


class TestFileExtensionValidation:
    """Test file extension validation functions."""

    def test_validate_file_extension_valid(self):
        """Test validation of valid file extension."""
        file_path = Path("config.yaml")
        allowed_exts = [".yaml", ".yml"]

        result = _validate_file_extension(file_path, allowed_exts)
        assert result is True

    def test_validate_file_extension_case_insensitive(self):
        """Test case-insensitive extension validation."""
        file_path = Path("config.YAML")
        allowed_exts = [".yaml", ".yml"]

        result = _validate_file_extension(file_path, allowed_exts)
        assert result is True

    def test_validate_file_extension_invalid(self):
        """Test validation of invalid file extension."""
        file_path = Path("config.txt")
        allowed_exts = [".yaml", ".yml"]

        result = _validate_file_extension(file_path, allowed_exts)
        assert result is False


class TestNumericRangeValidation:
    """Test numeric range validation functions."""

    def test_validate_numeric_range_valid(self):
        """Test validation of valid numeric value."""
        result = _validate_numeric_range(5.5, 0.0, 10.0, "stride")
        assert result == 5.5

    def test_validate_numeric_range_boundary_values(self):
        """Test validation of boundary values."""
        assert _validate_numeric_range(0.0, 0.0, 10.0, "test") == 0.0
        assert _validate_numeric_range(10.0, 0.0, 10.0, "test") == 10.0

    def test_validate_numeric_range_out_of_range(self):
        """Test validation with out-of-range value."""
        with pytest.raises(ValueError, match="test must be between"):
            _validate_numeric_range(15.0, 0.0, 10.0, "test")

    def test_validate_numeric_range_invalid_type(self):
        """Test validation with invalid type."""
        with pytest.raises(ValueError, match="test must be a number"):
            _validate_numeric_range("not_a_number", 0.0, 10.0, "test")


class TestFormatValidation:
    """Test format validation functions."""

    def test_validate_format_list_valid_single(self):
        """Test validation of single valid format."""
        formats = ["html"]
        valid_formats = ["html", "csv", "netcdf"]

        result = _validate_format_list(formats, valid_formats)
        assert result == ["html"]

    def test_validate_format_list_valid_multiple(self):
        """Test validation of multiple valid formats."""
        formats = ["html", "csv"]
        valid_formats = ["html", "csv", "netcdf"]

        result = _validate_format_list(formats, valid_formats)
        assert result == ["html", "csv"]

    def test_validate_format_list_remove_duplicates(self):
        """Test removal of duplicate formats."""
        formats = ["html", "csv", "html"]
        valid_formats = ["html", "csv", "netcdf"]

        result = _validate_format_list(formats, valid_formats)
        assert result == ["html", "csv"]

    def test_validate_format_list_empty(self):
        """Test validation with empty format list."""
        formats = []
        valid_formats = ["html", "csv", "netcdf"]

        with pytest.raises(ValueError, match="At least one format must be specified"):
            _validate_format_list(formats, valid_formats)

    def test_validate_format_list_invalid(self):
        """Test validation with invalid format."""
        formats = ["html", "invalid"]
        valid_formats = ["html", "csv", "netcdf"]

        with pytest.raises(ValueError, match="Invalid formats"):
            _validate_format_list(formats, valid_formats)

    def test_validate_format_options_all(self):
        """Test validation of 'all' format option."""
        valid_formats = ["html", "csv", "netcdf"]

        result = _validate_format_options("all", valid_formats)
        assert result == valid_formats

    def test_validate_format_options_comma_separated(self):
        """Test validation of comma-separated formats."""
        result = _validate_format_options("html,csv", ["html", "csv", "netcdf"])
        assert result == ["html", "csv"]

    def test_validate_format_options_single(self):
        """Test validation of single format."""
        result = _validate_format_options("html", ["html", "csv", "netcdf"])
        assert result == ["html"]

    def test_validate_format_options_invalid_single(self):
        """Test validation of invalid single format."""
        with pytest.raises(ValueError, match="Invalid format"):
            _validate_format_options("invalid", ["html", "csv", "netcdf"])

    def test_validate_format_options_invalid_in_list(self):
        """Test validation with invalid format in list."""
        with pytest.raises(ValueError, match="Invalid formats"):
            _validate_format_options("html,invalid", ["html", "csv", "netcdf"])


class TestPangaeaModeDetection:
    """Test PANGAEA mode detection functions."""

    def test_detect_pangaea_mode_file_existing(self, tmp_path):
        """Test detection of file mode with existing file."""
        doi_file = tmp_path / "dois.txt"
        doi_file.write_text("doi1\\ndoi2\\n")

        args = Namespace(query_or_file=str(doi_file))

        mode, params = _detect_pangaea_mode(args)
        assert mode == "file"
        assert params["query"] == str(doi_file)

    def test_detect_pangaea_mode_search_valid(self):
        """Test detection of search mode with valid coordinates."""
        args = Namespace(
            query_or_file="CTD temperature", lat=[50.0, 60.0], lon=[-10.0, 10.0]
        )

        mode, params = _detect_pangaea_mode(args)
        assert mode == "search"
        assert params["query"] == "CTD temperature"

    def test_detect_pangaea_mode_search_missing_lat(self):
        """Test search mode with missing latitude."""
        args = Namespace(query_or_file="CTD temperature", lon=[-10.0, 10.0])

        with pytest.raises(
            ValueError, match="Search mode requires both --lat and --lon bounds"
        ):
            _detect_pangaea_mode(args)

    def test_detect_pangaea_mode_search_invalid_coords(self):
        """Test search mode with invalid coordinates."""
        args = Namespace(
            query_or_file="CTD temperature",
            lat=[100.0, 60.0],  # Invalid lat
            lon=[-10.0, 10.0],
        )

        with pytest.raises(ValueError, match="Invalid coordinate bounds"):
            _detect_pangaea_mode(args)


class TestCLIParameterValidation:
    """Test CLI-specific parameter validation functions."""

    def test_validate_bathymetry_params_defaults(self):
        """Test bathymetry parameter validation with defaults."""
        args = Namespace()

        result = _validate_bathymetry_params(args)
        assert result == {
            "bathy_source": "etopo2022",
            "bathy_dir": "data",
            "bathy_stride": 10,
        }

    def test_validate_bathymetry_params_custom(self):
        """Test bathymetry parameter validation with custom values."""
        custom_path = Path("/custom/path")
        args = Namespace(
            bathy_source="gebco2025", bathy_dir=custom_path, bathy_stride=5
        )

        result = _validate_bathymetry_params(args)
        expected = {
            "bathy_source": "gebco2025",
            "bathy_dir": str(
                custom_path
            ),  # Convert to string for cross-platform compatibility
            "bathy_stride": 5,
        }
        assert result == expected

    def test_validate_bathymetry_params_invalid_source(self):
        """Test bathymetry parameter validation with invalid source."""
        args = Namespace(bathy_source="invalid")

        with pytest.raises(ValueError, match="Invalid bathymetry source"):
            _validate_bathymetry_params(args)

    def test_validate_bathymetry_params_invalid_stride(self):
        """Test bathymetry parameter validation with invalid stride."""
        args = Namespace(bathy_stride=0)

        with pytest.raises(
            ValueError, match="Bathymetry stride must be a positive integer"
        ):
            _validate_bathymetry_params(args)

    def test_validate_output_params_custom(self, tmp_path):
        """Test output parameter validation with custom values."""
        args = Namespace(output="myfile", output_dir=tmp_path)

        result = _validate_output_params(args, "default", "_test", ".yaml")
        assert result == tmp_path / "myfile_test.yaml"

    def test_validate_output_params_defaults(self, tmp_path):
        """Test output parameter validation with defaults."""
        args = Namespace(output_dir=tmp_path)

        result = _validate_output_params(args, "My Cruise", "_enriched", ".yaml")
        assert result == tmp_path / "My_Cruise_enriched.yaml"

    def test_validate_output_params_empty_basename(self, tmp_path):
        """Test output parameter validation with empty basename."""
        args = Namespace(output="", output_dir=tmp_path)

        with pytest.raises(ValueError, match="Output filename cannot be empty"):
            _validate_output_params(args, "", "_test", ".yaml")

    def test_validate_cli_config_file_valid(self, tmp_path):
        """Test CLI config file validation with valid file."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text("cruise_name: Test\\n")

        args = Namespace(config_file=config_file)

        with patch("cruiseplan.utils.yaml_io.load_yaml"):
            result = _validate_cli_config_file(args)
            assert result == config_file.resolve()

    def test_validate_cli_config_file_missing(self):
        """Test CLI config file validation with missing file."""
        args = Namespace()

        with pytest.raises(ValueError, match="Configuration file is required"):
            _validate_cli_config_file(args)

    def test_validate_coordinate_args_valid(self):
        """Test coordinate argument validation with valid values."""
        args = Namespace(lat=[50.0, 60.0], lon=[-10.0, 10.0])

        result = _validate_coordinate_args(args)
        assert result == (-10.0, 50.0, 10.0, 60.0)

    def test_validate_coordinate_args_missing_lat(self):
        """Test coordinate argument validation with missing latitude."""
        args = Namespace(lon=[-10.0, 10.0])

        with pytest.raises(ValueError, match=r"Latitude bounds .* are required"):
            _validate_coordinate_args(args)

    def test_validate_coordinate_args_missing_lon(self):
        """Test coordinate argument validation with missing longitude."""
        args = Namespace(lat=[50.0, 60.0])

        with pytest.raises(ValueError, match=r"Longitude bounds .* are required"):
            _validate_coordinate_args(args)


class TestDeprecatedParameterHandling:
    """Test deprecated parameter handling functions."""

    def test_handle_deprecated_cli_params_migration(self):
        """Test deprecated parameter migration."""
        args = Namespace(output_file="test.yaml")
        param_map = {"output_file": "output"}

        with patch("cruiseplan.utils.input_validation.logger") as mock_logger:
            _handle_deprecated_cli_params(args, param_map)

            mock_logger.warning.assert_called_once()
            assert hasattr(args, "output")
            assert args.output == "test.yaml"

    def test_handle_deprecated_cli_params_no_override(self):
        """Test deprecated parameter handling without override."""
        args = Namespace(output_file="old.yaml", output="new.yaml")
        param_map = {"output_file": "output"}

        with patch("cruiseplan.utils.input_validation.logger"):
            _handle_deprecated_cli_params(args, param_map)

            # Should not override existing value
            assert args.output == "new.yaml"

    def test_handle_deprecated_cli_params_no_deprecated(self):
        """Test deprecated parameter handling with no deprecated params."""
        args = Namespace(output="test.yaml")
        param_map = {"output_file": "output"}

        with patch("cruiseplan.utils.input_validation.logger") as mock_logger:
            _handle_deprecated_cli_params(args, param_map)

            mock_logger.warning.assert_not_called()

    def test_apply_cli_defaults(self):
        """Test application of CLI defaults."""
        args = Namespace()

        _apply_cli_defaults(args)

        assert args.bathy_dir == Path("data")
        assert args.output_dir == Path("data")

    def test_apply_cli_defaults_no_override(self):
        """Test CLI defaults don't override existing values."""
        args = Namespace(bathy_dir=Path("/custom"), output_dir=Path("/output"))

        _apply_cli_defaults(args)

        assert args.bathy_dir == Path("/custom")
        assert args.output_dir == Path("/output")


class TestChoiceParameterValidation:
    """Test choice parameter validation functions."""

    def test_validate_choice_param_valid(self):
        """Test validation of valid choice parameter."""
        result = _validate_choice_param(
            "gebco2025", "bathy_source", ["etopo2022", "gebco2025"]
        )
        assert result == "gebco2025"

    def test_validate_choice_param_invalid(self):
        """Test validation of invalid choice parameter."""
        with pytest.raises(ValueError, match="Invalid bathy_source"):
            _validate_choice_param(
                "invalid", "bathy_source", ["etopo2022", "gebco2025"]
            )

    def test_validate_positive_int_valid(self):
        """Test validation of valid positive integer."""
        result = _validate_positive_int(5, "stride")
        assert result == 5

    def test_validate_positive_int_zero(self):
        """Test validation of zero value."""
        with pytest.raises(ValueError, match="stride must be a positive integer"):
            _validate_positive_int(0, "stride")

    def test_validate_positive_int_negative(self):
        """Test validation of negative value."""
        with pytest.raises(ValueError, match="stride must be a positive integer"):
            _validate_positive_int(-1, "stride")

    def test_validate_positive_int_invalid_type(self):
        """Test validation of invalid type."""
        with pytest.raises(ValueError, match="stride must be a positive integer"):
            _validate_positive_int("5", "stride")
