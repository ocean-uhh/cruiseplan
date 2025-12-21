"""
Test suite for cruiseplan process command.

This module tests the unified process command that combines enrichment,
validation, and map generation with comprehensive flag validation.
"""

import argparse
from pathlib import Path
from unittest.mock import patch

import pytest

from cruiseplan.cli.process import determine_steps, main
from cruiseplan.cli.utils import CLIError


class TestProcessFlagValidation:
    """Test flag validation rules for the process command."""

    def create_args(self, **kwargs):
        """Create test arguments with defaults."""
        args = argparse.Namespace()

        # Required argument
        args.config_file = Path("test.yaml")

        # Processing mode flags
        args.only_enrich = kwargs.get("only_enrich", False)
        args.only_validate = kwargs.get("only_validate", False)
        args.only_map = kwargs.get("only_map", False)
        args.no_enrich = kwargs.get("no_enrich", False)
        args.no_validate = kwargs.get("no_validate", False)
        args.no_map = kwargs.get("no_map", False)

        # Enrichment control flags
        args.no_depths = kwargs.get("no_depths", False)
        args.no_coords = kwargs.get("no_coords", False)
        args.no_sections = kwargs.get("no_sections", False)
        args.no_ports = kwargs.get("no_ports", False)

        # Validation options
        args.no_depth_check = kwargs.get("no_depth_check", False)
        args.strict = kwargs.get("strict", False)
        args.tolerance = kwargs.get("tolerance", 10.0)

        # Map options
        args.format = kwargs.get("format", "all")
        args.figsize = kwargs.get("figsize", [12, 8])

        # Output options
        args.output_dir = kwargs.get("output_dir", Path("data"))
        args.output = kwargs.get("output", None)

        # Bathymetry options
        args.bathy_source = kwargs.get("bathy_source", "etopo2022")
        args.bathy_dir = kwargs.get("bathy_dir", Path("data"))
        args.bathy_stride = kwargs.get("bathy_stride", 10)

        # General options
        args.verbose = kwargs.get("verbose", False)
        args.quiet = kwargs.get("quiet", False)

        return args

    def test_multiple_only_flags_error(self):
        """Test that multiple --only-* flags raise error."""
        with pytest.raises(
            CLIError, match="Cannot specify multiple --only-\\* flags together"
        ):
            args = self.create_args(only_enrich=True, only_validate=True)
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify multiple --only-\\* flags together"
        ):
            args = self.create_args(only_enrich=True, only_map=True)
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify multiple --only-\\* flags together"
        ):
            args = self.create_args(only_validate=True, only_map=True)
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify multiple --only-\\* flags together"
        ):
            args = self.create_args(only_enrich=True, only_validate=True, only_map=True)
            determine_steps(args)

    def test_conflicting_only_and_no_flags_error(self):
        """Test that --only-X and --no-X flags raise error."""
        with pytest.raises(
            CLIError, match="Cannot specify both --only-enrich and --no-enrich"
        ):
            args = self.create_args(only_enrich=True, no_enrich=True)
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify both --only-validate and --no-validate"
        ):
            args = self.create_args(only_validate=True, no_validate=True)
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify both --only-map and --no-map"
        ):
            args = self.create_args(only_map=True, no_map=True)
            determine_steps(args)

    def test_no_map_with_format_error(self):
        """Test that --no-map with explicit format raises error."""
        with pytest.raises(CLIError, match="Cannot specify --no-map with --format"):
            args = self.create_args(no_map=True, format="png")
            determine_steps(args)

        with pytest.raises(CLIError, match="Cannot specify --no-map with --format"):
            args = self.create_args(no_map=True, format="kml")
            determine_steps(args)

        with pytest.raises(CLIError, match="Cannot specify --no-map with --format"):
            args = self.create_args(no_map=True, format="png,kml")
            determine_steps(args)

    def test_only_enrich_with_format_error(self):
        """Test that --only-enrich with format raises error."""
        with pytest.raises(
            CLIError, match="Cannot specify --only-enrich with --format"
        ):
            args = self.create_args(only_enrich=True, format="png")
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify --only-enrich with --format"
        ):
            args = self.create_args(only_enrich=True, format="kml")
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify --only-enrich with --format"
        ):
            args = self.create_args(only_enrich=True, format="png,kml")
            determine_steps(args)

    def test_only_validate_with_format_error(self):
        """Test that --only-validate with format raises error."""
        with pytest.raises(
            CLIError, match="Cannot specify --only-validate with --format"
        ):
            args = self.create_args(only_validate=True, format="png")
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify --only-validate with --format"
        ):
            args = self.create_args(only_validate=True, format="kml")
            determine_steps(args)

        with pytest.raises(
            CLIError, match="Cannot specify --only-validate with --format"
        ):
            args = self.create_args(only_validate=True, format="png,kml")
            determine_steps(args)

    def test_all_steps_disabled_error(self):
        """Test that disabling all steps raises error."""
        with pytest.raises(
            CLIError, match="All processing steps disabled - nothing to do"
        ):
            args = self.create_args(no_enrich=True, no_validate=True, no_map=True)
            determine_steps(args)


