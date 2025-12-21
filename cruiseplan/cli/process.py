"""
Unified configuration processing command - Wrapper/Orchestrator Pattern.

This module implements the 'cruiseplan process' command as a wrapper that
orchestrates individual enrich, validate, and map commands with smart defaults
and predictable file naming.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from cruiseplan.cli.utils import (
    CLIError,
    setup_logging,
    validate_input_file,
    validate_output_path,
)

logger = logging.getLogger(__name__)


def determine_steps(args: argparse.Namespace) -> List[str]:
    """
    Determine which processing steps to run based on arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments

    Returns
    -------
    List[str]
        List of steps to run: ['enrich', 'validate', 'map']
    """
    # Parse processing mode flags
    only_enrich = getattr(args, "only_enrich", False)
    only_validate = getattr(args, "only_validate", False)
    only_map = getattr(args, "only_map", False)
    no_enrich = getattr(args, "no_enrich", False)
    no_validate = getattr(args, "no_validate", False)
    no_map = getattr(args, "no_map", False)

    # Validate mode combinations first
    exclusive_modes = [only_enrich, only_validate, only_map]
    if sum(exclusive_modes) > 1:
        raise CLIError("Cannot specify multiple --only-* flags together")

    if only_enrich and no_enrich:
        raise CLIError("Cannot specify both --only-enrich and --no-enrich")
    if only_validate and no_validate:
        raise CLIError("Cannot specify both --only-validate and --no-validate")
    if only_map and no_map:
        raise CLIError("Cannot specify both --only-map and --no-map")

    # Parse format options for map step validation only when needed
    map_formats = []
    format_was_explicitly_set = (
        hasattr(args, "format") and args.format and args.format != "all"
    )  # Check if user explicitly set format

    # Only parse formats when map generation is possible
    if not only_enrich and not only_validate and not no_map:
        # We will be doing map generation, so parse formats
        if hasattr(args, "format") and args.format:
            if args.format == "all":
                map_formats = ["png", "kml"]
            else:
                map_formats = args.format.split(",")
    elif hasattr(args, "format") and args.format != "all":
        # User explicitly set format but we won't be generating maps
        if args.format == "all":
            map_formats = ["png", "kml"]
        else:
            map_formats = args.format.split(",")

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

    # Determine processing steps based on flags
    if only_enrich:
        return ["enrich"]
    elif only_validate:
        return ["validate"]
    elif only_map:
        return ["map"]
    else:
        # Full processing mode with selective disabling
        steps = []
        if not no_enrich:
            steps.append("enrich")
        if not no_validate:
            steps.append("validate")
        if not no_map:
            steps.append("map")

        if not steps:
            raise CLIError("All processing steps disabled - nothing to do")

        return steps


def create_enrich_args(
    args: argparse.Namespace, input_config: Path, output_config: Path
) -> argparse.Namespace:
    """
    Create arguments for enrich command from process arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Process command arguments
    input_config : Path
        Input configuration file
    output_config : Path
        Output enriched configuration file

    Returns
    -------
    argparse.Namespace
        Arguments for enrich command
    """
    enrich_args = argparse.Namespace()

    # Required arguments
    enrich_args.config_file = input_config
    enrich_args.output_dir = output_config.parent
    enrich_args.output = output_config.stem.replace(
        "_enriched", ""
    )  # Remove suffix to get base name
    enrich_args.output_file = None  # Don't use legacy parameter

    # Enrichment options (smart defaults with granular control)
    enrich_args.add_depths = not getattr(args, "no_depths", False)
    enrich_args.add_coords = not getattr(args, "no_coords", False)
    enrich_args.expand_sections = not getattr(args, "no_sections", False)
    enrich_args.expand_ports = not getattr(args, "no_ports", False)

    # Bathymetry options
    enrich_args.bathymetry_source = args.bathy_source
    enrich_args.bathymetry_dir = args.bathy_dir
    enrich_args.coord_format = "dmm"  # Fixed format

    # General options
    enrich_args.verbose = getattr(args, "verbose", False)
    enrich_args.quiet = getattr(args, "quiet", False)

    return enrich_args


def create_validate_args(
    args: argparse.Namespace, config_file: Path
) -> argparse.Namespace:
    """
    Create arguments for validate command from process arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Process command arguments
    config_file : Path
        Configuration file to validate

    Returns
    -------
    argparse.Namespace
        Arguments for validate command
    """
    validate_args = argparse.Namespace()

    # Required arguments
    validate_args.config_file = config_file

    # Validation options
    validate_args.check_depths = not getattr(args, "no_depth_check", False)
    validate_args.strict = getattr(args, "strict", False)
    validate_args.tolerance = getattr(args, "tolerance", 10.0)
    validate_args.warnings_only = False

    # Bathymetry options
    validate_args.bathymetry_source = args.bathy_source
    validate_args.bathymetry_dir = args.bathy_dir

    # General options
    validate_args.verbose = getattr(args, "verbose", False)
    validate_args.quiet = getattr(args, "quiet", False)

    return validate_args


def create_map_args(
    args: argparse.Namespace, config_file: Path, base_name: str
) -> argparse.Namespace:
    """
    Create arguments for map command from process arguments.

    Parameters
    ----------
    args : argparse.Namespace
        Process command arguments
    config_file : Path
        Configuration file to generate maps from
    base_name : str
        Base filename for output maps

    Returns
    -------
    argparse.Namespace
        Arguments for map command
    """
    map_args = argparse.Namespace()

    # Required arguments
    map_args.config_file = config_file
    map_args.output_dir = args.output_dir
    map_args.output = base_name
    map_args.output_file = None  # Don't use legacy parameter

    # Map options
    if hasattr(args, "format") and args.format:
        map_args.format = args.format
    else:
        map_args.format = "all"

    map_args.figsize = getattr(args, "figsize", [12, 8])
    map_args.show_plot = False  # Never show plot in batch processing

    # Bathymetry options
    map_args.bathymetry_source = args.bathy_source
    map_args.bathymetry_dir = args.bathy_dir
    map_args.bathymetry_stride = getattr(args, "bathy_stride", 10)

    # General options
    map_args.verbose = getattr(args, "verbose", False)
    map_args.quiet = getattr(args, "quiet", False)

    return map_args


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for unified process command (wrapper pattern).

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

        # Determine processing steps
        steps = determine_steps(args)

        # Determine output directory and base filename
        output_dir = validate_output_path(output_dir=args.output_dir)
        base_name = args.output if args.output else config_file.stem

        logger.info("=" * 60)
        logger.info("🌊 CRUISEPLAN UNIFIED PROCESSOR")
        logger.info("=" * 60)
        logger.info(f"Input configuration: {config_file}")
        logger.info(f"Base filename: {base_name}")
        logger.info(f"Processing steps: {' → '.join(steps)}")
        logger.info("")

        # Track current config file through pipeline
        current_config = config_file

        # Step 1: Enrichment (if requested)
        if "enrich" in steps:
            logger.info("🔄 Step 1: Configuration Enrichment")
            logger.info("-" * 40)

            # Predictable enriched file path
            enriched_config = output_dir / f"{base_name}_enriched.yaml"

            # Create enrich arguments and call enrich main
            enrich_args = create_enrich_args(args, current_config, enriched_config)

            from cruiseplan.cli.enrich import main as enrich_main

            enrich_main(enrich_args)

            # Update current config for next step
            current_config = enriched_config
            logger.info(f"✅ Enriched configuration: {enriched_config}")
            logger.info("")

        # Step 2: Validation (if requested)
        if "validate" in steps:
            logger.info("🔍 Step 2: Configuration Validation")
            logger.info("-" * 40)

            # Create validate arguments and call validate main
            validate_args = create_validate_args(args, current_config)

            from cruiseplan.cli.validate import main as validate_main

            validate_main(validate_args)

            logger.info("")

        # Step 3: Map Generation (if requested)
        if "map" in steps:
            logger.info("🗺️ Step 3: Map Generation")
            logger.info("-" * 40)

            # Create map arguments and call map main
            map_args = create_map_args(args, current_config, base_name)

            from cruiseplan.cli.map import main as map_main

            result = map_main(map_args)

            if result != 0:
                logger.error("❌ Map generation failed")
                sys.exit(1)

            logger.info("")

        # Final summary
        logger.info("=" * 60)
        logger.info("🏁 PROCESSING SUMMARY")
        logger.info("=" * 60)

        for step in steps:
            logger.info(f"{step.title()}: ✅ COMPLETED")

        logger.info("")
        logger.info("🎉 All processing steps completed successfully!")

        if "enrich" in steps:
            enriched_config = output_dir / f"{base_name}_enriched.yaml"
            logger.info(f"📁 Enriched configuration: {enriched_config}")

        if "map" in steps:
            # Show generated map files
            formats = getattr(args, "format", "all")
            if formats == "all":
                formats = "png,kml"

            for fmt in formats.split(","):
                if fmt == "png":
                    png_file = output_dir / f"{base_name}_map.png"
                    logger.info(f"📁 PNG map: {png_file}")
                elif fmt == "kml":
                    kml_file = output_dir / f"{base_name}_catalog.kml"
                    logger.info(f"📁 KML catalog: {kml_file}")

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
    # Same argument parser as before
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
