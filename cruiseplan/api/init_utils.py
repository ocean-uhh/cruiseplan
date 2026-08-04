"""Helper functions for __init__.py to reduce complexity in API functions."""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Internal helper functions (prefixed with _)
# ============================================================================


def _handle_error_with_logging(
    error: Exception, message: str, verbose: bool = False
) -> None:
    """Log error with optional traceback."""
    logger.error(f"❌ {message}: {error}")
    if verbose:
        import traceback

        traceback.print_exc()


def _validate_lat_lon_bounds(
    lat_bounds: list[float] | None, lon_bounds: list[float] | None
) -> tuple[float, float, float, float] | None:
    """
    Validate and convert lat/lon bounds to bbox format.

    Returns None if bounds are invalid or not provided.
    Returns (min_lon, min_lat, max_lon, max_lat) tuple if valid.
    """
    if lat_bounds or lon_bounds:
        if not (lat_bounds and lon_bounds):
            logger.error(
                "Both lat_bounds and lon_bounds must be provided for geographic search"
            )
            return None

        if len(lat_bounds) != 2 or len(lon_bounds) != 2:
            logger.error(
                "lat_bounds and lon_bounds must each contain exactly 2 values [min, max]"
            )
            return None

        # Validate latitude range (-90 to 90)
        if any(lat < -90 or lat > 90 for lat in lat_bounds):
            logger.error(
                f"Latitude values must be between -90 and 90, got: {lat_bounds}"
            )
            return None

        # Validate longitude range (-180 to 180)
        if any(lon < -180 or lon > 180 for lon in lon_bounds):
            logger.error(
                f"Longitude values must be between -180 and 180, got: {lon_bounds}"
            )
            return None

        return (lon_bounds[0], lat_bounds[0], lon_bounds[1], lat_bounds[1])
    return None


def _parse_schedule_formats(
    format_str: str | None, derive_netcdf: bool = False
) -> list[str]:
    """
    Parse format string for schedule generation.

    Parameters
    ----------
    format_str : Optional[str]
        Format string: "all", comma-separated list, or None
    derive_netcdf : bool
        Whether to include specialized NetCDF formats

    Returns
    -------
    List[str]
        List of format strings to process
    """
    if format_str is None:
        return []

    if format_str == "all":
        formats = ["html", "latex", "csv", "netcdf", "png"]
        if derive_netcdf:
            formats.append("netcdf_specialized")
    else:
        formats = [fmt.strip() for fmt in format_str.split(",")]

    return formats


def _parse_map_formats(format_str: str | None) -> list[str]:
    """
    Parse format string for map/process functions.

    Parameters
    ----------
    format_str : Optional[str]
        Format string: "all", "kml", "png", comma-separated list, or None

    Returns
    -------
    List[str]
        List of format strings to process
    """
    if format_str is None:
        return []

    if format_str == "all":
        return ["png", "kml"]
    else:
        formats = [fmt.strip() for fmt in format_str.split(",")]

    return formats


# ============================================================================
# Schedule generation helpers (public, used by schedule function)
# ============================================================================


def generate_html_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Path | None:
    """Generate HTML schedule output."""
    from cruiseplan.output.html_generator import generate_html_schedule

    output_path = output_dir_path / f"{base_name}_schedule.html"
    generate_html_schedule(cruise_config, timeline, output_path)
    logger.info(f"✅ Generated HTML schedule: {output_path}")
    return output_path


def generate_latex_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Path | None:
    """Generate LaTeX schedule output."""
    from cruiseplan.output.latex_generator import generate_latex_tables

    latex_files = generate_latex_tables(
        cruise_config, timeline, output_dir_path, base_name
    )
    output_path = (
        latex_files[0] if latex_files else output_dir_path / f"{base_name}_schedule.tex"
    )
    logger.info(f"✅ Generated LaTeX schedule: {output_path}")
    return output_path


def generate_csv_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Path | None:
    """Generate CSV schedule output."""
    from cruiseplan.output.csv_generator import generate_csv_schedule

    output_path = output_dir_path / f"{base_name}_schedule.csv"
    generate_csv_schedule(cruise_config, timeline, output_path)
    logger.info(f"✅ Generated CSV schedule: {output_path}")
    return output_path


