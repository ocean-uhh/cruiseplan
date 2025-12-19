"""Tests for cruiseplan.core.leg module - Maritime Leg architecture."""

from cruiseplan.core.cluster import Cluster
from cruiseplan.core.leg import Leg
from cruiseplan.core.validation import StrategyEnum


class TestLeg:
    """Test the new maritime Leg class."""

    def test_leg_basic_initialization(self):
        """Test basic Leg initialization with required ports."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        assert leg.name == "Test_Leg"
        # Ports are resolved to PortDefinition objects
        assert leg.departure_port.name == departure_port["name"]
        assert leg.departure_port.latitude == departure_port["latitude"]
        assert leg.arrival_port.name == arrival_port["name"]
        assert leg.arrival_port.longitude == arrival_port["longitude"]
        assert leg.strategy == StrategyEnum.SEQUENTIAL  # default
        assert leg.ordered is True  # default
        assert leg.clusters == []  # default empty

    def test_leg_with_full_parameters(self):
        """Test Leg with all optional parameters."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Full_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
            description="Test leg with all parameters",
            strategy=StrategyEnum.SPATIAL_INTERLEAVED,
            ordered=False,
            first_waypoint="STN_001",
            last_waypoint="STN_999",
        )

        # Set parameter inheritance attributes
        leg.vessel_speed = 12.0
        leg.distance_between_stations = 50.0
        leg.turnaround_time = 45.0

        assert leg.description == "Test leg with all parameters"
        assert leg.strategy == StrategyEnum.SPATIAL_INTERLEAVED
        assert leg.ordered is False
        assert leg.first_waypoint == "STN_001"
        assert leg.last_waypoint == "STN_999"
        assert leg.vessel_speed == 12.0
        assert leg.distance_between_stations == 50.0
        assert leg.turnaround_time == 45.0

        # Test the new entry/exit point abstraction methods
        entry_point = leg.get_entry_point()  # Should return departure port coordinates
        exit_point = leg.get_exit_point()  # Should return arrival port coordinates
        assert entry_point == (60.0, -20.0)  # departure_port coordinates
        assert exit_point == (64.0, -22.0)  # arrival_port coordinates

    def test_leg_add_cluster(self):
        """Test adding clusters to a leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        cluster = Cluster(name="Test_Cluster", description="Test cluster")
        leg.add_cluster(cluster)

        assert len(leg.clusters) == 1
        assert leg.clusters[0] == cluster

    def test_leg_get_effective_speed_inheritance(self):
        """Test parameter inheritance for vessel speed."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        # Test with leg-specific speed
        leg_with_speed = Leg(
            name="Fast_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )
        leg_with_speed.vessel_speed = 15.0

        assert leg_with_speed.get_effective_speed(default_speed=10.0) == 15.0

        # Test with default speed
        leg_without_speed = Leg(
            name="Default_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        assert leg_without_speed.get_effective_speed(default_speed=10.0) == 10.0

    def test_leg_string_representation(self):
        """Test string representation of Leg."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        str_repr = str(leg)
        assert "Test_Leg" in str_repr
        assert "Port_A" in str_repr
        assert "Port_B" in str_repr

    def test_leg_clusters_property(self):
        """Test clusters property management."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        leg = Leg(
            name="Test_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        # Initially empty
        assert len(leg.clusters) == 0

        # Add multiple clusters
        cluster1 = Cluster(name="Cluster_1")
        cluster2 = Cluster(name="Cluster_2")

        leg.add_cluster(cluster1)
        leg.add_cluster(cluster2)

        assert len(leg.clusters) == 2
        assert cluster1 in leg.clusters
        assert cluster2 in leg.clusters


class TestLegParameterInheritance:
    """Test parameter inheritance behavior in maritime Leg class."""

    def test_get_effective_turnaround_time(self):
        """Test turnaround time inheritance."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        # With leg-specific turnaround time
        leg_with_turnaround = Leg(
            name="Quick_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )
        leg_with_turnaround.turnaround_time = 20.0

        assert (
            leg_with_turnaround.get_effective_turnaround_time(default_turnaround=30.0)
            == 20.0
        )

        # Without leg-specific turnaround time
        leg_without_turnaround = Leg(
            name="Default_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        assert (
            leg_without_turnaround.get_effective_turnaround_time(
                default_turnaround=30.0
            )
            == 30.0
        )

    def test_get_effective_distance_between_stations(self):
        """Test distance between stations inheritance."""
        departure_port = {"name": "Port_A", "latitude": 60.0, "longitude": -20.0}
        arrival_port = {"name": "Port_B", "latitude": 64.0, "longitude": -22.0}

        # With leg-specific distance
        leg_with_distance = Leg(
            name="Sparse_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )
        leg_with_distance.distance_between_stations = 100.0

        assert leg_with_distance.get_effective_spacing(default_spacing=50.0) == 100.0

        # Without leg-specific distance
        leg_without_distance = Leg(
            name="Default_Leg",
            departure_port=departure_port,
            arrival_port=arrival_port,
        )

        assert leg_without_distance.get_effective_spacing(default_spacing=50.0) == 50.0
