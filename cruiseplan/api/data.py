"""
Data acquisition API functions.

This module provides functions for downloading bathymetry data and searching
PANGAEA oceanographic databases.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from cruiseplan.exceptions import ValidationError
from cruiseplan.types import BathymetryResult, PangaeaResult

logger = logging.getLogger(__name__)


def bathymetry(
    bathy_source: str = "etopo2022",
    output_dir: Optional[str] = None,
    citation: bool = False,
) -> BathymetryResult:
    """
    Download bathymetry data (mirrors: cruiseplan bathymetry).

    Parameters
    ----------
    bathy_source : str
        Bathymetry dataset to download ("etopo2022" or "gebco2025")
    output_dir : str, optional
        Output directory for bathymetry files (default: "data/bathymetry" relative to project root)
    citation : bool
        Show citation information for the bathymetry source (default: False)

    Returns
    -------
    BathymetryResult
        Structured result containing data file path, source information, and summary.

    Examples
    --------
    >>> import cruiseplan
    >>> # Download ETOPO2022 data to project root data/bathymetry/
    >>> cruiseplan.bathymetry()
    >>> # Download GEBCO2025 data to custom location
    >>> cruiseplan.bathymetry(bathy_source="gebco2025", output_dir="my_data/bathymetry")
    """
    from cruiseplan.data.bathymetry import download_bathymetry

    # Use default path relative to project root if none provided
    if output_dir is None:
        # Find project root (directory containing cruiseplan package)
        package_dir = Path(
            __file__
        ).parent.parent.parent  # Go up from cruiseplan/api/data.py
        data_dir = package_dir / "data" / "bathymetry"
    else:
        data_dir = Path(output_dir)

    data_dir = data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"🌊 Downloading {bathy_source} bathymetry data to {data_dir}")
    result = download_bathymetry(target_dir=str(data_dir), source=bathy_source)
    # Determine the data file path and gather metadata
    data_file = Path(result) if result else None
    file_size_mb = None
    if data_file and data_file.exists():
        file_size_mb = round(data_file.stat().st_size / (1024 * 1024), 1)

    # Create structured result
    summary = {
        "source": bathy_source,
        "output_dir": str(data_dir),
        "file_size_mb": file_size_mb,
        "citation_shown": citation,
    }

    return BathymetryResult(data_file=data_file, source=bathy_source, summary=summary)


def pangaea(
    query_terms: str,
    output_dir: str = "data",
    output: Optional[str] = None,
    lat_bounds: Optional[list[float]] = None,
    lon_bounds: Optional[list[float]] = None,
    max_results: int = 100,
    rate_limit: float = 1.0,
    merge_campaigns: bool = True,
    verbose: bool = False,
) -> PangaeaResult:
    """
    Search and download PANGAEA oceanographic data (mirrors: cruiseplan pangaea).

    Parameters
    ----------
    query_terms : str
        Search terms for PANGAEA database
    output_dir : str
        Output directory for station files (default: "data")
    output : str, optional
        Base filename for outputs (default: derived from query)
    lat_bounds : List[float], optional
        Latitude bounds [min_lat, max_lat]
    lon_bounds : List[float], optional
        Longitude bounds [min_lon, max_lon]
    max_results : int
        Maximum number of results to process (default: 100)
    rate_limit : float
        API request rate limit in requests per second (default: 1.0)
    merge_campaigns : bool
        Merge campaigns with the same name (default: True)
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    PangaeaResult
        Structured result containing stations data, generated files, and summary information.
        Stations data contains the loaded PANGAEA campaign data for analysis.
        Files list contains paths to all generated files (DOI list, stations pickle).
        Summary contains metadata about the search and processing.

    Examples
    --------
    >>> import cruiseplan
    >>> # Search for CTD data in Arctic
    >>> result = cruiseplan.pangaea("CTD", lat_bounds=[70, 80], lon_bounds=[-10, 10])
    >>> print(f"Found {len(result.stations_data)} campaigns in {len(result.files_created)} files")
    >>> # Search with custom output directory and filename
    >>> result = cruiseplan.pangaea("temperature", output_dir="pangaea_data", output="arctic_temp")
    >>> # Access the data directly
    >>> for campaign in result.stations_data:
    ...     print(f"Campaign: {campaign['Campaign']}, Stations: {len(campaign['Stations'])}")
    """
    from cruiseplan.data.pangaea import (
        PangaeaManager,
        save_campaign_data,
    )
    from cruiseplan.init_utils import (
        _handle_error_with_logging,
        _setup_verbose_logging,
        _validate_lat_lon_bounds,
    )

    _setup_verbose_logging(verbose)

    try:
        # Validate lat/lon bounds if provided
        bbox = _validate_lat_lon_bounds(lat_bounds, lon_bounds)
        if (lat_bounds or lon_bounds) and bbox is None:
            raise ValidationError("Invalid latitude/longitude bounds provided")

        # Setup output paths
        output_dir_path = Path(output_dir).resolve()
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # Generate base filename if not provided (similar to CLI logic)
        if not output:
            safe_query = "".join(c if c.isalnum() else "_" for c in query_terms)
            safe_query = re.sub(r"_+", "_", safe_query).strip("_")
            base_name = safe_query
        else:
            base_name = output

        # Define output files
        dois_file = output_dir_path / f"{base_name}_dois.txt"
        stations_file = output_dir_path / f"{base_name}_stations.pkl"
        generated_files = []

        # Search PANGAEA database using PangaeaManager with separate search/fetch
        logger.info(f"🔍 Searching PANGAEA for: '{query_terms}'")
        if bbox:
            logger.info(f"📍 Geographic bounds: lat {lat_bounds}, lon {lon_bounds}")

        manager = PangaeaManager()

        # First, do a search to get DOIs only (modify search to not auto-fetch)
        try:
            from pangaeapy.panquery import PanQuery

            pq = PanQuery(query_terms, bbox=bbox, limit=max_results)
            if pq.error:
                logger.error(f"PANGAEA Query Error: {pq.error}")
                return None, None

            raw_dois = pq.get_dois()
            clean_dois = [manager._clean_doi(doi) for doi in raw_dois]

            logger.info(
                f"Search found {pq.totalcount} total matches. Retrieving first {len(clean_dois)}..."
            )

            if not clean_dois:
                logger.warning("❌ No DOIs found. Try broadening your search criteria.")
                raise RuntimeError("No DOIs found for the given search criteria")

            logger.info(f"✅ Found {len(clean_dois)} datasets")

            # Save DOI list (intermediate file)
            with open(dois_file, "w") as f:
                for doi in clean_dois:
                    f.write(f"{doi}\n")
            generated_files.append(dois_file)

            logger.info(f"📂 DOI file: {dois_file}")
            logger.info(f"📂 Stations file: {stations_file}")

            # Now fetch detailed PANGAEA data with proper rate limiting
            logger.info(f"⚙️ Processing {len(clean_dois)} DOIs...")
            logger.info(f"🕐 Rate limit: {rate_limit} requests/second")

            detailed_datasets = manager.fetch_datasets(
                clean_dois, rate_limit=rate_limit, merge_campaigns=merge_campaigns
            )

            if not detailed_datasets:
                logger.warning(
                    "⚠️ No datasets retrieved. Check DOI list and network connection."
                )
                raise RuntimeError("No datasets could be retrieved from PANGAEA")

            # Save results using data function
            save_campaign_data(detailed_datasets, stations_file)
            generated_files.append(stations_file)

        except ImportError:
            logger.error(
                "❌ pangaeapy not available. Please install with: pip install pangaeapy"
            )
            raise RuntimeError(
                "pangaeapy package not available - please install with: pip install pangaeapy"
            )

        logger.info("✅ PANGAEA processing completed successfully!")
        logger.info(f"🚀 Next step: cruiseplan stations -p {stations_file}")

        return PangaeaResult(
            stations_data=detailed_datasets,
            files_created=generated_files,
            summary={
                "query_terms": query_terms,
                "campaigns_found": len(detailed_datasets) if detailed_datasets else 0,
                "files_generated": len(generated_files),
                "lat_bounds": lat_bounds,
                "lon_bounds": lon_bounds,
                "max_results": max_results,
            },
        )

    except Exception as e:
        _handle_error_with_logging(e, "PANGAEA search failed", verbose)
        raise  # Re-raise the exception so caller knows it failed
