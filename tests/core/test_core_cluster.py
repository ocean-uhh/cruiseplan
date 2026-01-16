"""Tests for cruiseplan.core.cluster module - Maritime Cluster architecture."""

from cruiseplan.core.organizational import Cluster
from cruiseplan.schema import StrategyEnum


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
        from unittest.mock import MagicMock

        operation = MagicMock(name="STN_001")
        operation.name = "STN_001"
        operation.operation_type = "CTD"
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

        # Add multiple operations (create mock BaseOperation objects)
        from unittest.mock import MagicMock

        op1 = MagicMock(name="STN_001")
        op1.name = "STN_001"
        op1.operation_type = "CTD"

        op2 = MagicMock(name="STN_002")
        op2.name = "STN_002"
        op2.operation_type = "mooring"

        op3 = MagicMock(name="STN_003")
        op3.name = "STN_003"
        op3.operation_type = "CTD"

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

        # Create mock operation objects
        from unittest.mock import MagicMock

        operations = []

        op1 = MagicMock(name="STN_001")
        op1.name = "STN_001"
        op1.priority = 3
        operations.append(op1)

        op2 = MagicMock(name="STN_002")
        op2.name = "STN_002"
        op2.priority = 1
        operations.append(op2)

        op3 = MagicMock(name="STN_003")
        op3.name = "STN_003"
        op3.priority = 2
        operations.append(op3)

        for op in operations:
            cluster.add_operation(op)

        # Should preserve addition order regardless of priority
        assert cluster.operations[0].name == "STN_001"
        assert cluster.operations[1].name == "STN_002"
        assert cluster.operations[2].name == "STN_003"
        assert cluster.ordered is True

    def test_unordered_cluster_allows_reordering(self):
        """Test that unordered clusters allow operation reordering."""
        cluster = Cluster(
            name="Flexible_Cluster",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
            ordered=False,  # Allow reordering
        )

        # Create mock operation objects
        from unittest.mock import MagicMock

        operations = []

        op1 = MagicMock(name="STN_001")
        op1.name = "STN_001"
        op1.operation_type = "CTD"
        operations.append(op1)

        op2 = MagicMock(name="STN_002")
        op2.name = "STN_002"
        op2.operation_type = "mooring"
        operations.append(op2)

        op3 = MagicMock(name="STN_003")
        op3.name = "STN_003"
        op3.operation_type = "water_sampling"
        operations.append(op3)

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
        from unittest.mock import MagicMock

        operation = MagicMock(name="STN_001")
        operation.name = "STN_001"
        operation.operation_type = "CTD"
        cluster.add_operation(operation)

        assert len(cluster.operations) == 1


