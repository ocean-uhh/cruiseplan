import logging
import pickle
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd

# PangaeaPy Imports
from pangaeapy.pandataset import PanDataSet
from pangaeapy.panquery import PanQuery

# Local Imports
from cruiseplan.data.cache import CacheManager
from cruiseplan.output.map_generator import generate_folium_map

logger = logging.getLogger(__name__)


class PangaeaManager:
    """
    Manager for PANGAEA dataset search and retrieval.

    Provides functionality to search PANGAEA datasets using spatial queries,
    fetch metadata and coordinate data, and cache results for performance.
    Integrates with the cruise planning system for incorporating existing
    cruise tracks into planning workflows.

    Attributes
    ----------
    cache : CacheManager
        File-based cache for storing fetched dataset metadata.
    """

    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize PANGAEA manager.

        Parameters
        ----------
        cache_dir : str, optional
            Directory for cache storage (default: ".cache").
        """
        self.cache = CacheManager(cache_dir)

    def search(
        self, query: str, bbox: tuple = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search PANGAEA using the native PanQuery bbox support.

        Parameters
        ----------
        query : str
            Search query string for PANGAEA datasets.
        bbox : tuple, optional
            Bounding box as (min_lon, min_lat, max_lon, max_lat).
        limit : int, optional
            Maximum number of results to return (default: 10).

        Returns
        -------
        List[Dict[str, Any]]
            List of dataset metadata dictionaries.
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

    def fetch_datasets(
        self,
        doi_list: List[str],
        rate_limit: Optional[float] = None,
        merge_campaigns: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process a list of DOIs and return standardized metadata objects.

        Parameters
        ----------
        doi_list : List[str]
            List of DOI strings to fetch.
        rate_limit : Optional[float], optional
            Optional requests per second limit (None = no rate limiting).
        merge_campaigns : bool, optional
            Whether to merge campaigns with same name (default: False).
        progress_callback : Optional[Callable[[int, int, str], None]], optional
            Optional function(current, total, message) for progress updates.

        Returns
        -------
        List[Dict[str, Any]]
            List of dataset dictionaries with standardized metadata.
        """
        import time

        results = []

        if progress_callback:
            progress_callback(
                0, len(doi_list), f"Starting fetch of {len(doi_list)} PANGAEA datasets"
            )

        for i, doi in enumerate(doi_list, 1):
            try:
                if progress_callback:
                    progress_callback(i, len(doi_list), f"Fetching {doi}")

                clean_doi = self._clean_doi(doi)
                if not clean_doi:
                    logger.warning(f"Skipping invalid DOI: {doi}")
                    if progress_callback:
                        progress_callback(
                            i, len(doi_list), f"⚠ Skipping invalid DOI: {doi}"
                        )
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
                    if progress_callback:
                        progress_callback(i, len(doi_list), "✓ Retrieved dataset")
                elif progress_callback:
                    progress_callback(i, len(doi_list), f"⚠ No data found for {doi}")

                # Rate limiting between requests
                if rate_limit and i < len(doi_list):  # Don't sleep after last request
                    sleep_time = 1.0 / rate_limit
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                if progress_callback:
                    progress_callback(
                        i - 1,
                        len(doi_list),
                        f"Processing interrupted at {i-1}/{len(doi_list)} DOIs",
                    )
                break

            except Exception as e:
                if progress_callback:
                    progress_callback(i, len(doi_list), f"✗ Error fetching {doi}: {e}")
                logger.error(f"Error fetching {doi}: {e}")
                continue

        # Merge campaigns if requested
        if merge_campaigns and results:
            original_count = len(results)
            results = merge_campaign_tracks(results)
            merged_count = len(results)

            if progress_callback and merged_count < original_count:
                progress_callback(
                    len(doi_list),
                    len(doi_list),
                    f"Merged {original_count} datasets into {merged_count} campaigns",
                )

        if progress_callback:
            progress_callback(
                len(doi_list),
                len(doi_list),
                f"Completed: {len(results)} datasets from {len(doi_list)} DOIs",
            )

        return results

    def create_map(
        self, datasets: List[Dict[str, Any]], filename: str = "pangaea_map.html"
    ) -> Path:
        """
        Convenience wrapper to visualize datasets fetched by this manager.

        Parameters
        ----------
        datasets : List[Dict[str, Any]]
            List of dataset dictionaries with latitude/longitude data.
        filename : str, optional
            Output filename for the HTML map (default: "pangaea_map.html").

        Returns
        -------
        Path
            Path to the generated HTML map file.
        """
        # You might want to do a quick transformation here if your dataset dicts
        # don't exactly match what generate_folium_map expects.
        # But if they match (latitude, longitude, label), just pass them through:

        return generate_folium_map(datasets, output_file=filename)

    def _clean_doi(self, doi: str) -> str:
        """
        Validate and clean DOI format (10.xxxx/xxxx).

        Parameters
        ----------
        doi : str
            DOI string to clean and validate.

        Returns
        -------
        str
            Cleaned DOI string or empty string if invalid.
        """
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
        Fetch dataset metadata from PANGAEA API.

        Strategy:
        1. Try extracting from `ds.events` (Metadata - Best for coordinates/campaigns)
        2. Fallback to `ds.data` (Main Table - Messy columns)

        Parameters
        ----------
        doi : str
            DOI identifier for the dataset.

        Returns
        -------
        Optional[Dict[str, Any]]
            Standardized dataset metadata or None if fetch fails.
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

        Parameters
        ----------
        events_data : Any
            Events data from PANGAEA dataset.
        doi : str
            DOI identifier for the dataset.

        Returns
        -------
        Optional[Dict[str, Any]]
            Standardized dataset metadata or None if parsing fails.
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
        """
        Fallback: Scrape the main data table for coordinates.

        Parameters
        ----------
        ds : PanDataSet
            PANGAEA dataset object.
        doi : str
            DOI identifier for the dataset.

        Returns
        -------
        Optional[Dict[str, Any]]
            Standardized dataset metadata or None if parsing fails.
        """
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
        """
        Helper to get attributes safely from dicts or objects.

        Parameters
        ----------
        obj : Any
            Object to extract attribute from.
        keys : List[str]
            List of possible key/attribute names to try.

        Returns
        -------
        Any
            Value if found, None otherwise.
        """
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

    Parameters
    ----------
    doi : any
        Input to validate as DOI.

    Returns
    -------
    bool
        True if valid DOI format, False otherwise.
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

    Parameters
    ----------
    datasets : List[Dict]
        List of dataset dictionaries to merge.

    Returns
    -------
    List[Dict]
        Merged campaign datasets with combined coordinates.
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


