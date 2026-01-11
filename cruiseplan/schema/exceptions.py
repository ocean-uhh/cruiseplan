"""
Custom exceptions for cruise configuration validation.
"""


class CruiseConfigurationError(Exception):
    """
    Exception raised when cruise configuration is invalid or cannot be processed.

    This exception is raised during configuration validation when the YAML
    file contains invalid data, missing required fields, or logical inconsistencies
    that prevent the cruise plan from being properly loaded.
    """

    ...
