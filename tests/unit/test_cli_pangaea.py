"""
Test suite for cruiseplan.cli.pangaea module (unified search + download).

This module tests the unified PANGAEA CLI functionality that combines both
search and DOI file processing modes, base filename output strategy,
and backward compatibility with deprecated parameters.
"""

import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest


@pytest.fixture
def setup_stdout_logging():
    """Set up logging to stdout for tests that capture output with capsys."""
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True
    )
    yield
    # Reset logging after test
    logging.getLogger().handlers.clear()


from cruiseplan.cli.pangaea import (
    determine_workflow_mode,
    main,
    save_doi_list,
    search_pangaea_datasets,
    validate_dois,
    validate_lat_lon_bounds,
)
from cruiseplan.cli.utils import CLIError


class TestWorkflowModeDetection:
    """Test suite for determine_workflow_mode function."""

    def test_search_mode_with_lat_lon(self):
        """Test search mode detection when lat/lon provided."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD temperature"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]

        result = determine_workflow_mode(mock_args)
        assert result == "search"

    def test_doi_file_mode_with_existing_txt_file(self):
        """Test DOI file mode detection with existing .txt file."""
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
            Path(tmp_path).unlink()  # Clean up

    def test_search_mode_with_query_string(self):
        """Test search mode detection with query string (no file extension)."""
        mock_args = MagicMock()
        mock_args.query_or_file = "Arctic Ocean CTD"
        mock_args.lat = None
        mock_args.lon = None

        result = determine_workflow_mode(mock_args)
        assert result == "search"

    def test_search_mode_default_when_ambiguous(self):
        """Test default to search mode when input is ambiguous."""
        mock_args = MagicMock()
        mock_args.query_or_file = "nonexistent_file.txt"  # File doesn't exist
        mock_args.lat = None
        mock_args.lon = None

        result = determine_workflow_mode(mock_args)
        assert result == "search"


class TestLatLonValidation:
    """Test suite for validate_lat_lon_bounds function (inherited from pandoi)."""

    def test_valid_standard_format(self):
        """Test valid -180 to 180 format."""
        result = validate_lat_lon_bounds([50, 60], [-90, -30])
        assert result == (-90, 50, -30, 60)

    def test_valid_360_format(self):
        """Test valid 0 to 360 format."""
        result = validate_lat_lon_bounds([50, 60], [270, 330])
        assert result == (270, 50, 330, 60)

    def test_valid_360_crossing_meridian(self):
        """Test valid 0-360 format crossing 0° meridian."""
        result = validate_lat_lon_bounds([50, 60], [350, 10])
        assert result == (350, 50, 10, 60)

    def test_mixed_format_error(self):
        """Test mixed longitude formats are rejected."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([50, 60], [-90, 240])

        assert "Cannot mix formats" in str(excinfo.value)

    def test_invalid_latitude_range(self):
        """Test invalid latitude values."""
        with pytest.raises(CLIError) as excinfo:
            validate_lat_lon_bounds([-100, 60], [-90, -30])

        assert "Latitude must be between -90 and 90" in str(excinfo.value)


