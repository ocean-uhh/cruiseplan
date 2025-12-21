"""
Integration tests for CLI commands.

These tests verify end-to-end functionality of CLI commands with
realistic data and workflows.
"""

import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPangaeaIntegration:
    """Integration tests for PANGAEA command."""

    def create_test_doi_file(self, tmp_path):
        """Create a test DOI file."""
        doi_file = tmp_path / "test_dois.txt"
        doi_content = """
        # Test DOI list
        10.1594/PANGAEA.12345
        10.1594/PANGAEA.67890
        """
        doi_file.write_text(doi_content)
        return doi_file

    @patch("cruiseplan.cli.pangaea.PangaeaManager")
    def test_pangaea_end_to_end(self, mock_pangaea_class, tmp_path):
        """Test complete PANGAEA workflow."""
        from argparse import Namespace

        from cruiseplan.cli.pangaea import main

        # Setup test data
        doi_file = self.create_test_doi_file(tmp_path)
        output_file = tmp_path / "pangaea_data.pkl"

        # Mock PANGAEA data
        mock_pangaea = MagicMock()
        mock_pangaea_class.return_value = mock_pangaea
        mock_pangaea.fetch_datasets.return_value = [
            {
                "label": "Test Campaign",
                "latitude": [50.0, 51.0],
                "longitude": [-10.0, -11.0],
                "events": [{"lat": 50.0, "lon": -10.0}],
            }
        ]

        # Create args (new unified format)
        args = Namespace(
            query_or_file=str(doi_file),
            output_dir=None,
            output_file=output_file,
            rate_limit=10.0,  # Fast for testing
            merge_campaigns=True,
            verbose=False,
            quiet=False,
            lat=None,
            lon=None,
            limit=None,
        )

        # Execute command
        main(args)

        # Verify output file exists and contains data
        assert output_file.exists()

        with open(output_file, "rb") as f:
            data = pickle.load(f)

        assert len(data) == 1
        assert data[0]["label"] == "Test Campaign"


class TestStationsIntegration:
    """Integration tests for stations command."""

    def create_test_pangaea_file(self, tmp_path):
        """Create a test PANGAEA pickle file."""
        pangaea_file = tmp_path / "test_pangaea.pkl"
        pangaea_data = [
            {
                "label": "Test Campaign",
                "latitude": [50.0, 51.0, 52.0],
                "longitude": [-10.0, -11.0, -12.0],
                "dois": ["10.1594/PANGAEA.12345"],
            }
        ]

        with open(pangaea_file, "wb") as f:
            pickle.dump(pangaea_data, f)

        return pangaea_file

    @patch("cruiseplan.interactive.station_picker.StationPicker")
    @patch("matplotlib.pyplot.show")
    def test_stations_with_pangaea(self, mock_show, mock_picker_class, tmp_path):
        """Test stations command with PANGAEA data."""
        from argparse import Namespace

        from cruiseplan.cli.stations import main

        # Setup test data
        pangaea_file = self.create_test_pangaea_file(tmp_path)
        output_file = tmp_path / "stations.yaml"

        # Mock station picker
        mock_picker = MagicMock()
        mock_picker_class.return_value = mock_picker

        # Create args
        args = Namespace(
            pangaea_file=pangaea_file,
            lat=None,  # Should use bounds from PANGAEA data
            lon=None,
            output_dir=None,
            output_file=output_file,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            high_resolution=False,
            verbose=False,
            quiet=False,
        )

        # Execute command
        main(args)

        # Verify picker was initialized and called
        mock_picker_class.assert_called_once()
        mock_picker.show.assert_called_once()

        # Verify coordinate bounds were set based on PANGAEA data
        call_args = mock_picker_class.call_args
        assert call_args[1]["campaign_data"] is not None

    @patch("cruiseplan.interactive.station_picker.StationPicker")
    @patch("matplotlib.pyplot.show")
    def test_stations_without_pangaea(self, mock_show, mock_picker_class, tmp_path):
        """Test stations command without PANGAEA data."""
        from argparse import Namespace

        from cruiseplan.cli.stations import main

        output_file = tmp_path / "stations.yaml"

        # Mock station picker
        mock_picker = MagicMock()
        mock_picker_class.return_value = mock_picker

        # Create args
        args = Namespace(
            pangaea_file=None,
            lat=[50.0, 60.0],
            lon=[-20.0, -10.0],
            output_dir=None,
            output_file=output_file,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            high_resolution=False,
            verbose=False,
            quiet=False,
        )

        # Execute command
        main(args)

        # Verify picker was initialized with explicit bounds
        mock_picker_class.assert_called_once()
        call_args = mock_picker_class.call_args
        assert call_args[1]["campaign_data"] is None


class TestScheduleIntegration:
    """Integration tests for schedule command with real data."""

    def get_fixture_path(self, filename: str) -> Path:
        """Get path to test fixture file."""
        return Path(__file__).parent.parent / "fixtures" / filename


