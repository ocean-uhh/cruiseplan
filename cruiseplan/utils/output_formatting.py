"""
Output formatting utilities for CLI commands.

This module provides internal utility functions for formatting and displaying
output from CLI commands. These functions ensure consistent presentation
across all CLI commands.
"""

import logging
from argparse import Namespace
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _format_timeline_summary(timeline: list[dict], total_duration: float) -> str:
    """
    Format timeline statistics for display.

    Internal utility function to create consistent timeline summaries.

    Parameters
    ----------
    timeline : List[Dict]
        Timeline activity records
    total_duration : float
        Total duration in hours

    Returns
    -------
    str
        Formatted timeline summary

    Examples
    --------
    >>> activities = [{'label': 'STN_001', 'duration_minutes': 120}]
    >>> _format_timeline_summary(activities, 24.5)
    'Timeline: 1 activities, 24.5 hours total duration'
    """
    activity_count = len(timeline)

    # Calculate activity type breakdown
    activity_types = {}
    for activity in timeline:
        op_type = activity.get("op_type", "unknown")
        activity_types[op_type] = activity_types.get(op_type, 0) + 1

    summary_parts = [
        f"Timeline: {activity_count} activities",
        f"{total_duration:.1f} hours total duration",
    ]

    if activity_types:
        type_summary = ", ".join(
            [f"{count} {op_type}" for op_type, count in activity_types.items()]
        )
        summary_parts.append(f"Types: {type_summary}")

    return " | ".join(summary_parts)


def _format_file_list(files: list[Path], base_dir: Optional[Path] = None) -> str:
    """
    Format generated file list with relative paths.

    Internal utility function for consistent file list display.

    Parameters
    ----------
    files : List[Path]
        List of file paths to format
    base_dir : Optional[Path]
        Base directory for relative path calculation

    Returns
    -------
    str
        Formatted file list string

    Examples
    --------
    >>> files = [Path("/data/cruise_map.png"), Path("/data/cruise.csv")]
    >>> _format_file_list(files, Path("/data"))
    '• cruise_map.png\\n• cruise.csv'
    """
    if not files:
        return "No files generated"

    if base_dir is None:
        base_dir = Path.cwd()

    formatted_files = []
    for file_path in files:
        try:
            # Try to show relative path
            rel_path = file_path.relative_to(base_dir)
            formatted_files.append(f"• {rel_path}")
        except ValueError:
            # Fall back to absolute path if not under base_dir
            formatted_files.append(f"• {file_path}")

    return "\\n".join(formatted_files)


