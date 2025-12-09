import pickle
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Import the function under test
from cruiseplan.data.pangaea import (
    PangaeaManager,
    _is_valid_doi,
    load_campaign_data,
    merge_campaign_tracks,
)


@pytest.fixture
def mock_pangaea_events():
    """
    Mock the complex .events structure found in real Pangaea datasets.
    """
    # Create mock event objects
    e1 = MagicMock()
    # CRITICAL FIX: Delete .get so _safe_get treats it as an object, not a dict
    del e1.get
    e1.Latitude = 50.0
    e1.Longitude = -10.0
    e1.Label = "Station_A"
    e1.Campaign.label = "PS100"

    e2 = MagicMock()
    del e2.get  # CRITICAL FIX
    e2.Latitude = 51.0
    e2.Longitude = -9.0
    e2.Label = "Station_B"
    e2.Campaign.label = "PS100"

    # Mock the dataset
    mock_ds = MagicMock()
    mock_ds.events = [e1, e2]
    return mock_ds


@patch("cruiseplan.data.pangaea.PanDataSet")
def test_fetch_from_events(mock_class, mock_pangaea_events, tmp_path):
    # Setup
    mock_class.return_value = mock_pangaea_events
    manager = PangaeaManager(cache_dir=str(tmp_path))

    doi = "10.1594/PANGAEA.123"

    # 1. Update Method Call (fetch_doi_list -> fetch_datasets)
    results = manager.fetch_datasets([doi])

    # 2. Verify Structure (Results is now a list)
    assert isinstance(results, list)
    assert len(results) == 1

    dataset = results[0]  # Get the first (and only) dataset object

    # Verify Keys exist in the standardized dictionary
    assert "label" in dataset
    assert "latitude" in dataset
    assert "longitude" in dataset

    # 3. Verify Content
    # Latitude is now a list of floats, check the first one
    assert dataset["latitude"][0] == 50.0

    # Check Metadata
    # Note: Depending on your normalizer, 'label' might be the dataset title
    # or the station label. Adjust if your logic aggregates labels differently.
    assert dataset["label"] == "PS100"


def test_doi_cleaning():
    manager = PangaeaManager()
    assert manager._clean_doi("https://doi.org/10.1000/1") == "10.1000/1"
    assert manager._clean_doi("  10.1000/1  ") == "10.1000/1"
    assert manager._clean_doi("bad_doi") == ""


def test_missing_event_attribute():
    """Verify safe_get works on partial objects"""
    manager = PangaeaManager()

    # FIX: Use spec=['lat'] to strictly define valid attributes.
    # Accessing 'Latitude', 'latitude', or 'get' will now raise AttributeError automatically.
    partial_event = MagicMock(spec=["lat"])
    partial_event.lat = 45.0

    val = manager._safe_get(partial_event, ["Latitude", "lat"])

    assert val == 45.0


class TestDOIValidation:

    @pytest.mark.parametrize(
        "doi",
        [
            "10.1594/PANGAEA.859930",
            "10.1594/PANGAEA.890362",
            "10.5194/essd-12-2459-2020",
            "10.1038/s41561-018-0123-4",
            "10.1000/182",
        ],
    )
    def test_valid_dois(self, doi):
        """Verify standard DOI formats pass."""
        assert _is_valid_doi(doi) is True

    @pytest.mark.parametrize(
        "doi",
        [
            "not a doi",
            "10.1594",  # missing suffix
            "PANGAEA.859930",  # missing 10. prefix
            "10.1594/PANGAEA 859930",  # has space
            "",  # empty
            "   ",  # whitespace only
            "10./PANGAEA.859930",  # malformed prefix
            "10.1594/",  # missing suffix after slash
            "   10.1594/PANGAEA.859930   ",  # leading/trailing whitespace (Strict check)
            "http://10.1594/PANGAEA.859930",  # URL prefix
            "10.1594\tPANGAEA.859930",  # tab character
            "10.1594\nPANGAEA.859930",  # newline character
            "10.",  # Just prefix start
            "/",  # Just slash
            None,  # None value
            123,  # non-string
        ],
    )
    def test_invalid_dois(self, doi):
        """Verify invalid DOIs, types, and edge cases fail."""
        assert _is_valid_doi(doi) is False


def test_merge_campaign_tracks_logic():
    """
    Test that datasets with the same campaign label are merged into a single track,
    aggregating their DOIs and coordinates.
    """
    # Input: 3 datasets. Two belong to 'Cruise-A', one to 'Cruise-B'.
    raw_data = [
        {
            "label": "Cruise-A",
            "latitude": [10.0, 11.0],
            "longitude": [5.0, 5.0],
            "doi": "doi:1",
        },
        {
            "label": "Cruise-A",
            "latitude": [12.0],  # Single point segment
            "longitude": [6.0],
            "doi": "doi:2",
        },
        {"label": "Cruise-B", "latitude": [50.0], "longitude": [0.0], "doi": "doi:3"},
    ]

    merged = merge_campaign_tracks(raw_data)

    # Assertions
    assert len(merged) == 2, "Should have collapsed 3 entries into 2 campaigns"

    # Check Cruise-A (The merged one)
    cruise_a = next(d for d in merged if d["label"] == "Cruise-A")
    assert len(cruise_a["latitude"]) == 3  # 2 + 1 points
    assert cruise_a["latitude"] == [10.0, 11.0, 12.0]
    assert set(cruise_a["dois"]) == {"doi:1", "doi:2"}  # DOIs preserved

    # Check Cruise-B (The standalone one)
    cruise_b = next(d for d in merged if d["label"] == "Cruise-B")
    assert len(cruise_b["latitude"]) == 1


