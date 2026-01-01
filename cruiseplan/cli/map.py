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
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import (
    _validate_config_file,
    _validate_directory_writable,
)

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
        # Setup logging using new utility
        _setup_cli_logging(verbose=getattr(args, "verbose", False))

        # Handle legacy parameter deprecation warnings using utility function
        from cruiseplan.cli.cli_utils import _handle_deprecated_params

        param_map = {
            "bathymetry_source_legacy": "bathy_source",
            "bathymetry_dir_legacy": "bathy_dir",
            "bathymetry_stride_legacy": "bathy_stride",
        }
        _handle_deprecated_params(args, param_map)

        # Handle deprecated --output-file parameter
        if hasattr(args, "output_file") and args.output_file:
            logger.warning(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )

        # Validate input file using new utility
        config_file = _validate_config_file(args.config_file)
        # Output directory validation handled by API layer

        # Format progress header using new utility
        _format_progress_header(
            operation="Map Generation",
            config_file=config_file,
            format=getattr(args, "format", "all"),
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "map")

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
            # Format success message using new utility
            _format_success_message("map generation", generated_files)
        else:
            errors = cli_response.get("errors", ["Map generation failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            return 1

    except FileNotFoundError:
        _format_error_message(
            "map",
            FileNotFoundError(f"Configuration file not found: {args.config_file}"),
        )
        return 1
    except Exception as e:
        _format_error_message(
            "map",
            e,
            [
                "Check configuration file syntax",
                "Verify bathymetry data availability",
                "Check output directory permissions",
            ],
        )
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1

    return 0
