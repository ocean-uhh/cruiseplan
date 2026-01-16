"""Tests for cruiseplan.core.leg module - Maritime Leg architecture."""

from unittest.mock import MagicMock

import pytest

from cruiseplan.core.organizational import Cluster, Leg
from cruiseplan.schema import StrategyEnum


class TestLeg:
    """Test the new maritime Leg class."""

    def test_leg_basic_initialization(self):
        """Test leg initialization with ports."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        assert leg.name == "Test_Leg"
        assert leg.departure_port.name == "Port_A"
        assert leg.arrival_port.name == "Port_B"
        assert leg.strategy == StrategyEnum.SEQUENTIAL
        assert leg.ordered is True
        assert len(leg.operations) == 0
        assert len(leg.clusters) == 0

    def test_leg_with_full_parameters(self):
        """Test leg with all optional parameters."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Full_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            description="Test description",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
            ordered=False,
            first_activity="WP1",
            last_activity="WP2",
        )

        assert leg.name == "Full_Leg"
        assert leg.description == "Test description"
        assert leg.strategy == StrategyEnum.SPATIAL_INTERLEAVED
        assert leg.ordered is False
        assert leg.first_activity == "WP1"
        assert leg.last_activity == "WP2"

    def test_leg_add_cluster(self):
        """Test adding clusters to a leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        cluster = Cluster(name="TestCluster")
        leg.add_cluster(cluster)

        assert len(leg.clusters) == 1
        assert leg.clusters[0] == cluster

    def test_leg_get_vessel_speed_inheritance(self):
        """Test speed parameter inheritance."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        # Test with no override (use default)
        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )
        assert leg.get_vessel_speed(12.0) == 12.0

        # Test with leg-specific override
        leg.vessel_speed = 15.0
        assert leg.get_vessel_speed(12.0) == 15.0

    def test_leg_string_representation(self):
        """Test string representation methods."""
        departure_port = {"name": "Halifax", "latitude": 44.6, "longitude": -63.6}
        arrival_port = {"name": "St_Johns", "latitude": 47.6, "longitude": -52.7}

        leg = Leg(
            name="Atlantic_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        str_repr = str(leg)
        assert "Atlantic_Leg" in str_repr
        assert "Halifax → St_Johns" in str_repr
        assert "0 operations" in str_repr

        # Test repr
        repr_str = repr(leg)
        assert "Leg(name='Atlantic_Leg'" in repr_str
        assert "departure='Halifax'" in repr_str
        assert "arrival='St_Johns'" in repr_str

    def test_leg_clusters_property(self):
        """Test clusters property returns copy."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        cluster1 = Cluster(name="Cluster1")
        cluster2 = Cluster(name="Cluster2")
        leg.add_cluster(cluster1)
        leg.add_cluster(cluster2)

        clusters = leg.get_all_clusters()
        assert len(clusters) == 2
        assert cluster1 in clusters
        assert cluster2 in clusters

        # Ensure it's a copy, not reference
        clusters.clear()
        assert len(leg.clusters) == 2


class TestLegParameterInheritance:
    """Test parameter inheritance functionality."""

    def test_get_turnaround_time(self):
        """Test turnaround time inheritance."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        # Test default value
        assert leg.get_turnaround_time(30.0) == 30.0

        # Test override
        leg.turnaround_time = 45.0
        assert leg.get_turnaround_time(30.0) == 45.0

    def test_get_station_spacing(self):
        """Test station spacing inheritance."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        # Test default value
        assert leg.get_station_spacing(10.0) == 10.0

        # Test override
        leg.distance_between_stations = 15.0
        assert leg.get_station_spacing(10.0) == 15.0


class TestLegOperationsManagement:
    """Test operation and cluster management in Leg class."""

    def test_add_operation(self):
        """Test adding operations to a leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        # Create mock operation
        mock_operation = MagicMock()
        mock_operation.name = "Test_Operation"
        leg.add_operation(mock_operation)

        assert len(leg.operations) == 1
        assert leg.operations[0] == mock_operation

    def test_get_all_operations(self):
        """Test getting all operations including those in clusters."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        # Add standalone operation
        standalone_op = MagicMock()
        standalone_op.name = "Standalone_Op"
        leg.add_operation(standalone_op)

        # Add cluster with operations
        cluster = Cluster(name="TestCluster")
        cluster_op1 = MagicMock()
        cluster_op1.name = "Cluster_Op1"
        cluster_op2 = MagicMock()
        cluster_op2.name = "Cluster_Op2"

        cluster.add_operation(cluster_op1)
        cluster.add_operation(cluster_op2)
        leg.add_cluster(cluster)

        # Get all operations
        all_ops = leg.get_all_operations()

        assert len(all_ops) == 3
        assert standalone_op in all_ops
        assert cluster_op1 in all_ops
        assert cluster_op2 in all_ops

    def test_get_all_clusters(self):
        """Test getting all clusters in a leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        cluster1 = Cluster(name="Cluster1")
        cluster2 = Cluster(name="Cluster2")
        leg.add_cluster(cluster1)
        leg.add_cluster(cluster2)

        all_clusters = leg.get_all_clusters()

        assert len(all_clusters) == 2
        assert cluster1 in all_clusters
        assert cluster2 in all_clusters

    def test_get_operation_count(self):
        """Test operation count including cluster operations."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        # Add standalone operation
        mock_operation = MagicMock()
        leg.add_operation(mock_operation)

        # Add cluster with 2 operations
        cluster = Cluster(name="TestCluster")
        mock_op1 = MagicMock()
        mock_op2 = MagicMock()
        cluster.add_operation(mock_op1)
        cluster.add_operation(mock_op2)
        leg.add_cluster(cluster)

        # Should count: 1 standalone + 2 from cluster = 3 total
        assert leg.get_operation_count() == 3


class TestLegBehaviorMethods:
    """Test behavioral methods of the Leg class."""

    def test_allows_reordering_ordered_leg(self):
        """Test reordering for ordered leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Ordered_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            ordered=True,
        )

        # With no clusters, ordered leg doesn't allow reordering
        assert leg.allows_reordering() is False

    def test_allows_reordering_unordered_leg(self):
        """Test reordering for unordered leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Unordered_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            ordered=False,
        )

        # Unordered leg allows reordering
        assert leg.allows_reordering() is True

    def test_allows_reordering_with_flexible_clusters(self):
        """Test reordering with flexible clusters."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Ordered_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            ordered=True,
        )

        # Add flexible cluster
        flexible_cluster = Cluster(name="FlexibleCluster", ordered=False)
        leg.add_cluster(flexible_cluster)

        # Ordered leg with flexible clusters allows reordering
        assert leg.allows_reordering() is True

    def test_get_boundary_waypoints(self):
        """Test boundary activity retrieval."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Waypoint_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            first_activity="WP_Start",
            last_activity="WP_End",
        )

        first, last = leg.get_boundary_waypoints()
        assert first == "WP_Start"
        assert last == "WP_End"

    def test_get_boundary_waypoints_none(self):
        """Test boundary activity retrieval when none set."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="No_Waypoint_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        first, last = leg.get_boundary_waypoints()
        assert first is None
        assert last is None

    def test_get_port_positions(self):
        """Test port position retrieval."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        dep_pos, arr_pos = leg.get_port_positions()
        assert dep_pos == (60.0, -20.0)
        assert arr_pos == (64.0, -22.0)

    def test_is_same_port_leg_false(self):
        """Test is_same_port_leg for different ports."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        assert leg.is_same_port_leg() is False

    def test_is_same_port_leg_true(self):
        """Test is_same_port_leg for same port."""
        same_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}

        leg = Leg(
            name="Round_Trip_Leg",
            departure_port=same_port,
            arrival_port=same_port,
        )

        assert leg.is_same_port_leg() is True

    def test_repr_method(self):
        """Test __repr__ method."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        mock_operation = MagicMock()
        leg.add_operation(mock_operation)
        leg.add_cluster(Cluster(name="Cluster1"))

        repr_str = repr(leg)
        assert "Leg(name='Test_Leg'" in repr_str
        assert "departure='Port_A'" in repr_str
        assert "arrival='Port_B'" in repr_str
        assert "operations=1" in repr_str
        assert "clusters=1" in repr_str


class TestLegOperationalActivities:
    """Test operational activity resolution methods."""

    def test_get_operational_entry_point_no_activity(self):
        """Test operational entry point when no activity is set."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        entry_point = leg.get_operational_entry_point()
        assert entry_point is None

    def test_get_operational_exit_point_no_activity(self):
        """Test operational exit point when no activity is set."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        exit_point = leg.get_operational_exit_point()
        assert exit_point is None

    @pytest.mark.skip(
        reason="Obsolete after scheduler refactor - _resolve_station_details removed"
    )
    def test_get_operational_points_with_resolver(self):
        """Test operational points with mock resolver."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            first_activity="WP_Start",
            last_activity="WP_End",
        )

        # Mock resolver that returns coordinates
        mock_resolver = MagicMock()

        # These methods import from scheduler, which might not be available
        # So we test the basic structure
        entry_point = leg.get_operational_entry_point(mock_resolver)
        exit_point = leg.get_operational_exit_point(mock_resolver)

        # These should return None since _resolve_station_details is from scheduler
        assert entry_point is None
        assert exit_point is None


