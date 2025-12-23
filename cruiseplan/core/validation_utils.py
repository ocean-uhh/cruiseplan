"""
Validation utilities for cruise configuration processing.

This module provides reusable utility functions for configuration validation,
coordinate processing, and data enrichment operations.
"""

import logging
import math
import re
import warnings as python_warnings
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --- Coordinate Processing Utilities ---


def _interpolate_great_circle_position(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float, fraction: float
) -> Tuple[float, float]:
    """
    Interpolate position along great circle route using spherical geometry.

    Parameters
    ----------
    start_lat : float
        Starting latitude in decimal degrees.
    start_lon : float
        Starting longitude in decimal degrees.
    end_lat : float
        Ending latitude in decimal degrees.
    end_lon : float
        Ending longitude in decimal degrees.
    fraction : float
        Interpolation fraction (0.0 = start, 1.0 = end).

    Returns
    -------
    Tuple[float, float]
        Interpolated (latitude, longitude) in decimal degrees.
    """
    # Convert degrees to radians
    lat1 = math.radians(start_lat)
    lon1 = math.radians(start_lon)
    lat2 = math.radians(end_lat)
    lon2 = math.radians(end_lon)

    # Calculate angular distance
    d = math.acos(
        min(
            1,
            math.sin(lat1) * math.sin(lat2)
            + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1),
        )
    )

    # Handle edge case for very short distances
    if d < 1e-9:
        return start_lat, start_lon

    # Spherical interpolation
    A = math.sin((1 - fraction) * d) / math.sin(d)
    B = math.sin(fraction * d) / math.sin(d)

    x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
    y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
    z = A * math.sin(lat1) + B * math.sin(lat2)

    # Convert back to lat/lon
    lat_result = math.atan2(z, math.sqrt(x * x + y * y))
    lon_result = math.atan2(y, x)

    return math.degrees(lat_result), math.degrees(lon_result)


def _sanitize_station_name(name: str) -> str:
    """
    Sanitize station name for safe use in file systems and identifiers.

    Parameters
    ----------
    name : str
        Original station name.

    Returns
    -------
    str
        Sanitized name with only alphanumeric characters and underscores.
    """
    # Robust sanitization - replace all non-alphanumeric with underscores
    base_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Remove duplicate underscores and strip leading/trailing underscores
    return re.sub(r"_+", "_", base_name).strip("_")


