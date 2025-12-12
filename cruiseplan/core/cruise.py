# cruiseplan/core/cruise.py
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from cruiseplan.core.validation import (
    CruiseConfig,
    StationDefinition,
    TransitDefinition,
)


class ReferenceError(Exception):
    """
    Exception raised when a referenced item is not found in the catalog.

    This exception is raised during the reference resolution phase when
    string identifiers in the cruise configuration cannot be matched to
    their corresponding definitions in the station or transit registries.
    """


class Cruise:
    """
    The main container object for cruise planning.

    Responsible for parsing YAML configuration files, validating the schema
    using Pydantic models, and resolving string references to full objects
    from the catalog registries.

    Attributes
    ----------
    config_path : Path
        Absolute path to the configuration file.
    raw_data : Dict[str, Any]
        Raw dictionary data loaded from the YAML file.
    config : CruiseConfig
        Validated Pydantic configuration object.
    station_registry : Dict[str, StationDefinition]
        Dictionary mapping station names to StationDefinition objects.
    transit_registry : Dict[str, TransitDefinition]
        Dictionary mapping transit names to TransitDefinition objects.
    """

    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize a Cruise object from a YAML configuration file.

        Performs three main operations:
        1. Loads and validates the YAML configuration using Pydantic
        2. Builds registries for stations and transits
        3. Resolves string references to full objects

        Parameters
        ----------
        config_path : Union[str, Path]
            Path to the YAML configuration file containing cruise definition.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        yaml.YAMLError
            If the YAML file cannot be parsed.
        ValidationError
            If the configuration does not match the expected schema.
        ReferenceError
            If referenced stations or transits are not found in the catalog.
        """
        self.config_path = Path(config_path)
        self.raw_data = self._load_yaml()

        # 1. Validation Pass (Pydantic)
        self.config = CruiseConfig(**self.raw_data)

        # 2. Indexing Pass (Build the Catalog Registry)
        self.station_registry: Dict[str, StationDefinition] = {
            s.name: s for s in (self.config.stations or [])
        }
        self.transit_registry: Dict[str, TransitDefinition] = {
            t.name: t for t in (self.config.transits or [])
        }

        # 3. Resolution Pass (Link Schedule to Catalog)
        self._resolve_references()

    def _load_yaml(self) -> Dict[str, Any]:
        """
        Load and parse the YAML configuration file.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing the parsed YAML data.

        Raises
        ------
        FileNotFoundError
            If the configuration file does not exist.
        yaml.YAMLError
            If the YAML file cannot be parsed.
        """
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _resolve_references(self):
        """
        Resolve string references to full objects from the registry.

        Traverses the cruise legs, clusters, and sections to convert string
        identifiers into their corresponding StationDefinition and
        TransitDefinition objects from the registries.

        Validates that global anchor stations (first_station and last_station)
        exist in the station registry before proceeding with resolution.

        Raises
        ------
        ReferenceError
            If any referenced station or transit ID is not found in the
            corresponding registry, or if global anchor stations are missing.
        """
        # Validate Global Anchors exist
        if self.config.first_station not in self.station_registry:
            raise ReferenceError(
                f"Global anchor 'first_station': {self.config.first_station} not found in catalog."
            )

        if self.config.last_station not in self.station_registry:
            raise ReferenceError(
                f"Global anchor 'last_station': {self.config.last_station} not found in catalog."
            )

        for leg in self.config.legs:
            # Resolve Direct Leg Stations
            if leg.stations:
                leg.stations = self._resolve_list(
                    leg.stations, self.station_registry, "Station"
                )

            # Resolve Clusters
            if leg.clusters:
                for cluster in leg.clusters:
                    # Resolve Mixed Sequence
                    if cluster.sequence:
                        # Sequence can contain anything, check all registries
                        cluster.sequence = self._resolve_mixed_list(cluster.sequence)

                    # Resolve Buckets
                    if cluster.stations:
                        cluster.stations = self._resolve_list(
                            cluster.stations, self.station_registry, "Station"
                        )

    def _resolve_list(
        self, items: List[Union[str, Any]], registry: Dict[str, Any], type_label: str
    ) -> List[Any]:
        """
        Resolve a list containing items of a specific type.

        Handles the "Hybrid Pattern" where strings are treated as lookups
        into the registry, while objects are kept as-is (already validated
        by Pydantic).

        Parameters
        ----------
        items : List[Union[str, Any]]
            List of items that may be strings (references) or objects.
        registry : Dict[str, Any]
            Dictionary mapping string IDs to their corresponding objects.
        type_label : str
            Human-readable label for the type (e.g., "Station", "Transit")
            used in error messages.

        Returns
        -------
        List[Any]
            List with string references resolved to their corresponding objects.

        Raises
        ------
        ReferenceError
            If any string reference is not found in the registry.
        """
        resolved_items = []
        for item in items:
            if isinstance(item, str):
                if item not in registry:
                    raise ReferenceError(
                        f"{type_label} ID '{item}' referenced in schedule but not found in Catalog."
                    )
                resolved_items.append(registry[item])
            else:
                # Item is already an inline object (validated by Pydantic)
                resolved_items.append(item)
        return resolved_items

    def _resolve_mixed_list(self, items: List[Union[str, Any]]) -> List[Any]:
        """
        Resolve a mixed sequence list containing stations or transits.

        Searches through all available registries (stations and transits) to
        resolve string references. This is used for cluster sequences which
        can contain heterogeneous types of operations.

        Parameters
        ----------
        items : List[Union[str, Any]]
            List of items that may be strings (references) or objects.

        Returns
        -------
        List[Any]
            List with string references resolved to their corresponding objects.

        Raises
        ------
        ReferenceError
            If any string reference is not found in any registry.
        """
        resolved_items = []
        for item in items:
            if isinstance(item, str):
                # Try finding it in any registry
                if item in self.station_registry:
                    resolved_items.append(self.station_registry[item])
                elif item in self.transit_registry:
                    resolved_items.append(self.transit_registry[item])
                else:
                    raise ReferenceError(
                        f"Sequence ID '{item}' not found in any Catalog (Stations, Transits)."
                    )
            else:
                resolved_items.append(item)
        return resolved_items