class TestSearchMode:
    """Test suite for search mode functionality."""

    def test_search_mode_basic_workflow(self, caplog):
        """Test basic search mode workflow with query and bounds."""
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

        mock_dois = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
        mock_datasets = [{"name": "Dataset1"}, {"name": "Dataset2"}]

        with (
            patch("cruiseplan.cli.pangaea.setup_logging") as mock_setup,
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch(
                "cruiseplan.cli.pangaea.search_pangaea_datasets", return_value=mock_dois
            ),
            patch("cruiseplan.cli.pangaea.save_doi_list"),
            patch("cruiseplan.cli.pangaea.validate_dois", return_value=mock_dois),
            patch(
                "cruiseplan.cli.pangaea.fetch_pangaea_data", return_value=mock_datasets
            ),
            patch("cruiseplan.cli.pangaea.save_pangaea_pickle"),
        ):

            with caplog.at_level(logging.INFO):
                main(mock_args)

            # Check that key messages were logged
            assert "🌊 CRUISEPLAN PANGAEA DATA PROCESSOR" in caplog.text
            assert "📋 Mode: Search + Download" in caplog.text
            assert "🔍 Query: 'CTD temperature'" in caplog.text

    def test_search_mode_missing_lat_lon_error(self):
        """Test search mode error when lat/lon not provided."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD temperature"
        mock_args.lat = None
        mock_args.lon = [50, 60]  # Only lon provided
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
        ):

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_search_mode_auto_generated_base_name(self):
        """Test search mode with auto-generated base filename."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD North Atlantic!"  # Special characters
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 10
        mock_args.output_dir = Path("data")
        mock_args.output = None  # No base name provided
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.output_file = None
        mock_args.verbose = False

        mock_dois = ["10.1594/PANGAEA.12345"]
        mock_datasets = [{"name": "Dataset1"}]

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch(
                "cruiseplan.cli.pangaea.search_pangaea_datasets", return_value=mock_dois
            ) as mock_search,
            patch("cruiseplan.cli.pangaea.save_doi_list") as mock_save_dois,
            patch("cruiseplan.cli.pangaea.validate_dois", return_value=mock_dois),
            patch(
                "cruiseplan.cli.pangaea.fetch_pangaea_data", return_value=mock_datasets
            ),
            patch("cruiseplan.cli.pangaea.save_pangaea_pickle"),
        ):

            main(mock_args)

            # Check that save_doi_list was called with sanitized filename
            mock_save_dois.assert_called_once()
            call_args = mock_save_dois.call_args[0]
            output_path = call_args[1]
            assert "CTD_North_Atlantic_dois.txt" in str(output_path)

    def test_search_mode_limit_validation(self):
        """Test search mode limit validation."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 0  # Invalid limit
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
        ):

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_search_mode_large_limit_warning(self, capsys):
        """Test search mode warning for large limits."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 150  # Large limit
        mock_args.output_dir = Path("data")
        mock_args.output = "test"
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch("cruiseplan.cli.pangaea.search_pangaea_datasets", return_value=[]),
            pytest.raises(SystemExit),
        ):  # Will exit due to no DOIs found

            main(mock_args)

            captured = capsys.readouterr()
            assert "Large limit values may result in slow searches" in captured.out


