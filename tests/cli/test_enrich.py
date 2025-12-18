"""
Tests for enrichment CLI command.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cruiseplan.cli.enrich import main


class TestEnrichCommand:
    """Test enrich command functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_enrich_depths_only_real_file(self, tmp_path):
        """Test enriching with depths only using real fixture file."""
        # Use real fixture file without depths
        input_file = self.get_fixture_path("cruise_simple_no_depth.yaml")
        output_file = tmp_path / "enriched_output.yaml"

        # Create args
        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify output file was created
        assert output_file.exists()

        # Verify depths were added
        with open(output_file) as f:
            enriched_data = yaml.safe_load(f)

        # Check that stations now have depth values
        for station in enriched_data["stations"]:
            assert "water_depth" in station
            assert station["water_depth"] > 0  # Should have positive depth values

    def test_enrich_coords_only_real_file(self, tmp_path):
        """Test enriching with coordinates only using real fixture file."""
        input_file = self.get_fixture_path("cruise_simple.yaml")
        output_file = tmp_path / "coords_output.yaml"

        # Create args
        args = Namespace(
            add_depths=False,
            add_coords=True,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify output file was created
        assert output_file.exists()

        # Verify coordinates were added
        with open(output_file) as f:
            enriched_data = yaml.safe_load(f)

        # Check that stations now have coordinate fields
        for station in enriched_data["stations"]:
            assert "coordinates_dmm" in station
            assert (
                "'" in station["coordinates_dmm"]
            )  # Should contain degree/minute format

    def test_enrich_both_depths_and_coords_real_file(self, tmp_path):
        """Test enriching with both depths and coordinates using real fixture file."""
        input_file = self.get_fixture_path("cruise_simple_no_depth.yaml")
        output_file = tmp_path / "full_enriched_output.yaml"

        # Create args
        args = Namespace(
            add_depths=True,
            add_coords=True,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify output file was created
        assert output_file.exists()

        # Verify both depths and coordinates were added
        with open(output_file) as f:
            enriched_data = yaml.safe_load(f)

        for station in enriched_data["stations"]:
            assert "water_depth" in station
            assert station["water_depth"] > 0
            assert "coordinates_dmm" in station
            assert "'" in station["coordinates_dmm"]

    def test_enrich_coords_already_enriched_real_file(self, tmp_path):
        """Test when coordinate enrichment is not needed because they already exist."""
        # First enrich a file with coordinates
        input_file = self.get_fixture_path("cruise_simple.yaml")
        intermediate_file = tmp_path / "intermediate.yaml"

        args1 = Namespace(
            add_depths=False,
            add_coords=True,
            config_file=input_file,
            output_file=intermediate_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )
        main(args1)

        # Now try to enrich coordinates again (should make no changes)
        final_output = tmp_path / "final_output.yaml"
        args2 = Namespace(
            add_depths=False,
            add_coords=True,
            config_file=intermediate_file,
            output_file=final_output,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )
        main(args2)

        # First file should exist, second should NOT exist since no enrichment was needed
        assert intermediate_file.exists()
        assert not final_output.exists()  # No output created when no changes made

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

    def test_enrich_verbose_and_quiet_flags(self, tmp_path):
        """Test verbose and quiet logging flags."""
        input_file = self.get_fixture_path("cruise_simple_no_depth.yaml")
        output_file = tmp_path / "verbose_test.yaml"

        # Test with verbose flag
        args_verbose = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=True,
            quiet=False,
        )

        main(args_verbose)
        assert output_file.exists()

        # Clean up for quiet test
        output_file.unlink()

        # Test with quiet flag
        args_quiet = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=True,
        )

        main(args_quiet)
        assert output_file.exists()

    def test_enrich_different_bathymetry_sources(self, tmp_path):
        """Test enrichment with different bathymetry sources."""
        input_file = self.get_fixture_path("cruise_simple_no_depth.yaml")

        # Test with gebco2025 source
        output_file = tmp_path / "gebco_test.yaml"
        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        main(args)
        assert output_file.exists()

    def test_enrich_different_coord_formats(self, tmp_path):
        """Test enrichment with different coordinate formats."""
        input_file = self.get_fixture_path("cruise_simple.yaml")

        # Test with dmm format (which is supported)
        output_file = tmp_path / "dmm_test.yaml"
        args = Namespace(
            add_depths=False,
            add_coords=True,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        main(args)
        assert output_file.exists()

        # Verify coordinate field was added
        with open(output_file) as f:
            enriched_data = yaml.safe_load(f)

        # Verify coordinate fields were added to stations
        for station in enriched_data["stations"]:
            if "coordinates_dmm" in station:
                assert (
                    "'" in station["coordinates_dmm"]
                )  # DMM format contains minute symbol
                break

    def test_enrich_coordinates_all_entities(self, tmp_path):
        """Test that coordinate enrichment works for all entity types."""
        input_file = self.get_fixture_path("cruise_simple.yaml")
        output_file = tmp_path / "all_coords_test.yaml"

        args = Namespace(
            add_depths=False,
            add_coords=True,
            config_file=input_file,
            output_file=output_file,
            output_dir=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        main(args)
        assert output_file.exists()

        # Verify coordinate fields were added to all entity types
        with open(output_file) as f:
            enriched_data = yaml.safe_load(f)

        # Check departure port coordinates
        if "departure_port" in enriched_data and enriched_data["departure_port"]:
            if "coordinates_dmm" in enriched_data["departure_port"]:
                assert "'" in enriched_data["departure_port"]["coordinates_dmm"]

        # Check arrival port coordinates
        if "arrival_port" in enriched_data and enriched_data["arrival_port"]:
            if "coordinates_dmm" in enriched_data["arrival_port"]:
                assert "'" in enriched_data["arrival_port"]["coordinates_dmm"]

        # Check transit route coordinates
        if "transits" in enriched_data:
            for transit in enriched_data["transits"]:
                if "route_dmm" in transit:
                    for point in transit["route_dmm"]:
                        assert "position_dmm" in point
                        assert "'" in point["position_dmm"]

        # Check area corner coordinates
        if "areas" in enriched_data:
            for area in enriched_data["areas"]:
                if "corners_dmm" in area:
                    for corner in area["corners_dmm"]:
                        assert "position_dmm" in corner
                        assert "'" in corner["position_dmm"]

    def test_enrich_output_dir_instead_of_file(self, tmp_path):
        """Test using output directory instead of specific output file."""
        input_file = self.get_fixture_path("cruise_simple_no_depth.yaml")

        args = Namespace(
            add_depths=True,
            add_coords=False,
            config_file=input_file,
            output_file=None,  # Use output_dir instead
            output_dir=tmp_path,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        main(args)

        # Check that output file was created with expected name
        expected_output = tmp_path / "cruise_simple_no_depth_enriched.yaml"
        assert expected_output.exists()


class TestEnrichCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import enrich

        assert hasattr(enrich, "main")


if __name__ == "__main__":
    pytest.main([__file__])
