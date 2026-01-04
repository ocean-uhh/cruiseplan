"""
Custom validation functions for cruise configuration.

Provides standalone validation functions that can be used across
different model classes to ensure consistent validation logic.
"""

import logging
import warnings
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Track deprecation warnings to show only once per session
_shown_warnings = set()


def validate_positive_number(value: float, field_name: str) -> float:
    """
    Validate that a number is positive.

    Parameters
    ----------
    value : float
        Value to validate.
    field_name : str
        Name of the field for error messages.

    Returns
    -------
    float
        Validated positive number.

    Raises
    ------
    ValueError
        If value is not positive.
    """
    if value <= 0:
        msg = f"{field_name} must be positive, got {value}"
        raise ValueError(msg)
    return value


def validate_non_negative_number(value: float, field_name: str) -> float:
    """
    Validate that a number is non-negative.

    Parameters
    ----------
    value : float
        Value to validate.
    field_name : str
        Name of the field for error messages.

    Returns
    -------
    float
        Validated non-negative number.

    Raises
    ------
    ValueError
        If value is negative.
    """
    if value < 0:
        msg = f"{field_name} must be non-negative, got {value}"
        raise ValueError(msg)
    return value


def validate_hour_range(value: int, field_name: str) -> int:
    """
    Validate that an hour value is in valid range (0-23).

    Parameters
    ----------
    value : int
        Hour value to validate.
    field_name : str
        Name of the field for error messages.

    Returns
    -------
    int
        Validated hour value.

    Raises
    ------
    ValueError
        If hour is outside 0-23 range.
    """
    if not (0 <= value <= 23):
        msg = f"{field_name} must be between 0 and 23, got {value}"
        raise ValueError(msg)
    return value


def show_deprecation_warning(message: str, category: type = DeprecationWarning) -> None:
    """
    Show a deprecation warning only once per session.

    Parameters
    ----------
    message : str
        Warning message to display.
    category : type, optional
        Warning category, by default DeprecationWarning.
    """
    if message not in _shown_warnings:
        warnings.warn(message, category, stacklevel=3)
        _shown_warnings.add(message)


def validate_unique_names(items: List[Dict[str, Any]], item_type: str) -> None:
    """
    Validate that all items in a list have unique names.

    Parameters
    ----------
    items : List[Dict[str, Any]]
        List of items with 'name' field.
    item_type : str
        Type of items for error messages.

    Raises
    ------
    ValueError
        If duplicate names are found.
    """
    if not items:
        return

    names = []
    for item in items:
        if hasattr(item, "name"):
            names.append(item.name)
        elif isinstance(item, dict) and "name" in item:
            names.append(item["name"])

    duplicates = []
    seen = set()
    for name in names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)

    if duplicates:
        msg = f"Duplicate {item_type} names found: {duplicates}"
        raise ValueError(msg)
