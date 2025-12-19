"""Tests for cruiseplan.core.cluster module - Maritime Cluster architecture."""

from cruiseplan.core.cluster import Cluster
from cruiseplan.core.validation import StrategyEnum


class TestCluster:
    """Test the maritime Cluster class for operation boundary management."""

    def test_cluster_basic_initialization(self):
        """Test basic Cluster initialization."""
        cluster = Cluster(name="Test_Cluster")

        assert cluster.name == "Test_Cluster"
        assert cluster.description is None  # default
        assert cluster.strategy == StrategyEnum.SEQUENTIAL  # default
        assert cluster.ordered is True  # default
        assert cluster.operations == []  # default empty

    def test_cluster_with_full_parameters(self):
        """Test Cluster with all parameters."""
        cluster = Cluster(
            name="Full_Cluster",
            description="Test cluster with all parameters",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
            ordered=False,
        )

        assert cluster.name == "Full_Cluster"
        assert cluster.description == "Test cluster with all parameters"
        assert cluster.strategy == StrategyEnum.SPATIAL_INTERLEAVED
        assert cluster.ordered is False

    def test_cluster_add_operation(self):
        """Test adding operations to a cluster."""
        cluster = Cluster(name="Test_Cluster")

        # Mock operation object
        operation = {"name": "STN_001", "operation_type": "CTD"}
        cluster.add_operation(operation)

        assert len(cluster.operations) == 1
        assert cluster.operations[0] == operation

    def test_cluster_boundary_management(self):
        """Test cluster boundary management for reordering constraints."""
        cluster = Cluster(
            name="Boundary_Cluster",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
            ordered=False,  # Allow reordering within cluster
        )

        # Add multiple operations
        op1 = {"name": "STN_001", "operation_type": "CTD"}
        op2 = {"name": "STN_002", "operation_type": "mooring"}
        op3 = {"name": "STN_003", "operation_type": "CTD"}

        cluster.add_operation(op1)
        cluster.add_operation(op2)
        cluster.add_operation(op3)

        assert len(cluster.operations) == 3
        # Operations can be reordered within this cluster since ordered=False
        assert not cluster.ordered

    def test_cluster_string_representation(self):
        """Test string representation of Cluster."""
        cluster = Cluster(
            name="Test_Cluster",
            description="Test cluster",
        )

        str_repr = str(cluster)
        assert "Test_Cluster" in str_repr

    def test_cluster_from_definition(self):
        """Test creating cluster from ClusterDefinition."""
        # Mock ClusterDefinition
        cluster_def = type(
            "ClusterDefinition",
            (),
            {
                "name": "Generated_Cluster",
                "description": "From definition",
                "strategy": StrategyEnum.SEQUENTIAL,
                "ordered": True,
                "activities": ["STN_001", "STN_002"],
            },
        )()

        cluster = Cluster.from_definition(cluster_def)

        assert cluster.name == "Generated_Cluster"
        assert cluster.description == "From definition"
        assert cluster.strategy == StrategyEnum.SEQUENTIAL
        assert cluster.ordered is True


class TestClusterBoundaryLogic:
    """Test cluster boundary management and operation shuffling control."""

    def test_ordered_cluster_preserves_sequence(self):
        """Test that ordered clusters preserve operation sequence."""
        cluster = Cluster(
            name="Ordered_Cluster",
            strategy=StrategyEnum.SEQUENTIAL,
            ordered=True,  # Strict ordering
        )

        operations = [
            {"name": "STN_001", "priority": 3},
            {"name": "STN_002", "priority": 1},
            {"name": "STN_003", "priority": 2},
        ]

        for op in operations:
            cluster.add_operation(op)

        # Should preserve addition order regardless of priority
        assert cluster.operations[0]["name"] == "STN_001"
        assert cluster.operations[1]["name"] == "STN_002"
        assert cluster.operations[2]["name"] == "STN_003"
        assert cluster.ordered is True

    def test_unordered_cluster_allows_reordering(self):
        """Test that unordered clusters allow operation reordering."""
        cluster = Cluster(
            name="Flexible_Cluster",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
            ordered=False,  # Allow reordering
        )

        operations = [
            {"name": "STN_001", "operation_type": "CTD"},
            {"name": "STN_002", "operation_type": "mooring"},
            {"name": "STN_003", "operation_type": "water_sampling"},
        ]

        for op in operations:
            cluster.add_operation(op)

        # Operations can be shuffled/reordered since ordered=False
        assert len(cluster.operations) == 3
        assert not cluster.ordered  # Indicates reordering is allowed

    def test_cluster_strategy_affects_execution(self):
        """Test that cluster strategy affects operation execution planning."""
        # Sequential cluster
        seq_cluster = Cluster(
            name="Sequential_Cluster",
            strategy=StrategyEnum.SEQUENTIAL,
        )

        # Parallel cluster
        par_cluster = Cluster(
            name="Parallel_Cluster",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
        )

        assert seq_cluster.strategy == StrategyEnum.SEQUENTIAL
        assert par_cluster.strategy == StrategyEnum.SPATIAL_INTERLEAVED

        # Strategy affects how operations within cluster are scheduled
        # (Implementation details would be in scheduler, this tests the property)

    def test_empty_cluster_operations(self):
        """Test cluster with no operations."""
        cluster = Cluster(name="Empty_Cluster")

        assert len(cluster.operations) == 0
        assert cluster.operations == []

        # Adding operations should work normally
        operation = {"name": "STN_001", "operation_type": "CTD"}
        cluster.add_operation(operation)

        assert len(cluster.operations) == 1
