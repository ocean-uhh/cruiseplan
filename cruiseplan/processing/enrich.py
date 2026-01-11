"""
Cruise configuration enrichment operations.

This module implements cruiseplan.enrich() business logic including:
- CTD section expansion into individual stations
- Coordinate addition and formatting
- Depth enrichment via bathymetry
- Port expansion and defaults
- Configuration structure validation and completion

All enrichment operations that transform and expand cruise configuration
data are centralized here to support the main API functions.
"""

import logging
import re
import tempfile
import warnings
import warnings as python_warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from cruiseplan.schema.vocabulary import (
    ACTION_FIELD,
    ACTIVITIES_FIELD,
    AREA_VERTEX_FIELD,
    AREAS_FIELD,
    ARRIVAL_PORT_FIELD,
    CLUSTERS_FIELD,
    DEFAULT_VESSEL_SPEED_FIELD,
    DEPARTURE_PORT_FIELD,
    DURATION_FIELD,
    FIRST_ACTIVITY_FIELD,
    LAST_ACTIVITY_FIELD,
    LEGS_FIELD,
    LINE_VERTEX_FIELD,
    LINES_FIELD,
    OP_TYPE_FIELD,
    POINTS_FIELD,
    START_DATE_FIELD,
    START_TIME_FIELD,
    WATER_DEPTH_FIELD,
)

# Core cruiseplan imports that don't cause circular imports
from cruiseplan.utils.coordinates import format_ddm_comment
from cruiseplan.utils.defaults import (
    DEFAULT_ARRIVAL_PORT,
    DEFAULT_CALC_DEPTH,
    DEFAULT_CALC_TRANSFER,
    DEFAULT_CTD_RATE_M_S,
    DEFAULT_DEPARTURE_PORT,
    DEFAULT_MOORING_DURATION_MIN,
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
    DEFAULT_VESSEL_SPEED_KT,
)
from cruiseplan.utils.global_ports import resolve_port_reference
from cruiseplan.utils.yaml_io import load_yaml, save_yaml

logger = logging.getLogger(__name__)


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

    old_showwarning = python_warnings.showwarning
    python_warnings.showwarning = warning_handler

    try:
        yield captured_warnings
    finally:
        python_warnings.showwarning = old_showwarning


# --- Configuration Field Processing ---


# Why do we add both a start_time and a start_date? If the start_date has the time in
# it, isn't that enough?
# Are these more opportunities to use vocabulary.py constants? START_DATE_FIELD, TURNAROUND_TIME_FIELDS
def _add_missing_defaults(
    config_dict: dict[str, Any],
) -> tuple[list[tuple[str, Any, str]], list[str]]:
    """
    Prepare missing configuration defaults for insertion.

    Handles both user-facing parameters (inserted at top) and technical parameters
    (inserted later). All fields are collected and inserted together to maintain
    proper positioning.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to check.

    Returns
    -------
    Tuple[List[Tuple[str, Any, str]], List[str]]
        Tuple of (fields_to_add, defaults_added_list) where fields_to_add contains
        (field_name, value, display_value) tuples for proper insertion.
    """
    defaults_added = []
    fields_to_add = []

    user_params = [
        (START_DATE_FIELD, DEFAULT_START_DATE, DEFAULT_START_DATE, "start_date"),
        (START_TIME_FIELD, "08:00", "08:00", "start_time"),
        (
            DEFAULT_VESSEL_SPEED_FIELD,
            DEFAULT_VESSEL_SPEED_KT,
            f"{DEFAULT_VESSEL_SPEED_KT} knots",
            "default_vessel_speed",
        ),
        (
            "turnaround_time",
            DEFAULT_TURNAROUND_TIME_MIN,
            f"{DEFAULT_TURNAROUND_TIME_MIN} minutes",
            "turnaround_time",
        ),
        (
            "ctd_descent_rate",
            DEFAULT_CTD_RATE_M_S,
            f"{DEFAULT_CTD_RATE_M_S} m/s",
            "ctd_descent_rate",
        ),
        (
            "ctd_ascent_rate",
            DEFAULT_CTD_RATE_M_S,
            f"{DEFAULT_CTD_RATE_M_S} m/s",
            "ctd_ascent_rate",
        ),
    ]

    technical_params = [
        (
            "calculate_transfer_between_sections",
            DEFAULT_CALC_TRANSFER,
            str(DEFAULT_CALC_TRANSFER),
            "transfer calculation",
        ),
        (
            "calculate_depth_via_bathymetry",
            DEFAULT_CALC_DEPTH,
            str(DEFAULT_CALC_DEPTH),
            "bathymetry depth calculation",
        ),
        (
            "default_distance_between_stations",
            DEFAULT_STATION_SPACING_KM,
            f"{DEFAULT_STATION_SPACING_KM} km",
            "station spacing",
        ),
    ]

    for field_name, default_value, display_value, description in user_params:
        if field_name not in config_dict or not config_dict[field_name]:
            fields_to_add.append((field_name, default_value, display_value))
            defaults_added.append(description)

    for field_name, default_value, display_value, _description in technical_params:
        if field_name not in config_dict or not config_dict[field_name]:
            fields_to_add.append((field_name, default_value, display_value))
            defaults_added.append(f"{field_name} = {default_value}")
            logger.warning(f"⚠️ Added missing field: {field_name} = {display_value}")

    return fields_to_add, defaults_added


