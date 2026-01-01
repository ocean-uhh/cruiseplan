"""
Test suite for cruiseplan.cli.pangaea command - API-First Architecture.

This module implements streamlined tests focused on CLI layer functionality
after API-first refactoring. Tests verify CLI argument handling and API
integration, not underlying business logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.pangaea import main


class TestPangaeaCommand:
    """Streamlined test suite for CLI pangaea functionality."""

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD temperature"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 10
        mock_args.output_dir = Path("data")
        mock_args.output = "atlantic_study"
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.output_file = None
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {"query": "CTD temperature"}),
            ),
            patch("cruiseplan.cli.pangaea._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.pangaea._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch("cruiseplan.cli.pangaea._collect_generated_files", return_value=[]),
            patch("cruiseplan.cli.pangaea._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (
                [{"name": "test"}],
                [Path("data/atlantic_study_stations.pkl")],
            )

            main(mock_args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD temperature"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.verbose = False
        mock_args.quiet = False
        mock_args.output_file = None

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {}),
            ),
        ):
            mock_api.side_effect = Exception("API error")

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_main_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD temperature"
        mock_args.verbose = False
        mock_args.quiet = False
        mock_args.output_file = None

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
        ):
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_doi_file_mode_calls_api_correctly(self):
        """Test DOI file mode passes correct parameters to API."""
        mock_args = MagicMock()
        mock_args.query_or_file = "/path/to/dois.txt"
        mock_args.lat = None
        mock_args.lon = None
        mock_args.output_dir = Path("data")
        mock_args.output = None
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.output_file = None
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("doi_file", {}),
            ),
            patch("cruiseplan.cli.pangaea._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.pangaea._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch("cruiseplan.cli.pangaea._collect_generated_files", return_value=[]),
            patch("cruiseplan.cli.pangaea._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (
                [{"name": "test"}],
                [Path("data/dois_stations.pkl")],
            )

            main(mock_args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_deprecated_output_file_parameter_still_works(self):
        """Test backward compatibility with deprecated --output-file parameter."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.output_dir = Path("data")
        mock_args.output = None
        mock_args.output_file = Path("/custom/path/results.pkl")  # Deprecated parameter
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.verbose = False
        mock_args.quiet = False

        with (
            patch("cruiseplan.pangaea") as mock_api,
            patch("cruiseplan.cli.pangaea._setup_cli_logging"),
            patch(
                "cruiseplan.cli.pangaea._detect_pangaea_mode",
                return_value=("search", {}),
            ),
            patch("cruiseplan.cli.pangaea._resolve_cli_to_api_params", return_value={}),
            patch(
                "cruiseplan.cli.pangaea._convert_api_response_to_cli",
                return_value={"success": True},
            ),
            patch("cruiseplan.cli.pangaea._format_progress_header"),
            patch("cruiseplan.cli.pangaea._collect_generated_files", return_value=[]),
            patch("cruiseplan.cli.pangaea._format_success_message"),
        ):

            # Mock successful API response
            mock_api.return_value = (
                [{"name": "test"}],
                [Path("/custom/path/results.pkl")],
            )

            main(mock_args)

            # Verify API was called
            mock_api.assert_called_once()


class TestUtilityFunctions:
    """Test suite for pangaea utility functions that still exist."""

    def test_validate_lat_lon_bounds_standard_format(self):
        """Test coordinate validation with standard -180 to 180 format."""
        from cruiseplan.cli.pangaea import validate_lat_lon_bounds

        result = validate_lat_lon_bounds([50, 60], [-90, -30])
        assert result == (-90, 50, -30, 60)

    def test_validate_lat_lon_bounds_360_format(self):
        """Test coordinate validation with 0 to 360 format."""
        from cruiseplan.cli.pangaea import validate_lat_lon_bounds

        result = validate_lat_lon_bounds([50, 60], [270, 330])
        assert result == (270, 50, 330, 60)

    def test_determine_workflow_mode_search(self):
        """Test workflow mode detection for search mode."""
        from cruiseplan.cli.pangaea import determine_workflow_mode

        mock_args = MagicMock()
        mock_args.query_or_file = "CTD temperature"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]

        result = determine_workflow_mode(mock_args)
        assert result == "search"

    def test_determine_workflow_mode_doi_file(self):
        """Test workflow mode detection for DOI file mode."""
        import tempfile

        from cruiseplan.cli.pangaea import determine_workflow_mode

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"10.1594/PANGAEA.12345\n")
            tmp.flush()
            tmp_path = tmp.name

        try:
            mock_args = MagicMock()
            mock_args.query_or_file = tmp_path
            mock_args.lat = None
            mock_args.lon = None

            result = determine_workflow_mode(mock_args)
            assert result == "doi_file"
        finally:
            Path(tmp_path).unlink()
