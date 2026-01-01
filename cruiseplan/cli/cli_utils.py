"""
Common utilities for CLI commands.

This module provides shared functionality across CLI modules including
file path validation, output directory management, progress indicators,
and error message formatting.
"""

import logging
import sys
import warnings as python_warnings
from argparse import Namespace
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cruiseplan.utils.yaml_io import YAMLIOError, load_yaml

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Custom exception for CLI-related errors."""

    pass


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Setup logging configuration for CLI commands.

    Parameters
    ----------
    verbose : bool, optional
        Enable verbose output. Default is False.
    quiet : bool, optional
        Suppress non-essential output. Default is False.
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="%(message)s", stream=sys.stdout)


def validate_input_file(file_path: Path, must_exist: bool = True) -> Path:
    """
    Validate input file path and ensure it exists.

    Parameters
    ----------
    file_path : Path
        Path to validate.
    must_exist : bool, optional
        Whether file must exist. Default is True.

    Returns
    -------
    Path
        Resolved and validated file path.

    Raises
    ------
    CLIError
        If file path is invalid or file doesn't exist when required.
    """
    resolved_path = file_path.resolve()

    if must_exist:
        if not resolved_path.exists():
            raise CLIError(f"Input file not found: {resolved_path}")

        if not resolved_path.is_file():
            raise CLIError(f"Path is not a file: {resolved_path}")

        if not resolved_path.stat().st_size:
            raise CLIError(f"Input file is empty: {resolved_path}")

    return resolved_path


def validate_output_path(
    output_dir: Optional[Path] = None,
    output_file: Optional[Path] = None,
    default_dir: Path = Path("."),
    default_filename: Optional[str] = None,
) -> Path:
    """
    Validate and resolve output path from directory and optional filename.

    Args:
        output_dir: Output directory path
        output_file: Specific output file path (overrides output_dir)
        default_dir: Default directory if none specified
        default_filename: Default filename to use with output_dir

    Returns
    -------
        Resolved output path

    Raises
    ------
        CLIError: If paths are invalid
    """
    if output_file:
        # Specific file path takes precedence
        output_path = output_file.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path

    if output_dir:
        resolved_dir = output_dir.resolve()
    else:
        resolved_dir = default_dir.resolve()

    # Create directory if it doesn't exist
    resolved_dir.mkdir(parents=True, exist_ok=True)

    if default_filename:
        return resolved_dir / default_filename
    else:
        return resolved_dir


def load_yaml_config(file_path: Path) -> dict:
    """
    Load and validate YAML configuration file.

    Args:
        file_path: Path to YAML file

    Returns
    -------
        Parsed YAML content

    Raises
    ------
        CLIError: If file cannot be loaded or parsed
    """
    try:
        return load_yaml(file_path)
    except YAMLIOError as e:
        raise CLIError(str(e)) from e


def save_yaml_config(config: dict, file_path: Path, backup: bool = True) -> None:
    """
    Save configuration to YAML file with optional backup.

    Args:
        config: Configuration dictionary to save
        file_path: Output file path
        backup: Whether to create backup of existing file

    Raises
    ------
        CLIError: If file cannot be written
    """
    from cruiseplan.utils.yaml_io import save_yaml

    try:
        save_yaml(config, file_path, backup=backup)
    except YAMLIOError as e:
        raise CLIError(str(e)) from e


def generate_output_filename(
    input_path: Path, suffix: str, extension: str = None
) -> str:
    """
    Generate output filename by adding suffix to input filename.

    Args:
        input_path: Input file path
        suffix: Suffix to add (e.g., "_with_depths")
        extension: New extension (defaults to input extension)

    Returns
    -------
        Generated filename
    """
    if extension is None:
        extension = input_path.suffix

    stem = input_path.stem
    return f"{stem}{suffix}{extension}"


def read_doi_list(file_path: Path) -> List[str]:
    """
    Read DOI list from text file, filtering out comments and empty lines.

    Args:
        file_path: Path to DOI list file

    Returns
    -------
        List of DOI strings

    Raises
    ------
        CLIError: If file cannot be read
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        dois = []
        for line_num, line in enumerate(lines, 1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Basic DOI format validation
            if not line.startswith(("10.", "doi:10.", "https://doi.org/10.")):
                logger.warning(f"Line {line_num}: '{line}' doesn't look like a DOI")

            dois.append(line)

        if not dois:
            raise CLIError(f"No valid DOIs found in {file_path}")

        logger.info(f"Loaded {len(dois)} DOIs from {file_path}")
        return dois

    except Exception as e:
        raise CLIError(f"Error reading DOI list from {file_path}: {e}")


def format_coordinate_bounds(lat_bounds: tuple, lon_bounds: tuple) -> str:
    """
    Format coordinate bounds for display.

    Args:
        lat_bounds: (min_lat, max_lat)
        lon_bounds: (min_lon, max_lon)

    Returns
    -------
        Formatted bounds string
    """
    return f"Lat: {lat_bounds[0]:.2f}° to {lat_bounds[1]:.2f}°, Lon: {lon_bounds[0]:.2f}° to {lon_bounds[1]:.2f}°"


def confirm_operation(message: str, default: bool = True) -> bool:
    """
    Prompt user for confirmation.

    Parameters
    ----------
    message : str
        Confirmation message.
    default : bool, optional
        Default response if user just presses enter. Default is True.

    Returns
    -------
    bool
        True if user confirms, False otherwise.
    """
    suffix = " [Y/n]" if default else " [y/N]"

    try:
        response = input(f"{message}{suffix}: ").strip().lower()

        if not response:
            return default

        return response in ["y", "yes", "true", "1"]

    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
        return False


def count_individual_warnings(warnings: List[str]) -> int:
    """
    Count individual warning messages from formatted warning groups.

    Parameters
    ----------
    warnings : List[str]
        List of formatted warning group strings.

    Returns
    -------
    int
        Total number of individual warning messages.
    """
    total_count = 0
    for warning_group in warnings:
        for line in warning_group.split("\n"):
            line = line.strip()
            # Count lines that start with "- " (individual warning items)
            if line.startswith("- "):
                total_count += 1
    return total_count


def display_user_warnings(
    warnings: List[str], title: str = "Configuration Warnings"
) -> None:
    """
    Display validation or configuration warnings in a consistent, user-friendly format.

    Parameters
    ----------
    warnings : List[str]
        List of warning messages to display.
    title : str, optional
        Title for the warning section (default: "Configuration Warnings").
    """
    if not warnings:
        return

    logger.warning(f"⚠️ {title}:")
    for warning_group in warnings:
        for line in warning_group.split("\n"):
            if line.strip():
                logger.warning(f"  {line}")
        logger.warning("")  # Add spacing between warning groups


@contextmanager
def capture_and_format_warnings():
    """
    Context manager to capture and format Pydantic warnings consistently.

    Captures Python warnings during execution and formats them in a user-friendly
    way instead of showing raw tracebacks. Use this around operations that might
    generate Pydantic validation warnings.

    Yields
    ------
    List[str]
        List of captured warning messages

    Example
    -------
    >>> with capture_and_format_warnings() as captured_warnings:
    ...     cruise = Cruise(config_file)  # May generate warnings
    >>> if captured_warnings:
    ...     display_user_warnings(captured_warnings, "Validation Warnings")
    """
    captured_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        # Extract just the warning message, ignore file paths and line numbers
        captured_warnings.append(str(message))

    # Set up warning capture
    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    try:
        yield captured_warnings
    finally:
        # Restore original warning handler
        python_warnings.showwarning = old_showwarning


def load_cruise_with_pretty_warnings(config_file):
    """
    Load a Cruise object with consistent warning formatting.

    This function wraps Cruise loading with warning capture to ensure
    any Pydantic validation warnings are displayed in a user-friendly
    format instead of showing raw Python warning tracebacks.

    Parameters
    ----------
    config_file : str or Path
        Path to the cruise configuration YAML file

    Returns
    -------
    Cruise
        Loaded cruise object

    Raises
    ------
    CLIError
        If cruise loading fails
    """
    from cruiseplan.core.cruise import Cruise

    try:
        with capture_and_format_warnings() as captured_warnings:
            cruise = Cruise(config_file)

        # Display any captured warnings in pretty format
        if captured_warnings:
            display_user_warnings(captured_warnings, "Configuration Warnings")

        return cruise

    except Exception as e:
        raise CLIError(f"Failed to load cruise configuration: {e}") from e


def determine_output_path(
    args, default_basename: str, suffix: str = "", extension: str = ""
) -> Path:
    """
    Determine output file path from CLI arguments following the standard pattern.

    This utility handles the common --output + --output-dir pattern used across
    multiple CLI commands, providing consistent behavior for output file naming.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments containing output and output_dir.
    default_basename : str
        Default base filename to use if --output is not provided.
    suffix : str, optional
        Suffix to append to basename (e.g., "_enriched", "_schedule"). Default "".
    extension : str, optional
        File extension including the dot (e.g., ".yaml", ".csv"). Default "".

    Returns
    -------
    Path
        Complete output file path.

    Examples
    --------
    >>> # With --output myfile --output-dir results/
    >>> determine_output_path(args, "cruise", "_enriched", ".yaml")
    Path("results/myfile_enriched.yaml")

    >>> # Without --output, using default
    >>> determine_output_path(args, "My_Cruise", "_schedule", ".csv")
    Path("data/My_Cruise_schedule.csv")
    """
    # Determine base filename
    if hasattr(args, "output") and args.output:
        base_name = args.output.replace(" ", "_")
    else:
        base_name = default_basename.replace(" ", "_")

    # Construct full filename
    filename = f"{base_name}{suffix}{extension}"

    # Determine output directory
    output_dir = getattr(args, "output_dir", Path("data"))

    return Path(output_dir) / filename


# ============================================================================
# Phase 1 Refactoring: New Utility Functions for API-First CLI Architecture
# ============================================================================


def _parse_format_options(format_str: str, valid_formats: List[str]) -> List[str]:
    """
    Unified format string parsing for CLI commands.

    Internal utility function to handle 'all', comma-separated lists, and single formats.

    Parameters
    ----------
    format_str : str
        Format string from user input ("all", "html,csv", "netcdf", etc.)
    valid_formats : List[str]
        List of valid format options

    Returns
    -------
    List[str]
        List of format strings to process

    Examples
    --------
    >>> _parse_format_options("all", ["html", "csv", "netcdf"])
    ["html", "csv", "netcdf"]
    >>> _parse_format_options("html,csv", ["html", "csv", "netcdf"])
    ["html", "csv"]
    """
    if format_str == "all":
        return valid_formats.copy()
    elif "," in format_str:
        formats = [fmt.strip().lower() for fmt in format_str.split(",")]
        # Validate formats
        invalid_formats = [fmt for fmt in formats if fmt not in valid_formats]
        if invalid_formats:
            raise CLIError(
                f"Invalid formats: {invalid_formats}. Valid options: {valid_formats}"
            )
        return formats
    else:
        format_clean = format_str.strip().lower()
        if format_clean not in valid_formats:
            raise CLIError(
                f"Invalid format: {format_clean}. Valid options: {valid_formats}"
            )
        return [format_clean]


def _handle_deprecated_params(args: Namespace, param_map: Dict[str, str]) -> None:
    """
    Centralized deprecation warnings and parameter migration.

    Internal utility to handle deprecated CLI parameters consistently across commands.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments
    param_map : Dict[str, str]
        Mapping of deprecated_param_name -> new_param_name

    Examples
    --------
    >>> _handle_deprecated_params(args, {'output_file': 'output'})
    # Shows warning and migrates args.output_file -> args.output
    """
    for old_param, new_param in param_map.items():
        if hasattr(args, old_param) and getattr(args, old_param) is not None:
            logger.warning(
                f"⚠️  WARNING: '--{old_param.replace('_', '-')}' is deprecated. "
                f"Use '--{new_param.replace('_', '-')}' instead."
            )
            # Migrate the value if new param isn't already set
            if not hasattr(args, new_param) or getattr(args, new_param) is None:
                setattr(args, new_param, getattr(args, old_param))


def _validate_bathymetry_params(args: Namespace) -> Dict[str, Any]:
    """
    Common bathymetry parameter validation and normalization.

    Internal utility to validate and normalize bathymetry-related parameters.

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
    CLIError
        If bathymetry parameters are invalid
    """
    # Handle legacy parameter names
    _handle_deprecated_params(
        args,
        {
            "bathymetry_source_legacy": "bathy_source",
            "bathymetry_dir_legacy": "bathy_dir",
            "bathymetry_stride_legacy": "bathy_stride",
        },
    )

    bathy_source = getattr(args, "bathy_source", "etopo2022")
    bathy_dir = getattr(args, "bathy_dir", "data")
    bathy_stride = getattr(args, "bathy_stride", 10)

    # Validate source
    valid_sources = ["etopo2022", "gebco2025"]
    if bathy_source not in valid_sources:
        raise CLIError(
            f"Invalid bathymetry source: {bathy_source}. Valid options: {valid_sources}"
        )

    # Validate stride
    if not isinstance(bathy_stride, int) or bathy_stride < 1:
        raise CLIError(
            f"Bathymetry stride must be a positive integer, got: {bathy_stride}"
        )

    return {
        "bathy_source": bathy_source,
        "bathy_dir": str(bathy_dir),
        "bathy_stride": bathy_stride,
    }


def _setup_output_strategy(config_file: Path, args: Namespace) -> Tuple[Path, str]:
    """
    Unified output path and basename resolution for CLI commands.

    Internal utility to handle output directory and filename strategies consistently.

    Parameters
    ----------
    config_file : Path
        Input configuration file path
    args : Namespace
        Parsed command line arguments

    Returns
    -------
    Tuple[Path, str]
        (output_directory_path, base_filename)
    """
    # Determine output directory
    output_dir = Path(getattr(args, "output_dir", "data"))
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine base filename
    if hasattr(args, "output") and args.output:
        base_name = args.output.replace(" ", "_")
    else:
        base_name = config_file.stem.replace(" ", "_")

    return output_dir, base_name


def _format_success_message(
    operation: str, files: List[Path], duration: Optional[float] = None
) -> None:
    """
    Consistent success reporting across CLI commands.

    Internal utility for standardized success message formatting.

    Parameters
    ----------
    operation : str
        Name of the operation that completed
    files : List[Path]
        List of generated files to display
    duration : Optional[float]
        Operation duration in seconds
    """
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"{operation} Complete")
    logger.info("=" * 60)

    if files:
        logger.info("📁 Generated files:")
        for file_path in files:
            # Show relative path if under current directory
            try:
                rel_path = file_path.relative_to(Path.cwd())
                logger.info(f"  • {rel_path}")
            except ValueError:
                logger.info(f"  • {file_path}")

    if duration is not None:
        logger.info(f"⏱️  Duration: {_format_duration_seconds(duration)}")

    logger.info("")
    logger.info(f"✅ {operation} successful!")


