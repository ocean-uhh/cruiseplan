"""
Cruise schedule generation command.

This module implements the 'cruiseplan schedule' command for generating
comprehensive cruise schedules from YAML configuration files.
"""

import argparse
import logging
import sys
from pathlib import Path

from cruiseplan.cli.utils import (
    CLIError,
    count_individual_warnings,
    display_user_warnings,
    setup_logging,
    validate_input_file,
    validate_output_path,
)

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for schedule command.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments containing config_file, output_dir, format, etc.

    Raises
    ------
    CLIError
        If input validation fails or schedule generation encounters errors.
    """
    try:
        # Setup logging
        setup_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Validate input file
        config_file = validate_input_file(args.config_file)

        # Determine output directory
        if args.output_dir:
            output_dir = validate_output_path(output_dir=args.output_dir)
        else:
            # Default to current directory with cruise name subdirectory
            output_dir = Path.cwd()

        # Parse formats list
        formats = []
        if args.format:
            if args.format == "all":
                formats = ["html", "csv", "latex", "netcdf", "png"]
            elif isinstance(args.format, str):
                formats = [f.strip().lower() for f in args.format.split(",")]
            elif isinstance(args.format, list):
                formats = [f.strip().lower() for f in args.format]
            else:
                formats = [args.format.strip().lower()]
        else:
            # Default formats
            formats = ["html", "csv"]

        # Check --derive-netcdf flag compatibility
        derive_netcdf = getattr(args, "derive_netcdf", False)
        if derive_netcdf and "netcdf" not in formats:
            logger.warning("⚠️  --derive-netcdf flag requires NetCDF output format")
            logger.warning("   Either add 'netcdf' to --format or use --format all")
            logger.warning("   Ignoring --derive-netcdf flag.")
            derive_netcdf = False

        logger.info("=" * 60)
        logger.info("Cruise Schedule Generation")
        logger.info("=" * 60)
        logger.info(f"Configuration: {config_file}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Formats: {', '.join(formats)}")
        logger.info("")

        # Run validation first to catch any issues and show warnings
        from cruiseplan.core.validation import validate_configuration_file

        success, errors, warnings = validate_configuration_file(
            config_path=config_file,
            check_depths=False,
            strict=False,
        )

        if errors:
            logger.error("❌ Configuration validation failed:")
            for error in errors:
                logger.error(f"  • {error}")
            raise CLIError(
                "Cannot proceed with schedule generation due to validation errors"
            )

        if warnings:
            warning_count = count_individual_warnings(warnings)
            logger.info(f"✅ Validation passed with {warning_count} warnings")
            display_user_warnings(warnings, "")  # Empty title since we show it above
            logger.info("")

        # Import and call core scheduling function
        from cruiseplan.calculators.scheduler import generate_cruise_schedule

        schedule_result = generate_cruise_schedule(
            config_path=config_file,
            output_dir=output_dir,
            formats=formats,
            selected_leg=getattr(args, "leg", None),
            derive_netcdf=derive_netcdf,
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_stride=getattr(args, "bathy_stride", 10),
            figsize=getattr(args, "figsize", [12.0, 8.0]),
            output_basename=getattr(args, "output", None),
        )

        logger.info("")
        logger.info("=" * 60)
        logger.info("Schedule Generation Complete")
        logger.info("=" * 60)
        logger.info(f"Total activities: {schedule_result['total_activities']}")
        logger.info(
            f"Total duration: {schedule_result['total_duration_hours']:.1f} hours"
        )

        logger.info("")
        logger.info("✅ Schedule generation successful!")

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
    parser = argparse.ArgumentParser(description="Generate cruise schedules")
    parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        required=True,
        help="Input YAML configuration file",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, help="Output directory for schedule files"
    )
    parser.add_argument(
        "--format",
        choices=["html", "latex", "csv", "netcdf", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--leg", type=str, help="Generate schedule for specific leg only"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")

    args = parser.parse_args()
    main(args)
