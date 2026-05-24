"""
Test ActivityRecord roundtrip preservation in NetCDF files.

This test verifies that all ActivityRecord fields are properly preserved
when writing to NetCDF and reading back, ensuring complete data fidelity.
Uses real cruise configuration and scheduling to test the complete workflow.
"""

import tempfile
from datetime import timedelta
from pathlib import Path

import numpy as np

from cruiseplan.api.schedule_cruise import schedule
from cruiseplan.forecast.reader import netcdf_to_activity_records, read_schedule
from cruiseplan.timeline.scheduler import ActivityRecord


def create_comprehensive_cruise_yaml():
    """Create a comprehensive cruise YAML file for testing."""
    yaml_content = """
cruise_name: "ROUNDTRIP_TEST_2026"
vessel_name: "R/V TestShip"
start_date: "2026-06-01T08:00:00"

start_port:
  name: "TestPort"
  latitude: 54.0
  longitude: -2.0

end_port:  
  name: "TestPort"
  latitude: 54.0
  longitude: -2.0

# Comprehensive stations with all ActivityRecord fields
points:
  - name: "CTD_001"
    latitude: 54.5
    longitude: -2.5
    operation_type: "CTD"
    action: "profile"
    operation_depth: 500.0
    water_depth: 1200.0
    comment: "Deep CTD cast for water mass analysis"
    
  - name: "MOOR_001"  
    latitude: 55.0
    longitude: -3.0
    operation_type: "mooring"
    action: "deployment"
    operation_depth: 1000.0
    water_depth: 2500.0
    comment: "Deploy deep ocean mooring"

legs:
  - name: "leg1"
    departure_port: "TestPort"
    arrival_port: "TestPort"
    clusters:
      - name: "cluster1"
        activities:
          - "CTD_001"
          - "MOOR_001"
"""
    return yaml_content


