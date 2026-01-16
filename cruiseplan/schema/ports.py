"""
Global port configuration system for maritime cruise planning.

This module provides a registry of common maritime ports with their coordinates,
timezones, and metadata. Users can reference these ports by standard identifiers
(e.g., 'port_reykjavik') or override them with custom definitions in their YAML.

Features:
- Standard port registry with common research cruise destinations
- Timezone information for port operations
- Extensible system allowing user-defined port overrides
- Support for both string references and PointDefinition objects

Usage:
    # In YAML configuration
    departure_port: "port_reykjavik"  # Reference to global port

    # Or override with custom definition
    departure_port:
      name: "Reykjavik_Custom"
      latitude: 64.1466
      longitude: -21.9426
      timezone: "GMT+0"
      comment: "Custom port definition"
"""

import warnings
from typing import Union

from pydantic import ValidationError

# Global port registry with common maritime research destinations
GLOBAL_PORTS: dict[str, dict[str, Union[str, float]]] = {
    # North Atlantic Research Ports
    "port_reykjavik": {
        "name": "Reykjavik",
        "display_name": "Reykjavik, Iceland",
        "latitude": 64.1466,
        "longitude": -21.9426,
        "timezone": "Atlantic/Reykjavik",
    },
    "port_nuuk": {
        "name": "Nuuk",
        "display_name": "Nuuk, Greenland",
        "latitude": 64.1836,
        "longitude": -51.7214,
        "timezone": "GMT-3",
    },
    # Norwegian Research Ports
    "port_tromso": {
        "name": "Tromsø",
        "display_name": "Tromsø, Norway",
        "latitude": 69.6496,
        "longitude": 18.9553,
        "timezone": "Europe/Oslo",
    },
    "port_trondheim": {
        "name": "Trondheim",
        "display_name": "Trondheim, Norway",
        "latitude": 63.4305,
        "longitude": 10.3951,
        "timezone": "Europe/Oslo",
    },
    "port_bergen": {
        "name": "Bergen",
        "display_name": "Bergen, Norway",
        "latitude": 60.3913,
        "longitude": 5.3221,
        "timezone": "Europe/Oslo",
    },
    # UK Research Ports
    "port_southampton": {
        "name": "Southampton",
        "display_name": "Southampton, UK",
        "latitude": 50.9097,
        "longitude": -1.4044,
        "timezone": "GMT+0",
    },
    # German Research Ports
    "port_bremerhaven": {
        "name": "Bremerhaven",
        "display_name": "Bremerhaven, Germany",
        "latitude": 53.5395,
        "longitude": 8.5809,
        "timezone": "Europe/Berlin",
    },
    "port_hamburg": {
        "name": "Hamburg",
        "display_name": "Hamburg, Germany",
        "latitude": 53.53490,
        "longitude": 9.97992,
        "timezone": "Europe/Berlin",
    },
    "port_emden": {
        "name": "Emden",
        "display_name": "Emden, Germany",
        "latitude": 53.3594,
        "longitude": 7.2067,
        "timezone": "Europe/Berlin",
    },
    "port_rostock": {
        "name": "Rostock",
        "display_name": "Rostock, Germany",
        "latitude": 54.0887,
        "longitude": 12.1308,
        "timezone": "Europe/Berlin",
    },
    "port_kiel": {
        "name": "Kiel",
        "display_name": "Kiel, Germany",
        "latitude": 54.3233,
        "longitude": 10.1394,
        "timezone": "Europe/Berlin",
    },
    # French Research Ports
    "port_brest": {
        "name": "Brest",
        "display_name": "Brest, France",
        "latitude": 48.3905,
        "longitude": -4.4860,
        "timezone": "Europe/Paris",
    },
    "port_nice": {
        "name": "Nice",
        "display_name": "Nice, France",
        "latitude": 43.7102,
        "longitude": 7.2620,
        "timezone": "Europe/Paris",
    },
    # Spanish Research Ports
    "port_vigo": {
        "name": "Vigo",
        "display_name": "Vigo, Spain",
        "latitude": 42.2406,
        "longitude": -8.7207,
        "timezone": "Europe/Madrid",
    },
    "port_cadiz": {
        "name": "Cadiz",
        "display_name": "Cadiz, Spain",
        "latitude": 36.5298,
        "longitude": -6.2923,
        "timezone": "Europe/Madrid",
    },
    "port_malaga": {
        "name": "Malaga",
        "display_name": "Malaga, Spain",
        "latitude": 36.7196,
        "longitude": -4.4204,
        "timezone": "Europe/Madrid",
    },
    # Mediterranean Research Ports
    "port_heraklion": {
        "name": "Heraklion",
        "display_name": "Heraklion, Crete",
        "latitude": 35.3387,
        "longitude": 25.1442,
        "timezone": "Europe/Athens",
    },
    "port_catania": {
        "name": "Catania",
        "display_name": "Catania, Italy",
        "latitude": 37.5079,
        "longitude": 15.0830,
        "timezone": "Europe/Rome",
    },
    "port_limassol": {
        "name": "Limassol",
        "display_name": "Limassol, Cyprus",
        "latitude": 34.6823,
        "longitude": 33.0464,
        "timezone": "Asia/Nicosia",
    },
    # Atlantic Islands Research Ports
    "port_las_palmas": {
        "name": "Las Palmas",
        "display_name": "Las Palmas, Canary Islands",
        "latitude": 28.1248,
        "longitude": -15.4300,
        "timezone": "Atlantic/Canary",
    },
    "port_ponta_delgada": {
        "name": "Ponta Delgada",
        "display_name": "Ponta Delgada, Azores",
        "latitude": 37.7412,
        "longitude": -25.6756,
        "timezone": "Atlantic/Azores",
    },
    "port_funchal": {
        "name": "Funchal",
        "display_name": "Funchal, Madeira",
        "latitude": 32.6669,
        "longitude": -16.9241,
        "timezone": "Atlantic/Madeira",
    },
    # African Research Ports
    "port_mindelo": {
        "name": "Mindelo",
        "display_name": "Mindelo, Cape Verde",
        "latitude": 16.8864,
        "longitude": -24.9811,
        "timezone": "Atlantic/Cape_Verde",
    },
    "port_walvis_bay": {
        "name": "Walvis Bay",
        "display_name": "Walvis Bay, Namibia",
        "latitude": -22.9576,
        "longitude": 14.5052,
        "timezone": "Africa/Windhoek",
    },
    "port_durban": {
        "name": "Durban",
        "display_name": "Durban, South Africa",
        "latitude": -29.8587,
        "longitude": 31.0218,
        "timezone": "Africa/Johannesburg",
    },
    # Canadian Research Ports
    "port_halifax": {
        "name": "Halifax",
        "display_name": "Halifax, Nova Scotia",
        "latitude": 44.6488,
        "longitude": -63.5752,
        "timezone": "America/Halifax",
    },
    "port_st_johns": {
        "name": "St. John's",
        "display_name": "St. John's, Newfoundland",
        "latitude": 47.5615,
        "longitude": -52.7126,
        "timezone": "America/St_Johns",
    },
    "port_vancouver": {
        "name": "Vancouver",
        "display_name": "Vancouver, Canada",
        "latitude": 49.2827,
        "longitude": -123.1207,
        "timezone": "America/Vancouver",
    },
    # US Research Ports
    "port_woods_hole": {
        "name": "Woods Hole",
        "display_name": "Woods Hole, Massachusetts",
        "latitude": 41.5265,
        "longitude": -70.6712,
        "timezone": "America/New_York",
    },
    "port_san_diego": {
        "name": "San Diego",
        "display_name": "San Diego, California",
        "latitude": 32.7157,
        "longitude": -117.1611,
        "timezone": "America/Los_Angeles",
    },
    "port_astoria": {
        "name": "Astoria",
        "display_name": "Astoria, Oregon",
        "latitude": 46.1879,
        "longitude": -123.8313,
        "timezone": "America/Los_Angeles",
    },
    "port_honolulu": {
        "name": "Honolulu",
        "display_name": "Honolulu, Hawaii",
        "latitude": 21.3099,
        "longitude": -157.8581,
        "timezone": "Pacific/Honolulu",
    },
    # Central American Research Ports
    "port_ensenada": {
        "name": "Ensenada",
        "display_name": "Ensenada, Mexico",
        "latitude": 31.8444,
        "longitude": -116.6197,
        "timezone": "America/Tijuana",
    },
    "port_balboa": {
        "name": "Balboa",
        "display_name": "Balboa, Panama",
        "latitude": 8.9823,
        "longitude": -79.5661,
        "timezone": "America/Panama",
    },
    # Caribbean Research Ports
    "port_bridgetown": {
        "name": "Bridgetown",
        "display_name": "Bridgetown, Barbados",
        "latitude": 13.1939,
        "longitude": -59.6161,
        "timezone": "America/Barbados",
    },
    # South American Research Ports
    "port_rio_de_janeiro": {
        "name": "Rio de Janeiro",
        "display_name": "Rio de Janeiro, Brazil",
        "latitude": -22.9068,
        "longitude": -43.1729,
        "timezone": "America/Sao_Paulo",
    },
    "port_fortaleza": {
        "name": "Fortaleza",
        "display_name": "Fortaleza, Brazil",
        "latitude": -3.7172,
        "longitude": -38.5433,
        "timezone": "America/Fortaleza",
    },
    "port_belem": {
        "name": "Belem",
        "display_name": "Belem, Brazil",
        "latitude": -1.4558,
        "longitude": -48.5044,
        "timezone": "America/Belem",
    },
    "port_recife": {
        "name": "Recife",
        "display_name": "Recife, Brazil",
        "latitude": -8.0476,
        "longitude": -34.8770,
        "timezone": "America/Recife",
    },
    "port_antofagasta": {
        "name": "Antofagasta",
        "display_name": "Antofagasta, Chile",
        "latitude": -23.6509,
        "longitude": -70.3975,
        "timezone": "America/Santiago",
    },
    # Indian Ocean Research Ports
    "port_port_louis_mauritius": {
        "name": "Port Louis",
        "display_name": "Port Louis, Mauritius",
        "latitude": -20.1654,
        "longitude": 57.5074,
        "timezone": "Indian/Mauritius",
    },
    "port_la_reunion": {
        "name": "La Reunion",
        "display_name": "La Reunion, France",
        "latitude": -21.1151,
        "longitude": 55.5364,
        "timezone": "Indian/Reunion",
    },
    "port_port_louis_seychelles": {
        "name": "Port Louis",
        "display_name": "Port Louis, Seychelles",
        "latitude": -4.6796,
        "longitude": 55.5274,
        "timezone": "Indian/Mahe",
    },
    "port_colombo": {
        "name": "Colombo",
        "display_name": "Colombo, Sri Lanka",
        "latitude": 6.9271,
        "longitude": 79.8612,
        "timezone": "Asia/Colombo",
    },
    "port_singapore": {
        "name": "Singapore",
        "display_name": "Singapore",
        "latitude": 1.3521,
        "longitude": 103.8198,
        "timezone": "Asia/Singapore",
    },
    # Pacific Research Ports
    "port_yokohama": {
        "name": "Yokohama",
        "display_name": "Yokohama, Japan",
        "latitude": 35.4437,
        "longitude": 139.6380,
        "timezone": "Asia/Tokyo",
    },
    "port_fremantle": {
        "name": "Fremantle",
        "display_name": "Fremantle, Australia",
        "latitude": -32.0569,
        "longitude": 115.7439,
        "timezone": "Australia/Perth",
    },
    "port_wellington": {
        "name": "Wellington",
        "display_name": "Wellington, New Zealand",
        "latitude": -41.2865,
        "longitude": 174.7762,
        "timezone": "Pacific/Auckland",
    },
    "port_auckland": {
        "name": "Auckland",
        "display_name": "Auckland, New Zealand",
        "latitude": -36.8485,
        "longitude": 174.7633,
        "timezone": "Pacific/Auckland",
    },
    "port_papeete": {
        "name": "Papeete",
        "display_name": "Papeete, Tahiti",
        "latitude": -17.5516,
        "longitude": -149.5585,
        "timezone": "Pacific/Tahiti",
    },
    # Default/Update Ports for Placeholders
    "port_update": {
        "name": "Hamburg (DEFAULT UPDATE PLACEHOLDER)",
        "display_name": "Hamburg, Germany - UPDATE PLACEHOLDER",
        "latitude": 53.53490,
        "longitude": 9.97992,
        "timezone": "Europe/Berlin",
    },
    "port_update_departure": {
        "name": "Hamburg (DEPARTURE PLACEHOLDER)",
        "display_name": "Hamburg, Germany - UPDATE DEPARTURE PORT",
        "latitude": 53.53490,
        "longitude": 9.97992,
        "timezone": "Europe/Berlin",
    },
    "port_update_arrival": {
        "name": "Hamburg (ARRIVAL PLACEHOLDER)",
        "display_name": "Hamburg, Germany - UPDATE ARRIVAL PORT",
        "latitude": 53.53490,
        "longitude": 9.97992,
        "timezone": "Europe/Berlin",
    },
}


