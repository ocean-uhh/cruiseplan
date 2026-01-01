"""
Configuration enrichment command.

This module implements the 'cruiseplan enrich' command for adding missing
data to existing YAML configuration files.

Uses the API-first architecture pattern with proper separation of concerns:
- CLI layer handles argument parsing and output formatting
- API layer (cruiseplan.__init__) contains business logic
- Utility functions provide consistent formatting and error handling
"""

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

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


def _format_validation_errors(errors: list) -> None:
    """Format detailed validation errors using existing logic."""
    for error in errors:
        field_path = ".".join(str(loc) for loc in error["loc"])
        field_type = error["type"]
        input_value = error.get("input", "")
        msg = error["msg"]

        # Extract entity type and name for better formatting
        if field_path.startswith("stations."):
            parts = field_path.split(".")
            if len(parts) > 1 and parts[1].isdigit():
                logger.error("- Stations:")
                if field_type == "missing":
                    field_name = parts[2] if len(parts) > 2 else "field"
                    logger.error(
                        f"    Station field missing: {field_name} (required field in yaml)"
                    )
                else:
                    logger.error(
                        f"    STN_{int(parts[1])+1:02d} value error: {input_value}"
                    )
                    logger.error(f"    {msg}")
            else:
                logger.error(f"- Stations: {msg}")
        elif field_path.startswith("moorings."):
            parts = field_path.split(".")
            if len(parts) > 1 and parts[1].isdigit():
                logger.error("- Moorings:")
                if field_type == "missing":
                    field_name = parts[2] if len(parts) > 2 else "field"
                    logger.error(
                        f"    Mooring field missing: {field_name} (required field in yaml)"
                    )
                else:
                    logger.error(
                        f"    Mooring_{int(parts[1])+1:02d} value error: {input_value}"
                    )
                    logger.error(f"    {msg}")
            else:
                logger.error(f"- Moorings: {msg}")
        elif field_path.startswith("transits."):
            parts = field_path.split(".")
            if len(parts) > 1 and parts[1].isdigit():
                logger.error("- Transits:")
                if field_type == "missing":
                    field_name = parts[2] if len(parts) > 2 else "field"
                    logger.error(
                        f"    Transit field missing: {field_name} (required field in yaml)"
                    )
                else:
                    logger.error(
                        f"    Transit_{int(parts[1])+1:02d} value error: {input_value}"
                    )
                    logger.error(f"    {msg}")
            else:
                logger.error(f"- Transits: {msg}")
        elif field_path.startswith("legs."):
            parts = field_path.split(".")
            if len(parts) > 1 and parts[1].isdigit():
                logger.error("- Legs:")
                if field_type == "missing":
                    field_name = parts[2] if len(parts) > 2 else "field"
                    logger.error(
                        f"    Leg field missing: {field_name} (required field in yaml)"
                    )
                else:
                    logger.error(
                        f"    Leg_{int(parts[1])+1:02d} value error: {input_value}"
                    )
                    logger.error(f"    {msg}")
            else:
                logger.error(f"- Legs: {msg}")
        elif field_path.startswith("areas."):
            parts = field_path.split(".")
            if len(parts) > 1 and parts[1].isdigit():
                logger.error("- Areas:")
                if field_type == "missing":
                    field_name = parts[2] if len(parts) > 2 else "field"
                    logger.error(
                        f"    Area field missing: {field_name} (required field in yaml)"
                    )
                else:
                    logger.error(
                        f"    Area_{int(parts[1])+1:02d} value error: {input_value}"
                    )
                    logger.error(f"    {msg}")
            else:
                logger.error(f"- Areas: {msg}")
        else:
            logger.error(f"- {field_path}: {msg}")


