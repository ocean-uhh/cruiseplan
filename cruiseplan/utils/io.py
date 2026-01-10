"""
General file I/O utilities for the cruiseplan package.

This module provides centralized file validation and I/O utilities used
by API functions to ensure consistent error handling across the package.
"""

import logging
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def validate_input_file(file_path: Union[str, Path], must_exist: bool = True) -> Path:
    """
    Validate and resolve an input file path for API operations.

    This is the centralized file validation used by all API functions to ensure
    consistent error handling and messaging across the package.

    Parameters
    ----------
    file_path : Union[str, Path]
        Path to validate
    must_exist : bool, optional
        Whether the file must exist (default: True)

    Returns
    -------
    Path
        Resolved and validated Path object

    Raises
    ------
    ValueError
        If file validation fails (will be caught and re-raised as FileError by API)
    """
    file_path = Path(file_path)
    resolved_path = file_path.resolve()

    if must_exist:
        if not resolved_path.exists():
            raise ValueError(f"File not found: {resolved_path}")

        if not resolved_path.is_file():
            raise ValueError(f"Path is not a file: {resolved_path}")

        # Check for empty files only if they should contain data
        if resolved_path.stat().st_size == 0:
            raise ValueError(f"File is empty: {resolved_path}")

    return resolved_path


def validate_output_directory(
    directory_path: Union[str, Path], create_if_missing: bool = True
) -> Path:
    """
    Validate and optionally create an output directory.

    Parameters
    ----------
    directory_path : Union[str, Path]
        Directory path to validate
    create_if_missing : bool, optional
        Whether to create the directory if it doesn't exist (default: True)

    Returns
    -------
    Path
        Resolved and validated directory Path object

    Raises
    ------
    ValueError
        If directory validation fails (will be caught and re-raised as FileError by API)
    """
    directory_path = Path(directory_path)
    resolved_path = directory_path.resolve()

    if create_if_missing:
        try:
            resolved_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create output directory: {resolved_path}: {e}")

    if not resolved_path.exists():
        raise ValueError(f"Output directory does not exist: {resolved_path}")

    if not resolved_path.is_dir():
        raise ValueError(f"Path is not a directory: {resolved_path}")

    # Test write permissions
    try:
        test_file = resolved_path / ".cruiseplan_write_test"
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        raise ValueError(f"Output directory is not writable: {resolved_path}: {e}")

    return resolved_path


def generate_output_filename(
    input_path: Union[str, Path], suffix: str, extension: str = None
) -> str:
    """
    Generate output filename by adding suffix to input filename.

    # TODO: Refactor stations.py to use this centralized function instead of CLI utils

    This utility creates output filenames by taking an input path,
    extracting its stem, and adding a suffix and optional new extension.

    Parameters
    ----------
    input_path : Union[str, Path]
        Input file path to base the output name on
    suffix : str
        Suffix to add (e.g., "_processed", "_with_depths")
    extension : str, optional
        New file extension including the dot (e.g., ".yaml", ".json").
        If None, uses the original file's extension.

    Returns
    -------
    str
        Generated filename with suffix and extension

    Examples
    --------
    >>> generate_output_filename("cruise.yaml", "_enriched")
    "cruise_enriched.yaml"
    >>> generate_output_filename("data.csv", "_processed", ".json")
    "data_processed.json"
    """
    input_path = Path(input_path)

    if extension is None:
        extension = input_path.suffix

    stem = input_path.stem
    return f"{stem}{suffix}{extension}"


def _setup_output_paths(
    config_file: Union[str, Path] = None,
    output_dir: str = "data",
    output_base: str = None,
    default_base: str = "output",
) -> tuple[Path, str]:
    """
    Setup output directory and determine base filename for API operations.

    # TODO: This consolidates functionality from:
    # - utils/config.py:setup_output_paths
    # - cli/cli_utils.py:determine_output_path - deleted
    # - utils/output_formatting.py:_determine_output_*
    # Once API functions are updated to use this, remove the duplicates.

    This is a centralized utility for API functions to determine where
    to write output files and what base filename to use.

    Parameters
    ----------
    config_file : Union[str, Path], optional
        Input configuration file to base naming on
    output_dir : str, optional
        Output directory path (default: "data")
    output_base : str, optional
        Explicit base filename to use. If provided, overrides config-based naming.
    default_base : str, optional
        Fallback base filename if neither output_base nor config_file provide a name

    Returns
    -------
    tuple[Path, str]
        (resolved_output_directory, base_filename_stem)

    Examples
    --------
    >>> setup_output_paths("cruise.yaml", "results")
    (Path("/path/to/results"), "cruise")
    >>> setup_output_paths(output_base="expedition_2024")
    (Path("/path/to/data"), "expedition_2024")
    """
    # Setup output directory
    try:
        output_dir_path = validate_output_directory(output_dir)
    except ValueError as e:
        raise ValueError(f"Output directory setup failed: {e}")

    # Determine base filename
    if output_base:
        # Explicit base name provided
        base_name = output_base.replace(" ", "_")
    elif config_file:
        # Use config file stem as base name
        config_path = Path(config_file)
        base_name = config_path.stem.replace(" ", "_")
    else:
        # Use default fallback
        base_name = default_base.replace(" ", "_")

    return output_dir_path, base_name
