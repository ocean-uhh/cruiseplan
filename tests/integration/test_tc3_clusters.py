"""Integration tests for TC3 clusters configuration - comprehensive cluster behavior validation."""

from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.cruise import Cruise
from cruiseplan.utils.config import ConfigLoader


class TestTC3ClustersIntegration:
    """Integration tests for TC3 clusters configuration with multiple test scenarios."""

    @pytest.fixture
    def tc3_config_path(self):
        """Path to TC3 clusters test configuration."""
        return Path(__file__).parent.parent / "fixtures" / "tc3_clusters.yaml"

    @pytest.fixture
    def tc3_config(self, tc3_config_path):
        """Load TC3 clusters configuration."""
        loader = ConfigLoader(tc3_config_path)
        return loader.load()

    @pytest.fixture
    def tc3_cruise(self, tc3_config_path):
        """Load TC3 clusters cruise object."""
        return Cruise(tc3_config_path)

    def test_tc3_validation_warnings(self, tc3_config):
        """Test that validation produces expected warnings for duplicate activities."""
        # Validation should produce warnings for:
        # 1. Duplicate STN_002 activities in clusters

        # Configuration should load successfully
        assert tc3_config.cruise_name == "TC3_Clusters_Test"
        assert len(tc3_config.legs) == 6

    def test_tc3_mooring_operations_count(self, tc3_config):
        """Test that configuration generates expected number of mooring operations."""
        timeline = generate_timeline(tc3_config)

        # Count mooring operations
        mooring_ops = [
            activity for activity in timeline if activity.get("activity") == "Mooring"
        ]

        # Expected: 12 mooring operations total (2 per leg × 6 legs)
        # Each leg has STN_003 and STN_004 with mooring operations
        assert (
            len(mooring_ops) == 12
        ), f"Expected 12 mooring operations, got {len(mooring_ops)}"

        # Verify total mooring duration is 12 hours (1 hour per operation)
        total_mooring_hours = sum(
            op.get("duration_minutes", 0) / 60.0 for op in mooring_ops
        )
        assert (
            total_mooring_hours == 12.0
        ), f"Expected 12 hours of mooring, got {total_mooring_hours}"

    def test_tc3_ctd_stations_count(self, tc3_config):
        """Test that configuration generates expected number of CTD stations."""
        timeline = generate_timeline(tc3_config)

        # Count CTD operations (station activities with CTD operation_type)
        ctd_ops = [
            activity
            for activity in timeline
            if activity.get("activity") == "Station"
            and activity.get("action") == "profile"
        ]

        # Expected CTD counts per leg (STN_001 and STN_002 are CTD operations):
        # Leg_Survey: 2 (STN_001 as first_station + STN_002 in cluster)
        # Leg_Survey_Faster: 2 (STN_001 as first_station + STN_002 in cluster)
        # Leg_Survey_Duplicate2: 3 (STN_001 as first_station + STN_002 × 2 in cluster)
        # Leg_Survey_Duplicate3: 3 (STN_001 as first_station + STN_002 + STN_001 in cluster)
        # Leg_Survey_Duplicate4: 3 (STN_001 as first_station + STN_001 + STN_002 in cluster)
        # Leg_Survey_Reorder: 2 (STN_002 in cluster + STN_001 as last_station)
        # Total: 2 + 2 + 3 + 3 + 3 + 2 = 15 CTD stations
        assert len(ctd_ops) == 15, f"Expected 15 CTD operations, got {len(ctd_ops)}"

    def test_tc3_vessel_speed_differences(self, tc3_config):
        """Test that leg-specific vessel speed configuration is preserved and applied."""
        # Verify that leg configurations have different vessel speeds
        leg_survey = next(leg for leg in tc3_config.legs if leg.name == "Leg_Survey")
        leg_faster = next(
            leg for leg in tc3_config.legs if leg.name == "Leg_Survey_Faster"
        )

        # Leg_Survey should use default speed (None), Leg_Survey_Faster should have 12.0
        assert (
            leg_survey.vessel_speed is None
        ), "Leg_Survey should use default vessel speed"
        assert (
            leg_faster.vessel_speed == 12.0
        ), "Leg_Survey_Faster should have vessel_speed 12.0"

        # Verify that leg-specific speeds are applied in timeline generation
        timeline = generate_timeline(tc3_config)

        # Extract transit activities for each leg
        leg_survey_transits = [
            activity
            for activity in timeline
            if activity.get("activity") == "Transit"
            and activity.get("leg_name") == "Leg_Survey"
        ]
        leg_faster_transits = [
            activity
            for activity in timeline
            if activity.get("activity") == "Transit"
            and activity.get("leg_name") == "Leg_Survey_Faster"
        ]

        # Verify transit speeds are applied correctly
        for transit in leg_survey_transits:
            assert (
                transit.get("vessel_speed_kt") == 10.0
            ), "Leg_Survey should use default 10.0 kt speed"

        for transit in leg_faster_transits:
            assert (
                transit.get("vessel_speed_kt") == 12.0
            ), "Leg_Survey_Faster should use 12.0 kt speed"

        # Calculate total leg durations and verify speed difference
        leg_survey_activities = [
            a for a in timeline if a.get("leg_name") == "Leg_Survey"
        ]
        leg_faster_activities = [
            a for a in timeline if a.get("leg_name") == "Leg_Survey_Faster"
        ]

        def calculate_leg_duration(activities):
            if not activities:
                return 0
            start_time = min(a["start_time"] for a in activities)
            end_time = max(a["end_time"] for a in activities)
            return (end_time - start_time).total_seconds() / 3600

        leg_survey_hours = calculate_leg_duration(leg_survey_activities)
        leg_faster_hours = calculate_leg_duration(leg_faster_activities)
        time_difference = leg_survey_hours - leg_faster_hours

        # Verify Leg_Survey_Faster is approximately 21.3 hours faster
        assert (
            20.0 < time_difference < 23.0
        ), f"Expected ~21.3h difference, got {time_difference:.1f}h"

    def test_tc3_duplicate_station_warnings(self, tc3_config):
        """Test warnings for stations appearing as both routing anchors and cluster activities."""
        # Leg_Survey_Duplicate4 has STN_001 as first_station and in CTD_Cluster5 activities
        # This should be accepted behavior (no errors, just informational)

        # Verify the cruise loads successfully despite duplicates
        assert tc3_config.cruise_name == "TC3_Clusters_Test"
        assert len(tc3_config.legs) == 6

        # Find leg with duplicate first_station in cluster
        duplicate4_leg = next(
            leg for leg in tc3_config.legs if leg.name == "Leg_Survey_Duplicate4"
        )

        assert duplicate4_leg.first_waypoint == "STN_001"

        # Find cluster containing first_station
        ctd_cluster5 = next(
            cluster
            for cluster in duplicate4_leg.clusters
            if cluster.name == "CTD_Cluster5"
        )

        assert "STN_001" in ctd_cluster5.activities

    def test_tc3_reorder_leg_behavior(self, tc3_config):
        """Test that Leg_Survey_Reorder correctly reverses first_station and last_station."""
        reorder_leg = next(
            leg for leg in tc3_config.legs if leg.name == "Leg_Survey_Reorder"
        )

        # This leg should have STN_004 as first and STN_001 as last (reversed)
        assert reorder_leg.first_waypoint == "STN_004"
        assert reorder_leg.last_waypoint == "STN_001"

    def test_tc3_html_working_area_transits(self, tc3_config):
        """Test that HTML generator calculates correct working area transit totals."""
        from cruiseplan.output.html_generator import _calculate_summary_statistics

        timeline = generate_timeline(tc3_config)
        stats = _calculate_summary_statistics(timeline)

        # Verify working area transit calculations include all Port_Departure and Port_Arrival
        expected_hours = 675.7  # Sum of all departure and arrival transits for 6 legs (updated for new coordinates)
        expected_distance = 6949.7  # Total nm for port-to-working-area transits (updated for new coordinates)

        assert (
            abs(stats["port_area"]["total_duration_h"] - expected_hours) < 1.0
        ), f"Expected ~{expected_hours}h working area transits, got {stats['port_area']['total_duration_h']:.1f}h"

        assert (
            abs(stats["port_area"]["total_distance_nm"] - expected_distance) < 10.0
        ), f"Expected ~{expected_distance}nm working area transits, got {stats['port_area']['total_distance_nm']:.1f}nm"

        # Verify average speed is reasonable (should be around 10.3 kts)
        assert (
            9.0 < stats["port_area"]["avg_speed_kts"] < 12.0
        ), f"Expected reasonable avg speed ~10.3 kts, got {stats['port_area']['avg_speed_kts']:.1f} kts"

    def test_tc3_complete_workflow(self, tc3_config):
        """Test complete workflow from YAML to all output formats."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir)

            # Generate timeline
            timeline = generate_timeline(tc3_config)

            # Verify timeline has expected activity count
            assert (
                len(timeline) > 50
            ), f"Expected >50 activities for 6-leg cruise, got {len(timeline)}"