def _format_error_message(
    operation: str, error: Exception, suggestions: List[str] = None
) -> None:
    """
    Consistent error reporting with actionable suggestions.

    Internal utility for standardized error message formatting.

    Parameters
    ----------
    operation : str
        Name of the operation that failed
    error : Exception
        The exception that occurred
    suggestions : List[str], optional
        List of suggested actions for the user
    """
    logger.error("")
    logger.error("=" * 60)
    logger.error(f"{operation} Failed")
    logger.error("=" * 60)
    logger.error(f"❌ Error: {error}")

    if suggestions:
        logger.error("")
        logger.error("💡 Suggestions:")
        for suggestion in suggestions:
            logger.error(f"  • {suggestion}")

    logger.error("")


def _format_progress_header(operation: str, config_file: Path, **kwargs) -> None:
    """
    Standardized operation header display for CLI commands.

    Internal utility to show consistent progress headers.

    Parameters
    ----------
    operation : str
        Name of the operation starting
    config_file : Path
        Input configuration file
    **kwargs
        Additional context to display (formats, leg, etc.)
    """
    logger.info("=" * 60)
    logger.info(f"{operation}")
    logger.info("=" * 60)
    logger.info(f"Configuration: {config_file}")

    for key, value in kwargs.items():
        if value is not None:
            # Format key name nicely
            display_key = key.replace("_", " ").title()
            logger.info(f"{display_key}: {value}")

    logger.info("")