def _show_enrichment_summary(summary: dict, args: argparse.Namespace) -> None:
    """Show enrichment operation summary using existing detailed logic."""
    # Calculate total enriched items
    total_enriched = (
        summary.get("stations_with_depths_added", 0)
        + summary.get("stations_with_coords_added", 0)
        + summary.get("sections_expanded", 0)
        + summary.get("ports_expanded", 0)
    )

    # Show specific operation results
    if (
        getattr(args, "add_depths", False)
        and summary.get("stations_with_depths_added", 0) > 0
    ):
        logger.info(
            f"✓ Added depths to {summary['stations_with_depths_added']} stations"
        )

    if (
        getattr(args, "add_coords", False)
        and summary.get("stations_with_coords_added", 0) > 0
    ):
        logger.info(
            f"✓ Added coordinate fields to {summary['stations_with_coords_added']} stations"
        )

    if (
        getattr(args, "expand_sections", False)
        and summary.get("sections_expanded", 0) > 0
    ):
        logger.info(
            f"✓ Expanded {summary['sections_expanded']} CTD sections into {summary.get('stations_from_expansion', 0)} stations"
        )

    if getattr(args, "expand_ports", False) and summary.get("ports_expanded", 0) > 0:
        logger.info(f"✓ Expanded {summary['ports_expanded']} global port references")

    if summary.get("defaults_added", 0) > 0:
        logger.info(
            f"✓ Added {summary['defaults_added']} missing required fields with defaults"
        )

    if summary.get("station_defaults_added", 0) > 0:
        logger.info(
            f"✓ Added {summary['station_defaults_added']} missing station defaults (e.g., mooring durations)"
        )

    # Show final summary
    if total_enriched > 0:
        logger.info(f"\n✅ Total enhancements: {total_enriched}")
    else:
        logger.info("ℹ️ No enhancements were needed - configuration is already complete")


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for enrich command using API-first architecture.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Setup logging using new utility
        _setup_cli_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Handle legacy --output-file parameter
        if hasattr(args, "output_file") and args.output_file:
            logger.warning(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )

        # Validate input file using new utility
        config_file = _validate_config_file(args.config_file)

        # Format progress header using new utility
        _format_progress_header(
            operation="Configuration Enrichment",
            config_file=config_file,
            add_depths=getattr(args, "add_depths", False),
            add_coords=getattr(args, "add_coords", False),
            expand_sections=getattr(args, "expand_sections", False),
            expand_ports=getattr(args, "expand_ports", False),
        )

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "enrich")

        # Call API function instead of core directly
        logger.info("Processing configuration...")
        api_response = cruiseplan.enrich(**api_params)

        # Convert API response to CLI format using bridge utility
        cli_response = _convert_api_response_to_cli(api_response, "enrich")

        # Collect generated files using utility
        generated_files = _collect_generated_files(
            cli_response, base_patterns=["*_enriched.yaml"]
        )

        if cli_response.get("success", True) and generated_files:
            # Format success message using new utility
            _format_success_message("configuration enrichment", generated_files)

            # Show operation summary if available in response data
            if cli_response.get("data"):
                summary = cli_response["data"]
                if isinstance(summary, dict):
                    _show_enrichment_summary(summary, args)
        else:
            errors = cli_response.get("errors", ["Enrichment failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            sys.exit(1)

    except CLIError as e:
        _format_error_message("enrich", e)
        sys.exit(1)

    except ValidationError as e:
        # Handle ValidationError with existing detailed formatting
        error_count = len(e.errors())
        plural = "error" if error_count == 1 else "errors"
        logger.error(f"❌ CruiseConfig: {error_count} validation {plural}")

        # Use existing detailed validation error formatting
        _format_validation_errors(e.errors())
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        _format_error_message(
            "enrich",
            e,
            [
                "Check configuration file syntax",
                "Verify bathymetry data availability",
                "Check output directory permissions",
            ],
        )
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(description="Enrich cruise configurations")
    parser.add_argument(
        "-c", "--config-file", type=Path, required=True, help="Input YAML file"
    )
    parser.add_argument("--add-depths", action="store_true", help="Add missing depths")
    parser.add_argument(
        "--add-coords", action="store_true", help="Add coordinate fields"
    )
    parser.add_argument(
        "--expand-sections", action="store_true", help="Expand CTD sections"
    )
    parser.add_argument(
        "--expand-ports", action="store_true", help="Expand global port references"
    )
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."))
    parser.add_argument(
        "--output", type=str, help="Base filename for output (without extension)"
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="[DEPRECATED] Use --output and --output-dir instead",
    )
    parser.add_argument("--bathymetry-source", default="etopo2022")
    parser.add_argument("--bathymetry-dir", type=Path, default=Path("data"))
    parser.add_argument("--coord-format", default="ddm", choices=["ddm", "dms"])

    args = parser.parse_args()
    main(args)
