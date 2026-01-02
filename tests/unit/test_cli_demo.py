"""Tests for cruiseplan.cli.demo module."""

import pytest
from unittest.mock import Mock, patch, call
from io import StringIO

from cruiseplan.cli.demo import main


class TestDemoMain:
    """Test suite for the demo main function."""

    @patch('cruiseplan.cli.demo.StationPicker')
    @patch('cruiseplan.cli.demo.PangaeaManager')
    @patch('cruiseplan.cli.demo.bathymetry')
    @patch('builtins.print')
    def test_main_function_complete_flow(self, mock_print, mock_bathymetry, mock_pangaea_class, mock_station_picker_class):
        """Test the complete demo flow with mocked dependencies."""
        # Setup mocks
        mock_bathymetry.get_depth_at_point.return_value = -2750.0
        
        mock_pangaea = Mock()
        mock_pangaea_class.return_value = mock_pangaea
        mock_pangaea.fetch_datasets.return_value = [
            {
                "label": "Test_Campaign",
                "latitude": [50.5, 51.0],
                "longitude": [-45.0, -44.0],
                "doi": "10.1594/PANGAEA.123456",
            }
        ]
        
        mock_picker = Mock()
        mock_station_picker_class.return_value = mock_picker

        # Run the demo
        main()

        # Verify bathymetry was tested
        mock_bathymetry.get_depth_at_point.assert_called_once_with(47.5, -52.0)
        
        # Verify PANGAEA manager was created and used
        mock_pangaea_class.assert_called_once()
        mock_pangaea.fetch_datasets.assert_called_once_with(["10.1594/PANGAEA.890663"])
        
        # Verify station picker was created with correct parameters
        mock_station_picker_class.assert_called_once_with(
            campaign_data=[{
                "label": "Test_Campaign",
                "latitude": [50.5, 51.0],
                "longitude": [-45.0, -44.0],
                "doi": "10.1594/PANGAEA.123456",
            }],
            output_file="demo_stations.yaml"
        )
        
        # Verify UI was shown
        mock_picker.show.assert_called_once()

        # Check that appropriate print statements were made
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert "   CRUISEPLAN - INTERACTIVE DEMO" in print_calls
        assert "\n1. Testing Bathymetry Layer..." in print_calls
        assert "\n2. Fetching Campaign Data..." in print_calls
        assert "\n3. Launching Station Picker UI..." in print_calls
        assert "\nDemo Complete. Check 'demo_stations.yaml' for results." in print_calls

    @patch('cruiseplan.cli.demo.StationPicker')
    @patch('cruiseplan.cli.demo.PangaeaManager')
    @patch('cruiseplan.cli.demo.bathymetry')
    @patch('builtins.print')
    def test_main_with_failed_pangaea_fetch(self, mock_print, mock_bathymetry, mock_pangaea_class, mock_station_picker_class):
        """Test demo behavior when PANGAEA fetch fails."""
        # Setup mocks
        mock_bathymetry.get_depth_at_point.return_value = -9999.0
        
        mock_pangaea = Mock()
        mock_pangaea_class.return_value = mock_pangaea
        mock_pangaea.fetch_datasets.return_value = []  # Empty result simulates failure
        
        mock_picker = Mock()
        mock_station_picker_class.return_value = mock_picker

        # Run the demo
        main()

        # Verify dummy data was used when real fetch failed
        expected_dummy_data = [
            {
                "label": "Expedition_A",
                "latitude": [50, 51, 52],
                "longitude": [-45, -44, -43],
                "doi": "10.dummy/a",
            },
            {
                "label": "Expedition_B",
                "latitude": [53, 53.5, 54],
                "longitude": [-40, -38, -36],
                "doi": "10.dummy/b",
            },
        ]
        
        mock_station_picker_class.assert_called_once_with(
            campaign_data=expected_dummy_data,
            output_file="demo_stations.yaml"
        )

        # Check that failure message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Real fetch failed (offline?), using Dummy Data." in call for call in print_calls)

    @patch('cruiseplan.cli.demo.StationPicker')
    @patch('cruiseplan.cli.demo.PangaeaManager')
    @patch('cruiseplan.cli.demo.bathymetry')
    @patch('builtins.print')
    def test_main_with_successful_pangaea_fetch(self, mock_print, mock_bathymetry, mock_pangaea_class, mock_station_picker_class):
        """Test demo behavior when PANGAEA fetch succeeds."""
        # Setup mocks
        mock_bathymetry.get_depth_at_point.return_value = -2750.0
        
        mock_pangaea = Mock()
        mock_pangaea_class.return_value = mock_pangaea
        
        # Return multiple datasets to test success case
        test_datasets = [
            {"label": "Campaign1", "latitude": [50], "longitude": [-45], "doi": "10.1594/PANGAEA.1"},
            {"label": "Campaign2", "latitude": [51], "longitude": [-44], "doi": "10.1594/PANGAEA.2"},
            {"label": "Campaign3", "latitude": [52], "longitude": [-43], "doi": "10.1594/PANGAEA.3"},
        ]
        mock_pangaea.fetch_datasets.return_value = test_datasets
        
        mock_picker = Mock()
        mock_station_picker_class.return_value = mock_picker

        # Run the demo
        main()

        # Verify real data was used
        mock_station_picker_class.assert_called_once_with(
            campaign_data=test_datasets,
            output_file="demo_stations.yaml"
        )

        # Check that success message was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        assert any("Fetched 3 campaigns." in call for call in print_calls)

    @patch('cruiseplan.cli.demo.StationPicker')
    @patch('cruiseplan.cli.demo.PangaeaManager')
    @patch('cruiseplan.cli.demo.bathymetry')
    def test_main_bathymetry_depth_values(self, mock_bathymetry, mock_pangaea_class, mock_station_picker_class):
        """Test various bathymetry depth return values."""
        # Setup other mocks
        mock_pangaea = Mock()
        mock_pangaea_class.return_value = mock_pangaea
        mock_pangaea.fetch_datasets.return_value = []
        
        mock_picker = Mock()
        mock_station_picker_class.return_value = mock_picker

        # Test different depth values
        for depth_value in [-9999.0, -2750.0, -3500.0, 0.0]:
            mock_bathymetry.get_depth_at_point.return_value = depth_value
            
            # Should run without errors regardless of depth value
            main()
            
            # Verify the depth lookup was called correctly
            mock_bathymetry.get_depth_at_point.assert_called_with(47.5, -52.0)