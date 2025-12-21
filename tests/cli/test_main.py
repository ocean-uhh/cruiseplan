"""
Tests for main CLI entry point.
"""

import sys
from io import StringIO
from unittest.mock import patch

from cruiseplan.cli.main import main


class TestCLIMainFunction:
    """Test main CLI function and argument parsing."""

    def test_help_display(self):
        """Test help message is displayed when no subcommand given."""
        test_args = ["cruiseplan"]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(1)

    @patch("cruiseplan.cli.pangaea.main")
    def test_pangaea_subcommand(self, mock_pangaea_main):
        """Test pangaea subcommand is called correctly."""
        test_args = [
            "cruiseplan",
            "pangaea",
            "dois.txt",
            "-o",
            "tests_output",
            "--rate-limit",
            "0.5",
        ]

        with patch.object(sys, "argv", test_args):
            main()
            mock_pangaea_main.assert_called_once()

    @patch("cruiseplan.cli.stations.main")
    def test_stations_subcommand(self, mock_stations_main):
        """Test stations subcommand is called correctly."""
        test_args = [
            "cruiseplan",
            "stations",
            "--lat",
            "50",
            "60",
            "--lon",
            "-20",
            "-10",
        ]

        with patch.object(sys, "argv", test_args):
            main()
            mock_stations_main.assert_called_once()

    def test_schedule_subcommand(self):
        """Test schedule subcommand shows not implemented message."""
        test_args = [
            "cruiseplan",
            "schedule",
            "-c",
            "cruise.yaml",
            "-o",
            "tests_output",
        ]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(1)

    def test_invalid_subcommand(self):
        """Test handling of invalid subcommand."""
        test_args = ["cruiseplan", "invalid-command"]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(1)

    def test_keyboard_interrupt(self):
        """Test handling of keyboard interrupt."""
        test_args = ["cruiseplan", "pangaea", "dois.txt"]

        with patch.object(sys, "argv", test_args):
            with patch("cruiseplan.cli.pangaea.main") as mock_pangaea:
                mock_pangaea.side_effect = KeyboardInterrupt()

                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_with(1)

    def test_unexpected_exception(self):
        """Test handling of unexpected exceptions."""
        test_args = ["cruiseplan", "pangaea", "dois.txt"]

        with patch.object(sys, "argv", test_args):
            with patch("cruiseplan.cli.pangaea.main") as mock_pangaea:
                mock_pangaea.side_effect = RuntimeError("Unexpected error")

                with patch("sys.exit") as mock_exit:
                    main()
                    mock_exit.assert_called_with(1)


class TestSubcommandArguments:
    """Test argument parsing for each subcommand."""

    def test_pangaea_arguments(self):
        """Test pangaea subcommand argument parsing."""
        test_args = [
            "cruiseplan",
            "pangaea",
            "dois.txt",
            "-o",
            "output_dir",
            "--output-file",
            "specific.pkl",
            "--rate-limit",
            "2.0",
            "--merge-campaigns",
        ]

        with patch.object(sys, "argv", test_args):
            with patch("cruiseplan.cli.pangaea.main") as mock_main:
                main()

                # Check that args were parsed correctly
                args = mock_main.call_args[0][0]
                assert str(args.query_or_file) == "dois.txt"
                assert str(args.output_dir) == "output_dir"
                assert str(args.output_file) == "specific.pkl"
                assert args.rate_limit == 2.0
                assert args.merge_campaigns == True

    def test_stations_arguments(self):
        """Test stations subcommand argument parsing."""
        test_args = [
            "cruiseplan",
            "stations",
            "-p",
            "pangaea.pkl",
            "--lat",
            "50.0",
            "60.0",
            "--lon",
            "-20.0",
            "-10.0",
            "-o",
            "output_dir",
            "--bathymetry-source",
            "gebco2025",
        ]

        with patch.object(sys, "argv", test_args):
            with patch("cruiseplan.cli.stations.main") as mock_main:
                main()

                args = mock_main.call_args[0][0]
                assert str(args.pangaea_file) == "pangaea.pkl"
                assert args.lat == [50.0, 60.0]
                assert args.lon == [-20.0, -10.0]
                assert str(args.output_dir) == "output_dir"
                assert args.bathymetry_source == "gebco2025"

    def test_schedule_arguments_not_implemented(self):
        """Test schedule subcommand shows not implemented for now."""
        test_args = [
            "cruiseplan",
            "schedule",
            "-c",
            "cruise.yaml",
            "-o",
            "output_dir",
            "--format",
            "html",
        ]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(1)

    def test_depths_arguments_not_implemented(self):
        """Test depths subcommand shows not implemented for now."""
        test_args = ["cruiseplan", "depths", "config.yaml", "-o", "output_dir"]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_with(1)


class TestVersionAndHelp:
    """Test version and help functionality."""

    def test_version_flag(self):
        """Test version flag displays version."""
        test_args = ["cruiseplan", "--version"]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                    main()
                    output = mock_stdout.getvalue()
                    assert "cruiseplan" in output
                    # Accept various version patterns (dev: 0.0.post1.dev1, release: 0.2.x)
                    assert (
                        "0.2." in output
                        or "0.1." in output
                        or "0.0.post" in output
                        or "0.0.dev" in output
                    )

    def test_subcommand_help(self):
        """Test subcommand help works."""
        test_args = ["cruiseplan", "pangaea", "--help"]

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit"):
                # Should not raise exception, just exit cleanly
                main()


class TestDynamicImports:
    """Test dynamic import functionality."""

    def test_not_implemented_subcommand(self):
        """Test handling of invalid subcommand choices."""
        test_args = ["cruiseplan", "optimize"]  # Not implemented yet

        with patch.object(sys, "argv", test_args):
            with patch("sys.exit") as mock_exit:
                # argparse will handle invalid choices and exit with code 2
                main()
                # argparse calls sys.exit(2) for invalid choices, but may also trigger our help logic
                # We just need to verify sys.exit was called
                mock_exit.assert_called()


class TestModuleStructure:
    """Test module structure and imports."""

    def test_main_function_exists(self):
        """Test main function can be imported."""
        from cruiseplan.cli.main import main

        assert callable(main)

    def test_main_module_executable(self):
        """Test main module can be run as script."""
        import cruiseplan.cli.main

        assert hasattr(cruiseplan.cli.main, "main")
