"""
Integration tests for CLI-to-API parameter mapping and contracts.

These tests verify that the CLI layer correctly maps parameters to the API layer
without mocking the API functions themselves. This catches parameter mapping bugs
that unit tests miss.
"""

import argparse
import inspect
from pathlib import Path
from unittest.mock import patch

import pytest

import cruiseplan
from cruiseplan.init_utils import _resolve_cli_to_api_params


class TestCLIAPIParameterMapping:
    """Test CLI parameter mapping to API functions."""

    def test_process_command_parameter_mapping(self):
        """Test that process CLI correctly maps parameters to API function signature."""
        # Create realistic CLI args that would come from argparse
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            output="test_output",
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
            bathy_source="etopo2022",
            bathy_dir="data/bathy",
            format="all",
            bathy_stride=10,
            run_validation=True,
            run_map_generation=True,
            validate_depths=True,
            tolerance=10.0,
            verbose=False,
        )

        # Resolve CLI args to API parameters
        api_params = _resolve_cli_to_api_params(args, "process")

        # Get the actual API function signature
        api_sig = inspect.signature(cruiseplan.process)

        # Check that we're not passing invalid parameters
        invalid_params = set(api_params.keys()) - set(api_sig.parameters.keys())
        assert (
            not invalid_params
        ), f"Invalid parameters passed to process API: {invalid_params}"

        # Check that all required parameters are provided or have defaults
        missing_params = []
        for param_name, param in api_sig.parameters.items():
            if (
                param.default is inspect.Parameter.empty
                and param_name not in api_params
            ):
                missing_params.append(param_name)

        assert (
            not missing_params
        ), f"Missing required parameters for process API: {missing_params}"

    def test_schedule_command_parameter_mapping(self):
        """Test that schedule CLI correctly maps parameters to API function signature."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            output="test_output",
            format="all",
            leg=None,
            derive_netcdf=False,
            bathy_stride=10,
            figsize=[12, 8],
            validate_depths=True,
            verbose=False,
        )

        api_params = _resolve_cli_to_api_params(args, "schedule")
        api_sig = inspect.signature(cruiseplan.schedule)

        # Check for invalid parameters
        invalid_params = set(api_params.keys()) - set(api_sig.parameters.keys())
        assert (
            not invalid_params
        ), f"Invalid parameters passed to schedule API: {invalid_params}"

    def test_enrich_command_parameter_mapping(self):
        """Test that enrich CLI correctly maps parameters to API function signature."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            output_dir="data",
            output="test_output",
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
            bathy_source="etopo2022",
            bathy_dir="data/bathy",
            verbose=False,
        )

        api_params = _resolve_cli_to_api_params(args, "enrich")
        api_sig = inspect.signature(cruiseplan.enrich)

        # Check for invalid parameters
        invalid_params = set(api_params.keys()) - set(api_sig.parameters.keys())
        assert (
            not invalid_params
        ), f"Invalid parameters passed to enrich API: {invalid_params}"

    def test_validate_command_parameter_mapping(self):
        """Test that validate CLI correctly maps parameters to API function signature."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            bathy_source="etopo2022",
            bathy_dir="data/bathy",
            check_depths=True,
            tolerance=10.0,
            strict=False,
            warnings_only=False,
            verbose=False,
        )

        api_params = _resolve_cli_to_api_params(args, "validate")
        api_sig = inspect.signature(cruiseplan.validate)

        # Check for invalid parameters
        invalid_params = set(api_params.keys()) - set(api_sig.parameters.keys())
        assert (
            not invalid_params
        ), f"Invalid parameters passed to validate API: {invalid_params}"


class TestCLIAPIIntegrationFlow:
    """Test end-to-end CLI to API integration without mocking API layer."""

    def test_process_command_integration(self):
        """Test process command integration with minimal mocking."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir="data",
            output="integration_test",
            add_depths=True,
            add_coords=True,
            expand_sections=True,
            expand_ports=True,
            bathy_source="etopo2022",
            bathy_dir="data/bathymetry",
            format="all",
            bathy_stride=10,
            run_validation=True,
            run_map_generation=True,
            validate_depths=True,
            tolerance=10.0,
            verbose=False,
        )

        # Mock only external dependencies, not the API layer
        with (
            patch("cruiseplan.core.cruise.Cruise") as mock_cruise,
            patch("cruiseplan.output.map_generator.generate_map"),
            patch("pathlib.Path.exists", return_value=True),
        ):

            mock_cruise.return_value.to_dict.return_value = {"cruise_name": "Test"}

            # Resolve parameters
            api_params = _resolve_cli_to_api_params(args, "process")

            # This should not raise TypeError about unexpected parameters
            try:
                # Call the actual API function with resolved parameters
                cruiseplan.process(**api_params)
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    pytest.fail(f"Parameter mapping error in process command: {e}")
            except Exception:
                # Other exceptions are acceptable for this test
                # (file not found, validation errors, etc.)
                pass

    def test_schedule_command_integration(self):
        """Test schedule command integration with minimal mocking."""
        args = argparse.Namespace(
            config_file=Path("tests/fixtures/tc1_single.yaml"),
            output_dir="data",
            output="integration_test",
            format="html",
            leg=None,
            derive_netcdf=False,
            bathy_stride=10,
            validate_depths=True,
            verbose=False,
        )

        # Mock only external dependencies
        with (
            patch("cruiseplan.core.cruise.Cruise") as mock_cruise,
            patch("cruiseplan.calculators.scheduler.generate_timeline"),
            patch("pathlib.Path.exists", return_value=True),
        ):

            mock_cruise.return_value.to_dict.return_value = {"cruise_name": "Test"}

            api_params = _resolve_cli_to_api_params(args, "schedule")

            try:
                cruiseplan.schedule(**api_params)
            except TypeError as e:
                if "unexpected keyword argument" in str(e):
                    pytest.fail(f"Parameter mapping error in schedule command: {e}")
            except Exception:
                # Other exceptions are acceptable for this test
                pass