def _format_duration(minutes: float) -> str:
    """
    Convert minutes to human-readable duration.

    Internal utility function for duration formatting.

    Parameters
    ----------
    minutes : float
        Duration in minutes

    Returns
    -------
    str
        Human-readable duration string

    Examples
    --------
    >>> _format_duration(90.5)
    '1h 31m'
    >>> _format_duration(45)
    '45m'
    >>> _format_duration(1.5)
    '2m'
    """
    if minutes < 60:
        return f"{int(round(minutes))}m"

    hours = int(minutes // 60)
    remaining_minutes = int(round(minutes % 60))

    if remaining_minutes == 0:
        return f"{hours}h"
    else:
        return f"{hours}h {remaining_minutes}m"


def _format_coordinate_summary(
    lat_range: tuple[float, float], lon_range: tuple[float, float]
) -> str:
    """
    Format coordinate bounds for display.

    Internal utility function for coordinate range formatting.

    Parameters
    ----------
    lat_range : Tuple[float, float]
        (min_latitude, max_latitude)
    lon_range : Tuple[float, float]
        (min_longitude, max_longitude)

    Returns
    -------
    str
        Formatted coordinate summary

    Examples
    --------
    >>> _format_coordinate_summary((50.0, 60.0), (-10.0, 10.0))
    'Coordinates: 50.0°N to 60.0°N, 10.0°W to 10.0°E'
    """
    min_lat, max_lat = lat_range
    min_lon, max_lon = lon_range

    # Format latitude
    if min_lat >= 0 and max_lat >= 0:
        lat_str = f"{min_lat:.1f}°N to {max_lat:.1f}°N"
    elif min_lat < 0 and max_lat < 0:
        lat_str = f"{abs(max_lat):.1f}°S to {abs(min_lat):.1f}°S"
    else:
        lat_str = f"{abs(min_lat):.1f}°S to {max_lat:.1f}°N"

    # Format longitude
    if min_lon >= 0 and max_lon >= 0:
        lon_str = f"{min_lon:.1f}°E to {max_lon:.1f}°E"
    elif min_lon < 0 and max_lon < 0:
        lon_str = f"{abs(max_lon):.1f}°W to {abs(min_lon):.1f}°W"
    else:
        lon_str = f"{abs(min_lon):.1f}°W to {max_lon:.1f}°E"

    return f"Coordinates: {lat_str}, {lon_str}"


def _format_validation_results(
    success: bool, errors: list[str], warnings: list[str]
) -> str:
    """
    Format validation results with appropriate icons and colors.

    Internal utility function for validation result formatting.

    Parameters
    ----------
    success : bool
        Whether validation passed
    errors : List[str]
        List of error messages
    warnings : List[str]
        List of warning messages

    Returns
    -------
    str
        Formatted validation summary
    """
    if success and not warnings:
        return "✅ All validations passed - configuration is valid!"
    elif success and warnings:
        return f"✅ Validation passed with {len(warnings)} warnings"
    else:
        error_count = len(errors)
        warning_count = len(warnings)

        parts = [f"❌ Validation failed with {error_count} errors"]
        if warning_count > 0:
            parts.append(f"and {warning_count} warnings")

        return " ".join(parts)


def _format_progress_bar(current: int, total: int, description: str = "") -> str:
    """
    Simple progress bar for long operations.

    Internal utility function for progress indication.

    Parameters
    ----------
    current : int
        Current progress value
    total : int
        Total expected value
    description : str, optional
        Description text

    Returns
    -------
    str
        Formatted progress bar string

    Examples
    --------
    >>> _format_progress_bar(7, 10, "Processing")
    'Processing: [#######...] 70% (7/10)'
    """
    if total == 0:
        return f"{description}: 100%" if description else "100%"

    percentage = min(100, (current * 100) // total)
    bar_length = 20
    filled_length = (current * bar_length) // total

    bar = "#" * filled_length + "." * (bar_length - filled_length)

    if description:
        return f"{description}: [{bar}] {percentage}% ({current}/{total})"
    else:
        return f"[{bar}] {percentage}% ({current}/{total})"


def _format_size_summary(files: list[Path]) -> str:
    """
    Format file size summary for generated files.

    Internal utility function for file size reporting.

    Parameters
    ----------
    files : List[Path]
        List of generated files

    Returns
    -------
    str
        Formatted size summary
    """
    if not files:
        return "No files generated"

    total_size = 0
    file_count = 0

    for file_path in files:
        if file_path.exists():
            total_size += file_path.stat().st_size
            file_count += 1

    if file_count == 0:
        return "Files not found"

    # Format size in appropriate units
    if total_size < 1024:
        size_str = f"{total_size} bytes"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.1f} KB"
    elif total_size < 1024 * 1024 * 1024:
        size_str = f"{total_size / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{total_size / (1024 * 1024 * 1024):.1f} GB"

    return f"{file_count} files, {size_str} total"


def _format_operation_summary(operation: str, status: str, details: dict = None) -> str:
    """
    Format operation summary with status and details.

    Internal utility function for operation status reporting.

    Parameters
    ----------
    operation : str
        Name of the operation
    status : str
        Status ('success', 'warning', 'error')
    details : Dict, optional
        Additional details to include

    Returns
    -------
    str
        Formatted operation summary
    """
    icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}

    icon = icons.get(status, "•")
    summary = f"{icon} {operation}: {status.title()}"

    if details:
        detail_parts = []
        for key, value in details.items():
            if value is not None:
                detail_parts.append(f"{key}={value}")

        if detail_parts:
            summary += f" ({', '.join(detail_parts)})"

    return summary


