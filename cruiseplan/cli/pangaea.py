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


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for pangaea command.

    Delegates all business logic to the cruiseplan.pangaea() API function.
    """
    try:
        # Determine workflow mode (CLI-specific logic)
        mode = determine_workflow_mode(args)

        # Handle DOI file mode (not yet implemented in API - would need enhancement)
        if mode == "doi_file":
            print("❌ DOI file mode not yet implemented in thin CLI", file=sys.stderr)
            sys.exit(1)

        # Validate lat/lon bounds if provided (CLI-specific validation)
        lat_bounds = getattr(args, "lat", None)
        lon_bounds = getattr(args, "lon", None)

        if lat_bounds and lon_bounds:
            try:
                validate_lat_lon_bounds(lat_bounds, lon_bounds)
            except ValueError as e:
                print(f"❌ Invalid coordinate bounds: {e}", file=sys.stderr)
                sys.exit(1)

        # Call the API function with CLI arguments
        result = cruiseplan.pangaea(
            query_terms=args.query,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            max_results=getattr(args, "max_results", 100),
            rate_limit=getattr(args, "rate_limit", 1.0),
            merge_campaigns=getattr(args, "merge_campaigns", True),
            verbose=getattr(args, "verbose", False),
        )

        # Display results
        print("")
        print("=" * 50)
        print("PANGAEA Processing Results")
        print("=" * 50)

        if result.stations_data:
            print(f"✅ {result}")
            print("📁 Generated files:")
            for file_path in result.files_created:
                print(f"  • {file_path}")

            # Show next steps
            print("🚀 Next steps:")
            stations_file = next(
                (f for f in result.files_created if str(f).endswith("_stations.pkl")),
                None,
            )
            if stations_file:
                print(f"   1. Review stations: {stations_file}")
                print(f"   2. Plan cruise: cruiseplan stations -p {stations_file}")
        else:
            print("❌ PANGAEA processing failed")
            sys.exit(1)

    except cruiseplan.ValidationError as e:
        print(f"❌ Configuration validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except cruiseplan.FileError as e:
        print(f"❌ File operation error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ PANGAEA processing error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    parser = argparse.ArgumentParser(description="Search and download PANGAEA data")
    parser.add_argument("query", help="Search terms for PANGAEA database")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for station files",
    )
    parser.add_argument(
        "--output", type=str, help="Base filename for outputs (without extension)"
    )
    parser.add_argument(
        "--lat",
        type=float,
        nargs=2,
        metavar=("MIN_LAT", "MAX_LAT"),
        help="Latitude bounds [min_lat, max_lat]",
    )
    parser.add_argument(
        "--lon",
        type=float,
        nargs=2,
        metavar=("MIN_LON", "MAX_LON"),
        help="Longitude bounds [min_lon, max_lon]",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=100,
        help="Maximum number of results to process",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="API request rate limit (requests per second)",
    )
    parser.add_argument(
        "--no-merge-campaigns",
        action="store_false",
        dest="merge_campaigns",
        help="Don't merge campaigns with the same name",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    main(args)
