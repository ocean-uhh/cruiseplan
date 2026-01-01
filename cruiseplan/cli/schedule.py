"""
Cruise schedule generation command.

This module implements the 'cruiseplan schedule' command for generating
comprehensive cruise schedules from YAML configuration files.

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
from cruiseplan.utils.output_formatting import _format_timeline_summary

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for schedule command using API-first architecture.

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
        # Setup logging using new utility
        _setup_cli_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Validate input file using new utility
        config_file = _validate_config_file(args.config_file)

        # Check --derive-netcdf flag compatibility (CLI-specific logic)
        derive_netcdf = getattr(args, "derive_netcdf", False)
        format_str = getattr(args, "format", "all")
        if derive_netcdf and format_str != "all" and "netcdf" not in format_str:
            logger.warning("⚠️  --derive-netcdf flag requires NetCDF output format")
            logger.warning("   Either add 'netcdf' to --format or use --format all")
            logger.warning("   Ignoring --derive-netcdf flag.")
            derive_netcdf = False

        # Format progress header using new utility
        _format_progress_header(
            operation="Cruise Schedule Generation",
            config_file=config_file,
            format=format_str,
            leg=getattr(args, "leg", None),
            derive_netcdf=derive_netcdf,
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "schedule")

        # Call API function instead of core directly
        logger.info("Generating cruise schedule and timeline...")
        timeline, generated_files = cruiseplan.schedule(**api_params)

        # Convert API response to CLI format using bridge utility
        api_response = (timeline, generated_files)
        cli_response = _convert_api_response_to_cli(api_response, "schedule")

        # Collect generated files using utility
        all_generated_files = _collect_generated_files(
            cli_response,
            base_patterns=[
                "*_schedule.*",
                "*_timeline.*",
                "*_map.png",
                "*_catalog.kml",
            ],
        )

        if cli_response.get("success", True) and timeline:
            # Show timeline summary using utility function
            total_duration_hours = (
                sum(activity.get("duration_minutes", 0) for activity in timeline) / 60.0
            )

            timeline_summary = _format_timeline_summary(timeline, total_duration_hours)
            logger.info(f"\n{timeline_summary}")

            # Format success message using new utility
            _format_success_message("schedule generation", all_generated_files)
        else:
            errors = cli_response.get("errors", ["Schedule generation failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            sys.exit(1)

    except CLIError as e:
        _format_error_message("schedule", e)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        _format_error_message(
            "schedule",
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
