"""
Unified PANGAEA command combining search and download functionality.

This module implements the 'cruiseplan pangaea' command that can either:
1. Search PANGAEA datasets by query + geographic bounds, then download station data
2. Process an existing DOI list file directly into station data

Supports base filename output strategy for consistent file naming.
"""

import argparse
import logging
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from cruiseplan.cli.utils import (
    CLIError,
    read_doi_list,
    setup_logging,
    validate_input_file,
)
from cruiseplan.data.pangaea import PangaeaManager
from cruiseplan.utils.coordinates import format_geographic_bounds

logger = logging.getLogger(__name__)


def validate_lat_lon_bounds(
    lat_bounds: List[float], lon_bounds: List[float]
) -> Tuple[float, float, float, float]:
    """
    Validate and convert latitude/longitude bounds into bounding box tuple.

    Parameters
    ----------
    lat_bounds : List[float]
        List of [min_lat, max_lat]
    lon_bounds : List[float]
        List of [min_lon, max_lon]

    Returns
    -------
    Tuple[float, float, float, float]
        Bounding box as (min_lon, min_lat, max_lon, max_lat)

    Raises
    ------
    CLIError
        If bounds are invalid
    """
    try:
        min_lat, max_lat = lat_bounds
        min_lon, max_lon = lon_bounds

        # Latitude validation (always -90 to 90)
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        if min_lat >= max_lat:
            raise ValueError("min_lat must be less than max_lat")

        # Longitude validation: support both -180/180 and 0/360 but prevent mixing
        # Check if using -180/180 format
        if -180 <= min_lon <= 180 and -180 <= max_lon <= 180:
            lon_format = "180"
        # Check if using 0/360 format
        elif 0 <= min_lon <= 360 and 0 <= max_lon <= 360:
            lon_format = "360"
        else:
            # Mixed or invalid format
            raise ValueError(
                "Longitude coordinates must be either:\n"
                "  - Both in -180 to 180 format (e.g., --lon -90 -30)\n"
                "  - Both in 0 to 360 format (e.g., --lon 270 330)\n"
                "  - Cannot mix formats (e.g., --lon -90 240 is invalid)"
            )

        # Check ordering within the chosen format
        if min_lon >= max_lon:
            if lon_format == "360" and min_lon > 180 and max_lon < 180:
                # Special case: crossing 0° meridian in 360 format (e.g., 350° to 10°)
                # This is valid, so don't raise error
                pass
            else:
                raise ValueError("min_lon must be less than max_lon")

        return (min_lon, min_lat, max_lon, max_lat)

    except (ValueError, IndexError) as e:
        raise CLIError(f"Invalid lat/lon bounds. Error: {e}")


def search_pangaea_datasets(
    query: str,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    limit: int = 10,
) -> List[str]:
    """
    Search PANGAEA datasets and return list of DOIs.

    Parameters
    ----------
    query : str
        Search query string
    bbox : Optional[Tuple[float, float, float, float]]
        Bounding box as (min_lon, min_lat, max_lon, max_lat)
    limit : int
        Maximum number of results to return

    Returns
    -------
    List[str]
        List of DOI strings found

    Raises
    ------
    CLIError
        If search fails
    """
    try:
        manager = PangaeaManager()
        logger.info(f"🔍 Searching PANGAEA for: '{query}'")

        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            bounds_str = format_geographic_bounds(min_lon, min_lat, max_lon, max_lat)
            logger.info(f"📍 Geographic bounds: {bounds_str}")

        # Use the existing search method
        datasets = manager.search(query=query, bbox=bbox, limit=limit)

        if not datasets:
            logger.warning("⚠️  No datasets found matching search criteria")
            return []

        # Extract DOIs from the returned datasets
        dois = []
        for dataset in datasets:
            doi = dataset.get("doi")
            if doi:
                dois.append(doi)

        logger.info(f"✓ Found {len(dois)} datasets with valid DOIs")
        return dois

    except Exception as e:
        raise CLIError(f"Search failed: {e}")


def save_doi_list(dois: List[str], output_path: Path) -> None:
    """
    Save DOI list to text file.

    Parameters
    ----------
    dois : List[str]
        List of DOI strings to save
    output_path : Path
        Output file path

    Raises
    ------
    CLIError
        If save operation fails
    """
    try:
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            for doi in dois:
                f.write(f"{doi}\n")

        logger.info(f"💾 Saved {len(dois)} DOIs to {output_path}")

    except Exception as e:
        raise CLIError(f"Failed to save DOI list: {e}")


