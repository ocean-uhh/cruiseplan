"""
Map generation CLI command for creating cruise track visualizations.

This module provides command-line functionality for generating PNG maps
directly from YAML cruise configuration files, independent of scheduling.

Uses the API-first architecture pattern with proper separation of concerns:
- CLI layer handles argument parsing and output formatting
- API layer (cruiseplan.__init__) contains business logic
- Utility functions provide consistent formatting and error handling
"""

import argparse
import logging

import cruiseplan
from cruiseplan.cli.cli_utils import (
    _collect_generated_files,
    _format_error_message,
    _format_progress_header,
    _format_success_message,
    _initialize_cli_command,
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import (
    _apply_cli_defaults,
    _handle_deprecated_cli_params,
    _validate_config_file,
    _validate_format_options,
)
from cruiseplan.utils.output_formatting import (
    _format_cli_error,
    _format_output_summary,
    _standardize_output_setup,
)

# Re-export functions for test mocking (cleaner than complex patch paths)
__all__ = [
    "_collect_generated_files",
    "_convert_api_response_to_cli",
    "_format_error_message",
    "_format_progress_header",
    "_format_success_message",
    "_resolve_cli_to_api_params",
    "_setup_cli_logging",
    "_validate_config_file",
    "main",
]

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> int:
    """
    Generate PNG maps and/or KML files from cruise configuration using API-first architecture.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing config_file, output options, etc.
    """
    try:
        # Handle deprecated parameters (currently no deprecated params for v0.3.0+)
        _handle_deprecated_cli_params(args)

        # Apply standard CLI defaults
        _apply_cli_defaults(args)

        # Standardized CLI initialization
        config_file = _initialize_cli_command(args)

        # Validate format options using new utility
        format_str = getattr(args, "format", "all")
        valid_formats = ["png", "kml"]

        if format_str != "all":
            format_list = _validate_format_options(format_str, valid_formats)
        else:
            format_list = valid_formats

        # Standardize output setup using new utilities
        output_dir, base_name, format_paths = _standardize_output_setup(
            args, suffix="_map", multi_formats=format_list
        )

        # Format progress header using new utility
        _format_progress_header(
            operation="Map Generation",
            config_file=config_file,
            format=format_str,
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "map")

        # Override output paths with standardized paths
        api_params["output_dir"] = output_dir
        api_params["output"] = base_name
        api_params["formats"] = format_list

        # Call API function instead of core directly
        logger.info("Generating maps and visualizations...")
        api_response = cruiseplan.map(**api_params)

        # Convert API response to CLI format using bridge utility
        cli_response = _convert_api_response_to_cli(api_response, "map")

        # Collect generated files using utility
        generated_files = _collect_generated_files(
            cli_response, base_patterns=["*_map.png", "*_catalog.kml"]
        )

        if cli_response.get("success", True) and generated_files:
            # Use new standardized output summary
            success_summary = _format_output_summary(generated_files, "Map generation")
            logger.info(success_summary)
        else:
            errors = cli_response.get("errors", ["Map generation failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            return 1

    except FileNotFoundError:
        error_msg = _format_cli_error(
            "Map generation",
            FileNotFoundError(f"Configuration file not found: {args.config_file}"),
            suggestions=[
                "Check configuration file path",
                "Verify file exists and is readable",
            ],
        )
        logger.error(error_msg)
        return 1
    except Exception as e:
        error_msg = _format_cli_error(
            "Map generation",
            e,
            suggestions=[
                "Check configuration file syntax",
                "Verify bathymetry data availability",
                "Check output directory permissions",
                "Run with --verbose for more details",
            ],
        )
        logger.error(error_msg)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1

    return 0
