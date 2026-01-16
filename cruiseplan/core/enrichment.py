"""
Cruise configuration enrichment functions.

This module contains functions for enriching cruise configurations by adding
missing data like depths, coordinate displays, and expanding sections into
individual stations. These functions operate on CruiseInstance objects.
"""

import logging
from typing import TYPE_CHECKING

from cruiseplan.data.bathymetry import BathymetryManager

if TYPE_CHECKING:
    from cruiseplan.core.cruise import CruiseInstance

logger = logging.getLogger(__name__)


def _sanitize_name_for_stations(name: str) -> str:
    """
    Sanitize a name for use as a station name base.

    Removes special characters, converts Unicode to ASCII, and ensures
    the result contains only alphanumeric characters and underscores.

    Parameters
    ----------
    name : str
        Original name to sanitize.

    Returns
    -------
    str
        Sanitized name suitable for station naming.
    """
    import re
    import unicodedata

    # Convert Unicode to ASCII equivalent
    name = unicodedata.normalize("NFD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    # Replace common separators and special chars with underscores
    name = re.sub(r"[^\w\s]", "_", name)  # Replace non-word chars (except spaces)
    name = re.sub(r"\s+", "_", name)  # Replace spaces with underscores

    # Clean up multiple consecutive underscores
    name = re.sub(r"_+", "_", name)

    # Remove leading and trailing underscores
    name = name.strip("_")

    # If name becomes empty, provide a fallback
    if not name:
        name = "Section"

    return name


def _generate_unique_name(base_name: str, point_registry: dict) -> str:
    """
    Generate a unique name by checking against existing point registry.

    If the base name already exists, append _01, _02, etc. until a unique name is found.

    Parameters
    ----------
    base_name : str
        The base name to make unique.
    point_registry : dict
        Dictionary of existing point names to check against.

    Returns
    -------
    str
        A unique name that doesn't exist in the point registry.
    """
    if base_name not in point_registry:
        return base_name

    # Name exists, find unique suffix (using legacy format _01, _02, etc.)
    counter = 1
    while f"{base_name}_{counter:02d}" in point_registry:
        counter += 1

    return f"{base_name}_{counter:02d}"


def _update_leg_activities_for_expanded_section(
    cruise_instance: "CruiseInstance", section_name: str, station_names: list[str]
) -> None:
    """
    Update leg activities to replace expanded section with station names.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to modify.
    section_name : str
        Name of the section that was expanded.
    station_names : list[str]
        Names of the stations created from the expansion.
    """
    for leg in cruise_instance.config.legs:
        # Update activities list - activities are resolved objects, not strings
        if hasattr(leg, "activities") and leg.activities:
            updated_activities = []
            for activity in leg.activities:
                # Check if this activity object has the name we're looking for
                if hasattr(activity, "name") and activity.name == section_name:
                    # Replace with PointDefinition objects from registry
                    for station_name in station_names:
                        if station_name in cruise_instance.point_registry:
                            updated_activities.append(
                                cruise_instance.point_registry[station_name]
                            )
                else:
                    updated_activities.append(activity)
            leg.activities = updated_activities

        # Update first_activity if it points to the expanded section
        if hasattr(leg, "first_activity") and leg.first_activity:
            # Handle both string references and resolved objects
            activity_name = (
                leg.first_activity.name
                if hasattr(leg.first_activity, "name")
                else leg.first_activity
            )
            if activity_name == section_name:
                leg.first_activity = cruise_instance.point_registry[station_names[0]]

        # Update last_activity if it points to the expanded section
        if hasattr(leg, "last_activity") and leg.last_activity:
            # Handle both string references and resolved objects
            activity_name = (
                leg.last_activity.name
                if hasattr(leg.last_activity, "name")
                else leg.last_activity
            )
            if activity_name == section_name:
                leg.last_activity = cruise_instance.point_registry[station_names[-1]]


def expand_sections(
    cruise_instance: "CruiseInstance", default_depth: float = -9999.0
) -> dict[str, int]:
    """
    Expand CTD sections into individual station definitions.

    This method finds CTD sections in lines catalog and expands them into
    individual stations, adding them to the point_registry. This is structural
    enrichment that modifies the cruise configuration.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to modify
    default_depth : float, optional
        Default depth value for expanded stations. Default is -9999.0.

    Returns
    -------
    dict[str, int]
        Dictionary with expansion summary:
        - sections_expanded: Number of sections expanded
        - stations_from_expansion: Number of stations created
    """
    sections_expanded = 0
    total_stations_created = 0

    # Find CTD sections in lines catalog
    ctd_sections = []
    for line_name, line_def in cruise_instance.line_registry.items():
        if (
            hasattr(line_def, "operation_type")
            and line_def.operation_type == "CTD"
            and hasattr(line_def, "action")
            and line_def.action == "section"
        ):
            ctd_sections.append(
                {
                    "name": line_name,
                    "route": line_def.route,
                    "distance_between_stations": (
                        getattr(line_def, "distance_between_stations", None) or 20.0
                    ),
                    "max_depth": getattr(line_def, "max_depth", None),
                    "planned_duration_hours": getattr(
                        line_def, "planned_duration_hours", None
                    ),
                    "duration": getattr(line_def, "duration", None),
                }
            )

    # Expand each section
    sections_to_remove = []
    for section in ctd_sections:
        route = section["route"]
        distance_km = section["distance_between_stations"]
        section_name = section["name"]

        # Sanitize section name for station naming
        base_name = _sanitize_name_for_stations(section_name)

        # Calculate stations along the route using original inline logic
        from cruiseplan.calculators.distance import haversine_distance
        from cruiseplan.utils.plot_config import interpolate_great_circle_position

        if not route or len(route) < 2:
            logger.warning(f"No valid route for section {section_name}")
            continue

        start = route[0]
        end = route[-1]

        # Extract coordinates from GeoPoint objects
        start_lat = start.latitude
        start_lon = start.longitude
        end_lat = end.latitude
        end_lon = end.longitude

        if any(coord is None for coord in [start_lat, start_lon, end_lat, end_lon]):
            logger.warning(f"Invalid coordinates for section {section_name}")
            continue

        total_distance_km = haversine_distance(
            (start_lat, start_lon), (end_lat, end_lon)
        )
        num_stations = max(2, int(total_distance_km / distance_km) + 1)

        # Create station definitions for each calculated position
        stations_created = 0
        station_names_created = []
        for ii in range(num_stations):
            # Calculate position along great circle route
            fraction = ii / (num_stations - 1) if num_stations > 1 else 0
            lat, lon = interpolate_great_circle_position(
                start_lat, start_lon, end_lat, end_lon, fraction
            )

            # Generate unique station name (handle duplicates)
            base_station_name = f"{base_name}_Stn{ii+1:03d}"
            station_name = _generate_unique_name(
                base_station_name, cruise_instance.point_registry
            )

            # Create PointDefinition
            from cruiseplan.schema.activities import PointDefinition

            station_attrs = {
                "name": station_name,
                "latitude": round(lat, 5),
                "longitude": round(lon, 5),
                "operation_type": "CTD",
                "action": "profile",
                "history": f"expanded from line operation: {section_name};",
            }

            # Add depth information
            if section["max_depth"] is not None:
                station_attrs["water_depth"] = section["max_depth"]
            # Skip setting water_depth if using default sentinel value

            # Add duration information
            if section["duration"] is not None:
                station_attrs["duration"] = section["duration"]
            elif section["planned_duration_hours"] is not None:
                station_attrs["duration"] = f"{section['planned_duration_hours']}h"

            # Create and register the station
            station = PointDefinition(**station_attrs)
            cruise_instance.point_registry[station_name] = station
            station_names_created.append(station_name)
            stations_created += 1

        if stations_created > 0:
            # Update leg activities to reference expanded stations
            _update_leg_activities_for_expanded_section(
                cruise_instance, section_name, station_names_created
            )

            sections_to_remove.append(section_name)
            total_stations_created += stations_created
            sections_expanded += 1
            logger.info(
                f"Expanded section {section_name}: {stations_created} stations created"
            )

    # Remove expanded sections from line registry
    for section_name in sections_to_remove:
        del cruise_instance.line_registry[section_name]

    logger.info(
        f"Section expansion complete: {sections_expanded} sections → {total_stations_created} stations"
    )

    return {
        "sections_expanded": sections_expanded,
        "stations_from_expansion": total_stations_created,
    }


def add_station_defaults(cruise_instance: "CruiseInstance") -> int:
    """
    Add missing defaults to station definitions.

    This function adds default values for station fields based on operation type
    and scientific best practices. Currently focuses on mooring duration defaults.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to modify

    Returns
    -------
    int
        Number of stations that had defaults added
    """
    defaults_added = 0

    for station_name, station in cruise_instance.point_registry.items():
        # Add mooring duration defaults
        if (
            hasattr(station, "operation_type")
            and station.operation_type == "mooring"
            and (not hasattr(station, "duration") or station.duration is None)
        ):
            # Default mooring deployment/recovery duration: 999 hours (59940 minutes)
            from cruiseplan.schema.values import DEFAULT_MOORING_DURATION_MIN

            station.__dict__["duration"] = DEFAULT_MOORING_DURATION_MIN
            defaults_added += 1
            logger.debug(
                f"Added default duration to mooring {station_name}: {DEFAULT_MOORING_DURATION_MIN} min"
            )

        # Add other operation-specific defaults as needed
        # Future: CTD cast duration defaults, transit speed defaults, etc.

    if defaults_added > 0:
        logger.info(f"Added defaults to {defaults_added} stations")

    return defaults_added


def enrich_depths(
    cruise_instance: "CruiseInstance",
    bathymetry_source: str = "etopo2022",
    bathymetry_dir: str = "data",
) -> set[str]:
    """
    Add missing depth values to stations using bathymetry data.

    This function queries bathymetry data to fill in missing water depth values
    for stations that don't have them specified.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to modify
    bathymetry_source : str, optional
        Bathymetry dataset to use (default: "etopo2022")
    bathymetry_dir : str, optional
        Directory containing bathymetry data (default: "data")

    Returns
    -------
    set[str]
        Set of station names that had depths added
    """
    stations_with_depths_added = set()

    # Initialize bathymetry manager
    bathymetry = BathymetryManager(source=bathymetry_source, data_dir=bathymetry_dir)

    for station_name, station in cruise_instance.point_registry.items():
        # Check if station already has water_depth
        if hasattr(station, "water_depth") and station.water_depth is not None:
            continue

        # Get depth from bathymetry
        try:
            bathymetry_depth = bathymetry.get_depth_at_point(
                station.latitude, station.longitude
            )

            if bathymetry_depth is not None:
                # Convert to positive depth value (bathymetry returns negative elevation)
                water_depth = abs(bathymetry_depth)

                # Add depth to station
                station.__dict__["water_depth"] = water_depth
                stations_with_depths_added.add(station_name)

                logger.debug(f"Added depth to {station_name}: {water_depth:.1f}m")

        except Exception as e:
            logger.warning(f"Failed to get depth for station {station_name}: {e}")
            continue

    if stations_with_depths_added:
        logger.info(
            f"Added depths to {len(stations_with_depths_added)} stations using {bathymetry_source}"
        )

    return stations_with_depths_added


def expand_ports(cruise_instance: "CruiseInstance") -> dict[str, int]:
    """
    Expand global port references into full PortDefinition objects.

    This function processes port references in the cruise configuration and
    expands them into full port definitions with coordinates and metadata.

    Note: In v0.3.4+ architecture, ports are automatically resolved during
    CruiseInstance creation, so this function may be largely redundant.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to modify

    Returns
    -------
    dict[str, int]
        Dictionary with expansion summary:
        - ports_expanded: Number of port references expanded
        - ports_added: Number of port definitions added
    """
    ports_expanded = 0
    ports_added = 0

    # This functionality is now handled during CruiseInstance initialization
    # Port references are automatically resolved to full PortDefinition objects
    # when the configuration is loaded.

    logger.debug("Port expansion is handled automatically during configuration loading")

    return {
        "ports_expanded": ports_expanded,
        "ports_added": ports_added,
    }


def add_coordinate_displays(
    cruise_instance: "CruiseInstance", coord_format: str = "ddm"
) -> int:
    """
    Add human-readable coordinate display fields for final YAML output.

    This function adds formatted coordinate fields (latitude_display, longitude_display)
    to all geographic entities (stations, ports, etc.) for better human readability
    in generated YAML files.

    Parameters
    ----------
    cruise_instance : CruiseInstance
        The cruise instance to modify
    coord_format : str, optional
        Coordinate format ("ddm" for degrees/decimal minutes, "dms" for degrees/minutes/seconds)
        Default is "ddm".

    Returns
    -------
    int
        Number of entities that had coordinate displays added
    """
    coord_changes_made = 0

    # Add coordinate displays for points that have coordinates but lack display fields
    for _, point in cruise_instance.point_registry.items():
        if (
            hasattr(point, "latitude")
            and hasattr(point, "longitude")
            and point.latitude is not None
            and point.longitude is not None
        ):
            # For now, we'll add the coordinate display as a "position_string" field
            # This will be used for display purposes in the output
            if coord_format == "ddm":
                from cruiseplan.utils.coordinates import format_ddm_comment

                position_display = format_ddm_comment(point.latitude, point.longitude)
                # Set the position string for display (this gets used in YAML output)
                point.position_string = position_display
                coord_changes_made += 1

    return coord_changes_made
