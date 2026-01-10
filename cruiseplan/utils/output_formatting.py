"""
Legacy CLI error formatting functions.

TODO: This entire module should be removed when cli/stations.py is refactored
to use the API-first approach. These functions are only used by the legacy
CLI commands and won't be needed after the refactor.

The round_time_to_minute function has been moved to output/output_utils.py
where it belongs with other output formatting utilities.
"""

from typing import Any, Optional


def format_cli_error(
    operation: str,
    error: Exception,
    context: Optional[dict[str, Any]] = None,
    suggestions: Optional[list[str]] = None,
) -> str:
    """
    Format CLI error messages with consistent structure.

    TODO: Remove when cli/stations.py is refactored to use API-first approach.

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

    TODO: Remove when cli/stations.py is refactored to use API-first approach.

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
    """
    parts = [f"❌ Dependency error: {missing_dependency} required for {operation}"]

    if install_command:
        parts.append(f"Install with: {install_command}")

    return "\n".join(parts)


# Legacy aliases for backward compatibility
# TODO: Remove these when cli/stations.py is refactored
_format_cli_error = format_cli_error
_format_dependency_error = format_dependency_error
