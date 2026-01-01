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
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import _validate_config_file

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
        # Setup logging using new utility
        _setup_cli_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Handle legacy parameter deprecation warnings using utility function
        from cruiseplan.cli.cli_utils import _handle_deprecated_params

        param_map = {
            "bathy_source_legacy": "bathy_source",
            "bathy_dir_legacy": "bathy_dir",
            "bathy_stride_legacy": "bathy_stride",
        }
        _handle_deprecated_params(args, param_map)

        # Validate input file using new utility
        config_file = _validate_config_file(args.config_file)

        # Format progress header using new utility
        _format_progress_header(
            operation="Configuration Processing",
            config_file=config_file,
            add_depths=getattr(args, "add_depths", True),
            add_coords=getattr(args, "add_coords", True),
            run_validation=getattr(args, "run_validation", True),
            run_map_generation=getattr(args, "run_map_generation", True),
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "process")

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
            # Format success message using new utility
            _format_success_message("configuration processing", all_generated_files)
        else:
            errors = cli_response.get("errors", ["Processing failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            sys.exit(1)

    except CLIError as e:
        _format_error_message("process", e)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        _format_error_message(
            "process",
            e,
            [
                "Check configuration file syntax",
                "Verify bathymetry data availability",
                "Ensure sufficient disk space",
            ],
        )
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