def generate_netcdf_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Path | None:
    """Generate NetCDF schedule output."""
    from cruiseplan.output.netcdf_generator import NetCDFGenerator

    output_path = output_dir_path / f"{base_name}_schedule.nc"
    logger.info(f"📄 NetCDF Generator: Starting generation of {output_path}")
    logger.info(f"   Timeline contains {len(timeline)} activities")

    generator = NetCDFGenerator()
    generator.generate_master_schedule(timeline, cruise_config, output_path)
    logger.info(f"✅ Generated NetCDF schedule: {output_path}")
    return output_path


def generate_specialized_netcdf(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path
) -> list[Path]:
    """Generate specialized NetCDF files."""
    from cruiseplan.output.netcdf_generator import NetCDFGenerator

    generator = NetCDFGenerator()
    specialized_files = generator.generate_all_netcdf_outputs(
        cruise_config, timeline, output_dir_path
    )
    logger.info(
        f"✅ Generated specialized NetCDF files: {len(specialized_files)} files"
    )
    return specialized_files


def generate_png_format(
    cruise: Any,
    timeline: list[Any],
    output_dir_path: Path,
    base_name: str,
    bathy_source: str,
    bathy_dir: str,
    bathy_stride: int,
    figsize: tuple,
    bathy_contours: list | None = None,
    lat_bounds: list | None = None,
    lon_bounds: list | None = None,
    no_ports: bool = False,
    no_title: bool = False,
    no_labels: bool = False,
    no_legend: bool = False,
    suffix: str = "map",
    max_depth: int | None = None,
    include_eez: bool = False,
) -> Path | None:
    """
    Generate a PNG map and write it to disk.

    Thin wrapper around ``generate_map_from_timeline`` that constructs the
    output path from *output_dir_path*, *base_name*, and *suffix*, then
    delegates all rendering work downstream.

    Parameters
    ----------
    cruise : CruiseInstance
        Loaded cruise object; passed as ``config`` to the map generator for
        port extraction and cruise metadata.
    timeline : list
        Timeline data from the scheduler (list of activity dicts with
        coordinates).
    output_dir_path : Path
        Directory where the PNG file will be written.
    base_name : str
        Filename stem; the output file is ``{base_name}_{suffix}.png``.
    bathy_source : str
        Bathymetry dataset identifier (e.g. ``"gebco2025"``).
    bathy_dir : str
        Path to the directory containing bathymetry netCDF files.
    bathy_stride : int
        Downsampling stride for bathymetry contours (higher = faster, less detail).
    figsize : tuple
        Figure size as ``(width, height)`` in inches.
    bathy_contours : list, optional
        Explicit depth contour levels (m). If None, contours are derived from
        *bathy_stride* automatically.
    lat_bounds : list, optional
        ``[min_lat, max_lat]`` in decimal degrees. If None, bounds are
        calculated from the cruise track.
    lon_bounds : list, optional
        ``[min_lon, max_lon]`` in decimal degrees. If None, bounds are
        calculated from the cruise track.
    no_ports : bool
        If True, departure and arrival ports are excluded from the map.
        Default is False.
    no_title : bool
        If True, the cruise title is omitted from the map. Default is False.
    no_labels : bool
        If True, station name annotations are omitted. Default is False.
    no_legend : bool
        If True, the legend is omitted. Default is False.
    suffix : str
        Filename suffix inserted before ``.png`` (default: ``"map"``).
    max_depth : int, optional
        Maximum water depth (m) for the bathymetry colour scale. If None,
        the full -8000 to +200 m range is used.
    include_eez : bool
        If True, EEZ boundaries from Marine Regions v12 are overlaid
        (visualization only; data downloaded and cached on first use).
        Default is False.

    Returns
    -------
    Path or None
        Absolute path to the generated PNG file, or None if generation failed.
    """
    from cruiseplan.output.map_generator import generate_map_from_timeline

    output_path = output_dir_path / f"{base_name}_{suffix}.png"
    logger.info(f"🗺️ PNG Map Generator: Starting generation of {output_path}")

    map_file = generate_map_from_timeline(
        timeline=timeline,
        output_file=output_path,
        bathy_source=bathy_source,
        bathy_dir=bathy_dir,
        bathy_stride=bathy_stride,
        bathy_contours=bathy_contours,
        lat_bounds=lat_bounds,
        lon_bounds=lon_bounds,
        figsize=figsize,
        no_ports=no_ports,
        no_title=no_title,
        no_labels=no_labels,
        no_legend=no_legend,
        config=cruise,
        max_depth=max_depth,
        include_eez=include_eez,
    )

    if map_file:
        logger.info(f"✅ Generated PNG map: {map_file}")
    else:
        logger.warning("PNG map generation failed")

    return map_file