class TestParameterMappingEdgeCases:
    """Test edge cases in parameter mapping that could cause issues."""

    def test_missing_optional_parameters(self):
        """Test that missing optional parameters don't break API calls."""
        # Minimal args with many optional parameters missing
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
        )

        for command in ["process", "schedule", "enrich", "validate"]:
            api_params = _resolve_cli_to_api_params(args, command)

            # Should not contain None values for missing optional parameters
            none_params = {k: v for k, v in api_params.items() if v is None}
            # Only config_file and output are allowed to be None
            allowed_none = {"config_file", "output"}
            unexpected_none = set(none_params.keys()) - allowed_none

            assert (
                not unexpected_none
            ), f"Unexpected None parameters in {command}: {unexpected_none}"

    def test_command_specific_parameter_isolation(self):
        """Test that commands only get their specific parameters."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            # Schedule-specific parameter
            derive_netcdf=True,
            leg="leg1",
            # Validate-specific parameter
            strict=True,
            warnings_only=True,
            # Enrich-specific parameter
            expand_sections=False,
        )

        # Process should not get schedule-specific parameters
        process_params = _resolve_cli_to_api_params(args, "process")
        assert (
            "derive_netcdf" not in process_params
        ), "process should not receive derive_netcdf"
        assert "leg" not in process_params, "process should not receive leg"

        # Schedule should not get validate-specific parameters
        schedule_params = _resolve_cli_to_api_params(args, "schedule")
        assert "strict" not in schedule_params, "schedule should not receive strict"
        assert (
            "warnings_only" not in schedule_params
        ), "schedule should not receive warnings_only"

        # Validate should not get enrich-specific parameters
        validate_params = _resolve_cli_to_api_params(args, "validate")
        assert (
            "expand_sections" not in validate_params
        ), "validate should not receive expand_sections"

    def test_deprecated_parameter_handling(self):
        """Test that deprecated parameters are handled correctly."""
        args = argparse.Namespace(
            config_file=Path("test.yaml"),
            # Simulate deprecated parameter that should map to new name
            validate_depths=True,  # Should map to depth_check for process
        )

        process_params = _resolve_cli_to_api_params(args, "process")

        # Should map deprecated parameter to correct API parameter
        assert "depth_check" in process_params
        assert process_params["depth_check"] is True
