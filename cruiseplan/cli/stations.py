"""
Interactive station placement command.

This module implements the 'cruiseplan stations' command for interactive
station placement with PANGAEA background data and bathymetry visualization.
"""

import argparse
import logging
import sys
from pathlib import Path

from cruiseplan.cli.utils import (
    CLIError,
    format_coordinate_bounds,
    generate_output_filename,
    setup_logging,
    validate_input_file,
    validate_output_path,
)

logger = logging.getLogger(__name__)


def check_bathymetry_availability(source: str) -> bool:
    """
    Check if bathymetry files are available for the specified source.

    Parameters
    ----------
    source : str
        Bathymetry source ("etopo2022" or "gebco2025")

    Returns
    -------
    bool
        True if bathymetry files are available and valid, False otherwise
    """
    try:
        from cruiseplan.data.bathymetry import BathymetryManager

        # Create a temporary manager to check availability
        manager = BathymetryManager(source=source)
        return not manager._is_mock
    except Exception:
        return False


def determine_bathymetry_source(requested_source: str) -> str:
    """
    Determine the optimal bathymetry source with automatic fallback.

    If the requested source is not available but an alternative is,
    automatically switch to the available source.

    Parameters
    ----------
    requested_source : str
        The user's requested bathymetry source

    Returns
    -------
    str
        The optimal available bathymetry source
    """
    # Check if requested source is available
    if check_bathymetry_availability(requested_source):
        return requested_source

    # Try alternative source
    alternative = "gebco2025" if requested_source == "etopo2022" else "etopo2022"

    if check_bathymetry_availability(alternative):
        logger.info(
            f"📁 Requested {requested_source} not available, "
            f"automatically switching to {alternative}"
        )
        return alternative

    # Neither available - return requested (will trigger mock mode with appropriate warning)
    return requested_source


def load_pangaea_data(pangaea_file: Path) -> list:
    """
    Load PANGAEA campaign data from pickle file.

    Parameters
    ----------
    pangaea_file : Path
        Path to PANGAEA pickle file.

    Returns
    -------
    list
        List of campaign datasets.

    Raises
    ------
    CLIError
        If file cannot be loaded or contains no data.
    """
    try:
        from cruiseplan.data.pangaea import load_campaign_data

        campaign_data = load_campaign_data(pangaea_file)

        if not campaign_data:
            raise CLIError(f"No campaign data found in {pangaea_file}")

        # Summary statistics
        total_points = sum(
            len(campaign.get("latitude", [])) for campaign in campaign_data
        )
        campaigns = [campaign.get("label", "Unknown") for campaign in campaign_data]

        logger.info(
            f"Loaded {len(campaign_data)} campaigns with {total_points} total stations:"
        )
        for campaign in campaigns:
            logger.info(f"  - {campaign}")

        return campaign_data

    except ImportError as e:
        raise CLIError(f"PANGAEA functionality not available: {e}")
    except Exception as e:
        raise CLIError(f"Error loading PANGAEA data: {e}")


def determine_coordinate_bounds(
    args: argparse.Namespace, campaign_data: list = None
) -> tuple:
    """
    Determine coordinate bounds from arguments or PANGAEA data.

    Args:
        args: Command line arguments
        campaign_data: Loaded PANGAEA campaign data

    Returns
    -------
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
    Main entry point for interactive station placement.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Setup logging
        setup_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Check for optional dependencies
        try:
            import matplotlib.pyplot as plt
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
            campaign_data = load_pangaea_data(pangaea_file)
        else:
            logger.info("No PANGAEA data provided - using bathymetry only")

        # Determine optimal bathymetry source (with automatic fallback)
        optimal_bathymetry_source = determine_bathymetry_source(args.bathymetry_source)

        # Determine coordinate bounds
        lat_bounds, lon_bounds = determine_coordinate_bounds(args, campaign_data)

        # Validate bounds
        if not (-90 <= lat_bounds[0] < lat_bounds[1] <= 90):
            raise CLIError(f"Invalid latitude bounds: {lat_bounds}")
        if not (-180 <= lon_bounds[0] < lon_bounds[1] <= 180):
            raise CLIError(f"Invalid longitude bounds: {lon_bounds}")

        # Determine output file
        if args.output_file:
            output_path = validate_output_path(output_file=args.output_file)
        else:
            output_dir = validate_output_path(output_dir=args.output_dir)
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
                bathymetry_dir=str(args.bathymetry_dir),
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

        except ImportError as e:
            raise CLIError(f"Station picker not available: {e}")

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
    parser.add_argument("--output-file", type=Path, help="Specific output file path")
    parser.add_argument(
        "--bathymetry-source", choices=["etopo2022", "gebco2025"], default="etopo2022"
    )

    args = parser.parse_args()
    main(args)