class TestProcessStepDetermination:
    """Test step determination logic for different flag combinations."""

    def create_args(self, **kwargs):
        """Create test arguments with defaults."""
        args = argparse.Namespace()

        # Required argument
        args.config_file = Path("test.yaml")

        # Processing mode flags
        args.only_enrich = kwargs.get("only_enrich", False)
        args.only_validate = kwargs.get("only_validate", False)
        args.only_map = kwargs.get("only_map", False)
        args.no_enrich = kwargs.get("no_enrich", False)
        args.no_validate = kwargs.get("no_validate", False)
        args.no_map = kwargs.get("no_map", False)

        # Map options
        args.format = kwargs.get("format", "all")
        args.figsize = kwargs.get("figsize", [12, 8])

        return args

    def test_only_enrich_steps(self):
        """Test --only-enrich returns only enrichment step."""
        args = self.create_args(only_enrich=True)
        steps = determine_steps(args)
        assert steps == ["enrich"]

    def test_only_validate_steps(self):
        """Test --only-validate returns only validation step."""
        args = self.create_args(only_validate=True)
        steps = determine_steps(args)
        assert steps == ["validate"]

    def test_only_map_steps(self):
        """Test --only-map returns only map step."""
        args = self.create_args(only_map=True)
        steps = determine_steps(args)
        assert steps == ["map"]

    def test_default_all_steps(self):
        """Test default behavior includes all steps."""
        args = self.create_args()
        steps = determine_steps(args)
        assert steps == ["enrich", "validate", "map"]

    def test_no_enrich_steps(self):
        """Test --no-enrich excludes enrichment."""
        args = self.create_args(no_enrich=True)
        steps = determine_steps(args)
        assert steps == ["validate", "map"]

    def test_no_validate_steps(self):
        """Test --no-validate excludes validation."""
        args = self.create_args(no_validate=True)
        steps = determine_steps(args)
        assert steps == ["enrich", "map"]

    def test_no_map_steps(self):
        """Test --no-map excludes map generation."""
        args = self.create_args(no_map=True)
        steps = determine_steps(args)
        assert steps == ["enrich", "validate"]

    def test_selective_step_combinations(self):
        """Test various selective step combinations."""
        # Only enrich and validate
        args = self.create_args(no_map=True)
        steps = determine_steps(args)
        assert steps == ["enrich", "validate"]

        # Only enrich and map
        args = self.create_args(no_validate=True)
        steps = determine_steps(args)
        assert steps == ["enrich", "map"]

        # Only validate and map
        args = self.create_args(no_enrich=True)
        steps = determine_steps(args)
        assert steps == ["validate", "map"]


