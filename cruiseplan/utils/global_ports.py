"""
Global port configuration system for maritime cruise planning.

This module provides a registry of common maritime ports with their coordinates,
timezones, and metadata. Users can reference these ports by standard identifiers
(e.g., 'port_reykjavik') or override them with custom definitions in their YAML.

Features:
- Standard port registry with common research cruise destinations
- Timezone information for port operations
- Extensible system allowing user-defined port overrides
- Support for both string references and PortDefinition objects

Usage:
    # In YAML configuration
    departure_port: "port_reykjavik"  # Reference to global port

    # Or override with custom definition
    departure_port:
      name: "Reykjavik_Custom"
      latitude: 64.1466
      longitude: -21.9426
      timezone: "GMT+0"
      description: "Custom port definition"
"""

# Ports to add
# Las Palmas, Canary Islands
# Ponta Delgada, Azores
# Nuuk, Greenland
# Mindelo, Cape Verde
# St. John's, Newfoundland
# Heraklion, Crete
# Malaga, Spain
# Trondheim, Norway
# Brest, France
# Rio de Janeiro, Brazil
# Funchal, Madeira
# Emden, Germany
# Rostock, Germany
# Catania, Italy
# Bridgetown, Barbados
# Fortaleza, Brazil
# Belem, Brazil
# Nice, France
# Limassol, Cyprus
# Walvis Bay, Namibia
# Recife, Brazil
# Port Louis, Mauritius
# Colombo, Sri Lanka
# La Reunion, France
# Singapore
# Port Louis, Seychelles
# Durban, South Africa
# Fremantle, Australia
# Wellington, New Zealand
# Auckland, New Zealand
# Papeete, Tahiti
# Antofagasta, Chile
# Balboa, Panama
# San Diego, CA, USA
# Ensenada, Mexico
# Yokohama, Japan
# Honolulu, Hawaii
# Vancouver, Canada
# Astoria, OR, USA


import warnings
from typing import Dict, Union

from pydantic import ValidationError

# Global port registry with common maritime research destinations
GLOBAL_PORTS: Dict[str, Dict[str, Union[str, float]]] = {
    # North Atlantic Research Ports
    "port_reykjavik": {
        "name": "Reykjavik",
        "display_name": "Reykjavik, Iceland",
        "latitude": 64.1466,
        "longitude": -21.9426,
        "timezone": "Atlantic/Reykjavik",
        "description": "Iceland capital, major Arctic research hub",
    },
    "port_tromso": {
        "name": "Tromsø",
        "display_name": "Tromsø, Norway",
        "latitude": 69.6496,
        "longitude": 18.9553,
        "timezone": "GMT+1",
        "description": "Northern Norway, Arctic gateway",
    },
    "port_bergen": {
        "name": "Bergen",
        "display_name": "Bergen, Norway",
        "latitude": 60.3913,
        "longitude": 5.3221,
        "timezone": "GMT+1",
        "description": "Western Norway, North Sea operations",
    },
    "port_stavanger": {
        "name": "Stavanger",
        "display_name": "Stavanger, Norway",
        "latitude": 58.9700,
        "longitude": 5.7331,
        "timezone": "GMT+1",
        "description": "Southern Norway, North Sea research",
    },
    # UK & Ireland Research Ports
    "port_southampton": {
        "name": "Southampton",
        "display_name": "Southampton, UK",
        "latitude": 50.9097,
        "longitude": -1.4044,
        "timezone": "GMT+0",
        "description": "UK south coast, Atlantic access",
    },
    "port_plymouth": {
        "name": "Plymouth",
        "display_name": "Plymouth, UK",
        "latitude": 50.3755,
        "longitude": -4.1427,
        "timezone": "GMT+0",
        "description": "UK southwest, Celtic Sea operations",
    },
    "port_cork": {
        "name": "Cork",
        "display_name": "Cork, Ireland",
        "latitude": 51.8985,
        "longitude": -8.4756,
        "timezone": "GMT+0",
        "description": "Ireland south coast, Atlantic research",
    },
    # German Research Ports
    "port_bremerhaven": {
        "name": "Bremerhaven",
        "display_name": "Bremerhaven, Germany",
        "latitude": 53.5395,
        "longitude": 8.5809,
        "timezone": "GMT+1",
        "description": "Germany, Arctic and Atlantic operations",
    },
    "port_hamburg": {
        "name": "Hamburg",
        "display_name": "Hamburg, Germany",
        "latitude": 53.5511,
        "longitude": 9.9937,
        "timezone": "GMT+1",
        "description": "Germany, North Sea and Baltic access",
    },
    # Baltic Research Ports
    "port_stockholm": {
        "name": "Stockholm",
        "display_name": "Stockholm, Sweden",
        "latitude": 59.3293,
        "longitude": 18.0686,
        "timezone": "GMT+1",
        "description": "Sweden, Baltic Sea operations",
    },
    "port_copenhagen": {
        "name": "Copenhagen",
        "display_name": "Copenhagen, Denmark",
        "latitude": 55.6761,
        "longitude": 12.5683,
        "timezone": "GMT+1",
        "description": "Denmark, Baltic and North Sea gateway",
    },
    # Mediterranean Research Ports
    "port_vigo": {
        "name": "Vigo",
        "display_name": "Vigo, Spain",
        "latitude": 42.2406,
        "longitude": -8.7207,
        "timezone": "GMT+1",
        "description": "Spain northwest, Atlantic margin research",
    },
    "port_cadiz": {
        "name": "Cadiz",
        "display_name": "Cadiz, Spain",
        "latitude": 36.5298,
        "longitude": -6.2923,
        "timezone": "GMT+1",
        "description": "Spain southwest, Atlantic and Mediterranean",
    },
    # Canadian Research Ports
    "port_halifax": {
        "name": "Halifax",
        "display_name": "Halifax, Nova Scotia",
        "latitude": 44.6488,
        "longitude": -63.5752,
        "timezone": "GMT-4",
        "description": "Nova Scotia, North Atlantic research hub",
    },
    "port_st_johns": {
        "name": "St. John's",
        "display_name": "St. John's, Newfoundland",
        "latitude": 47.5615,
        "longitude": -52.7126,
        "timezone": "GMT-3.5",
        "description": "Newfoundland, Labrador Sea operations",
    },
    # US East Coast Research Ports
    "port_woods_hole": {
        "name": "Woods Hole",
        "display_name": "Woods Hole, Massachusetts",
        "latitude": 41.5265,
        "longitude": -70.6712,
        "timezone": "GMT-5",
        "description": "Massachusetts, major oceanographic center",
    },
    "port_newport": {
        "name": "Newport",
        "display_name": "Newport, Oregon",
        "latitude": 44.6063,
        "longitude": -124.0533,
        "timezone": "GMT-8",
        "description": "Oregon, Pacific research operations",
    },
    # Default/Update Port for Station Picker
    "port_update": {
        "name": "Reykjavik (Update)",
        "display_name": "Update Port - Please Replace",
        "latitude": 64.1466,
        "longitude": -21.9426,
        "timezone": "GMT+0",
        "description": "Default port for station picker - update with actual ports",
    },
}


