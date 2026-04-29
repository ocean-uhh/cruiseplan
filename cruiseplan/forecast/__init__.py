"""
Forecast package for station plan generation.

This package provides functionality for reading cruise schedules from NetCDF files
and generating real-time station plan forecasts for cruise operations.
"""

from cruiseplan.forecast.generator import list_activities
from cruiseplan.forecast.reader import netcdf_to_activity_records, read_schedule

__all__ = ["list_activities", "netcdf_to_activity_records", "read_schedule"]
