"""
Output formatting utilities for CLI commands.

This module provides essential utility functions for formatting and displaying
output from CLI commands, focusing only on functions that are actually used
in the codebase.
"""

from datetime import datetime
from typing import Any, Optional


def round_time_to_minute(dt: datetime) -> datetime:
    """
    Round datetime to nearest minute.

    Utility function for standardizing time formatting by removing
    seconds and microseconds components for clean output display.

    Parameters
    ----------
    dt : datetime
        Input datetime

    Returns
    -------
    datetime
        Datetime rounded to nearest minute

    Examples
    --------
    >>> from datetime import datetime
    >>> round_time_to_minute(datetime(2023, 1, 1, 12, 30, 45))
    datetime(2023, 1, 1, 12, 30)
    """
    return dt.replace(second=0, microsecond=0)


def format_cli_error(
    operation: str,
    error: Exception,
    context: Optional[dict[str, Any]] = None,
    suggestions: Optional[list[str]] = None,
) -> str:
    """
    Format CLI error messages with consistent structure.

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
    >>> format_cli_error("Configuration loading", FileNotFoundError("file.yaml"))
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


def format_dependency_error(
    missing_dependency: str, operation: str, install_command: Optional[str] = None
) -> str:
    """
    Format dependency error messages with consistent structure.

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
    >>> format_dependency_error("netCDF4", "NetCDF export", "pip install netCDF4")
    '❌ Dependency error: netCDF4 required for NetCDF export\\nInstall with: pip install netCDF4'
    """
    parts = [f"❌ Dependency error: {missing_dependency} required for {operation}"]

    if install_command:
        parts.append(f"Install with: {install_command}")

    return "\n".join(parts)


# Legacy aliases for backward compatibility - will be removed in future versions
_format_cli_error = format_cli_error
_format_dependency_error = format_dependency_error
