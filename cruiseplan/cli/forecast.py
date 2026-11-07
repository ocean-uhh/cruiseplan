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
        start_time, duration, current_position.
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
        current_position=_parse_current_position(args),
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
        Parsed CLI args; reads output, start_index, start_time, duration,
        current_position.
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
        current_position=_parse_current_position(args),
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
        no_legend, start_index, start_time, duration, current_position.
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
        current_position=_parse_current_position(args),
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
        start_time, duration, current_position.
    schedule_file : Path
        NetCDF schedule file.
    """
    result = stationplan_forecast(
        schedule_file=schedule_file,
        start_index=args.start_index,
        start_time=args.start_time,
        duration_hours=args.duration,
        transit_speed=args.transit_speed,
        current_position=_parse_current_position(args),
    )
    if not result.success:
        print(f"ERROR: {result.message}", file=sys.stderr)
        sys.exit(1)
        return
    output_path = _resolve_output_path(args, ".txt")
    if output_path:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with Path(output_path).open("w") as f:
                f.write(result.output)
            print(f"Forecast written to: {output_path}")
        except Exception as e:  # noqa: BLE001 - CLI: report write failure without traceback
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


def parse_position(text: str) -> tuple[float, float]:
    """
    Parse a position given as ``"lat,lon"`` or ``"lat lon"`` in decimal degrees.

    Parameters
    ----------
    text : str
        Latitude and longitude separated by a comma and/or spaces, e.g.
        ``"-74.62,164.30"`` or ``"-74.62 164.30"``.

    Returns
    -------
    tuple of float
        (latitude, longitude).

    Raises
    ------
    ValueError
        If there are not exactly two numbers, or they are out of range.
    """
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        raise ValueError(f"expected 'lat,lon', got '{text}'")
    lat, lon = float(parts[0]), float(parts[1])
    if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 360.0:
        raise ValueError(f"position out of range: {lat}, {lon}")
    return lat, lon


def join_position_argv(argv: list[str]) -> list[str]:
    """
    Join a two-value or signed ``--current-position`` to its option.

    argparse reads ``-74.62,164.30`` as an unknown option and takes only the
    first of two values. This rewrites ``--current-position LAT LON`` (any
    signs, optionally ``LAT, LON``) and ``--current-position -LAT,LON`` to
    ``--current-position=LAT,LON``. The ``=``, comma and quoted forms pass
    through; a following option is never taken as the longitude.

    Parameters
    ----------
    argv : list of str
        Command-line arguments without the program name.

    Returns
    -------
    list of str
        Arguments with the position joined to its option.
    """
    out: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--current-position" and i + 1 < len(argv):
            value = argv[i + 1]
            first = value.rstrip(",")
            if (
                _is_number(first)
                and "," not in first
                and i + 2 < len(argv)
                and _is_number(argv[i + 2].lstrip(","))
            ):
                out.append(f"--current-position={first},{argv[i + 2].lstrip(',')}")
                i += 3
                continue
            if _is_number_start(value):
                out.append(f"--current-position={value}")
                i += 2
                continue
        out.append(arg)
        i += 1
    return out


def _is_number_start(text: str) -> bool:
    """Check whether text starts like a signed number ('-7', '-.5')."""
    return len(text) > 1 and text[0] == "-" and (text[1].isdigit() or text[1] == ".")


def _is_number(text: str) -> bool:
    """Check whether text parses as a float."""
    try:
        float(text)
    except ValueError:
        return False
    return True


def _parse_current_position(
    args: argparse.Namespace,
) -> tuple[float, float] | None:
    """Parse --current-position into a (lat, lon) float tuple, or None."""
    if not getattr(args, "current_position", None):
        return None
    try:
        return parse_position(args.current_position)
    except ValueError as e:
        print(
            f"ERROR: Invalid current position. Use 'lat,lon' like '-74.62,164.30': {e}",
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

Anchoring: the row at --start-index starts at --start-time (UTC). On an
operation row the ship is there (the transit into it is not included); on a
transit row the ship is starting that transit now. With --current-position
the given position wins: --start-time is the time at that position, a transit
from it to the operation (the one a transit row leads to) is added at the
leg's speed, and the operation starts when it ends. Later rows keep their
planned offsets. The text and TeX headers state the rule applied.

Forecast mode (--start-index and --start-time required together):
  cruiseplan forecast MSM142_schedule.nc --start-index 18 --start-time "2026-08-30T14:00:00"
  cruiseplan forecast MSM142_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --duration 36 --output forecast.txt
  cruiseplan forecast MSM142_schedule.nc --start-index 5 --start-time "2026-08-29T08:00:00" --current-position 65.123,-30.456
  cruiseplan forecast pycnmix_schedule.nc --start-index 12 --start-time "2026-03-09 08:00" --current-position -74.98,163.48
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
        help="Row index from 'cruiseplan list' (0-based) to anchor on: an "
        "operation starts at --start-time; a transit row starts at "
        "--start-time from where it begins; required with --start-time",
    )
    p.add_argument(
        "--start-time",
        help="Start time of the anchored row, or of the ship at "
        "--current-position if given (ISO format). Without a zone it is UTC "
        "('2026-08-30T14:00:00'); with the ship's zone it is ship time "
        "('2026-08-30T14:00+03:00') and the TeX table is printed in ship time; "
        "required with --start-index",
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
        metavar="LAT,LON",
        help="Ship position at --start-time in decimal degrees (e.g. "
        "-74.62,164.30, '-74.62 164.30' or 65.0 -30.0); the forecast starts "
        "with a transit from it to the anchored operation",
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
        default=Path(),
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
        "--bathy-contours",
        nargs="+",
        type=float,
        default=None,
        metavar="DEPTH",
        help="Bathymetry contour depths in meters (e.g. --bathy-contours 200 500 1000)",
    )
    p.add_argument(
        "--max-depth",
        type=int,
        default=None,
        metavar="METRES",
        help="Maximum water depth in meters for bathymetry colour scale",
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
        "--figsize",
        nargs=2,
        type=float,
        metavar=("WIDTH", "HEIGHT"),
        default=[10, 8.1],
        help="Figure size for PNG maps in inches (default: 10 8.1)",
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
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
