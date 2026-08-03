"""
Real-time cruise forecast command.

This module implements the 'cruiseplan forecast' command for generating
rolling station plan forecasts from NetCDF schedule files during a cruise.

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
    stationplan_tex,
    stationplan_waypoints,
)
from cruiseplan.cli import handle_cli_errors
from cruiseplan.config.values import (
    BATHY_SOURCES,
    DEFAULT_BATHY_DIR,
    DEFAULT_BATHY_SOURCE,
)


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for forecast command.

    Delegates all business logic to the cruiseplan.api.stationplan_api functions.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing schedule file and operation mode.
    """
    with handle_cli_errors("forecast", getattr(args, "verbose", False)):
        schedule_file = args.schedule_file
        if not schedule_file.exists():
            print(f"ERROR: Schedule file not found: {schedule_file}", file=sys.stderr)
            sys.exit(1)
            return

        if args.output and args.output.is_absolute():
            print(
                "ERROR: --output must be a relative filename; use --output-dir for the directory",
                file=sys.stderr,
            )
            sys.exit(1)
            return

        has_index = args.start_index is not None
        has_time = args.start_time is not None
        if has_index != has_time:
            missing = "--start-time" if has_index else "--start-index"
            given = "--start-index" if has_index else "--start-time"
            print(
                f"ERROR: {given} requires {missing} — both must be provided together",
                file=sys.stderr,
            )
            sys.exit(1)
            return

        format_type = args.format
        if has_index and has_time:
            _run_forecast_mode(args, schedule_file, format_type)
        else:
            _run_static_mode(args, schedule_file, format_type)


def _resolve_output_path(
    args: argparse.Namespace,
    target_suffix: str,
    bad_suffixes: set[str] | None = None,
) -> Path | None:
    """
    Build the output path from args, optionally correcting a wrong file extension.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; reads ``args.output`` (Path | None) and ``args.output_dir`` (Path).
    target_suffix : str
        Expected extension including dot (e.g. ``".kml"``).
    bad_suffixes : set[str] | None
        Extensions to swap out for ``target_suffix`` (e.g. ``{".txt", ".tex", ".png"}``).
        If None, or the file's suffix is not in the set, the filename is used as-is.

    Returns
    -------
    Path | None
        Full output path, or None if ``args.output`` is not set.
    """
    if not args.output:
        return None
    if bad_suffixes and args.output.suffix.lower() in bad_suffixes:
        return args.output_dir / args.output.with_suffix(target_suffix).name
    return args.output_dir / args.output


def _run_forecast_mode(
    args: argparse.Namespace, schedule_file: Path, format_type: str
) -> None:
    """
    Dispatch to the correct format handler for forecast mode.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; ``args.start_index`` and ``args.start_time`` must be set.
    schedule_file : Path
        NetCDF schedule file.
    format_type : str
        One of ``"tex"``, ``"waypoints"``, ``"kml"``, ``"png"``, or ``"text"``.
    """
    if format_type == "tex":
        _forecast_tex(args, schedule_file)
    elif format_type == "waypoints":
        _forecast_waypoints(args, schedule_file)
    elif format_type == "kml":
        _forecast_kml(args, schedule_file)
    elif format_type == "png":
        _forecast_png(args, schedule_file)
    else:
        _forecast_text(args, schedule_file)


def _forecast_tex(args: argparse.Namespace, schedule_file: Path) -> None:
    """
    Generate a TeX workplan for the forecast window.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; reads output, logo, number, title, start_index,
        start_time, duration.
    schedule_file : Path
        NetCDF schedule file.
    """
    output_path = _resolve_output_path(args, ".tex")
    result = stationplan_forecast_tex(
        schedule_file=schedule_file,
        start_index=args.start_index,
        start_time=args.start_time,
        duration_hours=args.duration,
        output_path=output_path,
        logo_path=args.logo,
        workplan_number=args.number,
        cruise_title=args.title,
    )
    if result.success:
        print(f"Generated TeX forecast: {result.output}")
    else:
        print(f"ERROR: {result.message}", file=sys.stderr)
        sys.exit(1)


def _forecast_waypoints(args: argparse.Namespace, schedule_file: Path) -> None:
    """
    Generate bridge waypoints for the forecast window.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; reads output, current_position, start_index,
        start_time, duration.
    schedule_file : Path
        NetCDF schedule file.
    """
    current_position = _parse_current_position(args)
    output_path = _resolve_output_path(args, ".txt")
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


def _forecast_kml(args: argparse.Namespace, schedule_file: Path) -> None:
    """
    Generate a KML forecast track.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; reads output, start_index, start_time, duration.
    schedule_file : Path
        NetCDF schedule file.
    """
    output_path = _resolve_output_path(args, ".kml", {".txt", ".tex", ".png"})
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


def _forecast_png(args: argparse.Namespace, schedule_file: Path) -> None:
    """
    Generate a PNG map for the forecast window.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; reads output, bathy_source, bathy_dir, bathy_stride,
        figsize, lat, lon, max_depth, bathy_contours, no_title, no_labels,
        no_legend, start_index, start_time, duration.
    schedule_file : Path
        NetCDF schedule file.
    """
    output_path = _resolve_output_path(args, ".png", {".txt", ".tex", ".kml"})
    result = stationplan_forecast_png(
        schedule_file=schedule_file,
        start_index=args.start_index,
        start_time=args.start_time,
        duration_hours=args.duration,
        output_path=output_path,
        bathy_source=args.bathy_source,
        bathy_dir=args.bathy_dir,
        bathy_stride=args.bathy_stride,
        figsize=tuple(args.figsize),
        lat_bounds=args.lat,
        lon_bounds=args.lon,
        max_depth=args.max_depth,
        bathy_contours=args.bathy_contours,
        no_title=args.no_title,
        no_labels=args.no_labels,
        no_legend=args.no_legend,
    )
    if result.success:
        print(f"Generated PNG forecast map: {result.output}")
    else:
        print(f"ERROR: {result.message}", file=sys.stderr)
        sys.exit(1)


