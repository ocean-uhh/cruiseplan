"""
Tests for validation CLI command.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.utils import CLIError
from cruiseplan.cli.validate import main


class TestValidateCommand:
    """Test validate command functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_validate_nonexistent_file(self, tmp_path):
        """Test validation with nonexistent file."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        args = Namespace(
            config_file=nonexistent_file,
            check_depths=False,
            tolerance=10.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.core.validation.validate_configuration_file")
    def test_validate_keyboard_interrupt(self, mock_validate_config):
        """Test handling of keyboard interrupt."""
        input_file = self.get_fixture_path("tc4_mixed_ops.yaml")
        mock_validate_config.side_effect = KeyboardInterrupt()

        args = Namespace(
            config_file=input_file,
            check_depths=False,
            tolerance=10.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.validate.validate_configuration_file")
    @patch("cruiseplan.cli.validate.validate_input_file")
    @patch("cruiseplan.cli.validate.setup_logging")
    def test_validate_success_with_warnings(
        self, mock_setup_logging, mock_validate_input, mock_validate_config
    ):
        """Test successful validation with warnings."""
        # Setup mocks
        mock_validate_input.return_value = Path("/test/config.yaml")
        mock_validate_config.return_value = (
            True,
            [],
            ["Station A: depth discrepancy of 15%", "Station B: no bathymetry data"],
        )

        # Create args
        args = Namespace(
            config_file=Path("config.yaml"),
            check_depths=True,
            tolerance=10.0,
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            strict=True,
            warnings_only=True,
            verbose=True,
            quiet=False,
        )

        # Should exit with code 0
        with pytest.raises(SystemExit, match="0"):
            main(args)

        # Verify depth checking was enabled
        mock_validate_config.assert_called_once_with(
            config_path=Path("/test/config.yaml"),
            check_depths=True,
            tolerance=10.0,
            bathymetry_source="gebco2025",
            bathymetry_dir="data",
            strict=True,
        )

    @patch("cruiseplan.cli.validate.validate_configuration_file")
    @patch("cruiseplan.cli.validate.validate_input_file")
    @patch("cruiseplan.cli.validate.setup_logging")
    def test_validate_failure_with_errors(
        self, mock_setup_logging, mock_validate_input, mock_validate_config
    ):
        """Test validation failure with errors."""
        # Setup mocks
        mock_validate_input.return_value = Path("/test/config.yaml")
        mock_validate_config.return_value = (
            False,
            [
                "Schema error at stations.0.depth: value must be positive",
                "Missing required field",
            ],
            ["Some warning"],
        )

        # Create args
        args = Namespace(
            config_file=Path("config.yaml"),
            check_depths=False,
            tolerance=10.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.validate.validate_input_file")
    @patch("cruiseplan.cli.validate.setup_logging")
    def test_validate_input_validation_error(
        self, mock_setup_logging, mock_validate_input
    ):
        """Test handling of input file validation errors."""
        mock_validate_input.side_effect = CLIError("File not found")

        args = Namespace(
            config_file=Path("nonexistent.yaml"),
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.validate.validate_configuration_file")
    @patch("cruiseplan.cli.validate.validate_input_file")
    @patch("cruiseplan.cli.validate.setup_logging")
    def test_validate_keyboard_interrupt(
        self, mock_setup_logging, mock_validate_input, mock_validate_config
    ):
        """Test handling of keyboard interrupt."""
        mock_validate_input.return_value = Path("/test/config.yaml")
        mock_validate_config.side_effect = KeyboardInterrupt()

        args = Namespace(
            config_file=Path("config.yaml"),
            check_depths=False,
            tolerance=10.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.validate.validate_configuration_file")
    @patch("cruiseplan.cli.validate.validate_input_file")
    @patch("cruiseplan.cli.validate.setup_logging")
    def test_validate_unexpected_error(
        self, mock_setup_logging, mock_validate_input, mock_validate_config
    ):
        """Test handling of unexpected errors."""
        mock_validate_input.return_value = Path("/test/config.yaml")
        mock_validate_config.side_effect = RuntimeError("Unexpected error")

        args = Namespace(
            config_file=Path("config.yaml"),
            check_depths=False,
            tolerance=10.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.validate.validate_configuration_file")
    @patch("cruiseplan.cli.validate.validate_input_file")
    @patch("cruiseplan.cli.validate.setup_logging")
    def test_validate_only_errors_no_warnings(
        self, mock_setup_logging, mock_validate_input, mock_validate_config
    ):
        """Test validation when only errors exist (no warnings)."""
        # Setup mocks
        mock_validate_input.return_value = Path("/test/config.yaml")
        mock_validate_config.return_value = (
            False,
            ["Critical error"],
            [],  # No warnings
        )

        args = Namespace(
            config_file=Path("config.yaml"),
            check_depths=False,
            tolerance=10.0,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            strict=False,
            warnings_only=False,
            verbose=False,
            quiet=False,
        )

        # Should exit with code 1
        with pytest.raises(SystemExit, match="1"):
            main(args)


class TestValidateCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import validate

        assert hasattr(validate, "main")


if __name__ == "__main__":
    pytest.main([__file__])
