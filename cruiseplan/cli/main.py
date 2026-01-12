"""
cruiseplan CLI - Modern subcommand architecture for oceanographic cruise planning.

This module provides the main command-line interface for the cruiseplan system,
implementing a git-style subcommand pattern with various operations for cruise
planning, data processing, and output generation.
"""

import argparse
import sys
from pathlib import Path

try:
    from cruiseplan._version import __version__
except ImportError:
    __version__ = "unknown"


# Define placeholder main functions for dynamic imports
# (These will be overwritten when the modules are implemented)
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
  cruiseplan bathymetry --source gebco2025
  cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -30
  cruiseplan stations --lat 50 65 --lon -60 -30
  cruiseplan enrich -c cruise.yaml --add-depths --add-coords
  cruiseplan validate -c cruise.yaml --check-depths
  cruiseplan schedule -c cruise.yaml -o results/
  cruiseplan map -c cruise.yaml --figsize 14 10

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

    # --- 1. Bathymetry Subcommand ---
    bathymetry_parser = subparsers.add_parser(
        "bathymetry",
        help="Download bathymetry datasets for depth calculations",
        description="Download bathymetry datasets for cruise planning",
        epilog="""
This command downloads bathymetry datasets for depth calculations and bathymetric analysis.

Available sources:
  etopo2022: ETOPO 2022 bathymetry (60s resolution, ~500MB)
  gebco2025: GEBCO 2025 bathymetry (15s resolution, ~7.5GB)

Examples:
  cruiseplan bathymetry                                          # Download ETOPO 2022 (default)
  cruiseplan bathymetry --bathy-source etopo2022                # Download ETOPO 2022 explicitly
  cruiseplan bathymetry --bathy-source gebco2025                # Download high-res GEBCO 2025
  cruiseplan bathymetry --bathy-source etopo2022 --citation     # Show citation info only
        """,
    )
    # Primary operation flags
    bathymetry_parser.add_argument(
        "--citation",
        action="store_true",
        help="Show citation information for the bathymetry source without downloading",
    )

    # Output control
    bathymetry_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data/bathymetry"),
        help="Output directory for bathymetry files (default: data/bathymetry)",
    )

    # Bathymetry options
    bathymetry_parser.add_argument(
        "--bathy-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset to download (default: etopo2022)",
    )

    # --- 2. Schedule Subcommand ---
    schedule_parser = subparsers.add_parser(
        "schedule", help="Generate cruise schedule from YAML configuration"
    )
    # Required arguments
    schedule_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="YAML cruise configuration file",
    )

    # Primary operation flags
    schedule_parser.add_argument("--leg", help="Process specific leg only")
    schedule_parser.add_argument(
        "--derive-netcdf",
        action="store_true",
        help="Generate specialized NetCDF files (_points.nc, _lines.nc, _areas.nc) in addition to master schedule",
    )

    # Output control
    schedule_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    schedule_parser.add_argument(
        "--output",
        type=str,
        help="Base filename for outputs (default: use cruise name from config)",
    )
    schedule_parser.add_argument(
        "--format",
        choices=["html", "latex", "csv", "netcdf", "png", "all"],
        default="all",
        help="Output formats (default: all)",
    )

    # Bathymetry options
    schedule_parser.add_argument(
        "--bathy-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset for PNG maps (default: etopo2022)",
    )
    schedule_parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    schedule_parser.add_argument(
        "--bathy-stride",
        type=int,
        default=10,
        help="Bathymetry contour stride for PNG maps (default: 10)",
    )

    # Display options
    schedule_parser.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[12.0, 8.0],
        help="Figure size for PNG maps in inches (default: 12 8)",
    )

    # --- 3. Stations Subcommand ---
    stations_parser = subparsers.add_parser(
        "stations", help="Interactive station placement with PANGAEA background"
    )
    # Primary operation flags
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
        "--overwrite",
        action="store_true",
        help="Overwrite existing output file without prompting",
    )

    # Output control
    stations_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )

    # Bathymetry options
    stations_parser.add_argument(
        "--bathy-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )
    stations_parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )

    # Display options
    stations_parser.add_argument(
        "--high-resolution",
        action="store_true",
        help="Use full resolution bathymetry (slower but more detailed)",
    )

    # --- 4. Enrich Subcommand ---
    enrich_parser = subparsers.add_parser(
        "enrich", help="Add missing data to configuration files"
    )
    # Required arguments
    enrich_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="Input YAML configuration file",
    )

    # Primary operation flags
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
        "--expand-sections",
        action="store_true",
        help="Expand CTD sections into individual station definitions",
    )

    # Output control
    enrich_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )

    # Bathymetry options
    enrich_parser.add_argument(
        "--bathy-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )
    enrich_parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )

    # General options
    enrich_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # --- 5. Validate Subcommand ---
    validate_parser = subparsers.add_parser(
        "validate", help="Validate configuration files (read-only)"
    )
    # Required arguments
    validate_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="Input YAML configuration file",
    )

    # Primary operation flags
    validate_parser.add_argument(
        "--check-depths",
        action="store_true",
        help="Compare existing depths with bathymetry data",
    )
    validate_parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference tolerance in percent (default: 10.0)",
    )

    # Bathymetry options
    validate_parser.add_argument(
        "--bathy-source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry dataset (default: etopo2022)",
    )
    validate_parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )

    # General options
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
  cruiseplan map -c cruise.yaml                              # Generate map with default settings
  cruiseplan map -c cruise.yaml -o maps/ --figsize 14 10     # Custom output dir and size
  cruiseplan map -c cruise.yaml --bathy-source gebco2025     # High-resolution bathymetry
  cruiseplan map -c cruise.yaml --output cruise_track        # Custom base filename
        """,
    )
    # Required arguments
    map_parser.add_argument(
        "-c",
        "--config-file",
        required=True,
        type=Path,
        help="YAML cruise configuration file",
    )

    # Primary operation flags
    map_parser.add_argument(
        "--no-ports",
        action="store_true",
        help="Suppress plotting of departure and arrival ports in both PNG and KML outputs",
    )

    # Output control
    map_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    map_parser.add_argument(
        "--output",
        type=str,
        help="Base filename for output maps (default: use config filename)",
    )
    map_parser.add_argument(
        "--format",
        choices=["png", "kml", "all"],
        default="all",
        help="Output format: png (map), kml (geographic data), or all (default: all)",
    )

    # Bathymetry options
    map_parser.add_argument(
        "--bathy-source",
        choices=["etopo2022", "gebco2025"],
        default="gebco2025",
        help="Bathymetry dataset (default: gebco2025)",
    )
    map_parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    map_parser.add_argument(
        "--bathy-stride",
        type=int,
        default=5,
        help="Bathymetry downsampling factor (default: 5, higher=faster/less detailed)",
    )

    # Display options
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

    # General options
    map_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # --- 8. Process Subcommand (Unified Configuration Processing) ---
    process_parser = subparsers.add_parser(
        "process",
        help="Unified configuration processing (enrich + validate + map)",
        description="Unified interface for complete configuration processing pipeline",
        epilog="""
