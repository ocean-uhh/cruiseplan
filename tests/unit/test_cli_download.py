"""
Test suite for cruiseplan.cli.download module.

This module tests the CLI download functionality for different bathymetry sources,
error handling, and user interaction scenarios.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.download import main


class TestCliDownload:
    """Test suite for CLI download functionality."""

    def test_main_with_etopo2022_source(self, capsys):
        """Test download main with ETOPO 2022 source."""
        # Mock args with etopo2022 source
        mock_args = MagicMock()
        mock_args.bathymetry_source = "etopo2022"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify output
            captured = capsys.readouterr()
            assert "CRUISEPLAN ASSET DOWNLOADER" in captured.out
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called correctly
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="etopo2022"
            )

    def test_main_with_gebco2025_source(self, capsys):
        """Test download main with GEBCO 2025 source."""
        # Mock args with gebco2025 source
        mock_args = MagicMock()
        mock_args.bathymetry_source = "gebco2025"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify output
            captured = capsys.readouterr()
            assert "CRUISEPLAN ASSET DOWNLOADER" in captured.out
            assert "GEBCO 2025 high-resolution bathymetry data (~7.5GB)" in captured.out

            # Verify download_bathymetry was called correctly
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="gebco2025"
            )

    def test_main_with_no_args_defaults_to_etopo2022(self, capsys):
        """Test download main with no args defaults to ETOPO 2022."""
        # Mock args without bathymetry_source attribute
        mock_args = MagicMock()
        del mock_args.bathymetry_source  # Remove the attribute to test getattr default
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(mock_args)

            # Verify output shows ETOPO default
            captured = capsys.readouterr()
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called with default
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="etopo2022"
            )

    def test_main_with_none_args_defaults_to_etopo2022(self, capsys):
        """Test download main with None args defaults to ETOPO 2022."""
        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = True

            main(None)

            # Verify output shows ETOPO default
            captured = capsys.readouterr()
            assert "ETOPO 2022 bathymetry data (~500MB)" in captured.out

            # Verify download_bathymetry was called with default
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="etopo2022"
            )

    def test_main_with_unknown_source_exits(self, capsys):
        """Test download main with unknown source exits with error."""
        # Mock args with unknown source
        mock_args = MagicMock()
        mock_args.bathymetry_source = "unknown_source"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
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
        mock_args.bathymetry_source = "gebco2025"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = False  # Simulate failed download

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify download_bathymetry was called
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="gebco2025"
            )

    def test_main_etopo2022_failed_download_does_not_exit(self, capsys):
        """Test that failed ETOPO 2022 download does not cause exit."""
        # Mock args with etopo2022 source
        mock_args = MagicMock()
        mock_args.bathymetry_source = "etopo2022"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = False  # Simulate failed download

            # Should not raise SystemExit for ETOPO failures
            main(mock_args)

            # Verify download_bathymetry was called
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="etopo2022"
            )

    def test_main_keyboard_interrupt_handling(self, capsys):
        """Test keyboard interrupt handling during download."""
        # Mock args
        mock_args = MagicMock()
        mock_args.bathymetry_source = "etopo2022"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
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
        mock_args.bathymetry_source = "etopo2022"
        mock_args.citation = False  # Don't show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.side_effect = RuntimeError("Unexpected error occurred")

            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify error message
            captured = capsys.readouterr()
            assert "❌ Unexpected error: Unexpected error occurred" in captured.out

    def test_main_as_script(self):
        """Test main when called as script (if __name__ == '__main__')."""
        # This tests the script entry point, but we can't easily test it without
        # mocking sys.argv. Instead, we test that the function can be called
        # without arguments when the module is imported.
        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = True

            # Test that calling main without args works (default behavior)
            main()

            # Verify download_bathymetry was called with default
            mock_download.assert_called_once_with(
                target_dir=str(Path("data") / "bathymetry"), source="etopo2022"
            )

    def test_main_with_citation_flag_etopo2022(self, capsys):
        """Test download main with --citation flag for ETOPO 2022."""
        # Mock args with citation flag
        mock_args = MagicMock()
        mock_args.bathymetry_source = "etopo2022"
        mock_args.citation = True  # Show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
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
        """Test download main with --citation flag for GEBCO 2025."""
        # Mock args with citation flag
        mock_args = MagicMock()
        mock_args.bathymetry_source = "gebco2025"
        mock_args.citation = True  # Show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            main(mock_args)

            # Verify citation output
            captured = capsys.readouterr()
            assert "CITATION INFORMATION: GEBCO 2025 Grid" in captured.out
            assert "FORMAL CITATION (for bibliography):" in captured.out
            assert "SHORT CITATION (for figure captions):" in captured.out

            # Verify download was NOT called (citation only mode)
            mock_download.assert_not_called()

    def test_main_with_citation_flag_unknown_source(self, capsys):
        """Test download main with --citation flag for unknown source."""
        # Mock args with citation flag and unknown source
        mock_args = MagicMock()
        mock_args.bathymetry_source = "unknown_source"
        mock_args.citation = True  # Show citation only
        del mock_args.output_dir  # Remove attribute to use getattr default

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            with pytest.raises(SystemExit) as excinfo:
                main(mock_args)

            # Verify exit code
            assert excinfo.value.code == 1

            # Verify error output
            captured = capsys.readouterr()
            assert "❌ Unknown bathymetry source: unknown_source" in captured.out

            # Verify download was NOT called
            mock_download.assert_not_called()

    def test_logging_configuration(self):
        """Test that logging configuration doesn't cause errors."""
        import logging

        # Test that we can import and call the module without logging errors
        # Since logging.basicConfig might have already been called by other tests,
        # we just verify that the module imports correctly and logging works

        with patch("cruiseplan.cli.download.download_bathymetry") as mock_download:
            mock_download.return_value = True

            # Import and run - this executes the logging.basicConfig line
            from cruiseplan.cli.download import main

            main()

            # If we get here without exception, logging configuration is working
            assert True

        # Verify logging can be used without errors
        logger = logging.getLogger("test_logger")
        logger.info("Test message")
        assert True  # If we get here, logging is working
