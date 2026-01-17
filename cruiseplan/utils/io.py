"""
General file I/O utilities for the cruiseplan package.

This module provides low-level file system validation and path handling utilities
used by API functions to ensure consistent error handling across the package.

**I/O Module Architecture:**
- **cruiseplan.utils.io** (this module): File system validation, path handling, directory creation
- **cruiseplan.schema.yaml_io**: YAML file format reading/writing with comment preservation
- **cruiseplan.core.serialization**: High-level CruiseInstance object serialization to YAML
- **cruiseplan.output.*_generator**: Specialized output format generators (HTML, LaTeX, CSV, etc.)

**Dependencies**: This is the lowest layer - other I/O modules may use these utilities.

**See Also**:
- For YAML file operations: `cruiseplan.schema.yaml_io`
- For converting CruiseInstance objects to YAML: `cruiseplan.core.serialization`
- For generating specific output formats: `cruiseplan.output.html_generator`, `cruiseplan.output.latex_generator`, etc.
"""

import logging
from pathlib import Path
from typing import Optional, Union

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
    input_path: Union[str, Path], suffix: str, extension: Optional[str] = None
) -> str:
    """
    Generate output filename by adding suffix to input filename.

    # NOTE: Used by stations_api.py and other API modules for consistent filename generation

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


def setup_output_paths(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
) -> tuple[Path, str]:
    """
    Helper function to set up output directory and base filename from config file and parameters.

    This is the consolidated output path utility, migrated from utils/config.py.
    It handles both explicit output naming and automatic name derivation from
    config files with YAML cruise_name extraction.

    Parameters
    ----------
    config_file : Union[str, Path]
        Input YAML configuration file
    output_dir : str, optional
        Output directory (default: "data")
    output : str, optional
        Base filename for outputs (default: use cruise name from YAML)

    Returns
    -------
    tuple[Path, str]
        (output_dir_path, base_name) where output_dir_path is resolved Path
        and base_name is the filename stem to use for outputs

    Examples
    --------
    >>> setup_output_paths("cruise.yaml", "results")
    (Path("/path/to/results"), "cruise_name_from_yaml")
    >>> setup_output_paths("cruise.yaml", output="custom_name")
    (Path("/path/to/data"), "custom_name")
    """
    # Setup output directory with validation
    try:
        output_dir_path = validate_output_directory(output_dir)
    except ValueError as e:
        raise ValueError(f"Output directory setup failed: {e}")

    # Determine base filename
    if output:
        base_name = output
    else:
        # Try to get cruise name from YAML content, fallback to filename
        try:
            import yaml

            with open(config_file) as f:
                config_data = yaml.safe_load(f)
                cruise_name = config_data.get("cruise_name")
                if cruise_name:
                    # Use cruise name with safe character replacement
                    base_name = str(cruise_name).replace(" ", "_").replace("/", "-")
                else:
                    # Fallback to config file stem
                    base_name = (
                        Path(config_file).stem.replace(" ", "_").replace("/", "-")
                    )
        except (FileNotFoundError, yaml.YAMLError, KeyError):
            # Fallback to config file stem if YAML reading fails
            base_name = Path(config_file).stem.replace(" ", "_").replace("/", "-")

    return output_dir_path, base_name
