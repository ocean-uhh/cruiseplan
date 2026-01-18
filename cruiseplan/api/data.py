"""
Data acquisition API functions.

This module provides functions for downloading bathymetry data and searching
PANGAEA oceanographic databases.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from cruiseplan.api.types import BathymetryResult, PangaeaResult
from cruiseplan.config.exceptions import ValidationError

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


def _prepare_pangaea_config(
    query_terms: str,
    output_dir: str,
    output: Optional[str],
    lat_bounds: Optional[list[float]],
    lon_bounds: Optional[list[float]],
) -> dict:
    """
    Validate inputs and prepare file paths configuration.

    Parameters
    ----------
    query_terms : str
        Search terms or DOI
    output_dir : str
        Output directory path
    output : Optional[str]
        Custom base filename
    lat_bounds, lon_bounds : Optional[list[float]]
        Geographic bounds for search

    Returns
    -------
    dict
        Configuration with validated bbox, paths, and filenames
    """
    from cruiseplan.api.init_utils import _validate_lat_lon_bounds

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
    stations_file = output_dir_path / f"{base_name}.pkl"

    return {
        "bbox": bbox,
        "output_dir_path": output_dir_path,
        "base_name": base_name,
        "dois_file": dois_file,
        "stations_file": stations_file,
    }


def _process_doi_file(
    query_terms: str, dois_file: Path
) -> tuple[list[str], list[Path]]:
    """Process DOI file input mode."""
    import shutil

    from cruiseplan.data.pangaea import read_doi_list

    logger.info(f"📁 Processing DOI file: '{query_terms}'")
    clean_dois = read_doi_list(query_terms)
    logger.info(f"✅ Loaded {len(clean_dois)} DOIs from file")

    # Copy the input file as dois_file for consistency
    shutil.copy(query_terms, dois_file)
    generated_files = [dois_file]
    logger.info(f"📂 DOI file: {dois_file}")

    return clean_dois, generated_files


def _process_single_doi(
    query_terms: str, dois_file: Path, manager
) -> tuple[list[str], list[Path]]:
    """Process single DOI input mode."""
    logger.info(f"📄 Processing single DOI: '{query_terms}'")

    # Validate DOI format and clean it
    clean_doi = manager._clean_doi(query_terms)
    clean_dois = [clean_doi]
    logger.info(f"✅ Validated DOI: {clean_doi}")

    # Save single DOI to file for consistency with header
    with open(dois_file, "w") as f:
        f.write("# Single DOI Processing\n")
        f.write(f"# DOI: {query_terms}\n")
        f.write("#\n")
        f.write(f"{clean_doi}\n")
    generated_files = [dois_file]
    logger.info(f"📂 DOI file: {dois_file}")

    return clean_dois, generated_files


def _process_search_query(
    query_terms: str,
    bbox,
    lat_bounds: Optional[list[float]],
    lon_bounds: Optional[list[float]],
    limit: int,
    dois_file: Path,
    manager,
) -> tuple[list[str], list[Path]]:
    """Process search query input mode."""
    logger.info(f"🔍 Searching PANGAEA for: '{query_terms}'")
    if bbox:
        logger.info(f"📍 Geographic bounds: lat {lat_bounds}, lon {lon_bounds}")

    try:
        from pangaeapy.panquery import PanQuery

        pq = PanQuery(query_terms, bbox=bbox, limit=limit)
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

        # Save DOI list (intermediate file) with query header
        with open(dois_file, "w") as f:
            # Add header comment with search information
            f.write("# PANGAEA Search Results\n")
            f.write(f"# Query: {query_terms}\n")
            if bbox and lat_bounds and lon_bounds:
                f.write(f"# Geographic bounds: lat {lat_bounds}, lon {lon_bounds}\n")
            f.write(f"# Results limit: {limit}\n")
            f.write(
                f"# Generated: {pq.totalcount} total matches, showing first {len(clean_dois)}\n"
            )
            f.write("#\n")
            # Write DOI list
            for doi in clean_dois:
                f.write(f"{doi}\n")
        generated_files = [dois_file]

        logger.info(f"📂 DOI file: {dois_file}")
        return clean_dois, generated_files

    except ImportError:
        logger.exception(
            "❌ pangaeapy not available. Please install with: pip install pangaeapy"
        )
        raise RuntimeError(
            "pangaeapy package not available - please install with: pip install pangaeapy"
        )


def _resolve_doi_list(
    query_terms: str,
    config: dict,
    limit: int,
    manager,
    lat_bounds: Optional[list[float]],
    lon_bounds: Optional[list[float]],
) -> tuple[list[str], list[Path]]:
    """
    Determine input type and get clean DOI list.

    Parameters
    ----------
    query_terms : str
        Input query terms, DOI, or file path
    config : dict
        Configuration from _prepare_pangaea_config
    limit : int
        Maximum number of results for search mode
    manager : PangaeaManager
        PANGAEA manager instance
    lat_bounds, lon_bounds : Optional[list[float]]
        Geographic bounds for search mode

    Returns
    -------
    tuple[list[str], list[Path]]
        Clean DOI list and generated files list
    """
    bbox = config["bbox"]
    dois_file = config["dois_file"]

    # Detect query_terms type and get DOI list accordingly
    query_path = Path(query_terms)
    if query_terms.endswith(".txt") and query_path.exists():
        # DOI file mode: read DOIs from existing file
        return _process_doi_file(query_terms, dois_file)

    elif query_terms.startswith("10.") and "/" in query_terms:
        # Single DOI mode: validate and process single DOI
        return _process_single_doi(query_terms, dois_file, manager)

    else:
        # Search mode: search PANGAEA database
        return _process_search_query(
            query_terms, bbox, lat_bounds, lon_bounds, limit, dois_file, manager
        )


def _fetch_and_save_datasets(
    clean_dois: list[str],
    stations_file: Path,
    generated_files: list,
    rate_limit: float,
    merge_campaigns: bool,
) -> list:
    """
    Fetch detailed PANGAEA datasets and save to file.

    Parameters
    ----------
    clean_dois : list[str]
        List of clean DOI strings
    stations_file : Path
        Path where to save stations data
    generated_files : list
        List to append the stations file to
    rate_limit : float
        API request rate limit
    merge_campaigns : bool
        Whether to merge campaigns with same name

    Returns
    -------
    list
        Retrieved PANGAEA datasets
    """
    from cruiseplan.data.pangaea import PangaeaManager, save_campaign_data

    # Common processing for all modes - fetch detailed data
    logger.info(f"📂 Stations file: {stations_file}")

    # Now fetch detailed PANGAEA data with proper rate limiting
    logger.info(f"⚙️ Processing {len(clean_dois)} DOIs...")
    logger.info(f"🕐 Rate limit: {rate_limit} requests/second")

    manager = PangaeaManager()
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

    return detailed_datasets


def _build_pangaea_result(
    query_terms: str,
    detailed_datasets: list,
    generated_files: list,
    lat_bounds: Optional[list[float]],
    lon_bounds: Optional[list[float]],
    limit: int,
    stations_file: Path,
) -> PangaeaResult:
    """
    Construct the final PangaeaResult object with summary information.

    Parameters
    ----------
    query_terms : str
        Original search query terms
    detailed_datasets : list
        Retrieved PANGAEA datasets
    generated_files : list
        List of generated file paths
    lat_bounds, lon_bounds : Optional[list[float]]
        Geographic bounds used in search
    limit : int
        Maximum number of results processed
    stations_file : Path
        Path to the stations pickle file

    Returns
    -------
    PangaeaResult
        Structured result with data, files, and summary
    """
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
            "limit": limit,
        },
    )


def pangaea(
    query_terms: str,
    output_dir: str = "data",
    output: Optional[str] = None,
    lat_bounds: Optional[list[float]] = None,
    lon_bounds: Optional[list[float]] = None,
    limit: int = 10,
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
    limit : int
        Maximum number of results to process (default: 10)
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
    from cruiseplan.api.init_utils import (
        _handle_error_with_logging,
        _setup_verbose_logging,
    )
    from cruiseplan.data.pangaea import (
        PangaeaManager,
    )

    _setup_verbose_logging(verbose)

    try:
        # Validate inputs and prepare paths
        config = _prepare_pangaea_config(
            query_terms, output_dir, output, lat_bounds, lon_bounds
        )
        stations_file = config["stations_file"]

        manager = PangaeaManager()

        # Get DOI list based on input type
        clean_dois, generated_files = _resolve_doi_list(
            query_terms, config, limit, manager, lat_bounds, lon_bounds
        )

        # Fetch and save detailed datasets
        detailed_datasets = _fetch_and_save_datasets(
            clean_dois, stations_file, generated_files, rate_limit, merge_campaigns
        )

        return _build_pangaea_result(
            query_terms,
            detailed_datasets,
            generated_files,
            lat_bounds,
            lon_bounds,
            limit,
            stations_file,
        )

    except Exception as e:
        _handle_error_with_logging(e, "PANGAEA search failed", verbose)
        raise  # Re-raise the exception so caller knows it failed