class TestProcessFormatValidation:
    """Test format validation with different step combinations."""

    def create_args(self, **kwargs):
        """Create test arguments with defaults."""
        args = argparse.Namespace()

        # Required argument
        args.config_file = Path("test.yaml")

        # Processing mode flags
        args.only_enrich = kwargs.get("only_enrich", False)
        args.only_validate = kwargs.get("only_validate", False)
        args.only_map = kwargs.get("only_map", False)
        args.no_enrich = kwargs.get("no_enrich", False)
        args.no_validate = kwargs.get("no_validate", False)
        args.no_map = kwargs.get("no_map", False)

        # Map options
        args.format = kwargs.get("format", "all")
        args.figsize = kwargs.get("figsize", [12, 8])

        return args

    def test_default_format_allowed_with_map_generation(self):
        """Test that default 'all' format is allowed when maps will be generated."""
        # Default case - should generate maps
        args = self.create_args()
        steps = determine_steps(args)  # Should not raise error
        assert "map" in steps

        # Only map mode
        args = self.create_args(only_map=True)
        steps = determine_steps(args)  # Should not raise error
        assert steps == ["map"]

    def test_default_format_ignored_with_no_map_generation(self):
        """Test that default 'all' format is ignored when no maps generated."""
        # Only enrich - no maps, default format should be ignored
        args = self.create_args(only_enrich=True)
        steps = determine_steps(args)  # Should not raise error
        assert steps == ["enrich"]

        # Only validate - no maps, default format should be ignored
        args = self.create_args(only_validate=True)
        steps = determine_steps(args)  # Should not raise error
        assert steps == ["validate"]

    def test_explicit_format_conflicts(self):
        """Test explicit format settings with non-map modes."""
        # Explicit PNG format with enrich-only should error
        with pytest.raises(CLIError):
            args = self.create_args(only_enrich=True, format="png")
            determine_steps(args)

        # Explicit KML format with validate-only should error
        with pytest.raises(CLIError):
            args = self.create_args(only_validate=True, format="kml")
            determine_steps(args)

        # Explicit format with no-map should error
        with pytest.raises(CLIError):
            args = self.create_args(no_map=True, format="png,kml")
            determine_steps(args)


