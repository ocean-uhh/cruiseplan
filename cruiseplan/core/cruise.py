# cruiseplan/core/cruise.py
from pathlib import Path
from typing import Any, Dict, List, Union

from cruiseplan.core.cluster import Cluster
from cruiseplan.core.leg import Leg
from cruiseplan.core.validation import (
    AreaDefinition,
    CruiseConfig,
    PortDefinition,
    StationDefinition,
    StrategyEnum,
    TransitDefinition,
)
from cruiseplan.utils.global_ports import resolve_port_reference
from cruiseplan.utils.yaml_io import load_yaml


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
    port_registry : Dict[str, PortDefinition]
        Dictionary mapping port names to PortDefinition objects.
    runtime_legs : List[Leg]
        List of runtime Leg objects converted from LegDefinition objects.
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
        YAMLIOError
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
        self.area_registry: Dict[str, AreaDefinition] = {
            a.name: a for a in (self.config.areas or [])
        }
        self.port_registry: Dict[str, PortDefinition] = {
            p.name: p for p in (self.config.ports or [])
        }

        # 3. Config Port Resolution Pass (Resolve top-level departure/arrival ports)
        self._resolve_config_ports()

        # 4. Resolution Pass (Link Schedule to Catalog)
        self._resolve_references()

        # 5. Leg Conversion Pass (Convert LegDefinition to runtime Leg objects)
        self.runtime_legs = self._convert_leg_definitions_to_legs()

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
        YAMLIOError
            If the YAML file cannot be parsed.
        """
        return load_yaml(self.config_path)

    def _resolve_references(self):
        """
        Resolve string references to full objects from the registry.

        Traverses the cruise legs, clusters, and sections to convert string
        identifiers into their corresponding StationDefinition and
        TransitDefinition objects from the registries.

        Resolves all references within legs to their corresponding definitions.

        Raises
        ------
        ReferenceError
            If any referenced station or transit ID is not found in the
            corresponding registry.
        """
        # Note: Global anchor validation removed - waypoints are now handled at leg level

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

                    # Resolve Activities (new unified field)
                    if cluster.activities:
                        cluster.activities = self._resolve_mixed_list(
                            cluster.activities
                        )

                    # Resolve Buckets (deprecated field - kept for compatibility)
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
        Resolve a mixed sequence list containing stations, transits, or areas.

        Searches through all available registries to resolve string references
        and converts inline dictionary definitions to proper object types.

        Parameters
        ----------
        items : List[Union[str, Any]]
            List of items that may be strings (references), dictionaries
            (inline definitions), or already-resolved objects.

        Returns
        -------
        List[Any]
            List with string references resolved and dictionaries converted
            to their corresponding definition objects.

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
                elif item in self.area_registry:
                    resolved_items.append(self.area_registry[item])
                else:
                    raise ReferenceError(
                        f"Activity ID '{item}' not found in any Catalog (Stations, Transits, Areas)."
                    )
            elif isinstance(item, dict):
                # Convert inline dictionary definition to proper object type
                resolved_items.append(self._convert_inline_definition(item))
            else:
                # Item is already a resolved object
                resolved_items.append(item)
        return resolved_items

    def _convert_inline_definition(
        self, definition_dict: dict
    ) -> Union[StationDefinition, TransitDefinition, AreaDefinition]:
        """
        Convert an inline dictionary definition to the appropriate definition object.

        Determines the type of definition based on the presence of key fields
        and creates the corresponding Pydantic object.

        Parameters
        ----------
        definition_dict : dict
            Dictionary containing the inline definition fields.

        Returns
        -------
        Union[StationDefinition, TransitDefinition, AreaDefinition]
            The appropriate definition object created from the dictionary.

        Raises
        ------
        ValueError
            If the definition type cannot be determined or validation fails.
        """
        # Determine definition type based on key fields
        if "operation_type" in definition_dict:
            # This is a station definition
            return StationDefinition(**definition_dict)
        elif "start" in definition_dict and "end" in definition_dict:
            # This is a transit definition
            return TransitDefinition(**definition_dict)
        elif any(
            field in definition_dict for field in ["polygon", "center", "boundary"]
        ):
            # This is an area definition
            return AreaDefinition(**definition_dict)
        # Fallback: assume it's a station if it has common station fields
        elif any(
            field in definition_dict
            for field in ["latitude", "longitude", "position", "action"]
        ):
            # Add default operation_type if missing
            if "operation_type" not in definition_dict:
                definition_dict = definition_dict.copy()
                definition_dict["operation_type"] = "CTD"  # Default operation type
            return StationDefinition(**definition_dict)
        else:
            raise ValueError(
                f"Cannot determine definition type for inline definition: {definition_dict}"
            )

    def _resolve_port_reference(self, port_ref) -> PortDefinition:
        """
        Resolve a port reference checking catalog first, then global registry.

        Follows the catalog-based pattern where string references are first
        checked against the local port catalog, then fall back to global
        port registry for resolution.

        Parameters
        ----------
        port_ref : Union[str, PortDefinition, dict]
            Port reference to resolve.

        Returns
        -------
        PortDefinition
            Resolved port definition object.

        Raises
        ------
        ReferenceError
            If string reference is not found in catalog or global registry.
        """
        # Catch-all for any port-like object at the beginning
        if (
            hasattr(port_ref, "name")
            and hasattr(port_ref, "latitude")
            and hasattr(port_ref, "longitude")
        ):
            return port_ref

        # If already a PortDefinition object, return as-is
        if isinstance(port_ref, PortDefinition):
            return port_ref

        # If dictionary, create PortDefinition
        if isinstance(port_ref, dict):
            return PortDefinition(**port_ref)

        # String reference - check catalog first, then global registry
        if isinstance(port_ref, str):
            # Check local catalog first
            if port_ref in self.port_registry:
                catalog_port = self.port_registry[port_ref]
                # If catalog port is already a PortDefinition, return it
                if isinstance(catalog_port, PortDefinition):
                    return catalog_port
                # If it's a dict, convert to PortDefinition
                elif isinstance(catalog_port, dict):
                    return PortDefinition(**catalog_port)
                else:
                    # Handle unexpected type in catalog
                    raise ReferenceError(
                        f"Unexpected type in port catalog: {type(catalog_port)}"
                    )

            # Fall back to global port registry
            try:
                return resolve_port_reference(port_ref)
            except ValueError as e:
                raise ReferenceError(
                    f"Port reference '{port_ref}' not found in catalog or global registry: {e}"
                ) from e

        raise ReferenceError(f"Invalid port reference type: {type(port_ref)}")

    def _resolve_config_ports(self):
        """
        Resolve top-level config departure_port and arrival_port references.

        This method resolves string references in the cruise configuration's
        top-level departure_port and arrival_port fields to PortDefinition objects.
        """
        if hasattr(self.config, "departure_port") and self.config.departure_port:
            if isinstance(self.config.departure_port, str):
                self.config.departure_port = self._resolve_port_reference(
                    self.config.departure_port
                )

        if hasattr(self.config, "arrival_port") and self.config.arrival_port:
            if isinstance(self.config.arrival_port, str):
                self.config.arrival_port = self._resolve_port_reference(
                    self.config.arrival_port
                )

    def _convert_leg_definitions_to_legs(self) -> List[Leg]:
        """
        Convert LegDefinition objects to runtime Leg objects with clusters.

        This method implements Phase 4 of the CLAUDE-legclass.md architecture:
        - Creates runtime Leg objects from LegDefinition YAML data
        - Resolves port references using global port system
        - Applies parameter inheritance from cruise to leg level
        - Creates clusters (explicit or default) within each leg
        - Validates required maritime structure (departure_port + arrival_port)

        Returns
        -------
        List[Leg]
            List of runtime Leg objects ready for scheduling.

        Raises
        ------
        ValueError
            If leg is missing required departure_port or arrival_port.
        ReferenceError
            If port references cannot be resolved.
        """
        runtime_legs = []

        for leg_def in self.config.legs or []:
            # Validate required maritime structure
            if not leg_def.departure_port or not leg_def.arrival_port:
                raise ValueError(
                    f"Leg '{leg_def.name}' missing required departure_port or arrival_port. "
                    "Maritime legs must be port-to-port segments."
                )

            # Resolve port references (check catalog first, then global registry)
            try:
                departure_port = self._resolve_port_reference(leg_def.departure_port)
                arrival_port = self._resolve_port_reference(leg_def.arrival_port)
            except ValueError as e:
                raise ReferenceError(
                    f"Port resolution failed for leg '{leg_def.name}': {e}"
                ) from e

            # Create runtime leg with maritime structure
            runtime_leg = Leg(
                name=leg_def.name,
                departure_port=departure_port,
                arrival_port=arrival_port,
                description=leg_def.description,
                strategy=leg_def.strategy or StrategyEnum.SEQUENTIAL,
                ordered=leg_def.ordered if leg_def.ordered is not None else True,
                first_waypoint=leg_def.first_waypoint,
                last_waypoint=leg_def.last_waypoint,
            )

            # Apply parameter inheritance (leg overrides cruise defaults)
            runtime_leg.vessel_speed = leg_def.vessel_speed or getattr(
                self.config, "default_vessel_speed", None
            )
            runtime_leg.distance_between_stations = (
                leg_def.distance_between_stations
                or getattr(self.config, "default_distance_between_stations", None)
            )
            runtime_leg.turnaround_time = leg_def.turnaround_time or getattr(
                self.config, "turnaround_time", None
            )

            # Create clusters within the leg
            if leg_def.clusters:
                # Explicit clusters defined
                for cluster_def in leg_def.clusters:
                    runtime_cluster = Cluster.from_definition(cluster_def)
                    # TODO: Resolve activities to operations in Phase 3 completion
                    runtime_leg.clusters.append(runtime_cluster)
            elif leg_def.activities:
                # Create default cluster from leg activities
                default_cluster = Cluster(
                    name=f"{leg_def.name}_Default",
                    description=f"Default cluster for leg {leg_def.name}",
                    strategy=leg_def.strategy or StrategyEnum.SEQUENTIAL,
                    ordered=leg_def.ordered if leg_def.ordered is not None else True,
                )
                # TODO: Resolve activities to operations in Phase 3 completion
                runtime_leg.clusters.append(default_cluster)
            elif hasattr(leg_def, "stations") and leg_def.stations:
                # Backward compatibility: create cluster from legacy stations field
                import warnings

                warnings.warn(
                    f"Leg '{leg_def.name}' uses deprecated 'stations' field. "
                    "Use 'activities' field for future compatibility.",
                    DeprecationWarning,
                    stacklevel=2,
                )
                legacy_cluster = Cluster(
                    name=f"{leg_def.name}_Legacy",
                    description=f"Legacy stations cluster for leg {leg_def.name}",
                    strategy=StrategyEnum.SEQUENTIAL,
                    ordered=True,
                )
                # Convert station references to activities format
                for station in leg_def.stations:
                    if hasattr(station, "name"):
                        # Station object
                        legacy_cluster.add_operation(station)
                    else:
                        # Station reference - will be resolved in Phase 3
                        pass
                runtime_leg.clusters.append(legacy_cluster)

            runtime_legs.append(runtime_leg)

        return runtime_legs

    def _anchor_exists_in_catalog(self, anchor_ref: str) -> bool:
        """
        Check if an anchor reference exists in any catalog registry.

        Anchors can be stations, areas, or other operation entities
        that can serve as routing points for maritime planning.

        Parameters
        ----------
        anchor_ref : str
            String reference to check against all registries.

        Returns
        -------
        bool
            True if the anchor reference exists in any registry.
        """
        # Check stations registry (includes moorings as operation_type=mooring)
        if anchor_ref in self.station_registry:
            return True

        # Check areas registry
        if anchor_ref in self.area_registry:
            return True

        # Check transits registry for scientific transits that can serve as anchors
        if anchor_ref in self.transit_registry:
            return True

        return False
