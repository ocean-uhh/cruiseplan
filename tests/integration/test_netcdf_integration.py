"""
Integration tests for NetCDF generator with real YAML fixture files.
"""

import shutil
from pathlib import Path

import netCDF4 as nc
import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.output.netcdf_generator import generate_netcdf_outputs
from cruiseplan.utils.config import ConfigLoader

# Available test fixtures
TEST_FIXTURES = [
    "tests/fixtures/cruise_simple.yaml",
    "tests/fixtures/cruise_mixed_ops.yaml",
    "tests/fixtures/cruise_multi_leg.yaml",
]

# NetCDF output directory
NETCDF_OUTPUT_DIR = Path("tests_output/netcdf")


def clean_netcdf_directory(output_path: Path):
    """Clean and recreate NetCDF output directory."""
    if output_path.exists():
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)


class TestNetCDFIntegration:
    """Integration tests for NetCDF generator with actual YAML configurations."""

    @pytest.mark.parametrize("yaml_path", TEST_FIXTURES)
    def test_netcdf_generation_all_fixtures(self, yaml_path):
        """Test NetCDF generation with all available YAML fixtures."""
        # Load configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        # Generate timeline
        timeline = generate_timeline(config)
        assert len(timeline) > 0, f"Timeline should not be empty for {yaml_path}"

        # Generate NetCDF outputs to dedicated directory
        fixture_name = Path(yaml_path).stem
        output_path = NETCDF_OUTPUT_DIR / f"all_fixtures/{fixture_name}"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        # Verify files were created
        assert len(netcdf_files) == 4, f"Should create 4 NetCDF files for {yaml_path}"

        # Verify all files exist and have content
        for netcdf_file in netcdf_files:
            assert netcdf_file.exists(), f"NetCDF file should exist: {netcdf_file}"
            assert (
                netcdf_file.stat().st_size > 0
            ), f"NetCDF file should not be empty: {netcdf_file}"

            # Quick CF compliance check
            with nc.Dataset(netcdf_file, "r") as ds:
                assert hasattr(
                    ds, "Conventions"
                ), f"Missing Conventions attribute in {netcdf_file}"
                assert (
                    ds.Conventions == "CF-1.8"
                ), f"Should be CF-1.8 compliant: {netcdf_file}"
                assert hasattr(
                    ds, "featureType"
                ), f"Missing featureType attribute in {netcdf_file}"

    def test_netcdf_generation_simple_cruise(self):
        """Test NetCDF generation with simple 2-station cruise."""
        yaml_path = "tests/fixtures/cruise_simple.yaml"

        # Load configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        assert config.cruise_name == "Simple_Test_Cruise_2028"
        assert len(config.stations) == 2

        # Generate timeline
        timeline = generate_timeline(config)
        assert len(timeline) > 0, "Timeline should not be empty"

        # Generate NetCDF outputs to dedicated directory
        output_path = NETCDF_OUTPUT_DIR / "simple_cruise"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        # Verify files were created
        assert len(netcdf_files) == 4, "Should create 4 NetCDF files"

        expected_files = [
            f"{config.cruise_name.replace(' ', '_')}_schedule.nc",
            f"{config.cruise_name.replace(' ', '_')}_points.nc",
            f"{config.cruise_name.replace(' ', '_')}_lines.nc",
            f"{config.cruise_name.replace(' ', '_')}_areas.nc",
        ]

        for expected_file in expected_files:
            expected_path = output_path / expected_file
            assert expected_path in netcdf_files
            assert expected_path.exists()
            assert expected_path.stat().st_size > 0

    def test_netcdf_generation_mixed_operations(self):
        """Test NetCDF generation with mixed operations (stations, moorings, transits)."""
        yaml_path = "tests/fixtures/cruise_mixed_ops.yaml"

        # Load configuration
        loader = ConfigLoader(yaml_path)
        config = loader.load()

        assert config.cruise_name == "Mixed_Operations_Test_2028"
        assert len(config.stations) == 2  # CTD station + mooring

        # Generate timeline
        timeline = generate_timeline(config)
        assert len(timeline) > 0, "Timeline should not be empty"

        # Generate NetCDF outputs to dedicated directory
        output_path = NETCDF_OUTPUT_DIR / "mixed_ops"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        # Verify files were created
        assert len(netcdf_files) == 4

        # Test points file contains both station and mooring
        points_file = output_path / f"{config.cruise_name.replace(' ', '_')}_points.nc"
        with nc.Dataset(points_file, "r") as ds:
            assert ds.dimensions["obs"].size == 2, "Should have 2 point operations"

            # Check operations include both CTD and mooring
            operation_types = [str(op_type) for op_type in ds.variables["type"][:]]
            assert "CTD_profile" in operation_types
            assert any("Mooring_" in op_type for op_type in operation_types)

        # Test schedule file contains scientific transit
        schedule_file = (
            output_path / f"{config.cruise_name.replace(' ', '_')}_schedule.nc"
        )
        with nc.Dataset(schedule_file, "r") as ds:
            activity_types = [str(at) for at in ds.variables["category"][:]]
            assert (
                "line_operation" in activity_types
            ), "Should include scientific transit"

    def test_cf_compliance_validation(self):
        """Test CF-1.8 compliance validation for all generated files."""
        yaml_path = "tests/fixtures/cruise_simple.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        output_path = NETCDF_OUTPUT_DIR / "cf_compliance"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        # Test each file for CF compliance
        for netcdf_file in netcdf_files:
            self._verify_cf_compliance(netcdf_file)

    def test_point_operations_structure(self):
        """Test detailed structure of point operations file."""
        yaml_path = "tests/fixtures/cruise_simple.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        output_path = NETCDF_OUTPUT_DIR / "point_structure"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        points_file = output_path / f"{config.cruise_name.replace(' ', '_')}_points.nc"

        with nc.Dataset(points_file, "r") as ds:
            # Check featureType
            assert ds.featureType == "point"

            # Check required dimensions
            assert "obs" in ds.dimensions
            assert ds.dimensions["obs"].size == 2  # 2 stations

            # Check coordinate variables
            assert "longitude" in ds.variables
            assert "latitude" in ds.variables
            assert "waterdepth" in ds.variables

            # Check coordinate attributes
            lon_var = ds.variables["longitude"]
            assert lon_var.standard_name == "longitude"
            assert lon_var.units == "degrees_east"

            lat_var = ds.variables["latitude"]
            assert lat_var.standard_name == "latitude"
            assert lat_var.units == "degrees_north"

            depth_var = ds.variables["waterdepth"]
            assert depth_var.standard_name == "sea_floor_depth_below_sea_surface"
            assert depth_var.units == "m"
            assert depth_var.positive == "down"

            # Check data variables have coordinates attribute
            for var_name in ["name", "type", "duration", "comment"]:
                var = ds.variables[var_name]
                assert hasattr(var, "coordinates")
                assert "latitude longitude waterdepth" in var.coordinates

    def test_ship_schedule_structure(self):
        """Test detailed structure of ship schedule file."""
        yaml_path = "tests/fixtures/cruise_mixed_ops.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        output_path = NETCDF_OUTPUT_DIR / "schedule_structure"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        schedule_file = (
            output_path / f"{config.cruise_name.replace(' ', '_')}_schedule.nc"
        )

        with nc.Dataset(schedule_file, "r") as ds:
            # Check featureType
            assert ds.featureType == "trajectory"

            # Check time coordinate
            assert "time" in ds.variables
            time_var = ds.variables["time"]
            assert time_var.standard_name == "time"
            assert "days since 1970-01-01" in time_var.units

            # Check that time values are reasonable (not all zeros)
            time_values = time_var[:]
            assert len(set(time_values)) > 1, "Time values should not all be the same"

            # Check activity types are valid
            activity_types = [str(at) for at in ds.variables["category"][:]]
            valid_types = {
                "point_operation",
                "line_operation",
                "transit",
                "area_operation",
                "other",
            }
            for activity_type in activity_types:
                assert (
                    activity_type in valid_types
                ), f"Invalid activity type: {activity_type}"

    def test_line_operations_structure(self):
        """Test structure of line operations file (scientific transits)."""
        yaml_path = "tests/fixtures/cruise_mixed_ops.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        output_path = NETCDF_OUTPUT_DIR / "line_structure"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        lines_file = output_path / f"{config.cruise_name.replace(' ', '_')}_lines.nc"

        with nc.Dataset(lines_file, "r") as ds:
            # Check featureType
            assert ds.featureType == "trajectory"

            # Check dimensions
            assert "operations" in ds.dimensions
            assert "endpoints" in ds.dimensions
            assert ds.dimensions["endpoints"].size == 2

            # Should have 1 line operation (Survey_Line_Alpha)
            n_operations = ds.dimensions["operations"].size
            assert n_operations == 1, f"Expected 1 line operation, got {n_operations}"

            # Check coordinate variables structure
            lon_var = ds.variables["longitude"]
            lat_var = ds.variables["latitude"]
            assert lon_var.shape == (n_operations, 2)
            assert lat_var.shape == (n_operations, 2)

            # Check that start and end coordinates are different (should be fixed with our offset)
            if n_operations > 0:
                start_lon, end_lon = lon_var[0, :]
                start_lat, end_lat = lat_var[0, :]
                # With our offset implementation, lat should be different
                assert (
                    start_lat != end_lat
                ), "Start and end latitudes should be different"

    def _verify_cf_compliance(self, netcdf_file: Path):
        """Verify CF compliance for a single NetCDF file."""
        with nc.Dataset(netcdf_file, "r") as ds:
            # Check required global attributes
            required_attrs = ["Conventions", "title", "institution", "featureType"]
            for attr in required_attrs:
                assert hasattr(
                    ds, attr
                ), f"Missing required global attribute: {attr} in {netcdf_file}"

            # Check Conventions value
            assert ds.Conventions == "CF-1.8"

            # Check featureType is valid
            valid_feature_types = {"point", "trajectory"}
            assert ds.featureType in valid_feature_types

            # Check coordinate variables have required attributes
            for var_name in ["longitude", "latitude"]:
                if var_name in ds.variables:
                    var = ds.variables[var_name]
                    assert hasattr(
                        var, "units"
                    ), f"Variable {var_name} missing 'units' attribute"
                    assert hasattr(
                        var, "long_name"
                    ), f"Variable {var_name} missing 'long_name' attribute"

    def test_data_consistency_across_files(self):
        """Test that coordinate and metadata are consistent across NetCDF files."""
        yaml_path = "tests/fixtures/cruise_simple.yaml"

        loader = ConfigLoader(yaml_path)
        config = loader.load()
        timeline = generate_timeline(config)

        # Get reference coordinates from config
        ref_station = config.stations[0]
        ref_lat, ref_lon = ref_station.position.latitude, ref_station.position.longitude

        output_path = NETCDF_OUTPUT_DIR / "data_consistency"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(config, timeline, output_path)

        points_file = output_path / f"{config.cruise_name.replace(' ', '_')}_points.nc"
        schedule_file = (
            output_path / f"{config.cruise_name.replace(' ', '_')}_schedule.nc"
        )

        # Verify coordinates match in both files
        with nc.Dataset(points_file, "r") as points_ds:
            points_lats = points_ds.variables["latitude"][:]
            points_lons = points_ds.variables["longitude"][:]

            # First station should match reference
            assert abs(points_lats[0] - ref_lat) < 1e-6
            assert abs(points_lons[0] - ref_lon) < 1e-6

        with nc.Dataset(schedule_file, "r") as schedule_ds:
            schedule_lats = schedule_ds.variables["latitude"][:]
            schedule_lons = schedule_ds.variables["longitude"][:]

            # Should contain the reference coordinates somewhere in timeline
            lat_matches = [abs(lat - ref_lat) < 1e-6 for lat in schedule_lats]
            lon_matches = [abs(lon - ref_lon) < 1e-6 for lon in schedule_lons]

            # Should have at least one position that matches reference station
            assert any(
                lat_matches
            ), f"Reference latitude {ref_lat} not found in schedule"
            assert any(
                lon_matches
            ), f"Reference longitude {ref_lon} not found in schedule"

    def test_empty_configuration_handling(self):
        """Test NetCDF generation with minimal/empty configuration."""
        # Create a minimal config with no stations
        from cruiseplan.core.validation import CruiseConfig, PortDefinition

        minimal_config = CruiseConfig(
            cruise_name="Empty_Test_Cruise",
            default_vessel_speed=10.0,
            calculate_transfer_between_sections=False,
            calculate_depth_via_bathymetry=False,
            departure_port=PortDefinition(name="Port A", position="0,0"),
            arrival_port=PortDefinition(name="Port B", position="1,1"),
            first_station="none",
            last_station="none",
            legs=[],
            start_date="2025-01-01",
            start_time="08:00",
        )

        timeline = generate_timeline(minimal_config)

        output_path = NETCDF_OUTPUT_DIR / "empty_config"
        clean_netcdf_directory(output_path)
        netcdf_files = generate_netcdf_outputs(minimal_config, timeline, output_path)

        # Should still create all files, even if empty
        assert len(netcdf_files) == 4

        # Check that files are valid but may have zero dimensions
        for netcdf_file in netcdf_files:
            assert netcdf_file.exists()
            with nc.Dataset(netcdf_file, "r") as ds:
                assert hasattr(ds, "Conventions")
                assert ds.Conventions == "CF-1.8"