class TestDoiFileMode:
    """Test suite for DOI file mode functionality."""

    def test_doi_file_mode_basic_workflow(self, caplog):
        """Test basic DOI file mode workflow."""
        with tempfile.NamedTemporaryFile(
            suffix="_dois.txt", mode="w", delete=False
        ) as tmp:
            tmp.write("10.1594/PANGAEA.12345\n10.1594/PANGAEA.67890\n")
            tmp.flush()
            tmp_path = tmp.name

        try:
            mock_args = MagicMock()
            mock_args.query_or_file = tmp_path
            mock_args.output_dir = Path("data")
            mock_args.output = None  # Auto-generate from input filename
            mock_args.rate_limit = 1.0
            mock_args.merge_campaigns = True
            mock_args.output_file = None
            mock_args.verbose = False

            mock_dois = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
            mock_datasets = [{"name": "Dataset1"}, {"name": "Dataset2"}]

            with (
                patch("cruiseplan.cli.pangaea.setup_logging"),
                patch(
                    "cruiseplan.cli.pangaea.determine_workflow_mode",
                    return_value="doi_file",
                ),
                patch(
                    "cruiseplan.cli.pangaea.validate_input_file",
                    return_value=Path(tmp_path),
                ),
                patch("cruiseplan.cli.pangaea.read_doi_list", return_value=mock_dois),
                patch("cruiseplan.cli.pangaea.validate_dois", return_value=mock_dois),
                patch(
                    "cruiseplan.cli.pangaea.fetch_pangaea_data",
                    return_value=mock_datasets,
                ),
                patch("cruiseplan.cli.pangaea.save_pangaea_pickle"),
            ):

                with caplog.at_level(logging.INFO):
                    main(mock_args)

                # Check that key messages were logged
                assert "📋 Mode: DOI File Processing" in caplog.text
        finally:
            Path(tmp_path).unlink()

    def test_doi_file_mode_auto_base_name_generation(self):
        """Test DOI file mode with automatic base name generation from input file."""
        with tempfile.NamedTemporaryFile(
            suffix="_dois.txt", mode="w", delete=False
        ) as tmp:
            tmp.write("10.1594/PANGAEA.12345\n")
            tmp.flush()
            tmp_path = tmp.name

        try:
            mock_args = MagicMock()
            mock_args.query_or_file = tmp_path
            mock_args.output_dir = Path("data")
            mock_args.output = None  # Should auto-generate from filename
            mock_args.rate_limit = 1.0
            mock_args.merge_campaigns = True
            mock_args.output_file = None
            mock_args.verbose = False

            expected_base = Path(tmp_path).stem.replace("_dois", "")
            expected_output = Path("data") / f"{expected_base}_stations.pkl"

            with (
                patch("cruiseplan.cli.pangaea.setup_logging"),
                patch(
                    "cruiseplan.cli.pangaea.determine_workflow_mode",
                    return_value="doi_file",
                ),
                patch(
                    "cruiseplan.cli.pangaea.validate_input_file",
                    return_value=Path(tmp_path),
                ),
                patch(
                    "cruiseplan.cli.pangaea.read_doi_list",
                    return_value=["10.1594/PANGAEA.12345"],
                ),
                patch(
                    "cruiseplan.cli.pangaea.validate_dois",
                    return_value=["10.1594/PANGAEA.12345"],
                ),
                patch(
                    "cruiseplan.cli.pangaea.fetch_pangaea_data",
                    return_value=[{"name": "Dataset"}],
                ),
                patch("cruiseplan.cli.pangaea.save_pangaea_pickle") as mock_save,
            ):

                main(mock_args)

                # Verify save_pangaea_pickle was called with expected path
                mock_save.assert_called_once()
                call_args = mock_save.call_args[0]
                assert expected_output == call_args[1]
        finally:
            Path(tmp_path).unlink()


