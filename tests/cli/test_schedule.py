"""
Tests for schedule CLI command.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.schedule import main


class TestScheduleCommand:
    """Test schedule command functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    def test_schedule_basic_real_file(self, tmp_path):
        """Test basic schedule generation using real fixture file."""
        input_file = self.get_fixture_path("cruise_simple.yaml")

        # Create args
        args = Namespace(
            config_file=input_file,
            output_dir=tmp_path,
            format="csv",
            validate_depths=False,
            leg=None,
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify output files were created
        expected_files = [tmp_path / "Simple_Test_Cruise_2028_schedule.csv"]

        for expected_file in expected_files:
            assert (
                expected_file.exists()
            ), f"Expected output file {expected_file} was not created"

    def test_schedule_all_formats_real_file(self, tmp_path):
        """Test schedule generation with all formats using real fixture file."""
        input_file = self.get_fixture_path("cruise_simple.yaml")

        # Create args
        args = Namespace(
            config_file=input_file,
            output_dir=tmp_path,
            format="all",
            validate_depths=False,
            leg=None,
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify at least some output files were created (some formats might not be available)
        output_files = list(tmp_path.glob("Simple_Test_Cruise_2028_schedule.*"))
        assert (
            len(output_files) >= 2
        ), "Expected at least HTML and CSV formats to be generated"

    def test_schedule_with_depth_validation_real_file(self, tmp_path):
        """Test schedule generation with depth validation."""
        input_file = self.get_fixture_path("cruise_simple.yaml")

        # Create args
        args = Namespace(
            config_file=input_file,
            output_dir=tmp_path,
            format="html",
            validate_depths=True,
            leg=None,
            verbose=False,
            quiet=False,
        )

        # Should complete successfully (may have warnings but should pass)
        main(args)

        # Verify at least one output file was created (may have different naming)
        output_files = list(tmp_path.glob("*.html"))
        assert (
            len(output_files) >= 1
        ), f"Expected HTML output file to be created, found files: {list(tmp_path.iterdir())}"

    def test_schedule_nonexistent_file(self, tmp_path):
        """Test handling of nonexistent input file."""
        nonexistent_file = tmp_path / "nonexistent.yaml"

        args = Namespace(
            config_file=nonexistent_file,
            output_dir=tmp_path,
            format="csv",
            validate_depths=False,
            leg=None,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    def test_schedule_specific_leg_real_file(self, tmp_path):
        """Test schedule generation for specific leg."""
        input_file = self.get_fixture_path("cruise_multi_leg.yaml")

        # Create args for specific leg
        args = Namespace(
            config_file=input_file,
            output_dir=tmp_path,
            format="csv",
            validate_depths=False,
            leg="Southern_Operations",  # Based on actual fixture content
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify output file was created with leg suffix
        output_files = list(tmp_path.glob("*_Southern_Operations_schedule.csv"))
        assert len(output_files) >= 1, "Expected leg-specific output file to be created"

    def test_schedule_nonexistent_leg_real_file(self, tmp_path):
        """Test handling of nonexistent leg name."""
        input_file = self.get_fixture_path("cruise_simple.yaml")

        args = Namespace(
            config_file=input_file,
            output_dir=tmp_path,
            format="csv",
            validate_depths=False,
            leg="NonexistentLeg",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.calculators.scheduler.generate_cruise_schedule")
    def test_schedule_keyboard_interrupt(self, mock_generate):
        """Test handling of keyboard interrupt."""
        input_file = self.get_fixture_path("cruise_simple.yaml")
        mock_generate.side_effect = KeyboardInterrupt()

        args = Namespace(
            config_file=input_file,
            output_dir=Path("."),
            format="csv",
            validate_depths=False,
            leg=None,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)

    @patch("cruiseplan.calculators.scheduler.generate_cruise_schedule")
    def test_schedule_unexpected_error(self, mock_generate):
        """Test handling of unexpected errors."""
        input_file = self.get_fixture_path("cruise_simple.yaml")
        mock_generate.side_effect = RuntimeError("Unexpected error")

        args = Namespace(
            config_file=input_file,
            output_dir=Path("."),
            format="csv",
            validate_depths=False,
            leg=None,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit, match="1"):
            main(args)


class TestScheduleCommandExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import schedule

        assert hasattr(schedule, "main")


if __name__ == "__main__":
    pytest.main([__file__])
