#!/usr/bin/env python3
"""
cruiseplan CLI - Modern subcommand architecture for oceanographic cruise planning.
"""

import argparse
import sys
from pathlib import Path
from typing import Any  # Added Any for generic type hinting


# Define placeholder main functions for dynamic imports
# (These will be overwritten when the modules are implemented)
def download_main(args: Any):
    """Placeholder for download subcommand logic."""
    print("Download logic will be implemented in cruiseplan.cli.download")


def schedule_main(args: argparse.Namespace):
    """Placeholder for schedule subcommand logic."""
    print(
        f"Schedule logic will process config: {args.config_file} and output to {args.output_dir}"
    )


def stations_main(args: argparse.Namespace):
    """Placeholder for stations subcommand logic."""
    print(f"Stations logic will process bounds: {args.lat}, {args.lon}")


def depths_main(args: argparse.Namespace):
    """Placeholder for depth validation logic."""
    print(f"Depth validation logic for config: {args.config_file}")


def pangaea_main(args: argparse.Namespace):
    """Placeholder for PANGAEA data processing logic."""
    print(f"PANGAEA logic for DOI file: {args.doi_file}")


def main():
    """Main CLI entry point following git-style subcommand pattern."""
    parser = argparse.ArgumentParser(
        prog="cruiseplan",
        description="Oceanographic Cruise Planning System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cruiseplan schedule -c cruise.yaml -o results/
  cruiseplan stations --lat 50 65 --lon -60 -30
  cruiseplan depths cruise.yaml --tolerance 15
  cruiseplan pangaea doi_list.txt -o pangaea_data/

For detailed help on a subcommand:
  cruiseplan <subcommand> --help
        """,
    )

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="Available commands",
        description="Choose a subcommand to run",
        help="Available subcommands",
    )

    # --- 1. Download Subcommand ---
    download_parser = subparsers.add_parser(
        "download", help="Download required data assets (bathymetry, etc.)"
    )
    # The download command is simple and has no arguments for now, but will eventually take a source.

    # --- 2. Schedule Subcommand ---
    schedule_parser = subparsers.add_parser(
        "schedule", help="Generate cruise schedule from YAML configuration"
    )
    schedule_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="YAML cruise configuration file",
    )
    schedule_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory (default: current)",
    )
    schedule_parser.add_argument(
        "--format",
        choices=["html", "latex", "csv", "kml", "netcdf", "all"],
        default="all",
        help="Output formats (default: all)",
    )
    schedule_parser.add_argument(
        "--validate-depths",
        action="store_true",
        help="Compare stated depths with bathymetry",
    )
    schedule_parser.add_argument("--leg", help="Process specific leg only")

    # --- 3. Stations Subcommand ---
    stations_parser = subparsers.add_parser(
        "stations", help="Interactive station placement with PANGAEA background"
    )
    stations_parser.add_argument(
        "-p", "--pangaea-file", type=Path, help="PANGAEA campaigns pickle file"
    )
    stations_parser.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=(45, 70),  # Adding a default based on spec examples
        help="Latitude bounds (default: 45 70)",
    )
    stations_parser.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=(-65, -5),  # Adding a default based on spec examples
        help="Longitude bounds (default: -65 -5)",
    )
    stations_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory (default: current)",
    )
    stations_parser.add_argument(
        "--output-file", type=Path, help="Specific output file path"
    )
    stations_parser.add_argument(
        "--bathymetry-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )

    # --- 4. Depths Subcommand (NEW) ---
    depths_parser = subparsers.add_parser(
        "depths", help="Validate and add bathymetry depths to configuration"
    )
    depths_parser.add_argument(
        "config_file",
        type=Path,
        help="Input YAML file with station positions",
    )
    depths_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory (default: current)",
    )
    depths_parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference warning threshold in percent (default: 10.0)",
    )
    depths_parser.add_argument(
        "--source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )
    depths_parser.add_argument(
        "--add-missing",
        action="store_true",
        help="Add depth for stations without depth values in the YAML",
    )
    depths_parser.add_argument(
        "--warnings-only",
        action="store_true",
        help="Only show warnings, don't modify the output file",
    )
    depths_parser.add_argument(
        "--output-file",
        type=Path,
        help="Specific output file path",
    )

    # --- 5. Pangaea Subcommand (NEW) ---
    pangaea_parser = subparsers.add_parser(
        "pangaea", help="Process PANGAEA DOI lists into campaign datasets"
    )
    pangaea_parser.add_argument(
        "doi_file",
        type=Path,
        help="Text file with PANGAEA DOIs (one per line)",
    )
    pangaea_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/"),
        help="Output directory (default: data/)",
    )
    pangaea_parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="API request rate limit (requests per second, default: 1.0)",
    )
    pangaea_parser.add_argument(
        "--merge-campaigns",
        action="store_true",
        help="Merge campaigns with the same name (Default: true in logic)",
    )
    pangaea_parser.add_argument(
        "--output-file",
        type=Path,
        help="Specific pickle output file path",
    )

    # Parse args
    args = parser.parse_args()

    # Handle case where no subcommand is given
    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    # Dispatch to appropriate function
    try:
        # We use dynamic imports here to minimize startup time and only import the
        # necessary module (e.g., cruiseplan.cli.schedule) when its command is run.
        if args.subcommand == "download":
            from cruiseplan.cli.download import main as download_main

            download_main(args)
        elif args.subcommand == "schedule":
            from cruiseplan.cli.schedule import main as schedule_main

            schedule_main(args)
        elif args.subcommand == "stations":
            from cruiseplan.cli.stations import main as stations_main

            stations_main(args)
        elif args.subcommand == "depths":
            from cruiseplan.cli.depths import main as depths_main

            depths_main(args)
        elif args.subcommand == "pangaea":
            from cruiseplan.cli.pangaea import main as pangaea_main

            pangaea_main(args)
        else:
            print(f"Subcommand '{args.subcommand}' not yet implemented.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        # A simple catch-all for unexpected errors
        print(f"\n❌ A critical error occurred during execution: {e}")
        # Optionally print traceback if debugging is enabled
        # import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