class TestBackwardCompatibility:
    """Test suite for backward compatibility features."""

    def test_deprecated_output_file_parameter_warning(self, caplog):
        """Test that deprecated --output-file shows warning."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 10
        mock_args.output_dir = Path("data")
        mock_args.output = None
        mock_args.output_file = Path(
            "/custom/path/stations.pkl"
        )  # Deprecated parameter
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch(
                "cruiseplan.cli.pangaea.search_pangaea_datasets",
                return_value=["10.1594/PANGAEA.12345"],
            ),
            patch("cruiseplan.cli.pangaea.save_doi_list"),
            patch(
                "cruiseplan.cli.pangaea.validate_dois",
                return_value=["10.1594/PANGAEA.12345"],
            ),
            patch(
                "cruiseplan.cli.pangaea.fetch_pangaea_data",
                return_value=[{"name": "Dataset"}],
            ),
            patch("cruiseplan.cli.pangaea.save_pangaea_pickle"),
        ):

            with caplog.at_level(logging.WARNING):
                main(mock_args)

            assert "WARNING: '--output-file' is deprecated" in caplog.text
            assert "will be removed in v0.3.0" in caplog.text

    def test_deprecated_output_file_search_mode_functionality(self):
        """Test that deprecated --output-file still works in search mode."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 10
        mock_args.output_dir = Path("data")
        mock_args.output = None
        mock_args.output_file = Path("/custom/path/results.pkl")
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch(
                "cruiseplan.cli.pangaea.search_pangaea_datasets",
                return_value=["10.1594/PANGAEA.12345"],
            ),
            patch("cruiseplan.cli.pangaea.save_doi_list") as mock_save_dois,
            patch(
                "cruiseplan.cli.pangaea.validate_dois",
                return_value=["10.1594/PANGAEA.12345"],
            ),
            patch(
                "cruiseplan.cli.pangaea.fetch_pangaea_data",
                return_value=[{"name": "Dataset"}],
            ),
            patch("cruiseplan.cli.pangaea.save_pangaea_pickle") as mock_save_pkl,
        ):

            main(mock_args)

            # Verify that stations file uses custom path
            mock_save_pkl.assert_called_once()
            stations_file = mock_save_pkl.call_args[0][1]
            assert stations_file == Path("/custom/path/results.pkl")

            # Verify DOI file is derived from stations file path
            mock_save_dois.assert_called_once()
            dois_file = mock_save_dois.call_args[0][1]
            assert "results_dois.txt" in str(dois_file)

    def test_deprecated_output_file_doi_mode_functionality(self):
        """Test that deprecated --output-file still works in DOI file mode."""
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as tmp:
            tmp.write("10.1594/PANGAEA.12345\n")
            tmp.flush()
            tmp_path = tmp.name

        try:
            mock_args = MagicMock()
            mock_args.query_or_file = tmp_path
            mock_args.output_dir = Path("data")
            mock_args.output = None
            mock_args.output_file = Path("/custom/path/custom_stations.pkl")
            mock_args.rate_limit = 1.0
            mock_args.merge_campaigns = True
            mock_args.verbose = False

            with (
                patch("cruiseplan.cli.pangaea.setup_logging"),
                patch(
                    "cruiseplan.cli.pangaea.determine_workflow_mode",
                    return_value="doi_file",
                ),
                patch(
                    "cruiseplan.cli.pangaea.validate_input_file",
                    return_value=Path(tmp_path),
                ),
                patch(
                    "cruiseplan.cli.pangaea.read_doi_list",
                    return_value=["10.1594/PANGAEA.12345"],
                ),
                patch(
                    "cruiseplan.cli.pangaea.validate_dois",
                    return_value=["10.1594/PANGAEA.12345"],
                ),
                patch(
                    "cruiseplan.cli.pangaea.fetch_pangaea_data",
                    return_value=[{"name": "Dataset"}],
                ),
                patch("cruiseplan.cli.pangaea.save_pangaea_pickle") as mock_save,
            ):

                main(mock_args)

                # Verify custom output file path is used
                mock_save.assert_called_once()
                output_file = mock_save.call_args[0][1]
                assert output_file == Path("/custom/path/custom_stations.pkl")
        finally:
            Path(tmp_path).unlink()


