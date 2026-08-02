"""
Unified configuration processing command.

This module implements the 'cruiseplan process' command that runs the complete
workflow: enrichment -> validation -> map generation.

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
    Thin CLI wrapper for process command.

    Delegates all business logic to the cruiseplan.process() API function.
    """
    verbose = getattr(args, "verbose", False)
    with handle_cli_errors("process", verbose):
        format_list = getattr(args, "format", None)
        format_str = ",".join(format_list) if format_list else "all"
        result = cruiseplan.process(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            add_depths=not (
                getattr(args, "no_enrich", False) or getattr(args, "no_depths", False)
            ),
            add_coords=not (
                getattr(args, "no_enrich", False) or getattr(args, "no_coords", False)
            ),
            expand_sections=not (
                getattr(args, "no_enrich", False) or getattr(args, "no_sections", False)
            ),
            run_validation=not getattr(args, "no_validate", False),
            run_map_generation=not getattr(args, "no_map", False),
            depth_check=not getattr(args, "no_depth_check", False),
            tolerance=getattr(args, "tolerance", 10.0),
            format=format_str,
            bathy_stride=getattr(args, "bathy_stride", 10),
            bathy_contours=getattr(args, "bathy_contours", None),
            lat_bounds=getattr(args, "lat", None),
            lon_bounds=getattr(args, "lon", None),
            figsize=getattr(args, "figsize", None),
            no_ports=getattr(args, "no_ports", False),
            no_title=getattr(args, "no_title", False),
            no_labels=getattr(args, "no_labels", False),
            no_legend=getattr(args, "no_legend", False),
            verbose=getattr(args, "verbose", False),
            max_depth=getattr(args, "max_depth", None),
        )

        print("")
        print("=" * 50)
        print("Processing Results")
        print("=" * 50)

        if result.config:
            print(result)
            print("Generated files:")
            for file_path in result.files_created:
                print(f"  • {file_path}")

            print("Processing summary:")
            print(f"  • Config file: {result.summary.get('config_file', 'N/A')}")
            print(f"  • Files generated: {result.summary.get('files_generated', 0)}")
            if result.summary.get("enrichment_run"):
                print("  - Enrichment completed")
            if result.summary.get("validation_run"):
                print("  - Validation completed")
            if result.summary.get("map_generation_run"):
                print("  - Map generation completed")
        else:
            print("Processing failed")
            sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the process subparser and return it."""
    p = subparsers.add_parser(
        "process",
        help="Unified configuration processing (enrich + validate + map)",
        description="Unified interface for complete configuration processing pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This command provides a unified interface for the complete configuration
processing pipeline, combining enrichment (adding missing data), validation
(checking configuration integrity), and map generation into a single command
with smart defaults and flexible control.

Examples:
  cruiseplan process cruise.yaml                             # Full processing
  cruiseplan process cruise.yaml --output expedition_2024   # Custom filename
  cruiseplan process cruise.yaml --no-map                   # Skip map generation
  cruiseplan process cruise.yaml --no-validate              # Skip validation
  cruiseplan enrich   cruise.yaml                           # Enrichment only
  cruiseplan validate cruise.yaml                           # Validation only
  cruiseplan map      cruise.yaml --format png              # Map only
        """,
    )
    p.add_argument(
        "config_file",
        type=Path,
        metavar="CONFIG_FILE",
        help="Input YAML configuration file",
    )
    p.add_argument("--no-enrich", action="store_true", help="Skip enrichment step")
    p.add_argument("--no-validate", action="store_true", help="Skip validation step")
    p.add_argument("--no-map", action="store_true", help="Skip map generation step")
    p.add_argument(
        "--no-depths",
        action="store_true",
        help="Skip adding missing depths (default: depths added)",
    )
    p.add_argument(
        "--no-coords",
        action="store_true",
        help="Skip adding coordinate fields (default: coords added)",
    )
    p.add_argument(
        "--no-sections",
        action="store_true",
        help="Skip expanding CTD sections (default: sections expanded)",
    )
    p.add_argument(
        "--no-depth-check",
        action="store_true",
        help="Skip depth accuracy checking (default: depths checked)",
    )
    p.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference tolerance in percent (default: 10.0)",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    p.add_argument(
        "--output", type=str, help="Base filename for outputs (without extension)"
    )
    p.add_argument(
        "--format",
        nargs="+",
        choices=["png", "kml"],
        default=None,
        metavar="FORMAT",
        help="Map output formats: png kml (space-separated). Omit to generate all.",
    )
    p.add_argument(
        "--bathy-source",
        default=DEFAULT_BATHY_SOURCE,
        choices=BATHY_SOURCES,
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
        help="Figure size for PNG maps (width height, default: 10 8.1)",
    )
    p.add_argument(
        "--no-ports",
        action="store_true",
        help="Exclude ports from generated maps (default: ports plotted)",
    )
    p.add_argument(
        "--no-title",
        action="store_true",
        help="Omit title from generated PNG maps",
    )
    p.add_argument(
        "--no-labels",
        action="store_true",
        help="Omit station name labels from generated PNG maps",
    )
    p.add_argument(
        "--no-legend",
        action="store_true",
        help="Omit legend from generated PNG maps",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    p.add_argument("--quiet", "-q", action="store_true", help="Enable quiet mode")
    return p
