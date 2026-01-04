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
    _format_progress_header,
    _format_success_message,
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import (
    _apply_cli_defaults,
    _detect_pangaea_mode,
    _handle_deprecated_cli_params,
    _validate_coordinate_bounds,
)
from cruiseplan.utils.output_formatting import (
    _format_api_error,
    _format_cli_error,
    _format_output_summary,
    _standardize_output_setup,
)

# Re-export functions for test mocking (cleaner than complex patch paths)
__all__ = [
    "_collect_generated_files",
    "_format_progress_header",
    "_format_success_message",
    "_setup_cli_logging",
    "determine_workflow_mode",
    "main",
    "validate_lat_lon_bounds",
]

logger = logging.getLogger(__name__)


def validate_lat_lon_bounds(
    lat_bounds: List[float], lon_bounds: List[float]
) -> Tuple[float, float, float, float]:
    """
    Validate and convert latitude/longitude bounds into bounding box tuple.

    CLI-specific coordinate validation that handles user input formats.
    Uses the new utility function for core validation.

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
        # Use new utility for comprehensive validation
        bbox = _validate_coordinate_bounds(lat_bounds, lon_bounds)
        return bbox
    except ValueError as e:
        raise CLIError(f"Invalid lat/lon bounds. Error: {e}") from e


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
        # Handle deprecated parameters (currently no deprecated params for v0.3.0+)
        _handle_deprecated_cli_params(args)

        # Apply standard CLI defaults
        _apply_cli_defaults(args)

        # Setup logging using new utility
        _setup_cli_logging(verbose=getattr(args, "verbose", False))

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

        # Standardize output setup using new utilities
        output_dir, base_name, format_paths = _standardize_output_setup(
            args, suffix="_stations", multi_formats=["pkl", "txt"]
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "pangaea")

        # Override output paths with standardized paths
        api_params["output_dir"] = output_dir
        api_params["output"] = base_name

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
            # Use new standardized output summary
            success_summary = _format_output_summary(
                all_generated_files, "PANGAEA data processing"
            )
            logger.info(success_summary)

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
        error_msg = _format_cli_error(
            "PANGAEA data processing",
            e,
            suggestions=[
                "Check query terms are valid",
                "Verify coordinate bounds format",
                "Ensure DOI file exists and is readable",
            ],
        )
        logger.error(error_msg)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        # Check if it's likely a network/API error
        if "ConnectionError" in str(type(e)) or "requests" in str(type(e)):
            error_msg = _format_api_error(
                "PANGAEA search", "PANGAEA", e, retry_suggestion=True
            )
        else:
            error_msg = _format_cli_error(
                "PANGAEA data processing",
                e,
                suggestions=[
                    "Check query terms",
                    "Verify coordinate bounds",
                    "Check network connection",
                    "Run with --verbose for more details",
                ],
            )
        logger.error(error_msg)
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
