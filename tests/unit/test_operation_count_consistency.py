"""
Test that operation counting is consistent between cruise-level and leg-level totals.

This test ensures that the sum of scientific operations across all legs
equals the total scientific operations at the cruise level.
"""

from pathlib import Path

import pytest

from cruiseplan.calculators import scheduler
from cruiseplan.core.cruise import CruiseInstance


class TestOperationCountConsistency:
    """Test operation count consistency between cruise and leg levels."""

    @pytest.fixture
    def tc1_cruise(self):
        """Load TC1 single leg test cruise."""
        yaml_file = Path("tests_output/fixtures/TC1_Single_Test_enriched.yaml")
        if yaml_file.exists():
            return CruiseInstance(yaml_file)
        pytest.skip(f"Test file not found: {yaml_file}")

    @pytest.fixture
    def tc2_cruise(self):
        """Load TC2 two legs test cruise."""
        yaml_file = Path("tests_output/fixtures/TC2_TwoLegs_Test_enriched.yaml")
        if yaml_file.exists():
            return CruiseInstance(yaml_file)
        pytest.skip(f"Test file not found: {yaml_file}")

    def _test_operation_consistency(self, cruise):
        """Helper method to test operation count consistency for any cruise."""
        timeline = scheduler.generate_timeline(cruise)
        stats = scheduler.calculate_timeline_statistics(timeline)

        # Calculate cruise-level total from individual operation types
        cruise_total = (
            stats["stations"]["count"]
            + stats["moorings"]["count"]
            + stats["surveys"]["count"]
            + stats["areas"]["count"]
        )

        # Calculate sum of leg-level totals
        leg_total_sum = sum(
            leg_stat["total_scientific"] for leg_stat in stats["leg_stats"].values()
        )

        # Calculate total from unified method
        unified_total = stats["total_scientific"]

        assert (
            cruise_total == leg_total_sum
        ), f"Cruise total ({cruise_total}) != sum of leg totals ({leg_total_sum})"

        assert (
            unified_total == leg_total_sum
        ), f"Unified total ({unified_total}) != sum of leg totals ({leg_total_sum})"

        assert (
            cruise_total == unified_total
        ), f"Cruise total ({cruise_total}) != unified total ({unified_total})"

        return cruise_total, leg_total_sum, unified_total

    def test_tc1_operation_consistency(self, tc1_cruise):
        """Test that TC1 single leg has consistent operation counts."""
        cruise_total, _leg_total_sum, _unified_total = self._test_operation_consistency(
            tc1_cruise
        )

        # TC1 should have 1 scientific operation (1 CTD station)
        assert cruise_total == 1, f"Expected 1 operation in TC1, got {cruise_total}"

    def test_tc2_operation_consistency(self, tc2_cruise):
        """Test that TC2 two legs has consistent operation counts."""
        cruise_total, _leg_total_sum, _unified_total = self._test_operation_consistency(
            tc2_cruise
        )

        # TC2 should have 2 scientific operations (1 CTD station + 1 mooring)
        assert cruise_total == 2, f"Expected 2 operations in TC2, got {cruise_total}"

    def test_operation_count_logic(self):
        """Test the operation counting logic directly."""
        # Create a mock timeline with various operation types
        mock_timeline = [
            {
                "operation_class": "PointOperation",
                "op_type": "station",
                "leg_name": "Leg1",
            },
            {
                "operation_class": "PointOperation",
                "op_type": "CTD",
                "leg_name": "Leg1",
            },
            {
                "operation_class": "PointOperation",
                "op_type": "mooring",
                "leg_name": "Leg2",
            },
            {
                "operation_class": "PointOperation",
                "op_type": "port",
                "leg_name": "Leg1",
            },
            {
                "operation_class": "LineOperation",
                "op_type": "survey",
                "leg_name": "Leg2",
            },
            {
                "operation_class": "AreaOperation",
                "op_type": "area",
                "leg_name": "Leg1",
            },
            {
                "operation_class": "NavigationalTransit",
                "op_type": "transit",
                "leg_name": "Leg1",
            },
        ]

        # Calculate leg stats using the same logic as scheduler
        leg_stats = {}
        for activity in mock_timeline:
            leg_name = activity.get("leg_name", "Unknown")
            if leg_name not in leg_stats:
                leg_stats[leg_name] = {
                    "stations": 0,
                    "moorings": 0,
                    "surveys": 0,
                    "areas": 0,
                    "total_scientific": 0,
                    "ports": 0,
                    "transits": 0,
                    "total_activities": 0,
                }

            leg_stats[leg_name]["total_activities"] += 1

            operation_class = activity.get("operation_class", "")
            op_type = activity.get("op_type", "")

            # Use the same counting logic as scheduler.py
            if op_type == "port":
                leg_stats[leg_name]["ports"] += 1
            elif operation_class == "NavigationalTransit":
                leg_stats[leg_name]["transits"] += 1
            else:
                # This is a scientific operation - count it
                leg_stats[leg_name]["total_scientific"] += 1

                # Also increment specific counters for detailed stats
                if operation_class == "PointOperation":
                    if op_type in {"station", "CTD"}:
                        leg_stats[leg_name]["stations"] += 1
                    elif op_type == "mooring":
                        leg_stats[leg_name]["moorings"] += 1
                elif operation_class == "LineOperation":
                    leg_stats[leg_name]["surveys"] += 1
                elif operation_class == "AreaOperation":
                    leg_stats[leg_name]["areas"] += 1

        # Verify counts
        assert leg_stats["Leg1"]["total_scientific"] == 3  # station + CTD + area
        assert leg_stats["Leg2"]["total_scientific"] == 2  # mooring + survey
        assert leg_stats["Leg1"]["ports"] == 1
        assert leg_stats["Leg1"]["transits"] == 1

        total_scientific = sum(
            leg_stats[leg_name]["total_scientific"] for leg_name in leg_stats
        )
        assert total_scientific == 5  # 3 + 2 = 5 scientific operations total
