"""
Test suite for cruiseplan.cli.forecast command - Thin CLI Architecture.

Tests the thin CLI layer argument passing to the API. Business logic
testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

from cruiseplan.api.stationplan_api import StationplanResult
from cruiseplan.cli.forecast import run


class TestForecastThinCLI:
    """Test suite for thin CLI forecast functionality."""

    def test_forecast_mode_success(self):
        """Test forecast mode calls stationplan_forecast API correctly."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
            start_index=10,
            start_time="2026-08-30T14:00:00",
            duration=24.0,
            transit_speed=10.0,
            format="text",
            output=None,
            output_dir=Path("data"),
            current_position=None,
        )

        with patch("cruiseplan.cli.forecast.stationplan_forecast") as mock_forecast:
            with patch("pathlib.Path.exists", return_value=True):
                mock_forecast.return_value = StationplanResult(
                    success=True,
                    message="Generated 24h forecast",
                    output="% Forecast output\nSTN_001 14:00 15:30\n",
                )

                run(args)

                mock_forecast.assert_called_once_with(
                    schedule_file=Path("test_schedule.nc"),
                    start_index=10,
                    start_time="2026-08-30T14:00:00",
                    duration_hours=24.0,
                    transit_speed=10.0,
                )

    def test_xor_validation_index_only(self):
        """Test that --start-index without --start-time gives a clean error."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
            start_index=5,
            start_time=None,
            duration=24.0,
            transit_speed=10.0,
            format="text",
            output=None,
            output_dir=Path("."),
            current_position=None,
        )

        with patch("pathlib.Path.exists", return_value=True):
            with patch("sys.exit") as mock_exit:
                run(args)
                mock_exit.assert_called_once_with(1)

    def test_xor_validation_time_only(self):
        """Test that --start-time without --start-index gives a clean error."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
            start_index=None,
            start_time="2026-08-30T14:00:00",
            duration=24.0,
            transit_speed=10.0,
            format="text",
            output=None,
            output_dir=Path("."),
            current_position=None,
        )

        with patch("pathlib.Path.exists", return_value=True):
            with patch("sys.exit") as mock_exit:
                run(args)
                mock_exit.assert_called_once_with(1)

    def test_static_tex_mode(self):
        """Test static TeX mode (no start params) calls stationplan_tex."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
            start_index=None,
            start_time=None,
            format="tex",
            output=None,
            output_dir=Path("data"),
            logo=None,
            number=None,
            title=None,
        )

        with patch("cruiseplan.cli.forecast.stationplan_tex") as mock_tex:
            with patch("pathlib.Path.exists", return_value=True):
                mock_tex.return_value = StationplanResult(
                    success=True,
                    message="Generated TeX table",
                    output="station_plan.tex",
                )

                run(args)

                mock_tex.assert_called_once()

    def test_api_failure_handling(self):
        """Test handling of API failures."""
        args = argparse.Namespace(
            schedule_file=Path("test_schedule.nc"),
            start_index=0,
            start_time="2026-08-30T14:00:00",
            duration=24.0,
            transit_speed=10.0,
            format="text",
            output=None,
            output_dir=Path("data"),
            current_position=None,
        )

        with patch("cruiseplan.cli.forecast.stationplan_forecast") as mock_forecast:
            with patch("pathlib.Path.exists", return_value=True):
                mock_forecast.return_value = StationplanResult(
                    success=False,
                    message="Schedule file corrupted",
                    output="",
                )

                with patch("sys.exit") as mock_exit:
                    run(args)
                    mock_exit.assert_called_once_with(1)