def resolve_port_reference(
    port_ref,
):
    """
    Resolve a port reference to a complete PointDefinition object.

    Handles three types of input:
    1. String reference to global port registry (e.g., 'port_reykjavik')
    2. Dictionary with port data (user-defined override)
    3. Already instantiated PointDefinition object

    Parameters
    ----------
    port_ref
        Port reference to resolve.

    Returns
    -------
    PointDefinition
        Complete port definition object.

    Raises
    ------
    ValueError
        If string reference is not found in global registry.
    """
    # Import locally to avoid circular dependency
    from cruiseplan.schema import PointDefinition

    # If already a PointDefinition object, return as-is
    if isinstance(port_ref, PointDefinition):
        return port_ref

    # Handle any port-like object (for compatibility)
    if (
        hasattr(port_ref, "name")
        and hasattr(port_ref, "latitude")
        and hasattr(port_ref, "longitude")
    ):
        return port_ref

    if isinstance(port_ref, dict):
        # User-defined port override
        try:
            return PointDefinition(**port_ref)
        except ValidationError as e:
            # Convert Pydantic validation error to more user-friendly message
            missing_fields = [
                error["loc"][0] for error in e.errors() if error["type"] == "missing"
            ]

            if missing_fields:
                raise ValueError(
                    f"Port dictionary missing required fields: {', '.join(missing_fields)}"
                )
            else:
                # Re-raise original validation error for other types of validation issues
                raise ValueError(str(e)) from e

    elif isinstance(port_ref, str):
        if port_ref.lower().startswith("port_"):
            # Global port reference
            port_key = port_ref.lower()
            if port_key in GLOBAL_PORTS:
                port_data = GLOBAL_PORTS[port_key].copy()
                return PointDefinition(**port_data)
            else:
                available_ports = list(GLOBAL_PORTS.keys())
                raise ValueError(
                    f"Port reference '{port_ref}' not found in global registry. "
                    f"Available ports: {', '.join(available_ports)}"
                )
        else:
            # Try reverse lookup: display name -> port reference
            # Look for port where display name starts with port_ref (before comma)
            for port_id, port_data in GLOBAL_PORTS.items():
                display_name = port_data.get("display_name", "")
                port_name = port_data.get("name", "")
                # Match if port_ref matches the display name up to comma, or the name field
                if (
                    display_name.split(",")[0].strip() == port_ref
                    or port_name == port_ref
                ):
                    return PointDefinition(
                        name=port_id,  # Use the port_id (e.g. port_halifax) as the canonical name
                        latitude=port_data["latitude"],
                        longitude=port_data["longitude"],
                        display_name=display_name,
                        comment=port_data.get("comment", ""),
                    )

            # Simple string port name (backward compatibility)
            warnings.warn(
                f"Port reference '{port_ref}' should use 'port_' prefix for global ports "
                "or be defined as a complete PointDefinition. "
                "Creating basic port with name only.",
                UserWarning,
                stacklevel=3,
            )
            return PointDefinition(
                name=port_ref,
                latitude=0.0,  # Placeholder - needs enrichment
                longitude=0.0,  # Placeholder - needs enrichment
                comment=f"Basic port '{port_ref}' - coordinates need enrichment",
            )
    else:
        raise ValueError(f"Invalid port reference type: {type(port_ref)}")


