"""
Centralized YAML I/O utilities with comment preservation.

This module provides all YAML reading and writing functionality for the
cruiseplan package, using ruamel.yaml to preserve comments, formatting,
and whitespace during configuration enrichment operations.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Union

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

logger = logging.getLogger(__name__)


class YAMLIOError(Exception):
    """Custom exception for YAML I/O operations."""

    pass


def _get_yaml_processor(preserve_quotes: bool = True, width: int = 4096) -> YAML:
    """
    Get configured YAML processor instance.

    Args:
        preserve_quotes: Whether to preserve quote styles
        width: Line width before wrapping (high value prevents wrapping)

    Returns
    -------
        Configured YAML processor instance
    """
    yaml = YAML()
    yaml.preserve_quotes = preserve_quotes
    yaml.width = width  # Prevent unwanted line wrapping
    yaml.indent(mapping=2, sequence=4, offset=2)  # Match existing formatting
    yaml.sort_keys = (
        False  # Preserve insertion order (equivalent to PyYAML sort_keys=False)
    )
    yaml.map_indent = 2  # Control mapping indentation
    yaml.sequence_indent = 4  # Control sequence indentation
    yaml.sequence_dash_offset = 2  # Control dash offset
    return yaml


def load_yaml(file_path: Union[str, Path], encoding: str = "utf-8") -> Dict[str, Any]:
    """
    Load YAML configuration file with comment preservation.

    Args:
        file_path: Path to YAML file
        encoding: File encoding

    Returns
    -------
        Parsed YAML content as dictionary

    Raises
    ------
        YAMLIOError: If file cannot be loaded or parsed
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise YAMLIOError(f"YAML file not found: {file_path}")

    if not file_path.is_file():
        raise YAMLIOError(f"Path is not a file: {file_path}")

    try:
        yaml = _get_yaml_processor()
        with open(file_path, encoding=encoding) as f:
            config = yaml.load(f)

        if config is None:
            raise YAMLIOError(f"YAML file is empty: {file_path}")

        return config

    except YAMLError as e:
        raise YAMLIOError(f"Invalid YAML syntax in {file_path}: {e}") from e
    except Exception as e:
        raise YAMLIOError(f"Error reading {file_path}: {e}") from e


def dump_yaml_simple(data: Dict[str, Any], file_handle) -> None:
    """
    Dump YAML data to file handle without comment preservation.

    This function provides basic YAML dumping for cases like temp files
    where comment preservation is not needed.

    Args:
        data: Dictionary to dump
        file_handle: Open file handle to write to

    Raises
    ------
        YAMLIOError: If dumping fails
    """
    try:
        from ruamel.yaml import YAML

        # Use regular YAML instead of safe mode to handle CommentedMap objects
        yaml = YAML()
        yaml.default_flow_style = False
        yaml.sort_keys = False  # Preserve insertion order
        yaml.dump(data, file_handle)
    except Exception as e:
        raise YAMLIOError(f"Error dumping YAML: {e}") from e


def save_yaml(
    config: Dict[str, Any],
    file_path: Union[str, Path],
    backup: bool = True,
    encoding: str = "utf-8",
) -> None:
    """
    Save configuration to YAML file with comment preservation.

    Args:
        config: Configuration dictionary to save
        file_path: Output file path
        backup: Whether to create backup of existing file
        encoding: File encoding

    Raises
    ------
        YAMLIOError: If file cannot be written
    """
    file_path = Path(file_path)

    try:
        # Create backup if requested and file exists
        if backup and file_path.exists():
            backup_path = _get_incremental_backup_path(file_path)
            backup_path.write_text(
                file_path.read_text(encoding=encoding), encoding=encoding
            )
            logger.info(f"Created backup: {backup_path}")

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write YAML file with comment preservation
        yaml = _get_yaml_processor()
        with open(file_path, "w", encoding=encoding) as f:
            yaml.dump(config, f)

        logger.info(f"Saved configuration to: {file_path}")

    except Exception as e:
        raise YAMLIOError(f"Error writing {file_path}: {e}") from e


def _get_incremental_backup_path(file_path: Path) -> Path:
    """
    Get an incremental backup file path that doesn't already exist.

    Args:
        file_path: Original file path

    Returns
    -------
        Available backup path with incremental number
    """
    counter = 1
    while True:
        backup_path = file_path.with_name(f"{file_path.name}-{counter}")
        if not backup_path.exists():
            return backup_path
        counter += 1


def load_yaml_safe(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load YAML file using ruamel.yaml safe loading (returns plain dict).

    This function provides basic dictionary loading without comment preservation.
    Returns a plain Python dictionary instead of ruamel.yaml's CommentedMap.
    Use load_yaml() for comment-preserving operations.

    Args:
        file_path: Path to YAML file

    Returns
    -------
        Parsed YAML content as basic dictionary

    Raises
    ------
        YAMLIOError: If file cannot be loaded or parsed
    """
    from ruamel.yaml import YAML

    file_path = Path(file_path)

    try:
        yaml = YAML(typ="safe")  # Use safe mode, returns plain Python objects
        yaml.sort_keys = False  # Preserve insertion order
        with open(file_path, encoding="utf-8") as f:
            config = yaml.load(f)

        if config is None:
            raise YAMLIOError(f"YAML file is empty: {file_path}")

        return config

    except YAMLError as e:
        raise YAMLIOError(f"Invalid YAML syntax in {file_path}: {e}") from e
    except Exception as e:
        raise YAMLIOError(f"Error reading {file_path}: {e}") from e