def save_campaign_data(
    datasets: List[Dict],
    file_path: Union[str, Path],
    progress_callback: Optional[Callable[[str], None]] = None,
    original_dataset_count: Optional[int] = None,
) -> None:
    """
    Save PANGAEA datasets to pickle file.

    Parameters
    ----------
    datasets : List[Dict]
        List of dataset dictionaries to save.
    file_path : Union[str, Path]
        Output file path for the pickle file.
    progress_callback : Optional[Callable[[str], None]], optional
        Optional function(message) for progress updates.
    original_dataset_count : Optional[int], optional
        Optional count of datasets before merging for summary.

    Raises
    ------
    ValueError
        If there's an error saving the file.
    """
    import pickle

    file_path = Path(file_path)

    try:
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Save datasets to pickle
        with open(file_path, "wb") as f:
            pickle.dump(datasets, f, protocol=pickle.HIGHEST_PROTOCOL)

        if progress_callback:
            progress_callback(f"Saved {len(datasets)} datasets to: {file_path}")

            # Provide summary statistics
            if datasets:
                # Count stations from latitude arrays (primary) or events (fallback)
                total_events = sum(
                    len(ds.get("latitude", ds.get("events", []))) for ds in datasets
                )
                campaigns = set(ds.get("label", "Unknown") for ds in datasets)

                progress_callback("Summary:")
                # Use original count if provided, otherwise current count
                dataset_count = (
                    original_dataset_count
                    if original_dataset_count is not None
                    else len(datasets)
                )
                progress_callback(f"  - {dataset_count} datasets")
                progress_callback(f"  - {len(campaigns)} unique campaigns")
                progress_callback(f"  - {total_events} total events/stations")

    except Exception as e:
        raise ValueError(f"Error saving pickle file: {e}")


def load_campaign_data(
    file_path: Union[str, Path], merge_tracks: bool = True
) -> List[Dict]:
    """
    Load pre-processed PANGAEA campaign data from pickle file.

    This function is required by the CLI to integrate with the interactive picker.
    If merge_tracks is True, it ensures that all datasets with the same
    label are combined into a single track before being returned.

    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the pickled PANGAEA campaign file.
    merge_tracks : bool
        If True, runs merge_campaign_tracks on the loaded data. (Default: True)

    Returns
    -------
    List[Dict]
        List of campaign datasets (merged if requested).
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"Campaign data file not found: {file_path}")

    try:
        with open(file_path, "rb") as f:
            campaign_data = pickle.load(f)

        # Validate the loaded data structure
        if not isinstance(campaign_data, list):
            raise ValueError(f"Expected list of campaigns, got {type(campaign_data)}")

        # Basic validation of campaign structure
        for i, campaign in enumerate(campaign_data):
            if not isinstance(campaign, dict):
                raise ValueError(f"Campaign {i} is not a dictionary: {type(campaign)}")

            required_keys = ["label", "latitude", "longitude"]
            missing_keys = [key for key in required_keys if key not in campaign]
            if missing_keys:
                raise ValueError(f"Campaign {i} missing required keys: {missing_keys}")

        logger.info(
            f"Successfully loaded {len(campaign_data)} campaigns from {file_path}"
        )

        if merge_tracks:
            # Apply your crucial merging step here before returning to the GUI
            logging.info("Merging campaign tracks by label for unique plotting.")
            return merge_campaign_tracks(campaign_data)
        else:
            return campaign_data

    except pickle.PickleError as e:
        raise pickle.PickleError(
            f"Failed to unpickle campaign data from {file_path}: {e}"
        )
    except Exception as e:
        raise ValueError(f"Error loading campaign data from {file_path}: {e}")
