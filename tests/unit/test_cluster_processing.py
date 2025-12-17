"""
Tests for cluster processing functionality in scheduler.

This module tests the _extract_activities_from_leg function which handles
the priority order: sequence > clusters > stations, and properly processes
cluster definitions containing sequences or stations.
"""

from unittest.mock import MagicMock

from cruiseplan.calculators.scheduler import _extract_activities_from_leg


class TestClusterProcessing:
    """Test cluster processing in activity extraction."""

    def test_priority_sequence_over_clusters(self):
        """Test that leg.sequence takes priority over clusters."""
        leg = MagicMock()
        leg.sequence = ["STN001", "STN002", "STN003"]
        leg.clusters = [MagicMock(sequence=["CLST001", "CLST002"])]
        leg.stations = ["FALLBACK001"]

        result = _extract_activities_from_leg(leg)

        # Should return sequence, ignoring clusters and stations
        assert result == ["STN001", "STN002", "STN003"]

    def test_clusters_when_no_sequence(self):
        """Test that clusters are processed when no sequence exists."""
        leg = MagicMock()
        leg.sequence = None  # No sequence
        leg.clusters = [
            MagicMock(
                sequence=["CLST001", "CLST002"],
                stations=["BACKUP001"],  # Should be ignored when sequence exists
            )
        ]
        leg.stations = ["FALLBACK001"]

        result = _extract_activities_from_leg(leg)

        # Should return cluster sequence
        assert result == ["CLST001", "CLST002"]

    def test_cluster_stations_when_no_sequence(self):
        """Test that cluster stations are used when no cluster sequence exists."""
        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [
            MagicMock(
                sequence=None,  # No cluster sequence
                stations=["CLST_STN001", "CLST_STN002"],
            )
        ]
        leg.stations = ["FALLBACK001"]

        result = _extract_activities_from_leg(leg)

        # Should return cluster stations
        assert result == ["CLST_STN001", "CLST_STN002"]

    def test_multiple_clusters_concatenation(self):
        """Test that multiple clusters are concatenated in order."""
        cluster1 = MagicMock()
        cluster1.sequence = ["C1_STN001", "C1_STN002"]
        cluster1.stations = ["C1_BACKUP"]

        cluster2 = MagicMock()
        cluster2.sequence = None  # No sequence
        cluster2.stations = ["C2_STN001", "C2_STN002"]

        cluster3 = MagicMock()
        cluster3.sequence = ["C3_STN001"]
        cluster3.stations = ["C3_BACKUP"]

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [cluster1, cluster2, cluster3]
        leg.stations = ["FALLBACK"]

        result = _extract_activities_from_leg(leg)

        # Should concatenate: cluster1.sequence + cluster2.stations + cluster3.sequence
        expected = ["C1_STN001", "C1_STN002", "C2_STN001", "C2_STN002", "C3_STN001"]
        assert result == expected

    def test_fallback_to_leg_stations(self):
        """Test fallback to leg.stations when no sequence or clusters."""
        leg = MagicMock()
        leg.sequence = None  # No sequence
        leg.clusters = None  # No clusters
        leg.stations = ["FALLBACK001", "FALLBACK002"]

        result = _extract_activities_from_leg(leg)

        # Should return leg stations as fallback
        assert result == ["FALLBACK001", "FALLBACK002"]

    def test_empty_leg_returns_empty_list(self):
        """Test that leg with no activities returns empty list."""
        leg = MagicMock()
        leg.sequence = None
        leg.clusters = None
        leg.stations = None

        result = _extract_activities_from_leg(leg)

        assert result == []

    def test_sequence_with_object_names(self):
        """Test sequence containing objects with name attributes."""
        station_obj1 = MagicMock()
        station_obj1.name = "OBJ_STN001"

        station_obj2 = MagicMock()
        station_obj2.name = "OBJ_STN002"

        leg = MagicMock()
        leg.sequence = ["STR_STN001", station_obj1, "STR_STN002", station_obj2]
        leg.clusters = []
        leg.stations = []

        result = _extract_activities_from_leg(leg)

        # Should extract names from objects
        assert result == ["STR_STN001", "OBJ_STN001", "STR_STN002", "OBJ_STN002"]

    def test_cluster_sequence_with_mixed_types(self):
        """Test cluster sequence containing mixed strings and objects."""
        station_obj = MagicMock()
        station_obj.name = "CLUSTER_OBJ_STN"

        cluster = MagicMock()
        cluster.sequence = ["CLUSTER_STR_STN", station_obj]
        cluster.stations = ["BACKUP"]

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [cluster]
        leg.stations = ["FALLBACK"]

        result = _extract_activities_from_leg(leg)

        assert result == ["CLUSTER_STR_STN", "CLUSTER_OBJ_STN"]

    def test_cluster_stations_with_mixed_types(self):
        """Test cluster stations containing mixed strings and objects."""
        station_obj = MagicMock()
        station_obj.name = "CLUSTER_STATION_OBJ"

        cluster = MagicMock()
        cluster.sequence = None  # No sequence
        cluster.stations = ["CLUSTER_STR_STATION", station_obj]

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [cluster]
        leg.stations = ["FALLBACK"]

        result = _extract_activities_from_leg(leg)

        assert result == ["CLUSTER_STR_STATION", "CLUSTER_STATION_OBJ"]

    def test_empty_sequence_skips_to_clusters(self):
        """Test that empty sequence list skips to clusters."""
        leg = MagicMock()
        leg.sequence = []  # Empty list
        leg.clusters = [MagicMock(sequence=["CLUSTER_STN001"])]
        leg.stations = ["FALLBACK"]

        result = _extract_activities_from_leg(leg)

        # Should skip empty sequence and use clusters
        assert result == ["CLUSTER_STN001"]

    def test_empty_clusters_list_skips_to_stations(self):
        """Test that empty clusters list skips to leg stations."""
        leg = MagicMock()
        leg.sequence = None
        leg.clusters = []  # Empty list
        leg.stations = ["STATION001", "STATION002"]

        result = _extract_activities_from_leg(leg)

        # Should skip empty clusters and use leg stations
        assert result == ["STATION001", "STATION002"]

    def test_cluster_with_empty_sequence_and_stations(self):
        """Test cluster with both empty sequence and stations."""
        cluster = MagicMock()
        cluster.sequence = []  # Empty
        cluster.stations = []  # Empty

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [cluster]
        leg.stations = ["FALLBACK001"]

        result = _extract_activities_from_leg(leg)

        # Should skip to leg stations since cluster contributes nothing
        assert result == ["FALLBACK001"]

    def test_mixed_empty_and_valid_clusters(self):
        """Test handling of mix of empty and valid clusters."""
        empty_cluster = MagicMock()
        empty_cluster.sequence = None
        empty_cluster.stations = None

        valid_cluster = MagicMock()
        valid_cluster.sequence = ["VALID_STN001"]
        valid_cluster.stations = ["BACKUP"]

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [empty_cluster, valid_cluster]
        leg.stations = ["FALLBACK"]

        result = _extract_activities_from_leg(leg)

        # Should only get stations from valid cluster
        assert result == ["VALID_STN001"]

    def test_hasattr_safety_for_missing_attributes(self):
        """Test that missing attributes are handled gracefully."""
        # Create leg without some attributes
        leg = MagicMock()

        # Remove attributes to test hasattr checks
        if hasattr(leg, "sequence"):
            delattr(leg, "sequence")
        if hasattr(leg, "clusters"):
            delattr(leg, "clusters")
        leg.stations = ["ONLY_STATIONS"]

        result = _extract_activities_from_leg(leg)

        # Should fall back to stations
        assert result == ["ONLY_STATIONS"]


