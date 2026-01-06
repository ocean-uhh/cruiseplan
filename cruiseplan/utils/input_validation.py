"""
Input validation utilities for CLI commands.

This module provides internal utility functions for validating and processing
user inputs across CLI commands. These functions are used internally by the
CLI layer to validate inputs before passing them to the API layer.
"""

import logging
from argparse import Namespace
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _validate_config_file(file_path: Path, must_exist: bool = True) -> Path:
    """
    Validate YAML config file exists, readable, and well-formed.

    Internal utility function for config file validation.

    Parameters
    ----------
    file_path : Path
        Path to configuration file
    must_exist : bool, optional
        Whether file must exist, by default True

    Returns
    -------
    Path
        Resolved and validated file path

    Raises
    ------
    ValueError
        If file is invalid or inaccessible

    Examples
    --------
    >>> _validate_config_file(Path("cruise.yaml"))
    PosixPath('/path/to/cruise.yaml')
    """
    resolved_path = file_path.resolve()

    if must_exist:
        if not resolved_path.exists():
            raise ValueError(f"Configuration file not found: {resolved_path}")

        if not resolved_path.is_file():
            raise ValueError(f"Path is not a file: {resolved_path}")

        if not resolved_path.stat().st_size:
            raise ValueError(f"Configuration file is empty: {resolved_path}")

        # Basic YAML validation - check if it can be loaded
        try:
            from cruiseplan.utils.yaml_io import load_yaml

            load_yaml(resolved_path)
        except Exception as e:
            raise ValueError(f"Invalid YAML configuration: {e}")

    return resolved_path


def _validate_directory_writable(
    dir_path: Path, create_if_missing: bool = True
) -> Path:
    """
    Ensure output directory exists and is writable.

    Internal utility function for directory validation.

    Parameters
    ----------
    dir_path : Path
        Directory path to validate
    create_if_missing : bool, optional
        Create directory if it doesn't exist, by default True

    Returns
    -------
    Path
        Resolved and validated directory path

    Raises
    ------
    ValueError
        If directory cannot be created or is not writable
    """
    resolved_path = dir_path.resolve()

    if create_if_missing:
        resolved_path.mkdir(parents=True, exist_ok=True)

    if not resolved_path.exists():
        raise ValueError(f"Output directory does not exist: {resolved_path}")

    if not resolved_path.is_dir():
        raise ValueError(f"Path is not a directory: {resolved_path}")

    # Check if directory is writable by trying to create a temporary file
    try:
        test_file = resolved_path / ".tmp_write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        raise ValueError(f"Directory is not writable: {resolved_path}") from e

    return resolved_path


def _validate_coordinate_bounds(
    lat_bounds: list[float], lon_bounds: list[float]
) -> tuple[float, float, float, float]:
    """
    Validate and normalize coordinate bounds to bbox format.

    Internal utility function for coordinate validation that supports both
    -180/180 and 0/360 longitude formats.

    Parameters
    ----------
    lat_bounds : List[float]
        Latitude bounds [min_lat, max_lat]
    lon_bounds : List[float]
        Longitude bounds [min_lon, max_lon]

    Returns
    -------
    Tuple[float, float, float, float]
        Normalized bounds (min_lon, min_lat, max_lon, max_lat)

    Raises
    ------
    ValueError
        If coordinate bounds are invalid

    Examples
    --------
    >>> _validate_coordinate_bounds([50.0, 60.0], [-10.0, 10.0])
    (-10.0, 50.0, 10.0, 60.0)
    >>> _validate_coordinate_bounds([50.0, 60.0], [350.0, 360.0])
    (350.0, 50.0, 360.0, 60.0)
    """
    # Validate input format
    if not isinstance(lat_bounds, list) or len(lat_bounds) != 2:
        raise ValueError(
            "lat_bounds must be a list of exactly 2 values [min_lat, max_lat]"
        )

    if not isinstance(lon_bounds, list) or len(lon_bounds) != 2:
        raise ValueError(
            "lon_bounds must be a list of exactly 2 values [min_lon, max_lon]"
        )

    # Validate coordinate ranges
    min_lat, max_lat = lat_bounds
    min_lon, max_lon = lon_bounds

    # Validate latitude (always -90 to 90)
    if not (-90 <= min_lat <= 90):
        raise ValueError(
            f"Invalid minimum latitude: {min_lat}. Must be between -90 and 90."
        )

    if not (-90 <= max_lat <= 90):
        raise ValueError(
            f"Invalid maximum latitude: {max_lat}. Must be between -90 and 90."
        )

    if min_lat >= max_lat:
        raise ValueError(
            f"Minimum latitude ({min_lat}) must be less than maximum latitude ({max_lat})"
        )

    # Validate longitude ranges first - check for completely out-of-range values
    if not (-180 <= min_lon <= 360):
        raise ValueError(
            f"Invalid minimum longitude: {min_lon}. Must be between -180 and 360."
        )

    if not (-180 <= max_lon <= 360):
        raise ValueError(
            f"Invalid maximum longitude: {max_lon}. Must be between -180 and 360."
        )

    # Validate longitude format and ranges
    # Support both -180/180 and 0/360 formats, but not mixed
    if -180 <= min_lon <= 180 and -180 <= max_lon <= 180:
        # -180/180 format - allows meridian crossing
        if min_lon >= max_lon:
            raise ValueError(
                f"Minimum longitude ({min_lon}) must be less than maximum longitude ({max_lon})"
            )
    elif 0 <= min_lon <= 360 and 0 <= max_lon <= 360:
        # 0/360 format - NO meridian crossing allowed
        if min_lon >= max_lon:
            raise ValueError(
                f"Minimum longitude ({min_lon}) must be less than maximum longitude ({max_lon}). "
                f"For meridian crossing, use -180/180 format instead."
            )
    else:
        # Mixed format (e.g., -90 and 240)
        raise ValueError(
            "Longitude coordinates must use the same format:\n"
            "  - Both in -180 to 180 format (e.g., --lon -90 -30)\n"
            "  - Both in 0 to 360 format (e.g., --lon 270 330)\n"
            "  - Cannot mix formats (e.g., --lon -90 240 is invalid)\n"
            "  - Use -180/180 format for meridian crossing ranges"
        )

    # Return in bbox format (min_lon, min_lat, max_lon, max_lat)
    return (min_lon, min_lat, max_lon, max_lat)