def _format_table_row(columns: list[str], widths: list[int]) -> str:
    """
    Format a table row with fixed column widths.

    Internal utility function for tabular output.

    Parameters
    ----------
    columns : List[str]
        Column values
    widths : List[int]
        Column widths

    Returns
    -------
    str
        Formatted table row
    """
    formatted_columns = []

    for i, (content, width) in enumerate(zip(columns, widths)):
        if len(content) > width:
            content = content[: width - 3] + "..."
        formatted_columns.append(content.ljust(width))

    return " | ".join(formatted_columns)


def _format_section_header(title: str, width: int = 60) -> str:
    """
    Format section header with consistent styling.

    Internal utility function for section headers.

    Parameters
    ----------
    title : str
        Section title
    width : int, optional
        Total width of header

    Returns
    -------
    str
        Formatted section header
    """
    if len(title) > width - 4:
        title = title[: width - 7] + "..."

    padding = (width - len(title) - 2) // 2
    return f"{'=' * padding} {title} {'=' * padding}"


# ============================================================================
# Standardized Output Path Management
# ============================================================================


def _determine_output_basename(args: Namespace, cruise_name: str = None) -> str:
    """
    Determine base filename from CLI arguments or cruise configuration.

    Internal utility function for consistent basename determination.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments
    cruise_name : str, optional
        Cruise name from configuration as fallback

    Returns
    -------
    str
        Base filename with spaces replaced by underscores

    Examples
    --------
    >>> args = argparse.Namespace(output="myfile")
    >>> _determine_output_basename(args)
    'myfile'
    >>> args = argparse.Namespace()
    >>> _determine_output_basename(args, "My Cruise")
    'My_Cruise'
    """
    if hasattr(args, "output") and args.output:
        return args.output.replace(" ", "_")
    elif cruise_name:
        return cruise_name.replace(" ", "_")
    else:
        return "cruise_output"


def _determine_output_directory(args: Namespace) -> Path:
    """
    Determine output directory from CLI arguments.

    Internal utility function for consistent output directory determination.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments

    Returns
    -------
    Path
        Output directory path

    Examples
    --------
    >>> args = argparse.Namespace(output_dir="results")
    >>> _determine_output_directory(args)
    PosixPath('results')
    """
    return Path(getattr(args, "output_dir", "data"))


def _construct_output_path(
    base_name: str,
    output_dir: Path,
    suffix: str = "",
    extension: str = "",
    format_specific: str = None,
) -> Path:
    """
    Construct complete output file path with consistent naming.

    Internal utility function for output path construction.

    Parameters
    ----------
    base_name : str
        Base filename
    output_dir : Path
        Output directory
    suffix : str, optional
        Suffix to append (e.g., "_enriched", "_schedule")
    extension : str, optional
        File extension including dot (e.g., ".yaml", ".csv")
    format_specific : str, optional
        Format-specific suffix (e.g., "_html", "_netcdf")

    Returns
    -------
    Path
        Complete output file path

    Examples
    --------
    >>> _construct_output_path("cruise", Path("data"), "_enriched", ".yaml")
    PosixPath('data/cruise_enriched.yaml')
    >>> _construct_output_path("cruise", Path("data"), "_schedule", ".html", "_timeline")
    PosixPath('data/cruise_schedule_timeline.html')
    """
    # Build filename components
    components = [base_name]

    if suffix:
        components.append(suffix)

    if format_specific:
        components.append(format_specific)

    filename = "".join(components) + extension

    return output_dir / filename


def _generate_multi_format_paths(
    base_name: str,
    output_dir: Path,
    formats: list[str],
    suffix: str = "",
    format_extensions: dict[str, str] = None,
) -> dict[str, Path]:
    """
    Generate output paths for multiple formats.

    Internal utility function for multi-format output path generation.

    Parameters
    ----------
    base_name : str
        Base filename
    output_dir : Path
        Output directory
    formats : List[str]
        List of output formats
    suffix : str, optional
        Common suffix for all formats
    format_extensions : Dict[str, str], optional
        Format-specific file extensions

    Returns
    -------
    Dict[str, Path]
        Mapping of format -> output path

    Examples
    --------
    >>> paths = _generate_multi_format_paths(
    ...     "cruise", Path("data"), ["html", "csv"], "_schedule",
    ...     {"html": ".html", "csv": ".csv"}
    ... )
    >>> paths["html"]
    PosixPath('data/cruise_schedule.html')
    """
    if format_extensions is None:
        format_extensions = {
            "html": ".html",
            "csv": ".csv",
            "netcdf": ".nc",
            "yaml": ".yaml",
            "json": ".json",
            "png": ".png",
            "pdf": ".pdf",
        }

    output_paths = {}

    for fmt in formats:
        extension = format_extensions.get(fmt, f".{fmt}")
        output_paths[fmt] = _construct_output_path(
            base_name, output_dir, suffix, extension
        )

    return output_paths


