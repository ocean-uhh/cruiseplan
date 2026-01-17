"""
Interactive station placement command.

Thin CLI wrapper that calls the cruiseplan.stations() API function.
This follows the established pattern used by process.py, validate.py, map.py, and schedule.py.
"""

import argparse
import logging
import sys
from pathlib import Path

from cruiseplan.api.stations_api import stations

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for interactive station placement.

    Thin CLI wrapper that calls the cruiseplan.stations() API function.
    This follows the established pattern used by process.py, validate.py, map.py, and schedule.py.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments
    """
    try:
        # Convert CLI args to API parameters
        lat_bounds = tuple(args.lat) if args.lat else None
        lon_bounds = tuple(args.lon) if args.lon else None

        # Call the API function
        result = stations(
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            output_dir=str(args.output_dir),
            output=getattr(args, "output", None),
            pangaea_file=str(args.pangaea_file) if args.pangaea_file else None,
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_dir=str(getattr(args, "bathy_dir", "data")),
            high_resolution=getattr(args, "high_resolution", False),
            overwrite=getattr(args, "overwrite", False),
            verbose=getattr(args, "verbose", False),
        )

        # The API function handles all logging and user interaction
        logger.info(f"✅ {result}")

    except (ImportError, ValueError, FileNotFoundError, RuntimeError) as e:
        # Inline simple error formatting
        error_msg = f"❌ Interactive station placement failed: {e}\nSuggestions:\n"
        error_msg += "  • Check coordinate bounds are valid\n"
        error_msg += "  • Verify PANGAEA file format if provided\n"
        error_msg += "  • Ensure matplotlib is installed\n"
        error_msg += "  • Check bathymetry data availability\n"
        error_msg += "  • Run with --verbose for more details"
        logger.exception(error_msg)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(description="Interactive station placement")
    parser.add_argument(
        "-p", "--pangaea-file", type=Path, help="PANGAEA campaigns pickle file"
    )
    parser.add_argument(
        "--lat", nargs=2, type=float, metavar=("MIN", "MAX"), help="Latitude bounds"
    )
    parser.add_argument(
        "--lon", nargs=2, type=float, metavar=("MIN", "MAX"), help="Longitude bounds"
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("."), help="Output directory"
    )
    parser.add_argument(
        "--bathy-source", choices=["etopo2022", "gebco2025"], default="etopo2022"
    )
    parser.add_argument(
        "--bathy-dir", type=Path, default=Path("data"), help="Bathymetry directory"
    )

    args = parser.parse_args()
    main(args)