def _validate_file_extension(file_path: Path, allowed_extensions: list[str]) -> bool:
    """
    Check if file has valid extension.

    Internal utility function for file extension validation.

    Parameters
    ----------
    file_path : Path
        File path to check
    allowed_extensions : List[str]
        List of allowed extensions (including dots, e.g., ['.yaml', '.yml'])

    Returns
    -------
    bool
        True if extension is valid

    Examples
    --------
    >>> _validate_file_extension(Path("config.yaml"), [".yaml", ".yml"])
    True
    """
    return file_path.suffix.lower() in [ext.lower() for ext in allowed_extensions]


def _validate_numeric_range(
    value: float, min_val: float, max_val: float, name: str
) -> float:
    """
    Validate numeric parameter is within acceptable range.

    Internal utility function for numeric validation.

    Parameters
    ----------
    value : float
        Value to validate
    min_val : float
        Minimum acceptable value
    max_val : float
        Maximum acceptable value
    name : str
        Parameter name for error messages

    Returns
    -------
    float
        Validated value

    Raises
    ------
    ValueError
        If value is outside acceptable range

    Examples
    --------
    >>> _validate_numeric_range(5.5, 0.0, 10.0, "stride")
    5.5
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}: {value}")

    if not (min_val <= value <= max_val):
        raise ValueError(
            f"{name} must be between {min_val} and {max_val}, got: {value}"
        )

    return float(value)


def _validate_format_list(formats: list[str], valid_formats: list[str]) -> list[str]:
    """
    Validate list of output formats.

    Internal utility function for format validation.

    Parameters
    ----------
    formats : List[str]
        List of format strings to validate
    valid_formats : List[str]
        List of valid format options

    Returns
    -------
    List[str]
        Validated and normalized format list

    Raises
    ------
    ValueError
        If any format is invalid
    """
    if not formats:
        raise ValueError("At least one format must be specified")

    normalized_formats = []
    invalid_formats = []

    for fmt in formats:
        fmt_clean = fmt.strip().lower()
        if fmt_clean in valid_formats:
            normalized_formats.append(fmt_clean)
        else:
            invalid_formats.append(fmt)

    if invalid_formats:
        raise ValueError(
            f"Invalid formats: {invalid_formats}. " f"Valid options: {valid_formats}"
        )

    # Remove duplicates while preserving order
    seen = set()
    result = []
    for fmt in normalized_formats:
        if fmt not in seen:
            seen.add(fmt)
            result.append(fmt)

    return result


def _detect_pangaea_mode(args) -> tuple[str, dict]:
    """
    Detect PANGAEA command mode (search vs file processing).

    Internal utility function for PANGAEA mode detection.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments

    Returns
    -------
    Tuple[str, dict]
        (mode, processed_arguments)
        mode is either 'search' or 'file'

    Raises
    ------
    ValueError
        If arguments are invalid for either mode
    """
    query_or_file = args.query_or_file

    # Check if it's a file path
    if Path(query_or_file).exists() and Path(query_or_file).is_file():
        # File mode
        if not _validate_file_extension(Path(query_or_file), [".txt", ".doi"]):
            logger.warning(
                f"File '{query_or_file}' doesn't have expected extension (.txt or .doi)"
            )

        return "file", {"query": query_or_file}

    # Search mode - requires lat/lon bounds
    if not (hasattr(args, "lat") and args.lat and hasattr(args, "lon") and args.lon):
        raise ValueError(
            "Search mode requires both --lat and --lon bounds. "
            "For file processing, provide an existing DOI file path."
        )

    # Validate coordinate bounds
    try:
        _validate_coordinate_bounds(args.lat, args.lon)
    except ValueError as e:
        raise ValueError(f"Invalid coordinate bounds: {e}")

    return "search", {"query": query_or_file}


def _validate_format_options(format_str: str, valid_formats: list[str]) -> list[str]:
    """
    Validate and parse format string for output generation.

    Internal utility function for format option validation.

    Parameters
    ----------
    format_str : str
        Format string from user input ("all", "html,csv", "netcdf", etc.)
    valid_formats : List[str]
        List of valid format options

    Returns
    -------
    List[str]
        Validated and normalized format list

    Raises
    ------
    ValueError
        If any format is invalid

    Examples
    --------
    >>> _validate_format_options("all", ["html", "csv", "netcdf"])
    ["html", "csv", "netcdf"]
    >>> _validate_format_options("html,csv", ["html", "csv", "netcdf"])
    ["html", "csv"]
    """
    if format_str == "all":
        return valid_formats.copy()
    elif "," in format_str:
        formats = [fmt.strip().lower() for fmt in format_str.split(",")]
        invalid_formats = [fmt for fmt in formats if fmt not in valid_formats]
        if invalid_formats:
            raise ValueError(
                f"Invalid formats: {invalid_formats}. Valid options: {valid_formats}"
            )
        return formats
    else:
        format_clean = format_str.strip().lower()
        if format_clean not in valid_formats:
            raise ValueError(
                f"Invalid format: {format_clean}. Valid options: {valid_formats}"
            )
        return [format_clean]


def _validate_bathymetry_params(args: Namespace) -> dict[str, Any]:
    """
    Validate and normalize bathymetry-related CLI parameters.

    Internal utility function for bathymetry parameter validation.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments containing bathymetry parameters

    Returns
    -------
    Dict[str, Any]
        Normalized bathymetry parameters

    Raises
    ------
    ValueError
        If bathymetry parameters are invalid

    Examples
    --------
    >>> args = argparse.Namespace(bathy_source="gebco2025", bathy_stride=5)
    >>> _validate_bathymetry_params(args)
    {'bathy_source': 'gebco2025', 'bathy_dir': 'data', 'bathy_stride': 5}
    """
    bathy_source = getattr(args, "bathy_source", "etopo2022")
    bathy_dir = getattr(args, "bathy_dir", "data")
    bathy_stride = getattr(args, "bathy_stride", 10)

    # Validate source
    valid_sources = ["etopo2022", "gebco2025"]
    if bathy_source not in valid_sources:
        raise ValueError(
            f"Invalid bathymetry source: {bathy_source}. Valid options: {valid_sources}"
        )

    # Validate stride
    if not isinstance(bathy_stride, int) or bathy_stride < 1:
        raise ValueError(
            f"Bathymetry stride must be a positive integer, got: {bathy_stride}"
        )

    return {
        "bathy_source": bathy_source,
        "bathy_dir": str(bathy_dir),
        "bathy_stride": bathy_stride,
    }


def _validate_output_params(
    args: Namespace, default_basename: str, suffix: str = "", extension: str = ""
) -> Path:
    """
    Validate and determine output file path from CLI arguments.

    Internal utility function for output path validation.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments containing output and output_dir
    default_basename : str
        Default base filename to use if --output is not provided
    suffix : str, optional
        Suffix to append to basename (e.g., "_enriched", "_schedule")
    extension : str, optional
        File extension including the dot (e.g., ".yaml", ".csv")

    Returns
    -------
    Path
        Validated output file path

    Raises
    ------
    ValueError
        If output parameters are invalid

    Examples
    --------
    >>> args = argparse.Namespace(output="myfile", output_dir="results/")
    >>> _validate_output_params(args, "cruise", "_enriched", ".yaml")
    PosixPath('results/myfile_enriched.yaml')
    """
    # Determine base filename
    if hasattr(args, "output") and args.output:
        base_name = args.output.replace(" ", "_")
    else:
        base_name = default_basename.replace(" ", "_")

    # Validate base_name
    if not base_name or not base_name.strip():
        raise ValueError("Output filename cannot be empty")

    # Construct full filename
    filename = f"{base_name}{suffix}{extension}"

    # Determine and validate output directory
    output_dir = getattr(args, "output_dir", Path("data"))
    validated_dir = _validate_directory_writable(Path(output_dir))

    return validated_dir / filename


def _validate_cli_config_file(args: Namespace) -> Path:
    """
    Validate config file from CLI arguments.

    Internal utility function for CLI config file validation.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments

    Returns
    -------
    Path
        Validated config file path

    Raises
    ------
    ValueError
        If config file is missing or invalid

    Examples
    --------
    >>> args = argparse.Namespace(config_file=Path("cruise.yaml"))
    >>> _validate_cli_config_file(args)
    PosixPath('/path/to/cruise.yaml')
    """
    if not hasattr(args, "config_file") or not args.config_file:
        raise ValueError("Configuration file is required for this command")

    return _validate_config_file(args.config_file)


def _validate_coordinate_args(args: Namespace) -> tuple[float, float, float, float]:
    """
    Validate coordinate bounds from CLI arguments.

    Internal utility function for CLI coordinate validation.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments containing lat and lon bounds

    Returns
    -------
    Tuple[float, float, float, float]
        Normalized bounds (min_lon, min_lat, max_lon, max_lat)

    Raises
    ------
    ValueError
        If coordinate arguments are invalid or missing

    Examples
    --------
    >>> args = argparse.Namespace(lat=[50.0, 60.0], lon=[-10.0, 10.0])
    >>> _validate_coordinate_args(args)
    (-10.0, 50.0, 10.0, 60.0)
    """
    if not hasattr(args, "lat") or not args.lat:
        raise ValueError("Latitude bounds (--lat) are required")

    if not hasattr(args, "lon") or not args.lon:
        raise ValueError("Longitude bounds (--lon) are required")

    return _validate_coordinate_bounds(args.lat, args.lon)


def _handle_deprecated_cli_params(
    args: Namespace, param_map: Optional[dict[str, str]] = None
) -> None:
    """
    Handle deprecated CLI parameters with warnings and migration.

    Internal utility function for deprecated parameter handling.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments
    param_map : Dict[str, str], optional
        Mapping of deprecated_param_name -> new_param_name.
        If None, no action is taken (useful for future-proofing).

    Examples
    --------
    >>> param_map = {'output_file': 'output', 'bathymetry_source': 'bathy_source'}
    >>> _handle_deprecated_cli_params(args, param_map)
    # Shows warnings and migrates deprecated parameters
    >>> _handle_deprecated_cli_params(args)  # No action taken
    """
    if param_map is None:
        return

    for old_param, new_param in param_map.items():
        if hasattr(args, old_param) and getattr(args, old_param) is not None:
            logger.warning(
                f"⚠️  WARNING: '--{old_param.replace('_', '-')}' is deprecated. "
                f"Use '--{new_param.replace('_', '-')}' instead."
            )
            # Migrate the value if new param isn't already set
            if not hasattr(args, new_param) or getattr(args, new_param) is None:
                setattr(args, new_param, getattr(args, old_param))


def _apply_cli_defaults(args: Namespace) -> None:
    """
    Apply standard CLI parameter defaults.

    Internal utility function for CLI default values.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments to apply defaults to

    Examples
    --------
    >>> _apply_cli_defaults(args)
    # Sets default values for common CLI parameters
    """
    # Apply bathymetry directory default
    if getattr(args, "bathy_dir", None) is None:
        args.bathy_dir = Path("data")

    # Apply output directory default
    if getattr(args, "output_dir", None) is None:
        args.output_dir = Path("data")


def _validate_choice_param(
    value: str, param_name: str, valid_choices: list[str]
) -> str:
    """
    Validate parameter value against allowed choices.

    Internal utility function for choice parameter validation.

    Parameters
    ----------
    value : str
        Parameter value to validate
    param_name : str
        Parameter name for error messages
    valid_choices : List[str]
        List of valid parameter values

    Returns
    -------
    str
        Validated parameter value

    Raises
    ------
    ValueError
        If value is not in valid choices

    Examples
    --------
    >>> _validate_choice_param("gebco2025", "bathy_source", ["etopo2022", "gebco2025"])
    'gebco2025'
    """
    if value not in valid_choices:
        raise ValueError(
            f"Invalid {param_name}: {value}. Valid options: {valid_choices}"
        )
    return value


def _validate_positive_int(value: int, param_name: str) -> int:
    """
    Validate parameter is a positive integer.

    Internal utility function for positive integer validation.

    Parameters
    ----------
    value : int
        Value to validate
    param_name : str
        Parameter name for error messages

    Returns
    -------
    int
        Validated integer value

    Raises
    ------
    ValueError
        If value is not a positive integer

    Examples
    --------
    >>> _validate_positive_int(5, "stride")
    5
    """
    if not isinstance(value, int) or value < 1:
        raise ValueError(f"{param_name} must be a positive integer, got: {value}")
    return value