@patch("cruiseplan.cli.process.validate_input_file")
@patch("cruiseplan.cli.process.validate_output_path")
@patch("cruiseplan.cli.process.setup_logging")
class TestProcessIntegration:
    """Test process command integration with individual commands."""

    def create_args(self, **kwargs):
        """Create test arguments with defaults."""
        args = argparse.Namespace()

        # Required argument
        args.config_file = Path("test.yaml")

        # Processing mode flags
        args.only_enrich = kwargs.get("only_enrich", False)
        args.only_validate = kwargs.get("only_validate", False)
        args.only_map = kwargs.get("only_map", False)
        args.no_enrich = kwargs.get("no_enrich", False)
        args.no_validate = kwargs.get("no_validate", False)
        args.no_map = kwargs.get("no_map", False)

        # Enrichment control flags
        args.no_depths = kwargs.get("no_depths", False)
        args.no_coords = kwargs.get("no_coords", False)
        args.no_sections = kwargs.get("no_sections", False)
        args.no_ports = kwargs.get("no_ports", False)

        # Validation options
        args.no_depth_check = kwargs.get("no_depth_check", False)
        args.strict = kwargs.get("strict", False)
        args.tolerance = kwargs.get("tolerance", 10.0)

        # Map options
        args.format = kwargs.get("format", "all")
        args.figsize = kwargs.get("figsize", [12, 8])

        # Output options
        args.output_dir = kwargs.get("output_dir", Path("data"))
        args.output = kwargs.get("output", None)

        # Bathymetry options
        args.bathy_source = kwargs.get("bathy_source", "etopo2022")
        args.bathy_dir = kwargs.get("bathy_dir", Path("data"))
        args.bathy_stride = kwargs.get("bathy_stride", 10)

        # General options
        args.verbose = kwargs.get("verbose", False)
        args.quiet = kwargs.get("quiet", False)

        return args

    @patch("cruiseplan.cli.enrich.main")
    def test_only_enrich_calls_enrich_main(
        self, mock_enrich, mock_setup_logging, mock_validate_output, mock_validate_input
    ):
        """Test --only-enrich calls enrich main function."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")

        args = self.create_args(only_enrich=True, output="test_cruise")
        main(args)

        # Verify enrich was called
        assert mock_enrich.called
        enrich_args = mock_enrich.call_args[0][0]

        # Verify enrich arguments are properly mapped
        assert enrich_args.config_file == Path("test.yaml")
        assert enrich_args.output_dir == Path("data")
        assert enrich_args.output == "test_cruise"
        assert enrich_args.add_depths is True  # Smart default
        assert enrich_args.add_coords is True  # Smart default
        assert enrich_args.expand_sections is True  # Smart default
        assert enrich_args.expand_ports is True  # Smart default

    @patch("cruiseplan.cli.validate.main")
    def test_only_validate_calls_validate_main(
        self,
        mock_validate,
        mock_setup_logging,
        mock_validate_output,
        mock_validate_input,
    ):
        """Test --only-validate calls validate main function."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")

        args = self.create_args(only_validate=True, strict=True, tolerance=5.0)
        main(args)

        # Verify validate was called
        assert mock_validate.called
        validate_args = mock_validate.call_args[0][0]

        # Verify validate arguments are properly mapped
        assert validate_args.config_file == Path("test.yaml")
        assert validate_args.check_depths is True  # Smart default
        assert validate_args.strict is True
        assert validate_args.tolerance == 5.0

    @patch("cruiseplan.cli.map.main")
    def test_only_map_calls_map_main(
        self, mock_map, mock_setup_logging, mock_validate_output, mock_validate_input
    ):
        """Test --only-map calls map main function."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")
        mock_map.return_value = 0  # Success

        args = self.create_args(only_map=True, format="png", figsize=[16, 10])
        main(args)

        # Verify map was called
        assert mock_map.called
        map_args = mock_map.call_args[0][0]

        # Verify map arguments are properly mapped
        assert map_args.config_file == Path("test.yaml")
        assert map_args.output_dir == Path("data")
        assert map_args.format == "png"
        assert map_args.figsize == [16, 10]

    @patch("cruiseplan.cli.map.main")
    @patch("cruiseplan.cli.validate.main")
    @patch("cruiseplan.cli.enrich.main")
    def test_full_processing_pipeline(
        self,
        mock_enrich,
        mock_validate,
        mock_map,
        mock_setup_logging,
        mock_validate_output,
        mock_validate_input,
    ):
        """Test full processing pipeline calls all commands in sequence."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")
        mock_map.return_value = 0  # Success

        args = self.create_args(output="expedition")
        main(args)

        # Verify all three commands were called
        assert mock_enrich.called
        assert mock_validate.called
        assert mock_map.called

        # Verify file chaining - enriched file fed to validation and mapping
        enrich_args = mock_enrich.call_args[0][0]
        validate_args = mock_validate.call_args[0][0]
        map_args = mock_map.call_args[0][0]

        # Enrich should use original file
        assert enrich_args.config_file == Path("test.yaml")
        assert enrich_args.output == "expedition"

        # Validate and map should use enriched file
        expected_enriched = Path("data") / "expedition_enriched.yaml"
        assert validate_args.config_file == expected_enriched
        assert map_args.config_file == expected_enriched
        assert map_args.output == "expedition"

    @patch("cruiseplan.cli.validate.main")
    @patch("cruiseplan.cli.enrich.main")
    def test_selective_processing_no_map(
        self,
        mock_enrich,
        mock_validate,
        mock_setup_logging,
        mock_validate_output,
        mock_validate_input,
    ):
        """Test selective processing without map generation."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")

        args = self.create_args(no_map=True)
        main(args)

        # Verify only enrich and validate were called
        assert mock_enrich.called
        assert mock_validate.called

    def test_enrichment_smart_defaults(
        self, mock_setup_logging, mock_validate_output, mock_validate_input
    ):
        """Test that enrichment smart defaults are properly applied."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")

        with patch("cruiseplan.cli.enrich.main") as mock_enrich:
            # Test default case - all enrichment enabled
            args = self.create_args(only_enrich=True)
            main(args)

            enrich_args = mock_enrich.call_args[0][0]
            assert enrich_args.add_depths is True
            assert enrich_args.add_coords is True
            assert enrich_args.expand_sections is True
            assert enrich_args.expand_ports is True

        with patch("cruiseplan.cli.enrich.main") as mock_enrich:
            # Test selective disabling
            args = self.create_args(only_enrich=True, no_depths=True, no_sections=True)
            main(args)

            enrich_args = mock_enrich.call_args[0][0]
            assert enrich_args.add_depths is False  # Disabled
            assert enrich_args.add_coords is True  # Still enabled
            assert enrich_args.expand_sections is False  # Disabled
            assert enrich_args.expand_ports is True  # Still enabled

    def test_legacy_parameter_warnings(
        self, mock_setup_logging, mock_validate_output, mock_validate_input
    ):
        """Test that legacy parameters trigger deprecation warnings."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")

        # Create args with legacy parameters
        args = self.create_args(only_validate=True)
        args.bathy_source_legacy = "gebco2025"
        args.bathy_dir_legacy = Path("legacy/path")
        args.bathy_stride_legacy = 5
        args.coord_format_legacy = "dms"

        with patch("cruiseplan.cli.validate.main") as mock_validate:
            with patch("cruiseplan.cli.process.logger") as mock_logger:
                main(args)

                # Verify deprecation warnings were logged
                warning_calls = [
                    call
                    for call in mock_logger.warning.call_args_list
                    if "deprecated" in str(call).lower()
                ]
                assert len(warning_calls) >= 3  # At least 3 deprecation warnings


class TestProcessEdgeCases:
    """Test edge cases and error scenarios."""

    def create_args(self, **kwargs):
        """Create test arguments with defaults."""
        args = argparse.Namespace()

        # Required argument
        args.config_file = Path("test.yaml")

        # All other args with defaults
        for attr in [
            "only_enrich",
            "only_validate",
            "only_map",
            "no_enrich",
            "no_validate",
            "no_map",
            "no_depths",
            "no_coords",
            "no_sections",
            "no_ports",
            "no_depth_check",
            "strict",
            "verbose",
            "quiet",
        ]:
            setattr(args, attr, kwargs.get(attr, False))

        args.tolerance = kwargs.get("tolerance", 10.0)
        args.format = kwargs.get("format", "all")
        args.figsize = kwargs.get("figsize", [12, 8])
        args.output_dir = kwargs.get("output_dir", Path("data"))
        args.output = kwargs.get("output", None)
        args.bathy_source = kwargs.get("bathy_source", "etopo2022")
        args.bathy_dir = kwargs.get("bathy_dir", Path("data"))
        args.bathy_stride = kwargs.get("bathy_stride", 10)

        return args

    @patch("cruiseplan.cli.process.validate_input_file")
    def test_invalid_config_file(self, mock_validate_input):
        """Test handling of invalid configuration file."""
        from cruiseplan.cli.utils import CLIError

        mock_validate_input.side_effect = CLIError("File not found")

        args = self.create_args()

        with pytest.raises(SystemExit) as exc_info:
            main(args)
        assert exc_info.value.code == 1

    @patch("cruiseplan.cli.process.validate_input_file")
    @patch("cruiseplan.cli.process.validate_output_path")
    @patch("cruiseplan.cli.process.setup_logging")
    @patch("cruiseplan.cli.map.main")
    def test_map_generation_failure(
        self, mock_map, mock_setup_logging, mock_validate_output, mock_validate_input
    ):
        """Test handling of map generation failure."""
        mock_validate_input.return_value = Path("test.yaml")
        mock_validate_output.return_value = Path("data")
        mock_map.return_value = 1  # Failure

        args = self.create_args(only_map=True)

        with pytest.raises(SystemExit) as exc_info:
            main(args)
        assert exc_info.value.code == 1

    def test_figsize_warning_validation(self):
        """Test figsize warning when PNG not requested."""
        # Custom figsize without PNG format should trigger warning logic
        args = self.create_args(only_map=True, format="kml", figsize=[20, 15])

        # This should not raise an error, but would log a warning in real execution
        steps = determine_steps(args)
        assert steps == ["map"]


if __name__ == "__main__":
    pytest.main([__file__])
