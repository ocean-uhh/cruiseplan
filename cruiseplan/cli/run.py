"""
Composite run command: process + schedule in one step.

This module implements the 'cruiseplan run' command, which chains
process (enrich + validate + map) and schedule, passing the enriched YAML
from process directly into schedule. Enrichment runs once.

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


def _print_file_list(label: str, files: list[Path]) -> None:
    """Print a labelled block of generated file paths."""
    print(f"\n{label}")
    print("-" * len(label))
    for f in files:
        print(f"  {f}")
    print(f"  {len(files)} file{'s' if len(files) != 1 else ''} written")


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for run command.

    Delegates all business logic to the cruiseplan.run() API function.
    """
    verbose = getattr(args, "verbose", False)
    with handle_cli_errors("run", verbose):
        config_file = args.config_file
        print(f"\nProcessing {config_file}")

        process_result, schedule_result = cruiseplan.run(
            config_file=config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            leg=getattr(args, "leg", None),
            bathy_source=getattr(args, "bathy_source", DEFAULT_BATHY_SOURCE),
            bathy_dir=getattr(args, "bathy_dir", DEFAULT_BATHY_DIR),
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

        if process_result.config is None:
            print("ERROR: Process step failed")
            sys.exit(1)

        _print_file_list(
            "Step 1/2  Enrich · validate · map", process_result.files_created
        )

        if schedule_result.timeline is None:
            print("\nERROR: Schedule step failed")
            sys.exit(1)

        _print_file_list("Step 2/2  Schedule", schedule_result.files_created)

        total = len(process_result.files_created) + len(schedule_result.files_created)
        output_dir = getattr(args, "output_dir", "data")
        print(f"\nRun complete — {total} files in {output_dir}/")


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the run subparser and return it."""
    p = subparsers.add_parser(
        "run",
        help="Full pipeline: enrich + validate + map + schedule in one step",
        description=(
            "Run the complete cruise planning pipeline. Enriches the YAML configuration, "
            "validates it, generates maps, then generates the cruise schedule — "
            "all in a single command. Enrichment runs once; the schedule uses the "
            "same enriched config as the maps."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cruiseplan run cruise.yaml
  cruiseplan run cruise.yaml -o results/ --eez
  cruiseplan run cruise.yaml --leg leg1 --bathy-source gebco2025
        """,
    )
    p.add_argument(
        "config_file",
        type=Path,
        metavar="CONFIG_FILE",
        help="YAML cruise configuration file",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for all generated files (default: data)",
    )
    p.add_argument(
        "--leg",
        help="Generate schedule for a specific leg only (default: all legs)",
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
        help="Bathymetry grid downsampling factor: 1 = full resolution, higher = faster (default: 10)",
    )
    p.add_argument(
        "--bathy-contours",
        type=float,
        nargs="+",
        metavar="DEPTH",
        help="Bathymetry contour depths in metres (e.g. --bathy-contours 200 500 1000 2000)",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="METRES",
        help="Maximum depth (m) for the bathymetry colour scale (e.g. --max-depth 1000)",
    )
    p.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds for map extent (e.g. --lat -75 -70)",
    )
    p.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for map extent (e.g. --lon 170 175)",
    )
    p.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=None,
        help="Figure size for PNG maps in inches (e.g. --figsize 14 10)",
    )
    p.add_argument(
        "--no-ports", action="store_true", help="Exclude ports from PNG maps"
    )
    p.add_argument("--no-title", action="store_true", help="Omit title from PNG maps")
    p.add_argument(
        "--no-labels", action="store_true", help="Omit station labels from PNG maps"
    )
    p.add_argument("--no-legend", action="store_true", help="Omit legend from PNG maps")
    p.add_argument(
        "--eez",
        action="store_true",
        default=False,
        help="Overlay EEZ boundaries on PNG maps (visualization only; data downloaded on first use)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
