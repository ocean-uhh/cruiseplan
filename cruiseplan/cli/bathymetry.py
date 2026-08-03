"""
Bathymetry data download command.

This module implements the 'cruiseplan bathymetry' command for downloading
bathymetry data assets required for cruise planning.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan
from cruiseplan.config.values import BATHY_SOURCES, DEFAULT_BATHY_SOURCE


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for bathymetry command.

    Delegates all business logic to the cruiseplan.bathymetry() API function.
    """
    from cruiseplan.cli import handle_cli_errors

    with handle_cli_errors("Download", args.verbose):
        result = cruiseplan.bathymetry(
            bathy_source=args.bathy_source,
            output_dir=str(args.output_dir) if args.output_dir is not None else None,
            citation=args.citation,
        )

        print("")
        print("=" * 50)
        print("Bathymetry Download Results")
        print("=" * 50)

        if result.data_file:
            print(result)
            print("Downloaded file:")
            print(f"  • {result.data_file}")

            print("Download summary:")
            print(f"  • Data source: {result.source}")
            print(f"  • Output directory: {result.summary.get('output_dir', 'N/A')}")
            if result.summary.get("file_size_mb"):
                print(f"  • File size: {result.summary.get('file_size_mb')} MB")

            if args.citation:
                print("")
                print("Citation information:")
                if result.source == "etopo2022":
                    print(
                        "  NOAA National Centers for Environmental Information. 2022."
                    )
                    print("  ETOPO 2022 15 Arc-Second Global Relief Model.")
                    print("  https://doi.org/10.25921/fd45-gt74")
                elif result.source == "gebco2025":
                    print("  GEBCO Compilation Group (2025) GEBCO 2025 Grid")
                    print(
                        "  https://doi.org/10.5285/c6612cbe-50b3-0cff-e053-6c86abc09f8f"
                    )
        else:
            print("Bathymetry download failed", file=sys.stderr)
            if "error" in result.summary:
                print(f"Error: {result.summary['error']}", file=sys.stderr)
            sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the bathymetry subparser and return it."""
    p = subparsers.add_parser(
        "bathymetry",
        help="Download bathymetry datasets for depth calculations",
        description="Download bathymetry datasets for cruise planning",
        epilog="""
This command downloads bathymetry datasets for depth calculations and bathymetric analysis.

Available sources:
  etopo2022: ETOPO 2022 bathymetry (60s resolution, ~500MB)
  gebco2025: GEBCO 2025 bathymetry (15s resolution, ~7.5GB)

Examples:
  cruiseplan bathymetry                                          # Download gebco2025 (default)
  cruiseplan bathymetry --bathy-source etopo2022                # Download ETOPO 2022
  cruiseplan bathymetry --bathy-source gebco2025 --citation     # Show citation info
        """,
    )
    p.add_argument(
        "--citation",
        action="store_true",
        help="Show citation information for the bathymetry source without downloading",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/bathymetry"),
        help="Output directory for bathymetry files (default: data/bathymetry)",
    )
    p.add_argument(
        "--bathy-source",
        choices=BATHY_SOURCES,
        default=DEFAULT_BATHY_SOURCE,
        help="Bathymetry dataset to download (default: gebco2025)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
