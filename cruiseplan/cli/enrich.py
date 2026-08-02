"""
Configuration enrichment command.

This module implements the 'cruiseplan enrich' command for adding missing
data to existing YAML configuration files.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
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
    Thin CLI wrapper for enrich command.

    Delegates all business logic to the cruiseplan.enrich() API function.
    """
    verbose = getattr(args, "verbose", False)
    with handle_cli_errors("enrich", verbose):
        result = cruiseplan.enrich(
            config_file=args.config_file,
            output_dir=(
                str(args.output_dir)
                if hasattr(args, "output_dir") and args.output_dir
                else "data"
            ),
            output=getattr(args, "output", None),
            add_depths=getattr(args, "add_depths", False),
            add_coords=getattr(args, "add_coords", False),
            expand_sections=getattr(args, "expand_sections", False),
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=(
                str(args.bathy_dir)
                if hasattr(args, "bathy_dir") and args.bathy_dir
                else "data/bathymetry"
            ),
            verbose=verbose,
        )

        print(f"Configuration enriched successfully: {result}")


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the enrich subparser and return it."""
    p = subparsers.add_parser("enrich", help="Add missing data to configuration files")
    p.add_argument(
        "config_file",
        type=Path,
        metavar="CONFIG_FILE",
        help="Input YAML configuration file",
    )
    p.add_argument(
        "--add-depths",
        action="store_true",
        help="Add missing depth values to stations using bathymetry data",
    )
    p.add_argument(
        "--add-coords",
        action="store_true",
        help="Add formatted coordinate fields (DMM; DMS not yet implemented)",
    )
    p.add_argument(
        "--expand-sections",
        action="store_true",
        help="Expand CTD sections into individual station definitions",
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
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
