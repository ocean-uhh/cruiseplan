"""
Centralized logging configuration utilities.

This module provides common logging setup functions used across
multiple CLI commands and API modules for consistent logging behavior.
"""

import logging


def configure_logging(verbose: bool = False) -> None:
    """
    Configure logging level and format for cruiseplan operations.

    This standardizes logging configuration across all API modules,
    replacing multiple inconsistent basicConfig calls.

    Parameters
    ----------
    verbose : bool, optional
        Enable verbose (DEBUG) logging. If False, uses INFO level.

    Notes
    -----
    Uses a consistent format: "%(levelname)s: %(message)s"
    Forces reconfiguration with force=True to override any existing config.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", force=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with consistent naming convention.

    Parameters
    ----------
    name : str
        Logger name, typically __name__

    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    return logging.getLogger(name)
