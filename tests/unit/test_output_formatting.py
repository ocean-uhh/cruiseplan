"""
Tests for output formatting utility functions.

This module tests the remaining formatting functions after cleanup.
- Time utilities moved to output.output_utils
- Error formatters remain in utils.output_formatting as legacy functions
"""

from datetime import datetime

from cruiseplan.output.output_utils import round_time_to_minute
from cruiseplan.utils.output_formatting import (
    _format_cli_error,  # Legacy alias
    _format_dependency_error,  # Legacy alias
    format_cli_error,
    format_dependency_error,
)


class TestTimeUtilities:
    """Test time formatting utilities in their new home."""

    def test_round_time_to_minute_basic(self):
        """Test basic time rounding functionality."""
        dt = datetime(2023, 1, 1, 12, 30, 45, 123456)
        result = round_time_to_minute(dt)

        assert result == datetime(2023, 1, 1, 12, 30, 0, 0)
        assert result.second == 0
        assert result.microsecond == 0

    def test_round_time_to_minute_already_rounded(self):
        """Test time that's already rounded to minute."""
        dt = datetime(2023, 1, 1, 12, 30, 0, 0)
        result = round_time_to_minute(dt)

        assert result == dt

    def test_round_time_to_minute_preserves_other_fields(self):
        """Test that year, month, day, hour, minute are preserved."""
        dt = datetime(2023, 12, 25, 23, 59, 30, 500000)
        result = round_time_to_minute(dt)

        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25
        assert result.hour == 23
        assert result.minute == 59


class TestErrorFormatting:
    """Test error message formatting functions."""

    def test_format_cli_error_basic(self):
        """Test basic CLI error formatting."""
        error = FileNotFoundError("config.yaml not found")
        result = format_cli_error("Configuration loading", error)

        assert "❌ Configuration loading failed:" in result
        assert "config.yaml not found" in result

    def test_format_cli_error_with_context(self):
        """Test CLI error formatting with context."""
        error = ValueError("Invalid parameter")
        context = {"file": "cruise.yaml", "line": 15}
        result = format_cli_error("Validation", error, context=context)

        assert "❌ Validation failed:" in result
        assert "Context:" in result
        assert "file: cruise.yaml" in result
        assert "line: 15" in result

    def test_format_cli_error_with_suggestions(self):
        """Test CLI error formatting with suggestions."""
        error = FileNotFoundError("file.yaml")
        suggestions = ["Check file path", "Verify file exists"]
        result = format_cli_error("File loading", error, suggestions=suggestions)

        assert "❌ File loading failed:" in result
        assert "Suggestions:" in result
        assert "• Check file path" in result
        assert "• Verify file exists" in result

    def test_format_cli_error_complete(self):
        """Test CLI error formatting with all parameters."""
        error = Exception("Something went wrong")
        context = {"operation": "test"}
        suggestions = ["Try again"]
        result = format_cli_error(
            "Test", error, context=context, suggestions=suggestions
        )

        assert "❌ Test failed:" in result
        assert "Context:" in result
        assert "Suggestions:" in result

    def test_format_dependency_error_basic(self):
        """Test basic dependency error formatting."""
        result = format_dependency_error("netCDF4", "NetCDF export")

        assert "❌ Dependency error:" in result
        assert "netCDF4 required for NetCDF export" in result

    def test_format_dependency_error_with_install(self):
        """Test dependency error with install command."""
        result = format_dependency_error(
            "netCDF4", "NetCDF export", "pip install netCDF4"
        )

        assert "❌ Dependency error:" in result
        assert "netCDF4 required for NetCDF export" in result
        assert "Install with: pip install netCDF4" in result


class TestLegacyAliases:
    """Test that legacy function aliases still work."""

    def test_legacy_format_cli_error(self):
        """Test that _format_cli_error alias works."""
        error = Exception("test error")
        result = _format_cli_error("Test", error)

        assert "❌ Test failed:" in result
        assert "test error" in result

    def test_legacy_format_dependency_error(self):
        """Test that _format_dependency_error alias works."""
        result = _format_dependency_error("test_dep", "test operation")

        assert "❌ Dependency error:" in result
        assert "test_dep required for test operation" in result