def _add_port_defaults(config_dict: dict[str, Any]) -> list[str]:
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

    if not config_dict.get(LEGS_FIELD):
        if (
            DEPARTURE_PORT_FIELD not in config_dict
            or not config_dict[DEPARTURE_PORT_FIELD]
        ):
            config_dict[DEPARTURE_PORT_FIELD] = DEFAULT_DEPARTURE_PORT
            defaults_added.append("departure_port")

        if ARRIVAL_PORT_FIELD not in config_dict or not config_dict[ARRIVAL_PORT_FIELD]:
            config_dict[ARRIVAL_PORT_FIELD] = DEFAULT_ARRIVAL_PORT
            defaults_added.append("arrival_port")

    return defaults_added


# TODO Also LEGS_FIELD and CLUSTERS_FIELD
def _validate_required_structure(config_dict: dict[str, Any]) -> list[str]:
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

    required_sections = [LEGS_FIELD]
    for section in required_sections:
        if section not in config_dict:
            config_dict[section] = []
            structure_added.append(f"empty_{section}_list")

    if not config_dict[LEGS_FIELD]:
        # Check for global-level ports to use in the leg
        departure_port = config_dict.get(DEPARTURE_PORT_FIELD, DEFAULT_DEPARTURE_PORT)
        arrival_port = config_dict.get(ARRIVAL_PORT_FIELD, DEFAULT_ARRIVAL_PORT)

        config_dict[LEGS_FIELD] = [
            {
                "name": "Main_Leg",
                "description": "Main cruise leg",
                DEPARTURE_PORT_FIELD: departure_port,
                ARRIVAL_PORT_FIELD: arrival_port,
            }
        ]

        # Remove global-level ports since they now belong to the leg
        if DEPARTURE_PORT_FIELD in config_dict:
            del config_dict[DEPARTURE_PORT_FIELD]
            structure_added.append("moved_global_departure_port_to_leg")
        if ARRIVAL_PORT_FIELD in config_dict:
            del config_dict[ARRIVAL_PORT_FIELD]
            structure_added.append("moved_global_arrival_port_to_leg")

        structure_added.append("default_main_leg")

    return structure_added


