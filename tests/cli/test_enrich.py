"""
Tests for enrichment CLI command.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.enrich import main


class TestEnrichCommand:
    """Test enrich command functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    @patch("cruiseplan.cli.enrich.setup_logging")
    def test_enrich_no_operations_specified(self, mock_setup_logging):
        """Test that command fails when no operations are specified."""
        input_file = self.get_fixture_path("cruise_simple.yaml")

        args = Namespace(
            add_depths=False,
            add_coords=False,
            config_file=input_file,
            output_file=None,
            output_dir=Path("."),
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    def test_enrich_nonexistent_file(self, tmp_path):
        """Test handling of nonexistent input file."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=nonexistent_file,
            output_file=tmp_path / "output.yaml",
            output_dir=None,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_enrich_keyboard_interrupt(self, mock_enrich):
        """Test handling of keyboard interrupt."""
        input_file = self.get_fixture_path("cruise_simple.yaml")
        mock_enrich.side_effect = KeyboardInterrupt()

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=Path("output.yaml"),
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_enrich_unexpected_error(self, mock_enrich):
        """Test handling of unexpected errors."""
        input_file = self.get_fixture_path("cruise_simple.yaml")
        mock_enrich.side_effect = RuntimeError("Unexpected error")

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=Path("output.yaml"),
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    def test_enrich_validation_error_formatting(self, tmp_path):
        """Test that ValidationError is properly formatted with user-friendly messages."""
        # Create a YAML with validation errors (missing longitude)
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text(
            """
cruise_name: "Test"
start_date: "2025-01-01"
default_vessel_speed: 10
departure_port: {name: P1, position: "0,0"}
arrival_port: {name: P1, position: "0,0"}
first_station: "S1"
last_station: "S1"
stations:
  - name: S1
    latitude: 60.0
    operation_type: CTD
    action: profile
legs: []
"""
        )

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=invalid_yaml,
            output_file=tmp_path / "output.yaml",
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.enrich.validate_output_path")
    def test_enrich_cli_error_formatting(self, mock_validate_output, tmp_path):
        """Test that CLIError is properly handled."""
        from cruiseplan.cli.utils import CLIError

        # Mock validate_output_path to raise CLIError
        mock_validate_output.side_effect = CLIError("Invalid output path")
        input_file = self.get_fixture_path("cruise_simple.yaml")

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=tmp_path / "output.yaml",
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)


class TestEnrichCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import enrich

        assert hasattr(enrich, "main")


if __name__ == "__main__":
    pytest.main([__file__])
