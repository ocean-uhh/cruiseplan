"""
Interactive station placement command.

This module implements the 'cruiseplan stations' command for interactive
station placement with PANGAEA background data and bathymetry visualization.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from cruiseplan.cli.cli_utils import (
    CLIError,
    _apply_cli_defaults,
    _handle_deprecated_params,
    _initialize_cli_command,
    format_coordinate_bounds,
    generate_output_filename,
    load_pangaea_campaign_data,
)
from cruiseplan.utils.coordinates import _validate_coordinate_bounds
from cruiseplan.utils.io import validate_input_file, validate_output_directory

# TODO: Remove these error formatters when stations.py is refactored to use API-first approach
# These are legacy CLI formatting functions that won't be needed after refactor
from cruiseplan.utils.output_formatting import (
    _format_cli_error,
    _format_dependency_error,
)

logger = logging.getLogger(__name__)


def determine_coordinate_bounds(
    args: argparse.Namespace, campaign_data: Optional[list] = None
) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Determine coordinate bounds from arguments or PANGAEA data.

    Parameters
    ----------
    args : argparse.Namespace
        Command line arguments
    campaign_data : list, optional
        Loaded PANGAEA campaign data

    Returns
    -------
    Tuple[Tuple[float, float], Tuple[float, float]]
        Tuple of (lat_bounds, lon_bounds) as (min, max) tuples
    """
    # Use explicit bounds if provided
    if args.lat and args.lon:
        lat_bounds = tuple(args.lat)
        lon_bounds = tuple(args.lon)
        logger.info(
            f"Using explicit bounds: {format_coordinate_bounds(lat_bounds, lon_bounds)}"
        )
        return lat_bounds, lon_bounds

    # Try to derive bounds from PANGAEA data
    if campaign_data:
        all_lats = []
        all_lons = []

        for campaign in campaign_data:
            all_lats.extend(campaign.get("latitude", []))
            all_lons.extend(campaign.get("longitude", []))

        if all_lats and all_lons:
            # Add some padding
            lat_padding = (max(all_lats) - min(all_lats)) * 0.1
            lon_padding = (max(all_lons) - min(all_lons)) * 0.1

            lat_bounds = (min(all_lats) - lat_padding, max(all_lats) + lat_padding)
            lon_bounds = (min(all_lons) - lon_padding, max(all_lons) + lon_padding)

            logger.info(
                f"Using bounds from PANGAEA data: {format_coordinate_bounds(lat_bounds, lon_bounds)}"
            )
            return lat_bounds, lon_bounds

    # Fall back to defaults
    lat_bounds = tuple(args.lat) if args.lat else (45.0, 70.0)
    lon_bounds = tuple(args.lon) if args.lon else (-65.0, -5.0)

    logger.info(
        f"Using default bounds: {format_coordinate_bounds(lat_bounds, lon_bounds)}"
    )
    return lat_bounds, lon_bounds


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for interactive station placement using API-first architecture.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments
    """
    try:
        # Handle deprecated parameters
        deprecated_params = {
            "bathy_source_legacy": "bathy_source",
            "bathy_dir_legacy": "bathy_dir",
        }
        _handle_deprecated_params(args, deprecated_params)

        # Apply standard CLI defaults
        _apply_cli_defaults(args)

        # Standardized CLI initialization
        _initialize_cli_command(args, requires_config_file=False)

        # Check for optional dependencies
        try:
            import matplotlib.pyplot  # noqa: F401
        except ImportError:
            raise CLIError(
                "Interactive station picker requires matplotlib. "
                "Install with: pip install matplotlib"
            )

        logger.info("=" * 50)
        logger.info("Interactive Station Picker")
        logger.info("=" * 50)

        # Load PANGAEA campaign data if provided
        campaign_data = None
        if args.pangaea_file:
            pangaea_file = validate_input_file(args.pangaea_file)
            logger.info(f"Loading PANGAEA data from: {pangaea_file}")
            campaign_data = load_pangaea_campaign_data(pangaea_file)
        else:
            logger.info("No PANGAEA data provided - using bathymetry only")

        # Use the requested bathymetry source (or default)
        # The BathymetryManager will handle fallback to mock mode if files aren't available
        optimal_bathymetry_source = getattr(args, "bathy_source", None) or "etopo2022"

        # Determine coordinate bounds
        lat_bounds, lon_bounds = determine_coordinate_bounds(args, campaign_data)

        # Validate coordinate bounds using new utility
        try:
            _validate_coordinate_bounds(list(lat_bounds), list(lon_bounds))
        except ValueError as e:
            raise CLIError(f"Invalid coordinate bounds: {e}")

        # Determine output file (output_file parameter was deprecated)
        output_dir = validate_output_directory(args.output_dir)
        output_filename = "stations.yaml"
        if args.pangaea_file:
            # Generate filename based on PANGAEA file
            output_filename = generate_output_filename(
                args.pangaea_file, "_stations", ".yaml"
            )
        output_path = output_dir / output_filename

        logger.info(f"Output file: {output_path}")
        logger.info(f"Bathymetry source: {optimal_bathymetry_source}")
        resolution_msg = (
            "high resolution (no downsampling)"
            if getattr(args, "high_resolution", False)
            else "standard resolution (10x downsampled)"
        )
        logger.info(f"Bathymetry resolution: {resolution_msg}")

        # Performance warning for GEBCO + high-resolution combination
        if optimal_bathymetry_source == "gebco2025" and getattr(
            args, "high_resolution", False
        ):
            logger.warning("⚠️  PERFORMANCE WARNING:")
            logger.warning(
                "   GEBCO 2025 with high resolution can be very slow for interactive use!"
            )
            logger.warning(
                "   Consider using --bathymetry-source etopo2022 for faster interaction."
            )
            logger.warning(
                "   Reserve GEBCO high-resolution for final detailed planning only."
            )
            logger.warning("")
        logger.info("")

        # Display usage instructions
        logger.info("Interactive Controls:")
        logger.info("  'p' or 'w' - Place point stations (waypoints)")
        logger.info("  'l' or 's' - Draw line transects (survey lines)")
        logger.info("  'a'        - Define area operations")
        logger.info("  'n'        - Navigation mode (pan/zoom)")
        logger.info("  'u'        - Undo last operation")
        logger.info("  'r'        - Remove operation (click to select)")
        logger.info("  'y'        - Save to YAML file")
        logger.info("  'Escape'   - Exit without saving")
        logger.info("")
        logger.info("🎯 Launching interactive station picker...")

        # Import and initialize the interactive picker
        try:
            from cruiseplan.interactive.station_picker import StationPicker

            # Initialize the picker
            bathymetry_stride = 1 if getattr(args, "high_resolution", False) else 10

            picker = StationPicker(
                campaign_data=campaign_data,
                output_file=str(output_path),
                bathymetry_stride=bathymetry_stride,
                bathymetry_source=optimal_bathymetry_source,
                bathymetry_dir=str(getattr(args, "bathy_dir", Path("data"))),
                overwrite=getattr(args, "overwrite", False),
            )

            # Set coordinate bounds
            picker.ax_map.set_xlim(lon_bounds)
            picker.ax_map.set_ylim(lat_bounds)
            picker._update_aspect_ratio()

            # Re-plot bathymetry with correct bounds
            picker._plot_bathymetry()

            # Show the interactive interface (blocking call)
            picker.show()

        except ImportError:
            error_msg = _format_dependency_error(
                "matplotlib", "Interactive station picker", "pip install matplotlib"
            )
            logger.exception(error_msg)
            sys.exit(1)

    except CLIError as e:
        error_msg = _format_cli_error(
            "Interactive station placement",
            e,
            suggestions=[
                "Check coordinate bounds are valid",
                "Verify PANGAEA file format if provided",
                "Ensure matplotlib is installed",
            ],
        )
        logger.exception(error_msg)
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        error_msg = _format_cli_error(
            "Interactive station placement",
            e,
            suggestions=[
                "Check matplotlib installation",
                "Verify bathymetry data availability",
                "Check PANGAEA file format",
                "Run with --verbose for more details",
            ],
        )
        logger.exception(error_msg)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(description="Interactive station placement")
    parser.add_argument(
        "-p", "--pangaea-file", type=Path, help="PANGAEA campaigns pickle file"
    )
    parser.add_argument(
        "--lat", nargs=2, type=float, metavar=("MIN", "MAX"), help="Latitude bounds"
    )
    parser.add_argument(
        "--lon", nargs=2, type=float, metavar=("MIN", "MAX"), help="Longitude bounds"
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=Path("."), help="Output directory"
    )
    parser.add_argument(
        "--bathy-source", choices=["etopo2022", "gebco2025"], default="etopo2022"
    )
    parser.add_argument(
        "--bathy-dir", type=Path, default=Path("data"), help="Bathymetry directory"
    )

    args = parser.parse_args()
    main(args)