def _validate_output_directory(
    output_dir: Path, create_if_missing: bool = True
) -> Path:
    """
    Validate and prepare output directory.

    Internal utility function for output directory validation.

    Parameters
    ----------
    output_dir : Path
        Output directory to validate
    create_if_missing : bool, optional
        Create directory if it doesn't exist

    Returns
    -------
    Path
        Validated output directory

    Raises
    ------
    ValueError
        If directory validation fails
    """
    from cruiseplan.utils.input_validation import _validate_directory_writable

    return _validate_directory_writable(output_dir, create_if_missing)


def _standardize_output_setup(
    args: Namespace,
    cruise_name: str = None,
    suffix: str = "",
    single_format: str = None,
    multi_formats: list[str] = None,
) -> tuple[Path, str, dict[str, Path]]:
    """
    Complete standardized output setup for CLI commands.

    Internal utility function that combines all output path logic.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments
    cruise_name : str, optional
        Cruise name for default basename
    suffix : str, optional
        Common suffix for output files
    single_format : str, optional
        Single format extension (e.g., ".yaml")
    multi_formats : List[str], optional
        Multiple formats for generation

    Returns
    -------
    Tuple[Path, str, Dict[str, Path]]
        (output_directory, base_name, format_paths)

    Examples
    --------
    >>> args = argparse.Namespace(output="cruise", output_dir="data")
    >>> dir_path, basename, paths = _standardize_output_setup(
    ...     args, suffix="_enriched", single_format=".yaml"
    ... )
    >>> paths["single"]
    PosixPath('data/cruise_enriched.yaml')
    """
    # Determine base components
    base_name = _determine_output_basename(args, cruise_name)
    output_dir = _determine_output_directory(args)

    # Validate output directory
    validated_dir = _validate_output_directory(output_dir)

    # Generate format paths
    format_paths = {}

    if single_format:
        format_paths["single"] = _construct_output_path(
            base_name, validated_dir, suffix, single_format
        )

    if multi_formats:
        multi_paths = _generate_multi_format_paths(
            base_name, validated_dir, multi_formats, suffix
        )
        format_paths.update(multi_paths)

    return validated_dir, base_name, format_paths


def _format_output_summary(
    generated_files: list[Path], operation: str, include_size: bool = True
) -> str:
    """
    Format standardized output summary for CLI commands.

    Internal utility function for consistent output reporting.

    Parameters
    ----------
    generated_files : List[Path]
        List of generated output files
    operation : str
        Operation name for summary
    include_size : bool, optional
        Include file size information

    Returns
    -------
    str
        Formatted output summary

    Examples
    --------
    >>> files = [Path("data/cruise_enriched.yaml")]
    >>> _format_output_summary(files, "Configuration enrichment")
    '✅ Configuration enrichment completed:\n• cruise_enriched.yaml\n1 files, 1.2 KB total'
    """
    if not generated_files:
        return f"❌ {operation} failed - no files generated"

    # Filter to existing files
    existing_files = [f for f in generated_files if f.exists()]

    if not existing_files:
        return f"❌ {operation} failed - output files not found"

    # Format success message
    parts = [f"✅ {operation} completed:"]

    # Add file list
    file_list = _format_file_list(existing_files)
    parts.append(file_list)

    # Add size summary if requested
    if include_size:
        size_summary = _format_size_summary(existing_files)
        parts.append(size_summary)

    return "\n".join(parts)


# ============================================================================
# Standardized Error Message Formatting
# ============================================================================


