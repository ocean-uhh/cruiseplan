"""
Test suite for cruiseplan.cli.validate command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.validate import main


class TestValidateThinCLI:
    """Test suite for thin CLI validate functionality."""

    def test_minimal_validate_command(self):
        """Test minimal validate command with required arguments."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            # Mock successful validation response
            mock_validate.return_value = cruiseplan.ValidationResult(
                success=True,
                errors=[],
                warnings=["Sample warning"],
                summary={
                    "cruise_name": "test_cruise",
                    "error_count": 0,
                    "warning_count": 1,
                },
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with code 0 (success)
            assert exc_info.value.code == 0

            # Verify API was called with correct arguments
            mock_validate.assert_called_once_with(
                config_file=Path("test.yaml"),
                bathy_source="etopo2022",
                bathy_dir="data/bathymetry",
                check_depths=True,
                tolerance=10.0,
                strict=False,
                warnings_only=False,
                verbose=False,
            )

    def test_validate_with_custom_options(self):
        """Test validate command with custom validation options."""
        args = argparse.Namespace(
            config_file=Path("custom.yaml"),
            bathy_source="gebco2025",
            bathy_dir="/custom/bathy",
            check_depths=False,
            tolerance=5.0,
            strict=True,
            warnings_only=True,
            verbose=True,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.return_value = cruiseplan.ValidationResult(
                success=True,
                errors=[],
                warnings=["Custom warning", "Another warning"],
                summary={
                    "cruise_name": "custom_cruise",
                    "error_count": 0,
                    "warning_count": 2,
                },
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 0
            mock_validate.assert_called_once_with(
                config_file=Path("custom.yaml"),
                bathy_source="gebco2025",
                bathy_dir="/custom/bathy",
                check_depths=False,
                tolerance=5.0,
                strict=True,
                warnings_only=True,
                verbose=True,
            )

    def test_validate_with_errors(self):
        """Test validate command when validation fails with errors."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.return_value = cruiseplan.ValidationResult(
                success=False,
                errors=[
                    "Missing required field: cruise_name",
                    "Invalid station coordinates",
                ],
                warnings=["Depth value suspicious"],
                summary={"cruise_name": None, "error_count": 2, "warning_count": 1},
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with code 1 (failure)
            assert exc_info.value.code == 1

    def test_validate_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.side_effect = cruiseplan.ValidationError(
                "Invalid YAML configuration: syntax error"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_validate_file_error_handling(self):
        """Test handling of FileError from API."""
        args = argparse.Namespace(
            config_file=Path("missing.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.side_effect = cruiseplan.FileError(
                "Configuration file not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_validate_bathymetry_error_handling(self):
        """Test handling of BathymetryError from API."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            bathy_source="invalid_source",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.side_effect = cruiseplan.BathymetryError(
                "Bathymetry data not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_validate_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_validate_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_validate_unexpected_error_with_verbose(self):
        """Test handling of unexpected errors with verbose traceback."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=True,  # Should trigger traceback printing
        )

        with (
            patch("cruiseplan.validate") as mock_validate,
            patch("traceback.print_exc") as mock_traceback,
        ):
            mock_validate.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should print traceback when verbose=True
            mock_traceback.assert_called_once()
            assert exc_info.value.code == 1

    def test_default_argument_handling(self):
        """Test that missing arguments get proper defaults."""
        # Minimal args - missing optional attributes
        args = argparse.Namespace(
            config_file=Path("test.yaml")
            # Missing: bathy_source, bathy_dir, check_depths, etc.
        )

        with patch("cruiseplan.validate") as mock_validate:
            mock_validate.return_value = cruiseplan.ValidationResult(
                success=True, errors=[], warnings=[], summary={}
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should use defaults for missing arguments
            mock_validate.assert_called_once_with(
                config_file=Path("test.yaml"),
                bathy_source="etopo2022",  # default
                bathy_dir="data/bathymetry",  # default
                check_depths=True,  # default
                tolerance=10.0,  # default
                strict=False,  # default
                warnings_only=False,  # default
                verbose=False,  # default
            )
            assert exc_info.value.code == 0


class TestValidationResultType:
    """Test the ValidationResult type for completeness."""

    def test_validation_result_success(self):
        """Test ValidationResult with successful validation."""
        result = cruiseplan.ValidationResult(
            success=True,
            errors=[],
            warnings=["warning1", "warning2"],
            summary={"cruise_name": "test", "error_count": 0, "warning_count": 2},
        )

        assert result.success is True
        assert bool(result) is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 2
        assert "✅ Validation complete" in str(result)
        assert "(2 warnings)" in str(result)

    def test_validation_result_failure(self):
        """Test ValidationResult with failed validation."""
        result = cruiseplan.ValidationResult(
            success=False,
            errors=["error1", "error2"],
            warnings=["warning1"],
            summary={"cruise_name": "test", "error_count": 2, "warning_count": 1},
        )

        assert result.success is False
        assert bool(result) is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert "❌ Validation failed (2 errors, 1 warnings)" in str(result)