class TestClusterOperationMethods:
    """Test cluster operation management methods."""

    def test_remove_operation_success(self):
        """Test removing operation that exists."""
        cluster = Cluster(name="Test_Cluster")

        # Create mock operations with name attribute
        op1 = type("MockOperation", (), {"name": "STN_001"})()
        op2 = type("MockOperation", (), {"name": "STN_002"})()

        cluster.add_operation(op1)
        cluster.add_operation(op2)

        result = cluster.remove_operation("STN_001")
        assert result is True
        assert len(cluster.operations) == 1
        assert cluster.operations[0].name == "STN_002"

    def test_remove_operation_not_found(self):
        """Test removing operation that doesn't exist."""
        cluster = Cluster(name="Test_Cluster")

        result = cluster.remove_operation("NonExistent")
        assert result is False
        assert len(cluster.operations) == 0

    def test_get_operation_success(self):
        """Test getting operation by name."""
        cluster = Cluster(name="Test_Cluster")

        op1 = type("MockOperation", (), {"name": "STN_001"})()
        cluster.add_operation(op1)

        result = cluster.get_operation("STN_001")
        assert result == op1

    def test_get_operation_not_found(self):
        """Test getting operation that doesn't exist."""
        cluster = Cluster(name="Test_Cluster")

        result = cluster.get_operation("NonExistent")
        assert result is None

    def test_get_all_operations(self):
        """Test getting all operations returns copy."""
        cluster = Cluster(name="Test_Cluster")

        op1 = type("MockOperation", (), {"name": "STN_001"})()
        op2 = type("MockOperation", (), {"name": "STN_002"})()
        cluster.add_operation(op1)
        cluster.add_operation(op2)

        operations = cluster.get_all_operations()
        assert len(operations) == 2
        assert operations is not cluster.operations  # Should be a copy
        assert operations[0] == op1
        assert operations[1] == op2

    def test_calculate_total_duration(self):
        """Test calculating total duration for cluster operations."""
        cluster = Cluster(name="Test_Cluster")

        # Mock operations with calculate_duration method
        # Note: The lambda needs to accept 'self' as first argument since it's a method
        op1 = type(
            "MockOperation",
            (),
            {"name": "STN_001", "calculate_duration": lambda self, rules: 60.0},
        )()
        op2 = type(
            "MockOperation",
            (),
            {"name": "STN_002", "calculate_duration": lambda self, rules: 90.0},
        )()

        cluster.add_operation(op1)
        cluster.add_operation(op2)

        total_duration = cluster.calculate_total_duration("mock_rules")
        assert total_duration == 150.0

    def test_is_empty(self):
        """Test checking if cluster is empty."""
        cluster = Cluster(name="Test_Cluster")

        assert cluster.is_empty() is True

        op1 = type("MockOperation", (), {"name": "STN_001"})()
        cluster.add_operation(op1)

        assert cluster.is_empty() is False

    def test_get_operation_count(self):
        """Test getting operation count."""
        cluster = Cluster(name="Test_Cluster")

        assert cluster.get_operation_count() == 0

        op1 = type("MockOperation", (), {"name": "STN_001"})()
        op2 = type("MockOperation", (), {"name": "STN_002"})()
        cluster.add_operation(op1)
        cluster.add_operation(op2)

        assert cluster.get_operation_count() == 2

    def test_allows_reordering(self):
        """Test checking if cluster allows reordering."""
        ordered_cluster = Cluster(name="Ordered_Cluster", ordered=True)
        unordered_cluster = Cluster(name="Unordered_Cluster", ordered=False)

        assert ordered_cluster.allows_reordering() is False
        assert unordered_cluster.allows_reordering() is True

    def test_get_operation_names(self):
        """Test getting list of operation names."""
        cluster = Cluster(name="Test_Cluster")

        op1 = type("MockOperation", (), {"name": "STN_001"})()
        op2 = type("MockOperation", (), {"name": "STN_002"})()
        cluster.add_operation(op1)
        cluster.add_operation(op2)

        names = cluster.get_operation_names()
        assert names == ["STN_001", "STN_002"]

    def test_get_entry_point_no_operations(self):
        """Test getting entry point when cluster is empty."""
        cluster = Cluster(name="Test_Cluster")

        entry_point = cluster.get_entry_point()
        assert entry_point is None

    def test_get_entry_point_with_operations(self):
        """Test getting entry point with operations."""
        cluster = Cluster(name="Test_Cluster")

        # Mock operation with direct latitude/longitude
        op1 = type(
            "MockOperation",
            (),
            {"name": "STN_001", "latitude": 60.0, "longitude": -20.0},
        )()
        cluster.add_operation(op1)

        entry_point = cluster.get_entry_point()
        assert entry_point == (60.0, -20.0)

    def test_get_entry_point_no_position_attribute(self):
        """Test getting entry point when operations lack latitude/longitude attributes."""
        cluster = Cluster(name="Test_Cluster")

        op1 = type("MockOperation", (), {"name": "STN_001"})()
        cluster.add_operation(op1)

        entry_point = cluster.get_entry_point()
        assert entry_point is None

    def test_get_exit_point_no_operations(self):
        """Test getting exit point when cluster is empty."""
        cluster = Cluster(name="Test_Cluster")

        exit_point = cluster.get_exit_point()
        assert exit_point is None

    def test_get_exit_point_with_operations(self):
        """Test getting exit point with operations."""
        cluster = Cluster(name="Test_Cluster")

        # Mock operations with direct latitude/longitude
        op1 = type(
            "MockOperation",
            (),
            {"name": "STN_001", "latitude": 60.0, "longitude": -20.0},
        )()
        op2 = type(
            "MockOperation",
            (),
            {"name": "STN_002", "latitude": 65.0, "longitude": -25.0},
        )()
        cluster.add_operation(op1)
        cluster.add_operation(op2)

        exit_point = cluster.get_exit_point()
        assert exit_point == (65.0, -25.0)  # Should be last operation

    def test_repr(self):
        """Test __repr__ method."""
        cluster = Cluster(name="Test_Cluster", ordered=False)

        repr_str = repr(cluster)
        assert "Test_Cluster" in repr_str
        assert "operations=0" in repr_str
        assert "ordered=False" in repr_str

    def test_str(self):
        """Test __str__ method."""
        ordered_cluster = Cluster(name="Ordered_Cluster", ordered=True)
        unordered_cluster = Cluster(name="Unordered_Cluster", ordered=False)

        ordered_str = str(ordered_cluster)
        unordered_str = str(unordered_cluster)

        assert "Ordered_Cluster" in ordered_str
        assert "strict order" in ordered_str

        assert "Unordered_Cluster" in unordered_str
        assert "flexible order" in unordered_str

    def test_from_definition_defaults(self):
        """Test from_definition with None values uses defaults."""
        cluster_def = type(
            "ClusterDefinition",
            (),
            {
                "name": "Default_Cluster",
                "description": None,
                "strategy": None,
                "ordered": None,
                "activities": ["STN_001"],
            },
        )()

        cluster = Cluster.from_definition(cluster_def)

        assert cluster.name == "Default_Cluster"
        assert cluster.description is None
        assert cluster.strategy == StrategyEnum.SEQUENTIAL  # Default
        assert cluster.ordered is True  # Default
