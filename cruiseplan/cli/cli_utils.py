"""
Common utilities for CLI commands.

This module provides shared functionality across CLI modules including
file path validation, output directory management, progress indicators,
error message formatting, and input validation utilities.

Consolidated from utils/input_validation.py to keep all CLI-specific
utilities in one place.
"""

import logging
from argparse import Namespace
from pathlib import Path
from typing import Optional

from cruiseplan.utils.io import validate_input_file

logger = logging.getLogger(__name__)


class CLIError(Exception):
    """Custom exception for CLI-related errors."""

    pass


def generate_output_filename(
    input_path: Path, suffix: str, extension: Optional[str] = None
) -> str:
    """
    Generate output filename by adding suffix to input filename.

    # TODO: Remove this function when stations.py is refactored to API-first architecture.
    # Duplicate of utils.io.generate_output_filename - stations.py should use that centralized version.

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


def load_pangaea_campaign_data(pangaea_file: Path) -> list:
    """
    Load PANGAEA campaign data from pickle file with validation and summary.

    # TODO: Remove this function when stations.py is refactored to API-first architecture.
    # This is a redundant wrapper around pangaea.load_campaign_data() that only adds:
    # 1) CLIError exception wrapping (cosmetic)
    # 2) Extra logging with statistics (could be done by caller)
    # 3) Import error handling (could be handled at import time)
    # The core pangaea.load_campaign_data() already provides all necessary validation,
    # error handling, and logging. stations.py should call that function directly.

    Parameters
    ----------
    pangaea_file : Path
        Path to PANGAEA pickle file.

    Returns
    -------
    list
        List of campaign datasets.

    Raises
    ------
    CLIError
        If file cannot be loaded or contains no data.
    """
    try:
        from cruiseplan.data.pangaea import load_campaign_data

        campaign_data = load_campaign_data(pangaea_file)

        if not campaign_data:
            raise CLIError(f"No campaign data found in {pangaea_file}")

        # Summary statistics
        total_points = sum(
            len(campaign.get("latitude", [])) for campaign in campaign_data
        )
        campaigns = [campaign.get("label", "Unknown") for campaign in campaign_data]

        logger.info(
            f"Loaded {len(campaign_data)} campaigns with {total_points} total stations:"
        )
        for campaign in campaigns:
            logger.info(f"  - {campaign}")

        return campaign_data

    except ImportError as e:
        raise CLIError(f"PANGAEA functionality not available: {e}")
    except Exception as e:
        raise CLIError(f"Error loading PANGAEA data: {e}")


def format_coordinate_bounds(lat_bounds: tuple, lon_bounds: tuple) -> str:
    """
    Format coordinate bounds for display.

    # TODO: Remove this function when stations.py is refactored to API-first architecture.
    # Use utils.output_formatting._format_coordinate_summary which has better formatting (N/S/E/W indicators).

    Args:
        lat_bounds: (min_lat, max_lat)
        lon_bounds: (min_lon, max_lon)

    Returns
    -------
        Formatted bounds string
    """
    return f"Lat: {lat_bounds[0]:.2f}° to {lat_bounds[1]:.2f}°, Lon: {lon_bounds[0]:.2f}° to {lon_bounds[1]:.2f}°"


# ============================================================================
# Phase 1 Refactoring: New Utility Functions for API-First CLI Architecture
# ============================================================================


def _handle_deprecated_params(args: Namespace, param_map: dict[str, str]) -> None:
    """
    Centralized deprecation warnings and parameter migration.

    # TODO: Remove this function when stations.py is refactored to API-first architecture.
    # Modern API-first commands (e.g., enrich.py) use the cleaner argparse dest= pattern:
    # parser.add_argument("--old-param", dest="new_param", help=argparse.SUPPRESS)
    # This automatically maps deprecated parameters to new attribute names without
    # requiring custom warning logic or manual migration. This legacy approach
    # should be replaced with the argparse mapping pattern.

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


def _apply_cli_defaults(args: Namespace) -> None:
    """
    Apply common CLI parameter defaults after legacy parameter migration.

    # TODO: Remove this function when stations.py is refactored to API-first architecture.
    # This function only sets bathymetry directory defaults and is only used by stations.py.
    # API-first commands handle defaults through the API layer, not CLI argument processing.

    Internal utility to handle default values consistently across CLI commands.
    Should be called after _handle_deprecated_params to ensure migrated
    parameters get proper defaults applied.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments to apply defaults to

    Examples
    --------
    >>> _handle_deprecated_params(args, param_map)
    >>> _apply_cli_defaults(args)  # Apply defaults after migration
    """
    from pathlib import Path

    # Apply bathymetry directory default
    if getattr(args, "bathy_dir", None) is None:
        args.bathy_dir = Path("data")


def _handle_common_deprecated_params(args: Namespace) -> None:
    """
    Handle deprecated parameters that are common across multiple CLI commands.

    # TODO: Remove this function when stations.py is refactored to API-first architecture.
    # This function is currently empty and serves no purpose. Modern API-first commands
    # handle deprecated parameters using the argparse dest= pattern instead of custom
    # logic. This legacy approach should be removed along with _handle_deprecated_params().

    Internal utility to handle deprecated parameters that appear in multiple
    commands consistently. Should be called before command-specific deprecated
    parameter handling.

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments

    Examples
    --------
    >>> _handle_common_deprecated_params(args)  # Handle common deprecated params
    >>> _handle_deprecated_params(args, command_specific_map)  # Handle command-specific
    """


def _initialize_cli_command(
    args: Namespace,
    deprecated_param_map: Optional[dict[str, str]] = None,
    requires_config_file: bool = True,
) -> Optional[Path]:
    """
    Standardized CLI command initialization with common setup patterns.

    # TODO: This function is legacy from pre-API refactor era and can likely be removed.
    # Only used by stations.py (and redundantly - it calls _handle_deprecated_params
    # and _apply_cli_defaults before calling this function which does the same).
    # Other CLI commands use thin wrapper pattern and call API functions directly.
    # When stations.py is refactored, this function can probably be removed.

    Performs the standard initialization sequence that most CLI commands need:
    1. Setup logging based on verbose/quiet flags
    2. Handle common deprecated parameters
    3. Handle command-specific deprecated parameters
    4. Apply common defaults
    5. Validate config file (if required)

    Parameters
    ----------
    args : Namespace
        Parsed command line arguments
    deprecated_param_map : Dict[str, str], optional
        Command-specific deprecated parameter mappings
    requires_config_file : bool, default True
        Whether this command requires a config file

    Returns
    -------
    Optional[Path]
        Validated config file path if requires_config_file=True, None otherwise

    Examples
    --------
    >>> # Simple initialization without config file
    >>> _initialize_cli_command(args, requires_config_file=False)

    >>> # Full initialization with deprecated params
    >>> param_map = {"bathy_dir_legacy": "bathy_dir"}
    >>> config_file = _initialize_cli_command(args, param_map)
    """
    # Setup logging
    verbose = getattr(args, "verbose", False)
    quiet = getattr(args, "quiet", False)

    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s", force=True)

    # Handle common deprecated parameters
    _handle_common_deprecated_params(args)

    # Handle command-specific deprecated parameters
    if deprecated_param_map:
        _handle_deprecated_params(args, deprecated_param_map)

    # Apply common defaults
    _apply_cli_defaults(args)

    # Validate config file if required
    if requires_config_file:
        if not hasattr(args, "config_file") or not args.config_file:
            raise CLIError("Configuration file is required for this command")
        return validate_input_file(args.config_file)

    return None
