"""
Configuration validation command.

This module implements the 'cruiseplan validate' command for comprehensive
validation of YAML configuration files without modification.
"""

import argparse
import logging
import sys
from pathlib import Path

from cruiseplan.cli.utils import (
    CLIError,
    count_individual_warnings,
    setup_logging,
    validate_input_file,
)
from cruiseplan.core.validation import validate_configuration_file

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for validate command.

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
        # Setup logging
        setup_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Validate input file
        config_file = validate_input_file(args.config_file)

        logger.info("=" * 50)
        logger.info("Configuration Validation")
        logger.info("=" * 50)
        logger.info(f"Validating: {config_file}")
        logger.info("")

        # Call core validation function
        logger.info("Running validation checks...")
        success, errors, warnings = validate_configuration_file(
            config_path=config_file,
            check_depths=args.check_depths,
            tolerance=args.tolerance,
            bathymetry_source=args.bathymetry_source,
            bathymetry_dir=str(args.bathymetry_dir),
            strict=args.strict,
        )

        # Report results
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

        # Summary
        if success and not warnings:
            logger.info("✅ All validations passed - configuration is valid!")
            sys.exit(0)
        elif success and warnings:
            warning_count = count_individual_warnings(warnings)
            logger.info(f"✅ Validation passed with {warning_count} warnings")
            if args.warnings_only:
                logger.info("ℹ️ Treating warnings as informational only")
            sys.exit(0)
        else:
            logger.error(f"❌ Validation failed with {len(errors)} errors")
            if warnings:
                warning_count = count_individual_warnings(warnings)
                logger.error(f"   and {warning_count} additional warnings")
            sys.exit(1)

    except CLIError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
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
