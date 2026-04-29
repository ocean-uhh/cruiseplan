"""
Forecast package for station plan generation.

This package provides functionality for reading cruise schedules from NetCDF files
and generating real-time station plan forecasts for cruise operations.
"""

from cruiseplan.forecast.reader import read_schedule, netcdf_to_activity_records
from cruiseplan.forecast.generator import list_activities

__all__ = ["read_schedule", "list_activities", "netcdf_to_activity_records"]