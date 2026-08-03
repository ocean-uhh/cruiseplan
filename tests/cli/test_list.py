"""
Test suite for cruiseplan.cli.list command - Thin CLI Architecture.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

from cruiseplan.api.stationplan_api import StationplanResult
from cruiseplan.cli.list import run


class TestListThinCLI:
    """Test suite for thin CLI list functionality."""

    def test_list_success(self):
        """Test list command calls stationplan_list API correctly."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
        )

        with patch("cruiseplan.cli.list.stationplan_list") as mock_list:
            with patch("pathlib.Path.exists", return_value=True):
                mock_list.return_value = StationplanResult(
                    success=True,
                    message="Listed 5 activities",
                    output="Index  Time    Category  Duration  Name\n"
                    "0      0.0     station   2.0       STN_001\n",
                )

                run(args)

                mock_list.assert_called_once_with(Path("test_schedule.nc"))

    def test_list_missing_file(self):
        """Test list command exits cleanly when schedule file is missing."""
        args = argparse.Namespace(
            schedule_file=Path("nonexistent.nc"),
        )

        with patch("pathlib.Path.exists", return_value=False):
            with patch("sys.exit") as mock_exit:
                run(args)
                mock_exit.assert_called_once_with(1)

    def test_list_api_failure(self):
        """Test list command exits on API error."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
        )

        with patch("cruiseplan.cli.list.stationplan_list") as mock_list:
            with patch("pathlib.Path.exists", return_value=True):
                mock_list.return_value = StationplanResult(
                    success=False,
                    message="Invalid NetCDF file",
                    output="",
                )

                with patch("sys.exit") as mock_exit:
                    run(args)
                    mock_exit.assert_called_once_with(1)
