"""
Activity listing command.

This module implements the 'cruiseplan list' command for displaying all
activities in a NetCDF schedule file with their indices — typically the
first step before running 'cruiseplan forecast'.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

from cruiseplan.api.stationplan_api import stationplan_list


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for list command.

    Delegates all business logic to cruiseplan.api.stationplan_api.stationplan_list.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing the schedule file path.
    """
    try:
        schedule_file = Path(args.schedule_file)
        if not schedule_file.exists():
            print(f"ERROR: Schedule file not found: {schedule_file}", file=sys.stderr)
            sys.exit(1)
            return

        result = stationplan_list(schedule_file)

        if result.success:
            print(result.output)
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the list subparser and return it."""
    p = subparsers.add_parser(
        "list",
        help="List all activities in a schedule with indices",
        description=(
            "Display all activities in a NetCDF schedule file with their indices, "
            "time offsets, categories, durations, and names. "
            "Use the printed indices with 'cruiseplan forecast --start-index'."
        ),
        epilog="""
Examples:
  cruiseplan list MSM142_leg_2_schedule.nc
  cruiseplan list data/cruise_schedule.nc
        """,
    )
    p.add_argument(
        "schedule_file",
        type=Path,
        metavar="SCHEDULE_FILE",
        help="NetCDF schedule file (e.g., 'MSM142_leg_2_schedule.nc')",
    )
    return p
