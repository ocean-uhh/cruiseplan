"""
Custom exception types for CruisePlan.

Provides clean error handling for configuration validation, file operations,
and bathymetry processing.
"""


# Custom exception types for clean CLI error handling
class ValidationError(Exception):
    """Raised when configuration validation fails."""


class FileError(Exception):
    """Raised when file operations fail (reading, writing, permissions)."""


class BathymetryError(Exception):
    """Raised when bathymetry operations fail."""