def _insert_missing_fields(
    config_dict: dict[str, Any], fields_to_add: list[tuple[str, Any, str]]
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
    if not fields_to_add:
        return

    if isinstance(config_dict, CommentedMap):
        keys = list(config_dict.keys())
        insert_index = 1 if "cruise_name" in keys else 0

        for field_name, value, _display_value in fields_to_add:
            config_dict.insert(insert_index, field_name, value)
            config_dict.yaml_add_eol_comment(
                " # default added by cruiseplan enrich", field_name
            )
            insert_index += 1
    else:
        config_dict.update(
            {field_name: value for field_name, value, _display_value in fields_to_add}
        )


# --- Station Name Utilities ---


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


# --- Coordinate Enrichment Utilities ---


def _add_ddm_coordinates(
    data_dict: dict[str, Any],
    lat: float,
    lon: float,
    coord_field_name: str,
    coord_format: str,
) -> tuple[Optional[str], int]:
    """
    Add DDM coordinates to a data dictionary with proper field positioning.

    Parameters
    ----------
    data_dict : dict[str, Any]
        Dictionary to add coordinates to.
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.
    coord_field_name : str
        Name of the coordinate field to add.
    coord_format : str
        Coordinate format to use.

    Returns
    -------
    tuple[Optional[str], int]
        Tuple of (ddm_comment_string, changes_made_count)
    """
    # Skip if data_dict is not a dictionary (e.g., a string port reference)
    if not isinstance(data_dict, dict):
        return None, 0

    if coord_format == "ddm":
        if coord_field_name not in data_dict or not data_dict.get(coord_field_name):
            ddm_comment = format_ddm_comment(lat, lon)

            # For ruamel.yaml CommentedMap, insert coordinates right after the name field
            if hasattr(data_dict, "insert"):
                # Strategy: Insert coordinates_ddm right after the 'name' field (which is required)
                if "name" in data_dict:
                    name_pos = list(data_dict.keys()).index("name")
                    insert_pos = name_pos + 1
                else:
                    # Fallback to beginning if no name field (shouldn't happen)
                    insert_pos = 0

                logger.debug(
                    f"Inserting {coord_field_name} at position {insert_pos} after 'name' field in {type(data_dict).__name__}"
                )
                data_dict.insert(insert_pos, coord_field_name, ddm_comment)
            else:
                # Fallback for regular dict
                data_dict[coord_field_name] = ddm_comment

            return ddm_comment, 1
    else:
        warnings.warn(
            f"Unknown coordinate format '{coord_format}' specified. No coordinates were added.",
            UserWarning,
        )
    return None, 0


# --- CTD Section Expansion Utilities ---


def _expand_single_ctd_section(
    transit: dict[str, Any], default_depth: float = -9999.0
) -> list[dict[str, Any]]:
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

    # TODO why not use Geopoint here?
    def _extract_coordinate_value(
        coord_dict: dict[str, Any], lat_keys: list[str], lon_keys: list[str]
    ) -> tuple[Optional[float], Optional[float]]:
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
        from cruiseplan.utils.plot_config import interpolate_great_circle_position

        fraction = i / (num_stations - 1) if num_stations > 1 else 0
        lat, lon = interpolate_great_circle_position(
            start_lat, start_lon, end_lat, end_lon, fraction
        )

        station = {
            "name": f"{base_name}_Stn{i+1:03d}",
            OP_TYPE_FIELD: "CTD",
            ACTION_FIELD: "profile",
            "latitude": round(lat, 5),  # Direct coordinate storage
            "longitude": round(lon, 5),  # Direct coordinate storage
            "comment": f"Station {i+1}/{num_stations} on {transit['name']} section",
            DURATION_FIELD: 120.0,  # Duration in minutes for consistency
        }

        # Copy additional fields if present, converting to modern field names
        if "max_depth" in transit:
            station[WATER_DEPTH_FIELD] = transit[
                "max_depth"
            ]  # Use semantic water_depth
        elif default_depth != -9999.0:
            # Use provided default depth if valid (not the placeholder value)
            station[WATER_DEPTH_FIELD] = default_depth
        # If no depth is specified, let enrichment process handle bathymetry lookup

        if "planned_duration_hours" in transit:
            # Convert hours to minutes for consistency
            station[DURATION_FIELD] = float(transit["planned_duration_hours"]) * 60.0
        if DURATION_FIELD in transit:
            station[DURATION_FIELD] = float(
                transit[DURATION_FIELD]
            )  # Already in minutes

        stations.append(station)

    logger.info(f"Expanded '{transit['name']}' into {len(stations)} stations")
    return stations


def expand_ctd_sections(
    config: dict[str, Any],
    default_depth: float = -9999.0,
) -> tuple[dict[str, Any], dict[str, int]]:
    """
    Expand CTD sections into individual station definitions.

    This function finds transits with Ctype="CTD" and action="section",
    expands them into individual stations along the route, and updates all
    references in legs to point to the new stations.

    Parameters
    ----------
    config : Dict[str, Any]
        The cruise configuration dictionary
    default_depth : float, optional
        Default depth value to use for stations. Default is -9999.0 (placeholder).

    Returns
    -------
    Tuple[Dict[str, Any], Dict[str, int]]
        Modified configuration and summary with sections_expanded and stations_from_expansion counts
    """
    if hasattr(config, "copy"):
        config = config.copy()
    else:
        import copy

        config = copy.copy(config)

    ctd_sections = []
    if LINES_FIELD in config:
        for transect in config[LINES_FIELD]:
            if (
                transect.get(OP_TYPE_FIELD) == "CTD"
                and transect.get(ACTION_FIELD) == "section"
            ):
                ctd_sections.append(transect)

    expanded_stations = {}
    total_stations_created = 0

    for section in ctd_sections:
        section_name = section["name"]
        new_stations = _expand_single_ctd_section(section, default_depth)

        if new_stations:
            if POINTS_FIELD not in config:
                if hasattr(config, "copy"):
                    config[POINTS_FIELD] = CommentedSeq()
                else:
                    config[POINTS_FIELD] = []

            existing_names = {
                s.get("name") for s in config[POINTS_FIELD] if s.get("name")
            }

            station_names = []
            for station in new_stations:
                station_name = station["name"]
                counter = 1
                original_name = station_name
                while station_name in existing_names:
                    station_name = f"{original_name}_{counter:02d}"
                    counter += 1

                station["name"] = station_name
                existing_names.add(station_name)

                if hasattr(config, "copy"):
                    if not isinstance(station, CommentedMap):
                        commented_station = CommentedMap(station)
                        station = commented_station

                config[POINTS_FIELD].append(station)

                if hasattr(config[POINTS_FIELD], "yaml_add_eol_comment"):
                    station_index = len(config[POINTS_FIELD]) - 1
                    config[POINTS_FIELD].yaml_add_eol_comment(
                        " expanded by cruiseplan enrich --expand-sections",
                        station_index,
                    )

                station_names.append(station_name)
                total_stations_created += 1

            expanded_stations[section_name] = station_names

    if LINES_FIELD in config and ctd_sections:
        config[LINES_FIELD] = [
            t
            for t in config[LINES_FIELD]
            if not (t.get(OP_TYPE_FIELD) == "CTD" and t.get(ACTION_FIELD) == "section")
        ]
        if not config[LINES_FIELD]:
            del config[LINES_FIELD]
    for leg in config.get(LEGS_FIELD, []):
        if (
            leg.get(FIRST_ACTIVITY_FIELD)
            and leg[FIRST_ACTIVITY_FIELD] in expanded_stations
        ):
            leg[FIRST_ACTIVITY_FIELD] = expanded_stations[leg[FIRST_ACTIVITY_FIELD]][0]
            logger.info(f"Updated leg first_activity to {leg[FIRST_ACTIVITY_FIELD]}")

        if (
            leg.get(LAST_ACTIVITY_FIELD)
            and leg[LAST_ACTIVITY_FIELD] in expanded_stations
        ):
            leg[LAST_ACTIVITY_FIELD] = expanded_stations[leg[LAST_ACTIVITY_FIELD]][-1]
            logger.info(f"Updated leg last_activity to {leg[LAST_ACTIVITY_FIELD]}")

        if leg.get(ACTIVITIES_FIELD):
            new_activities = []
            for item in leg[ACTIVITIES_FIELD]:
                if isinstance(item, str) and item in expanded_stations:
                    new_activities.extend(expanded_stations[item])
                    logger.info(
                        f"Expanded activities list: {item} → {expanded_stations[item]}"
                    )
                else:
                    new_activities.append(item)
            leg[ACTIVITIES_FIELD] = new_activities

        for cluster in leg.get(CLUSTERS_FIELD, []):
            # Note: sequence field has been removed - all references now use activities
            pass

    summary = {
        "sections_expanded": len(ctd_sections),
        "stations_from_expansion": total_stations_created,
    }

    return config, summary


def add_missing_required_fields(
    config_dict: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Add missing required fields with sensible defaults and provide user feedback.

    Inserts missing fields at the top of the configuration after cruise_name with
    appropriate comments indicating they were added by enrichment.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary loaded from YAML

    Returns
    -------
    Tuple[Dict[str, Any], List[str]]
        Updated configuration dictionary and list of fields that were added
    """
    all_defaults_added = []

    # Add all missing defaults (user parameters first, then technical parameters)
    fields_to_add, defaults_added = _add_missing_defaults(config_dict)
    all_defaults_added.extend(defaults_added)

    # Add port defaults
    port_defaults = _add_port_defaults(config_dict)
    all_defaults_added.extend(port_defaults)

    # Insert all missing fields with proper formatting (user params after cruise_name, technical params later)
    _insert_missing_fields(config_dict, fields_to_add)

    # Validate and add required structure
    structure_defaults = _validate_required_structure(config_dict)
    all_defaults_added.extend(structure_defaults)

    return config_dict, all_defaults_added


def add_missing_station_defaults(config_dict: dict[str, Any]) -> int:
    """
    Add missing defaults to station definitions.

    Adds default duration to mooring operations that lack this field.

    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary loaded from YAML

    Returns
    -------
    int
        Number of station defaults added
    """
    station_defaults_added = 0

    # Process points for missing defaults
    if POINTS_FIELD in config_dict:
        for station_data in config_dict[POINTS_FIELD]:
            # Check for mooring operations without duration
            if (
                station_data.get(OP_TYPE_FIELD) == "mooring"
                and DURATION_FIELD not in station_data
            ):
                station_name = station_data.get("name", "unnamed")

                # Add default mooring duration
                if isinstance(station_data, CommentedMap):
                    # Find appropriate position to insert duration (after operation_type if present)
                    keys = list(station_data.keys())
                    insert_index = len(keys)  # Default to end

                    if OP_TYPE_FIELD in keys:
                        insert_index = keys.index(OP_TYPE_FIELD) + 1
                    elif "name" in keys:
                        insert_index = keys.index("name") + 1

                    station_data.insert(
                        insert_index, DURATION_FIELD, DEFAULT_MOORING_DURATION_MIN
                    )
                    station_data.yaml_add_eol_comment(
                        "# default added by cruiseplan enrich", DURATION_FIELD
                    )
                else:
                    # Fallback for regular dict
                    station_data[DURATION_FIELD] = DEFAULT_MOORING_DURATION_MIN

                station_defaults_added += 1
                logger.warning(
                    f"⚠️ Added missing mooring duration to station '{station_name}': {DEFAULT_MOORING_DURATION_MIN} minutes (999 hours)"
                )

    return station_defaults_added


def _load_and_validate_config(
    config_path: Path, expand_sections: bool = False
) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    """
    Load, validate and preprocess cruise configuration.

    Parameters
    ----------
    config_path : Path
        Path to input YAML configuration.
    expand_sections : bool, optional
        Whether to expand CTD sections into individual stations.

    Returns
    -------
    tuple[dict[str, Any], Any, dict[str, Any]]
        Tuple of (config_dict, cruise, enrichment_summary_base)
    """
    # Import here to avoid circular dependencies
    from cruiseplan.core.cruise import Cruise

    # Load and preprocess the YAML configuration to replace placeholders
    config_dict = load_yaml(config_path)

    # Add missing required fields with sensible defaults
    config_dict, defaults_added = add_missing_required_fields(config_dict)

    # Add missing station-level defaults (e.g., mooring durations)
    station_defaults_added = add_missing_station_defaults(config_dict)

    # Expand CTD sections if requested
    sections_expanded = 0
    stations_from_expansion = 0
    if expand_sections:
        config_dict, expansion_summary = expand_ctd_sections(config_dict)
        sections_expanded = expansion_summary["sections_expanded"]
        stations_from_expansion = expansion_summary["stations_from_expansion"]

    # Create temporary file with processed config for Cruise loading
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as tmp_file:
        temp_config_path = Path(tmp_file.name)

    try:
        # Use comment-preserving YAML save for temp file
        save_yaml(config_dict, temp_config_path, backup=False)

        # Load cruise configuration with warning capture
        with _validation_warning_capture() as captured_warnings:
            cruise = Cruise(temp_config_path)
    finally:
        # Clean up temporary file safely
        if temp_config_path.exists():
            temp_config_path.unlink()

    enrichment_summary = {
        "stations_with_depths_added": 0,
        "stations_with_coords_added": 0,
        "sections_expanded": sections_expanded,
        "stations_from_expansion": stations_from_expansion,
        "ports_expanded": 0,
        "defaults_added": len(defaults_added),
        "station_defaults_added": station_defaults_added,
        "defaults_list": defaults_added,
        "total_stations_processed": len(cruise.point_registry),
    }

    return config_dict, cruise, enrichment_summary


def _enrich_station_depths(
    cruise, add_depths: bool, bathymetry_source: str, bathymetry_dir: str
) -> set[str]:
    """
    Add bathymetry depths to stations that are missing water_depth values.

    Parameters
    ----------
    cruise : Cruise
        Loaded cruise configuration object.
    add_depths : bool
        Whether to add depth values.
    bathymetry_source : str
        Bathymetry dataset to use.
    bathymetry_dir : str
        Directory containing bathymetry data.

    Returns
    -------
    set[str]
        Set of station names that had depths added.
    """
    stations_with_depths_added = set()

    if not add_depths:
        return stations_with_depths_added

    from cruiseplan.data.bathymetry import BathymetryManager

    # Initialize bathymetry manager
    bathymetry = BathymetryManager(source=bathymetry_source, data_dir=bathymetry_dir)

    # Process each station
    for station_name, station in cruise.point_registry.items():
        # Add water depths if requested (bathymetry enrichment targets water_depth field)
        should_add_water_depth = (
            not hasattr(station, "water_depth")
            or station.water_depth is None
            or station.water_depth == -9999.0  # Replace placeholder depth
        )
        if should_add_water_depth:
            depth = bathymetry.get_depth_at_point(station.latitude, station.longitude)
            if depth is not None and depth != 0:
                station.water_depth = round(
                    abs(depth)
                )  # Convert to positive depth, rounded to nearest meter
                stations_with_depths_added.add(station_name)
                logger.debug(
                    f"Added water depth {station.water_depth:.0f}m to station {station_name}"
                )

    return stations_with_depths_added


def _sync_depths_to_config(
    config_dict: dict[str, Any], cruise, stations_with_depths_added: set[str]
) -> None:
    """
    Update config_dict with depth values that were added to the Cruise object.

    This function synchronizes water_depth values from the Cruise object station
    registry back to the config_dict YAML structure, maintaining proper field
    positioning and comment preservation.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to modify.
    cruise : Cruise
        Loaded cruise configuration object with updated depths.
    stations_with_depths_added : set[str]
        Station names that had depths added.
    """
    if POINTS_FIELD in config_dict:
        for station_data in config_dict[POINTS_FIELD]:
            station_name = station_data["name"]
            if (
                station_name in cruise.point_registry
                and station_name in stations_with_depths_added
            ):
                station_obj = cruise.point_registry[station_name]
                # Add water_depth field with careful placement after name field
                water_depth_value = float(station_obj.water_depth)

                if hasattr(station_data, "insert"):
                    # Position water_depth after the 'name' field for consistent structure
                    if "name" in station_data:
                        name_pos = list(station_data.keys()).index("name")
                        insert_pos = name_pos + 1
                    else:
                        insert_pos = 0

                    logger.debug(
                        f"Inserting water_depth at position {insert_pos} after 'name' field"
                    )
                    station_data.insert(
                        insert_pos, WATER_DEPTH_FIELD, water_depth_value
                    )
                else:
                    # Fallback for regular dict
                    station_data[WATER_DEPTH_FIELD] = water_depth_value


def _enrich_station_coordinates(
    config_dict: dict[str, Any],
    cruise,
    add_coords: bool,
    coord_format: str,
) -> int:
    """
    Add coordinate fields to stations in the config dictionary.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to modify.
    cruise : Cruise
        Loaded cruise configuration object.
    add_coords : bool
        Whether to add coordinate fields.
    coord_format : str
        Coordinate format to use.

    Returns
    -------
    int
        Number of coordinate changes made.
    """
    coord_changes_made = 0

    # Process coordinate additions for stations
    if POINTS_FIELD in config_dict:
        for station_data in config_dict[POINTS_FIELD]:
            station_name = station_data["name"]
            if station_name in cruise.point_registry:
                station_obj = cruise.point_registry[station_name]

                # Add coordinate fields if requested
                if add_coords:
                    ddm_result, changes_count = _add_ddm_coordinates(
                        station_data,
                        station_obj.latitude,
                        station_obj.longitude,
                        "coordinates_ddm",
                        coord_format,
                    )
                    coord_changes_made += changes_count
                    if ddm_result:
                        logger.debug(
                            f"Added ddm coordinates to station {station_name}: {ddm_result}"
                        )

    return coord_changes_made


def _enrich_port_coordinates(
    config_dict: dict[str, Any], cruise, add_coords: bool, coord_format: str
) -> int:
    """
    Add coordinate fields to departure and arrival ports.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to modify.
    cruise : Cruise
        Loaded cruise configuration object.
    add_coords : bool
        Whether to add coordinate fields.
    coord_format : str
        Coordinate format to use.

    Returns
    -------
    int
        Number of coordinate changes made.
    """
    coord_changes_made = 0

    # Process coordinate additions for departure and arrival ports
    if add_coords:
        for port_key in [DEPARTURE_PORT_FIELD, ARRIVAL_PORT_FIELD]:
            if config_dict.get(port_key):
                port_data = config_dict[port_key]
                # Use literal attribute names for Pydantic model access
                attr_name = (
                    "departure_port"
                    if port_key == DEPARTURE_PORT_FIELD
                    else "arrival_port"
                )
                if hasattr(cruise.config, attr_name):
                    port_obj = getattr(cruise.config, attr_name)
                    if hasattr(port_obj, "latitude") and hasattr(port_obj, "longitude"):
                        ddm_result, changes_count = _add_ddm_coordinates(
                            port_data,
                            port_obj.latitude,
                            port_obj.longitude,
                            "coordinates_ddm",
                            coord_format,
                        )
                        coord_changes_made += changes_count
                        if ddm_result:
                            logger.debug(
                                f"Added ddm coordinates to {port_key}: {ddm_result}"
                            )

    return coord_changes_made


def _enrich_transit_coordinates(config_dict: dict[str, Any], add_coords: bool) -> int:
    """
    Add coordinate fields to transit routes.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to modify.
    add_coords : bool
        Whether to add coordinate fields.

    Returns
    -------
    int
        Number of coordinate changes made.
    """
    from cruiseplan.utils.coordinates import format_ddm_comment

    coord_changes_made = 0

    # Process coordinate additions for transect routes
    if add_coords and LINES_FIELD in config_dict:
        for transect_data in config_dict[LINES_FIELD]:
            if transect_data.get(LINE_VERTEX_FIELD):
                # Add route_ddm field with list of position_ddm entries
                if "route_ddm" not in transect_data:
                    route_ddm_list = []
                    for point in transect_data[LINE_VERTEX_FIELD]:
                        if "latitude" in point and "longitude" in point:
                            ddm_comment = format_ddm_comment(
                                point["latitude"], point["longitude"]
                            )
                            route_ddm_list.append({"position_ddm": ddm_comment})
                            coord_changes_made += 1

                    if route_ddm_list:
                        transect_data["route_ddm"] = route_ddm_list
                        logger.debug(
                            f"Added ddm coordinates to transect {transect_data.get('name', 'unnamed')} route: {len(route_ddm_list)} points"
                        )

    return coord_changes_made


def _enrich_area_coordinates(config_dict: dict[str, Any], add_coords: bool) -> int:
    """
    Add coordinate fields to area corners.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to modify.
    add_coords : bool
        Whether to add coordinate fields.

    Returns
    -------
    int
        Number of coordinate changes made.
    """
    from cruiseplan.utils.coordinates import format_ddm_comment

    coord_changes_made = 0

    # Process coordinate additions for area corners
    if add_coords and AREAS_FIELD in config_dict:
        for area_data in config_dict[AREAS_FIELD]:
            if area_data.get(AREA_VERTEX_FIELD):
                # Add corners_ddm field with list of position_ddm entries
                if "corners_ddm" not in area_data:
                    corners_ddm_list = []
                    for corner in area_data[AREA_VERTEX_FIELD]:
                        if "latitude" in corner and "longitude" in corner:
                            ddm_comment = format_ddm_comment(
                                corner["latitude"], corner["longitude"]
                            )
                            corners_ddm_list.append({"position_ddm": ddm_comment})
                            coord_changes_made += 1

                    if corners_ddm_list:
                        area_data["corners_ddm"] = corners_ddm_list
                        logger.debug(
                            f"Added ddm coordinates to area {area_data.get('name', 'unnamed')} corners: {len(corners_ddm_list)} points"
                        )

    return coord_changes_made


def _expand_port_references(
    config_dict: dict[str, Any], expand_ports: bool
) -> dict[str, int]:
    """
    Expand global port references into port catalog and leg definitions.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to modify.
    expand_ports : bool
        Whether to expand port references.

    Returns
    -------
    dict[str, int]
        Dictionary with 'ports_expanded' and 'leg_ports_expanded' counts.
    """
    ports_expanded_count = 0
    leg_ports_expanded = 0

    # Expand global port references to ports catalog if requested
    if expand_ports:
        # Create ports catalog section if it doesn't exist
        if "ports" not in config_dict:
            config_dict["ports"] = []

        # Track which ports we've already added to avoid duplicates
        existing_port_names = {port.get("name", "") for port in config_dict["ports"]}

        # Collect all port references from cruise-level and leg-level
        port_references = set()

        # Check cruise-level ports
        for port_field in [DEPARTURE_PORT_FIELD, ARRIVAL_PORT_FIELD]:
            if port_field in config_dict and isinstance(config_dict[port_field], str):
                port_ref = config_dict[port_field]
                if port_ref.startswith("port_"):
                    port_references.add(port_ref)

        # Check leg-level ports
        if LEGS_FIELD in config_dict:
            for leg_data in config_dict[LEGS_FIELD]:
                for port_field in [DEPARTURE_PORT_FIELD, ARRIVAL_PORT_FIELD]:
                    if port_field in leg_data and isinstance(leg_data[port_field], str):
                        port_ref = leg_data[port_field]
                        if port_ref.startswith("port_"):
                            port_references.add(port_ref)

        # Resolve each unique port reference and add to catalog
        for port_ref in port_references:
            if port_ref not in existing_port_names:
                try:
                    port_definition = resolve_port_reference(port_ref)
                    # Add to ports catalog with display_name from global registry
                    catalog_port = {
                        "name": port_ref,  # Keep the full port_* name as catalog identifier
                        "latitude": port_definition.latitude,
                        "longitude": port_definition.longitude,
                        OP_TYPE_FIELD: "port",  # Explicitly set operation_type for ports
                    }
                    # Add display_name if available
                    if hasattr(port_definition, "display_name"):
                        catalog_port["display_name"] = port_definition.display_name
                    elif hasattr(port_definition, "name"):
                        catalog_port["display_name"] = port_definition.name

                    config_dict["ports"].append(catalog_port)
                    ports_expanded_count += 1
                    logger.debug(
                        f"Added port '{port_ref}' to catalog as '{catalog_port.get('display_name', port_ref)}'"
                    )
                except ValueError as e:
                    logger.warning(
                        f"Could not resolve port reference '{port_ref}': {e}"
                    )

        # Expand leg-level port references into full port definitions with actions
        if LEGS_FIELD in config_dict:
            for leg_data in config_dict[LEGS_FIELD]:
                # Expand departure_port
                if DEPARTURE_PORT_FIELD in leg_data and isinstance(
                    leg_data[DEPARTURE_PORT_FIELD], str
                ):
                    port_ref = leg_data[DEPARTURE_PORT_FIELD]
                    if port_ref.startswith("port_"):
                        try:
                            port_definition = resolve_port_reference(port_ref)
                            # Replace string reference with full port definition
                            leg_data[DEPARTURE_PORT_FIELD] = {
                                "name": port_ref,
                                "latitude": port_definition.latitude,
                                "longitude": port_definition.longitude,
                                OP_TYPE_FIELD: "port",
                                ACTION_FIELD: "mob",  # Departure ports are mobilization
                            }
                            if hasattr(port_definition, "display_name"):
                                leg_data[DEPARTURE_PORT_FIELD][
                                    "display_name"
                                ] = port_definition.display_name
                            elif hasattr(port_definition, "name"):
                                leg_data[DEPARTURE_PORT_FIELD][
                                    "display_name"
                                ] = port_definition.name
                            leg_ports_expanded += 1
                            logger.debug(
                                f"Expanded departure_port '{port_ref}' with action 'mob'"
                            )
                        except ValueError as e:
                            logger.warning(
                                f"Could not expand departure_port '{port_ref}': {e}"
                            )

                # Expand arrival_port
                if ARRIVAL_PORT_FIELD in leg_data and isinstance(
                    leg_data[ARRIVAL_PORT_FIELD], str
                ):
                    port_ref = leg_data[ARRIVAL_PORT_FIELD]
                    if port_ref.startswith("port_"):
                        try:
                            port_definition = resolve_port_reference(port_ref)
                            # Replace string reference with full port definition
                            leg_data[ARRIVAL_PORT_FIELD] = {
                                "name": port_ref,
                                "latitude": port_definition.latitude,
                                "longitude": port_definition.longitude,
                                OP_TYPE_FIELD: "port",
                                ACTION_FIELD: "demob",  # Arrival ports are demobilization
                            }
                            if hasattr(port_definition, "display_name"):
                                leg_data[ARRIVAL_PORT_FIELD][
                                    "display_name"
                                ] = port_definition.display_name
                            elif hasattr(port_definition, "name"):
                                leg_data[ARRIVAL_PORT_FIELD][
                                    "display_name"
                                ] = port_definition.name
                            leg_ports_expanded += 1
                            logger.debug(
                                f"Expanded arrival_port '{port_ref}' with action 'demob'"
                            )
                        except ValueError as e:
                            logger.warning(
                                f"Could not expand arrival_port '{port_ref}': {e}"
                            )

    return {
        "ports_expanded": ports_expanded_count,
        "leg_ports_expanded": leg_ports_expanded,
    }


def _process_warnings_and_save(
    config_dict: dict[str, Any],
    captured_warnings: list[str],
    cruise,
    output_path: Optional[Path],
) -> None:
    """
    Process captured warnings and save configuration to file.

    Parameters
    ----------
    config_dict : dict[str, Any]
        Configuration dictionary to save.
    captured_warnings : list[str]
        List of captured warning messages.
    cruise : Cruise
        Loaded cruise configuration object.
    output_path : Optional[Path]
        Path for output file (if None, no save).
    """
    # Process captured warnings and display them in user-friendly format
    if captured_warnings:
        # Keep this import conditional as it might create circular dependencies
        from cruiseplan.processing.validate import _format_validation_warnings

        formatted_warnings = _format_validation_warnings(captured_warnings, cruise)
        for warning_group in formatted_warnings:
            logger.warning("⚠️ Configuration Warnings:")
            for line in warning_group.split("\n"):
                if line.strip():
                    logger.warning(f"  {line}")
            logger.warning("")  # Add spacing between warning groups

    # Save enriched configuration if output path is specified
    if output_path:
        save_yaml(config_dict, output_path, backup=False)


def _build_enrichment_summary(
    base_summary: dict[str, Any],
    stations_with_depths_added: set[str],
    coord_changes_made: int,
    port_summary: dict[str, int],
) -> dict[str, Any]:
    """
    Build final enrichment summary with all counts.

    Parameters
    ----------
    base_summary : dict[str, Any]
        Base summary dictionary from loading.
    stations_with_depths_added : set[str]
        Station names that had depths added.
    coord_changes_made : int
        Number of coordinate changes made.
    port_summary : dict[str, int]
        Port expansion summary.

    Returns
    -------
    dict[str, Any]
        Complete enrichment summary.
    """
    base_summary["stations_with_depths_added"] = len(stations_with_depths_added)
    base_summary["stations_with_coords_added"] = coord_changes_made
    base_summary.update(port_summary)
    return base_summary


def enrich_configuration(
    config_path: Path,
    add_depths: bool = False,
    add_coords: bool = False,
    expand_sections: bool = False,
    expand_ports: bool = False,
    bathymetry_source: str = "etopo2022",
    bathymetry_dir: str = "data",
    coord_format: str = "ddm",
    output_path: Optional[Path] = None,
) -> dict[str, Any]:
    """
    Add missing data to cruise configuration.

    Enriches the cruise configuration by adding bathymetric depths and
    formatted coordinates where missing.

    Parameters
    ----------
    config_path : Path
        Path to input YAML configuration.
    add_depths : bool, optional
        Whether to add missing depth values (default: False).
    add_coords : bool, optional
        Whether to add formatted coordinate fields (default: False).
    expand_sections : bool, optional
        Whether to expand CTD sections into individual stations (default: False).
    expand_ports : bool, optional
        Whether to expand global port references into full PortDefinition objects (default: False).
    bathymetry_source : str, optional
        Bathymetry dataset to use (default: "etopo2022").
    coord_format : str, optional
        Coordinate format ("ddm" or "dms", default: "ddm").
    output_path : Optional[Path], optional
        Path for output file (if None, modifies in place).

    Returns
    -------
    Dict[str, Any]
        Dictionary with enrichment summary containing:
        - stations_with_depths_added: Number of depths added
        - stations_with_coords_added: Number of coordinates added
        - sections_expanded: Number of CTD sections expanded
        - stations_from_expansion: Number of stations generated from expansion
        - total_stations_processed: Total stations processed
    """
    # Load, validate, and preprocess configuration
    config_dict, cruise, enrichment_summary = _load_and_validate_config(
        config_path, expand_sections
    )

    # Capture warnings during enrichment
    with _validation_warning_capture() as captured_warnings:
        # Add depths to stations if requested
        stations_with_depths_added = _enrich_station_depths(
            cruise, add_depths, bathymetry_source, bathymetry_dir
        )

        # Sync depth changes from Cruise object back to config_dict
        _sync_depths_to_config(config_dict, cruise, stations_with_depths_added)

        # Initialize coordinate change tracking
        coord_changes_made = 0

        # Add coordinates if requested
        if add_coords:
            coord_changes_made += _enrich_station_coordinates(
                config_dict,
                cruise,
                add_coords,
                coord_format,
            )
            coord_changes_made += _enrich_port_coordinates(
                config_dict, cruise, add_coords, coord_format
            )
            coord_changes_made += _enrich_transit_coordinates(config_dict, add_coords)
            coord_changes_made += _enrich_area_coordinates(config_dict, add_coords)

        # Expand port references if requested
        port_summary = _expand_port_references(config_dict, expand_ports)

        # Build final enrichment summary
        final_summary = _build_enrichment_summary(
            enrichment_summary,
            stations_with_depths_added,
            coord_changes_made,
            port_summary,
        )

        # Process warnings and save configuration
        _process_warnings_and_save(config_dict, captured_warnings, cruise, output_path)

        return final_summary
