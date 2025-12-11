"""
Configuration enrichment command.

This module implements the 'cruiseplan enrich' command for adding missing
data to existing YAML configuration files.
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

        # Validate that at least one operation is requested
        if not (args.add_depths or args.add_coords):
            logger.error(
                "At least one operation must be specified: --add-depths or --add-coords"
            )
            sys.exit(1)

        # Validate input file
        config_file = validate_input_file(args.config_file)

        # Determine output path
        if args.output_file:
            output_path = validate_output_path(output_file=args.output_file)
        else:
            output_dir = validate_output_path(output_dir=args.output_dir)
            # Generate filename from input file
            output_filename = f"{config_file.stem}_enriched.yaml"
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
            bathymetry_source=args.bathymetry_source,
            coord_format=args.coord_format,
            output_path=output_path,
        )

        # Report results
        total_enriched = (
            summary["stations_with_depths_added"]
            + summary["stations_with_coords_added"]
        )

        if args.add_depths and summary["stations_with_depths_added"] > 0:
            logger.info(
                f"✓ Added depths to {summary['stations_with_depths_added']} stations"
            )

        if args.add_coords and summary["stations_with_coords_added"] > 0:
            logger.info(
                f"✓ Added coordinate fields to {summary['stations_with_coords_added']} stations"
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
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."))
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--bathymetry-source", default="etopo2022")
    parser.add_argument("--coord-format", default="dmm", choices=["dmm", "dms"])

    args = parser.parse_args()
    main(args)
