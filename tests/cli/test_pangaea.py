"""
Tests for PANGAEA CLI command.
"""

import pickle
import unittest.mock
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.pangaea import (
    fetch_pangaea_data,
    main,
    save_pangaea_pickle,
    validate_dois,
)
from cruiseplan.cli.utils import CLIError


class TestDoiValidation:
    """Test DOI validation functionality."""

    def test_validate_dois_basic(self):
        """Test basic DOI validation."""
        dois = [
            "10.1594/PANGAEA.12345",
            "doi:10.1594/PANGAEA.67890",
            "https://doi.org/10.1594/PANGAEA.11111",
        ]

        result = validate_dois(dois)
        expected = [
            "10.1594/PANGAEA.12345",
            "10.1594/PANGAEA.67890",
            "10.1594/PANGAEA.11111",
        ]
        assert result == expected

    def test_validate_dois_invalid(self):
        """Test validation filters invalid DOIs."""
        dois = [
            "10.1594/PANGAEA.12345",
            "invalid-doi",
            "not-a-doi-at-all",
            "10.1594/PANGAEA.67890",
        ]

        result = validate_dois(dois)
        expected = [
            "10.1594/PANGAEA.12345",
            "10.1594/PANGAEA.67890",
        ]
        assert result == expected

    def test_validate_dois_empty(self):
        """Test validation fails with no valid DOIs."""
        dois = ["invalid-doi", "not-a-doi"]

        with pytest.raises(CLIError, match="No valid DOIs found"):
            validate_dois(dois)


class TestPangaeaDataFetching:
    """Test PANGAEA data fetching with mocks."""

    @patch("cruiseplan.cli.pangaea.PangaeaManager")
    def test_fetch_pangaea_data_success(self, mock_pangaea_class):
        """Test successful data fetching."""
        # Setup mocks
        mock_pangaea = MagicMock()
        mock_pangaea_class.return_value = mock_pangaea

        # Mock fetched datasets
        mock_datasets = [
            {"label": "Campaign1", "events": [{"lat": 50.0, "lon": -10.0}]},
            {"label": "Campaign2", "events": [{"lat": 51.0, "lon": -11.0}]},
        ]
        mock_pangaea.fetch_datasets.return_value = mock_datasets

        dois = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]

        result = fetch_pangaea_data(dois, rate_limit=2.0, merge_campaigns=True)

        # Verify calls
        mock_pangaea.fetch_datasets.assert_called_once_with(
            doi_list=dois,
            rate_limit=2.0,
            merge_campaigns=True,
            progress_callback=unittest.mock.ANY,
        )
        assert result == mock_datasets

    @patch("cruiseplan.cli.pangaea.PangaeaManager")
    def test_fetch_pangaea_data_with_errors(self, mock_pangaea_class):
        """Test data fetching handles individual errors."""
        # Setup mocks
        mock_pangaea = MagicMock()
        mock_pangaea_class.return_value = mock_pangaea

        # Mock some successful results despite errors
        mock_result = [{"label": "Campaign1", "events": []}]
        mock_pangaea.fetch_datasets.return_value = mock_result

        dois = ["10.1594/PANGAEA.12345", "10.1594/PANGAEA.67890"]

        result = fetch_pangaea_data(dois, rate_limit=10.0, merge_campaigns=False)

        # Verify the core function was called properly
        mock_pangaea.fetch_datasets.assert_called_once_with(
            doi_list=dois,
            rate_limit=10.0,
            merge_campaigns=False,
            progress_callback=unittest.mock.ANY,
        )
        assert result == mock_result