def _format_cli_error(
    operation: str,
    error: Exception,
    context: dict[str, Any] = None,
    suggestions: list[str] = None,
) -> str:
    """
    Format CLI error messages with consistent structure.

    Internal utility function for standardized error formatting.

    Parameters
    ----------
    operation : str
        Name of the operation that failed
    error : Exception
        The exception that occurred
    context : Dict[str, Any], optional
        Additional context information
    suggestions : List[str], optional
        List of suggestions to help user resolve the issue

    Returns
    -------
    str
        Formatted error message

    Examples
    --------
    >>> _format_cli_error("Configuration loading", FileNotFoundError("file.yaml"))
    '❌ Configuration loading failed: file.yaml'
    """
    parts = [f"❌ {operation} failed: {error}"]

    if context:
        context_parts = []
        for key, value in context.items():
            if value is not None:
                context_parts.append(f"{key}: {value}")

        if context_parts:
            parts.append(f"Context: {', '.join(context_parts)}")

    if suggestions:
        parts.append("Suggestions:")
        for suggestion in suggestions:
            parts.append(f"  • {suggestion}")

    return "\n".join(parts)


def _format_cli_warning(
    operation: str, message: str, details: dict[str, Any] = None
) -> str:
    """
    Format CLI warning messages with consistent structure.

    Internal utility function for standardized warning formatting.

    Parameters
    ----------
    operation : str
        Name of the operation or context
    message : str
        Warning message
    details : Dict[str, Any], optional
        Additional details about the warning

    Returns
    -------
    str
        Formatted warning message

    Examples
    --------
    >>> _format_cli_warning("Parameter validation", "Using deprecated parameter")
    '⚠️ Parameter validation: Using deprecated parameter'
    """
    parts = [f"⚠️ {operation}: {message}"]

    if details:
        detail_parts = []
        for key, value in details.items():
            if value is not None:
                detail_parts.append(f"{key}={value}")

        if detail_parts:
            parts.append(f"({', '.join(detail_parts)})")

    return " ".join(parts)


def _format_validation_error(
    validation_type: str,
    field_name: str,
    error_message: str,
    current_value: Any = None,
    expected_format: str = None,
) -> str:
    """
    Format validation error messages with consistent structure.

    Internal utility function for validation error formatting.

    Parameters
    ----------
    validation_type : str
        Type of validation (e.g., "Parameter", "Configuration", "File")
    field_name : str
        Name of the field that failed validation
    error_message : str
        Detailed error message
    current_value : Any, optional
        Current value that failed validation
    expected_format : str, optional
        Expected format or value description

    Returns
    -------
    str
        Formatted validation error message

    Examples
    --------
    >>> _format_validation_error("Parameter", "bathy_stride", "must be positive", 0, "integer > 0")
    '❌ Parameter validation failed: bathy_stride must be positive\nCurrent value: 0\nExpected: integer > 0'
    """
    parts = [f"❌ {validation_type} validation failed: {field_name} {error_message}"]

    if current_value is not None:
        parts.append(f"Current value: {current_value}")

    if expected_format:
        parts.append(f"Expected: {expected_format}")

    return "\n".join(parts)


def _format_file_operation_error(
    operation: str,
    file_path: Path,
    error: Exception,
    recovery_suggestions: list[str] = None,
) -> str:
    """
    Format file operation error messages with consistent structure.

    Internal utility function for file operation error formatting.

    Parameters
    ----------
    operation : str
        File operation name (e.g., "Reading", "Writing", "Creating")
    file_path : Path
        Path to the file that caused the error
    error : Exception
        The exception that occurred
    recovery_suggestions : List[str], optional
        Suggestions for resolving the issue

    Returns
    -------
    str
        Formatted file operation error message

    Examples
    --------
    >>> _format_file_operation_error("Reading", Path("config.yaml"), FileNotFoundError())
    '❌ File operation failed: Reading config.yaml\nError: [Errno 2] No such file or directory'
    """
    parts = [f"❌ File operation failed: {operation} {file_path}", f"Error: {error}"]

    if recovery_suggestions:
        parts.append("Suggestions:")
        for suggestion in recovery_suggestions:
            parts.append(f"  • {suggestion}")

    return "\n".join(parts)


