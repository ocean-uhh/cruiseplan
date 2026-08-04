"""
Test suite for cruiseplan.cli.run command - Thin CLI Architecture.

Tests argument passing to the API only. Business logic tested in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.run import run


class TestRunThinCLI:
    """Test suite for thin CLI run functionality."""

    def _make_args(self, **overrides):
        defaults = dict(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            leg=None,
            bathy_source="gebco2025",
            bathy_dir="data/bathymetry",
            bathy_stride=10,
            bathy_contours=None,
            lat=None,
            lon=None,
            figsize=None,
            no_ports=False,
            no_title=False,
            no_labels=False,
            no_legend=False,
            verbose=False,
            max_depth=None,
            eez=False,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def _make_results(self):
        process_result = cruiseplan.ProcessResult(
            config=Path("data/test_enriched.yaml"),
            files_created=[
                Path("data/test_enriched.yaml"),
                Path("data/test_map.png"),
            ],
            summary={
                "config_file": "test.yaml",
                "files_generated": 2,
                "enrichment_run": True,
                "validation_run": True,
                "map_generation_run": True,
                "enriched_config": "data/test_enriched.yaml",
                "total_files_created": 2,
            },
        )
        schedule_result = cruiseplan.ScheduleResult(
            timeline=[{"name": "CTD001", "duration_minutes": 60}],
            files_created=[
                Path("data/test_schedule.csv"),
                Path("data/test_schedule.html"),
            ],
            summary={"config_file": "data/test_enriched.yaml", "files_generated": 2},
        )
        return process_result, schedule_result

    def test_minimal_run_command(self):
        """Test minimal run command with required arguments only."""
        args = self._make_args()
        process_result, schedule_result = self._make_results()

        with patch("cruiseplan.run") as mock_run:
            mock_run.return_value = (process_result, schedule_result)
            run(args)

        mock_run.assert_called_once_with(
            config_file=Path("test.yaml"),
            output_dir="data",
            leg=None,
            bathy_source="gebco2025",
            bathy_dir="data/bathymetry",
            bathy_stride=10,
            bathy_contours=None,
            lat_bounds=None,
            lon_bounds=None,
            figsize=None,
            no_ports=False,
            no_title=False,
            no_labels=False,
            no_legend=False,
            verbose=False,
            max_depth=None,
            include_eez=False,
        )

    def test_eez_flag_passed(self):
        """Test that --eez flag is passed as include_eez=True."""
        args = self._make_args(eez=True)
        process_result, schedule_result = self._make_results()

        with patch("cruiseplan.run") as mock_run:
            mock_run.return_value = (process_result, schedule_result)
            run(args)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["include_eez"] is True

    def test_leg_flag_passed(self):
        """Test that --leg is passed through to the API."""
        args = self._make_args(leg="leg1")
        process_result, schedule_result = self._make_results()

        with patch("cruiseplan.run") as mock_run:
            mock_run.return_value = (process_result, schedule_result)
            run(args)

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["leg"] == "leg1"

    def test_process_failure_exits(self):
        """Test that a failed process step (config=None) causes sys.exit(1)."""
        args = self._make_args()
        failed_process = cruiseplan.ProcessResult(
            config=None,
            files_created=[],
            summary={"config_file": "test.yaml", "files_generated": 0},
        )
        # schedule_result won't be used but run() needs to return a tuple
        _, schedule_result = self._make_results()

        with patch("cruiseplan.run") as mock_run:
            mock_run.return_value = (failed_process, schedule_result)
            with pytest.raises(SystemExit) as exc_info:
                run(args)
        assert exc_info.value.code == 1

    def test_schedule_failure_exits(self):
        """Test that a failed schedule step (timeline=None) causes sys.exit(1)."""
        args = self._make_args()
        process_result, _ = self._make_results()
        failed_schedule = cruiseplan.ScheduleResult(
            timeline=None,
            files_created=[],
            summary={"config_file": "data/test_enriched.yaml", "files_generated": 0},
        )

        with patch("cruiseplan.run") as mock_run:
            mock_run.return_value = (process_result, failed_schedule)
            with pytest.raises(SystemExit) as exc_info:
                run(args)
        assert exc_info.value.code == 1


class TestRunBuildParser:
    """Test suite for run subparser construction."""

    def test_build_parser_registers_subcommand(self):
        """Test that build_parser registers the run subcommand."""
        import argparse

        from cruiseplan.cli.run import build_parser

        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest="subcommand")
        build_parser(subparsers)
        args = main_parser.parse_args(["run", "cruise.yaml"])
        assert args.subcommand == "run"
        assert args.config_file == Path("cruise.yaml")

    def test_defaults(self):
        """Test parser default values."""
        import argparse

        from cruiseplan.cli.run import build_parser

        main_parser = argparse.ArgumentParser()
        subparsers = main_parser.add_subparsers(dest="subcommand")
        build_parser(subparsers)
        args = main_parser.parse_args(["run", "cruise.yaml"])
        assert args.leg is None
        assert args.eez is False
        assert args.no_ports is False
        assert args.bathy_stride == 10
