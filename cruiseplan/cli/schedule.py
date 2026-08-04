"""
Cruise schedule generation command.

This module implements the 'cruiseplan schedule' command for generating
comprehensive cruise schedules from YAML configuration files.

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
    Thin CLI wrapper for schedule command.

    Delegates all business logic to the cruiseplan.schedule() API function.
    """
    verbose = getattr(args, "verbose", False)
    with handle_cli_errors("schedule", verbose):
        derive_netcdf = getattr(args, "derive_netcdf", False)
        format_list = getattr(args, "format", None)
        format_str = ",".join(format_list) if format_list else "all"
        if derive_netcdf and format_list and "netcdf" not in format_list:
            print(
                "WARNING: --derive-netcdf requires netcdf output format",
                file=sys.stderr,
            )
            print(
                "  Either add 'netcdf' to --format (e.g., --format netcdf html)"
                " or omit --format to generate all formats.",
                file=sys.stderr,
            )
            print("  Ignoring --derive-netcdf flag.", file=sys.stderr)
            derive_netcdf = False

        result = cruiseplan.schedule(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            format=format_str,
            leg=getattr(args, "leg", None),
            derive_netcdf=derive_netcdf,
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            bathy_stride=getattr(args, "bathy_stride", 10),
            bathy_contours=getattr(args, "bathy_contours", None),
            lat_bounds=getattr(args, "lat", None),
            lon_bounds=getattr(args, "lon", None),
            figsize=getattr(args, "figsize", None),
            no_ports=getattr(args, "no_ports", False),
            no_title=getattr(args, "no_title", False),
            no_labels=getattr(args, "no_labels", False),
            no_legend=getattr(args, "no_legend", False),
            verbose=verbose,
            max_depth=getattr(args, "max_depth", None),
            include_eez=getattr(args, "eez", False),
        )

        print("")
        print("=" * 50)
        print("Schedule Generation Results")
        print("=" * 50)

        if result.timeline:
            print(result)
            print("Generated files:")
            for file_path in result.files_created:
                print(f"  • {file_path}")

            total_duration_hours = (
                sum(activity.get("duration_minutes", 0) for activity in result.timeline)
                / 60.0
            )
            print(f"Total timeline duration: {total_duration_hours:.1f} hours")
            print(f"Timeline activities: {len(result.timeline)}")
        else:
            print("Schedule generation failed")
            sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the schedule subparser and return it."""
    p = subparsers.add_parser(
        "schedule", help="Generate cruise schedule from YAML configuration"
    )
    p.add_argument(
        "config_file",
        type=Path,
        metavar="CONFIG_FILE",
        help="YAML cruise configuration file",
    )
    p.add_argument("--leg", help="Process specific leg only")
    p.add_argument(
        "--derive-netcdf",
        action="store_true",
        help="Generate specialised NetCDF files (_points.nc, _lines.nc, _areas.nc) in addition to master schedule",
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
        help="Base filename for outputs (default: use cruise name from config)",
    )
    p.add_argument(
        "--format",
        nargs="+",
        choices=["html", "latex", "csv", "netcdf", "png"],
        default=None,
        metavar="FORMAT",
        help="Output formats: html latex csv netcdf png (space-separated). Omit to generate all.",
    )
    p.add_argument(
        "--bathy-source",
        choices=BATHY_SOURCES,
        default=DEFAULT_BATHY_SOURCE,
        help="Bathymetry dataset for PNG maps (default: gebco2025)",
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
        default=10,
        help="Bathymetry grid downsampling factor: 1 = full resolution, higher = faster but less detail (default: 10)",
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
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[10, 8.1],
        help="Figure size for PNG maps in inches (default: 10 8.1)",
    )
    p.add_argument(
        "--no-ports",
        action="store_true",
        help="Exclude ports from PNG schedule maps",
    )
    p.add_argument(
        "--no-title",
        action="store_true",
        help="Omit title from PNG schedule maps",
    )
    p.add_argument(
        "--no-labels",
        action="store_true",
        help="Omit station name labels from PNG schedule maps",
    )
    p.add_argument(
        "--no-legend",
        action="store_true",
        help="Omit legend from PNG schedule maps",
    )
    p.add_argument(
        "--eez",
        action="store_true",
        default=False,
        help="Overlay EEZ boundaries on PNG schedule maps (visualization only; data downloaded on first use)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