def _format_configuration_error(
    config_file: Path, section: str, error_details: list[str], line_number: int = None
) -> str:
    """
    Format configuration error messages with consistent structure.

    Internal utility function for configuration error formatting.

    Parameters
    ----------
    config_file : Path
        Path to the configuration file
    section : str
        Configuration section that contains the error
    error_details : List[str]
        List of specific error messages
    line_number : int, optional
        Line number where error occurred

    Returns
    -------
    str
        Formatted configuration error message

    Examples
    --------
    >>> errors = ["Missing required field: cruise_name", "Invalid port reference"]
    >>> _format_configuration_error(Path("cruise.yaml"), "cruise", errors, 15)
    '❌ Configuration error in cruise.yaml (cruise section, line 15):\n  • Missing required field: cruise_name\n  • Invalid port reference'
    """
    location_parts = [f"{config_file}", f"{section} section"]
    if line_number:
        location_parts.append(f"line {line_number}")

    location = " (".join(location_parts) + ")" * (len(location_parts) - 1)

    parts = [f"❌ Configuration error in {location}:"]

    for error in error_details:
        parts.append(f"  • {error}")

    return "\n".join(parts)


def _format_api_error(
    api_operation: str,
    service: str,
    error: Exception,
    status_code: int = None,
    retry_suggestion: bool = True,
) -> str:
    """
    Format API error messages with consistent structure.

    Internal utility function for API error formatting.

    Parameters
    ----------
    api_operation : str
        API operation that failed
    service : str
        Name of the service or API
    error : Exception
        The exception that occurred
    status_code : int, optional
        HTTP status code if applicable
    retry_suggestion : bool, optional
        Whether to suggest retrying the operation

    Returns
    -------
    str
        Formatted API error message

    Examples
    --------
    >>> _format_api_error("Data download", "PANGAEA", ConnectionError(), 503)
    '❌ API operation failed: Data download from PANGAEA\nError: Connection error\nStatus: 503\nSuggestion: Check network connection and retry'
    """
    parts = [
        f"❌ API operation failed: {api_operation} from {service}",
        f"Error: {error}",
    ]

    if status_code:
        parts.append(f"Status: {status_code}")

    if retry_suggestion:
        if status_code and status_code >= 500:
            parts.append("Suggestion: Server error - try again later")
        else:
            parts.append("Suggestion: Check network connection and retry")

    return "\n".join(parts)


def _format_processing_error(
    processing_stage: str,
    input_data: str,
    error: Exception,
    partial_results: bool = False,
) -> str:
    """
    Format data processing error messages with consistent structure.

    Internal utility function for processing error formatting.

    Parameters
    ----------
    processing_stage : str
        Stage of processing that failed
    input_data : str
        Description of input data being processed
    error : Exception
        The exception that occurred
    partial_results : bool, optional
        Whether partial results are available

    Returns
    -------
    str
        Formatted processing error message

    Examples
    --------
    >>> _format_processing_error("Station enrichment", "cruise.yaml", ValueError("Invalid coordinates"))
    '❌ Processing failed: Station enrichment of cruise.yaml\nError: Invalid coordinates'
    """
    parts = [
        f"❌ Processing failed: {processing_stage} of {input_data}",
        f"Error: {error}",
    ]

    if partial_results:
        parts.append("⚠️ Note: Partial results may be available in output directory")

    return "\n".join(parts)


def _format_dependency_error(
    missing_dependency: str, operation: str, install_command: str = None
) -> str:
    """
    Format dependency error messages with consistent structure.

    Internal utility function for dependency error formatting.

    Parameters
    ----------
    missing_dependency : str
        Name of the missing dependency
    operation : str
        Operation that requires the dependency
    install_command : str, optional
        Command to install the missing dependency

    Returns
    -------
    str
        Formatted dependency error message

    Examples
    --------
    >>> _format_dependency_error("netCDF4", "NetCDF export", "pip install netCDF4")
    '❌ Dependency error: netCDF4 required for NetCDF export\nInstall with: pip install netCDF4'
    """
    parts = [f"❌ Dependency error: {missing_dependency} required for {operation}"]

    if install_command:
        parts.append(f"Install with: {install_command}")

    return "\n".join(parts)
