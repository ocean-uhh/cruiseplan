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
