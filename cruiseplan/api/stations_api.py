"""
Station picker API implementation.

This module implements the 'cruiseplan.stations()' API function for interactive
station placement. This is a direct migration of business logic from cli/stations.py
with no changes to core functionality.
"""

import logging
from pathlib import Path
from typing import Any, Optional

from cruiseplan.api.config import StationsConfig
from cruiseplan.api.types import BaseResult
from cruiseplan.config.cruise_config import CruiseConfig
from cruiseplan.config.yaml_io import load_yaml
from cruiseplan.utils.coordinates import _validate_coordinate_bounds
from cruiseplan.utils.io import (
    generate_output_filename,
    validate_input_file,
    validate_output_directory,
)
from cruiseplan.utils.logging import configure_logging
from cruiseplan.utils.plot_config import check_matplotlib_available

logger = logging.getLogger(__name__)


class StationPickerResult(BaseResult):
    """Result object for station picker operations."""

    def __init__(
        self,
        output_file: Path,
        summary: dict[str, Any],
        pangaea_data: Optional[list[dict]] = None,
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
    lat_bounds: Optional[tuple[float, float]] = None,
    lon_bounds: Optional[tuple[float, float]] = None,
    campaign_data: Optional[list[dict]] = None,
    config_lat_bounds: Optional[tuple[float, float]] = None,
    config_lon_bounds: Optional[tuple[float, float]] = None,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Determine coordinate bounds from parameters, config file, or PANGAEA data.

    Parameters
    ----------
    lat_bounds : tuple, optional
        Explicit latitude bounds (min, max)
    lon_bounds : tuple, optional
        Explicit longitude bounds (min, max)
    campaign_data : list, optional
        Loaded PANGAEA campaign data
    config_lat_bounds : tuple, optional
        Latitude bounds derived from config file
    config_lon_bounds : tuple, optional
        Longitude bounds derived from config file

    Returns
    -------
    Tuple[Tuple[float, float], Tuple[float, float]]
        Tuple of (lat_bounds, lon_bounds) as (min, max) tuples
    """
    # Use explicit bounds if provided (highest priority)
    if lat_bounds and lon_bounds:
        logger.info(
            f"Using explicit bounds: Lat: {lat_bounds[0]:.2f}° to {lat_bounds[1]:.2f}°, Lon: {lon_bounds[0]:.2f}° to {lon_bounds[1]:.2f}°"
        )
        return lat_bounds, lon_bounds
    
    # Use config file bounds if available (second priority)
    if config_lat_bounds and config_lon_bounds:
        logger.info(
            f"Using bounds from config file: Lat: {config_lat_bounds[0]:.2f}° to {config_lat_bounds[1]:.2f}°, Lon: {config_lon_bounds[0]:.2f}° to {config_lon_bounds[1]:.2f}°"
        )
        return config_lat_bounds, config_lon_bounds

    # Try to derive bounds from PANGAEA data (third priority)
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


def load_pangaea_campaign_data(pangaea_file: Path) -> list[dict]:
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


def load_config_stations_data(config_file: Path) -> tuple[list[dict], list[dict], tuple[float, float], tuple[float, float]]:
    """
    Load existing stations from cruise configuration file.

    Parameters
    ----------
    config_file : Path
        Path to YAML cruise configuration file.

    Returns
    -------
    tuple
        (stations_data, lat_bounds, lon_bounds) where:
        - stations_data: List of station dictionaries with lat/lon/depth
        - lat_bounds: Tuple of (min_lat, max_lat) 
        - lon_bounds: Tuple of (min_lon, max_lon)

    Raises
    ------
    ValueError
        If file cannot be loaded or contains no station data.
    """
    try:
        # Load and validate the YAML configuration
        raw_data = load_yaml(config_file)
        config = CruiseConfig(**raw_data)
        
        # Extract stations from points catalog
        stations_data = []
        all_lats = []
        all_lons = []
        
        if config.points:
            for point in config.points:
                station = {
                    "lat": point.latitude,
                    "lon": point.longitude,
                    "depth": getattr(point, 'water_depth', None) or 0.0,
                    "name": point.name,
                    "operation_type": str(point.operation_type) if hasattr(point, 'operation_type') else "station",
                    "action": str(point.action) if hasattr(point, 'action') else None,
                    "comment": point.comment if hasattr(point, 'comment') else None,
                    "duration": point.duration if hasattr(point, 'duration') else None,
                }
                stations_data.append(station)
                all_lats.append(point.latitude)
                all_lons.append(point.longitude)
        
        # Extract line data separately for proper line plotting
        lines_data = []
        if config.lines:
            for line in config.lines:
                if hasattr(line, 'route') and line.route:
                    # Extract full route for line plotting
                    route_points = []
                    for point in line.route:
                        route_points.append({
                            "lat": point.latitude,
                            "lon": point.longitude
                        })
                        all_lats.append(point.latitude)
                        all_lons.append(point.longitude)
                    
                    line_data = {
                        "name": line.name,
                        "route": route_points,
                        "operation_type": "transect"
                    }
                    lines_data.append(line_data)
        
        if not stations_data:
            raise ValueError(f"No stations found in configuration file {config_file}")
        
        # Calculate bounds with padding
        lat_padding = (max(all_lats) - min(all_lats)) * 0.1 or 1.0  # Add default padding if all same
        lon_padding = (max(all_lons) - min(all_lons)) * 0.1 or 1.0
        
        lat_bounds = (min(all_lats) - lat_padding, max(all_lats) + lat_padding)
        lon_bounds = (min(all_lons) - lon_padding, max(all_lons) + lon_padding)
        
        logger.info(f"Loaded {len(stations_data)} stations from {config_file}")
        logger.info(f"Station bounds: Lat {lat_bounds[0]:.2f}° to {lat_bounds[1]:.2f}°, Lon {lon_bounds[0]:.2f}° to {lon_bounds[1]:.2f}°")
        
        return stations_data, lat_bounds, lon_bounds

    except Exception as e:
        raise ValueError(f"Error loading config stations: {e}")


def _determine_output_path(
    output_dir: str, output: Optional[str], config_file: Optional[str], pangaea_file: Optional[str]
) -> tuple[Path, str]:
    """Determine output directory and filename for station picker."""
    output_dir_path = validate_output_directory(output_dir)

    if output:
        output_filename = output
    elif config_file:
        # Generate filename based on config file using centralized utility
        output_filename = generate_output_filename(config_file, "_stations_edited", ".yaml")
    elif pangaea_file:
        # Generate filename based on PANGAEA file using centralized utility
        output_filename = generate_output_filename(pangaea_file, "_stations", ".yaml")
    else:
        output_filename = "stations.yaml"

    return output_dir_path, output_filename


def _log_configuration_info(
    output_path: Path, bathy_source: str, high_resolution: bool
) -> None:
    """Log configuration information for the station picker."""
    logger.info("=" * 50)
    logger.info("Interactive Station Picker")
    logger.info("=" * 50)

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


def _display_usage_instructions() -> None:
    """Display interactive controls and usage instructions."""
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


def stations_with_config(
    config: StationsConfig = None,
) -> StationPickerResult:
    """
    Launch interactive station picker using configuration object.

    This is the modern API that uses a configuration object to reduce the number
    of function parameters. For backward compatibility, the legacy stations()
    function with individual parameters is still available.

    Parameters
    ----------
    config : StationsConfig, optional
        Configuration object containing all station picker options.
        If None, default configuration is used.

    Returns
    -------
    StationPickerResult
        Result object containing output file and metadata

    Examples
    --------
    Basic usage with defaults:

    >>> result = stations_with_config()

    Custom configuration:

    >>> from cruiseplan.api.config import StationsConfig, OutputConfig
    >>> config = StationsConfig(
    ...     lat_bounds=(-65, -45),
    ...     lon_bounds=(160, 180),
    ...     pangaea_file="pangaea_data.pkl",
    ...     output=OutputConfig(directory="cruise_stations")
    ... )
    >>> result = stations_with_config(config)
    """
    if config is None:
        config = StationsConfig()

    # Call the legacy function with expanded parameters
    return stations(
        lat_bounds=config.lat_bounds,
        lon_bounds=config.lon_bounds,
        output_dir=config.output.directory,
        output=config.output.filename,
        pangaea_file=config.pangaea_file,
        bathy_source=config.bathy_source,
        bathy_dir=config.bathy_dir,
        high_resolution=config.high_resolution,
        overwrite=config.overwrite,
        verbose=config.output.verbose,
    )


def stations(
    lat_bounds: Optional[tuple[float, float]] = None,
    lon_bounds: Optional[tuple[float, float]] = None,
    output_dir: str = "data",
    output: Optional[str] = None,
    config_file: Optional[str] = None,
    pangaea_file: Optional[str] = None,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data",
    bathy_contours: Optional[list] = None,
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
        Latitude bounds as (min, max). If None, derived from config file, PANGAEA data, or defaults.
    lon_bounds : tuple, optional
        Longitude bounds as (min, max). If None, derived from config file, PANGAEA data, or defaults.
    output_dir : str
        Output directory for generated YAML file
    output : str, optional
        Output filename (default: "stations.yaml" or based on input files)
    config_file : str, optional
        Path to existing YAML cruise configuration file to load and edit
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
        If coordinate bounds are invalid, config file cannot be loaded, or PANGAEA file cannot be loaded
    FileNotFoundError
        If config file, PANGAEA file, or bathymetry data not found
    """
    # Configure logging and check dependencies
    configure_logging(verbose)
    check_matplotlib_available()

    # Load config file data if provided
    config_stations_data = None
    config_lat_bounds = None
    config_lon_bounds = None
    
    if config_file:
        config_path = validate_input_file(config_file)
        logger.info(f"Loading existing stations from: {config_path}")
        config_stations_data, config_lat_bounds, config_lon_bounds = load_config_stations_data(config_path)
    
    # Load PANGAEA campaign data if provided
    campaign_data = None
    if pangaea_file:
        pangaea_path = validate_input_file(pangaea_file)
        logger.info(f"Loading PANGAEA data from: {pangaea_path}")
        campaign_data = load_pangaea_campaign_data(pangaea_path)
    else:
        logger.info("No PANGAEA data provided - using bathymetry only")

    # Determine and validate coordinate bounds
    final_lat_bounds, final_lon_bounds = determine_coordinate_bounds(
        lat_bounds, lon_bounds, campaign_data, config_lat_bounds, config_lon_bounds
    )
    try:
        _validate_coordinate_bounds(list(final_lat_bounds), list(final_lon_bounds))
    except ValueError as e:
        raise ValueError(f"Invalid coordinate bounds: {e}")

    # Set up output paths
    output_dir_path, output_filename = _determine_output_path(
        output_dir, output, config_file, pangaea_file
    )
    output_path = output_dir_path / output_filename

    # Log configuration and display instructions
    _log_configuration_info(output_path, bathy_source, high_resolution)
    _display_usage_instructions()

    # Import and initialize the interactive picker (unchanged from cli/stations.py)
    try:
        from cruiseplan.interactive.station_picker import StationPicker

        # Initialize the picker with exact same parameters as CLI version
        bathymetry_stride = 1 if high_resolution else 10

        picker = StationPicker(
            campaign_data=campaign_data,
            existing_stations=config_stations_data,
            output_file=str(output_path),
            bathymetry_stride=bathymetry_stride,
            bathymetry_source=bathy_source,
            bathymetry_dir=str(bathy_dir),
            custom_contours=bathy_contours,
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
        raise ImportError(f"matplotlib dependency error: {e}") from e
    except FileNotFoundError as e:
        # Provide clearer context for missing bathymetry or related data files
        raise FileNotFoundError(f"Bathymetry data error: {e}") from e
    except Exception:
        # Log unexpected errors without changing their type
        logger.exception("Station picker error")
        raise
