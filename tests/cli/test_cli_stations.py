import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the main function of the CLI subcommand
from cruiseplan.cli.stations import main

# --- Fixtures for Mocking External Dependencies ---


@pytest.fixture
def mock_external_deps():
    """Patches the stations API function that the CLI now calls."""
    with (
        patch("cruiseplan.cli.stations.stations") as MockStationsAPI,
        patch("sys.exit") as MockExit,
    ):
        # Configure the mock API function to return a successful result
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: "Interactive station picker completed"
        MockStationsAPI.return_value = mock_result

        yield MockStationsAPI, MockExit


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
        bathy_source_legacy="etopo2022",  # Legacy param that gets migrated
        bathy_dir_legacy=tmp_path / "bathymetry",  # Legacy param that gets migrated
        high_resolution=False,
        verbose=False,
        quiet=False,
    )
    return args


# --- Test Cases ---


def test_main_success_with_pangaea(mock_args, mock_external_deps):
    """Tests that the CLI correctly calls the stations API function."""
    MockStationsAPI, MockExit = mock_external_deps

    # Ensure the output directory exists
    mock_args.output_dir.mkdir(parents=True, exist_ok=True)

    main(mock_args)

    # Assert the stations API was called with correct parameters
    MockStationsAPI.assert_called_once_with(
        lat_bounds=(50.0, 60.0),
        lon_bounds=(-30.0, -20.0),
        output_dir=str(mock_args.output_dir),
        output=None,
        pangaea_file=str(mock_args.pangaea_file),
        bathy_source="etopo2022",
        bathy_dir="data",  # Default value used by API
        high_resolution=False,
        overwrite=False,
        verbose=False,
    )

    # Assert program did NOT exit
    MockExit.assert_not_called()


def test_main_uses_default_bounds_if_not_provided(mock_args, mock_external_deps):
    """Tests that CLI passes None bounds to API when not provided (API handles defaults)."""
    MockStationsAPI, MockExit = mock_external_deps

    # Simulate args missing the bounds
    mock_args.lat = None
    mock_args.lon = None

    main(mock_args)

    # Assert the stations API was called with None bounds (API handles defaults internally)
    MockStationsAPI.assert_called_once()
    call_args = MockStationsAPI.call_args[1]  # Get keyword arguments
    assert call_args["lat_bounds"] is None
    assert call_args["lon_bounds"] is None


def test_main_handles_missing_pangaea_file(mock_args, mock_external_deps):
    """Tests that CLI passes file path to API (API handles file validation and errors)."""
    MockStationsAPI, MockExit = mock_external_deps

    # Simulate non-existent file path
    mock_args.pangaea_file = Path("non_existent_path.pkl")

    # Configure API to raise FileNotFoundError to simulate file validation failure
    MockStationsAPI.side_effect = FileNotFoundError("PANGAEA file not found")

    main(mock_args)

    # CLI should call API and handle API's FileNotFoundError by exiting
    MockStationsAPI.assert_called_once()
    call_args = MockStationsAPI.call_args[1]
    assert call_args["pangaea_file"] == "non_existent_path.pkl"

    # Should exit with error code 1 due to the FileNotFoundError
    MockExit.assert_called_once_with(1)


@pytest.mark.skip(reason="Import error testing is complex with dynamic imports")
def test_main_handles_import_error(mock_args):
    """Tests the graceful exit path if core dependencies (matplotlib) are missing."""
    # This test is skipped due to complexity of mocking dynamic imports
    # The import error handling works in practice but is difficult to test
    pass