def _forecast_text(args: argparse.Namespace, schedule_file: Path) -> None:
    """
    Generate a plain-text rolling forecast.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args; reads output, transit_speed, start_index,
        start_time, duration.
    schedule_file : Path
        NetCDF schedule file.
    """
    result = stationplan_forecast(
        schedule_file=schedule_file,
        start_index=args.start_index,
        start_time=args.start_time,
        duration_hours=args.duration,
        transit_speed=args.transit_speed,
    )
    if not result.success:
        print(f"ERROR: {result.message}", file=sys.stderr)
        sys.exit(1)
        return
    output_path = _resolve_output_path(args, ".txt")
    if output_path:
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


def _run_static_mode(
    args: argparse.Namespace, schedule_file: Path, format_type: str
) -> None:
    """
    Handle static format mode (no start params): tex, waypoints, or error.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI args.
    schedule_file : Path
        NetCDF schedule file.
    format_type : str
        One of ``"tex"``, ``"waypoints"``, ``"kml"``, ``"png"``, or ``"text"``.
    """
    if format_type == "tex":
        output_path = _resolve_output_path(args, ".tex")
        result = stationplan_tex(
            schedule_file,
            output_path,
            args.logo,
            args.number,
            args.title,
        )
        if result.success:
            print(f"Generated TeX station table: {result.output}")
        else:
            print(f"ERROR: {result.message}", file=sys.stderr)
            sys.exit(1)

    elif format_type == "waypoints":
        current_position = _parse_current_position(args)
        output_path = _resolve_output_path(args, ".txt")
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

    elif format_type in ("kml", "png"):
        print(
            f"ERROR: {format_type.upper()} format requires --start-index and --start-time",
            file=sys.stderr,
        )
        sys.exit(1)

    else:
        print(
            "ERROR: Must specify --start-index and --start-time, or --format tex/waypoints",
            file=sys.stderr,
        )
        print(
            "   Use 'cruiseplan forecast --help' for usage information",
            file=sys.stderr,
        )
        sys.exit(1)


def _parse_current_position(
    args: argparse.Namespace,
) -> tuple[float, float] | None:
    """Parse --current-position 'lat,lon' string into a (lat, lon) float tuple."""
    if not getattr(args, "current_position", None):
        return None
    try:
        lat_str, lon_str = args.current_position.split(",")
        return (float(lat_str.strip()), float(lon_str.strip()))
    except ValueError as e:
        print(
            f"ERROR: Invalid current position format. Use 'lat,lon' like '65.123,-30.456': {e}",
            file=sys.stderr,
        )
        sys.exit(1)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the forecast subparser and return it."""
    p = subparsers.add_parser(
        "forecast",
        help="Generate real-time station plan forecasts from NetCDF schedules",
        description="Generate rolling station plan forecasts for real-time cruise operations.",
        epilog="""
Run 'cruiseplan list SCHEDULE_FILE' first to see activity indices.

Forecast mode (--start-index and --start-time required together):
  cruiseplan forecast MSM142_schedule.nc --start-index 18 --start-time "2026-08-30T14:00:00"
  cruiseplan forecast MSM142_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --duration 36 --output forecast.txt
  cruiseplan forecast MSM142_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --current-position "65.123,-30.456"
  cruiseplan forecast MSM142_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --duration 48 --format waypoints
  cruiseplan forecast MSM142_schedule.nc --start-index 2 --start-time "2026-05-05 08:00" --duration 24 --format png

Static format mode (no start params):
  cruiseplan forecast MSM142_schedule.nc --format tex --output station_plan.tex
  cruiseplan forecast MSM142_schedule.nc --format waypoints
        """,
    )
    p.add_argument(
        "schedule_file",
        type=Path,
        metavar="SCHEDULE_FILE",
        help="NetCDF schedule file (e.g., 'MSM142_leg_2_schedule.nc')",
    )
    p.add_argument(
        "--start-index",
        type=int,
        help="Starting activity index (0-based); required with --start-time",
    )
    p.add_argument(
        "--start-time",
        help="New start time for first activity (ISO format: '2026-08-30T14:00:00'); required with --start-index",
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
        help="Ship transit speed in knots for text forecast (default: 10)",
    )
    p.add_argument(
        "--current-position",
        help="Current ship position as 'lat,lon' in decimal degrees (e.g., '65.123,-30.456')",
    )
    p.add_argument(
        "--format",
        choices=["text", "tex", "waypoints", "kml", "png"],
        default="text",
        help="Output format: text (default), tex, waypoints, kml, png",
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
        type=Path,
        help="Output filename, relative to --output-dir (default: stdout)",
    )
    p.add_argument(
        "--logo",
        type=Path,
        help="Path to logo image file (PNG, JPG, PDF) for TeX output",
    )
    p.add_argument(
        "--number",
        help="Workplan number for TeX output (e.g., '28')",
    )
    p.add_argument(
        "--title",
        help="Cruise title for TeX output (e.g., 'MSM142')",
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
        help="Bathymetry grid downsampling factor for PNG maps (default: 10)",
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
        help="Maximum water depth in meters for bathymetry colour scale",
    )
    p.add_argument(
        "--bathy-contours",
        nargs="+",
        type=float,
        default=None,
        metavar="DEPTH",
        help="Bathymetry contour depths in meters (e.g. --bathy-contours 200 500 1000)",
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
        help="Latitude bounds for PNG map extent (e.g., --lat 60 70)",
    )
    p.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for PNG map extent (e.g., --lon -40 -20)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
