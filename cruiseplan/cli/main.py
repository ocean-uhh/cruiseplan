"""
cruiseplan CLI - Subcommand dispatcher for oceanographic cruise planning.

Each subcommand is defined in its own module (e.g. cruiseplan/cli/schedule.py)
via a build_parser(subparsers) function. This module wires them together and
dispatches to the appropriate run(args) function.
"""

import argparse
import importlib
import sys

try:
    from cruiseplan._version import __version__
except ImportError:
    __version__ = "unknown"

_SUBCOMMAND_MODULES = {
    "bathymetry": "cruiseplan.cli.bathymetry",
    "run": "cruiseplan.cli.run",
    "schedule": "cruiseplan.cli.schedule",
    "stations": "cruiseplan.cli.stations",
    "enrich": "cruiseplan.cli.enrich",
    "validate": "cruiseplan.cli.validate",
    "process": "cruiseplan.cli.process",
    "map": "cruiseplan.cli.map",
    "pangaea": "cruiseplan.cli.pangaea",
    "forecast": "cruiseplan.cli.forecast",
    "list": "cruiseplan.cli.list",
}


def main():
    """Main CLI entry point following git-style subcommand pattern."""
    parser = argparse.ArgumentParser(
        prog="cruiseplan",
        description="Oceanographic Cruise Planning System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cruiseplan bathymetry --bathy-source gebco2025
  cruiseplan pangaea "CTD temperature" --lat 50 60 --lon -50 -30
  cruiseplan stations --lat 50 65 --lon -60 -30
  cruiseplan run cruise.yaml
  cruiseplan enrich cruise.yaml --add-depths --add-coords
  cruiseplan validate cruise.yaml
  cruiseplan schedule cruise.yaml -o results/
  cruiseplan map cruise.yaml --figsize 14 10
  cruiseplan list MSM142_schedule.nc
  cruiseplan forecast MSM142_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00"

For detailed help on a subcommand:
  cruiseplan <subcommand> --help
        """,
    )

    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )

    subparsers = parser.add_subparsers(
        dest="subcommand",
        title="Available commands",
        description="Choose a subcommand to run",
        help="Available subcommands",
    )

    # Register each subcommand parser (lazy imports keep startup fast)
    for module_path in _SUBCOMMAND_MODULES.values():
        mod = importlib.import_module(module_path)
        mod.build_parser(subparsers)

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    try:
        mod = importlib.import_module(_SUBCOMMAND_MODULES[args.subcommand])
        mod.run(args)
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: A critical error occurred during execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
