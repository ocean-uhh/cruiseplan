"""
Tests for stations CLI command.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.cli.stations import (
    determine_coordinate_bounds,
    load_pangaea_data,
    main,
)
from cruiseplan.cli.utils import CLIError


class TestPangaeaDataLoading:
    """Test PANGAEA data loading for stations."""

    @patch("cruiseplan.data.pangaea.load_campaign_data")
    def test_load_pangaea_data_success(self, mock_load):
        """Test successful PANGAEA data loading."""
        mock_data = [
            {
                "label": "Campaign1",
                "latitude": [50.0, 51.0],
                "longitude": [-10.0, -11.0],
            },
            {"label": "Campaign2", "latitude": [52.0], "longitude": [-12.0]},
        ]
        mock_load.return_value = mock_data

        result = load_pangaea_data(Path("test.pkl"))

        assert result == mock_data
        mock_load.assert_called_once()

    @patch("cruiseplan.data.pangaea.load_campaign_data")
    def test_load_pangaea_data_empty(self, mock_load):
        """Test loading empty PANGAEA data."""
        mock_load.return_value = []

        with pytest.raises(CLIError, match="No campaign data found"):
            load_pangaea_data(Path("empty.pkl"))

    @patch("cruiseplan.data.pangaea.load_campaign_data")
    def test_load_pangaea_data_import_error(self, mock_load):
        """Test handling of import errors."""
        mock_load.side_effect = ImportError("Module not found")

        with pytest.raises(CLIError, match="PANGAEA functionality not available"):
            load_pangaea_data(Path("test.pkl"))


class TestCoordinateBounds:
    """Test coordinate bounds determination."""

    def test_determine_bounds_explicit(self):
        """Test using explicit coordinate bounds."""
        args = Namespace(lat=[50.0, 60.0], lon=[-20.0, -10.0])

        lat_bounds, lon_bounds = determine_coordinate_bounds(args)

        assert lat_bounds == (50.0, 60.0)
        assert lon_bounds == (-20.0, -10.0)

    def test_determine_bounds_from_pangaea(self):
        """Test deriving bounds from PANGAEA data."""
        args = Namespace(lat=None, lon=None)
        campaign_data = [
            {"latitude": [50.0, 55.0], "longitude": [-20.0, -15.0]},
            {"latitude": [52.0], "longitude": [-18.0]},
        ]

        lat_bounds, lon_bounds = determine_coordinate_bounds(args, campaign_data)

        # Should have padding around data bounds
        assert lat_bounds[0] < 50.0  # Min with padding
        assert lat_bounds[1] > 55.0  # Max with padding
        assert lon_bounds[0] < -20.0  # Min with padding
        assert lon_bounds[1] > -15.0  # Max with padding

    def test_determine_bounds_defaults(self):
        """Test falling back to default bounds."""
        args = Namespace(lat=None, lon=None)
        campaign_data = None

        lat_bounds, lon_bounds = determine_coordinate_bounds(args, campaign_data)

        assert lat_bounds == (45.0, 70.0)
        assert lon_bounds == (-65.0, -5.0)

    def test_determine_bounds_partial_args(self):
        """Test with only lat or lon specified."""
        args = Namespace(lat=[50.0, 60.0], lon=None)

        lat_bounds, lon_bounds = determine_coordinate_bounds(args)

        # Should use default for missing coordinate
        assert lat_bounds == (50.0, 60.0)
        assert lon_bounds == (-65.0, -5.0)


class TestMainCommand:
    """Test main command integration."""

    @patch("cruiseplan.interactive.station_picker.StationPicker")
    @patch("matplotlib.pyplot.show")
    @patch("cruiseplan.cli.stations.load_pangaea_data")
    @patch("cruiseplan.cli.stations.validate_input_file")
    @patch("cruiseplan.cli.stations.validate_output_path")
    def test_main_with_pangaea(
        self,
        mock_validate_output,
        mock_validate_input,
        mock_load_pangaea,
        mock_show,
        mock_picker_class,
    ):
        """Test main command with PANGAEA data."""
        # Setup mocks
        mock_validate_input.return_value = Path("/test/pangaea.pkl")
        mock_validate_output.return_value = Path("/test/stations.yaml")

        mock_pangaea_data = [
            {"label": "Campaign1", "latitude": [50.0], "longitude": [-10.0]}
        ]
        mock_load_pangaea.return_value = mock_pangaea_data

        mock_picker = MagicMock()
        mock_picker_class.return_value = mock_picker

        # Create args
        args = Namespace(
            pangaea_file=Path("pangaea.pkl"),
            lat=[50.0, 60.0],
            lon=[-20.0, -10.0],
            output_dir=Path("tests_output"),
            output_file=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            high_resolution=False,
            verbose=False,
            quiet=False,
        )

        # Should not raise exception
        main(args)

        # Verify calls
        mock_validate_input.assert_called_once()
        mock_load_pangaea.assert_called_once()
        mock_picker_class.assert_called_once()
        mock_picker.show.assert_called_once()

    @patch("cruiseplan.interactive.station_picker.StationPicker")
    @patch("matplotlib.pyplot.show")
    @patch("cruiseplan.cli.stations.validate_output_path")
    def test_main_without_pangaea(
        self, mock_validate_output, mock_show, mock_picker_class
    ):
        """Test main command without PANGAEA data."""
        mock_validate_output.return_value = Path("/test/stations.yaml")

        mock_picker = MagicMock()
        mock_picker_class.return_value = mock_picker

        args = Namespace(
            pangaea_file=None,
            lat=[50.0, 60.0],
            lon=[-20.0, -10.0],
            output_dir=Path("tests_output"),
            output_file=None,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            high_resolution=False,
            verbose=False,
            quiet=False,
        )

        main(args)

        # Should still work without PANGAEA data
        mock_picker_class.assert_called_once()
        mock_picker.show.assert_called_once()

    def test_main_no_matplotlib(self):
        """Test main command fails gracefully without matplotlib."""

        def mock_import(*args, **kwargs):
            if args[0] == "matplotlib.pyplot":
                raise ImportError("No matplotlib")
            return original_import(*args, **kwargs)

        import builtins

        original_import = builtins.__import__

        with patch("builtins.__import__", side_effect=mock_import):
            args = Namespace(
                pangaea_file=None,
                lat=None,
                lon=None,
                output_dir=Path("tests_output"),
                output_file=None,
                bathymetry_source="etopo2022",
                verbose=False,
                quiet=False,
            )

            with pytest.raises(SystemExit):
                main(args)

    def test_main_invalid_bounds(self):
        """Test main command with invalid coordinate bounds."""
        args = Namespace(
            pangaea_file=None,
            lat=[90.0, 45.0],  # Invalid: min > max
            lon=[-20.0, -10.0],
            output_dir=Path("tests_output"),
            output_file=None,
            bathymetry_source="etopo2022",
        )

        with pytest.raises(SystemExit):
            main(args)

    @patch("cruiseplan.cli.stations.validate_input_file")
    def test_main_pangaea_file_error(self, mock_validate_input):
        """Test main command with PANGAEA file error."""
        mock_validate_input.side_effect = CLIError("File not found")

        args = Namespace(
            pangaea_file=Path("nonexistent.pkl"),
            lat=None,
            lon=None,
            output_dir=Path("tests_output"),
            output_file=None,
            bathymetry_source="etopo2022",
        )

        with pytest.raises(SystemExit):
            main(args)

    def test_main_keyboard_interrupt(self):
        """Test main command handles keyboard interrupt."""
        args = Namespace(
            pangaea_file=None,
            lat=None,
            lon=None,
            output_dir=Path("tests_output"),
            output_file=None,
            bathymetry_source="etopo2022",
        )

        with patch("cruiseplan.cli.stations.validate_output_path") as mock_validate:
            mock_validate.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit):
                main(args)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_determine_bounds_empty_pangaea_data(self):
        """Test coordinate bounds with empty PANGAEA data lists."""
        args = Namespace(lat=None, lon=None)
        campaign_data = [
            {"latitude": [], "longitude": []},  # Empty lists
            {"latitude": [50.0], "longitude": []},  # Mismatched lengths
        ]

        lat_bounds, lon_bounds = determine_coordinate_bounds(args, campaign_data)

        # Should fall back to defaults
        assert lat_bounds == (45.0, 70.0)
        assert lon_bounds == (-65.0, -5.0)

    def test_determine_bounds_missing_coordinate_keys(self):
        """Test coordinate bounds with missing keys in PANGAEA data."""
        args = Namespace(lat=None, lon=None)
        campaign_data = [
            {"label": "Campaign1"},  # Missing lat/lon keys
            {"latitude": [50.0]},  # Missing longitude key
        ]

        lat_bounds, lon_bounds = determine_coordinate_bounds(args, campaign_data)

        # Should fall back to defaults
        assert lat_bounds == (45.0, 70.0)
        assert lon_bounds == (-65.0, -5.0)


class TestModuleStructure:
    """Test module can be executed and has required functions."""

    def test_module_executable(self):
        """Test the module can be imported and has required functions."""
        from cruiseplan.cli import stations

        assert hasattr(stations, "main")
        assert hasattr(stations, "load_pangaea_data")
        assert hasattr(stations, "determine_coordinate_bounds")
