from typing import Any, List, Optional

from cruiseplan.core.operations import BaseOperation, CompositeOperation

# Assuming you have a StrategyEnum defined in cruiseplan.core.validation
from cruiseplan.core.validation import StrategyEnum


class Leg:
    """
    Discrete working area/time period container for cruise operations.

    The Leg class acts as the 'Chapter' in the cruise timeline, grouping related
    operations and composites (clusters/sections) and allowing for leg-specific
    overrides of cruise parameters like speed and station spacing.

    Attributes
    ----------
    name : str
        Unique identifier for this leg.
    description : Optional[str]
        Optional human-readable description of the leg's purpose.
    strategy : StrategyEnum
        Execution strategy for operations (default: SEQUENTIAL).
    ordered : bool
        Whether operations should maintain their specified order (default: True).
    operations : List[BaseOperation]
        List of standalone operations (e.g., single CTD, single Transit).
    composites : List[CompositeOperation]
        List of composite operations (e.g., Sections, Array Clusters).
    vessel_speed : Optional[float]
        Leg-specific vessel speed override (None uses cruise default).
    distance_between_stations : Optional[float]
        Leg-specific station spacing override (None uses cruise default).
    """

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        strategy: StrategyEnum = StrategyEnum.SEQUENTIAL,
        ordered: bool = True,
    ):
        """
        Initialize a Leg with the specified parameters.

        Parameters
        ----------
        name : str
            Unique identifier for this leg.
        description : Optional[str], optional
            Human-readable description of the leg's purpose.
        strategy : StrategyEnum, optional
            Execution strategy for operations (default: SEQUENTIAL).
        ordered : bool, optional
            Whether operations should maintain their specified order (default: True).
        """
        self.name = name
        self.description = description
        self.strategy = strategy
        self.ordered = ordered

        # Operation containers
        # Operations are simple, standalone tasks (e.g., a single CTD, a single Transit)
        self.operations: List[BaseOperation] = []
        # Composites are logical groups (e.g., a Section, an Array Cluster)
        self.composites: List[CompositeOperation] = []

        # Inheritance attributes (to be set by parent Cruise)
        # These allow a Leg to override global cruise settings.
        self.vessel_speed: Optional[float] = None
        self.distance_between_stations: Optional[float] = None

    def add_operation(self, operation: BaseOperation) -> None:
        """
        Add a single, standalone operation to this leg.

        Parameters
        ----------
        operation : BaseOperation
            The operation to add (e.g., a single CTD cast or transit).
        """
        self.operations.append(operation)

    def add_composite(self, composite: CompositeOperation) -> None:
        """
        Add a composite operation (cluster/section) to this leg.

        Parameters
        ----------
        composite : CompositeOperation
            The composite operation to add (e.g., a section or array cluster).
        """
        self.composites.append(composite)

    def get_all_operations(self) -> List[BaseOperation]:
        """
        Flatten all operations including those within composites' children.

        This provides a unified list of atomic operations for route optimization
        that respects the Leg's boundaries.

        Returns
        -------
        List[BaseOperation]
            Unified list containing both standalone operations and operations
            from within composite operations.
        """
        # Start with simple, direct operations
        all_ops = self.operations.copy()

        # Add children from all composite operations
        for composite in self.composites:
            all_ops.extend(composite.children)

        return all_ops

    def calculate_total_duration(self, rules: Any) -> float:
        """
        Calculate total duration for all operations in this leg.

        Note: The duration for composites includes internal routing/optimization
        logic defined within the CompositeOperation class itself.

        Parameters
        ----------
        rules : Any
            Duration calculation rules/parameters.

        Returns
        -------
        float
            Total duration in appropriate units (typically minutes or hours).
        """
        total = 0.0

        # Duration of standalone operations (Point, Line, Area)
        for op in self.operations:
            total += op.calculate_duration(rules)

        # Duration of Composite operations (includes internal routing/optimization)
        for composite in self.composites:
            total += composite.calculate_duration(rules)

        return total

    def get_effective_speed(self, default_speed: float) -> float:
        """
        Get leg-specific vessel speed or fallback to the parent cruise's default.

        Parameters
        ----------
        default_speed : float
            The default speed from the parent cruise configuration.

        Returns
        -------
        float
            The effective vessel speed for this leg.
        """
        return self.vessel_speed if self.vessel_speed is not None else default_speed

    def get_effective_spacing(self, default_spacing: float) -> float:
        """
        Get leg-specific station spacing or fallback to the parent cruise's default.

        Parameters
        ----------
        default_spacing : float
            The default spacing from the parent cruise configuration.

        Returns
        -------
        float
            The effective station spacing for this leg.
        """
        return (
            self.distance_between_stations
            if self.distance_between_stations is not None
            else default_spacing
        )
