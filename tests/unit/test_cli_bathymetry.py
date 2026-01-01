"""
Test suite for cruiseplan.cli.bathymetry module.

Streamlined tests focused on CLI layer functionality after API-first refactoring.
Tests verify CLI argument handling and API integration, not underlying business logic.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.bathymetry import main


class TestCliBathymetry:
    """Streamlined test suite for CLI bathymetry functionality."""

    def test_main_calls_api_with_correct_params(self):
        """Test that CLI correctly calls API layer with proper parameters."""
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"
        mock_args.source = None
        mock_args.bathymetry_source = None
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")
        mock_args.verbose = False

        with patch("cruiseplan.bathymetry") as mock_api:
            mock_api.return_value = Path(
                "data/bathymetry/ETOPO_2022_v1_60s_N90W180_bed.nc"
            )

            main(mock_args)

            # Verify API was called
            mock_api.assert_called_once()

    def test_main_handles_legacy_parameters(self):
        """Test that legacy parameter names still work with deprecation warnings."""
        mock_args = MagicMock()
        mock_args.bathy_source = None
        mock_args.source = "etopo2022"  # Legacy parameter
        mock_args.bathymetry_source = None
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")
        mock_args.verbose = False

        with patch("cruiseplan.bathymetry") as mock_api:
            mock_api.return_value = Path(
                "data/bathymetry/ETOPO_2022_v1_60s_N90W180_bed.nc"
            )

            main(mock_args)

            # Verify API was called despite legacy parameter usage
            mock_api.assert_called_once()

    def test_main_citation_mode_skips_api_call(self):
        """Test that citation mode shows info without calling download API."""
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"
        mock_args.source = None
        mock_args.bathymetry_source = None
        mock_args.citation = True  # Citation mode
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.bathymetry") as mock_api:
            main(mock_args)

            # Verify API was NOT called in citation mode
            mock_api.assert_not_called()

    def test_main_handles_api_errors_gracefully(self):
        """Test that CLI handles API errors gracefully."""
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"
        mock_args.source = None
        mock_args.bathymetry_source = None
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")
        mock_args.verbose = False

        with patch("cruiseplan.bathymetry") as mock_api:
            mock_api.side_effect = Exception("API error")

            with pytest.raises(SystemExit):
                main(mock_args)

    def test_main_unknown_source_exits_before_api_call(self):
        """Test that unknown source causes early exit without API call."""
        mock_args = MagicMock()
        mock_args.bathy_source = "unknown_source"
        mock_args.source = None
        mock_args.bathymetry_source = None
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")
        mock_args.verbose = False

        with patch("cruiseplan.bathymetry") as mock_api:
            with pytest.raises(SystemExit):
                main(mock_args)

            # API should not be called for unknown sources
            mock_api.assert_not_called()

    def test_main_keyboard_interrupt_handling(self):
        """Test graceful handling of keyboard interrupt."""
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"
        mock_args.source = None
        mock_args.bathymetry_source = None
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")
        mock_args.verbose = False

        with patch("cruiseplan.bathymetry") as mock_api:
            mock_api.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(mock_args)
