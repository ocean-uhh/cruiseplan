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

    def test_schedule_nonexistent_leg_real_file(self, tmp_path):
        """Test handling of nonexistent leg name."""
        input_file = self.get_fixture_path("tc4_mixed_ops.yaml")

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