def _extract_coordinate_value(
    coord_dict: Dict[str, Any], lat_keys: List[str], lon_keys: List[str]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract latitude and longitude from coordinate dictionary with flexible key names.

    Parameters
    ----------
    coord_dict : Dict[str, Any]
        Dictionary potentially containing coordinate information.
    lat_keys : List[str]
        List of possible latitude key names to check.
    lon_keys : List[str]
        List of possible longitude key names to check.

    Returns
    -------
    Tuple[Optional[float], Optional[float]]
        Extracted (latitude, longitude) or (None, None) if not found.
    """
    lat = None
    lon = None

    for key in lat_keys:
        if key in coord_dict and coord_dict[key] is not None:
            lat = coord_dict[key]
            break

    for key in lon_keys:
        if key in coord_dict and coord_dict[key] is not None:
            lon = coord_dict[key]
            break

    return lat, lon


# --- CTD Section Expansion Utilities ---


def _expand_single_ctd_section(
    transit: Dict[str, Any], default_depth: float = -9999.0
) -> List[Dict[str, Any]]:
    """
    Expand a single CTD section transit into individual station definitions.

    Parameters
    ----------
    transit : Dict[str, Any]
        Transit definition containing route and section parameters.
    default_depth : float, optional
        Default depth value to use for stations. Default is -9999.0 (placeholder).

    Returns
    -------
    List[Dict[str, Any]]
        List of station definitions along the section.
    """
    from cruiseplan.calculators.distance import haversine_distance

    if not transit.get("route") or len(transit["route"]) < 2:
        logger.warning(
            f"Transit {transit.get('name', 'unnamed')} has insufficient route points for expansion"
        )
        return []

    start = transit["route"][0]
    end = transit["route"][-1]

    # Extract coordinates using flexible key lookup
    start_lat, start_lon = _extract_coordinate_value(
        start, ["latitude", "lat"], ["longitude", "lon"]
    )
    end_lat, end_lon = _extract_coordinate_value(
        end, ["latitude", "lat"], ["longitude", "lon"]
    )

    if any(coord is None for coord in [start_lat, start_lon, end_lat, end_lon]):
        logger.warning(
            f"Transit {transit.get('name', 'unnamed')} has missing coordinates"
        )
        return []

    total_distance_km = haversine_distance((start_lat, start_lon), (end_lat, end_lon))
    spacing_km = transit.get("distance_between_stations", 20.0)
    num_stations = max(2, int(total_distance_km / spacing_km) + 1)

    stations = []
    base_name = _sanitize_station_name(transit["name"])

    for i in range(num_stations):
        fraction = i / (num_stations - 1) if num_stations > 1 else 0
        lat, lon = _interpolate_great_circle_position(
            start_lat, start_lon, end_lat, end_lon, fraction
        )

        station = {
            "name": f"{base_name}_Stn{i+1:03d}",
            "operation_type": "CTD",
            "action": "profile",
            "latitude": round(lat, 5),  # Direct coordinate storage
            "longitude": round(lon, 5),  # Direct coordinate storage
            "comment": f"Station {i+1}/{num_stations} on {transit['name']} section",
            "duration": 120.0,  # Duration in minutes for consistency
        }

        # Copy additional fields if present, converting to modern field names
        if "max_depth" in transit:
            station["water_depth"] = transit["max_depth"]  # Use semantic water_depth
        elif default_depth != -9999.0:
            # Use provided default depth if valid (not the placeholder value)
            station["water_depth"] = default_depth
        # If no depth is specified, let enrichment process handle bathymetry lookup

        if "planned_duration_hours" in transit:
            # Convert hours to minutes for consistency
            station["duration"] = float(transit["planned_duration_hours"]) * 60.0
        if "duration" in transit:
            station["duration"] = float(transit["duration"])  # Already in minutes

        stations.append(station)

    logger.info(f"Expanded '{transit['name']}' into {len(stations)} stations")
    return stations


# --- Warning Handling Utilities ---


@contextmanager
def _validation_warning_capture():
    """
    Context manager for capturing and formatting validation warnings.

    Yields
    ------
    List[str]
        List that will be populated with captured warning messages.
    """
    captured_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        captured_warnings.append(str(message))

    # Set up warning capture
    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    try:
        yield captured_warnings
    finally:
        # Restore original warning handler
        python_warnings.showwarning = old_showwarning


# --- Configuration Field Processing ---


def _add_cruise_level_defaults(config_dict: Dict[str, Any]) -> List[str]:
    """
    Add missing cruise-level configuration defaults.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to modify.

    Returns
    -------
    List[str]
        List of default fields that were added.
    """
    from cruiseplan.utils.constants import (
        DEFAULT_START_DATE,
        DEFAULT_TURNAROUND_TIME_MIN,
        DEFAULT_VESSEL_SPEED_KT,
    )

    defaults_added = []

    # Add missing cruise-level defaults
    if "start_date" not in config_dict or not config_dict["start_date"]:
        config_dict["start_date"] = DEFAULT_START_DATE
        defaults_added.append("start_date")

    if "start_time" not in config_dict or not config_dict["start_time"]:
        config_dict["start_time"] = "08:00"
        defaults_added.append("start_time")

    if (
        "default_vessel_speed" not in config_dict
        or not config_dict["default_vessel_speed"]
    ):
        config_dict["default_vessel_speed"] = DEFAULT_VESSEL_SPEED_KT
        defaults_added.append("default_vessel_speed")

    if "turnaround_time" not in config_dict or not config_dict["turnaround_time"]:
        config_dict["turnaround_time"] = DEFAULT_TURNAROUND_TIME_MIN
        defaults_added.append("turnaround_time")

    return defaults_added


def _add_port_defaults(config_dict: Dict[str, Any]) -> List[str]:
    """
    Add missing port configuration defaults.

    Only adds cruise-level port defaults if no legs are defined.
    When legs are present, ports should be defined within leg definitions.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to modify.

    Returns
    -------
    List[str]
        List of default fields that were added.
    """
    defaults_added = []

    # Only add cruise-level port defaults if no legs are defined
    # When legs exist, ports should be defined within leg definitions
    if not config_dict.get("legs"):
        # Add missing port defaults only if no legs exist
        if "departure_port" not in config_dict or not config_dict["departure_port"]:
            config_dict["departure_port"] = "port_bergen"
            defaults_added.append("departure_port")

        if "arrival_port" not in config_dict or not config_dict["arrival_port"]:
            config_dict["arrival_port"] = "port_bergen"
            defaults_added.append("arrival_port")

    return defaults_added


def _validate_required_structure(config_dict: Dict[str, Any]) -> List[str]:
    """
    Ensure required configuration structure exists.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to validate.

    Returns
    -------
    List[str]
        List of structural elements that were added or validated.
    """
    structure_added = []

    # Ensure basic sections exist
    required_sections = ["legs"]
    for section in required_sections:
        if section not in config_dict:
            config_dict[section] = []
            structure_added.append(f"empty_{section}_list")

    # Ensure at least one leg exists
    if not config_dict["legs"]:
        config_dict["legs"] = [
            {
                "name": "Main_Leg",
                "description": "Main cruise leg",
                "departure_port": "port_bergen",
                "arrival_port": "port_bergen",
            }
        ]
        structure_added.append("default_main_leg")

    return structure_added


def _add_configuration_fields(config_dict: Dict[str, Any]) -> List[str]:
    """
    Add missing configuration fields with sensible defaults.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to modify.

    Returns
    -------
    List[str]
        List of default fields that were added.
    """
    from cruiseplan.utils.constants import (
        DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY,
        DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS,
        DEFAULT_STATION_SPACING_KM,
        DEFAULT_TURNAROUND_TIME_MIN,
        DEFAULT_VESSEL_SPEED_KT,
    )

    defaults_added = []
    fields_to_add = []

    # Define field configurations: (field_name, default_value, display_value, description)
    field_configs = [
        (
            "default_vessel_speed",
            DEFAULT_VESSEL_SPEED_KT,
            f"{DEFAULT_VESSEL_SPEED_KT} knots",
            "vessel speed",
        ),
        (
            "calculate_transfer_between_sections",
            DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS,
            str(DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS),
            "transfer calculation",
        ),
        (
            "calculate_depth_via_bathymetry",
            DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY,
            str(DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY),
            "bathymetry depth calculation",
        ),
        (
            "default_distance_between_stations",
            DEFAULT_STATION_SPACING_KM,
            f"{DEFAULT_STATION_SPACING_KM} km",
            "station spacing",
        ),
        (
            "turnaround_time",
            DEFAULT_TURNAROUND_TIME_MIN,
            f"{DEFAULT_TURNAROUND_TIME_MIN} minutes",
            "turnaround time",
        ),
    ]

    for field_name, default_value, display_value, description in field_configs:
        if field_name not in config_dict:
            fields_to_add.append((field_name, default_value, display_value))
            defaults_added.append(f"{field_name} = {default_value}")
            logger.warning(f"⚠️ Added missing field: {field_name} = {display_value}")

    return fields_to_add, defaults_added


def _insert_missing_fields(
    config_dict: Dict[str, Any], fields_to_add: List[Tuple[str, Any, str]]
) -> None:
    """
    Insert missing fields into configuration with proper formatting.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to modify.
    fields_to_add : List[Tuple[str, Any, str]]
        List of (field_name, value, display_value) tuples to add.
    """
    from ruamel.yaml.comments import CommentedMap

    if not fields_to_add:
        return

    if isinstance(config_dict, CommentedMap):
        # Find insertion point after cruise_name
        keys = list(config_dict.keys())
        insert_index = 1 if "cruise_name" in keys else 0

        for field_name, value, display_value in fields_to_add:
            config_dict.insert(insert_index, field_name, value)
            config_dict.yaml_add_eol_comment(
                " # default added by cruiseplan enrich", field_name
            )
            insert_index += 1
    else:
        # Plain dictionary - just add fields
        for field_name, value, display_value in fields_to_add:
            config_dict[field_name] = value


# --- Validation Pattern Utilities ---


def _check_placeholder_values(entity: Any, field_mapping: Dict[str, str]) -> List[str]:
    """
    Generic placeholder value checker for any entity.

    Parameters
    ----------
    entity : Any
        Entity to check for placeholder values.
    field_mapping : Dict[str, str]
        Mapping of field names to user-friendly descriptions.

    Returns
    -------
    List[str]
        List of warnings about placeholder values found.
    """
    warnings = []

    for field_name, description in field_mapping.items():
        if hasattr(entity, field_name):
            value = getattr(entity, field_name)
            if value and isinstance(value, str) and "placeholder" in str(value).lower():
                warnings.append(f"{description} contains placeholder value: {value}")

    return warnings


def _check_default_coordinates(entity: Any, coord_fields: List[str]) -> List[str]:
    """
    Generic default coordinate checker.

    Parameters
    ----------
    entity : Any
        Entity to check for default coordinates.
    coord_fields : List[str]
        List of coordinate field names to check.

    Returns
    -------
    List[str]
        List of warnings about default coordinates found.
    """
    warnings = []
    default_coords = [0.0, 0]  # Common default coordinate values

    for field_name in coord_fields:
        if hasattr(entity, field_name):
            value = getattr(entity, field_name)
            if value in default_coords:
                warnings.append(f"{field_name} is set to default value: {value}")

    return warnings