class TestPangaeaPickleSaving:
    """Test saving PANGAEA data to pickle files."""

    def test_save_pangaea_pickle(self, tmp_path):
        """Test saving datasets to pickle file."""
        datasets = [
            {"label": "Campaign1", "events": [{"lat": 50.0, "lon": -10.0}]},
            {"label": "Campaign2", "events": [{"lat": 51.0, "lon": -11.0}]},
        ]

        output_file = tmp_path / "test_data.pkl"

        save_pangaea_pickle(datasets, output_file)

        # Verify file exists and content
        assert output_file.exists()

        with open(output_file, "rb") as f:
            loaded_data = pickle.load(f)

        assert loaded_data == datasets

    def test_save_pangaea_pickle_creates_directory(self, tmp_path):
        """Test saving creates parent directories."""
        output_file = tmp_path / "subdir" / "data.pkl"
        datasets = [{"label": "Test"}]

        save_pangaea_pickle(datasets, output_file)

        assert output_file.exists()
        assert output_file.parent.exists()


class TestMainCommand:
    """Test main command integration."""

    @patch("cruiseplan.cli.pangaea.fetch_pangaea_data")
    @patch("cruiseplan.cli.pangaea.save_pangaea_pickle")
    @patch("cruiseplan.cli.pangaea.read_doi_list")
    @patch("cruiseplan.cli.pangaea.validate_dois")
    @patch("cruiseplan.cli.pangaea.validate_input_file")
    @patch("cruiseplan.cli.utils.validate_output_path")
    def test_main_success(
        self,
        mock_validate_output,
        mock_validate_input,
        mock_validate_dois,
        mock_read_dois,
        mock_save,
        mock_fetch,
    ):
        """Test successful main command execution."""
        import tempfile

        # Setup mocks
        mock_validate_input.return_value = Path("/test/dois.txt")
        mock_validate_output.return_value = Path("/test/output.pkl")
        mock_read_dois.return_value = ["10.1594/PANGAEA.12345"]
        mock_validate_dois.return_value = ["10.1594/PANGAEA.12345"]
        mock_fetch.return_value = [{"label": "Campaign1"}]

        # Create temporary DOI file for workflow detection
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("10.1594/PANGAEA.12345\n")
            temp_doi_file = f.name

        try:
            # Create args (new unified format for DOI file mode)
            args = Namespace(
                query_or_file=temp_doi_file,
                output_dir=Path("tests_output"),
                output_file=None,
                rate_limit=1.0,
                merge_campaigns=True,
                verbose=False,
                quiet=False,
                lat=None,  # Not provided in DOI file mode
                lon=None,  # Not provided in DOI file mode
                limit=None,  # Not used in DOI file mode
            )

            # Should not raise exception
            main(args)
        finally:
            # Clean up temporary file
            import os

            os.unlink(temp_doi_file)

        # Verify calls
        mock_validate_input.assert_called_once()
        mock_read_dois.assert_called_once()
        mock_validate_dois.assert_called_once()
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()

    @patch("cruiseplan.cli.pangaea.validate_input_file")
    def test_main_file_not_found(self, mock_validate_input):
        """Test main command with file not found."""
        mock_validate_input.side_effect = CLIError("File not found")

        args = Namespace(
            query_or_file="nonexistent.txt",
            output_dir=Path("tests_output"),
            output_file=None,
            rate_limit=1.0,
            merge_campaigns=True,
            verbose=False,
            lat=None,
            lon=None,
            limit=None,
        )

        with pytest.raises(SystemExit):
            main(args)

    def test_main_keyboard_interrupt(self):
        """Test main command handles keyboard interrupt."""
        args = Namespace(
            query_or_file="dois.txt",
            output_dir=Path("tests_output"),
            output_file=None,
            rate_limit=1.0,
            merge_campaigns=True,
            verbose=False,
            lat=None,
            lon=None,
            limit=None,
        )

        with patch("cruiseplan.cli.pangaea.validate_input_file") as mock_validate:
            mock_validate.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)


class TestCommandLineExecution:
    """Test command can be executed directly."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import pangaea

        assert hasattr(pangaea, "main")
        assert hasattr(pangaea, "fetch_pangaea_data")
        assert hasattr(pangaea, "validate_dois")
        assert hasattr(pangaea, "save_pangaea_pickle")