def _format_duration_seconds(seconds: float) -> str:
    """
    Convert seconds to human-readable duration format.

    Internal utility for duration formatting.

    Parameters
    ----------
    seconds : float
        Duration in seconds

    Returns
    -------
    str
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def _collect_generated_files(
    result: Any, base_patterns: List[str] = None
) -> List[Path]:
    """
    Extract file paths from API responses.

    Internal utility to handle different API response formats and extract file lists.

    Parameters
    ----------
    result : Any
        API response that may contain file paths
    base_patterns : List[str], optional
        Base filename patterns to look for

    Returns
    -------
    List[Path]
        List of generated file paths
    """
    files = []

    if isinstance(result, Path):
        files.append(result)
    elif isinstance(result, list):
        for item in result:
            if isinstance(item, Path):
                files.append(item)
    elif isinstance(result, tuple) and len(result) >= 2:
        # Handle (data, files) tuple returns
        potential_files = result[1]
        if isinstance(potential_files, list):
            files.extend([Path(f) for f in potential_files if f is not None])

    return files


def _setup_cli_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Enhanced logging setup for new CLI architecture.

    Internal utility that wraps setup_logging with additional configuration.

    Parameters
    ----------
    verbose : bool
        Enable verbose output
    quiet : bool
        Suppress non-essential output
    """
    setup_logging(verbose, quiet)

    # Additional setup for API-first architecture
    if verbose:
        # Ensure API-level logging is also visible
        api_logger = logging.getLogger("cruiseplan")
        api_logger.setLevel(logging.DEBUG)
