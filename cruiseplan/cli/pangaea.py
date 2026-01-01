"""
Unified PANGAEA command - API-First Architecture.

This module implements the 'cruiseplan pangaea' command that can either:
1. Search PANGAEA datasets by query + geographic bounds, then download station data
2. Process an existing DOI list file directly into station data

Uses the API-first architecture pattern with proper separation of concerns:
- CLI layer handles argument parsing and output formatting
- API layer (cruiseplan.__init__) contains business logic
- Utility functions provide consistent formatting and error handling
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

import cruiseplan
from cruiseplan.cli.cli_utils import (
    CLIError,
    _collect_generated_files,
    _format_error_message,
    _format_progress_header,
    _format_success_message,
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import (
    _detect_pangaea_mode,
)

logger = logging.getLogger(__name__)


def validate_lat_lon_bounds(
    lat_bounds: List[float], lon_bounds: List[float]
) -> Tuple[float, float, float, float]:
    """
    Validate and convert latitude/longitude bounds into bounding box tuple.

    CLI-specific coordinate validation that handles user input formats.

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


def determine_workflow_mode(args: argparse.Namespace) -> str:
    """
    Determine whether we're in search mode or DOI file mode.

    CLI-specific mode detection based on user input patterns.

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
    Main entry point for unified PANGAEA command using API-first architecture.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments
    """
    try:
        # Setup logging using new utility
        _setup_cli_logging(verbose=getattr(args, "verbose", False))

        # Handle deprecated --output-file option
        if hasattr(args, "output_file") and args.output_file:
            logger.warning(
                "⚠️  WARNING: '--output-file' is deprecated and will be removed in v0.3.0."
            )
            logger.warning("   Please use '--output' for base filename instead.\n")

        # Detect mode and validate parameters using utility function
        mode, processed_params = _detect_pangaea_mode(args)

        # Format progress header using new utility
        _format_progress_header(
            operation="PANGAEA Data Processing",
            config_file=None,
            mode=mode,
            query=processed_params.get("query", ""),
            lat_bounds=getattr(args, "lat", None),
            lon_bounds=getattr(args, "lon", None),
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "pangaea")

        # Call API function instead of complex processing logic
        logger.info("Searching and processing PANGAEA data...")
        stations_data, generated_files = cruiseplan.pangaea(**api_params)

        # Convert API response to CLI format using bridge utility
        api_response = (stations_data, generated_files)
        cli_response = _convert_api_response_to_cli(api_response, "pangaea")

        # Collect generated files using utility
        all_generated_files = _collect_generated_files(
            cli_response, base_patterns=["*_dois.txt", "*_stations.pkl"]
        )

        if cli_response.get("success", True) and stations_data:
            # Format success message using new utility
            _format_success_message("PANGAEA data processing", all_generated_files)

            # Show next steps
            logger.info("🚀 Next steps:")
            if generated_files:
                stations_file = next(
                    (f for f in generated_files if str(f).endswith("_stations.pkl")),
                    None,
                )
                if stations_file:
                    logger.info(f"   1. Review stations: {stations_file}")
                    logger.info(
                        f"   2. Plan cruise: cruiseplan stations -p {stations_file}"
                    )
        else:
            errors = cli_response.get("errors", ["PANGAEA processing failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            sys.exit(1)

    except CLIError as e:
        _format_error_message("pangaea", e)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        _format_error_message(
            "pangaea",
            e,
            [
                "Check query terms",
                "Verify coordinate bounds",
                "Check network connection",
            ],
        )
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(description="Process PANGAEA datasets")
    parser.add_argument("query_or_file", help="Search query or DOI file path")
    parser.add_argument("--lat", nargs=2, type=float, help="Latitude bounds")
    parser.add_argument("--lon", nargs=2, type=float, help="Longitude bounds")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", help="Base filename for outputs")
    parser.add_argument("--limit", type=int, default=100, help="Max results")
    parser.add_argument("--verbose", "-v", action="store_true")

    args = parser.parse_args()
    main(args)