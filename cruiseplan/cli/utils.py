"""
Common utilities for CLI commands.

This module provides shared functionality across CLI modules including
file path validation, output directory management, progress indicators,
and error message formatting.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

import yaml

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
        with open(file_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if config is None:
            raise CLIError(f"YAML file is empty: {file_path}")

        return config

    except yaml.YAMLError as e:
        raise CLIError(f"Invalid YAML syntax in {file_path}: {e}")
    except Exception as e:
        raise CLIError(f"Error reading {file_path}: {e}")


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
    try:
        # Create backup if requested and file exists
        if backup and file_path.exists():
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            backup_path.write_text(file_path.read_text())
            logger.info(f"Created backup: {backup_path}")

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False, indent=2)

        logger.info(f"Saved configuration to: {file_path}")

    except Exception as e:
        raise CLIError(f"Error writing {file_path}: {e}")


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
