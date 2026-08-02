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
from cruiseplan.config.values import (
    BATHY_SOURCES,
    DEFAULT_BATHY_DIR,
    DEFAULT_BATHY_SOURCE,
)

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> None:
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
        lat_bounds = tuple(args.lat) if args.lat else None
        lon_bounds = tuple(args.lon) if args.lon else None

        result = stations(
            lat_bounds=lat_bounds,
            lon_bounds=lon_bounds,
            output_dir=str(args.output_dir),
            output=getattr(args, "output", None),
            config_file=(
                str(getattr(args, "config_file", None))
                if getattr(args, "config_file", None)
                else None
            ),
            pangaea_file=str(args.pangaea_file) if args.pangaea_file else None,
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=str(getattr(args, "bathy_dir", "data/bathymetry")),
            bathy_contours=getattr(args, "bathy_contours", None),
            bathy_stride=getattr(args, "bathy_stride", 10),
            max_depth=getattr(args, "max_depth", None),
            overwrite=getattr(args, "overwrite", False),
            verbose=getattr(args, "verbose", False),
        )

        logger.info(str(result))

    except (ImportError, ValueError, FileNotFoundError, RuntimeError) as e:
        error_msg = f"ERROR: Interactive station placement failed: {e}\nSuggestions:\n"
        error_msg += "  • Check coordinate bounds are valid\n"
        error_msg += "  • Verify PANGAEA file format if provided\n"
        error_msg += "  • Ensure matplotlib is installed\n"
        error_msg += "  • Check bathymetry data availability\n"
        error_msg += "  • Run with --verbose for more details"
        logger.exception(error_msg)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\nOperation cancelled by user.")
        sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the stations subparser and return it."""
    p = subparsers.add_parser(
        "stations", help="Interactive station placement with PANGAEA background"
    )
    p.add_argument(
        "config_file",
        type=Path,
        nargs="?",
        metavar="CONFIG_FILE",
        help="Existing YAML cruise configuration file to load and edit (optional)",
    )
    p.add_argument(
        "-p", "--pangaea-file", type=Path, help="PANGAEA campaigns pickle file"
    )
    p.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=(45, 70),
        help="Latitude bounds (default: 45 70)",
    )
    p.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=(-65, -5),
        help="Longitude bounds (default: -65 -5)",
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file without prompting",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    p.add_argument(
        "--bathy-source",
        choices=BATHY_SOURCES,
        default=DEFAULT_BATHY_SOURCE,
        help="Bathymetry dataset (default: gebco2025)",
    )
    p.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path(DEFAULT_BATHY_DIR),
        help="Directory containing bathymetry data (default: data/bathymetry)",
    )
    p.add_argument(
        "--bathy-contours",
        type=float,
        nargs="+",
        metavar="DEPTH",
        help="Bathymetry contour depths in metres (e.g. --bathy-contours 200 500 1000 2000). Replaces defaults.",
    )
    p.add_argument(
        "--bathy-stride",
        type=int,
        default=10,
        help="Bathymetry grid downsampling factor: 1 = full resolution, higher = faster but less detail (default: 10)",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="METRES",
        help="Maximum water depth (m) for the colour scale (e.g. 500 to focus on shelf seas)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