def test_merge_handles_inconsistent_data():
    """Robustness check: Ignore segments where lat/lon lengths don't match."""
    bad_data = [
        {
            "label": "Bad-Data",
            "latitude": [10.0, 20.0],
            "longitude": [5.0],  # Mismatched length!
            "doi": "bad:1",
        }
    ]

    merged = merge_campaign_tracks(bad_data)

    # Depending on strategy, we either skip the bad data or the whole entry.
    # Here we assume robust code skips the bad arrays but keeps the entry if valid.
    # Since the only data was bad, the lat/lon lists should be empty.
    assert merged[0]["latitude"] == []


class TestLoadCampaignData:

    @pytest.fixture
    def mock_merged_data(self):
        """Standardized, simple mock data representing merged campaigns."""
        return [
            {
                "label": "Cruise-A",
                "latitude": [10.0, 11.0],
                "longitude": [5.0, 6.0],
                "doi": "doi:1",
            },
            {
                "label": "Cruise-B",
                "latitude": [50.0],
                "longitude": [0.0],
                "doi": "doi:3",
            },
        ]

    # --- Test 1: Success Path (Loading and Merging) ---

    @patch("cruiseplan.data.pangaea.merge_campaign_tracks")
    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    def test_load_and_merge_success(self, mock_exists, mock_merge, mock_merged_data):
        """
        Tests successful loading, validation, and mandatory merging.
        The mock open simulates loading raw data, and we mock merge to verify it runs.
        """
        # Mock the data found in the pickle file (must be a list of dicts)
        raw_loaded_data = [
            {"label": "Cruise-A", "latitude": [10.0], "longitude": [5.0]},
            {
                "label": "Cruise-A",
                "latitude": [11.0],
                "longitude": [6.0],
            },  # Duplicate label to be merged
            {"label": "Cruise-B", "latitude": [50.0], "longitude": [0.0]},
        ]

        # Configure merge_campaign_tracks to return the final, clean data
        mock_merge.return_value = mock_merged_data

        # Patch pickle.load to return the raw data
        with patch("builtins.open", mock_open(read_data=pickle.dumps(raw_loaded_data))):
            results = load_campaign_data("dummy_path.pkl", merge_tracks=True)

        # 1. Assert merge was called with the raw data
        mock_merge.assert_called_once_with(raw_loaded_data)

        # 2. Assert final output is the merged data
        assert results == mock_merged_data
        assert len(results) == 2

    # --- Test 2: Success Path (Loading without Merging) ---

    @patch("cruiseplan.data.pangaea.merge_campaign_tracks")
    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    def test_load_without_merging(self, mock_exists, mock_merge, mock_merged_data):
        """Tests successful loading when merge_tracks=False."""
        raw_loaded_data = (
            mock_merged_data  # Use clean data to skip deep validation issues
        )

        with patch("builtins.open", mock_open(read_data=pickle.dumps(raw_loaded_data))):
            results = load_campaign_data("dummy_path.pkl", merge_tracks=False)

        # 1. Assert merge was NOT called
        mock_merge.assert_not_called()

        # 2. Assert final output is the raw data
        assert results == raw_loaded_data
        assert len(results) == 2

    # --- Test 3: File System and General Error Handling ---

    @patch("cruiseplan.data.pangaea.Path.exists", return_value=False)
    def test_file_not_found(self, mock_exists):
        """Tests the FileNotFoundError exception path."""
        with pytest.raises(FileNotFoundError, match="Campaign data file not found"):
            load_campaign_data("non_existent_path.pkl")

    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    def test_io_error_handling(self, mock_open, mock_exists):
        """Tests general IO errors during file reading."""
        with pytest.raises(ValueError, match="Error loading campaign data"):
            load_campaign_data("unreadable_file.pkl")

    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    @patch("builtins.open", mock_open(read_data=b"invalid pickle data"))
    def test_pickle_error_handling(self, mock_exists):
        """Tests failure during unpickling."""
        with pytest.raises(
            pickle.PickleError, match="Failed to unpickle campaign data"
        ):
            load_campaign_data("bad_pickle.pkl")

    # --- Test 4: Data Validation and Structure Errors ---

    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    def test_invalid_data_root_structure(self, mock_exists):
        """Tests failure if the loaded data is not a list."""
        with patch(
            "builtins.open", mock_open(read_data=pickle.dumps({"campaign": "dict"}))
        ):
            with pytest.raises(ValueError, match="Expected list of campaigns, got"):
                load_campaign_data("dict_not_list.pkl")

    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    def test_missing_required_keys(self, mock_exists):
        """Tests failure if a campaign dictionary is missing required keys."""
        bad_data = [
            {"label": "Good", "latitude": [10.0], "longitude": [5.0]},
            {"label": "Bad", "latitude": [10.0]},  # Missing longitude
        ]
        with patch("builtins.open", mock_open(read_data=pickle.dumps(bad_data))):
            with pytest.raises(
                ValueError, match="missing required keys: \\['longitude'\\]"
            ):
                load_campaign_data("missing_key.pkl")

    @patch("cruiseplan.data.pangaea.Path.exists", return_value=True)
    def test_invalid_campaign_is_not_dict(self, mock_exists):
        """Tests failure if an item in the list is not a dictionary."""
        bad_data = [
            {"label": "Good", "latitude": [10.0], "longitude": [5.0]},
            "this is a string",  # Invalid item
        ]
        with patch("builtins.open", mock_open(read_data=pickle.dumps(bad_data))):
            with pytest.raises(ValueError, match="is not a dictionary"):
                load_campaign_data("not_dict.pkl")
