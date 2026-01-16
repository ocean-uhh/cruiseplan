"""
Test suite for cruiseplan.cli.enrich command - Thin CLI Architecture.

This module implements streamlined tests for the thin CLI layer that only
tests argument passing to the API. Business logic testing happens in API tests.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.cli.enrich import main


class TestEnrichThinCLI:
    """Test suite for thin CLI enrich functionality."""

    def test_minimal_enrich_command(self):
        """Test minimal enrich command with required arguments."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            add_depths=False,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=False,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            # Mock successful API response
            mock_enrich.return_value = cruiseplan.EnrichResult(
                output_file=Path("data/test_enriched.yaml"),
                files_created=[Path("data/test_enriched.yaml")],
                summary={"stations_enriched": 3},
            )

            main(args)

            # Verify API was called with correct arguments
            mock_enrich.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",
                output=None,
                add_depths=False,
                add_coords=False,
                expand_sections=False,
                bathy_source="etopo2022",
                bathy_dir="data",
                verbose=False,
            )

    def test_enrich_with_all_flags_enabled(self):
        """Test enrich command with all enrichment flags enabled."""
        args = argparse.Namespace(
            config_file=Path("tc1_single.yaml"),
            output_dir=Path("custom_output"),
            output="custom_base",
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            bathy_source="gebco2025",
            bathy_dir=Path("custom_bathy"),
            verbose=True,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.return_value = cruiseplan.EnrichResult(
                output_file=Path("custom_output/custom_base_enriched.yaml"),
                files_created=[Path("custom_output/custom_base_enriched.yaml")],
                summary={"stations_enriched": 5, "depths_added": 5},
            )

            main(args)

            mock_enrich.assert_called_once_with(
                config_file=Path("tc1_single.yaml"),
                output_dir="custom_output",
                output="custom_base",
                add_depths=True,
                add_coords=True,
                expand_sections=True,
                bathy_source="gebco2025",
                bathy_dir="custom_bathy",
                verbose=True,
            )

    def test_enrich_validation_error_handling(self):
        """Test handling of ValidationError from API."""
        args = argparse.Namespace(
            config_file=Path("invalid.yaml"),
            output_dir=Path("data"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=False,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.side_effect = cruiseplan.ValidationError(
                "Invalid YAML configuration: missing cruise_name"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should exit with code 1
            assert exc_info.value.code == 1

    def test_enrich_file_error_handling(self):
        """Test handling of FileError from API."""
        args = argparse.Namespace(
            config_file=Path("nonexistent.yaml"),
            output_dir=Path("data"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=False,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.side_effect = cruiseplan.FileError(
                "Configuration file not found"
            )

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_enrich_file_not_found_error_handling(self):
        """Test handling of FileNotFoundError."""
        args = argparse.Namespace(
            config_file=Path("missing.yaml"),
            output_dir=Path("data"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=False,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.side_effect = FileNotFoundError("No such file or directory")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_enrich_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=False,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_enrich_unexpected_error_handling(self):
        """Test handling of unexpected errors."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=False,
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            assert exc_info.value.code == 1

    def test_enrich_unexpected_error_with_verbose(self):
        """Test handling of unexpected errors with verbose traceback."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir=Path("data"),
            add_depths=True,
            add_coords=False,
            expand_sections=False,
            bathy_source="etopo2022",
            bathy_dir=Path("data"),
            verbose=True,  # Should trigger traceback printing
        )

        with (
            patch("cruiseplan.enrich") as mock_enrich,
            patch("traceback.print_exc") as mock_traceback,
        ):
            mock_enrich.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                main(args)

            # Should print traceback when verbose=True
            mock_traceback.assert_called_once()
            assert exc_info.value.code == 1

    def test_default_argument_handling(self):
        """Test that missing arguments get proper defaults."""
        # Minimal args - missing optional attributes
        args = argparse.Namespace(
            config_file=Path("test.yaml")
            # Missing: output_dir, output, add_depths, etc.
        )

        with patch("cruiseplan.enrich") as mock_enrich:
            mock_enrich.return_value = cruiseplan.EnrichResult(
                output_file=Path("data/test_enriched.yaml"),
                files_created=[Path("data/test_enriched.yaml")],
                summary={},
            )

            main(args)

            # Should use defaults for missing arguments
            mock_enrich.assert_called_once_with(
                config_file=Path("test.yaml"),
                output_dir="data",  # default
                output=None,  # default
                add_depths=False,  # default
                add_coords=False,  # default
                expand_sections=False,  # default
                bathy_source="etopo2022",  # default
                bathy_dir="data/bathymetry",  # default
                verbose=False,  # default
            )


class TestEnrichResultType:
    """Test the EnrichResult type for completeness."""

    def test_enrich_result_creation(self):
        """Test EnrichResult can be created and used."""
        result = cruiseplan.EnrichResult(
            output_file=Path("test.yaml"),
            files_created=[Path("test.yaml"), Path("other.yaml")],
            summary={"stations": 5},
        )

        assert result.output_file == Path("test.yaml")
        assert len(result.files_created) == 2
        assert result.summary["stations"] == 5
        assert "✅ Enrichment complete" in str(result)
        assert "(2 files)" in str(result)