def fetch_pangaea_data(
    doi_list: List[str], rate_limit: float = 1.0, merge_campaigns: bool = True
) -> List[dict]:
    """
    CLI wrapper for fetching PANGAEA datasets with logging.

    Parameters
    ----------
    doi_list : List[str]
        List of DOI strings to fetch
    rate_limit : float
        Requests per second limit
    merge_campaigns : bool
        Whether to merge campaigns with same name

    Returns
    -------
    List[dict]
        List of dataset dictionaries
    """

    def progress_callback(current: int, total: int, message: str) -> None:
        """Progress callback that logs to CLI logger."""
        if current == 0:
            logger.info(message)
            logger.info(f"🕐 Rate limit: {rate_limit} requests/second")
        elif "✓" in message or "⚠" in message or "✗" in message:
            logger.info(f"[{current}/{total}] {message}")
        elif "Merged" in message or "Completed" in message:
            logger.info(message)
        elif "interrupted" in message:
            logger.info(f"\n\n{message}")
        else:
            logger.info(f"[{current}/{total}] {message}")

    pangaea = PangaeaManager()
    return pangaea.fetch_datasets(
        doi_list=doi_list,
        rate_limit=rate_limit,
        merge_campaigns=merge_campaigns,
        progress_callback=progress_callback,
    )


def save_pangaea_pickle(
    datasets: List[dict], output_path: Path, original_count: int = None
) -> None:
    """
    CLI wrapper for saving PANGAEA datasets to pickle file.

    Parameters
    ----------
    datasets : List[dict]
        List of dataset dictionaries
    output_path : Path
        Output file path
    original_count : int, optional
        Count of datasets before any merging (for accurate summary)
    """
    from cruiseplan.data.pangaea import save_campaign_data

    def progress_callback(message: str) -> None:
        """Progress callback that logs to CLI logger."""
        logger.info(message)

    try:
        save_campaign_data(datasets, output_path, progress_callback, original_count)
    except ValueError as e:
        raise CLIError(str(e))


def validate_dois(doi_list: List[str]) -> List[str]:
    """
    Validate DOI format and filter invalid entries.

    Uses the existing DOI validation from data.pangaea module with
    CLI-friendly prefix cleanup.

    Parameters
    ----------
    doi_list : List[str]
        List of DOI strings

    Returns
    -------
    List[str]
        List of valid DOIs
    """
    from cruiseplan.data.pangaea import _is_valid_doi

    valid_dois = []

    for doi in doi_list:
        # Clean up common prefixes that users might include
        clean_doi = doi.strip()

        if clean_doi.startswith("https://doi.org/"):
            clean_doi = clean_doi.replace("https://doi.org/", "")
        elif clean_doi.startswith("doi:"):
            clean_doi = clean_doi.replace("doi:", "")

        # Use the strict validation from data module
        if _is_valid_doi(clean_doi):
            valid_dois.append(clean_doi)
        else:
            logger.warning(f"⚠️  Skipping invalid DOI format: {doi}")

    if not valid_dois:
        raise CLIError("No valid DOIs found in input file")

    if len(valid_dois) != len(doi_list):
        logger.info(f"🔍 Filtered {len(doi_list) - len(valid_dois)} invalid DOIs")

    return valid_dois


