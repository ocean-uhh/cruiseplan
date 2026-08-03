"""
Unified PANGAEA command.

This module implements the 'cruiseplan pangaea' command that can either:
1. Search PANGAEA datasets by query + geographic bounds, then download station data
2. Process an existing DOI list file directly into station data

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def validate_lat_lon_bounds(
    lat_bounds: list[float], lon_bounds: list[float]
) -> tuple[float, float, float, float]:
    """
    Validate and convert latitude/longitude bounds into bounding box tuple.

    This is a simple CLI helper that validates the user input format.
    """
    if len(lat_bounds) != 2:
        raise ValueError("lat_bounds must contain exactly 2 values [min_lat, max_lat]")
    if len(lon_bounds) != 2:
        raise ValueError("lon_bounds must contain exactly 2 values [min_lon, max_lon]")

    min_lat, max_lat = lat_bounds
    min_lon, max_lon = lon_bounds

    if not (-90 <= min_lat <= 90) or not (-90 <= max_lat <= 90):
        raise ValueError("Latitude values must be between -90 and 90 degrees")
    if min_lat >= max_lat:
        raise ValueError("min_lat must be less than max_lat")

    return min_lon, min_lat, max_lon, max_lat


def determine_workflow_mode(args: argparse.Namespace) -> str:
    """
    Determine whether we're in search mode or DOI file mode.
    """
    if hasattr(args, "doi_file") and args.doi_file:
        return "doi_file"
    else:
        return "search"


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for pangaea command.

    Delegates all business logic to the cruiseplan.pangaea() API function.
    """
    from cruiseplan.cli import handle_cli_errors

    with handle_cli_errors("PANGAEA processing", args.verbose):
        if args.lat and args.lon:
            try:
                validate_lat_lon_bounds(args.lat, args.lon)
            except ValueError as e:
                print(f"ERROR: Invalid coordinate bounds: {e}", file=sys.stderr)
                sys.exit(1)

        result = cruiseplan.pangaea(
            query_terms=args.query_or_file,
            output_dir=str(args.output_dir),
            output=args.output,
            lat_bounds=args.lat,
            lon_bounds=args.lon,
            limit=args.limit,
            rate_limit=args.rate_limit,
            merge_campaigns=args.merge_campaigns,
            verbose=args.verbose,
        )

        print("")
        print("=" * 50)
        print("PANGAEA Processing Results")
        print("=" * 50)

        if result.stations_data:
            print(result)
            print("Generated files:")
            for file_path in result.files_created:
                print(f"  • {file_path}")

            print("Next steps:")
            stations_file = next(
                (f for f in result.files_created if str(f).endswith(".pkl")),
                None,
            )
            if stations_file:
                print(f"   1. Review stations: {stations_file}")
                print(f"   2. Plan cruise: cruiseplan stations -p {stations_file}")
        else:
            print("PANGAEA processing failed")
            sys.exit(1)

        sys.exit(0)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the pangaea subparser and return it."""
    p = subparsers.add_parser(
        "pangaea",
        help="Search and download PANGAEA datasets, or process existing DOI lists",
        description="Unified PANGAEA data processor - search by query + geographic bounds OR process existing DOI files",
        epilog="""
This command combines PANGAEA dataset search and download functionality:

SEARCH + DOWNLOAD MODE (requires --lat and --lon):
  cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -30 --output atlantic_study
  → Generates: atlantic_study_dois.txt + atlantic_study_stations.pkl

DOI FILE MODE (provide existing .txt file):
  cruiseplan pangaea arctic_dois.txt --output arctic_analysis
  → Generates: arctic_analysis_stations.pkl

Examples:
  cruiseplan pangaea "CTD Arctic Ocean" --lat 70 85 --lon -180 -120 --limit 50
  cruiseplan pangaea my_dois.txt --rate-limit 0.5 --merge-campaigns
  cruiseplan pangaea "salinity North Atlantic" --lat 40 65 --lon -70 -10 --output north_atlantic
        """,
    )
    p.add_argument(
        "query_or_file",
        help="Search query string (for search mode) or DOI file path (for file mode)",
    )
    p.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds for search mode (e.g., --lat 50 70)",
    )
    p.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for search mode (e.g., --lon -60 -30)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum search results to return (default: 10, max recommended: 100)",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    p.add_argument(
        "--output",
        help="Base filename for outputs (without extension or directory)",
    )
    p.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="API request rate limit (requests per second, default: 1.0)",
    )
    p.add_argument(
        "--merge-campaigns",
        action="store_true",
        default=True,
        help="Merge campaigns with the same name (default: true)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
