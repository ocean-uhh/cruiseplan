"""
Map generation command.

This module implements the 'cruiseplan map' command for generating
cruise track visualisations (PNG maps and KML files).

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan
from cruiseplan.cli import handle_cli_errors
from cruiseplan.config.values import (
    BATHY_SOURCES,
    DEFAULT_BATHY_DIR,
    DEFAULT_BATHY_SOURCE,
)


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for map command.

    Delegates all business logic to the cruiseplan.map() API function.
    """
    verbose = getattr(args, "verbose", False)
    with handle_cli_errors("map", verbose):
        format_list = getattr(args, "format", None)
        format_str = ",".join(format_list) if format_list else "all"
        result = cruiseplan.map(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            format=format_str,
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            bathy_stride=getattr(args, "bathy_stride", 5),
            bathy_contours=getattr(args, "bathy_contours", None),
            lat_bounds=getattr(args, "lat", None),
            lon_bounds=getattr(args, "lon", None),
            figsize=getattr(args, "figsize", None),
            show_plot=getattr(args, "show_plot", False),
            no_ports=getattr(args, "no_ports", False),
            no_title=getattr(args, "no_title", False),
            no_labels=getattr(args, "no_labels", False),
            no_legend=getattr(args, "no_legend", False),
            verbose=verbose,
            max_depth=getattr(args, "max_depth", None),
        )

        print("")
        print("=" * 50)
        print("Map Generation Results")
        print("=" * 50)

        if result.map_files:
            print(result)
            print("Generated files:")
            for file_path in result.map_files:
                print(f"  • {file_path}")

            print("Generation summary:")
            print(f"  • Config file: {result.summary.get('config_file', 'N/A')}")
            print(f"  • Output format: {result.format}")
            print(f"  • Files generated: {result.summary.get('files_generated', 0)}")
            print(f"  • Output directory: {result.summary.get('output_dir', 'N/A')}")
        else:
            print("Map generation failed")
            if "error" in result.summary:
                print(f"Error: {result.summary['error']}")
            sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the map subparser and return it."""
    p = subparsers.add_parser(
        "map",
        help="Generate PNG maps and KML geographic data from YAML configuration",
        description="Create static PNG maps and/or KML files from cruise configuration catalog",
        epilog="""
This command generates PNG maps and/or KML geographic data from cruise configuration.
PNG maps show stations, cruise tracks, ports, and bathymetric background.
KML files contain geographic data for Google Earth viewing of all catalog entities.

Examples:
  cruiseplan map cruise.yaml                              # Generate map with default settings
  cruiseplan map cruise.yaml -o maps/ --figsize 14 10     # Custom output dir and size
  cruiseplan map cruise.yaml --bathy-source gebco2025     # High-resolution bathymetry
  cruiseplan map cruise.yaml --output cruise_track        # Custom base filename
        """,
    )
    p.add_argument(
        "config_file",
        type=Path,
        metavar="CONFIG_FILE",
        help="YAML cruise configuration file",
    )
    p.add_argument(
        "--no-ports",
        action="store_true",
        help="Suppress plotting of departure and arrival ports in both PNG and KML outputs",
    )
    p.add_argument(
        "--no-title",
        action="store_true",
        help="Omit title from PNG map",
    )
    p.add_argument(
        "--no-labels",
        action="store_true",
        help="Omit station name labels from PNG map",
    )
    p.add_argument(
        "--no-legend",
        action="store_true",
        help="Omit legend from PNG map",
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
        type=str,
        help="Base filename for output maps (default: use config filename)",
    )
    p.add_argument(
        "--format",
        nargs="+",
        choices=["png", "kml"],
        default=None,
        metavar="FORMAT",
        help="Output formats: png kml (space-separated). Omit to generate all.",
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
        "--bathy-stride",
        type=int,
        default=5,
        help="Bathymetry grid downsampling factor: 1 = full resolution, higher = faster but less detail (default: 5)",
    )
    p.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[10, 8.1],
        help="Figure size in inches (default: 10 8.1)",
    )
    p.add_argument(
        "--show-plot",
        action="store_true",
        help="Display plot interactively instead of saving to file",
    )
    p.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds for map extent (e.g., --lat -75 -70)",
    )
    p.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for map extent (e.g., --lon 170 175)",
    )
    p.add_argument(
        "--bathy-contours",
        type=float,
        nargs="+",
        metavar="DEPTH",
        help="Bathymetry contour depths in metres (e.g. --bathy-contours 200 500 1000 2000). Replaces defaults.",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="METRES",
        help="Maximum water depth (m) for the bathymetry colour scale. Example: --max-depth 1000",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