def resolve_port_reference(
    port_ref,
):
    """
    Resolve a port reference to a complete PortDefinition object.

    Handles three types of input:
    1. String reference to global port registry (e.g., 'port_reykjavik')
    2. Dictionary with port data (user-defined override)
    3. Already instantiated PortDefinition object

    Parameters
    ----------
    port_ref
        Port reference to resolve.

    Returns
    -------
    PortDefinition
        Complete port definition object.

    Raises
    ------
    ValueError
        If string reference is not found in global registry.
    """
    # Import locally to avoid circular dependency
    from cruiseplan.core.validation import PortDefinition

    # If already a PortDefinition object, return as-is
    if isinstance(port_ref, PortDefinition):
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
            return PortDefinition(**port_ref)
        except ValidationError as e:
            # Convert Pydantic validation error to more user-friendly message
            missing_fields = []
            for error in e.errors():
                if error["type"] == "missing":
                    missing_fields.append(error["loc"][0])

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
                return PortDefinition(**port_data)
            else:
                available_ports = list(GLOBAL_PORTS.keys())
                raise ValueError(
                    f"Port reference '{port_ref}' not found in global registry. "
                    f"Available ports: {', '.join(available_ports)}"
                )
        else:
            # Simple string port name (backward compatibility)
            warnings.warn(
                f"Port reference '{port_ref}' should use 'port_' prefix for global ports "
                "or be defined as a complete PortDefinition. "
                "Creating basic port with name only.",
                UserWarning,
                stacklevel=3,
            )
            return PortDefinition(
                name=port_ref,
                latitude=0.0,  # Placeholder - needs enrichment
                longitude=0.0,  # Placeholder - needs enrichment
                description=f"Basic port '{port_ref}' - coordinates need enrichment",
            )
    else:
        raise ValueError(f"Invalid port reference type: {type(port_ref)}")


def get_available_ports() -> Dict[str, str]:
    """
    Get a dictionary of available global ports with descriptions.

    Returns
    -------
    Dict[str, str]
        Mapping of port identifiers to descriptions.
    """
    return {
        port_id: port_data.get("description", f"Port: {port_data['name']}")
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

    # Validate the port data by creating a PortDefinition
    try:
        from cruiseplan.core.validation import PortDefinition

        PortDefinition(**port_data)
    except Exception as e:
        raise ValueError(f"Invalid port data: {e}") from e

    GLOBAL_PORTS[port_id.lower()] = port_data.copy()


def list_ports_in_region(
    min_lat: float, max_lat: float, min_lon: float, max_lon: float
) -> Dict[str, str]:
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
