import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# PangaeaPy Imports
from pangaeapy.pandataset import PanDataSet
from pangaeapy.panquery import PanQuery

# Local Imports
from cruiseplan.data.cache import CacheManager
from cruiseplan.output.map_generator import generate_cruise_map

logger = logging.getLogger(__name__)


class PangaeaManager:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache = CacheManager(cache_dir)

    def search(
        self, query: str, bbox: tuple = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Pangaea using the native PanQuery bbox support.
        """
        logger.info(f"Searching Pangaea: '{query}' (Limit: {limit})")

        try:
            # 1. Use bbox directly. The class maps it to &minlon, &maxlat, etc.
            pq = PanQuery(query, bbox=bbox, limit=limit)

            # Check for errors reported by the class
            if pq.error:
                logger.error(f"Pangaea Query Error: {pq.error}")
                return []

            # 2. Extract DOIs correctly
            # The source code provides a helper method for this:
            raw_dois = pq.get_dois()
            clean_dois = [self._clean_doi(doi) for doi in raw_dois]

            logger.info(
                f"Search found {pq.totalcount} total matches. Retrieving first {len(clean_dois)}..."
            )

            if not clean_dois:
                return []

            return self.fetch_datasets(clean_dois)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def fetch_datasets(self, doi_list: List[str]) -> List[Dict[str, Any]]:
        """
        Process a list of DOIs and return standardized metadata objects.

        Returns
        -------
            List of dicts: [{'label': '...', 'latitude': [...], 'longitude': [...], 'doi': '...'}, ...]
        """
        results = []

        for doi in doi_list:
            clean_doi = self._clean_doi(doi)
            if not clean_doi:
                logger.warning(f"Skipping invalid DOI: {doi}")
                continue

            cache_key = f"pangaea_meta_{clean_doi.replace('/', '_')}"
            data = self.cache.get(cache_key)

            if data is None:
                # Fetch fresh from API
                data = self._fetch_from_api(clean_doi)
                if data is not None:
                    self.cache.set(cache_key, data)

            if data is not None:
                results.append(data)

        return results

    def create_map(
        self, datasets: List[Dict[str, Any]], filename: str = "pangaea_map.html"
    ) -> Path:
        """
        Convenience wrapper to visualize datasets fetched by this manager.
        """
        # You might want to do a quick transformation here if your dataset dicts
        # don't exactly match what generate_cruise_map expects.
        # But if they match (latitude, longitude, label), just pass them through:

        return generate_cruise_map(datasets, output_file=filename)

    def _clean_doi(self, doi: str) -> str:
        """Validate and clean DOI format (10.xxxx/xxxx)."""
        if not isinstance(doi, str):
            return ""

        doi = doi.strip()

        # Handle "doi:" prefix (e.g., from Pangaea API "doi:10.1594/...")
        if doi.lower().startswith("doi:"):
            doi = doi[4:]  # Remove the first 4 characters

        # Handle full URL format (e.g., "https://doi.org/10.xxxx")
        if "doi.org/" in doi:
            doi = doi.split("doi.org/")[-1]

        # Final validation: Must start with the directory indicator "10."
        if not doi.startswith("10."):
            return ""

        return doi

    def _fetch_from_api(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Strategy:
        1. Try extracting from `ds.events` (Metadata - Best for coordinates/campaigns)
        2. Fallback to `ds.data` (Main Table - Messy columns)
        """
        try:
            logger.info(f"Fetching PANGAEA dataset: {doi}")
            ds = PanDataSet(doi)

            # STRATEGY 1: Use Events Metadata (Preferred - Lightweight)
            if hasattr(ds, "events") and ds.events:
                data = self._parse_events(ds.events, doi)
                if data:
                    return data

            # STRATEGY 2: Fallback to Main Data Table
            logger.info(f"No events found for {doi}, falling back to data table.")
            return self._parse_data_table(ds, doi)

        except Exception as e:
            logger.error(f"Failed to fetch {doi}: {e}")
            return None

    def _parse_events(self, events_data: Any, doi: str) -> Optional[Dict[str, Any]]:
        """
        Extracts lat/lon/label/campaign from the .events attribute.
        Returns a standardized Dictionary.
        """
        events_list = []

        # Normalize input to list
        if hasattr(events_data, "iterrows"):
            events_list = [event for _, event in events_data.iterrows()]
        elif isinstance(events_data, list):
            events_list = events_data
        else:
            return None

        lats = []
        lons = []
        campaign_label = "Unknown Campaign"

        # We need to aggregate points for this single dataset
        for event in events_list:
            lat = self._safe_get(event, ["Latitude", "latitude", "lat", "LATITUDE"])
            lon = self._safe_get(
                event, ["Longitude", "longitude", "lon", "long", "LONGITUDE"]
            )

            if lat is not None and lon is not None:
                try:
                    lats.append(float(lat))
                    lons.append(float(lon))
                except (ValueError, TypeError):
                    continue

            # Try to grab the campaign label from the first valid event
            if campaign_label == "Unknown Campaign":
                camp_obj = self._safe_get(
                    event, ["Campaign", "campaign", "expedition", "Expedition"]
                )
                if camp_obj:
                    if hasattr(camp_obj, "label"):
                        campaign_label = camp_obj.label
                    elif hasattr(camp_obj, "name"):
                        campaign_label = camp_obj.name
                    else:
                        campaign_label = str(camp_obj)

        if not lats:
            return None

        return {
            "label": str(campaign_label),
            "latitude": lats,
            "longitude": lons,
            "doi": doi,
        }

    def _parse_data_table(self, ds: PanDataSet, doi: str) -> Optional[Dict[str, Any]]:
        """Fallback: Scrape the main data table for coordinates."""
        if ds.data is None or ds.data.empty:
            return None

        df = ds.data

        # Find columns
        lat_col = next((c for c in df.columns if c.lower().startswith("lat")), None)
        lon_col = next((c for c in df.columns if c.lower().startswith("lon")), None)

        if not (lat_col and lon_col):
            return None

        # Extract Clean Lists
        try:
            clean_lats = pd.to_numeric(df[lat_col], errors="coerce").dropna().tolist()
            clean_lons = pd.to_numeric(df[lon_col], errors="coerce").dropna().tolist()
        except Exception:
            return None

        if not clean_lats:
            return None

        # Campaign is likely global metadata in this case
        campaign = getattr(ds, "title", doi)

        # Clean up title if it's too long (common in Pangaea titles)
        if len(campaign) > 50:
            campaign = campaign[:47] + "..."

        return {
            "label": campaign,
            "latitude": clean_lats,
            "longitude": clean_lons,
            "doi": doi,
        }

    def _safe_get(self, obj: Any, keys: List[str]) -> Any:
        """Helper to get attributes safely from dicts or objects."""
        for key in keys:
            # Try dictionary access
            if hasattr(obj, "get"):
                val = obj.get(key)
                if val is not None:
                    return val

            # Try attribute access
            if hasattr(obj, key):
                val = getattr(obj, key)
                if val is not None:
                    return val

            # Try lowercase attribute
            lower_key = key.lower()
            if hasattr(obj, lower_key):
                val = getattr(obj, lower_key)
                if val is not None:
                    return val
        return None


# ------------------------------------------------------------------------------
# Utility Functions (Module Level)
# ------------------------------------------------------------------------------


def _is_valid_doi(doi: any) -> bool:
    """
    Validates if the input string is a valid DOI format.
    Strictly checks for '10.XXXX/XXXX' format.
    """
    if not isinstance(doi, str):
        return False
    if doi.strip() != doi:
        return False
    pattern = r"^10\.\d{4,9}/\S+$"
    return bool(re.match(pattern, doi))


def merge_campaign_tracks(datasets: List[Dict]) -> List[Dict]:
    """
    Merges datasets by their 'label' (campaign).
    Aggregates coordinates into single arrays and collects all source DOIs.
    """
    grouped = {}

    for ds in datasets:
        label = ds.get("label", "Unknown Campaign")

        if label not in grouped:
            grouped[label] = {
                "label": label,
                "latitude": [],
                "longitude": [],
                "dois": set(),
            }

        lats = ds.get("latitude", [])
        lons = ds.get("longitude", [])
        doi = ds.get("doi")

        # Robustness: Normalize scalars to lists
        if not isinstance(lats, list):
            lats = [lats]
        if not isinstance(lons, list):
            lons = [lons]

        if len(lats) != len(lons):
            logging.warning(
                f"Skipping segment in {label} (DOI: {doi}): Lat/Lon length mismatch."
            )
            continue

        grouped[label]["latitude"].extend(lats)
        grouped[label]["longitude"].extend(lons)

        if doi:
            grouped[label]["dois"].add(doi)

    # Convert sets to lists for JSON serialization
    result = []
    for data in grouped.values():
        data["dois"] = list(data["dois"])
        result.append(data)

    return result