def get_available_ports() -> dict[str, str]:
    """
    Get a dictionary of available global ports with comments.

    Returns
    -------
    Dict[str, str]
        Mapping of port identifiers to comments.
    """
    return {
        port_id: port_data.get("comment", f"Port: {port_data['name']}")
        for port_id, port_data in GLOBAL_PORTS.items()
    }


def add_custom_port(port_id: str, port_data: dict) -> None:
    """
    Add a custom port to the global registry at runtime.

    Useful for adding project-specific ports that aren't in the default registry.

    Parameters
    ----------
    port_id : str
        Port identifier (should start with 'port_').
    port_data : dict
        Port data dictionary with required fields (name, latitude, longitude).

    Raises
    ------
    ValueError
        If port_id doesn't follow naming convention or required fields are missing.
    """
    if not port_id.startswith("port_"):
        raise ValueError("Custom port IDs must start with 'port_' prefix")

    required_fields = ["name", "latitude", "longitude"]
    missing_fields = [field for field in required_fields if field not in port_data]
    if missing_fields:
        raise ValueError(f"Port data missing required fields: {missing_fields}")

    # Validate the port data by creating a PointDefinition
    try:
        from cruiseplan.schema import PointDefinition

        PointDefinition(**port_data)
    except Exception as e:
        raise ValueError(f"Invalid port data: {e}") from e

    GLOBAL_PORTS[port_id.lower()] = port_data.copy()


def list_ports_in_region(
    min_lat: float, max_lat: float, min_lon: float, max_lon: float
) -> dict[str, str]:
    """
    List ports within a geographic bounding box.

    Parameters
    ----------
    min_lat, max_lat : float
        Latitude bounds in degrees.
    min_lon, max_lon : float
        Longitude bounds in degrees.

    Returns
    -------
    Dict[str, str]
        Mapping of port identifiers to names for ports in the region.
    """
    regional_ports = {}
    for port_id, port_data in GLOBAL_PORTS.items():
        lat = port_data["latitude"]
        lon = port_data["longitude"]

        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            regional_ports[port_id] = port_data["name"]

    return regional_ports
