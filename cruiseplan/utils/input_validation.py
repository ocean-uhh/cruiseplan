"""
Input validation utilities for CLI commands.

This module provides internal utility functions for validating and processing
user inputs across CLI commands. These functions are used internally by the
CLI layer to validate inputs before passing them to the API layer.
"""

import logging
from pathlib import Path
from typing import List, Tuple

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
        raise ValueError(f"Directory is not writable: {resolved_path}. Error: {e}")

    return resolved_path


def _validate_coordinate_bounds(
    lat_bounds: List[float], lon_bounds: List[float]
) -> Tuple[float, float, float, float]:
    """
    Validate and normalize coordinate bounds to bbox format.

    Internal utility function for coordinate validation.

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

    if not (-90 <= min_lat <= 90):
        raise ValueError(
            f"Invalid minimum latitude: {min_lat}. Must be between -90 and 90."
        )

    if not (-90 <= max_lat <= 90):
        raise ValueError(
            f"Invalid maximum latitude: {max_lat}. Must be between -90 and 90."
        )

    if not (-180 <= min_lon <= 180):
        raise ValueError(
            f"Invalid minimum longitude: {min_lon}. Must be between -180 and 180."
        )

    if not (-180 <= max_lon <= 180):
        raise ValueError(
            f"Invalid maximum longitude: {max_lon}. Must be between -180 and 180."
        )

    # Validate logical ranges
    if min_lat >= max_lat:
        raise ValueError(
            f"Minimum latitude ({min_lat}) must be less than maximum latitude ({max_lat})"
        )

    if min_lon >= max_lon:
        raise ValueError(
            f"Minimum longitude ({min_lon}) must be less than maximum longitude ({max_lon})"
        )

    # Return in bbox format (min_lon, min_lat, max_lon, max_lat)
    return (min_lon, min_lat, max_lon, max_lat)


def _validate_file_extension(file_path: Path, allowed_extensions: List[str]) -> bool:
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
        raise ValueError(
            f"{name} must be a number, got {type(value).__name__}: {value}"
        )

    if not (min_val <= value <= max_val):
        raise ValueError(
            f"{name} must be between {min_val} and {max_val}, got: {value}"
        )

    return float(value)


def _validate_format_list(formats: List[str], valid_formats: List[str]) -> List[str]:
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


def _detect_pangaea_mode(args) -> Tuple[str, dict]:
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
