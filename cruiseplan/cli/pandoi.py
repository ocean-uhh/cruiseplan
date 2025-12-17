"""
PANGAEA search command using PanQuery.

This module implements the 'cruiseplan pandoi' command for searching
PANGAEA datasets by query terms and geographic bounding box, outputting
DOI lists that can be used with 'cruiseplan pangaea'.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from cruiseplan.cli.utils import CLIError, setup_logging
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
        logger.info(f"Searching PANGAEA for: '{query}'")

        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            bounds_str = format_geographic_bounds(min_lon, min_lat, max_lon, max_lat)
            logger.info(f"Geographic bounds: {bounds_str}")

        # Use the existing search method
        datasets = manager.search(query=query, bbox=bbox, limit=limit)

        if not datasets:
            logger.warning("No datasets found matching search criteria")
            return []

        # Extract DOIs from the returned datasets
        dois = []
        for dataset in datasets:
            doi = dataset.get("doi")
            if doi:
                dois.append(doi)

        logger.info(f"Found {len(dois)} datasets with valid DOIs")
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

        logger.info(f"Saved {len(dois)} DOIs to {output_path}")

    except Exception as e:
        raise CLIError(f"Failed to save DOI list: {e}")


def main(args: argparse.Namespace) -> None:
    """Main entry point for pandoi CLI command."""
    # Setup logging
    setup_logging(verbose=args.verbose)

    try:
        # Parse lat/lon bounds if provided
        bbox = None
        # Ensure lat and lon bounds are specified together
        if (args.lat and not args.lon) or (args.lon and not args.lat):
            raise CLIError(
                "Both --lat and --lon must be specified together for geographic filtering."
            )
        if args.lat and args.lon:
            bbox = validate_lat_lon_bounds(args.lat, args.lon)

        # Validate limit
        if args.limit <= 0:
            raise CLIError("Limit must be a positive integer")
        if args.limit > 100:
            logger.warning(
                "Large limit values may result in slow searches. Consider using --limit 50 or less."
            )

        # Search for datasets
        dois = search_pangaea_datasets(query=args.query, bbox=bbox, limit=args.limit)

        if not dois:
            logger.warning("No DOIs found. Try broadening your search criteria.")
            sys.exit(1)

        # Determine output path
        if args.output_file:
            output_path = args.output_file
        else:
            # Create default filename from query and use output directory
            import re

            safe_query = "".join(c if c.isalnum() else "_" for c in args.query)
            # Collapse multiple consecutive underscores
            safe_query = re.sub(r"_+", "_", safe_query).strip("_")
            output_path = args.output_dir / f"{safe_query}_dois.txt"

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save DOI list
        save_doi_list(dois, output_path)

        # Success summary
        logger.info("Search completed successfully!")
        logger.info("Next steps:")
        logger.info(f"  1. Review DOIs in: {output_path}")
        logger.info(f"  2. Fetch datasets: cruiseplan pangaea {output_path}")

        # Generate expected output filename for the pangaea command
        # Based on pangaea command's naming pattern: <input_basename>_pangaea_data.pkl
        # The pangaea command defaults to data/ directory, so use that path
        pangaea_output = f"data/{output_path.stem}_pangaea_data.pkl"
        logger.info(f"     (This will create: {pangaea_output})")
        logger.info(f"  3. Plan stations: cruiseplan stations -p {pangaea_output}")

    except CLIError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nSearch interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="PANGAEA dataset search")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--lat", nargs=2, type=float, help="Latitude bounds")
    parser.add_argument("--lon", nargs=2, type=float, help="Longitude bounds")
    parser.add_argument("--limit", type=int, default=10, help="Result limit")
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("data"), help="Output directory"
    )
    parser.add_argument("--output-file", type=Path, help="Output file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    main(args)
