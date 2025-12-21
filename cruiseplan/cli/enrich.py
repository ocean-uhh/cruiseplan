"""
Configuration enrichment command.

This module implements the 'cruiseplan enrich' command for adding missing
data to existing YAML configuration files.
"""

import argparse
import logging
import sys
from pathlib import Path

from pydantic import ValidationError

from cruiseplan.cli.utils import (
    CLIError,
    setup_logging,
    validate_input_file,
    validate_output_path,
)
from cruiseplan.core.validation import enrich_configuration

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for enrich command.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Setup logging
        setup_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Get expansion flags (optional operations)
        expand_sections = getattr(args, "expand_sections", False)
        expand_ports = getattr(args, "expand_ports", False)

        # Note: At minimum, enrichment will add missing defaults even with no explicit flags

        # Validate input file
        config_file = validate_input_file(args.config_file)

        # Handle legacy --output-file parameter
        if hasattr(args, "output_file") and args.output_file:
            logger.warning(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )
            output_path = validate_output_path(output_file=args.output_file)
        else:
            output_dir = validate_output_path(output_dir=args.output_dir)
            # Use --output base filename if provided, otherwise use input filename
            base_name = getattr(args, "output", config_file.stem)
            output_filename = f"{base_name}_enriched.yaml"
            output_path = output_dir / output_filename

        logger.info("=" * 50)
        logger.info("Configuration Enrichment")
        logger.info("=" * 50)
        logger.info(f"Input file: {config_file}")
        logger.info(f"Output file: {output_path}")
        logger.info("")

        # Call core enrichment function
        logger.info("Processing configuration...")
        summary = enrich_configuration(
            config_path=config_file,
            add_depths=args.add_depths,
            add_coords=args.add_coords,
            expand_sections=getattr(args, "expand_sections", False),
            expand_ports=getattr(args, "expand_ports", False),
            bathymetry_source=args.bathymetry_source,
            bathymetry_dir=str(args.bathymetry_dir),
            coord_format=args.coord_format,
            output_path=output_path,
        )

        # Report results
        total_enriched = (
            summary["stations_with_depths_added"]
            + summary["stations_with_coords_added"]
            + summary.get("sections_expanded", 0)
            + summary.get("ports_expanded", 0)
        )

        if args.add_depths and summary["stations_with_depths_added"] > 0:
            logger.info(
                f"✓ Added depths to {summary['stations_with_depths_added']} stations"
            )

        if args.add_coords and summary["stations_with_coords_added"] > 0:
            logger.info(
                f"✓ Added coordinate fields to {summary['stations_with_coords_added']} stations"
            )

        if expand_sections and summary.get("sections_expanded", 0) > 0:
            logger.info(
                f"✓ Expanded {summary['sections_expanded']} CTD sections into {summary.get('stations_from_expansion', 0)} stations"
            )

        if expand_ports and summary.get("ports_expanded", 0) > 0:
            logger.info(
                f"✓ Expanded {summary['ports_expanded']} global port references"
            )

        if summary.get("defaults_added", 0) > 0:
            logger.info(
                f"✓ Added {summary['defaults_added']} missing required fields with defaults"
            )

        if summary.get("station_defaults_added", 0) > 0:
            logger.info(
                f"✓ Added {summary['station_defaults_added']} missing station defaults (e.g., mooring durations)"
            )

        if total_enriched > 0:
            logger.info("")
            logger.info("✅ Configuration enriched successfully!")
            logger.info(f"Total enhancements: {total_enriched}")
            logger.info(f"Output saved to: {output_path}")
        else:
            logger.info(
                "ℹ️ No enhancements were needed - configuration is already complete"
            )

    except CLIError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)

    except ValidationError as e:
        error_count = len(e.errors())
        plural = "error" if error_count == 1 else "errors"
        logger.error(f"❌ CruiseConfig: {error_count} validation {plural}")

        # Group errors by field prefix for better organization
        for error in e.errors():
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
    parser.add_argument("--coord-format", default="dmm", choices=["dmm", "dms"])

    args = parser.parse_args()
    main(args)
