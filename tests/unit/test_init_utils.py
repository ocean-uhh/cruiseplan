"""Unit tests for init_utils module."""

import logging
from unittest.mock import patch

from cruiseplan.init_utils import (
    _handle_error_with_logging,
    _parse_map_formats,
    _parse_schedule_formats,
    _setup_verbose_logging,
    _validate_lat_lon_bounds,
)


class TestSetupVerboseLogging:
    """Test the _setup_verbose_logging function."""

    @patch("logging.basicConfig")
    def test_verbose_true(self, mock_config):
        """Test that verbose=True sets DEBUG level."""
        _setup_verbose_logging(True)
        mock_config.assert_called_once_with(level=logging.DEBUG)

    @patch("logging.basicConfig")
    def test_verbose_false(self, mock_config):
        """Test that verbose=False doesn't configure logging."""
        _setup_verbose_logging(False)
        mock_config.assert_not_called()


class TestHandleErrorWithLogging:
    """Test the _handle_error_with_logging function."""

    @patch("cruiseplan.init_utils.logger")
    @patch("traceback.print_exc")
    def test_with_verbose(self, mock_traceback, mock_logger):
        """Test error handling with verbose mode."""
        error = ValueError("Test error")
        _handle_error_with_logging(error, "Operation failed", verbose=True)

        mock_logger.error.assert_called_once_with("❌ Operation failed: Test error")
        mock_traceback.assert_called_once()

    @patch("cruiseplan.init_utils.logger")
    @patch("traceback.print_exc")
    def test_without_verbose(self, mock_traceback, mock_logger):
        """Test error handling without verbose mode."""
        error = RuntimeError("Another error")
        _handle_error_with_logging(error, "Task failed", verbose=False)

        mock_logger.error.assert_called_once_with("❌ Task failed: Another error")
        mock_traceback.assert_not_called()


class TestValidateLatLonBounds:
    """Test the _validate_lat_lon_bounds function."""

    def test_valid_bounds(self):
        """Test with valid lat/lon bounds."""
        result = _validate_lat_lon_bounds([45.0, 50.0], [-10.0, 10.0])
        assert result == (-10.0, 45.0, 10.0, 50.0)

    def test_no_bounds(self):
        """Test with no bounds provided."""
        result = _validate_lat_lon_bounds(None, None)
        assert result is None

    @patch("cruiseplan.init_utils.logger")
    def test_missing_lon_bounds(self, mock_logger):
        """Test with lat bounds but no lon bounds."""
        result = _validate_lat_lon_bounds([45.0, 50.0], None)
        assert result is None
        mock_logger.error.assert_called_once_with(
            "Both lat_bounds and lon_bounds must be provided for geographic search"
        )

    @patch("cruiseplan.init_utils.logger")
    def test_missing_lat_bounds(self, mock_logger):
        """Test with lon bounds but no lat bounds."""
        result = _validate_lat_lon_bounds(None, [-10.0, 10.0])
        assert result is None
        mock_logger.error.assert_called_once_with(
            "Both lat_bounds and lon_bounds must be provided for geographic search"
        )

    @patch("cruiseplan.init_utils.logger")
    def test_invalid_lat_bounds_length(self, mock_logger):
        """Test with invalid lat bounds length."""
        result = _validate_lat_lon_bounds([45.0], [-10.0, 10.0])
        assert result is None
        mock_logger.error.assert_called_once_with(
            "lat_bounds and lon_bounds must each contain exactly 2 values [min, max]"
        )

    @patch("cruiseplan.init_utils.logger")
    def test_invalid_lon_bounds_length(self, mock_logger):
        """Test with invalid lon bounds length."""
        result = _validate_lat_lon_bounds([45.0, 50.0], [-10.0, 10.0, 20.0])
        assert result is None
        mock_logger.error.assert_called_once_with(
            "lat_bounds and lon_bounds must each contain exactly 2 values [min, max]"
        )


class TestParseScheduleFormats:
    """Test the _parse_schedule_formats function."""

    def test_parse_all_without_netcdf(self):
        """Test parsing 'all' without derive_netcdf."""
        result = _parse_schedule_formats("all", derive_netcdf=False)
        assert result == ["html", "latex", "csv", "netcdf", "png"]

    def test_parse_all_with_netcdf(self):
        """Test parsing 'all' with derive_netcdf."""
        result = _parse_schedule_formats("all", derive_netcdf=True)
        assert result == ["html", "latex", "csv", "netcdf", "png", "netcdf_specialized"]

    def test_parse_single_format(self):
        """Test parsing single format."""
        result = _parse_schedule_formats("html")
        assert result == ["html"]

    def test_parse_multiple_formats(self):
        """Test parsing multiple comma-separated formats."""
        result = _parse_schedule_formats("html,csv,png")
        assert result == ["html", "csv", "png"]

    def test_parse_formats_with_spaces(self):
        """Test parsing formats with spaces."""
        result = _parse_schedule_formats("html, csv , png")
        assert result == ["html", "csv", "png"]

    def test_parse_none(self):
        """Test parsing None returns empty list."""
        result = _parse_schedule_formats(None)
        assert result == []


class TestParseMapFormats:
    """Test the _parse_map_formats function."""

    def test_parse_all(self):
        """Test parsing 'all' for map formats."""
        result = _parse_map_formats("all")
        assert result == ["png", "kml"]

    def test_parse_single_format(self):
        """Test parsing single map format."""
        result = _parse_map_formats("png")
        assert result == ["png"]

    def test_parse_multiple_formats(self):
        """Test parsing multiple map formats."""
        result = _parse_map_formats("png,kml")
        assert result == ["png", "kml"]

    def test_parse_none(self):
        """Test parsing None returns empty list."""
        result = _parse_map_formats(None)
        assert result == []
