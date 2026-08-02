"""
Station plan generation command.

This module implements the 'cruiseplan stationplan' command for listing
activities and generating station plan forecasts from NetCDF schedule files.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

from cruiseplan.api.stationplan_api import (
    stationplan_forecast,
    stationplan_forecast_kml,
    stationplan_forecast_png,
    stationplan_forecast_tex,
    stationplan_list,
    stationplan_tex,
    stationplan_waypoints,
)
from cruiseplan.config.values import (
    BATHY_SOURCES,
    DEFAULT_BATHY_DIR,
    DEFAULT_BATHY_SOURCE,
)


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for stationplan command.

    Delegates all business logic to the cruiseplan.api.stationplan_api functions.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing schedule file and operation mode.
    """
    try:
        schedule_file = Path(args.schedule_file)
        if not schedule_file.exists():
            print(f"ERROR: Schedule file not found: {schedule_file}", file=sys.stderr)
            sys.exit(1)

        # List mode
        if args.list:
            result = stationplan_list(schedule_file)

            if result.success:
                print(result.output)
            else:
                print(f"ERROR: {result.message}", file=sys.stderr)
                sys.exit(1)

        # Forecast mode with optional format
        elif args.start_index is not None and args.start_time is not None:
            format_type = getattr(args, "format", None)

            if format_type == "tex":
                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output

                result = stationplan_forecast_tex(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    output_path=output_path,
                    logo_path=getattr(args, "logo", None),
                    workplan_number=getattr(args, "number", None),
                    cruise_title=getattr(args, "title", None),
                )

                if result.success:
                    print(f"Generated TeX forecast: {result.output}")
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

            elif format_type == "waypoints":
                current_position = None
                if hasattr(args, "current_position") and args.current_position:
                    try:
                        lat_str, lon_str = args.current_position.split(",")
                        current_position = (
                            float(lat_str.strip()),
                            float(lon_str.strip()),
                        )
                    except (ValueError, AttributeError) as e:
                        print(
                            f"ERROR: Invalid current position format. Use 'lat,lon' like '65.123,-30.456': {e}",
                            file=sys.stderr,
                        )
                        sys.exit(1)

                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output

                result = stationplan_waypoints(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    current_position=current_position,
                    output_path=output_path,
                )

                if result.success:
                    if output_path:
                        print(f"Generated bridge waypoints: {result.output}")
                    else:
                        print(result.output)
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

            elif format_type == "kml":
                output_path = None
                if args.output:
                    output_file = Path(args.output)
                    if output_file.suffix.lower() in [".txt", ".tex"]:
                        output_path = (
                            args.output_dir / output_file.with_suffix(".kml").name
                        )
                    else:
                        output_path = args.output_dir / args.output

                result = stationplan_forecast_kml(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    output_path=output_path,
                )

                if result.success:
                    print(f"Generated KML forecast: {result.output}")
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

            elif format_type == "png":
                output_path = None
                if args.output:
                    output_file = Path(args.output)
                    if output_file.suffix.lower() in [".txt", ".tex", ".kml"]:
                        output_path = (
                            args.output_dir / output_file.with_suffix(".png").name
                        )
                    else:
                        output_path = args.output_dir / args.output

                lat_bounds = None
                lon_bounds = None
                if hasattr(args, "lat") and args.lat:
                    lat_bounds = args.lat
                if hasattr(args, "lon") and args.lon:
                    lon_bounds = args.lon

                result = stationplan_forecast_png(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    output_path=output_path,
                    bathy_source=getattr(args, "bathy_source", "gebco2025"),
                    bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
                    bathy_stride=getattr(args, "bathy_stride", 10),
                    figsize=tuple(getattr(args, "figsize", [10.0, 8.1])),
                    lat_bounds=lat_bounds,
                    lon_bounds=lon_bounds,
                    max_depth=getattr(args, "max_depth", None),
                    bathy_contours=getattr(args, "bathy_contours", None),
                    no_title=getattr(args, "no_title", False),
                    no_labels=getattr(args, "no_labels", False),
                    no_legend=getattr(args, "no_legend", False),
                )

                if result.success:
                    print(f"Generated PNG forecast map: {result.output}")
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

            else:
                result = stationplan_forecast(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    transit_speed=args.transit_speed,
                )

                if result.success:
                    if args.output:
                        output_path = args.output_dir / args.output
                        try:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, "w") as f:
                                f.write(result.output)
                            print(f"Forecast written to: {output_path}")
                        except Exception as e:
                            print(
                                f"ERROR: Error writing to {output_path}: {e}",
                                file=sys.stderr,
                            )
                            sys.exit(1)
                    else:
                        print(result.output)
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

        # Format mode without forecast parameters
        elif getattr(args, "format", None) in ["tex", "waypoints", "kml", "png"]:
            format_type = getattr(args, "format", None)

            if format_type == "tex":
                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output

                result = stationplan_tex(
                    schedule_file,
                    output_path,
                    getattr(args, "logo", None),
                    getattr(args, "number", None),
                    getattr(args, "title", None),
                )

                if result.success:
                    print(f"Generated TeX station table: {result.output}")
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

            elif format_type == "waypoints":
                current_position = None
                if hasattr(args, "current_position") and args.current_position:
                    try:
                        lat_str, lon_str = args.current_position.split(",")
                        current_position = (
                            float(lat_str.strip()),
                            float(lon_str.strip()),
                        )
                    except (ValueError, AttributeError) as e:
                        print(
                            f"ERROR: Invalid current position format. Use 'lat,lon' like '65.123,-30.456': {e}",
                            file=sys.stderr,
                        )
                        sys.exit(1)

                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output

                result = stationplan_waypoints(
                    schedule_file=schedule_file,
                    start_index=None,
                    start_time=None,
                    duration_hours=None,
                    current_position=current_position,
                    output_path=output_path,
                )

                if result.success:
                    if output_path:
                        print(f"Generated bridge waypoints: {result.output}")
                    else:
                        print(result.output)
                else:
                    print(f"ERROR: {result.message}", file=sys.stderr)
                    sys.exit(1)

            elif format_type == "kml":
                print(
                    "ERROR: KML format requires forecast parameters: --start-index and --start-time",
                    file=sys.stderr,
                )
                print(
                    "   Use 'cruiseplan stationplan --help' for usage information",
                    file=sys.stderr,
                )
                sys.exit(1)

            elif format_type == "png":
                print(
                    "ERROR: PNG format requires forecast parameters: --start-index and --start-time",
                    file=sys.stderr,
                )
                print(
                    "   Use 'cruiseplan stationplan --help' for usage information",
                    file=sys.stderr,
                )
                sys.exit(1)

        # No valid mode specified
        else:
            print(
                "ERROR: Must specify either --list or both --start-index and --start-time",
                file=sys.stderr,
            )
            print(
                "   Use 'cruiseplan stationplan --help' for usage information",
                file=sys.stderr,
            )
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the stationplan subparser and return it."""
    p = subparsers.add_parser(
        "stationplan",
        help="Generate station plan forecasts from NetCDF schedules",
        description="Generate simple text-based station plans for real-time cruise operations",
        epilog="""
