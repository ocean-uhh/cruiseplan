"""
System constants and fallback values for cruise planning calculations.

This module defines system-level constants and sentinel values used for
calculations and error handling throughout the cruiseplan system.
For YAML field values and defaults, see cruiseplan.schema.values.

Notes
-----
These are primarily calculation constants and system fallbacks,
not user-configurable field values.
"""

# --- Depth/Bathymetry Constants ---

# Sentinel value indicating that depth data is missing, the station is outside
# the bathymetry grid boundaries, or a calculation failed.
# This value is defined in the specs as the default depth if ETOPO data is not found.
DEFAULT_DEPTH = -9999.0
