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
        input_file = self.get_fixture_path("tc1_single.yaml")

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
        input_file = self.get_fixture_path("tc1_single.yaml")
        mock_enrich.side_effect = KeyboardInterrupt()

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=Path("output.yaml"),
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_enrich_unexpected_error(self, mock_enrich):
        """Test handling of unexpected errors."""
        input_file = self.get_fixture_path("tc1_single.yaml")
        mock_enrich.side_effect = RuntimeError("Unexpected error")

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=Path("output.yaml"),
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
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
            coord_format="ddm",
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
        input_file = self.get_fixture_path("tc1_single.yaml")

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=tmp_path / "output.yaml",
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
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


class TestEnrichSuccessfulOperations:
    """Test successful enrichment operations."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    @patch("cruiseplan.cli.enrich.validate_input_file")
    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_add_depths_success(self, mock_enrich, mock_validate_input, tmp_path):
        """Test successful depth addition."""
        input_file = self.get_fixture_path("tc1_single.yaml")
        output_file = tmp_path / "enriched.yaml"

        # Mock validate_input_file to return the input file path
        mock_validate_input.return_value = input_file

        # Mock successful enrichment
        mock_enrich.return_value = {
            "stations_with_depths_added": 3,
            "stations_with_coords_added": 0,
            "sections_expanded": 0,
            "ports_expanded": 0,
            "defaults_added": 1,
            "station_defaults_added": 0,
        }

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            verbose=False,
            quiet=False,
        )

        # Should not raise an exception
        main(args)

        # Verify enrich_configuration was called with correct parameters
        mock_enrich.assert_called_once_with(
            config_path=input_file,
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            expand_ports=False,
            bathymetry_source="etopo2022",
            bathymetry_dir="data",
            coord_format="ddm",
            output_path=output_file,
        )

    @patch("cruiseplan.cli.enrich.validate_input_file")
    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_add_coords_success(self, mock_enrich, mock_validate_input, tmp_path):
        """Test successful coordinate addition."""
        input_file = self.get_fixture_path("tc1_single.yaml")

        # Mock validate_input_file to return the input file path
        mock_validate_input.return_value = input_file

        # Mock successful enrichment
        mock_enrich.return_value = {
            "stations_with_depths_added": 0,
            "stations_with_coords_added": 5,
            "sections_expanded": 0,
            "ports_expanded": 0,
            "defaults_added": 0,
            "station_defaults_added": 2,
        }

        args = Namespace(
            add_depths=False,
            add_coords=True,
            config_file=input_file,
            output_file=None,
            output_dir=tmp_path,
            output="custom_name",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("bathy_data"),
            coord_format="dms",
            verbose=False,
            quiet=False,
        )

        # Should not raise an exception
        main(args)

        # Verify enrich_configuration was called with correct parameters
        expected_output = tmp_path / "custom_name_enriched.yaml"
        mock_enrich.assert_called_once_with(
            config_path=input_file,
            add_depths=False,
            add_coords=True,
            expand_sections=False,
            expand_ports=False,
            bathymetry_source="gebco2025",
            bathymetry_dir="bathy_data",
            coord_format="dms",
            output_path=expected_output,
        )

    @patch("cruiseplan.cli.enrich.validate_input_file")
    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_expansion_operations_success(
        self, mock_enrich, mock_validate_input, tmp_path
    ):
        """Test successful section and port expansion."""
        input_file = self.get_fixture_path("tc1_single.yaml")

        # Mock validate_input_file to return the input file path
        mock_validate_input.return_value = input_file

        # Mock successful enrichment with expansions
        mock_enrich.return_value = {
            "stations_with_depths_added": 0,
            "stations_with_coords_added": 0,
            "sections_expanded": 2,
            "stations_from_expansion": 15,
            "ports_expanded": 3,
            "defaults_added": 0,
            "station_defaults_added": 0,
        }

        args = Namespace(
            add_depths=False,
            add_coords=False,
            expand_sections=True,
            expand_ports=True,
            config_file=input_file,
            output_file=None,
            output_dir=tmp_path,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            verbose=False,
            quiet=False,
        )

        # Should not raise an exception
        main(args)

        # Verify expansion flags were passed correctly
        mock_enrich.assert_called_once_with(
            config_path=input_file,
            add_depths=False,
            add_coords=False,
            expand_sections=True,
            expand_ports=True,
            bathymetry_source="etopo2022",
            bathymetry_dir="data",
            coord_format="ddm",
            output_path=tmp_path / f"{input_file.stem}_enriched.yaml",
        )

    @patch("cruiseplan.cli.enrich.validate_input_file")
    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_no_enhancements_needed(self, mock_enrich, mock_validate_input, tmp_path):
        """Test when configuration is already complete."""
        input_file = self.get_fixture_path("tc1_single.yaml")

        # Mock validate_input_file to return the input file path
        mock_validate_input.return_value = input_file

        # Mock no changes needed
        mock_enrich.return_value = {
            "stations_with_depths_added": 0,
            "stations_with_coords_added": 0,
            "sections_expanded": 0,
            "ports_expanded": 0,
            "defaults_added": 0,
            "station_defaults_added": 0,
        }

        args = Namespace(
            add_depths=True,
            add_coords=True,
            config_file=input_file,
            output_file=None,
            output_dir=tmp_path,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            verbose=False,
            quiet=False,
        )

        # Should not raise an exception
        main(args)

    @patch("cruiseplan.cli.enrich.validate_output_path")
    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_legacy_output_file_warning(
        self, mock_enrich, mock_validate_output, tmp_path
    ):
        """Test that legacy --output-file parameter shows deprecation warning."""
        input_file = self.get_fixture_path("tc1_single.yaml")
        output_file = tmp_path / "legacy_output.yaml"

        # Mock successful validation and enrichment
        mock_validate_output.return_value = output_file
        mock_enrich.return_value = {
            "stations_with_depths_added": 1,
            "stations_with_coords_added": 0,
            "sections_expanded": 0,
            "ports_expanded": 0,
            "defaults_added": 0,
            "station_defaults_added": 0,
        }

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=output_file,  # Using legacy parameter
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            verbose=False,
            quiet=False,
        )

        with patch("cruiseplan.cli.enrich.logger") as mock_logger:
            main(args)

            # Verify deprecation warning was logged
            mock_logger.warning.assert_called_with(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )

    @patch("cruiseplan.cli.enrich.validate_input_file")
    @patch("cruiseplan.cli.enrich.enrich_configuration")
    def test_all_enhancement_types_combined(
        self, mock_enrich, mock_validate_input, tmp_path
    ):
        """Test all enhancement types working together."""
        input_file = self.get_fixture_path("tc1_single.yaml")

        # Mock validate_input_file to return the input file path
        mock_validate_input.return_value = input_file

        # Mock all types of enhancements
        mock_enrich.return_value = {
            "stations_with_depths_added": 2,
            "stations_with_coords_added": 3,
            "sections_expanded": 1,
            "stations_from_expansion": 8,
            "ports_expanded": 2,
            "defaults_added": 1,
            "station_defaults_added": 1,
        }

        args = Namespace(
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
            config_file=input_file,
            output_file=None,
            output_dir=tmp_path,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="ddm",
            verbose=False,
            quiet=False,
        )

        # Should complete successfully
        main(args)


if __name__ == "__main__":
    pytest.main([__file__])