This command provides a unified interface for the complete configuration processing pipeline,
combining enrichment (adding missing data), validation (checking configuration integrity),
and map generation into a single command with smart defaults and flexible control.

Key Features:
- Smart defaults: All enrichment options enabled by default
- Flexible execution: Control which steps run with --only-* and --no-* flags
- Consistent output naming: Use --output for base filename across all generated files
- Modern parameter names: Shorter --bathy-* parameters for reduced typing

Examples:
  cruiseplan process -c cruise.yaml                                    # Full processing with smart defaults
  cruiseplan process -c cruise.yaml --output expedition_2024          # With custom base filename
  cruiseplan process -c cruise.yaml --only-enrich --no-sections       # Only enrichment, skip CTD sections
  cruiseplan process -c cruise.yaml --only-validate --tolerance 5.0   # Only validation with custom tolerance
  cruiseplan process -c cruise.yaml --only-map --format png           # Only map generation, PNG only
  cruiseplan process -c cruise.yaml --no-map --strict                 # Skip maps, strict validation
        """,
    )
    # Required arguments
    process_parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        required=True,
        help="Input YAML configuration file",
    )

    # Primary operation flags
    # Processing mode flags (mutually exclusive --only-* modes)
    process_parser.add_argument(
        "--only-enrich", action="store_true", help="Only run enrichment step"
    )
    process_parser.add_argument(
        "--only-validate",
        action="store_true",
        help="Only run validation step (no enrichment or map)",
    )
    process_parser.add_argument(
        "--only-map",
        action="store_true",
        help="Only run map generation (no enrichment or validation)",
    )

    # Processing step control flags (for full processing mode)
    process_parser.add_argument(
        "--no-enrich", action="store_true", help="Skip enrichment step"
    )
    process_parser.add_argument(
        "--no-validate", action="store_true", help="Skip validation step"
    )
    process_parser.add_argument(
        "--no-map", action="store_true", help="Skip map generation step"
    )

    # Enrichment control flags (smart defaults - all enabled unless disabled)
    process_parser.add_argument(
        "--no-depths",
        action="store_true",
        help="Skip adding missing depths (default: depths added)",
    )
    process_parser.add_argument(
        "--no-coords",
        action="store_true",
        help="Skip adding coordinate fields (default: coords added)",
    )
    process_parser.add_argument(
        "--no-sections",
        action="store_true",
        help="Skip expanding CTD sections (default: sections expanded)",
    )
    process_parser.add_argument(
        "--no-ports",
        action="store_true",
        help="Skip expanding port references (default: ports expanded)",
    )

    # Validation options
    process_parser.add_argument(
        "--no-depth-check",
        action="store_true",
        help="Skip depth accuracy checking (default: depths checked)",
    )
    process_parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference tolerance in percent (default: 10.0)",
    )

    # Output control
    process_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    process_parser.add_argument(
        "--output", type=str, help="Base filename for outputs (without extension)"
    )
    process_parser.add_argument(
        "--format", default="all", help="Map output formats: png,kml,all (default: all)"
    )

    # Bathymetry options
    process_parser.add_argument(
        "--bathy-source",
        default="etopo2022",
        choices=["etopo2022", "gebco2025"],
        help="Bathymetry dataset (default: etopo2022)",
    )
    process_parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    process_parser.add_argument(
        "--bathy-stride",
        type=int,
        default=10,
        help="Bathymetry contour stride (default: 10)",
    )

    # Display options
    process_parser.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        default=[12, 8],
        help="Figure size for PNG maps (width height, default: 12 8)",
    )
    process_parser.add_argument(
        "--no-port-map",
        action="store_true",
        help="Skip plotting ports on generated maps (default: ports plotted)",
    )

    # General options
    process_parser.add_argument(
        "--strict", action="store_true", help="Enable strict validation mode"
    )
    process_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    process_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Enable quiet mode"
    )

    # --- 9. Pangaea Subcommand (Unified Search + Download) ---
    pangaea_parser = subparsers.add_parser(
        "pangaea",
        help="Search and download PANGAEA datasets, or process existing DOI lists",
        description="Unified PANGAEA data processor - search by query + geographic bounds OR process existing DOI files",
        epilog="""
