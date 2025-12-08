# cruiseplan/core/cruise.py
import yaml
from pathlib import Path
from typing import Dict, Any, List, Union

from cruiseplan.core.validation import (
    CruiseConfig,
    StationDefinition,
    MooringDefinition,
    TransitDefinition
)

class ReferenceError(Exception):
    """Raised when a scheduled item ID is not found in the Catalog."""
    pass

class Cruise:
    """
    The main container object.
    Responsible for parsing YAML, Validating Schema, and Resolving References.
    """
    def __init__(self, config_path: Union[str, Path]):
        self.config_path = Path(config_path)
        self.raw_data = self._load_yaml()

        # 1. Validation Pass (Pydantic)
        self.config = CruiseConfig(**self.raw_data)

        # 2. Indexing Pass (Build the Catalog Registry)
        self.station_registry: Dict[str, StationDefinition] = {s.name: s for s in (self.config.stations or [])}
        self.mooring_registry: Dict[str, MooringDefinition] = {m.name: m for m in (self.config.moorings or [])}
        self.transit_registry: Dict[str, TransitDefinition] = {t.name: t for t in (self.config.transits or [])}

        # 3. Resolution Pass (Link Schedule to Catalog)
        self._resolve_references()

    def _load_yaml(self) -> Dict[str, Any]:
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _resolve_references(self):
        """
        Traverses the Legs -> Clusters/Sections -> Lists.
        Converts string references into full objects from the registry.
        """
        # Validate Global Anchors exist
        if self.config.first_station not in self.station_registry and \
           self.config.first_station not in self.mooring_registry:
             raise ReferenceError(f"Global anchor 'first_station': {self.config.first_station} not found in catalog.")

        if self.config.last_station not in self.station_registry and \
           self.config.last_station not in self.mooring_registry:
             raise ReferenceError(f"Global anchor 'last_station': {self.config.last_station} not found in catalog.")

        for leg in self.config.legs:

            # Resolve Direct Leg Buckets
            if leg.moorings:
                leg.moorings = self._resolve_list(leg.moorings, self.mooring_registry, "Mooring")

            # Resolve Clusters
            if leg.clusters:
                for cluster in leg.clusters:
                    # Resolve Mixed Sequence
                    if cluster.sequence:
                        # Sequence can contain anything, check all registries
                        cluster.sequence = self._resolve_mixed_list(cluster.sequence)

                    # Resolve Buckets
                    if cluster.moorings:
                        cluster.moorings = self._resolve_list(cluster.moorings, self.mooring_registry, "Mooring")
                    if cluster.stations:
                        cluster.stations = self._resolve_list(cluster.stations, self.station_registry, "Station")

    def _resolve_list(self, items: List[Union[str, Any]], registry: Dict[str, Any], type_label: str) -> List[Any]:
        """
        Resolves a list that should strictly contain items of a specific type (e.g. Moorings).
        Handles the "Hybrid Pattern" (Strings are lookups, Objects are kept as-is).
        """
        resolved_items = []
        for item in items:
            if isinstance(item, str):
                if item not in registry:
                    raise ReferenceError(f"{type_label} ID '{item}' referenced in schedule but not found in Catalog.")
                resolved_items.append(registry[item])
            else:
                # Item is already an inline object (validated by Pydantic)
                resolved_items.append(item)
        return resolved_items

    def _resolve_mixed_list(self, items: List[Union[str, Any]]) -> List[Any]:
        """
        Resolves a 'sequence' list which can contain Stations, Moorings, or Transits.
        """
        resolved_items = []
        for item in items:
            if isinstance(item, str):
                # Try finding it in any registry
                if item in self.mooring_registry:
                    resolved_items.append(self.mooring_registry[item])
                elif item in self.station_registry:
                    resolved_items.append(self.station_registry[item])
                elif item in self.transit_registry:
                    resolved_items.append(self.transit_registry[item])
                else:
                    raise ReferenceError(f"Sequence ID '{item}' not found in any Catalog (Stations, Moorings, Transits).")
            else:
                resolved_items.append(item)
        return resolved_items