def determine_workflow_mode(args: argparse.Namespace) -> str:
    """
    Determine whether we're in search mode or DOI file mode.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments

    Returns
    -------
    str
        Either 'search' or 'doi_file'
    """
    # If first positional argument looks like a file path, it's DOI file mode
    if hasattr(args, "query_or_file") and args.query_or_file:
        potential_file = Path(args.query_or_file)
        if potential_file.exists() and potential_file.suffix == ".txt":
            return "doi_file"

    # If lat/lon bounds provided, must be search mode
    if args.lat and args.lon:
        return "search"

    # If query looks like search terms (no file extension), search mode
    if hasattr(args, "query_or_file") and not Path(args.query_or_file).suffix:
        return "search"

    # Default to search mode if ambiguous
    return "search"


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for unified PANGAEA command.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments
    """
    try:
        # Setup logging
        setup_logging(verbose=getattr(args, "verbose", False))

        # Determine workflow mode
        mode = determine_workflow_mode(args)

        logger.info("=" * 60)
        logger.info("🌊 CRUISEPLAN PANGAEA DATA PROCESSOR")
        logger.info("=" * 60)

        # Handle deprecated --output-file option
        if hasattr(args, "output_file") and args.output_file:
            logger.warning(
                "⚠️  WARNING: '--output-file' is deprecated and will be removed in v0.3.0."
            )
            logger.warning("   Please use '--output' for base filename instead.\n")

        if mode == "search":
            # Search + Download workflow
            query = args.query_or_file
            logger.info("📋 Mode: Search + Download")
            logger.info(f"🔍 Query: '{query}'")

            # Validate that lat/lon are provided for search mode
            if not (args.lat and args.lon):
                raise CLIError(
                    "Search mode requires both --lat and --lon bounds.\n"
                    "Example: cruiseplan pangaea 'CTD temperature' --lat 50 60 --lon -50 -30"
                )

            # Parse lat/lon bounds
            bbox = validate_lat_lon_bounds(args.lat, args.lon)

            # Validate limit
            if args.limit <= 0:
                raise CLIError("Limit must be a positive integer")
            if args.limit > 100:
                logger.warning(
                    "⚠️  Large limit values may result in slow searches. Consider using --limit 50 or less."
                )

            # Search for datasets
            dois = search_pangaea_datasets(query=query, bbox=bbox, limit=args.limit)

            if not dois:
                logger.warning("❌ No DOIs found. Try broadening your search criteria.")
                sys.exit(1)

            # Determine output paths using base filename strategy
            base_name = getattr(args, "output", None)
            output_dir = args.output_dir

            # Handle legacy --output-file for backwards compatibility
            if hasattr(args, "output_file") and args.output_file:
                # Use the provided file path directly for stations file
                stations_file = args.output_file
                # Generate DOI file based on stations file name
                base_name = args.output_file.stem.replace("_stations", "").replace(
                    "_pangaea_data", ""
                )
                dois_file = args.output_file.parent / f"{base_name}_dois.txt"
            else:
                # Generate base filename if not provided
                if not base_name:
                    safe_query = "".join(c if c.isalnum() else "_" for c in query)
                    safe_query = re.sub(r"_+", "_", safe_query).strip("_")
                    base_name = safe_query

                dois_file = output_dir / f"{base_name}_dois.txt"
                stations_file = output_dir / f"{base_name}_stations.pkl"

            # Save DOI list (intermediate file)
            save_doi_list(dois, dois_file)

            logger.info(f"📂 DOI file: {dois_file}")
            logger.info(f"📂 Stations file: {stations_file}")
            logger.info("")

        else:
            # DOI file input workflow
            doi_file_path = validate_input_file(Path(args.query_or_file))
            logger.info("📋 Mode: DOI File Processing")
            logger.info(f"📁 Input file: {doi_file_path}")

            # Determine output path using base filename strategy
            base_name = getattr(args, "output", None)
            output_dir = args.output_dir

            # Handle legacy --output-file for backwards compatibility
            if hasattr(args, "output_file") and args.output_file:
                stations_file = args.output_file
            else:
                # Generate base filename from input file if not provided
                if not base_name:
                    base_name = doi_file_path.stem.replace(
                        "_dois", ""
                    )  # Remove _dois suffix if present

                stations_file = output_dir / f"{base_name}_stations.pkl"

            # Read DOI list
            dois = read_doi_list(doi_file_path)

            logger.info(f"📂 Stations file: {stations_file}")
            logger.info("")

        # Common processing for both modes
        logger.info(f"⚙️  Processing {len(dois)} DOIs...")
        logger.info(f"🕐 Rate limit: {args.rate_limit} requests/second")
        logger.info("")

        # Validate DOIs
        valid_dois = validate_dois(dois)

        # Fetch PANGAEA data
        datasets = fetch_pangaea_data(
            valid_dois, rate_limit=args.rate_limit, merge_campaigns=args.merge_campaigns
        )

        if not datasets:
            logger.warning(
                "⚠️  No datasets retrieved. Check DOI list and network connection."
            )
            return

        # Save results
        save_pangaea_pickle(datasets, stations_file, len(valid_dois))

        logger.info("")
        logger.info("✅ PANGAEA processing completed successfully!")
        logger.info("")
        logger.info("🚀 Next steps:")
        if mode == "search":
            logger.info(f"   1. Review DOIs: {dois_file}")
            logger.info(f"   2. Review stations: {stations_file}")
            logger.info(f"   3. Plan cruise: cruiseplan stations -p {stations_file}")
        else:
            logger.info(f"   1. Review stations: {stations_file}")
            logger.info(f"   2. Plan cruise: cruiseplan stations -p {stations_file}")

    except CLIError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    parser = argparse.ArgumentParser(description="Unified PANGAEA search and download")
    parser.add_argument("query_or_file", help="Search query or DOI file path")
    parser.add_argument("--lat", nargs=2, type=float, help="Latitude bounds")
    parser.add_argument("--lon", nargs=2, type=float, help="Longitude bounds")
    parser.add_argument("--limit", type=int, default=10, help="Result limit")
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("data"), help="Output directory"
    )
    parser.add_argument(
        "--output", help="Base filename for outputs (without extension)"
    )
    parser.add_argument("--rate-limit", type=float, default=1.0, help="API rate limit")
    parser.add_argument(
        "--merge-campaigns", action="store_true", default=True, help="Merge campaigns"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()
    main(args)
