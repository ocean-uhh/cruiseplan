"""
Tests for map CLI command.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from cruiseplan.cli.map import main


class TestMapCommand:
    """Test map command functionality."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_basic_success(self, mock_load_cruise, mock_generate, tmp_path):
        """Test basic map generation with default settings."""
        # Setup mocks
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise_instance.config.cruise_name = "Test_Cruise_2028"
        mock_load_cruise_instance.station_registry = {"STN_001": MagicMock()}
        mock_load_cruise.return_value = mock_load_cruise_instance

        output_path = tmp_path / "Test_Cruise_2028_map.png"
        mock_generate.return_value = output_path

        # Create args
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=tmp_path,
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        # Call main function
        result = main(args)

        # Verify success
        assert result == 0
        mock_load_cruise.assert_called_once_with(Path("test_cruise.yaml"))
        mock_generate.assert_called_once()

        # Verify generate_map_from_yaml was called with correct arguments
        call_args = mock_generate.call_args
        assert call_args[0][0] == mock_load_cruise_instance  # cruise object
        assert call_args[1]["output_file"] == tmp_path / "Test_Cruise_2028_map.png"
        assert call_args[1]["bathymetry_source"] == "gebco2025"
        assert call_args[1]["bathymetry_stride"] == 5
        assert call_args[1]["show_plot"] == False
        assert call_args[1]["figsize"] == (12, 10)

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_custom_output_file(self, mock_load_cruise, mock_generate, tmp_path):
        """Test map generation with custom output file."""
        # Setup mocks
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise_instance.config.cruise_name = "Test_Cruise"
        mock_load_cruise_instance.station_registry = {"STN_001": MagicMock()}
        mock_load_cruise.return_value = mock_load_cruise_instance

        custom_output = tmp_path / "my_custom_map.png"
        mock_generate.return_value = custom_output

        # Create args with custom output file
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=tmp_path,
            output_file=custom_output,
            format="png",
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            bathymetry_stride=10,
            show_plot=False,
            figsize=[14, 12],
            verbose=False,
        )

        # Call main function
        result = main(args)

        # Verify success
        assert result == 0
        mock_generate.assert_called_once()

        # Verify generate_map_from_yaml was called with custom output file
        call_args = mock_generate.call_args
        assert call_args[1]["output_file"] == custom_output
        assert call_args[1]["bathymetry_source"] == "etopo2022"
        assert call_args[1]["bathymetry_stride"] == 10
        assert call_args[1]["figsize"] == (14, 12)

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_cruise_name_sanitization(
        self, mock_load_cruise, mock_generate, tmp_path
    ):
        """Test cruise name sanitization for filename generation."""
        # Setup mocks with problematic cruise name
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise_instance.config.cruise_name = (
            "Test Cruise/With Special Characters"
        )
        mock_load_cruise_instance.station_registry = {"STN_001": MagicMock()}
        mock_load_cruise.return_value = mock_load_cruise_instance

        mock_generate.return_value = tmp_path / "output.png"

        # Create args
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=tmp_path,
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        # Call main function
        main(args)

        # Verify filename sanitization
        call_args = mock_generate.call_args
        expected_filename = tmp_path / "Test_Cruise-With_Special_Characters_map.png"
        assert call_args[1]["output_file"] == expected_filename

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_with_port_info(
        self, mock_load_cruise, mock_generate, tmp_path, capsys
    ):
        """Test map generation with departure and arrival ports."""
        # Setup mocks with port information
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise_instance.config.cruise_name = "Test_Cruise"
        mock_load_cruise_instance.station_registry = {
            "STN_001": MagicMock(),
            "STN_002": MagicMock(),
        }

        # Setup departure port
        mock_departure_port = MagicMock()
        mock_departure_port.name = "Reykjavik"
        mock_load_cruise_instance.config.departure_port = mock_departure_port

        # Setup arrival port
        mock_arrival_port = MagicMock()
        mock_arrival_port.name = "Longyearbyen"
        mock_load_cruise_instance.config.arrival_port = mock_arrival_port

        mock_load_cruise.return_value = mock_load_cruise_instance
        mock_generate.return_value = tmp_path / "output.png"

        # Create args
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=tmp_path,
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        # Call main function
        result = main(args)

        # Verify success and output
        assert result == 0
        captured = capsys.readouterr()
        assert "📁 PNG map:" in captured.out
        assert "📍 Stations: 2" in captured.out
        assert "🚢 Departure: Reykjavik" in captured.out
        assert "🏁 Arrival: Longyearbyen" in captured.out

    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_file_not_found(self, mock_load_cruise):
        """Test handling of missing configuration file."""
        mock_load_cruise.side_effect = FileNotFoundError("Config file not found")

        # Create args
        args = Namespace(
            config_file=Path("nonexistent.yaml"),
            output_dir=Path("."),
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        # Call main function
        result = main(args)

        # Verify error handling
        assert result == 1

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_generation_failure(self, mock_load_cruise, mock_generate):
        """Test handling of map generation failure."""
        # Setup mocks
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise.return_value = mock_load_cruise_instance
        mock_generate.return_value = None  # Simulate failure

        # Create args
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=Path("."),
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        # Call main function
        result = main(args)

        # Verify error handling
        assert result == 1

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_general_exception(self, mock_load_cruise, mock_generate):
        """Test handling of general exceptions."""
        # Setup mocks to raise exception
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise.return_value = mock_load_cruise_instance
        mock_generate.side_effect = RuntimeError("Map generation failed")

        # Create args
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=Path("."),
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=False,
        )

        # Call main function
        result = main(args)

        # Verify error handling
        assert result == 1

    @patch("cruiseplan.cli.map.generate_map_from_yaml")
    @patch("cruiseplan.cli.map.load_cruise_with_pretty_warnings")
    def test_map_verbose_exception(self, mock_load_cruise, mock_generate, capsys):
        """Test verbose exception handling."""
        # Setup mocks to raise exception
        mock_load_cruise_instance = MagicMock()
        mock_load_cruise.return_value = mock_load_cruise_instance
        mock_generate.side_effect = RuntimeError("Map generation failed")

        # Create args with verbose=True
        args = Namespace(
            config_file=Path("test_cruise.yaml"),
            output_dir=Path("."),
            output_file=None,
            format="png",
            bathymetry_source="gebco2025",
            bathymetry_dir=Path("data"),
            bathymetry_stride=5,
            show_plot=False,
            figsize=[12, 10],
            verbose=True,
        )

        # Call main function
        result = main(args)

        # Verify error handling and verbose output
        assert result == 1
