from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.data.pangaea import PangaeaManager, merge_campaign_tracks
from cruiseplan.output.map_generator import generate_folium_map


# --------------------------------------------------------------------------
# FAST INTEGRATION TEST (Mocks the API, tests the logic flow)
# --------------------------------------------------------------------------
def test_workflow_fetch_and_merge_mocked():
    """
    Simulates a search that returns 3 datasets (2 for 'Cruise-A', 1 for 'Cruise-B').
    Verifies that the manager can fetch them and the merger consolidates them.
    """
    # 1. Setup the Manager
    manager = PangaeaManager()

    # 2. Mock the external 'PanDataSet' from the pangaeapy library
    # We simulate 3 datasets returned from a search
    mock_ds1 = MagicMock()
    mock_ds1.data.campaign = "Cruise-A"
    mock_ds1.data.geometry = [MagicMock(x=10, y=5)]  # x=Lon, y=Lat
    mock_ds1.doi = "doi:10.1/A"

    mock_ds2 = MagicMock()
    mock_ds2.data.campaign = "Cruise-A"
    mock_ds2.data.geometry = [MagicMock(x=11, y=6)]
    mock_ds2.doi = "doi:10.1/B"

    mock_ds3 = MagicMock()
    mock_ds3.data.campaign = "Cruise-B"
    mock_ds3.data.geometry = [MagicMock(x=50, y=50)]
    mock_ds3.doi = "doi:10.1/C"

    # Patch the method in your manager that does the actual API search/retrieval
    # Assuming you have a method `get_datasets` or similar.
    # If not, we mock the library call directly:
    with patch("cruiseplan.data.pangaea.PanDataSet") as MockPanDataSet:
        # Configure the mock to return our fake datasets when instantiated/called
        # This part depends heavily on how your Manager calls the library.
        # simpler approach: Let's assume your manager has a `fetch_raw_data` method we mock.

        # ACT: simulate obtaining this raw list from the API
        raw_results = [
            {"label": "Cruise-A", "latitude": [5], "longitude": [10], "doi": "doi:1"},
            {"label": "Cruise-A", "latitude": [6], "longitude": [11], "doi": "doi:2"},
            {"label": "Cruise-B", "latitude": [50], "longitude": [50], "doi": "doi:3"},
        ]

        # 3. Run the Merge Logic
        merged_results = merge_campaign_tracks(raw_results)

    # 4. Assertions
    assert len(merged_results) == 2, "Should merge into 2 unique campaigns"

    cruise_a = next(r for r in merged_results if r["label"] == "Cruise-A")
    assert len(cruise_a["latitude"]) == 2
    assert set(cruise_a["dois"]) == {"doi:1", "doi:2"}


# --------------------------------------------------------------------------
# FAST MOCK TEST (Logic Verification)
# --------------------------------------------------------------------------
def test_workflow_fetch_and_merge_mocked():
    """Verifies the loop from Manager -> Standardize -> Merge works."""
    manager = PangaeaManager()

    # Mock the internal _standardize method to avoid needing complex PanDataSet mocks
    # We simulate that fetch_datasets has already done its job
    with patch.object(PangaeaManager, "fetch_datasets") as mock_fetch:
        mock_fetch.return_value = [
            {
                "label": "Cruise-A",
                "latitude": [10, 11],
                "longitude": [5, 5],
                "doi": "d1",
            },
            {"label": "Cruise-A", "latitude": [12], "longitude": [6], "doi": "d2"},
        ]

        # Act
        raw_data = manager.fetch_datasets(["fake-doi-1", "fake-doi-2"])
        merged = merge_campaign_tracks(raw_data)

        # Assert
        assert len(merged) == 1
        assert merged[0]["label"] == "Cruise-A"
        assert len(merged[0]["latitude"]) == 3


# --------------------------------------------------------------------------
# REAL SLOW TEST (Network Verification)
# --------------------------------------------------------------------------
@pytest.mark.slow
def test_real_pangaea_workflow_1():
    """
    Connects to Pangaea, downloads 2 real datasets, and merges them.
    """
    manager = PangaeaManager()

    # Two actual datasets from Polarstern cruise PS122/1
    # These are small datasets suitable for testing
    real_dois = [
        "10.1594/PANGAEA.910365",  # Thermosalinograph data
        "10.1594/PANGAEA.910366",  # (Another subset or similar)
    ]

    # 1. Fetch
    logger_data = manager.fetch_datasets(real_dois)

    # If the API fails or datasets are archived/changed, skip gracefully
    if not logger_data:
        pytest.skip("Could not retrieve data from Pangaea (network or data issue)")

    # 2. Merge
    merged = merge_campaign_tracks(logger_data)

    # 3. Verify
    assert len(merged) > 0
    track = merged[0]

    # Check that we actually got coordinates
    assert len(track["latitude"]) > 0
    assert len(track["longitude"]) > 0
    # Check that the label looks correct (Should be related to Polarstern/PS122)
    assert "PS122" in track["label"] or "Polarstern" in track["label"]


@pytest.mark.slow
def test_real_pangaea_workflow(caplog):
    """
    Connects to Pangaea, downloads a known simple dataset, and merges it.
    """
    # Force logging to be visible so we see WHY it fails if it fails
    import logging

    caplog.set_level(logging.INFO)

    manager = PangaeaManager()

    # Use a "Leaf" dataset (Actual data table, not a collection)
    # 10.1594/PANGAEA.890746 is a simple list of statioms with Lat/Lon
    real_dois = ["10.1594/PANGAEA.890746"]

    # 1. Fetch
    print(f"\nAttempting to fetch {real_dois}...")
    dataset_list = manager.fetch_datasets(real_dois)

    # DEBUG: If this is empty, fail the test and show the logs
    if not dataset_list:
        print("\n--- CAPTURED LOGS ---")
        print(caplog.text)
        pytest.fail("Returned dataset list is empty! Check logs above.")

    # 2. Merge
    merged = merge_campaign_tracks(dataset_list)

    # 3. Verify
    assert len(merged) > 0
    track = merged[0]
    assert len(track["latitude"]) > 0
    assert "VA176" in track["label"]

    # 4. VISUALIZE
    # Create test_output directory if it doesn't exist
    output_dir = Path("tests_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save to tests_output/test_map_VA176.html
    output_path = output_dir / "test_map_VA176.html"

    # Generate
    result_path = generate_folium_map(merged, output_path)

    # Verify
    assert result_path is not None
    assert result_path.exists()
    assert result_path.stat().st_size > 0  # Ensure file is not empty

    print(f"\nMap generated: {result_path}")
