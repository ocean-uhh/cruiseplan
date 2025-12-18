"""
Tests for map generation utilities.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.output.map_generator import (
    extract_map_data,
    generate_folium_map,
    generate_map,
    generate_map_from_timeline,
    generate_map_from_yaml,
    plot_bathymetry,
    plot_cruise_elements,
)


class TestExtractMapData:
    """Test map data extraction from different sources."""

    def test_extract_map_data_cruise_source(self):
        """Test extracting data from cruise configuration."""
        from unittest.mock import MagicMock

        # Create mock cruise
        mock_cruise = MagicMock()
        mock_cruise.config.cruise_name = "Test Cruise"

        # Mock station registry
        mock_station = MagicMock()
        mock_station.latitude = 60.0
        mock_station.longitude = -20.0
        mock_station.operation_type = "CTD"
        mock_cruise.station_registry = {"STN_001": mock_station}

        # Mock ports
        mock_cruise.config.departure_port = None
        mock_cruise.config.arrival_port = None

        # Mock extract_coordinates_from_cruise function
        with patch(
            "cruiseplan.utils.coordinates.extract_coordinates_from_cruise"
        ) as mock_extract:
            mock_extract.return_value = ([60.0], [-20.0], ["STN_001"], None, None)

            data = extract_map_data(mock_cruise, "cruise")

            assert data["lats"] == [60.0]
            assert data["lons"] == [-20.0]
            assert data["station_names"] == ["STN_001"]
            assert data["station_types"] == ["CTD"]
            assert data["departure_port"] is None
            assert data["arrival_port"] is None
            assert "Test Cruise" in data["title"]

    def test_extract_map_data_timeline_source_list(self):
        """Test extracting data from timeline list."""
        timeline = [
            {"lat": 60.0, "lon": -20.0, "activity": "STN_001", "operation_type": "CTD"},
            {
                "lat": 61.0,
                "lon": -21.0,
                "activity": "STN_002",
                "operation_type": "mooring",
            },
        ]

        data = extract_map_data(timeline, "timeline")

        assert data["lats"] == [60.0, 61.0]
        assert data["lons"] == [-20.0, -21.0]
        assert data["station_names"] == ["STN_001", "STN_002"]
        assert data["station_types"] == ["CTD", "mooring"]
        assert data["departure_port"] is None
        assert data["arrival_port"] is None
        assert "Timeline" in data["title"]

    def test_extract_map_data_timeline_source_dict_with_config(self):
        """Test extracting data from timeline dict with config."""
        timeline = [
            {"lat": 60.0, "lon": -20.0, "activity": "STN_001", "operation_type": "CTD"},
        ]

        # Mock config with ports
        mock_config = MagicMock()
        mock_dep_port = MagicMock()
        mock_dep_port.position.latitude = 64.0
        mock_dep_port.position.longitude = -22.0
        mock_dep_port.name = "Reykjavik"
        mock_config.departure_port = mock_dep_port
        mock_config.arrival_port = None

        timeline_data = {"timeline": timeline, "config": mock_config}

        data = extract_map_data(timeline_data, "timeline")

        assert data["lats"] == [60.0]
        assert data["lons"] == [-20.0]
        assert data["departure_port"] == (64.0, -22.0, "Reykjavik")
        assert data["arrival_port"] is None

    def test_extract_map_data_timeline_skip_zero_coords(self):
        """Test that timeline extraction skips zero coordinates."""
        timeline = [
            {"lat": 60.0, "lon": -20.0, "activity": "STN_001", "operation_type": "CTD"},
            {
                "lat": 0.0,
                "lon": 0.0,
                "activity": "TRANSIT",
                "operation_type": "transit",
            },
            {"lat": 61.0, "lon": -21.0, "activity": "STN_002", "operation_type": "CTD"},
        ]

        data = extract_map_data(timeline, "timeline")

        # Should skip the zero coordinate entry
        assert data["lats"] == [60.0, 61.0]
        assert data["lons"] == [-20.0, -21.0]
        assert data["station_names"] == ["STN_001", "STN_002"]

    def test_extract_map_data_invalid_source_type(self):
        """Test error handling for invalid source type."""
        with pytest.raises(ValueError, match="Unknown source_type"):
            extract_map_data([], "invalid")


class TestPlotBathymetry:
    """Test bathymetry plotting function."""

    @patch("cruiseplan.data.bathymetry.BathymetryManager")
    @patch("cruiseplan.interactive.colormaps.get_colormap")
    @patch("matplotlib.pyplot.colorbar")
    def test_plot_bathymetry_success(
        self, mock_colorbar, mock_get_colormap, mock_bathymetry_manager
    ):
        """Test successful bathymetry plotting."""
        # Mock matplotlib axis
        mock_ax = MagicMock()

        # Mock bathymetry data
        mock_bathy_instance = MagicMock()
        mock_bathy_data = ([1, 2, 3], [4, 5, 6], [[-100, -200], [-300, -400]])
        mock_bathy_instance.get_grid_subset.return_value = mock_bathy_data
        mock_bathymetry_manager.return_value = mock_bathy_instance

        # Mock colormap
        mock_cmap = MagicMock()
        mock_get_colormap.return_value = mock_cmap

        # Mock contourf result
        mock_cs_filled = MagicMock()
        mock_ax.contourf.return_value = mock_cs_filled

        # Mock colorbar
        mock_cbar = MagicMock()
        mock_colorbar.return_value = mock_cbar

        result = plot_bathymetry(mock_ax, -25, -15, 55, 65, "gebco2025", 5, "data")

        assert result is True
        mock_bathymetry_manager.assert_called_once_with(
            source="gebco2025", data_dir="data"
        )
        mock_bathy_instance.get_grid_subset.assert_called_once()
        mock_ax.contourf.assert_called_once()
        mock_colorbar.assert_called_once()

    @patch("cruiseplan.data.bathymetry.BathymetryManager")
    def test_plot_bathymetry_no_data(self, mock_bathymetry_manager):
        """Test bathymetry plotting when no data is available."""
        mock_ax = MagicMock()

        # Mock no bathymetry data
        mock_bathy_instance = MagicMock()
        mock_bathy_instance.get_grid_subset.return_value = None
        mock_bathymetry_manager.return_value = mock_bathy_instance

        result = plot_bathymetry(mock_ax, -25, -15, 55, 65)

        assert result is False

    @patch("cruiseplan.data.bathymetry.BathymetryManager")
    def test_plot_bathymetry_exception(self, mock_bathymetry_manager):
        """Test bathymetry plotting exception handling."""
        mock_ax = MagicMock()

        # Mock exception
        mock_bathymetry_manager.side_effect = Exception("Bathymetry error")

        result = plot_bathymetry(mock_ax, -25, -15, 55, 65)

        assert result is False


class TestPlotCruiseElements:
    """Test cruise element plotting function."""

    @patch("cruiseplan.output.map_generator.extract_map_data")
    def test_plot_cruise_elements_basic(self, mock_extract):
        """Test basic cruise element plotting."""
        # Mock matplotlib axis
        mock_ax = MagicMock()

        # Mock map data
        mock_extract.return_value = {
            "lats": [60.0, 61.0],
            "lons": [-20.0, -21.0],
            "station_names": ["STN_001", "STN_002"],
            "station_types": ["station", "mooring"],
            "departure_port": (64.0, -22.0, "Reykjavik"),
            "arrival_port": (78.0, 15.0, "Longyearbyen"),
            "title": "Test Cruise",
        }

        # Mock cruise object with station registry
        mock_cruise = MagicMock()
        mock_station1 = MagicMock()
        mock_station1.latitude = 60.0
        mock_station1.longitude = -20.0
        mock_station2 = MagicMock()
        mock_station2.position.latitude = 61.0
        mock_station2.position.longitude = -21.0
        mock_cruise.station_registry = {
            "STN_001": mock_station1,
            "STN_002": mock_station2,
        }

        display_bounds = (-25, -15, 55, 65)

        plot_cruise_elements(mock_ax, mock_cruise, display_bounds, "cruise")

        # Verify basic plotting calls
        mock_ax.set_xlim.assert_called_once_with(-25, -15)
        mock_ax.set_ylim.assert_called_once_with(55, 65)
        mock_ax.set_xlabel.assert_called_once()
        mock_ax.set_ylabel.assert_called_once()
        mock_ax.set_title.assert_called_once_with(
            "Test Cruise", fontsize=14, fontweight="bold"
        )
        mock_ax.grid.assert_called_once()
        mock_ax.legend.assert_called_once()

    @patch("cruiseplan.output.map_generator.extract_map_data")
    def test_plot_cruise_elements_timeline_with_track(self, mock_extract):
        """Test plotting timeline data with cruise track."""
        mock_ax = MagicMock()

        mock_extract.return_value = {
            "lats": [60.0, 61.0, 62.0],
            "lons": [-20.0, -21.0, -22.0],
            "station_names": ["STN_001", "STN_002", "STN_003"],
            "station_types": ["station", "station", "station"],
            "departure_port": None,
            "arrival_port": None,
            "title": "Timeline",
        }

        timeline_data = [
            {"lat": 60.0, "lon": -20.0, "activity": "STN_001"},
            {"lat": 61.0, "lon": -21.0, "activity": "STN_002"},
            {"lat": 62.0, "lon": -22.0, "activity": "STN_003"},
        ]

        display_bounds = (-25, -15, 55, 65)

        plot_cruise_elements(mock_ax, timeline_data, display_bounds, "timeline")

        # Should plot cruise track for timeline data
        mock_ax.plot.assert_called()  # Cruise track line
        # Should also plot stations
        mock_ax.scatter.assert_called()

    @patch("cruiseplan.output.map_generator.extract_map_data")
    def test_plot_cruise_elements_mixed_station_types(self, mock_extract):
        """Test plotting with mixed station and mooring types."""
        mock_ax = MagicMock()

        mock_extract.return_value = {
            "lats": [60.0, 61.0],
            "lons": [-20.0, -21.0],
            "station_names": ["STN_001", "MOOR_001"],
            "station_types": ["station", "mooring"],
            "departure_port": None,
            "arrival_port": None,
            "title": "Mixed Types",
        }

        timeline_data = [
            {"lat": 60.0, "lon": -20.0, "activity": "STN_001"},
            {"lat": 61.0, "lon": -21.0, "activity": "MOOR_001"},
        ]

        display_bounds = (-25, -15, 55, 65)

        plot_cruise_elements(mock_ax, timeline_data, display_bounds, "timeline")

        # Should call scatter twice - once for stations, once for moorings
        assert mock_ax.scatter.call_count >= 2


class TestGenerateMap:
    """Test the unified generate_map function."""

    @patch("cruiseplan.output.map_generator.plot_cruise_elements")
    @patch("cruiseplan.output.map_generator.plot_bathymetry")
    @patch("cruiseplan.utils.coordinates.calculate_map_bounds")
    @patch("cruiseplan.output.map_generator.extract_map_data")
    @patch("matplotlib.pyplot.subplots")
    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.close")
    def test_generate_map_success(
        self,
        mock_close,
        mock_savefig,
        mock_subplots,
        mock_extract,
        mock_calc_bounds,
        mock_plot_bathy,
        mock_plot_elements,
    ):
        """Test successful map generation."""
        # Mock matplotlib
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Mock map data
        mock_extract.return_value = {
            "lats": [60.0],
            "lons": [-20.0],
            "departure_port": None,
            "arrival_port": None,
        }

        # Mock bounds calculation
        mock_calc_bounds.return_value = (-25, -15, 55, 65)

        # Mock plotting functions
        mock_plot_bathy.return_value = True

        mock_cruise = MagicMock()
        output_file = Path("/tmp/test_map.png")

        result = generate_map(
            mock_cruise, source_type="cruise", output_file=output_file, figsize=(10, 8)
        )

        assert result == output_file.resolve()
        mock_subplots.assert_called_once_with(figsize=(10, 8))
        mock_plot_bathy.assert_called_once()
        mock_plot_elements.assert_called_once()
        mock_savefig.assert_called_once()
        mock_close.assert_called_once()

    @patch("cruiseplan.output.map_generator.extract_map_data")
    def test_generate_map_no_coordinates(self, mock_extract):
        """Test map generation with no coordinates."""
        mock_extract.return_value = {"lats": [], "lons": []}

        result = generate_map(MagicMock(), "cruise")

        assert result is None

    @patch("cruiseplan.output.map_generator.plot_cruise_elements")
    @patch("cruiseplan.output.map_generator.plot_bathymetry")
    @patch("cruiseplan.utils.coordinates.calculate_map_bounds")
    @patch("cruiseplan.output.map_generator.extract_map_data")
    @patch("matplotlib.pyplot.subplots")
    @patch("matplotlib.pyplot.show")
    def test_generate_map_show_plot(
        self,
        mock_show,
        mock_subplots,
        mock_extract,
        mock_calc_bounds,
        mock_plot_bathy,
        mock_plot_elements,
    ):
        """Test map generation with show_plot=True."""
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        mock_extract.return_value = {
            "lats": [60.0],
            "lons": [-20.0],
            "departure_port": None,
            "arrival_port": None,
        }
        mock_calc_bounds.return_value = (-25, -15, 55, 65)
        mock_plot_bathy.return_value = True

        generate_map(MagicMock(), "cruise", show_plot=True)

        mock_show.assert_called_once()
        # Should not call savefig when showing


class TestGenerateMapFromYaml:
    """Test YAML-based map generation function."""

    @patch("cruiseplan.output.map_generator.generate_map")
    def test_generate_map_from_yaml(self, mock_generate):
        """Test that generate_map_from_yaml calls generate_map with correct parameters."""
        mock_cruise = MagicMock()
        output_file = Path("/tmp/test.png")

        mock_generate.return_value = output_file

        result = generate_map_from_yaml(
            mock_cruise,
            output_file=output_file,
            bathymetry_source="etopo2022",
            bathymetry_stride=10,
            show_plot=True,
            figsize=(14, 12),
        )

        assert result == output_file
        mock_generate.assert_called_once_with(
            data_source=mock_cruise,
            source_type="cruise",
            output_file=output_file,
            bathymetry_source="etopo2022",
            bathymetry_stride=10,
            bathymetry_dir="data",
            show_plot=True,
            figsize=(14, 12),
        )


class TestGenerateMapFromTimeline:
    """Test timeline-based map generation function."""

    @patch("cruiseplan.output.map_generator.generate_map")
    def test_generate_map_from_timeline(self, mock_generate):
        """Test that generate_map_from_timeline calls generate_map with correct parameters."""
        timeline = [{"lat": 60.0, "lon": -20.0, "activity": "STN_001"}]
        config = MagicMock()
        output_file = Path("/tmp/timeline.png")

        mock_generate.return_value = output_file

        result = generate_map_from_timeline(
            timeline,
            output_file=output_file,
            bathymetry_source="gebco2025",
            bathymetry_stride=5,
            figsize=(12, 10),
            config=config,
        )

        assert result == output_file

        # Should call generate_map with timeline data structure
        call_args = mock_generate.call_args
        assert call_args.kwargs["source_type"] == "timeline"
        assert call_args.kwargs["output_file"] == output_file
        assert call_args.kwargs["bathymetry_source"] == "gebco2025"
        assert call_args.kwargs["bathymetry_stride"] == 5
        assert call_args.kwargs["figsize"] == (12, 10)

        # Check that timeline data includes config
        # The data_source should be passed as a keyword argument
        assert "data_source" in call_args.kwargs
        timeline_data = call_args.kwargs["data_source"]
        assert timeline_data["timeline"] == timeline
        assert timeline_data["config"] == config


class TestGenerateFoliumMap:
    """Test Folium-based interactive map generation."""

    @patch("cruiseplan.output.map_generator.folium")
    def test_generate_folium_map_basic(self, mock_folium):
        """Test basic Folium map generation."""
        # Mock folium objects
        mock_map = MagicMock()
        mock_folium.Map.return_value = mock_map

        tracks = [
            {
                "latitude": [60.0, 61.0],
                "longitude": [-20.0, -21.0],
                "label": "Test Track",
                "dois": ["10.1000/test"],
            }
        ]

        output_file = Path("/tmp/test_map.html")

        result = generate_folium_map(tracks, output_file)

        assert result == output_file.resolve()
        mock_folium.Map.assert_called_once()
        mock_map.save.assert_called_once()

    def test_generate_folium_map_no_tracks(self):
        """Test Folium map generation with no tracks."""
        result = generate_folium_map([], Path("/tmp/empty.html"))

        assert result is None

    @patch("cruiseplan.output.map_generator.folium")
    def test_generate_folium_map_empty_coordinates(self, mock_folium):
        """Test Folium map generation with empty coordinates."""
        mock_map = MagicMock()
        mock_folium.Map.return_value = mock_map

        tracks = [{"latitude": [], "longitude": [], "label": "Empty Track", "dois": []}]

        result = generate_folium_map(tracks, Path("/tmp/empty.html"))

        assert result is None

    @patch("cruiseplan.output.map_generator.folium")
    def test_generate_folium_map_multiple_tracks(self, mock_folium):
        """Test Folium map generation with multiple tracks."""
        mock_map = MagicMock()
        mock_folium.Map.return_value = mock_map

        tracks = [
            {
                "latitude": [60.0, 61.0],
                "longitude": [-20.0, -21.0],
                "label": "Track 1",
                "dois": ["10.1000/test1"],
            },
            {
                "latitude": [62.0, 63.0],
                "longitude": [-22.0, -23.0],
                "label": "Track 2",
                "dois": ["10.1000/test2"],
            },
        ]

        output_file = Path("/tmp/multi_track.html")

        result = generate_folium_map(tracks, output_file)

        assert result == output_file.resolve()
        # Should add multiple polylines and markers
        assert mock_folium.PolyLine.call_count == 2
        assert mock_folium.Marker.call_count == 4  # 2 start + 2 end markers
