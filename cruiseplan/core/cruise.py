"""
Core cruise management and organizational runtime classes.

This module provides the main CruiseInstance class for loading, validating, and managing
cruise configurations from YAML files, along with the organizational runtime
classes (Leg, Cluster) that form the hierarchical structure for cruise execution.
The BaseOrganizationUnit abstract base class provides the common interface for
all organizational units in the cruise planning hierarchy.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Union

from cruiseplan.core import enrichment, serialization
from cruiseplan.core.organizational import (
    Cluster,
    Leg,
    ReferenceError,
)
from cruiseplan.core.serialization import deserialize_inline_definition
from cruiseplan.schema import (
    AreaDefinition,
    CruiseConfig,
    LineDefinition,
    PointDefinition,
    StrategyEnum,
)
from cruiseplan.schema.ports import resolve_port_reference
from cruiseplan.schema.yaml_io import load_yaml

logger = logging.getLogger(__name__)


# TODO Question - why do we not also have a "leg_registry" and maybe a "cluster_registry"?
class CruiseInstance:
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
    point_registry : Dict[str, PointDefinition]
        Dictionary mapping point names to PointDefinition objects.
    line_registry : Dict[str, LineDefinition]
        Dictionary mapping line names to LineDefinition objects.
    port_registry : Dict[str, PointDefinition]
        Dictionary mapping port names to PointDefinition objects.
    area_registry : Dict[str, AreaDefinition]
        Dictionary mapping area names to AreaDefinition objects.
    runtime_legs : List[Leg]
        List of runtime Leg objects converted from LegDefinition objects.
    """

    def __init__(self, config_path: Union[str, Path]):
        """
        Initialize a CruiseInstance object from a YAML configuration file.

        Performs three main operations:
        1. Loads and validates the YAML configuration using Pydantic
        2. Builds registries for points and lines
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
            If referenced points or lines are not found in the catalog.
        """
        self.config_path = Path(config_path)
        self.raw_data = self._load_yaml()

        # 1. Validation Pass (Pydantic)
        self.config = CruiseConfig(**self.raw_data)

        # 2. Indexing Pass (Build the Catalog Registry)
        self.point_registry: dict[str, PointDefinition] = {
            s.name: s for s in (self.config.points or [])
        }
        self.line_registry: dict[str, LineDefinition] = {
            t.name: t for t in (self.config.lines or [])
        }
        self.area_registry: dict[str, AreaDefinition] = {
            a.name: a for a in (self.config.areas or [])
        }
        self.port_registry: dict[str, PointDefinition] = {
            p.name: p for p in (self.config.ports or [])
        }

        # 3. Config Port Resolution Pass (Resolve top-level departure/arrival ports)
        self._resolve_config_ports()

        # 4. Port Enrichment Pass (Auto-expand leg port references with actions)
        self._enrich_leg_ports()

        # 5. Resolution Pass (Link Schedule to Catalog)
        self._resolve_references()

        # 6. Leg Conversion Pass (Convert LegDefinition to runtime Leg objects)
        self.runtime_legs = self._convert_leg_definitions_to_legs()

    def _load_yaml(self) -> dict[str, Any]:
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
        identifiers into their corresponding PointDefinition and
        LineDefinition objects from the registries.

        Resolves all references within legs to their corresponding definitions.

        Raises
        ------
        ReferenceError
            If any referenced station or transit ID is not found in the
            corresponding registry.
        """
        # Note: Global anchor validation removed - waypoints are now handled at leg level

        for leg in self.config.legs:
            # Resolve Direct Leg Activities (modern field)
            if leg.activities:
                leg.activities = self._resolve_mixed_list(leg.activities)

            # Resolve Clusters
            if leg.clusters:
                for cluster in leg.clusters:
                    # Resolve Activities (new unified field)
                    if cluster.activities:
                        cluster.activities = self._resolve_mixed_list(
                            cluster.activities
                        )

    # TODO update docstring, I don't think we have "Station" and "Transit" are these supposed to be human readable for "operation_type"?
    def _resolve_list(
        self, items: list[Union[str, Any]], registry: dict[str, Any], type_label: str
    ) -> list[Any]:
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

    def _resolve_mixed_list(self, items: list[Union[str, Any]]) -> list[Any]:
        """
        Resolve a mixed sequence list containing points, lines, or areas.

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
                if item in self.point_registry:
                    resolved_items.append(self.point_registry[item])
                elif item in self.line_registry:
                    resolved_items.append(self.line_registry[item])
                elif item in self.area_registry:
                    resolved_items.append(self.area_registry[item])
                else:
                    raise ReferenceError(
                        f"Activity ID '{item}' not found in any Catalog (Points, Lines, Areas)."
                    )
            elif isinstance(item, dict):
                # Convert inline dictionary definition to proper object type
                resolved_items.append(deserialize_inline_definition(item))
            else:
                # Item is already a resolved object
                resolved_items.append(item)
        return resolved_items

    def _resolve_port_reference(self, port_ref) -> PointDefinition:
        """
        Resolve a port reference checking catalog first, then global registry.

        Follows the catalog-based pattern where string references are first
        checked against the local port catalog, then fall back to global
        port registry for resolution.

        Parameters
        ----------
        port_ref : Union[str, PointDefinition, dict]
            Port reference to resolve.

        Returns
        -------
        PointDefinition
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

        # If already a PointDefinition object, return as-is
        if isinstance(port_ref, PointDefinition):
            return port_ref

        # If dictionary, create PointDefinition
        if isinstance(port_ref, dict):
            return PointDefinition(**port_ref)

        # String reference - check catalog first, then global registry
        if isinstance(port_ref, str):
            # Check local catalog first
            if port_ref in self.port_registry:
                catalog_port = self.port_registry[port_ref]
                # If catalog port is already a PointDefinition, return it
                if isinstance(catalog_port, PointDefinition):
                    return catalog_port
                # If it's a dict, convert to PointDefinition
                elif isinstance(catalog_port, dict):
                    return PointDefinition(**catalog_port)
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

    # TODO check is this pydantic or yaml-based, if yaml-based can we use vocabulary.py for DEPARTURE_PORT_FIELD and ARRIVAL_PORT_FIELD?
    def _resolve_config_ports(self):
        """
        Resolve top-level config departure_port and arrival_port references.

        This method resolves string references in the cruise configuration's
        top-level departure_port and arrival_port fields to PointDefinition objects.
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

    def _enrich_leg_ports(self):
        """
        Automatically enrich leg-level port references with actions.

        Handles both string port references and inline port objects:
        - String references are expanded using global port registry
        - Inline port objects get action and operation_type fields added
        - departure_port gets action='mob' (mobilization)
        - arrival_port gets action='demob' (demobilization)
        """
        for leg_def in self.config.legs or []:
            # Enrich departure_port with mob action
            if hasattr(leg_def, "departure_port") and leg_def.departure_port:
                if isinstance(leg_def.departure_port, str):
                    # String reference - expand from global registry
                    port_ref = leg_def.departure_port
                    try:
                        port_definition = resolve_port_reference(port_ref)
                        # Create enriched port with action
                        enriched_port = PointDefinition(
                            name=port_definition.name,
                            latitude=port_definition.latitude,
                            longitude=port_definition.longitude,
                            operation_type="port",
                            action="mob",  # Departure ports are mobilization
                            display_name=getattr(
                                port_definition, "display_name", port_definition.name
                            ),
                        )
                        leg_def.departure_port = enriched_port
                    except ValueError:
                        # If global port resolution fails, keep as string
                        pass
                else:
                    # Inline port object - add missing fields
                    port_obj = leg_def.departure_port
                    if not hasattr(port_obj, "action") or port_obj.action is None:
                        port_obj.action = "mob"
                    if (
                        not hasattr(port_obj, "operation_type")
                        or port_obj.operation_type is None
                    ):
                        port_obj.operation_type = "port"

            # Enrich arrival_port with demob action
            if hasattr(leg_def, "arrival_port") and leg_def.arrival_port:
                if isinstance(leg_def.arrival_port, str):
                    # String reference - expand from global registry
                    port_ref = leg_def.arrival_port
                    try:
                        port_definition = resolve_port_reference(port_ref)
                        # Create enriched port with action
                        enriched_port = PointDefinition(
                            name=port_definition.name,
                            latitude=port_definition.latitude,
                            longitude=port_definition.longitude,
                            operation_type="port",
                            action="demob",  # Arrival ports are demobilization
                            display_name=getattr(
                                port_definition, "display_name", port_definition.name
                            ),
                        )
                        leg_def.arrival_port = enriched_port
                    except ValueError:
                        # If global port resolution fails, keep as string
                        pass
                else:
                    # Inline port object - add missing fields
                    port_obj = leg_def.arrival_port
                    if not hasattr(port_obj, "action") or port_obj.action is None:
                        port_obj.action = "demob"
                    if (
                        not hasattr(port_obj, "operation_type")
                        or port_obj.operation_type is None
                    ):
                        port_obj.operation_type = "port"

    def _convert_leg_definitions_to_legs(self) -> list[Leg]:
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
                first_activity=leg_def.first_activity,
                last_activity=leg_def.last_activity,
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

            runtime_legs.append(runtime_leg)

        return runtime_legs

    def _anchor_exists_in_catalog(self, anchor_ref: str) -> bool:
        """
        Check if an anchor reference exists in any catalog registry.

        Anchors can be points, areas, or other operation entities
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
        # Check all registries for the anchor reference
        return (
            anchor_ref in self.point_registry
            or anchor_ref in self.area_registry
            or anchor_ref in self.line_registry
        )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "CruiseInstance":
        """
        Create a CruiseInstance from a dictionary without file I/O.

        This class method provides single source of truth functionality by creating
        a CruiseInstance object directly from a configuration dictionary, eliminating the
        need for temporary file creation during enrichment operations.

        Parameters
        ----------
        config_dict : Dict[str, Any]
            Dictionary containing cruise configuration data (e.g., from YAML parsing).

        Returns
        -------
        CruiseInstance
            New CruiseInstance with all registries built and references resolved.

        Raises
        ------
        ValidationError
            If the configuration does not match the expected schema.
        ReferenceError
            If referenced points or lines are not found in the catalog.

        Examples
        --------
        >>> config = {
        ...     "cruise_name": "Test Cruise",
        ...     "default_vessel_speed": 10.0,
        ...     "points": [{"name": "P1", "latitude": 60.0, "longitude": 5.0}],
        ...     "legs": [{"name": "Leg1", "departure_port": "Bergen", "arrival_port": "Tromsø"}]
        ... }
        >>> cruise = CruiseInstance.from_dict(config)
        >>> cruise.config.cruise_name
        'Test Cruise'
        """
        # Create a temporary instance to leverage existing initialization logic
        instance = cls.__new__(cls)

        # Set path to None since we're creating from dict
        instance.config_path = None
        instance.raw_data = config_dict.copy()

        # 1. Validation Pass (Pydantic)
        instance.config = CruiseConfig(**instance.raw_data)

        # 2. Indexing Pass (Build the Catalog Registry)
        instance.point_registry: dict[str, PointDefinition] = {
            s.name: s for s in (instance.config.points or [])
        }
        instance.line_registry: dict[str, LineDefinition] = {
            t.name: t for t in (instance.config.lines or [])
        }
        instance.area_registry: dict[str, AreaDefinition] = {
            a.name: a for a in (instance.config.areas or [])
        }
        instance.port_registry: dict[str, PointDefinition] = {
            p.name: p for p in (instance.config.ports or [])
        }

        # 3. Config Port Resolution Pass
        instance._resolve_config_ports()

        # 4. Port Enrichment Pass
        instance._enrich_leg_ports()

        # 5. Resolution Pass
        instance._resolve_references()

        # 6. Leg Conversion Pass
        instance.runtime_legs = instance._convert_leg_definitions_to_legs()

        return instance

    def to_commented_dict(self) -> dict[str, Any]:
        """
        Export CruiseInstance configuration to a structured dictionary with comment preservation.

        This method provides the foundation for YAML output with canonical field
        ordering and comment preservation capabilities. Returns a dictionary that
        can be processed by ruamel.yaml for structured output with comments.

        Returns
        -------
        Dict[str, Any]
            Dictionary with canonical field ordering suitable for YAML export
            with comment preservation.

        Notes
        -----
        The output dictionary follows canonical ordering:
        1. Cruise Metadata (cruise_name, description, start_date, start_time)
        2. Vessel Parameters (default_vessel_speed, turnaround_time, etc.)
        3. Calculation Settings (calculate_*, day_start_hour, etc.)
        4. Catalog Definitions (points, lines, areas, ports)
        5. Schedule Organization (legs)

        Comment preservation is handled at the YAML layer using ruamel.yaml
        with end-of-line and section header comment support.
        """
        return serialization.to_commented_dict(self)

    def to_yaml(
        self, output_path: Union[str, Path], enrichment_command: Optional[str] = None
    ) -> None:
        """
        Export CruiseInstance configuration to YAML file with canonical ordering.

        This method provides direct YAML export capability with standardized
        field ordering and basic comment preservation. Uses ruamel.yaml for
        structured output that maintains readability.

        Parameters
        ----------
        output_path : Union[str, Path]
            Path where the YAML file should be written.
        enrichment_command : Optional[str]
            The enrichment command that was used to create this file, for documentation.

        Raises
        ------
        IOError
            If the output file cannot be written.

        Examples
        --------
        >>> cruise = CruiseInstance.from_dict(config_dict)
        >>> cruise.to_yaml("enhanced_cruise.yaml")

        Notes
        -----
        The exported YAML follows canonical field ordering and includes
        section comments for improved readability. This replaces the need
        for dual state management during enrichment operations.
        """
        return serialization.to_yaml(self, output_path, enrichment_command)

    # === CruiseInstance Enhancement Methods ===
    # These methods modify the CruiseInstance object state to add functionality

    def expand_sections(self, default_depth: float = -9999.0) -> dict[str, int]:
        """
        Expand CTD sections into individual station definitions.

        This method finds CTD sections in lines catalog and expands them into
        individual stations, adding them to the point_registry. This is structural
        enrichment that modifies the cruise configuration.

        Parameters
        ----------
        default_depth : float, optional
            Default depth value for expanded stations. Default is -9999.0.

        Returns
        -------
        dict[str, int]
            Dictionary with expansion summary:
            - sections_expanded: Number of sections expanded
            - stations_from_expansion: Number of stations created
        """
        return enrichment.expand_sections(self, default_depth)

    def enrich_depths(
        self, bathymetry_source: str = "etopo2022", bathymetry_dir: str = "data"
    ) -> set[str]:
        """
        Add bathymetry depths to stations that are missing water_depth values.

        This method modifies the point_registry directly by adding water depth
        information from bathymetry datasets to stations that don't have depth
        values or have placeholder values.

        Parameters
        ----------
        bathymetry_source : str, optional
            Bathymetry dataset to use. Default is "etopo2022".
        bathymetry_dir : str, optional
            Directory containing bathymetry data. Default is "data".

        Returns
        -------
        set[str]
            Set of station names that had depths added.
        """
        return enrichment.enrich_depths(self, bathymetry_source, bathymetry_dir)

    def add_station_defaults(self) -> int:
        """
        Add missing defaults to station definitions.

        This method adds default duration to mooring operations and other stations
        that lack required default values.

        Returns
        -------
        int
            Number of station defaults added.
        """
        return enrichment.add_station_defaults(self)

    def expand_ports(self) -> dict[str, int]:
        """
        Expand global port references into full PortDefinition objects.

        This method finds string port references and expands them into full
        PortDefinition objects with coordinates and other metadata from the
        global ports database.

        Returns
        -------
        dict[str, int]
            Dictionary with expansion summary:
            - ports_expanded: Number of global ports expanded
            - leg_ports_expanded: Number of leg ports expanded
        """
        return enrichment.expand_ports(self)

    def add_coordinate_displays(self, coord_format: str = "ddm") -> int:
        """
        Add human-readable coordinate display fields for final YAML output.

        This method adds formatted coordinate annotations that will appear in
        the YAML output but don't affect the core cruise data. This is for
        display enhancement only.

        Parameters
        ----------
        coord_format : str, optional
            Coordinate format to use for display. Default is "ddm".

        Returns
        -------
        int
            Number of coordinate display fields added.
        """
        return enrichment.add_coordinate_displays(self, coord_format)
