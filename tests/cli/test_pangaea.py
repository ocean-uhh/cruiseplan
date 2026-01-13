"""
Test suite for cruiseplan.cli.pangaea command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.pangaea import (
    determine_workflow_mode,
    main,
    validate_lat_lon_bounds,
)


class TestPangaeaThinCLI:
    """Test suite for thin CLI pangaea functionality."""

    def test_minimal_pangaea_command(self):
        """Test minimal pangaea command with required arguments."""
        args = argparse.Namespace(
            query="CTD",
            output_dir="data",
            lat=None,
            lon=None,
            max_results=100,
            rate_limit=1.0,
            merge_campaigns=True,
            verbose=False,
        )

        with patch("cruiseplan.pangaea") as mock_pangaea:
            # Mock successful pangaea response
            mock_pangaea.return_value = cruiseplan.PangaeaResult(
                stations_data=[
                    {
                        "Campaign": "Arctic_CTD_2023",
                        "Stations": [{"lat": 75, "lon": -10}],
                    }
                ],
                files_created=[
                    Path("data/CTD_dois.txt"),
                    Path("data/CTD_stations.pkl"),
                ],
                summary={
                    "query_terms": "CTD",
                    "campaigns_found": 1,
                    "files_generated": 2,
                },
            )

            main(args)

            # Verify API was called with correct arguments
            mock_pangaea.assert_called_once_with(
                query_terms="CTD",
                output_dir="data",
                output=None,
                lat_bounds=None,
                lon_bounds=None,
                max_results=100,
                rate_limit=1.0,
                merge_campaigns=True,
                verbose=False,
            )

    def test_pangaea_with_geographic_bounds(self):
        """Test pangaea command with geographic bounds."""
        args = argparse.Namespace(
            query="temperature",
            output_dir="/custom/output",
            output="arctic_data",
            lat=[70.0, 80.0],
            lon=[-20.0, 10.0],
            max_results=50,
            rate_limit=0.5,
            merge_campaigns=False,
            verbose=True,
        )

        with patch("cruiseplan.pangaea") as mock_pangaea:
            mock_pangaea.return_value = cruiseplan.PangaeaResult(
                stations_data=[
                    {
                        "Campaign": "Arctic_Temp_2022",
                        "Stations": [{"lat": 75, "lon": -5}],
                    }
                ],
                files_created=[
                    Path("/custom/output/arctic_data_dois.txt"),
                    Path("/custom/output/arctic_data_stations.pkl"),
                ],
                summary={
                    "query_terms": "temperature",
                    "campaigns_found": 1,
                    "files_generated": 2,
                },
            )

            main(args)

            mock_pangaea.assert_called_once_with(
                query_terms="temperature",
                output_dir="/custom/output",
                output="arctic_data",
                lat_bounds=[70.0, 80.0],
                lon_bounds=[-20.0, 10.0],
                max_results=50,
                rate_limit=0.5,
                merge_campaigns=False,
                verbose=True,
            )

    def test_pangaea_invalid_lat_bounds(self):
        """Test pangaea command with invalid latitude bounds."""
        args = argparse.Namespace(
            query="CTD",
            lat=[95.0, 100.0],  # Invalid latitudes
            lon=[-10.0, 10.0],
            verbose=False,
        )

        with pytest.raises(SystemExit) as exc_info:
            main(args)

        assert exc_info.value.code == 1

    def test_pangaea_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            query="invalid query", output_dir="data", verbose=False
        )

        with patch("cruiseplan.pangaea") as mock_pangaea:
            mock_pangaea.side_effect = cruiseplan.ValidationError(
                "Invalid query parameters"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_pangaea_runtime_error_handling(self):
        """Test handling of RuntimeError from API."""
        args = argparse.Namespace(query="CTD", output_dir="data", verbose=False)

        with patch("cruiseplan.pangaea") as mock_pangaea:
            mock_pangaea.side_effect = RuntimeError(
                "No DOIs found for the given search criteria"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_pangaea_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(query="CTD", output_dir="data", verbose=False)

        with patch("cruiseplan.pangaea") as mock_pangaea:
            mock_pangaea.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_default_argument_handling(self):
        """Test that missing arguments get proper defaults."""
        # Minimal args - missing optional attributes
        args = argparse.Namespace(
            query="salinity"
            # Missing: output_dir, output, lat, lon, max_results, etc.
        )

        with patch("cruiseplan.pangaea") as mock_pangaea:
            mock_pangaea.return_value = cruiseplan.PangaeaResult(
                stations_data=[{"Campaign": "Test", "Stations": []}],
                files_created=[Path("data/salinity_stations.pkl")],
                summary={"query_terms": "salinity", "campaigns_found": 1},
            )

            main(args)

            # Should use defaults for missing arguments
            mock_pangaea.assert_called_once_with(
                query_terms="salinity",
                output_dir="data",  # default
                output=None,  # default
                lat_bounds=None,  # default
                lon_bounds=None,  # default
                max_results=100,  # default
                rate_limit=1.0,  # default
                merge_campaigns=True,  # default
                verbose=False,  # default
            )


class TestCoordinateBoundsValidation:
    """Test coordinate bounds validation helpers."""

    def test_validate_lat_lon_bounds_valid(self):
        """Test validation with valid bounds."""
        lat_bounds = [70.0, 80.0]
        lon_bounds = [-10.0, 10.0]

        result = validate_lat_lon_bounds(lat_bounds, lon_bounds)
        assert result == (-10.0, 70.0, 10.0, 80.0)

    def test_validate_lat_lon_bounds_invalid_lat_range(self):
        """Test validation with invalid latitude range."""
        lat_bounds = [95.0, 100.0]  # Outside -90 to 90
        lon_bounds = [-10.0, 10.0]

        with pytest.raises(
            ValueError, match="Latitude values must be between -90 and 90"
        ):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)

    def test_validate_lat_lon_bounds_invalid_lat_order(self):
        """Test validation with invalid latitude order."""
        lat_bounds = [80.0, 70.0]  # min > max
        lon_bounds = [-10.0, 10.0]

        with pytest.raises(ValueError, match="min_lat must be less than max_lat"):
            validate_lat_lon_bounds(lat_bounds, lon_bounds)


class TestWorkflowModeDetection:
    """Test workflow mode detection helpers."""

    def test_determine_workflow_mode_search(self):
        """Test workflow mode detection for search mode."""
        args = argparse.Namespace(query="CTD")
        mode = determine_workflow_mode(args)
        assert mode == "search"

    def test_determine_workflow_mode_doi_file(self):
        """Test workflow mode detection for DOI file mode."""
        args = argparse.Namespace(query="CTD", doi_file=Path("test.txt"))
        mode = determine_workflow_mode(args)
        assert mode == "doi_file"


class TestPangaeaResultType:
    """Test the PangaeaResult type for completeness."""

    def test_pangaea_result_success(self):
        """Test PangaeaResult with successful processing."""
        stations_data = [
            {"Campaign": "Arctic_2023", "Stations": [{"lat": 75, "lon": -10}]}
        ]
        result = cruiseplan.PangaeaResult(
            stations_data=stations_data,
            files_created=[Path("dois.txt"), Path("stations.pkl")],
            summary={"campaigns_found": 1, "files_generated": 2},
        )

        assert result.stations_data == stations_data
        assert bool(result) is True
        assert len(result.files_created) == 2
        assert "✅ PANGAEA processing (1 stations) complete" in str(result)
        assert "(2 files)" in str(result)

    def test_pangaea_result_failure(self):
        """Test PangaeaResult with failed processing."""
        result = cruiseplan.PangaeaResult(
            stations_data=None,
            files_created=[],
            summary={"campaigns_found": 0, "files_generated": 0},
        )

        assert result.stations_data is None
        assert bool(result) is False
        assert len(result.files_created) == 0
        assert "❌ PANGAEA processing failed" in str(result)