def test_activity_record_netcdf_roundtrip():
    """Test complete ActivityRecord roundtrip using real cruise schedule generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)

        # Create real cruise YAML file
        cruise_yaml_path = tmp_dir_path / "test_cruise.yaml"
        cruise_yaml_path.write_text(create_comprehensive_cruise_yaml())

        # Generate schedule using the real cruiseplan API
        result = schedule(
            config_file=cruise_yaml_path,
            output_dir=str(tmp_dir_path),
            format="netcdf",  # Generate NetCDF file
            verbose=False,
        )

        # Find the generated NetCDF schedule file
        netcdf_files = [
            f
            for f in result.files_created
            if f.suffix == ".nc" and "schedule" in f.name
        ]
        assert len(netcdf_files) == 1, (
            f"Expected 1 schedule NetCDF file, got {len(netcdf_files)}"
        )
        netcdf_path = netcdf_files[0]

        print(f"Generated NetCDF file: {netcdf_path}")

        # Read back the original timeline from the result object
        original_timeline = result.timeline
        print(f"Original timeline has {len(original_timeline)} activities")

        # Read back from NetCDF using our reader
        schedule_dataset = read_schedule(netcdf_path)
        try:
            recovered_records = netcdf_to_activity_records(schedule_dataset)
        finally:
            # Ensure NetCDF file is properly closed on Windows
            schedule_dataset.close()

        print(f"Recovered {len(recovered_records)} ActivityRecord objects from NetCDF")

        # Verify we have the same number of records
        assert len(recovered_records) == len(original_timeline), (
            f"Expected {len(original_timeline)} records, got {len(recovered_records)}"
        )

        # Create reference ActivityRecord objects from the original timeline
        original_records = [
            ActivityRecord(activity_data) for activity_data in original_timeline
        ]

        # Debug: print activity types to understand the data
        print("\nActivity types in timeline:")
        for i, activity in enumerate(original_timeline):
            print(
                f"  {i}: {activity['label']} -> activity='{activity['activity']}', category='{activity.get('category', 'N/A')}'"
            )

        # Verify each record's fields with comprehensive comparison
        for i, (orig, recovered) in enumerate(zip(original_records, recovered_records)):
            print(f"\nComparing record {i}: {orig.label}")
            print(
                f"  Original: activity='{orig.activity}', recovered: activity='{recovered.activity}'"
            )

            # Activity should be preserved exactly now
            assert recovered.activity == orig.activity, (
                f"Activity mismatch: {recovered.activity} != {orig.activity}"
            )
            assert recovered.label == orig.label, (
                f"Label mismatch: {recovered.label} != {orig.label}"
            )
            assert recovered.leg_name == orig.leg_name, (
                f"Leg name mismatch: {recovered.leg_name} != {orig.leg_name}"
            )

            # Operation type and class should be preserved exactly now
            print(f"op_type: orig='{orig.op_type}', recovered='{recovered.op_type}'")
            print(
                f"operation_class: orig='{orig.operation_class}', recovered='{recovered.operation_class}'"
            )

            assert recovered.op_type == orig.op_type, (
                f"Op type mismatch: {recovered.op_type} != {orig.op_type}"
            )
            assert recovered.operation_class == orig.operation_class, (
                f"Operation class mismatch: {recovered.operation_class} != {orig.operation_class}"
            )

            # Coordinate fields (with small floating point tolerance)
            assert abs(recovered.entry_lat - orig.entry_lat) < 1e-6, (
                f"Entry lat mismatch: {recovered.entry_lat} != {orig.entry_lat}"
            )
            assert abs(recovered.entry_lon - orig.entry_lon) < 1e-6, (
                f"Entry lon mismatch: {recovered.entry_lon} != {orig.entry_lon}"
            )
            assert abs(recovered.exit_lat - orig.exit_lat) < 1e-6, (
                f"Exit lat mismatch: {recovered.exit_lat} != {orig.exit_lat}"
            )
            assert abs(recovered.exit_lon - orig.exit_lon) < 1e-6, (
                f"Exit lon mismatch: {recovered.exit_lon} != {orig.exit_lon}"
            )

            # Time fields (with small tolerance for datetime conversion)
            time_tolerance = timedelta(seconds=1)
            assert abs(recovered.start_time - orig.start_time) < time_tolerance, (
                f"Start time mismatch: {recovered.start_time} != {orig.start_time}"
            )
            assert abs(recovered.end_time - orig.end_time) < time_tolerance, (
                f"End time mismatch: {recovered.end_time} != {orig.end_time}"
            )

            # Numeric fields
            assert abs(recovered.duration_minutes - orig.duration_minutes) < 0.1, (
                f"Duration mismatch: {recovered.duration_minutes} != {orig.duration_minutes}"
            )
            assert abs(recovered.dist_nm - orig.dist_nm) < 0.1, (
                f"Distance mismatch: {recovered.dist_nm} != {orig.dist_nm}"
            )
            assert abs(recovered.vessel_speed_kt - orig.vessel_speed_kt) < 0.1, (
                f"Speed mismatch: {recovered.vessel_speed_kt} != {orig.vessel_speed_kt}"
            )

            # Optional fields (handle None values)
            if orig.action is not None:
                print(f"action: orig='{orig.action}', recovered='{recovered.action}'")
                # Actions should be preserved exactly now
                assert recovered.action == orig.action, (
                    f"Action mismatch: {recovered.action} != {orig.action}"
                )

            if orig.operation_depth is not None:
                assert recovered.operation_depth is not None, (
                    "Operation depth should not be None"
                )
                assert abs(recovered.operation_depth - orig.operation_depth) < 0.1, (
                    f"Operation depth mismatch: {recovered.operation_depth} != {orig.operation_depth}"
                )
            else:
                assert recovered.operation_depth is None or np.isnan(
                    recovered.operation_depth
                ), "Operation depth should be None or NaN"

            if orig.water_depth is not None:
                assert recovered.water_depth is not None, (
                    "Water depth should not be None"
                )
                assert abs(recovered.water_depth - orig.water_depth) < 0.1, (
                    f"Water depth mismatch: {recovered.water_depth} != {orig.water_depth}"
                )
            else:
                assert recovered.water_depth is None or np.isnan(
                    recovered.water_depth
                ), "Water depth should be None or NaN"

        print(
            f"\n✅ Successfully verified complete roundtrip preservation of {len(recovered_records)} ActivityRecord objects"
        )
        print(
            "✅ All ActivityRecord fields properly preserved through real cruise schedule generation!"
        )


def test_activity_record_required_fields_present():
    """Test that all required ActivityRecord fields are present in NetCDF using real schedule generation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)

        # Create real cruise YAML file
        cruise_yaml_path = tmp_dir_path / "test_cruise.yaml"
        cruise_yaml_path.write_text(create_comprehensive_cruise_yaml())

        # Generate schedule using the real cruiseplan API
        result = schedule(
            config_file=cruise_yaml_path,
            output_dir=str(tmp_dir_path),
            format="netcdf",  # Generate NetCDF file
            verbose=False,
        )

        # Find the generated NetCDF schedule file
        netcdf_files = [
            f
            for f in result.files_created
            if f.suffix == ".nc" and "schedule" in f.name
        ]
        assert len(netcdf_files) == 1, (
            f"Expected 1 schedule NetCDF file, got {len(netcdf_files)}"
        )
        netcdf_path = netcdf_files[0]

        # Read back and check variables
        schedule_dataset = read_schedule(netcdf_path)
        try:
            # List of all ActivityRecord fields that should be preserved
            expected_variables = [
                "time",  # start_time
                "latitude",  # entry_lat
                "longitude",  # entry_lon
                "exit_latitude",  # exit_lat
                "exit_longitude",  # exit_lon
                "end_time",  # end_time
                "duration",  # duration_minutes (converted to hours)
                "dist_nm",  # dist_nm
                "vessel_speed",  # vessel_speed_kt
                "leg_assignment",  # leg_name
                "type",  # op_type
                "operation_class",  # operation_class
                "name",  # label
                "activity",  # activity
                "action",  # action
                "operation_depth",  # operation_depth
                "water_depth",  # water_depth (or waterdepth legacy)
            ]

            missing_vars = []
            for var in expected_variables:
                if var not in schedule_dataset.variables:
                    # Check for legacy names
                    if (
                        var == "water_depth"
                        and "waterdepth" in schedule_dataset.variables
                    ):
                        continue
                    missing_vars.append(var)

            assert not missing_vars, (
                f"Missing ActivityRecord variables in NetCDF: {missing_vars}"
            )

            print(
                f"✅ All {len(expected_variables)} expected ActivityRecord variables present in NetCDF"
            )
            print(
                f"✅ Variables found: {sorted(list(schedule_dataset.variables.keys()))}"
            )
        finally:
            # Ensure NetCDF file is properly closed on Windows
            schedule_dataset.close()


if __name__ == "__main__":
    test_activity_record_netcdf_roundtrip()
    test_activity_record_required_fields_present()
    print("All ActivityRecord roundtrip tests passed!")