class TestClusterProcessingEdgeCases:
    """Test edge cases in cluster processing."""

    def test_none_values_in_sequences(self):
        """Test handling of None values in sequences."""
        leg = MagicMock()

        # Create sequence with None (shouldn't happen but test robustness)
        leg.sequence = ["VALID_STN", None, "ANOTHER_STN"]
        leg.clusters = []
        leg.stations = []

        # This tests the isinstance(item, str) check
        # None items should be skipped (they don't match str or have .name)
        result = _extract_activities_from_leg(leg)

        assert result == ["VALID_STN", "ANOTHER_STN"]

    def test_objects_without_name_attribute(self):
        """Test objects in sequence without name attribute."""
        bad_obj = MagicMock()
        # Remove name attribute
        if hasattr(bad_obj, "name"):
            delattr(bad_obj, "name")

        leg = MagicMock()
        leg.sequence = ["VALID_STN", bad_obj, "ANOTHER_STN"]
        leg.clusters = []
        leg.stations = []

        result = _extract_activities_from_leg(leg)

        # Should skip object without name attribute
        assert result == ["VALID_STN", "ANOTHER_STN"]

    def test_cluster_sequence_priority_over_stations(self):
        """Test that within a cluster, sequence takes priority over stations."""
        cluster = MagicMock()
        cluster.sequence = ["CLUSTER_SEQ_STN"]  # This should be used
        cluster.stations = ["CLUSTER_STAT_STN"]  # This should be ignored

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [cluster]
        leg.stations = ["LEG_STN"]

        result = _extract_activities_from_leg(leg)

        # Should use cluster sequence, not cluster stations
        assert result == ["CLUSTER_SEQ_STN"]

    def test_complex_nested_scenario(self):
        """Test complex scenario with multiple nested structures."""
        # Station object
        stn_obj = MagicMock()
        stn_obj.name = "COMPLEX_OBJ_STN"

        # Cluster 1: has sequence
        cluster1 = MagicMock()
        cluster1.sequence = ["C1_SEQ_STN001", stn_obj]
        cluster1.stations = ["C1_IGNORED_STN"]  # Should be ignored

        # Cluster 2: no sequence, has stations
        cluster2 = MagicMock()
        cluster2.sequence = []  # Empty sequence
        cluster2.stations = ["C2_STAT_STN001", "C2_STAT_STN002"]

        # Cluster 3: empty
        cluster3 = MagicMock()
        cluster3.sequence = None
        cluster3.stations = None

        # Leg with no sequence, using clusters
        leg = MagicMock()
        leg.sequence = None
        leg.clusters = [cluster1, cluster2, cluster3]
        leg.stations = ["LEG_FALLBACK"]

        result = _extract_activities_from_leg(leg)

        expected = [
            "C1_SEQ_STN001",
            "COMPLEX_OBJ_STN",  # From cluster1.sequence
            "C2_STAT_STN001",
            "C2_STAT_STN002",  # From cluster2.stations
            # cluster3 contributes nothing
        ]
        assert result == expected

    def test_leg_stations_with_mixed_types(self):
        """Test leg stations fallback with mixed types."""
        station_obj = MagicMock()
        station_obj.name = "LEG_STATION_OBJ"

        leg = MagicMock()
        leg.sequence = None
        leg.clusters = None
        leg.stations = ["LEG_STR_STATION", station_obj, "ANOTHER_STR_STATION"]

        result = _extract_activities_from_leg(leg)

        assert result == ["LEG_STR_STATION", "LEG_STATION_OBJ", "ANOTHER_STR_STATION"]
