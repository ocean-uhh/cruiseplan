"""
Configuration validation command.

This module implements the 'cruiseplan validate' command for comprehensive
validation of YAML configuration files without modification.

Uses the API-first architecture pattern with proper separation of concerns:
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
    _format_error_message,
    _format_progress_header,
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _extract_api_errors,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import _validate_config_file
from cruiseplan.utils.output_formatting import _format_validation_results

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for validate command using API-first architecture.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments containing config_file, check_depths, tolerance, etc.

    Raises
    ------
    CLIError
        If input validation fails or configuration validation encounters errors.
    """
    try:
        # Setup logging using new utility
        _setup_cli_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Validate input file using new utility
        config_file = _validate_config_file(args.config_file)

        # Format progress header using new utility
        _format_progress_header(
            operation="Configuration Validation",
            config_file=config_file,
            check_depths=getattr(args, "check_depths", False),
            tolerance=getattr(args, "tolerance", 10.0),
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "validate")

        # Call API function instead of core directly
        logger.info("Running validation checks...")
        api_response = cruiseplan.validate(**api_params)

        # Convert API response to CLI format using bridge utility
        cli_response = _convert_api_response_to_cli(api_response, "validate")

        # Extract success status and messages using utility
        success, errors, warnings = _extract_api_errors(cli_response)

        # Report results using new formatting utility
        logger.info("")
        logger.info("=" * 50)
        logger.info("Validation Results")
        logger.info("=" * 50)

        if errors:
            logger.error("❌ Validation Errors:")
            for error in errors:
                logger.error(f"  • {error}")

        if warnings:
            logger.warning("⚠️ Validation Warnings:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

        # Format and display summary using new utility
        summary_message = _format_validation_results(success, errors, warnings)

        if success:
            logger.info(summary_message)
            if warnings and getattr(args, "warnings_only", False):
                logger.info("ℹ️ Treating warnings as informational only")
            sys.exit(0)
        else:
            logger.error(summary_message)
            sys.exit(1)

    except CLIError as e:
        _format_error_message("validate", e)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        _format_error_message(
            "validate",
            e,
            ["Check configuration file syntax", "Verify file permissions"],
        )
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(description="Validate cruise configurations")
    parser.add_argument(
        "-c", "--config-file", type=Path, required=True, help="Input YAML file"
    )
    parser.add_argument(
        "--check-depths", action="store_true", help="Check depth accuracy"
    )
    parser.add_argument("--strict", action="store_true", help="Strict validation mode")
    parser.add_argument(
        "--warnings-only", action="store_true", help="Show warnings without failing"
    )
    parser.add_argument(
        "--tolerance", type=float, default=10.0, help="Depth tolerance percentage"
    )
    parser.add_argument("--bathymetry-source", default="etopo2022")

    args = parser.parse_args()
    main(args)
