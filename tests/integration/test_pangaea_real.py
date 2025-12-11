from pathlib import Path

import pytest

from cruiseplan.data.pangaea import PangaeaManager

# List provided by user
REAL_DOIS = ["10.1594/PANGAEA.859930", "10.1594/PANGAEA.890362"]


@pytest.mark.slow
def test_real_pangaea_connection(tmp_path):
    """
    Integration test hitting the actual API.
    Verifies that the column normalizer works on real-world dirty data.
    """
    manager = PangaeaManager(cache_dir=str(tmp_path))

    # This now returns a List[Dict], not a Dict[str, DataFrame]
    results = manager.fetch_datasets(REAL_DOIS)

    # Check that we got data back
    assert len(results) == len(REAL_DOIS)

    for dataset in results:
        # 1. It's now a Dictionary, so check keys instead of df.columns
        assert "latitude" in dataset
        assert "longitude" in dataset

        # 2. Check for data presence instead of df.empty
        # (The standardized dict likely has lists of floats)
        assert len(dataset["latitude"]) > 0
        assert len(dataset["longitude"]) > 0

        # 3. Verify coordinates are numeric
        # Check the first value in the list
        first_lat = dataset["latitude"][0]
        assert isinstance(first_lat, (float, int))


@pytest.mark.slow
def test_pangaea_natl_campaign_validation():
    """
    Test real PANGAEA data fetching with North Atlantic campaign data.

    This test validates that the actual PANGAEA API returns expected
    campaign labels and station counts for the test fixture DOIs.

    Expected results:
    - MSM21/1a: 91 stations
    - VA176: 89 stations
    - DY081: 1 station (appears twice, so 2 datasets total)
    """
    # Load test DOI list
    fixture_path = Path(__file__).parent.parent / "fixtures" / "pangaea_list_NAtl.txt"
    assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"

    # Read DOIs from fixture
    with open(fixture_path) as f:
        dois = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # Expected to have 4 DOIs based on the edited fixture
    assert len(dois) == 4, f"Expected 4 DOIs in fixture, got {len(dois)}"

    # Fetch data from PANGAEA
    manager = PangaeaManager()
    datasets = manager.fetch_datasets(dois, rate_limit=0.5)  # Be polite to API

    # Should get 4 datasets (one per DOI)
    assert len(datasets) == 4, f"Expected 4 datasets, got {len(datasets)}"

    # Group datasets by campaign label
    campaigns = {}
    for dataset in datasets:
        label = dataset.get("label", "Unknown")
        if label not in campaigns:
            campaigns[label] = []
        campaigns[label].append(dataset)

    # Validate expected campaigns exist
    expected_campaigns = {"MSM21/1a", "VA176", "DY081"}
    actual_campaigns = set(campaigns.keys())
    assert (
        actual_campaigns == expected_campaigns
    ), f"Expected campaigns {expected_campaigns}, got {actual_campaigns}"

    # Validate station counts for each campaign
    expected_counts = {
        "MSM21/1a": 91,
        "VA176": 89,
        "DY081": 1,  # Per dataset, but there are 2 DY081 datasets
    }

    for campaign_label, expected_count in expected_counts.items():
        campaign_datasets = campaigns[campaign_label]

        if campaign_label == "DY081":
            # DY081 should have 2 datasets, each with 1 station
            assert (
                len(campaign_datasets) == 2
            ), f"Expected 2 DY081 datasets, got {len(campaign_datasets)}"
            for dataset in campaign_datasets:
                events_count = len(dataset.get("events", []))
                station_count = len(dataset.get("latitude", []))
                actual_count = max(events_count, station_count)
                assert (
                    actual_count == expected_count
                ), f"DY081 dataset expected {expected_count} stations, got {actual_count}"
        else:
            # MSM21/1a and VA176 should have 1 dataset each
            assert (
                len(campaign_datasets) == 1
            ), f"Expected 1 {campaign_label} dataset, got {len(campaign_datasets)}"
            dataset = campaign_datasets[0]
            events_count = len(dataset.get("events", []))
            station_count = len(dataset.get("latitude", []))
            actual_count = max(events_count, station_count)
            assert (
                actual_count == expected_count
            ), f"{campaign_label} expected {expected_count} stations, got {actual_count}"

    # Validate that all datasets have required fields
    for dataset in datasets:
        assert "label" in dataset, "Dataset missing 'label' field"
        assert "doi" in dataset, "Dataset missing 'doi' field"
        assert "latitude" in dataset, "Dataset missing 'latitude' field"
        assert "longitude" in dataset, "Dataset missing 'longitude' field"

        # Coordinates should be lists (or at least have length)
        lats = dataset["latitude"]
        lons = dataset["longitude"]
        if isinstance(lats, list) and isinstance(lons, list):
            assert len(lats) == len(lons), (
                f"Mismatched coordinate lengths in {dataset['label']}: "
                f"{len(lats)} lats vs {len(lons)} lons"
            )
            assert len(lats) > 0, f"No coordinates found in {dataset['label']}"