class TestWorkflowIntegration:
    """Test complete workflow integration."""

    @patch("cruiseplan.cli.pangaea.PangaeaManager")
    @patch("cruiseplan.interactive.station_picker.StationPicker")
    @patch("matplotlib.pyplot.show")
    def test_pangaea_to_stations_workflow(
        self, mock_show, mock_picker_class, mock_pangaea_class, tmp_path
    ):
        """Test workflow from PANGAEA fetching to station picking."""
        from argparse import Namespace

        from cruiseplan.cli.pangaea import main as pangaea_main
        from cruiseplan.cli.stations import main as stations_main

        # Step 1: Create DOI file and fetch PANGAEA data
        doi_file = tmp_path / "dois.txt"
        doi_file.write_text("10.1594/PANGAEA.12345\n10.1594/PANGAEA.67890")

        pangaea_file = tmp_path / "pangaea_data.pkl"

        # Mock PANGAEA fetch
        mock_pangaea = MagicMock()
        mock_pangaea_class.return_value = mock_pangaea
        mock_pangaea.fetch_datasets.return_value = [
            {
                "label": "Workflow Test Campaign",
                "latitude": [55.0, 56.0],
                "longitude": [-15.0, -14.0],
                "events": [{"lat": 55.0, "lon": -15.0}],
            }
        ]

        pangaea_args = Namespace(
            query_or_file=str(doi_file),
            output_dir=None,
            output_file=pangaea_file,
            rate_limit=10.0,
            merge_campaigns=True,
            verbose=False,
            quiet=False,
            lat=None,
            lon=None,
            limit=None,
        )

        # Execute PANGAEA command
        pangaea_main(pangaea_args)

        # Verify PANGAEA file was created
        assert pangaea_file.exists()

        # Step 2: Use PANGAEA data for station picking
        stations_file = tmp_path / "stations.yaml"

        mock_picker = MagicMock()
        mock_picker_class.return_value = mock_picker

        stations_args = Namespace(
            pangaea_file=pangaea_file,
            lat=None,
            lon=None,
            output_dir=None,
            output_file=stations_file,
            bathymetry_source="etopo2022",
            bathymetry_dir=Path("data"),
            high_resolution=False,
            verbose=False,
            quiet=False,
        )

        # Execute stations command
        stations_main(stations_args)

        # Verify stations picker was called with PANGAEA data
        mock_picker_class.assert_called_once()
        call_args = mock_picker_class.call_args
        campaign_data = call_args[1]["campaign_data"]

        assert campaign_data is not None
        assert len(campaign_data) == 1
        assert campaign_data[0]["label"] == "Workflow Test Campaign"


class TestErrorHandling:
    """Test error handling in CLI commands."""

    def test_pangaea_invalid_doi_file(self, tmp_path):
        """Test PANGAEA command with invalid DOI file."""
        from argparse import Namespace

        from cruiseplan.cli.pangaea import main

        # Create invalid DOI file
        doi_file = tmp_path / "invalid_dois.txt"
        doi_file.write_text("not-a-doi\ninvalid-format")

        args = Namespace(
            doi_file=doi_file,
            output_dir=tmp_path,
            output_file=None,
            rate_limit=1.0,
            merge_campaigns=True,
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit):
            main(args)

    def test_stations_invalid_bounds(self, tmp_path):
        """Test stations command with invalid coordinate bounds."""
        from argparse import Namespace

        from cruiseplan.cli.stations import main

        args = Namespace(
            pangaea_file=None,
            lat=[100.0, 110.0],  # Invalid latitude range
            lon=[-20.0, -10.0],
            output_dir=tmp_path,
            output_file=None,
            bathymetry_source="etopo2022",
            verbose=False,
            quiet=False,
        )

        with pytest.raises(SystemExit):
            main(args)


class TestOutputGeneration:
    """Test output file generation and naming."""

    def test_auto_generated_filenames(self, tmp_path):
        """Test automatic filename generation."""
        from cruiseplan.cli.utils import generate_output_filename

        # Test different input files and suffixes
        test_cases = [
            (Path("cruise.yaml"), "_processed", "cruise_processed.yaml"),
            (Path("data.pkl"), "_stations", "data_stations.pkl"),
            (Path("test"), "_output", "test_output"),
        ]

        for input_path, suffix, expected in test_cases:
            result = generate_output_filename(input_path, suffix)
            assert result == expected

    def test_output_directory_creation(self, tmp_path):
        """Test output directory creation."""
        from cruiseplan.cli.utils import validate_output_path

        # Test nested directory creation
        nested_path = tmp_path / "level1" / "level2" / "output.txt"

        result = validate_output_path(output_file=nested_path)

        assert result == nested_path.resolve()
        assert nested_path.parent.exists()


if __name__ == "__main__":
    pytest.main([__file__])
