"""
cruiseplan CLI - Modern subcommand architecture for oceanographic cruise planning.

This module provides the main command-line interface for the cruiseplan system,
implementing a git-style subcommand pattern with various operations for cruise
planning, data processing, and output generation.
"""

import argparse
import sys
from pathlib import Path
from typing import Any  # Added Any for generic type hinting

try:
    from cruiseplan._version import __version__
except ImportError:
    __version__ = "unknown"


# Define placeholder main functions for dynamic imports
# (These will be overwritten when the modules are implemented)
def download_main(args: Any):
    """
    Placeholder for download subcommand logic.

    Parameters
    ----------
    args : Any
        Parsed command-line arguments.
    """
    print("Download logic will be implemented in cruiseplan.cli.download")


def schedule_main(args: argparse.Namespace):
    """
    Placeholder for schedule subcommand logic.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing config_file and output_dir.
    """
    print(
        f"Schedule logic will process config: {args.config_file} and output to {args.output_dir}"
    )


def stations_main(args: argparse.Namespace):
    """
    Placeholder for stations subcommand logic.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing lat, lon bounds.
    """
    print(f"Stations logic will process bounds: {args.lat}, {args.lon}")


def enrich_main(args: argparse.Namespace):
    """
    Placeholder for enrich logic.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing config_file.
    """
    print(f"Enrich logic for config: {args.config_file}")


def validate_main(args: argparse.Namespace):
    """
    Placeholder for validate logic.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing config_file.
    """
    print(f"Validate logic for config: {args.config_file}")


def pangaea_main(args: argparse.Namespace):
    """
    Placeholder for PANGAEA data processing logic.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing doi_file.
    """
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
  cruiseplan map -c cruise.yaml --figsize 14 10
  cruiseplan stations --lat 50 65 --lon -60 -30
  cruiseplan enrich -c cruise.yaml --add-depths --add-coords
  cruiseplan validate -c cruise.yaml --check-depths
  cruiseplan pandoi "CTD" --lat 50 60 --lon -50 -40 --limit 20
  cruiseplan pangaea doi_list.txt