@pytest.mark.slow
def test_pangaea_data_structure():
    """
    Test that PANGAEA data has the expected structure for downstream processing.

    This validates that the data format is compatible with the rest of the
    cruiseplan pipeline (station picker, map generation, etc.).
    """
    # Use just one DOI for structure validation
    test_doi = "10.1594/PANGAEA.859930"  # MSM21/1a

    manager = PangaeaManager()
    datasets = manager.fetch_datasets([test_doi], rate_limit=0.5)

    assert len(datasets) == 1, f"Expected 1 dataset, got {len(datasets)}"
    dataset = datasets[0]

    # Validate required structure
    assert dataset["label"] == "MSM21/1a", f"Expected MSM21/1a, got {dataset['label']}"
    assert dataset["doi"] == test_doi, f"Expected {test_doi}, got {dataset['doi']}"

    # Coordinates should be numeric lists
    lats = dataset["latitude"]
    lons = dataset["longitude"]

    assert isinstance(lats, list), "Latitudes should be a list"
    assert isinstance(lons, list), "Longitudes should be a list"
    assert len(lats) > 0, "Should have latitude data"
    assert len(lons) > 0, "Should have longitude data"
    assert len(lats) == len(lons), "Lat/lon arrays should be same length"

    # All coordinates should be valid numbers
    for lat in lats:
        assert isinstance(lat, (int, float)), f"Invalid latitude type: {type(lat)}"
        assert -90 <= lat <= 90, f"Invalid latitude value: {lat}"

    for lon in lons:
        assert isinstance(lon, (int, float)), f"Invalid longitude type: {type(lon)}"
        assert -180 <= lon <= 180, f"Invalid longitude value: {lon}"


@pytest.mark.slow
def test_pangaea_merge_campaigns():
    """
    Test that campaign merging works correctly with real data.

    This tests the merge_campaigns functionality using real PANGAEA data
    where DY081 appears multiple times and should be merged.
    """
    fixture_path = Path(__file__).parent.parent / "fixtures" / "pangaea_list_NAtl.txt"

    with open(fixture_path) as f:
        dois = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    manager = PangaeaManager()

    # Fetch without merging
    datasets_unmerged = manager.fetch_datasets(
        dois, rate_limit=0.5, merge_campaigns=False
    )

    # Fetch with merging
    datasets_merged = manager.fetch_datasets(dois, rate_limit=0.5, merge_campaigns=True)

    # Unmerged should have 4 datasets (one per DOI)
    assert (
        len(datasets_unmerged) == 4
    ), f"Expected 4 unmerged datasets, got {len(datasets_unmerged)}"

    # Merged should have 3 datasets (DY081 entries merged)
    assert (
        len(datasets_merged) == 3
    ), f"Expected 3 merged datasets, got {len(datasets_merged)}"

    # Find the merged DY081 dataset
    dy081_datasets = [ds for ds in datasets_merged if ds.get("label") == "DY081"]
    assert (
        len(dy081_datasets) == 1
    ), f"Expected 1 merged DY081 dataset, got {len(dy081_datasets)}"

    merged_dy081 = dy081_datasets[0]

    # Merged DY081 should have coordinates from both original datasets
    # (2 stations total since each original DY081 had 1 station)
    lats = merged_dy081.get("latitude", [])
    lons = merged_dy081.get("longitude", [])
    assert len(lats) == 2, f"Expected 2 merged stations, got {len(lats)}"
    assert len(lons) == 2, f"Expected 2 merged stations, got {len(lons)}"

    # Should have both DOIs in the merged dataset
    dois_in_merged = merged_dy081.get("dois", [])
    dy081_dois = [
        doi
        for doi in dois
        if "DY081" in doi or doi in ["10.1594/PANGAEA.935444", "10.1594/PANGAEA.935448"]
    ]
    assert (
        len(dois_in_merged) == 2
    ), f"Expected 2 DOIs in merged DY081, got {len(dois_in_merged)}"
    assert set(dy081_dois).issubset(
        set(dois_in_merged)
    ), "Merged dataset should contain both DY081 DOIs"
