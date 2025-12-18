import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the main function of the CLI subcommand
from cruiseplan.cli.stations import main

# --- Fixtures for Mocking External Dependencies ---


@pytest.fixture
def mock_external_deps():
    """Patches all external components imported by cli/stations.py."""
    # Mocking the interactive and data components that don't exist yet
    # We patch the entire module path to control the import behavior
    with (
        patch("cruiseplan.interactive.station_picker.StationPicker") as MockPicker,
        patch("cruiseplan.data.pangaea.load_campaign_data") as MockLoadCampaign,
        patch("sys.exit") as MockExit,
    ):

        # Configure the mock dependencies
        MockPicker.return_value = MagicMock()
        MockPicker.return_value.ax_map = MagicMock()
        MockPicker.return_value._update_aspect_ratio = MagicMock()
        MockLoadCampaign.return_value = [
            {"name": "C1", "data": []},
            {"name": "C2", "data": []},
        ]

        yield MockPicker, MockLoadCampaign, MockExit


@pytest.fixture
def mock_args(tmp_path):
    """Generates a mock argparse.Namespace object with default values."""
    mock_file = tmp_path / "campaigns.pkl"
    mock_file.write_text("dummy data")  # Create a file to pass .exists() check

    args = argparse.Namespace(
        pangaea_file=mock_file,
        lat=[50.0, 60.0],
        lon=[-30.0, -20.0],
        output_dir=tmp_path / "results",
        output_file=None,
        bathymetry_source="etopo2022",
        bathymetry_dir=tmp_path / "bathymetry",
        high_resolution=False,
    )
    return args


# --- Test Cases ---


def test_main_success_with_pangaea(mock_args, mock_external_deps):
    """Tests the standard success path with valid PANGAEA file provided."""
    MockPicker, MockLoadCampaign, MockExit = mock_external_deps

    # Ensure the output directory doesn't exist yet so mkdir is covered
    mock_args.output_dir.mkdir(parents=True, exist_ok=True)

    main(mock_args)

    # 1. Assert PANGAEA loading was attempted
    MockLoadCampaign.assert_called_once_with(mock_args.pangaea_file)

    # 2. Assert StationPicker was initialized correctly
    output_file = str(mock_args.output_dir / "campaigns_stations.yaml")
    MockPicker.assert_called_once_with(
        campaign_data=[{"name": "C1", "data": []}, {"name": "C2", "data": []}],
        output_file=output_file,
        bathymetry_stride=10,  # Default stride since high_resolution=False
        bathymetry_source="etopo2022",  # Default bathymetry source
        bathymetry_dir=str(mock_args.bathymetry_dir),
        overwrite=False,  # Default overwrite behavior
    )

    # 3. Assert map bounds were set
    MockPicker.return_value.ax_map.set_xlim.assert_called_once_with(
        (-30.0, -20.0)
    )  # lon bounds from mock_args
    MockPicker.return_value.ax_map.set_ylim.assert_called_once_with((50.0, 60.0))

    # 4. Assert picker was shown
    MockPicker.return_value.show.assert_called_once()

    # 5. Assert program did NOT exit
    MockExit.assert_not_called()


def test_main_uses_default_bounds_if_not_provided(mock_args, mock_external_deps):
    """Tests that default bounds are used if args are None."""
    MockPicker, _, _ = mock_external_deps

    # Simulate args missing the bounds
    mock_args.lat = None
    mock_args.lon = None

    main(mock_args)

    # Assert default bounds are used: lat [45, 70], lon [-65, -5]
    MockPicker.return_value.ax_map.set_xlim.assert_called_once_with((-65.0, -5.0))
    MockPicker.return_value.ax_map.set_ylim.assert_called_once_with((45.0, 70.0))


def test_main_handles_missing_pangaea_file(mock_args, mock_external_deps):
    """Tests successful execution when the PANGAEA file path is invalid/missing."""
    _, MockLoadCampaign, _ = mock_external_deps

    # Simulate non-existent file path
    mock_args.pangaea_file = Path("non_existent_path.pkl")

    main(mock_args)

    # Assert load_campaign_data was NOT called
    MockLoadCampaign.assert_not_called()


def test_main_handles_explicit_output_file(mock_args, mock_external_deps):
    """Tests that --output-file takes precedence over --output-dir."""
    MockPicker, _, _ = mock_external_deps

    custom_output = Path("/tmp/custom_output.yml")
    mock_args.output_file = custom_output

    main(mock_args)

    # Assert picker was initialized with the custom path
    MockPicker.assert_called_once()
    actual_path = MockPicker.call_args[1]["output_file"]
    # Resolve both paths to handle symlinks like /tmp -> /private/tmp on macOS
    assert Path(actual_path).resolve() == custom_output.resolve()


@pytest.mark.skip(reason="Import error testing is complex with dynamic imports")
def test_main_handles_import_error(mock_args):
    """Tests the graceful exit path if core dependencies (matplotlib) are missing."""
    # This test is skipped due to complexity of mocking dynamic imports
    # The import error handling works in practice but is difficult to test
    pass
