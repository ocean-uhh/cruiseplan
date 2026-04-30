"""
Test suite for cruiseplan.cli.stationplan command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.api.stationplan_api import StationplanResult
from cruiseplan.cli.stationplan import main


class TestStationplanThinCLI:
    """Test suite for thin CLI stationplan functionality."""

    def test_list_mode_success(self):
        """Test list mode calls stationplan_list API correctly."""
        args = argparse.Namespace(
            schedule=Path("test_schedule.nc"),
            list=True,
            forecast=False,
            tex=False,
            waypoints=False,
            output=None,
            output_dir=Path("data"),
        )

        with patch("cruiseplan.cli.stationplan.stationplan_list") as mock_list:
            with patch("pathlib.Path.exists", return_value=True):
                mock_list.return_value = StationplanResult(
                    success=True,
                    message="Listed 5 activities",
                    output="Index  Time    Category  Duration  Name\n0      0.0     station   2.0       STN_001\n",
                )

                # Should not raise exception
                main(args)

                # Verify API was called correctly
                mock_list.assert_called_once_with(Path("test_schedule.nc"))

    def test_forecast_mode_success(self):
        """Test forecast mode calls stationplan_forecast API correctly."""
        args = argparse.Namespace(
            schedule=Path("test_schedule.nc"),
            list=False,
            forecast=True,
            tex=False,
            waypoints=False,
            start_index=10,
            start_time="2026-08-30T14:00:00",
            duration=24.0,
            transit_speed=10.0,
            output=None,
            output_dir=Path("data"),
        )

        with patch("cruiseplan.cli.stationplan.stationplan_forecast") as mock_forecast:
            with patch("pathlib.Path.exists", return_value=True):
                mock_forecast.return_value = StationplanResult(
                    success=True,
                    message="Generated 24h forecast",
                    output="% Forecast output\nSTN_001 14:00 15:30\n",
                )

                # Should not raise exception
                main(args)

                # Verify API was called correctly
                mock_forecast.assert_called_once_with(
                    schedule_file=Path("test_schedule.nc"),
                    start_index=10,
                    start_time="2026-08-30T14:00:00",
                    duration_hours=24.0,
                    transit_speed=10.0,
                )

    def test_api_failure_handling(self):
        """Test handling of API failures."""
        args = argparse.Namespace(
            schedule=Path("test_schedule.nc"),
            list=True,
            forecast=False,
            tex=False,
            waypoints=False,
            output=None,
            output_dir=Path("data"),
        )

        with patch("cruiseplan.cli.stationplan.stationplan_list") as mock_list:
            with patch("pathlib.Path.exists", return_value=True):
                mock_list.return_value = StationplanResult(
                    success=False,
                    message="Schedule file corrupted",
                    output="",
                )

                with patch("sys.exit") as mock_exit:
                    main(args)
                    mock_exit.assert_called_once_with(1)