class TestErrorHandling:
    """Test suite for error handling scenarios."""

    def test_no_dois_found_in_search(self):
        """Test handling when search returns no DOIs."""
        mock_args = MagicMock()
        mock_args.query_or_file = "nonexistent data"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 10
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch("cruiseplan.cli.pangaea.search_pangaea_datasets", return_value=[]),
        ):

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_no_datasets_retrieved(self, caplog):
        """Test handling when no datasets are retrieved."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.limit = 10
        mock_args.output_dir = Path("data")
        mock_args.output = "test"
        mock_args.rate_limit = 1.0
        mock_args.merge_campaigns = True
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode", return_value="search"
            ),
            patch(
                "cruiseplan.cli.pangaea.search_pangaea_datasets",
                return_value=["10.1594/PANGAEA.12345"],
            ),
            patch("cruiseplan.cli.pangaea.save_doi_list"),
            patch(
                "cruiseplan.cli.pangaea.validate_dois",
                return_value=["10.1594/PANGAEA.12345"],
            ),
            patch("cruiseplan.cli.pangaea.fetch_pangaea_data", return_value=[]),
        ):  # No datasets returned

            with caplog.at_level(logging.WARNING):
                main(mock_args)

            assert "No datasets retrieved" in caplog.text

    def test_keyboard_interrupt_handling(self, caplog):
        """Test keyboard interrupt handling."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode",
                side_effect=KeyboardInterrupt(),
            ),
        ):

            with pytest.raises(SystemExit):
                with caplog.at_level(logging.INFO):
                    main(mock_args)

            assert "Operation cancelled by user" in caplog.text

    def test_cli_error_handling(self, caplog):
        """Test CLIError handling."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.lat = [50, 60]
        mock_args.lon = [-50, -30]
        mock_args.output_file = None
        mock_args.verbose = False

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode",
                side_effect=CLIError("Test error"),
            ),
        ):

            with pytest.raises(SystemExit):
                with caplog.at_level(logging.ERROR):
                    main(mock_args)

            assert "❌ Test error" in caplog.text

    def test_unexpected_exception_handling(self, caplog):
        """Test unexpected exception handling."""
        mock_args = MagicMock()
        mock_args.query_or_file = "CTD"
        mock_args.verbose = False
        mock_args.output_file = None

        with (
            patch("cruiseplan.cli.pangaea.setup_logging"),
            patch(
                "cruiseplan.cli.pangaea.determine_workflow_mode",
                side_effect=RuntimeError("Unexpected error"),
            ),
        ):

            with pytest.raises(SystemExit):
                with caplog.at_level(logging.ERROR):
                    main(mock_args)

            assert "❌ Unexpected error: Unexpected error" in caplog.text


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_search_pangaea_datasets(self):
        """Test search_pangaea_datasets function."""
        mock_datasets = [
            {"doi": "10.1594/PANGAEA.12345"},
            {"doi": "10.1594/PANGAEA.67890"},
            {"name": "No DOI dataset"},  # No DOI field
        ]

        with patch("cruiseplan.cli.pangaea.PangaeaManager") as mock_manager_class:
            mock_manager = mock_manager_class.return_value
            mock_manager.search.return_value = mock_datasets

            result = search_pangaea_datasets("CTD", bbox=(-50, 50, -30, 60), limit=10)

            assert result == ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
            mock_manager.search.assert_called_once_with(
                query="CTD", bbox=(-50, 50, -30, 60), limit=10
            )

    def test_save_doi_list(self):
        """Test save_doi_list function."""
        dois = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]
        output_path = Path("/tmp/test_dois.txt")

        with (
            patch("builtins.open", mock_open()) as mock_file,
            patch("pathlib.Path.mkdir"),
        ):

            save_doi_list(dois, output_path)

            mock_file.assert_called_once_with(output_path, "w")
            handle = mock_file()
            handle.write.assert_any_call("10.1594/PANGAEA.12345\n")
            handle.write.assert_any_call("10.1594/PANGAEA.67890\n")

    def test_validate_dois(self):
        """Test validate_dois function."""
        input_dois = [
            "10.1594/PANGAEA.12345",
            "https://doi.org/10.1594/PANGAEA.67890",
            "doi:10.1594/PANGAEA.11111",
            "invalid_doi",
            "  10.1594/PANGAEA.22222  ",  # With whitespace
        ]

        with patch("cruiseplan.data.pangaea._is_valid_doi") as mock_valid:
            # Mock validation: return True for proper DOI format, False for invalid
            def validate_side_effect(doi):
                return doi.startswith("10.1594/PANGAEA.")

            mock_valid.side_effect = validate_side_effect

            result = validate_dois(input_dois)

            expected = [
                "10.1594/PANGAEA.12345",
                "10.1594/PANGAEA.67890",  # Cleaned from URL
                "10.1594/PANGAEA.11111",  # Cleaned from doi: prefix
                "10.1594/PANGAEA.22222",  # Cleaned whitespace
            ]
            assert result == expected
