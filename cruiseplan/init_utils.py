"""Helper functions for __init__.py to reduce complexity in API functions."""

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Internal helper functions (prefixed with _)
# ============================================================================


def _setup_verbose_logging(verbose: bool) -> None:
    """Setup logging configuration based on verbose flag."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)


def _handle_error_with_logging(
    error: Exception, message: str, verbose: bool = False
) -> None:
    """Log error with optional traceback."""
    logger.error(f"❌ {message}: {error}")
    if verbose:
        import traceback

        traceback.print_exc()


def _validate_lat_lon_bounds(
    lat_bounds: Optional[list[float]], lon_bounds: Optional[list[float]]
) -> Optional[tuple[float, float, float, float]]:
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

        return (lon_bounds[0], lat_bounds[0], lon_bounds[1], lat_bounds[1])
    return None


def _parse_schedule_formats(
    format_str: Optional[str], derive_netcdf: bool = False
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


def _parse_map_formats(format_str: Optional[str]) -> list[str]:
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
) -> Optional[Path]:
    """Generate HTML schedule output."""
    from cruiseplan.output.html_generator import generate_html_schedule

    output_path = output_dir_path / f"{base_name}_schedule.html"
    generate_html_schedule(cruise_config, timeline, output_path)
    logger.info(f"✅ Generated HTML schedule: {output_path}")
    return output_path


def generate_latex_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Optional[Path]:
    """Generate LaTeX schedule output."""
    from cruiseplan.output.latex_generator import generate_latex_tables

    latex_files = generate_latex_tables(cruise_config, timeline, output_dir_path)
    output_path = (
        latex_files[0] if latex_files else output_dir_path / f"{base_name}_schedule.tex"
    )
    logger.info(f"✅ Generated LaTeX schedule: {output_path}")
    return output_path


def generate_csv_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Optional[Path]:
    """Generate CSV schedule output."""
    from cruiseplan.output.csv_generator import generate_csv_schedule

    output_path = output_dir_path / f"{base_name}_schedule.csv"
    generate_csv_schedule(cruise_config, timeline, output_path)
    logger.info(f"✅ Generated CSV schedule: {output_path}")
    return output_path


def generate_netcdf_format(
    cruise_config: Any, timeline: list[Any], output_dir_path: Path, base_name: str
) -> Optional[Path]:
    """Generate NetCDF schedule output."""
    from cruiseplan.output.netcdf_generator import NetCDFGenerator

    output_path = output_dir_path / f"{base_name}_schedule.nc"
    logger.info(f"📄 NetCDF Generator: Starting generation of {output_path}")
    logger.info(f"   Timeline contains {len(timeline)} activities")

    generator = NetCDFGenerator()
    generator.generate_ship_schedule(timeline, cruise_config, output_path)
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
    suffix: str = "map",
) -> Optional[Path]:
    """Generate PNG map output."""
    from cruiseplan.output.map_generator import generate_map_from_timeline

    output_path = output_dir_path / f"{base_name}_{suffix}.png"
    logger.info(f"🗺️ PNG Map Generator: Starting generation of {output_path}")

    map_file = generate_map_from_timeline(
        timeline=timeline,
        output_file=output_path,
        bathy_source=bathy_source,
        bathy_dir=bathy_dir,
        bathy_stride=bathy_stride,
        figsize=figsize,
        config=cruise,
    )

    if map_file:
        logger.info(f"✅ Generated PNG map: {map_file}")
    else:
        logger.warning("PNG map generation failed")

    return map_file


# ============================================================================
# CLI-API Bridge Utilities for Refactoring
# ============================================================================


def _resolve_cli_to_api_params(args: Any, command: str) -> dict:
    """
    Map CLI arguments to API function parameters.

    Internal utility to convert CLI namespace arguments to API function parameters.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments
    command : str
        Command name for parameter mapping

    Returns
    -------
    Dict[str, Any]
        Dictionary of API parameters
    """
    from argparse import Namespace

    if not isinstance(args, Namespace):
        return {}

    # Common parameter mappings
    param_map = {
        "config_file": getattr(args, "config_file", None),
        "verbose": getattr(args, "verbose", False),
    }

    # Commands that need output parameters
    if command in ["enrich", "process", "schedule", "map", "pangaea"]:
        param_map.update(
            {
                "output_dir": getattr(args, "output_dir", "data"),
                "output": getattr(args, "output", None),
            }
        )

    # Command-specific mappings
    if command in ["validate", "enrich", "process"]:
        param_map.update(
            {
                "bathy_source": getattr(args, "bathy_source", "etopo2022"),
                "bathy_dir": getattr(args, "bathy_dir", "data"),
            }
        )

    if command in ["enrich", "process"]:
        param_map.update(
            {
                "add_depths": getattr(args, "add_depths", True),
                "add_coords": getattr(args, "add_coords", True),
                "expand_sections": getattr(args, "expand_sections", True),
            }
        )

    if command in ["validate"]:
        param_map.update(
            {
                "check_depths": getattr(args, "check_depths", True),
                "tolerance": getattr(args, "tolerance", 10.0),
                "strict": getattr(args, "strict", False),
                "warnings_only": getattr(args, "warnings_only", False),
            }
        )

    if command == "schedule":
        param_map.update(
            {
                "format": getattr(args, "format", "all"),
                "leg": getattr(args, "leg", None),
                "derive_netcdf": getattr(args, "derive_netcdf", False),
                "bathy_stride": getattr(args, "bathy_stride", 10),
                "figsize": getattr(args, "figsize", [12, 8]),
            }
        )

    if command == "process":
        param_map.update(
            {
                "format": getattr(args, "format", "all"),
                "bathy_stride": getattr(args, "bathy_stride", 10),
                "figsize": getattr(args, "figsize", [12, 8]),
                "run_validation": getattr(args, "run_validation", True),
                "run_map_generation": getattr(args, "run_map_generation", True),
                "depth_check": getattr(args, "validate_depths", True),
                "tolerance": getattr(args, "tolerance", 10.0),
                "no_port_map": getattr(args, "no_port_map", False),
            }
        )

    if command == "map":
        param_map.update(
            {
                "bathy_stride": getattr(args, "bathy_stride", 5),
                "figsize": getattr(args, "figsize", [12, 8]),
                "show_plot": getattr(args, "show_plot", False),
                "no_ports": getattr(args, "no_ports", False),
            }
        )

    if command == "bathymetry":
        # Bathymetry command doesn't accept common parameters like verbose
        param_map = {
            "bathy_source": getattr(args, "bathy_source", "etopo2022"),
            "output_dir": getattr(args, "output_dir", None),
            "citation": getattr(args, "citation", False),
        }

    if command == "pangaea":
        param_map.update(
            {
                "query_terms": getattr(args, "query_or_file", ""),
                "lat_bounds": getattr(args, "lat", None),
                "lon_bounds": getattr(args, "lon", None),
                "max_results": getattr(args, "limit", 100),
                "rate_limit": getattr(args, "rate_limit", 1.0),
                "merge_campaigns": getattr(args, "merge_campaigns", True),
            }
        )

    # Remove None values
    return {k: v for k, v in param_map.items() if v is not None}


def _convert_api_response_to_cli(response: Any, command: str) -> dict:
    """
    Convert API response to CLI-friendly format.

    Internal utility to standardize API responses for CLI display.

    Parameters
    ----------
    response : Any
        API response (various formats)
    command : str
        Command name for response formatting

    Returns
    -------
    Dict[str, Any]
        Standardized response format with 'success', 'data', 'files', etc.
    """
    result = {"success": True, "data": None, "files": [], "errors": [], "warnings": []}

    try:
        if isinstance(response, bool):
            # Simple boolean response (validate command)
            result["success"] = response

        elif isinstance(response, (str, Path)):
            # Single file path response (bathymetry, enrich commands)
            result["files"] = [Path(response)]

        elif isinstance(response, list):
            # List of file paths
            result["files"] = [Path(f) for f in response if f is not None]

        elif isinstance(response, tuple) and len(response) >= 2:
            # Tuple response (timeline, files) or (data, files)
            result["data"] = response[0]
            if response[1] is not None:
                if isinstance(response[1], list):
                    result["files"] = [Path(f) for f in response[1] if f is not None]
                else:
                    result["files"] = [Path(response[1])]

        else:
            # Other response types
            result["data"] = response

    except Exception as e:
        result["success"] = False
        result["errors"] = [str(e)]

    return result


def _aggregate_generated_files(*file_lists: list[Path]) -> list[Path]:
    """
    Combine and deduplicate file lists from multiple operations.

    Internal utility to handle file aggregation across multiple API calls.

    Parameters
    ----------
    *file_lists : List[Path]
        Variable number of file lists to combine

    Returns
    -------
    List[Path]
        Combined and deduplicated file list
    """
    all_files = []

    for file_list in file_lists:
        if isinstance(file_list, list):
            all_files.extend([Path(f) for f in file_list if f is not None])
        elif file_list is not None:
            all_files.append(Path(file_list))

    # Deduplicate while preserving order
    seen = set()
    unique_files = []

    for file_path in all_files:
        if file_path not in seen:
            seen.add(file_path)
            unique_files.append(file_path)

    return unique_files


def _extract_api_errors(response: Any) -> tuple[bool, list[str], list[str]]:
    """
    Extract success status, errors, and warnings from API response.

    Internal utility to parse API responses for error reporting.

    Parameters
    ----------
    response : Any
        API response that may contain error information

    Returns
    -------
    Tuple[bool, List[str], List[str]]
        (success, errors, warnings)
    """
    success = True
    errors = []
    warnings = []

    if isinstance(response, dict):
        success = response.get("success", True)
        errors = response.get("errors", [])
        warnings = response.get("warnings", [])

    elif isinstance(response, Exception):
        success = False
        errors = [str(response)]

    elif response is False:
        success = False
        errors = ["Operation failed"]

    return success, errors, warnings