This command generates station plans from processed cruise schedules for real-time
cruise operations. It can list all activities with indices or generate rolling
forecasts starting from any activity with updated timing.

Examples:
  cruiseplan stationplan MSM142_leg_2_schedule.nc --list
  cruiseplan stationplan data/cruise_schedule.nc --start-index 18 --start-time "2026-08-30T14:00:00"
  cruiseplan stationplan data/cruise_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --duration 36 --output forecast.txt
  cruiseplan stationplan data/cruise_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --current-position "65.123,-30.456"
  cruiseplan stationplan data/cruise_schedule.nc --format tex --output station_plan.tex
  cruiseplan stationplan data/cruise_schedule.nc --start-index 5 --duration 48 --format waypoints --output bridge_waypoints.txt
  cruiseplan stationplan data/cruise_schedule.nc --start-index 2 --start-time "2026-05-05 08:00" --duration 24 --format png --output forecast_map.png
        """,
    )
    p.add_argument(
        "schedule_file",
        type=Path,
        metavar="SCHEDULE_FILE",
        help="NetCDF schedule file (e.g., 'MSM142_leg_2_schedule.nc')",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="Display all activities with indices and exit",
    )
    p.add_argument(
        "--start-index",
        type=int,
        help="Starting activity index for forecast mode (0-based)",
    )
    p.add_argument(
        "--start-time",
        help="New start time for first activity (ISO format: '2026-08-30T14:00:00')",
    )
    p.add_argument(
        "--duration",
        type=float,
        default=24.0,
        help="Forecast duration in hours (default: 24)",
    )
    p.add_argument(
        "--transit-speed",
        type=float,
        default=10.0,
        help="Ship transit speed in knots (default: 10)",
    )
    p.add_argument(
        "--current-position",
        help="Current ship position as 'lat,lon' in decimal degrees (e.g., '65.123,-30.456')",
    )
    p.add_argument(
        "--format",
        choices=["text", "tex", "waypoints", "kml", "png"],
        default="text",
        help="Output format: 'text' for console/file output, 'tex' for LaTeX tables, 'waypoints' for bridge navigation, 'kml' for Google Earth, 'png' for map visualisation (default: text)",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Output directory (default: current directory)",
    )
    p.add_argument(
        "--output",
        help="Output filename (default: stdout)",
    )
    p.add_argument(
        "--logo",
        type=Path,
        help="Path to logo image file (PNG, JPG, PDF). If not specified, uses default logo from images/ folder",
    )
    p.add_argument(
        "--number",
        help="Workplan number for TeX output (e.g., '28'). Used in title as 'TITLE - Workplan XX'",
    )
    p.add_argument(
        "--title",
        help="Cruise title for TeX output (e.g., 'MSM142'). Used in title as 'TITLE - Workplan XX'",
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
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[10, 8.1],
        help="Figure size for PNG maps in inches (default: 10 8.1)",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="METRES",
        help="Maximum water depth (m) for the bathymetry colour scale. Example: --max-depth 1000",
    )
    p.add_argument(
        "--bathy-contours",
        nargs="+",
        type=float,
        default=None,
        metavar="DEPTH",
        help="Bathymetry contour depths in metres (e.g. --bathy-contours 200 500 1000 2000). Replaces defaults.",
    )
    p.add_argument(
        "--no-title",
        action="store_true",
        help="Suppress the map title",
    )
    p.add_argument(
        "--no-labels",
        action="store_true",
        help="Suppress station name labels on the map",
    )
    p.add_argument(
        "--no-legend",
        action="store_true",
        help="Suppress the map legend",
    )
    p.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds for map extent (e.g., --lat 60 70)",
    )
    p.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for map extent (e.g., --lon -40 -20)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
