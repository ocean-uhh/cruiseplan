"""
Integration tests for NetCDF generator with real YAML fixture files.
"""

import shutil
import tempfile
from pathlib import Path

import netCDF4 as nc
import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.core.validation import enrich_configuration
from cruiseplan.output.netcdf_generator import generate_netcdf_outputs
from cruiseplan.utils.config import ConfigLoader

# Available test fixtures
TEST_FIXTURES = [
    "tests/fixtures/tc4_mixed_ops.yaml",
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
        # Create temporary enriched file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as tmp_file:
            enriched_path = Path(tmp_file.name)

        try:
            # Enrich the fixture file to add missing global fields
            # This will save the enriched config to the temporary file
            enrich_configuration(yaml_path, output_path=enriched_path)

            # Load enriched configuration
            loader = ConfigLoader(str(enriched_path))
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
            assert (
                len(netcdf_files) == 4
            ), f"Should create 4 NetCDF files for {yaml_path}"

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

        finally:
            # Clean up temporary enriched file
            if enriched_path.exists():
                enriched_path.unlink()

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

    def test_empty_configuration_handling(self):
        """Test NetCDF generation with minimal/empty configuration."""
        # Create a minimal config with no stations
        from cruiseplan.core.validation import (
            CruiseConfig,
            LegDefinition,
            PortDefinition,
        )

        minimal_config = CruiseConfig(
            cruise_name="Empty_Test_Cruise",
            default_vessel_speed=10.0,
            calculate_transfer_between_sections=False,
            calculate_depth_via_bathymetry=False,
            start_date="2025-01-01",
            start_time="08:00",
            legs=[
                LegDefinition(
                    name="empty_leg",
                    departure_port=PortDefinition(
                        name="Port A", latitude=0.0, longitude=0.0
                    ),
                    arrival_port=PortDefinition(
                        name="Port B", latitude=1.0, longitude=1.0
                    ),
                    first_station="none",
                    last_station="none",
                    activities=[],
                )
            ],
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
