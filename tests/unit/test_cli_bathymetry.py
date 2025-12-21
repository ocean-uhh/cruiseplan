"""
Test suite for cruiseplan.cli.bathymetry module.

This module tests the CLI bathymetry functionality for different bathymetry sources,
error handling, user interaction scenarios, and the new --source parameter format.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.bathymetry import main


class TestCliBathymetry:
    """Test suite for CLI bathymetry functionality."""

    def test_main_with_etopo2022_source(self, capsys):
        """Test bathymetry main with ETOPO 2022 source using new --bathy-source parameter."""
        # Mock args with etopo2022 source using new parameter name
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify output uses updated title
            captured = capsys.readouterr()
            assert "CRUISEPLAN BATHYMETRY DOWNLOADER" in captured.out
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called correctly
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="etopo2022"
            )

    def test_main_with_gebco2025_source(self, capsys):
        """Test bathymetry main with GEBCO 2025 source using new --bathy-source parameter."""
        # Mock args with gebco2025 source using new parameter name
        mock_args = MagicMock()
        mock_args.bathy_source = "gebco2025"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify output uses updated title
            captured = capsys.readouterr()
            assert "CRUISEPLAN BATHYMETRY DOWNLOADER" in captured.out
            assert "GEBCO 2025 high-resolution bathymetry data (~7.5GB)" in captured.out

            # Verify download_bathymetry was called correctly
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="gebco2025"
            )

    def test_main_with_legacy_bathymetry_source_parameter(self, capsys):
        """Test bathymetry main with legacy --bathymetry-source parameter (backward compatibility)."""
        # Mock args with legacy bathymetry_source parameter
        mock_args = MagicMock()
        mock_args.bathy_source = None  # New primary parameter not set
        mock_args.source = None  # Legacy --source parameter not set
        mock_args.bathymetry_source = (
            "etopo2022"  # Legacy --bathymetry-source parameter set
        )
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify legacy parameter still works
            captured = capsys.readouterr()
            assert "CRUISEPLAN BATHYMETRY DOWNLOADER" in captured.out
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called correctly
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="etopo2022"
            )

    def test_main_new_source_parameter_takes_precedence(self, capsys):
        """Test that new --bathy-source parameter takes precedence over legacy parameters."""
        # Mock args with both parameters set (new should win)
        mock_args = MagicMock()
        mock_args.bathy_source = "gebco2025"  # New primary parameter
        mock_args.source = "etopo2022"  # Legacy --source parameter
        mock_args.bathymetry_source = (
            "etopo2022"  # Legacy --bathymetry-source parameter
        )
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify new parameter takes precedence (GEBCO, not ETOPO)
            captured = capsys.readouterr()
            assert "GEBCO 2025 high-resolution bathymetry data (~7.5GB)" in captured.out

            # Verify download_bathymetry was called with new parameter value
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="gebco2025"
            )

    def test_main_with_no_args_defaults_to_etopo2022(self, capsys):
        """Test bathymetry main with no args defaults to ETOPO 2022."""
        # Mock args without source attributes
        mock_args = MagicMock()
        mock_args.bathy_source = None  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify output shows ETOPO default
            captured = capsys.readouterr()
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called with default
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="etopo2022"
            )

    def test_main_with_none_args_defaults_to_etopo2022(self, capsys):
        """Test bathymetry main with None args defaults to ETOPO 2022."""
        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(None)

            # Verify output shows ETOPO default
            captured = capsys.readouterr()
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called with default
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="etopo2022"
            )

    def test_main_with_unknown_source_exits(self, capsys):
        """Test bathymetry main with unknown source exits with error."""
        # Mock args with unknown source
        mock_args = MagicMock()
        mock_args.bathy_source = "unknown_source"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify error message
            captured = capsys.readouterr()
            assert "Unknown bathymetry source: unknown_source" in captured.out

            # Verify download_bathymetry was not called
            mock_download.assert_not_called()

    def test_main_gebco2025_failed_download_exits(self, capsys):
        """Test that failed GEBCO 2025 download causes exit."""
        # Mock args with gebco2025 source
        mock_args = MagicMock()
        mock_args.bathy_source = "gebco2025"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = False  # Simulate failed download

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify download_bathymetry was called
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="gebco2025"
            )

    def test_main_etopo2022_failed_download_does_not_exit(self, capsys):
        """Test that failed ETOPO 2022 download does not cause exit."""
        # Mock args with etopo2022 source
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = False  # Simulate failed download

            # Should not raise SystemExit for ETOPO failures
            main(mock_args)

            # Verify download_bathymetry was called
            mock_download.assert_called_once_with(
                target_dir=str(Path("data/bathymetry")), source="etopo2022"
            )

    def test_main_keyboard_interrupt_handling(self, capsys):
        """Test keyboard interrupt handling during download."""
        # Mock args
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.side_effect = KeyboardInterrupt("User cancelled")

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify cancellation message
            captured = capsys.readouterr()
            assert "⚠️  Download cancelled by user." in captured.out

    def test_main_unexpected_exception_handling(self, capsys):
        """Test unexpected exception handling during download."""
        # Mock args
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.side_effect = RuntimeError("Unexpected error occurred")

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify error message
            captured = capsys.readouterr()
            assert "❌ Unexpected error: Unexpected error occurred" in captured.out

    def test_main_with_citation_flag_etopo2022(self, capsys):
        """Test bathymetry main with --citation flag for ETOPO 2022."""
        # Mock args with citation flag
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = True  # Show citation only
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            main(mock_args)

            # Verify citation output
            captured = capsys.readouterr()
            assert (
                "CITATION INFORMATION: ETOPO 2022 15 Arc-Second Global Relief Model"
                in captured.out
            )
            assert "FORMAL CITATION (for bibliography):" in captured.out
            assert "SHORT CITATION (for figure captions):" in captured.out
            assert "DOI:" in captured.out
            assert "LICENSE:" in captured.out

            # Verify download was NOT called (citation only mode)
            mock_download.assert_not_called()

    def test_main_with_citation_flag_gebco2025(self, capsys):
        """Test bathymetry main with --citation flag for GEBCO 2025."""
        # Mock args with citation flag
        mock_args = MagicMock()
        mock_args.bathy_source = "gebco2025"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = True  # Show citation only
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            main(mock_args)

            # Verify citation output
            captured = capsys.readouterr()
            assert "CITATION INFORMATION: GEBCO 2025 Grid" in captured.out
            assert "FORMAL CITATION (for bibliography):" in captured.out
            assert "SHORT CITATION (for figure captions):" in captured.out

            # Verify download was NOT called (citation only mode)
            mock_download.assert_not_called()

    def test_main_citation_help_text_updated(self, capsys):
        """Test that citation help text references new command name."""
        # Mock args with citation flag
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False  # Regular download to check success message
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify citation help text uses new parameter name
            captured = capsys.readouterr()
            assert (
                "cruiseplan bathymetry --bathy-source etopo2022 --citation"
                in captured.out
            )

    def test_main_with_citation_flag_unknown_source(self, capsys):
        """Test bathymetry main with --citation flag for unknown source."""
        # Mock args with citation flag and unknown source
        mock_args = MagicMock()
        mock_args.bathy_source = "unknown_source"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = True  # Show citation only
        mock_args.output_dir = Path("data/bathymetry")

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify error output
            captured = capsys.readouterr()
            assert "❌ Unknown bathymetry source: unknown_source" in captured.out

            # Verify download was NOT called
            mock_download.assert_not_called()

    def test_main_custom_output_dir(self, capsys):
        """Test bathymetry main with custom output directory."""
        # Mock args with custom output directory
        custom_dir = Path("/custom/path/bathymetry")
        mock_args = MagicMock()
        mock_args.bathy_source = "etopo2022"  # New primary parameter
        mock_args.source = None  # Legacy parameter not set
        mock_args.bathymetry_source = None  # Legacy parameter not set
        mock_args.citation = False
        mock_args.output_dir = custom_dir

        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify download_bathymetry was called with custom directory
            mock_download.assert_called_once_with(
                target_dir=str(custom_dir), source="etopo2022"
            )

    def test_logging_configuration(self):
        """Test that logging configuration doesn't cause errors."""
        import logging

        # Test that we can import and call the module without logging errors
        with patch("cruiseplan.cli.bathymetry.download_bathymetry") as mock_download:
            mock_download.return_value = True

            # Import and run - this executes the logging.basicConfig line
            from cruiseplan.cli.bathymetry import main

            main()

            # If we get here without exception, logging configuration is working
            assert True

        # Verify logging can be used without errors
        logger = logging.getLogger("test_logger")
        logger.info("Test message")
        assert True  # If we get here, logging is working
