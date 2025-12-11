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
    setup_logging,
    validate_input_file,
    validate_output_path,
)

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for schedule command.

    Args:
        args: Parsed command line arguments
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
                formats = ["html", "csv", "latex", "kml", "netcdf"]
            elif isinstance(args.format, str):
                formats = [f.strip().lower() for f in args.format.split(",")]
            elif isinstance(args.format, list):
                formats = [f.strip().lower() for f in args.format]
            else:
                formats = [args.format.strip().lower()]
        else:
            # Default formats
            formats = ["html", "csv"]

        logger.info("=" * 60)
        logger.info("Cruise Schedule Generation")
        logger.info("=" * 60)
        logger.info(f"Configuration: {config_file}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Formats: {', '.join(formats)}")
        logger.info("")

        # Import and call core scheduling function
        from cruiseplan.calculators.scheduler import generate_cruise_schedule

        logger.info("Generating cruise schedule...")
        schedule_result = generate_cruise_schedule(
            config_path=config_file,
            output_dir=output_dir,
            formats=formats,
            selected_leg=getattr(args, "leg", None),
        )

        # Report results
        logger.info("")
        logger.info("=" * 60)
        logger.info("Schedule Generation Complete")
        logger.info("=" * 60)
        logger.info(f"Total activities: {schedule_result['total_activities']}")
        logger.info(
            f"Total duration: {schedule_result['total_duration_hours']:.1f} hours"
        )
        logger.info(
            f"Generated formats: {', '.join(schedule_result['formats_generated'])}"
        )

        if schedule_result.get("warnings"):
            logger.warning("⚠️ Warnings:")
            for warning in schedule_result["warnings"]:
                logger.warning(f"  • {warning}")

        logger.info("")
        logger.info("✅ Schedule generation successful!")
        logger.info(f"📁 Output files saved to: {output_dir}")

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
        choices=["html", "latex", "csv", "kml", "netcdf", "all"],
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
