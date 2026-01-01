"""
Output formatting utilities for CLI commands.

This module provides internal utility functions for formatting and displaying
output from CLI commands. These functions ensure consistent presentation
across all CLI commands.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _format_timeline_summary(timeline: List[Dict], total_duration: float) -> str:
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


def _format_file_list(files: List[Path], base_dir: Optional[Path] = None) -> str:
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
    lat_range: Tuple[float, float], lon_range: Tuple[float, float]
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
    success: bool, errors: List[str], warnings: List[str]
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


def _format_size_summary(files: List[Path]) -> str:
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


def _format_operation_summary(operation: str, status: str, details: Dict = None) -> str:
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


def _format_table_row(columns: List[str], widths: List[int]) -> str:
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
