"""
Unified configuration processing command.

This module implements the 'cruiseplan process' command that combines
enrichment, validation, and map generation into a single workflow.
This is the main command users should use for processing cruise configurations.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from cruiseplan.cli.utils import (
    CLIError,
    count_individual_warnings,
    load_cruise_with_pretty_warnings,
    setup_logging,
    validate_input_file,
    validate_output_path,
)
from cruiseplan.core.validation import enrich_configuration, validate_configuration_file

logger = logging.getLogger(__name__)


def run_enrichment(
    args: argparse.Namespace, config_file: Path, output_path: Optional[Path] = None
) -> Path:
    """
    Run configuration enrichment step.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    config_file : Path
        Input configuration file
    output_path : Path, optional
        Specific output path for enriched file

    Returns
    -------
    Path
        Path to enriched configuration file
    """
    logger.info("🔄 Step 1: Configuration Enrichment")
    logger.info("-" * 40)

    # Determine output path for enriched file
    if output_path:
        enriched_path = output_path
    else:
        output_dir = validate_output_path(output_dir=args.output_dir)
        # Use --output base filename if provided, otherwise use input filename
        base_name = getattr(args, "output", config_file.stem)
        enriched_path = output_dir / f"{base_name}_enriched.yaml"

    logger.info(f"Input file: {config_file}")
    logger.info(f"Enriched file: {enriched_path}")

    # Determine enrichment options (smart defaults with granular control)
    add_depths = not getattr(
        args, "no_depths", False
    )  # Default enabled unless --no-depths
    add_coords = not getattr(
        args, "no_coords", False
    )  # Default enabled unless --no-coords
    expand_sections = not getattr(
        args, "no_sections", False
    )  # Default enabled unless --no-sections
    expand_ports = not getattr(
        args, "no_ports", False
    )  # Default enabled unless --no-ports

    # Call core enrichment function with smart defaults
    summary = enrich_configuration(
        config_path=config_file,
        add_depths=add_depths,
        add_coords=add_coords,
        expand_sections=expand_sections,
        expand_ports=expand_ports,
        bathymetry_source=args.bathy_source,
        bathymetry_dir=str(args.bathy_dir),
        coord_format="dmm",  # Fixed to dmm format
        output_path=enriched_path,
    )

    # Report enrichment results
    total_enriched = (
        summary["stations_with_depths_added"]
        + summary["stations_with_coords_added"]
        + summary.get("sections_expanded", 0)
        + summary.get("ports_expanded", 0)
    )

    if summary["stations_with_depths_added"] > 0:
        logger.info(
            f"✓ Added depths to {summary['stations_with_depths_added']} stations"
        )

    if summary["stations_with_coords_added"] > 0:
        logger.info(
            f"✓ Added coordinate fields to {summary['stations_with_coords_added']} stations"
        )

    if summary.get("sections_expanded", 0) > 0:
        logger.info(
            f"✓ Expanded {summary['sections_expanded']} CTD sections into {summary.get('stations_from_expansion', 0)} stations"
        )

    if summary.get("ports_expanded", 0) > 0:
        logger.info(f"✓ Expanded {summary['ports_expanded']} global port references")

    if summary.get("defaults_added", 0) > 0:
        logger.info(
            f"✓ Added {summary['defaults_added']} missing required fields with defaults"
        )

    if summary.get("station_defaults_added", 0) > 0:
        logger.info(
            f"✓ Added {summary['station_defaults_added']} missing station defaults (e.g., mooring durations)"
        )

    if total_enriched > 0:
        logger.info(f"✅ Enrichment complete! Total enhancements: {total_enriched}")
    else:
        logger.info("ℹ️ No enhancements needed - configuration is already complete")

    return enriched_path


def run_validation(args: argparse.Namespace, config_file: Path) -> bool:
    """
    Run configuration validation step.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    config_file : Path
        Configuration file to validate

    Returns
    -------
    bool
        True if validation passed, False if failed
    """
    logger.info("")
    logger.info("🔍 Step 2: Configuration Validation")
    logger.info("-" * 40)

    # Determine validation options
    check_depths = not getattr(
        args, "no_depth_check", False
    )  # Default enabled unless --no-depth-check

    # Call core validation function
    success, errors, warnings = validate_configuration_file(
        config_path=config_file,
        check_depths=check_depths,
        tolerance=args.tolerance,
        bathymetry_source=args.bathy_source,
        bathymetry_dir=str(args.bathy_dir),
        strict=args.strict,
    )

    # Report validation results
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
        return True
    elif success and warnings:
        warning_count = count_individual_warnings(warnings)
        logger.info(f"✅ Validation passed with {warning_count} warnings")
        return True
    else:
        logger.error(f"❌ Validation failed with {len(errors)} errors")
        if warnings:
            warning_count = count_individual_warnings(warnings)
            logger.error(f"   and {warning_count} additional warnings")
        return False


def run_map_generation(args: argparse.Namespace, config_file: Path) -> bool:
    """
    Run map generation step.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    config_file : Path
        Configuration file to generate maps from

    Returns
    -------
    bool
        True if map generation succeeded, False if failed
    """
    logger.info("")
    logger.info("🗺️ Step 3: Map Generation")
    logger.info("-" * 40)

    try:
        # Load cruise configuration
        cruise = load_cruise_with_pretty_warnings(config_file)

        # Parse format selection
        formats = []
        if hasattr(args, "format") and args.format:
            if args.format == "all":
                formats = ["png", "kml"]
            else:
                formats = args.format.split(",")
        else:
            # Default formats
            formats = ["png", "kml"]

        # Ensure output directory exists
        output_dir = validate_output_path(output_dir=args.output_dir)

        # Determine base filename (use --output if provided, otherwise cruise name)
        if hasattr(args, "output") and args.output:
            base_name = args.output
        else:
            base_name = cruise.config.cruise_name.replace(" ", "_").replace("/", "-")

        generated_files = []

        # Generate PNG map if requested
        if "png" in formats:
            png_output_file = output_dir / f"{base_name}_map.png"

            logger.info(f"Generating PNG map: {png_output_file}")
            logger.info(f"Bathymetry source: {args.bathy_source}")

            from cruiseplan.output.map_generator import generate_map_from_yaml

            png_result = generate_map_from_yaml(
                cruise,
                output_file=png_output_file,
                bathymetry_source=args.bathy_source,
                bathymetry_stride=getattr(args, "bathy_stride", 10),
                bathymetry_dir=str(args.bathy_dir),
                show_plot=False,  # Never show plot in batch processing
                figsize=getattr(args, "figsize", (12, 8)),
                include_ports=False,  # Focus on scientific operations
            )

            if not png_result:
                logger.error("❌ PNG map generation failed")
                return False

            generated_files.append(("PNG map", png_result))
            logger.info(f"✅ PNG map generated: {png_result}")

        # Generate KML catalog if requested
        if "kml" in formats:
            kml_output_file = output_dir / f"{base_name}_catalog.kml"

            logger.info(f"Generating KML catalog: {kml_output_file}")

            from cruiseplan.output.kml_generator import generate_kml_catalog

            kml_result = generate_kml_catalog(cruise.config, kml_output_file)

            if not kml_result:
                logger.error("❌ KML catalog generation failed")
                return False

            generated_files.append(("KML catalog", kml_result))
            logger.info(f"✅ KML catalog generated: {kml_result}")

        logger.info("✅ Map generation complete!")
        for file_type, file_path in generated_files:
            logger.info(f"📁 {file_type}: {file_path}")

        # Print operation statistics
        station_count = 0
        mooring_count = 0

        if hasattr(cruise, "station_registry") and cruise.station_registry:
            for station in cruise.station_registry.values():
                operation_type = getattr(station, "operation_type", "station")
                if operation_type == "mooring":
                    mooring_count += 1
                else:
                    station_count += 1

        if hasattr(cruise, "mooring_registry") and cruise.mooring_registry:
            mooring_count += len(cruise.mooring_registry)

        transit_count = (
            len(cruise.transit_registry)
            if hasattr(cruise, "transit_registry") and cruise.transit_registry
            else 0
        )
        area_count = (
            len(cruise.area_registry)
            if hasattr(cruise, "area_registry") and cruise.area_registry
            else 0
        )

        logger.info("📊 Operations mapped:")
        logger.info(f"   📍 Stations: {station_count}")
        logger.info(f"   ⚓ Moorings: {mooring_count}")
        logger.info(f"   🚢 Transits: {transit_count}")
        logger.info(f"   📐 Areas: {area_count}")

        return True

    except Exception as e:
        logger.error(f"❌ Map generation failed: {e}")
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return False


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for unified process command.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments
    """
    try:
        # Setup logging
        setup_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Handle legacy argument deprecation warnings
        if hasattr(args, "bathy_source_legacy") and args.bathy_source_legacy:
            logger.warning(
                "⚠️  WARNING: '--bathymetry-source' is deprecated. Use '--bathy-source' instead."
            )
            args.bathy_source = args.bathy_source_legacy

        if hasattr(args, "bathy_dir_legacy") and args.bathy_dir_legacy:
            logger.warning(
                "⚠️  WARNING: '--bathymetry-dir' is deprecated. Use '--bathy-dir' instead."
            )
            args.bathy_dir = args.bathy_dir_legacy

        if hasattr(args, "bathy_stride_legacy") and args.bathy_stride_legacy:
            logger.warning(
                "⚠️  WARNING: '--bathymetry-stride' is deprecated. Use '--bathy-stride' instead."
            )
            args.bathy_stride = args.bathy_stride_legacy

        if hasattr(args, "coord_format_legacy") and args.coord_format_legacy:
            logger.warning(
                "⚠️  WARNING: '--coord-format' is deprecated. Coordinate format is now fixed to DMM."
            )

        # Validate input file
        config_file = validate_input_file(args.config_file)

        # Parse processing mode flags
        only_enrich = getattr(args, "only_enrich", False)
        only_validate = getattr(args, "only_validate", False)
        only_map = getattr(args, "only_map", False)
        no_enrich = getattr(args, "no_enrich", False)
        no_validate = getattr(args, "no_validate", False)
        no_map = getattr(args, "no_map", False)

        # Parse format options
        map_formats = []
        if hasattr(args, "format") and args.format:
            if args.format == "all":
                map_formats = ["png", "kml"]
            else:
                map_formats = args.format.split(",")

        # Validate mode combinations
        exclusive_modes = [only_enrich, only_validate, only_map]
        if sum(exclusive_modes) > 1:
            raise CLIError("Cannot specify multiple --only-* flags together")

        if only_enrich and no_enrich:
            raise CLIError("Cannot specify both --only-enrich and --no-enrich")
        if only_validate and no_validate:
            raise CLIError("Cannot specify both --only-validate and --no-validate")
        if only_map and no_map:
            raise CLIError("Cannot specify both --only-map and --no-map")

        # Validate format conflicts
        if no_map and map_formats:
            raise CLIError(
                "Cannot specify --no-map with --format (map formats requested but mapping disabled)"
            )

        if only_enrich and map_formats:
            raise CLIError(
                "Cannot specify --only-enrich with --format (enrichment mode doesn't generate maps)"
            )

        if only_validate and map_formats:
            raise CLIError(
                "Cannot specify --only-validate with --format (validation mode doesn't generate maps)"
            )

        # Validate figsize is only used with PNG format
        if hasattr(args, "figsize") and args.figsize != [12, 8]:  # Non-default figsize
            if not map_formats or "png" not in map_formats:
                logger.warning(
                    "⚠️  --figsize specified but PNG format not requested - figsize will be ignored"
                )

        logger.info("=" * 60)
        logger.info("🌊 CRUISEPLAN UNIFIED PROCESSOR")
        logger.info("=" * 60)
        logger.info(f"Input configuration: {config_file}")

        # Determine processing steps based on flags
        if only_enrich:
            logger.info("Mode: Enrichment only")
            steps = ["enrich"]
        elif only_validate:
            logger.info("Mode: Validation only")
            steps = ["validate"]
        elif only_map:
            logger.info("Mode: Map generation only")
            steps = ["map"]
        else:
            # Full processing mode with selective disabling
            logger.info("Mode: Full processing")
            steps = []
            if not no_enrich:
                steps.append("enrich")
            if not no_validate:
                steps.append("validate")
            if not no_map:
                steps.append("map")

            if not steps:
                raise CLIError("All processing steps disabled - nothing to do")

        logger.info(f"Processing steps: {' → '.join(steps)}")
        logger.info("")

        # Track processing state
        current_config = config_file
        enrichment_success = True
        validation_success = True
        map_success = True

        # Step 1: Enrichment (if requested)
        if "enrich" in steps:
            try:
                current_config = run_enrichment(args, current_config)
            except ValidationError as e:
                logger.error("❌ Enrichment failed due to validation errors:")
                # Use same detailed validation error formatting as enrich.py
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    msg = error["msg"]
                    logger.error(f"  • {field_path}: {msg}")
                enrichment_success = False
            except Exception as e:
                logger.error(f"❌ Enrichment failed: {e}")
                enrichment_success = False

        # Step 2: Validation (if requested and enrichment succeeded)
        if "validate" in steps and enrichment_success:
            validation_success = run_validation(args, current_config)

        # Step 3: Map generation (if requested and previous steps succeeded)
        if "map" in steps and enrichment_success and validation_success:
            map_success = run_map_generation(args, current_config)

        # Final summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("🏁 PROCESSING SUMMARY")
        logger.info("=" * 60)

        if "enrich" in steps:
            status = "✅ PASSED" if enrichment_success else "❌ FAILED"
            logger.info(f"Enrichment: {status}")

        if "validate" in steps:
            status = "✅ PASSED" if validation_success else "❌ FAILED"
            logger.info(f"Validation: {status}")

        if "map" in steps:
            status = "✅ PASSED" if map_success else "❌ FAILED"
            logger.info(f"Map Generation: {status}")

        # Overall result
        overall_success = enrichment_success and validation_success and map_success

        if overall_success:
            logger.info("")
            logger.info("🎉 All processing steps completed successfully!")
            if current_config != config_file:
                logger.info(f"📁 Processed configuration: {current_config}")
        else:
            logger.error("")
            logger.error("❌ One or more processing steps failed")
            sys.exit(1)

    except CLIError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
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

    # Processing mode flags (mutually exclusive --only-* modes)
    parser.add_argument(
        "--only-enrich", action="store_true", help="Only run enrichment step"
    )
    parser.add_argument(
        "--only-validate",
        action="store_true",
        help="Only run validation step (no enrichment or map)",
    )
    parser.add_argument(
        "--only-map",
        action="store_true",
        help="Only run map generation (no enrichment or validation)",
    )

    # Processing step control flags (for full processing mode)
    parser.add_argument("--no-enrich", action="store_true", help="Skip enrichment step")
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip validation step"
    )
    parser.add_argument(
        "--no-map", action="store_true", help="Skip map generation step"
    )

    # Enrichment control flags (smart defaults - all enabled unless disabled)
    parser.add_argument(
        "--no-depths",
        action="store_true",
        help="Skip adding missing depths (default: depths added)",
    )
    parser.add_argument(
        "--no-coords",
        action="store_true",
        help="Skip adding coordinate fields (default: coords added)",
    )
    parser.add_argument(
        "--no-sections",
        action="store_true",
        help="Skip expanding CTD sections (default: sections expanded)",
    )
    parser.add_argument(
        "--no-ports",
        action="store_true",
        help="Skip expanding port references (default: ports expanded)",
    )

    # Validation options
    parser.add_argument(
        "--no-depth-check",
        action="store_true",
        help="Skip depth accuracy checking (default: depths checked)",
    )
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict validation mode"
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference tolerance in percent (default: 10.0)",
    )

    # Map generation options
    parser.add_argument(
        "--format", default="all", help="Map output formats: png,kml,all (default: all)"
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        type=float,
        default=[12, 8],
        help="Figure size for PNG maps (width height, default: 12 8)",
    )

    # Output and bathymetry options
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory (default: data)",
    )
    parser.add_argument(
        "--output", type=str, help="Base filename for outputs (without extension)"
    )
    parser.add_argument(
        "--bathy-source",
        default="etopo2022",
        choices=["etopo2022", "gebco2025"],
        help="Bathymetry dataset (default: etopo2022)",
    )
    parser.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing bathymetry data (default: data)",
    )
    parser.add_argument(
        "--bathy-stride",
        type=int,
        default=10,
        help="Bathymetry contour stride (default: 10)",
    )

    # Legacy argument support with deprecation warnings
    parser.add_argument(
        "--bathymetry-source",
        dest="bathy_source_legacy",
        choices=["etopo2022", "gebco2025"],
        help="[DEPRECATED] Use --bathy-source instead",
    )
    parser.add_argument(
        "--bathymetry-dir",
        type=Path,
        dest="bathy_dir_legacy",
        help="[DEPRECATED] Use --bathy-dir instead",
    )
    parser.add_argument(
        "--bathymetry-stride",
        type=int,
        dest="bathy_stride_legacy",
        help="[DEPRECATED] Use --bathy-stride instead",
    )
    parser.add_argument(
        "--coord-format",
        dest="coord_format_legacy",
        choices=["dmm", "dms"],
        help="[DEPRECATED] Coordinate format fixed to DMM",
    )

    # General options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Enable quiet mode")

    args = parser.parse_args()
    main(args)
