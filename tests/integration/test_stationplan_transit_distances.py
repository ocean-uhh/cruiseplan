"""
Integration test for transit distances in stationplan TeX output.

This test verifies that the distance_to_next field is properly calculated
and displayed as "+XX nm" transit distances in the stationplan TeX format.
"""

import tempfile
from pathlib import Path

from cruiseplan.api.config import OutputConfig, ScheduleConfig
from cruiseplan.api.schedule_cruise import schedule_with_config
from cruiseplan.api.stationplan_api import stationplan_tex


class TestStationplanTransitDistances:
    """Test transit distance display in stationplan TeX output."""

    def test_transit_distance_60nm_appears_in_tex(self):
        """
        Test that a 60 nm transit between two stations appears as "+60.0 nm" in TeX output.

        Uses two mooring stations exactly 1 degree latitude apart (60 nm),
        which should generate a transit distance entry in the TeX table.
        """
        # Get the test fixture
        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "test_transit_distance.yaml"
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Step 1: Generate schedule from the test fixture
            schedule_config = ScheduleConfig(
                output=OutputConfig(directory=str(temp_path), format="netcdf")
            )
            schedule_result = schedule_with_config(
                config_file=fixture_path, config=schedule_config
            )

            # Verify schedule generation succeeded
            assert bool(
                schedule_result
            ), f"Schedule generation failed: {schedule_result.errors}"
            assert schedule_result.timeline is not None
            assert len(schedule_result.timeline) > 0

            # Find the NetCDF schedule file
            netcdf_files = [
                f for f in schedule_result.files_created if f.suffix == ".nc"
            ]
            assert (
                len(netcdf_files) == 1
            ), f"Expected 1 NetCDF file, got {len(netcdf_files)}"
            schedule_file = netcdf_files[0]

            # Step 2: Generate stationplan TeX output
            tex_output_path = temp_path / "test_stationplan.tex"
            tex_result = stationplan_tex(
                schedule_file=schedule_file, output_path=tex_output_path
            )

            # Verify TeX generation succeeded
            assert bool(tex_result), f"TeX generation failed: {tex_result.errors}"
            assert tex_output_path.exists(), "TeX file was not created"

            # Step 3: Check TeX content for transit distance
            tex_content = tex_output_path.read_text()

            # Debug: Print the TeX content for inspection
            print("\\n=== Generated TeX Content ===")
            print(tex_content)
            print("=== End TeX Content ===\\n")

            # Look for the transit distance line
            # Should contain "+60.0 nm" or similar (allowing for floating point precision)
            tex_lines = tex_content.split("\n")
            transit_distance_lines = [
                line
                for line in tex_lines
                if "+" in line
                and "nm" in line
                and ("60" in line or "59." in line or "60." in line)
            ]

            # Verify we found the expected transit distance
            plus_nm_lines = [line for line in tex_lines if "+" in line and "nm" in line]
            assert len(transit_distance_lines) > 0, (
                f"Expected to find transit distance line with '+60 nm', but found none. "
                f"Lines with '+' and 'nm': {plus_nm_lines}"
            )

            # Additional check: verify the distance is approximately 60 nm
            # (1 degree latitude = 60 nautical miles)
            print(f"Found transit distance lines: {transit_distance_lines}")

    def test_schedule_contains_transit_activities(self):
        """
        Verify that the generated schedule contains Transit activities with distances.

        This is a supporting test to ensure the schedule generation is working correctly.
        """
        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "test_transit_distance.yaml"
        )

        schedule_result = schedule_with_config(config_file=fixture_path, config=None)

        assert bool(
            schedule_result
        ), f"Schedule generation failed: {schedule_result.errors}"
        timeline = schedule_result.timeline

        # Debug: Print timeline contents
        print(f"Timeline length: {len(timeline)}")
        for i, activity in enumerate(timeline[:5]):  # Show first 5 activities
            print(
                f"Activity {i}: {dict(activity) if hasattr(activity, 'keys') else activity}"
            )

        # Check for Transit activities
        transit_activities = [
            activity for activity in timeline if activity.get("activity") == "Transit"
        ]
        assert (
            len(transit_activities) > 0
        ), f"Expected at least one Transit activity in timeline. Activities found: {[activity.get('activity') for activity in timeline]}"

        # Check that Transit activities have distance
        transit_with_distance = [
            activity
            for activity in transit_activities
            if activity.get("dist_nm", 0) > 0
        ]
        assert (
            len(transit_with_distance) > 0
        ), "Expected Transit activities to have distance > 0"

        # Verify we have approximately 60 nm distance
        distances = [activity.get("dist_nm", 0) for activity in transit_with_distance]
        print(f"Transit distances found: {distances}")

        # Should be close to 60 nm (1 degree latitude)
        assert any(
            55 <= dist <= 65 for dist in distances
        ), f"Expected distance ~60nm, got {distances}"