class TestLegFactoryMethod:
    """Test the from_definition() factory method."""

    def test_from_definition_basic_leg(self):
        """Test creating leg from basic definition."""
        from cruiseplan.schema import LegDefinition

        # Create mock definition using actual global ports
        leg_def = LegDefinition(
            name="Test_Leg",
            departure_port="port_halifax",
            arrival_port="port_st_johns",
            activities=[
                {"name": "test_station", "operation_type": "CTD"}
            ],  # Minimal activity to pass validation
        )

        # Create leg from definition
        leg = Leg.from_definition(leg_def)

        assert leg.name == "Test_Leg"
        # Note: Ports will be resolved by resolve_port_reference function
        # Activities are automatically converted to cluster operations
        assert len(leg.operations) == 0
        assert len(leg.clusters) == 1  # Activities automatically clustered

    def test_from_definition_with_activities(self):
        """Test creating leg with activities."""
        from cruiseplan.schema import LegDefinition

        leg_def = LegDefinition(
            name="Test_Leg",
            departure_port="port_halifax",
            arrival_port="port_st_johns",
            first_activity="start_wp",
            last_activity="end_wp",
            activities=[
                {"name": "test_station", "operation_type": "CTD"}
            ],  # Minimal activity to pass validation
        )

        leg = Leg.from_definition(leg_def)

        assert leg.name == "Test_Leg"
        assert leg.first_activity == "start_wp"
        assert leg.last_activity == "end_wp"
        assert len(leg.clusters) == 1  # Activities automatically clustered

    def test_from_definition_with_parameter_overrides(self):
        """Test creating leg with parameter overrides."""
        from cruiseplan.schema import LegDefinition

        leg_def = LegDefinition(
            name="Test_Leg",
            departure_port="port_halifax",
            arrival_port="port_st_johns",
            vessel_speed=15.0,
            turnaround_time=45.0,
            distance_between_stations=20.0,
            activities=[
                {"name": "test_station", "operation_type": "CTD"}
            ],  # Minimal activity to pass validation
        )

        leg = Leg.from_definition(leg_def)

        assert leg.name == "Test_Leg"
        assert leg.vessel_speed == 15.0
        assert leg.turnaround_time == 45.0
        assert leg.distance_between_stations == 20.0
        assert len(leg.clusters) == 1  # Activities automatically clustered
