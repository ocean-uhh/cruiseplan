"""
Cluster runtime class for operation boundary management.

This module provides the Cluster runtime class that handles boundary management
for operation shuffling/reordering during scheduling. Clusters define which
operations can be reordered together while maintaining separation from other
clusters or the parent leg.
"""

from typing import Any, List, Optional

from cruiseplan.core.operations import BaseOperation
from cruiseplan.core.validation import ClusterDefinition, StrategyEnum


class Cluster:
    """
    Runtime container for operation boundary management during scheduling.

    Clusters define boundaries for operation shuffling/reordering. Operations within
    a cluster can be reordered according to the cluster's strategy, but cannot be
    mixed with operations from other clusters or the parent leg.

    This provides scientific flexibility (weather-dependent reordering) while
    maintaining operational safety (critical sequences protected).

    Attributes
    ----------
    name : str
        Unique identifier for this cluster.
    description : Optional[str]
        Human-readable description of the cluster's purpose.
    strategy : StrategyEnum
        Scheduling strategy for operations within this cluster.
    ordered : bool
        Whether operations should maintain their defined order.
    operations : List[BaseOperation]
        List of operations contained within this cluster boundary.

    Examples
    --------
    >>> # Weather-flexible CTD cluster
    >>> ctd_cluster = Cluster(
    ...     name="CTD_Survey",
    ...     description="CTD operations that can be reordered for weather",
    ...     strategy=StrategyEnum.SEQUENTIAL,
    ...     ordered=False  # Allow weather-based reordering
    ... )

    >>> # Critical mooring sequence cluster
    >>> mooring_cluster = Cluster(
    ...     name="Mooring_Deployment",
    ...     description="Critical mooring sequence - strict order required",
    ...     strategy=StrategyEnum.SEQUENTIAL,
    ...     ordered=True  # Maintain deployment order for safety
    ... )
    """

    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        strategy: StrategyEnum = StrategyEnum.SEQUENTIAL,
        ordered: bool = True,
    ):
        """
        Initialize a Cluster with the specified parameters.

        Parameters
        ----------
        name : str
            Unique identifier for this cluster.
        description : Optional[str], optional
            Human-readable description of the cluster's purpose.
        strategy : StrategyEnum, optional
            Scheduling strategy for operations within cluster (default: SEQUENTIAL).
        ordered : bool, optional
            Whether operations should maintain their defined order (default: True).
        """
        self.name = name
        self.description = description
        self.strategy = strategy
        self.ordered = ordered

        # Operation container - maintains cluster boundary
        self.operations: List[BaseOperation] = []

    def add_operation(self, operation: BaseOperation) -> None:
        """
        Add an operation to this cluster boundary.

        Operations added to a cluster can be reordered with other operations
        in the same cluster (subject to the cluster's ordering constraints)
        but will not be mixed with operations from other clusters.

        Parameters
        ----------
        operation : BaseOperation
            The operation to add to this cluster boundary.
        """
        self.operations.append(operation)

    def remove_operation(self, operation_name: str) -> bool:
        """
        Remove an operation from this cluster by name.

        Parameters
        ----------
        operation_name : str
            Name of the operation to remove.

        Returns
        -------
        bool
            True if operation was found and removed, False otherwise.
        """
        for i, operation in enumerate(self.operations):
            if operation.name == operation_name:
                del self.operations[i]
                return True
        return False

    def get_operation(self, operation_name: str) -> Optional[BaseOperation]:
        """
        Get an operation from this cluster by name.

        Parameters
        ----------
        operation_name : str
            Name of the operation to retrieve.

        Returns
        -------
        Optional[BaseOperation]
            The operation if found, None otherwise.
        """
        for operation in self.operations:
            if operation.name == operation_name:
                return operation
        return None

    def get_all_operations(self) -> List[BaseOperation]:
        """
        Get all operations within this cluster boundary.

        Returns a copy of the operations list to prevent external modification
        of the cluster boundary.

        Returns
        -------
        List[BaseOperation]
            Copy of all operations within this cluster.
        """
        return self.operations.copy()

    def calculate_total_duration(self, rules: Any) -> float:
        """
        Calculate total duration for all operations within this cluster.

        Parameters
        ----------
        rules : Any
            Duration calculation rules/parameters.

        Returns
        -------
        float
            Total duration in appropriate units (typically minutes).
        """
        total = 0.0
        for operation in self.operations:
            total += operation.calculate_duration(rules)
        return total

    def is_empty(self) -> bool:
        """
        Check if this cluster contains no operations.

        Returns
        -------
        bool
            True if cluster is empty, False otherwise.
        """
        return len(self.operations) == 0

    def get_operation_count(self) -> int:
        """
        Get the number of operations in this cluster.

        Returns
        -------
        int
            Number of operations within the cluster boundary.
        """
        return len(self.operations)

    def allows_reordering(self) -> bool:
        """
        Check if this cluster allows operation reordering.

        Returns
        -------
        bool
            True if operations can be reordered within cluster, False if strict order required.
        """
        return not self.ordered

    def get_operation_names(self) -> List[str]:
        """
        Get names of all operations within this cluster.

        Returns
        -------
        List[str]
            List of operation names within the cluster.
        """
        return [operation.name for operation in self.operations]

    def get_entry_point(self) -> Optional[tuple[float, float]]:
        """
        Get the geographic entry point for this cluster (first operation position).

        This provides a standardized interface regardless of internal field names.

        Returns
        -------
        tuple[float, float] or None
            (latitude, longitude) of the cluster's entry point, or None if no operations.
        """
        if not self.operations:
            return None
        first_op = self.operations[0]
        if hasattr(first_op, "position"):
            return (first_op.position.latitude, first_op.position.longitude)
        return None

    def get_exit_point(self) -> Optional[tuple[float, float]]:
        """
        Get the geographic exit point for this cluster (last operation position).

        This provides a standardized interface regardless of internal field names.

        Returns
        -------
        tuple[float, float] or None
            (latitude, longitude) of the cluster's exit point, or None if no operations.
        """
        if not self.operations:
            return None
        last_op = self.operations[-1]
        if hasattr(last_op, "position"):
            return (last_op.position.latitude, last_op.position.longitude)
        return None

    def __repr__(self) -> str:
        """
        String representation of the cluster.

        Returns
        -------
        str
            String representation showing cluster name and operation count.
        """
        return f"Cluster(name='{self.name}', operations={self.get_operation_count()}, ordered={self.ordered})"

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns
        -------
        str
            Human-readable description of the cluster.
        """
        order_desc = "strict order" if self.ordered else "flexible order"
        return f"Cluster '{self.name}': {self.get_operation_count()} operations ({order_desc})"

    @classmethod
    def from_definition(cls, cluster_def: ClusterDefinition) -> "Cluster":
        """
        Create a Cluster runtime instance from a ClusterDefinition.

        This factory method converts a validated ClusterDefinition into a runtime
        Cluster with proper boundary management configuration.

        Parameters
        ----------
        cluster_def : ClusterDefinition
            Validated cluster definition from YAML configuration.

        Returns
        -------
        Cluster
            New Cluster runtime instance with boundary management settings.
        """
        cluster = cls(
            name=cluster_def.name,
            description=cluster_def.description,
            strategy=(
                cluster_def.strategy
                if cluster_def.strategy
                else StrategyEnum.SEQUENTIAL
            ),
            ordered=cluster_def.ordered if cluster_def.ordered is not None else True,
        )

        # Note: Operations will be added later during resolution phase
        # based on the activities listed in cluster_def.activities
        # The cluster boundary structure is established here

        return cluster
