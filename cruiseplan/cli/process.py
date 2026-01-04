"""
Unified configuration processing command - API-First Architecture.

This module implements the 'cruiseplan process' command using the API-first
pattern with proper separation of concerns:
- CLI layer handles argument parsing and output formatting
- API layer (cruiseplan.__init__) contains business logic
- Utility functions provide consistent formatting and error handling
"""

import argparse
import logging
import sys
from pathlib import Path

import cruiseplan
from cruiseplan.cli.cli_utils import (
    CLIError,
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


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for process command using API-first architecture.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments
    """
    try:
        # Handle deprecated parameters (currently no deprecated params for v0.3.0+)
        _handle_deprecated_cli_params(args)

        # Apply standard CLI defaults
        _apply_cli_defaults(args)

        # Standardized CLI initialization
        config_file = _initialize_cli_command(args)

        # Extract cruise name from config file for proper naming
        try:
            import yaml

            with open(config_file) as f:
                config_data = yaml.safe_load(f)
                cruise_name = config_data.get("cruise_name")
        except (FileNotFoundError, yaml.YAMLError, KeyError):
            cruise_name = None

        # Format progress header using new utility
        _format_progress_header(
            operation="Configuration Processing",
            config_file=config_file,
            add_depths=getattr(args, "add_depths", True),
            add_coords=getattr(args, "add_coords", True),
            run_validation=getattr(args, "run_validation", True),
            run_map_generation=getattr(args, "run_map_generation", True),
        )

        # Standardize output setup using new utilities
        output_dir, base_name, format_paths = _standardize_output_setup(
            args,
            cruise_name=cruise_name,
            suffix="",
            multi_formats=["yaml", "html", "csv", "png", "kml"],
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "process")

        # Override output paths with standardized paths
        api_params["output_dir"] = output_dir
        api_params["output"] = base_name

        # Call API function instead of complex wrapper logic
        logger.info("Processing configuration through full workflow...")
        timeline, generated_files = cruiseplan.process(**api_params)

        # Convert API response to CLI format using bridge utility
        api_response = (timeline, generated_files)
        cli_response = _convert_api_response_to_cli(api_response, "process")

        # Collect all generated files using utility
        all_generated_files = _collect_generated_files(
            cli_response,
            base_patterns=[
                "*_enriched.yaml",
                "*_schedule.*",
                "*_map.png",
                "*_catalog.kml",
            ],
        )

        if cli_response.get("success", True):
            # Use new standardized output summary
            success_summary = _format_output_summary(
                all_generated_files, "Configuration processing"
            )
            logger.info(success_summary)
        else:
            errors = cli_response.get("errors", ["Processing failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            sys.exit(1)

    except CLIError as e:
        error_msg = _format_cli_error(
            "Configuration processing",
            e,
            suggestions=[
                "Check configuration file path and syntax",
                "Verify output directory permissions",
                "Ensure bathymetry data is available",
            ],
        )
        logger.error(error_msg)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        error_msg = _format_cli_error(
            "Configuration processing",
            e,
            suggestions=[
                "Check configuration file syntax",
                "Verify bathymetry data availability",
                "Ensure sufficient disk space",
                "Run with --verbose for more details",
            ],
        )
        logger.error(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(
        description="Unified cruise configuration processing"
    )
    parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        required=True,
        help="Input YAML configuration file",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("data"), help="Output directory"
    )
    parser.add_argument(
        "--output", help="Base filename for outputs (without extension)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Enable quiet mode")

    args = parser.parse_args()
    main(args)