This command combines PANGAEA dataset search and download functionality:

SEARCH + DOWNLOAD MODE (requires --lat and --lon):
  cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -30 --output atlantic_study
  → Generates: atlantic_study_dois.txt + atlantic_study_stations.pkl

DOI FILE MODE (provide existing .txt file):
  cruiseplan pangaea arctic_dois.txt --output arctic_analysis
  → Generates: arctic_analysis_stations.pkl

Output Strategy:
  --output: Base filename (without extension) for generated files
  --output-dir: Directory where files are saved (default: data/)

Examples:
  cruiseplan pangaea "CTD Arctic Ocean" --lat 70 85 --lon -180 -120 --limit 50
  cruiseplan pangaea my_dois.txt --rate-limit 0.5 --merge-campaigns
  cruiseplan pangaea "salinity North Atlantic" --lat 40 65 --lon -70 -10 --output north_atlantic
        """,
    )
    pangaea_parser.add_argument(
        "query_or_file",
        help="Search query string (for search mode) or DOI file path (for file mode)",
    )
    pangaea_parser.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds for search mode (e.g., --lat 50 70)",
    )
    pangaea_parser.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for search mode (e.g., --lon -60 -30)",
    )
    pangaea_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum search results to return (default: 10, max recommended: 100)",
    )
    pangaea_parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    pangaea_parser.add_argument(
        "--output",
        help="Base filename for outputs (without extension or directory)",
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
        default=True,
        help="Merge campaigns with the same name (default: true)",
    )
    pangaea_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
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
        if args.subcommand == "bathymetry":
            from cruiseplan.cli.bathymetry import main as bathymetry_main

            bathymetry_main(args)
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
        elif args.subcommand == "process":
            from cruiseplan.cli.process import main as process_main

            process_main(args)
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
