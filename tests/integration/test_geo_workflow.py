import logging
from pathlib import Path

import pytest

# Adjust imports to match your structure
from cruiseplan.data.pangaea import PangaeaManager, merge_campaign_tracks

# Setup logging to see what happens
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.slow
def test_geo_search_and_map_generation(caplog):
    """
    End-to-End Test:
    1. Search Pangaea for CTD data in a specific box (Iceland/Greenland Sea).
    2. Retrieve the DOIs.
    3. Merge the tracks.
    4. Generate a map.
    """
    caplog.set_level(logging.INFO)

    manager = PangaeaManager()

    output_dir = Path("tests_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    map_filename = output_dir / "test_map_geo_search.html"

    # 1. Define Geographic Query (66-67N, 27-28W)
    # Note: West longitudes are negative.
    # We use Lucene range syntax: field:[min TO max]
    query = "CTD/Rosette"
    bbox = (-28, 66, -27, 67)  # (minlon, minlat, maxlon, maxlat)

    print(f"\nExecuting Query: {query}")

    # 2. Search
    # We limit to 5 to keep the test reasonable speed-wise,
    # but enough to hopefully find overlapping tracks.
    search_results = manager.search(query, bbox, limit=5)

    if not search_results:
        pytest.fail(f"Search returned no results for query: {query}")

    print(f"Found {len(search_results)} datasets.")

    # Optional: Print DOIs found to confirm we got distinct things
    found_dois = [d["doi"] for d in search_results]
    print(f"DOIs found: {found_dois}")

    # 3. Merge
    merged_tracks = merge_campaign_tracks(search_results)

    assert len(merged_tracks) > 0, "Merging resulted in zero tracks."
    print(f"Merged into {len(merged_tracks)} unique campaigns.")

    # 4. Generate Map
    generated_file = manager.create_map(merged_tracks, filename=str(map_filename))

    # 5. Verify
    assert generated_file.exists()
    assert generated_file.stat().st_size > 0

    print(f"\nTest Successful! Map generated at: {generated_file.resolve()}")