For detailed help on a subcommand:
  cruiseplan <subcommand> --help
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="Available commands",
        description="Choose a subcommand to run",
        help="Available subcommands",
    )

    # --- 1. Download Subcommand ---
    download_parser = subparsers.add_parser(
        "download",
        help="Download required data assets (bathymetry, etc.)",
        description="Download bathymetry datasets for cruise planning",
        epilog="""
This command downloads bathymetry datasets for depth calculations and bathymetric analysis.

Available sources:
  etopo2022: ETOPO 2022 bathymetry (60s resolution, ~500MB)
  gebco2025: GEBCO 2025 bathymetry (15s resolution, ~7.5GB)

Examples:
  cruiseplan download                                    # Download ETOPO 2022 (default)
  cruiseplan download --bathymetry-source etopo2022     # Download ETOPO 2022 explicitly  
  cruiseplan download --bathymetry-source gebco2025     # Download high-res GEBCO 2025
  cruiseplan download --bathymetry-source etopo2022 --citation  # Show citation info only
        """,
    )
    download_parser.add_argument(
        "--bathymetry-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset to download (default: etopo2022)",
    )
    download_parser.add_argument(
        "--citation",
        action="store_true",
        help="Show citation information for the bathymetry source without downloading",
    )
    download_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/bathymetry"),
        help="Output directory for bathymetry files (default: data/bathymetry)",
    )

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
        default=Path("data"),
        help="Output directory (default: data)",
    )
    schedule_parser.add_argument(
        "--format",
        choices=["html", "latex", "csv", "netcdf", "png", "all"],
        default="all",
        help="Output formats (default: all)",
    )
    schedule_parser.add_argument("--leg", help="Process specific leg only")
    schedule_parser.add_argument(
        "--derive-netcdf",
        action="store_true",
        help="Generate specialized NetCDF files (_points.nc, _lines.nc, _areas.nc) in addition to master schedule",
    )

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
        default=Path("data"),
        help="Output directory (default: data)",
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
    stations_parser.add_argument(
        "--bathymetry-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    stations_parser.add_argument(
        "--high-resolution",
        action="store_true",
        help="Use full resolution bathymetry (slower but more detailed)",
    )
    stations_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file without prompting",
    )

    # --- 4. Enrich Subcommand ---
    enrich_parser = subparsers.add_parser(
        "enrich", help="Add missing data to configuration files"
    )
    enrich_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="Input YAML configuration file",
    )
    enrich_parser.add_argument(
        "--add-depths",
        action="store_true",
        help="Add missing depth values to stations using bathymetry data",
    )
    enrich_parser.add_argument(
        "--add-coords",
        action="store_true",
        help="Add formatted coordinate fields (DMM; DMS not yet implemented)",
    )
    enrich_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    enrich_parser.add_argument(
        "--output-file",
        type=Path,
        help="Specific output file path",
    )
    enrich_parser.add_argument(
        "--bathymetry-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )
    enrich_parser.add_argument(
        "--bathymetry-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    enrich_parser.add_argument(
        "--coord-format",
        choices=["dmm", "dms"],
        default="dmm",
        help="Coordinate format (default: dmm)",
    )
    enrich_parser.add_argument(
        "--expand-sections",
        action="store_true",
        help="Expand CTD sections into individual station definitions",
    )
    enrich_parser.add_argument(
        "--expand-ports", action="store_true", help="Expand global port references"
    )
    enrich_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # --- 5. Validate Subcommand ---
    validate_parser = subparsers.add_parser(
        "validate", help="Validate configuration files (read-only)"
    )
    validate_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="Input YAML configuration file",
    )
    validate_parser.add_argument(
        "--check-depths",
        action="store_true",
        help="Compare existing depths with bathymetry data",
    )
    validate_parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )
    validate_parser.add_argument(
        "--warnings-only",
        action="store_true",
        help="Show warnings without failing",
    )
    validate_parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference tolerance in percent (default: 10.0)",
    )
    validate_parser.add_argument(
        "--bathymetry-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )
    validate_parser.add_argument(
        "--bathymetry-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )

    # --- 6. PANDOI Subcommand ---
    pandoi_parser = subparsers.add_parser(
        "pandoi", help="Search PANGAEA datasets by query and geographic bounds"
    )
    pandoi_parser.add_argument(
        "query", help="Search query string (e.g., 'CTD', 'temperature', 'Arctic Ocean')"
    )
    pandoi_parser.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds (e.g., --lat 50 70)",
    )
    pandoi_parser.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds (e.g., --lon -60 -30)",
    )
    pandoi_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of results to return (default: 10)",
    )
    pandoi_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    pandoi_parser.add_argument(
        "--output-file",
        type=Path,
        help="Specific output file path (overrides -o/--output-dir)",
    )
    pandoi_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # --- 7. Map Subcommand ---
    map_parser = subparsers.add_parser(
        "map",
        help="Generate PNG maps and KML geographic data from YAML configuration",
        description="Create static PNG maps and/or KML files from cruise configuration catalog",
        epilog="""
This command generates PNG maps and/or KML geographic data from cruise configuration.
PNG maps show stations, cruise tracks, ports, and bathymetric background.
KML files contain geographic data for Google Earth viewing of all catalog entities.

Examples:
  cruiseplan map -c cruise.yaml                                # Generate map with default settings
  cruiseplan map -c cruise.yaml -o maps/ --figsize 14 10      # Custom output dir and size  
  cruiseplan map -c cruise.yaml --bathymetry-source gebco2025 # High-resolution bathymetry
  cruiseplan map -c cruise.yaml --output-file track_map.png   # Specific output file
        """,
    )
    map_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="YAML cruise configuration file",
    )
    map_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    map_parser.add_argument(
        "--output-file",
        type=Path,
        help="Specific output file path (overrides auto-generated name)",
    )
    map_parser.add_argument(
        "--format",
        choices=["png", "kml", "all"],
        default="all",
        help="Output format: png (map), kml (geographic data), or all (default: all)",
    )
    map_parser.add_argument(
        "--bathymetry-source",
        choices=["etopo2022", "gebco2025"],
        default="gebco2025",
        help="Bathymetry dataset (default: gebco2025)",
    )
    map_parser.add_argument(
        "--bathymetry-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    map_parser.add_argument(
        "--bathymetry-stride",
        type=int,
        default=5,
        help="Bathymetry downsampling factor (default: 5, higher=faster/less detailed)",
    )
    map_parser.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[12, 10],
        help="Figure size in inches (default: 12 10)",
    )
    map_parser.add_argument(
        "--show-plot",
        action="store_true",
        help="Display plot interactively instead of saving to file",
    )
    map_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # --- 8. Pangaea Subcommand ---
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
        elif args.subcommand == "enrich":
            from cruiseplan.cli.enrich import main as enrich_main

            enrich_main(args)
        elif args.subcommand == "validate":
            from cruiseplan.cli.validate import main as validate_main

            validate_main(args)
        elif args.subcommand == "pandoi":
            from cruiseplan.cli.pandoi import main as pandoi_main

            pandoi_main(args)
        elif args.subcommand == "map":
            from cruiseplan.cli.map import main as map_main

            map_main(args)
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
