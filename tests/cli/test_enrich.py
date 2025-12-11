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
            assert "depth" in station
            assert station["depth"] > 0  # Should have positive depth values

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
            assert "depth" in station
            assert station["depth"] > 0
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
            coord_format="dmm",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

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
