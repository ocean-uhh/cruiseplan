"""
Station picker API implementation.

This module implements the 'cruiseplan.stations()' API function for interactive
station placement. This is a direct migration of business logic from cli/stations.py
with no changes to core functionality.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cruiseplan.types import BaseResult
from cruiseplan.utils.coordinates import _validate_coordinate_bounds
from cruiseplan.utils.io import validate_input_file, validate_output_directory

logger = logging.getLogger(__name__)


class StationPickerResult(BaseResult):
    """Result object for station picker operations."""

    def __init__(
        self,
        output_file: Path,
        summary: Dict[str, Any],
        pangaea_data: Optional[List[Dict]] = None,
    ):
        """Initialize station picker result."""
        super().__init__(
            files_created=[output_file],
            summary=summary,
        )
        self.output_file = output_file
        self.pangaea_data = pangaea_data

    def __str__(self) -> str:
        """String representation of the result."""
        return f"Interactive station picker completed - output: {self.output_file}"


def determine_coordinate_bounds(
    lat_bounds: Optional[Tuple[float, float]] = None,
    lon_bounds: Optional[Tuple[float, float]] = None,
    campaign_data: Optional[List[Dict]] = None,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    Determine coordinate bounds from parameters or PANGAEA data.

    Moved from cli/stations.py with no changes to logic.

    Parameters
    ----------
    lat_bounds : tuple, optional
        Explicit latitude bounds (min, max)
    lon_bounds : tuple, optional
        Explicit longitude bounds (min, max)
    campaign_data : list, optional
        Loaded PANGAEA campaign data

    Returns
    -------
    Tuple[Tuple[float, float], Tuple[float, float]]
        Tuple of (lat_bounds, lon_bounds) as (min, max) tuples
    """
    # Use explicit bounds if provided
    if lat_bounds and lon_bounds:
        logger.info(
            f"Using explicit bounds: Lat: {lat_bounds[0]:.2f}° to {lat_bounds[1]:.2f}°, Lon: {lon_bounds[0]:.2f}° to {lon_bounds[1]:.2f}°"
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

            lat_bounds_calc = (min(all_lats) - lat_padding, max(all_lats) + lat_padding)
            lon_bounds_calc = (min(all_lons) - lon_padding, max(all_lons) + lon_padding)

            logger.info(
                f"Using bounds from PANGAEA data: Lat: {lat_bounds_calc[0]:.2f}° to {lat_bounds_calc[1]:.2f}°, Lon: {lon_bounds_calc[0]:.2f}° to {lon_bounds_calc[1]:.2f}°"
            )
            return lat_bounds_calc, lon_bounds_calc

    # Fall back to defaults
    default_lat = lat_bounds if lat_bounds else (45.0, 70.0)
    default_lon = lon_bounds if lon_bounds else (-65.0, -5.0)

    logger.info(
        f"Using default bounds: Lat: {default_lat[0]:.2f}° to {default_lat[1]:.2f}°, Lon: {default_lon[0]:.2f}° to {default_lon[1]:.2f}°"
    )
    return default_lat, default_lon


def load_pangaea_campaign_data(pangaea_file: Path) -> List[Dict]:
    """
    Load PANGAEA campaign data from pickle file with validation and summary.

    Moved from cli_utils.py with no changes to logic.

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
    ValueError
        If file cannot be loaded or contains no data.
    """
    try:
        from cruiseplan.data.pangaea import load_campaign_data

        campaign_data = load_campaign_data(pangaea_file)

        if not campaign_data:
            raise ValueError(f"No campaign data found in {pangaea_file}")

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
        raise ValueError(f"PANGAEA functionality not available: {e}")
    except Exception as e:
        raise ValueError(f"Error loading PANGAEA data: {e}")


def generate_output_filename(
    input_path: Path, suffix: str, extension: Optional[str] = None
) -> str:
    """
    Generate output filename by adding suffix to input filename.

    Moved from cli_utils.py with no changes to logic.

    Args:
        input_path: Input file path
        suffix: Suffix to add (e.g., "_stations")
        extension: New extension (defaults to input extension)

    Returns
    -------
        Generated filename
    """
    if extension is None:
        extension = input_path.suffix

    stem = input_path.stem
    return f"{stem}{suffix}{extension}"


def stations(
    lat_bounds: Optional[Tuple[float, float]] = None,
    lon_bounds: Optional[Tuple[float, float]] = None,
    output_dir: str = "data",
    output: Optional[str] = None,
    pangaea_file: Optional[str] = None,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data",
    high_resolution: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
) -> StationPickerResult:
    """
    Launch interactive station picker for cruise planning.

    This function moves all business logic from cli/stations.py with no changes
    to core functionality, just better error handling and structured returns.

    Parameters
    ----------
    lat_bounds : tuple, optional
        Latitude bounds as (min, max). If None, derived from PANGAEA data or defaults.
    lon_bounds : tuple, optional
        Longitude bounds as (min, max). If None, derived from PANGAEA data or defaults.
    output_dir : str
        Output directory for generated YAML file
    output : str, optional
        Output filename (default: "stations.yaml" or based on PANGAEA file)
    pangaea_file : str, optional
        Path to PANGAEA campaigns pickle file
    bathy_source : str
        Bathymetry source ("etopo2022" or "gebco2025")
    bathy_dir : str
        Bathymetry data directory
    high_resolution : bool
        Use high resolution bathymetry (slower)
    overwrite : bool
        Overwrite existing output file
    verbose : bool
        Enable verbose logging

    Returns
    -------
    StationPickerResult
        Result with output file path and summary information

    Raises
    ------
    ImportError
        If matplotlib is not available
    ValueError
        If coordinate bounds are invalid or PANGAEA file cannot be loaded
    FileNotFoundError
        If PANGAEA file or bathymetry data not found
    """
    # Configure logging level
    if verbose:
        logging.basicConfig(
            level=logging.DEBUG, format="%(levelname)s: %(message)s", force=True
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(levelname)s: %(message)s", force=True
        )

    # Check for matplotlib dependency
    try:
        import matplotlib.pyplot  # noqa: F401
    except ImportError:
        raise ImportError(
            "Interactive station picker requires matplotlib. "
            "Install with: pip install matplotlib"
        )

    logger.info("=" * 50)
    logger.info("Interactive Station Picker")
    logger.info("=" * 50)

    # Load PANGAEA campaign data if provided
    campaign_data = None
    if pangaea_file:
        pangaea_path = validate_input_file(pangaea_file)
        logger.info(f"Loading PANGAEA data from: {pangaea_path}")
        campaign_data = load_pangaea_campaign_data(pangaea_path)
    else:
        logger.info("No PANGAEA data provided - using bathymetry only")

    # Determine coordinate bounds
    final_lat_bounds, final_lon_bounds = determine_coordinate_bounds(
        lat_bounds, lon_bounds, campaign_data
    )

    # Validate coordinate bounds
    try:
        _validate_coordinate_bounds(list(final_lat_bounds), list(final_lon_bounds))
    except ValueError as e:
        raise ValueError(f"Invalid coordinate bounds: {e}")

    # Set up output file
    output_dir_path = validate_output_directory(output_dir)

    if output:
        output_filename = output
    elif pangaea_file:
        # Generate filename based on PANGAEA file
        output_filename = generate_output_filename(
            Path(pangaea_file), "_stations", ".yaml"
        )
    else:
        output_filename = "stations.yaml"

    output_path = output_dir_path / output_filename

    logger.info(f"Output file: {output_path}")
    logger.info(f"Bathymetry source: {bathy_source}")
    resolution_msg = (
        "high resolution (no downsampling)"
        if high_resolution
        else "standard resolution (10x downsampled)"
    )
    logger.info(f"Bathymetry resolution: {resolution_msg}")

    # Performance warning for GEBCO + high-resolution combination
    if bathy_source == "gebco2025" and high_resolution:
        logger.warning("⚠️  PERFORMANCE WARNING:")
        logger.warning(
            "   GEBCO 2025 with high resolution can be very slow for interactive use!"
        )
        logger.warning("   Consider using etopo2022 for faster interaction.")
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

    # Import and initialize the interactive picker (unchanged from cli/stations.py)
    try:
        from cruiseplan.interactive.station_picker import StationPicker

        # Initialize the picker with exact same parameters as CLI version
        bathymetry_stride = 1 if high_resolution else 10

        picker = StationPicker(
            campaign_data=campaign_data,
            output_file=str(output_path),
            bathymetry_stride=bathymetry_stride,
            bathymetry_source=bathy_source,
            bathymetry_dir=str(bathy_dir),
            overwrite=overwrite,
        )

        # Set coordinate bounds (unchanged from cli/stations.py)
        picker.ax_map.set_xlim(final_lon_bounds)
        picker.ax_map.set_ylim(final_lat_bounds)
        picker._update_aspect_ratio()

        # Re-plot bathymetry with correct bounds
        picker._plot_bathymetry()

        # Show the interactive interface (blocking call)
        picker.show()

        # Create result summary
        summary = {
            "output_file": str(output_path),
            "lat_bounds": final_lat_bounds,
            "lon_bounds": final_lon_bounds,
            "bathy_source": bathy_source,
            "high_resolution": high_resolution,
            "pangaea_campaigns": len(campaign_data) if campaign_data else 0,
        }

        return StationPickerResult(
            output_file=output_path,
            summary=summary,
            pangaea_data=campaign_data,
        )

    except ImportError as e:
        raise ImportError(f"matplotlib dependency error: {e}")
    except Exception as e:
        # Convert generic exceptions to more specific ones
        if "bathymetry" in str(e).lower():
            raise FileNotFoundError(f"Bathymetry data error: {e}")
        else:
            raise RuntimeError(f"Station picker error: {e}")
