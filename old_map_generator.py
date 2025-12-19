"""
Interactive Map Generation System.

Generates interactive Leaflet maps from cruise track data using Folium.
Creates HTML files with embedded JavaScript for web-based geographic visualization
of cruise operations and tracks.

Notes
-----
Maps are centered on the first track's average position. Multiple tracks are
displayed with different colors. Requires internet connection for tile loading
when viewing the generated HTML files.
"""

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import folium
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


def extract_map_data(data_source, source_type="cruise"):
    """
    Extract coordinate and metadata from either cruise config or timeline data.

    Parameters
    ----------
    data_source : Cruise or list
        Either a Cruise object or timeline list
    source_type : str, optional
        "cruise" for Cruise object, "timeline" for timeline list

    Returns
    -------
    dict
        Dictionary with keys: lats, lons, station_names, station_types, departure_port, arrival_port, title
    """
    if source_type == "cruise":
        from cruiseplan.utils.coordinates import extract_coordinates_from_cruise

        all_lats, all_lons, station_names, departure_port, arrival_port = (
            extract_coordinates_from_cruise(data_source)
        )

        # Extract station types from cruise station registry
        station_types = []
        for station_name, station in data_source.station_registry.items():
            # Check operation_type or fall back to detecting from object type
            if hasattr(station, "operation_type"):
                station_types.append(station.operation_type)
            elif "mooring" in station_name.lower() or hasattr(station, "mooring"):
                station_types.append("mooring")
            else:
                station_types.append("station")  # Default to station

        title = f"{data_source.config.cruise_name}\nCruise Track with Bathymetry"

    elif source_type == "timeline":
        all_lats = []
        all_lons = []
        station_names = []
        station_types = []
        departure_port = None
        arrival_port = None

        # Handle both old (list) and new (dict) timeline data format
        if isinstance(data_source, dict):
            timeline = data_source["timeline"]
            config = data_source.get("config")
        else:
            timeline = data_source
            config = None

        # Extract coordinates from timeline activities
        for activity in timeline:
            if isinstance(activity, dict):
                lat = activity.get("lat", 0.0)
                lon = activity.get("lon", 0.0)
                name = activity.get("activity", "Unknown")
                operation_type = activity.get("operation_type", "station")

                if lat != 0.0 or lon != 0.0:
                    all_lats.append(lat)
                    all_lons.append(lon)
                    station_names.append(name)
                    station_types.append(operation_type)

        # Extract ports from config if available
        if config:
            if hasattr(config, "departure_port") and config.departure_port:
                dep_lat = config.departure_port.position.latitude
                dep_lon = config.departure_port.position.longitude
                departure_port = (dep_lat, dep_lon, config.departure_port.name)

            if hasattr(config, "arrival_port") and config.arrival_port:
                arr_lat = config.arrival_port.position.latitude
                arr_lon = config.arrival_port.position.longitude
                arrival_port = (arr_lat, arr_lon, config.arrival_port.name)

        title = "Cruise Schedule\nOperations Timeline with Bathymetry"

    else:
        raise ValueError(f"Unknown source_type: {source_type}")

    return {
        "lats": all_lats,
        "lons": all_lons,
        "station_names": station_names,
        "station_types": station_types,
        "departure_port": departure_port,
        "arrival_port": arrival_port,
        "title": title,
    }


def plot_bathymetry(
    ax,
    bathy_min_lon: float,
    bathy_max_lon: float,
    bathy_min_lat: float,
    bathy_max_lat: float,
    bathymetry_source: str = "gebco2025",
    stride: int = 5,
    bathymetry_dir: str = "data",
) -> bool:
    """
    Plot bathymetry contours on a matplotlib axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The matplotlib axis to plot on
    bathy_min_lon, bathy_max_lon : float
        Longitude bounds for bathymetry data
    bathy_min_lat, bathy_max_lat : float
        Latitude bounds for bathymetry data
    bathymetry_source : str, optional
        Bathymetry dataset to use (default "gebco2025")
    stride : int, optional
        Downsampling factor for bathymetry (default 5)

    Returns
    -------
    bool
        True if bathymetry was successfully plotted, False otherwise
    """
    try:
        from cruiseplan.data.bathymetry import BathymetryManager
        from cruiseplan.interactive.colormaps import get_colormap

        logger.info(
            f"Loading bathymetry for region: {bathy_min_lat:.1f}°-{bathy_max_lat:.1f}°N, {bathy_min_lon:.1f}°-{bathy_max_lon:.1f}°E"
        )

        # Initialize bathymetry
        bathymetry = BathymetryManager(
            source=bathymetry_source, data_dir=bathymetry_dir
        )
        bathy_data = bathymetry.get_grid_subset(
            lat_min=bathy_min_lat,
            lat_max=bathy_max_lat,
            lon_min=bathy_min_lon,
            lon_max=bathy_max_lon,
            stride=stride,
        )

        if bathy_data is None:
            logger.warning("No bathymetry data available for this region")
            return False

        lons_grid, lats_grid, depths_grid = bathy_data

        # Use same colormap as station picker
        cmap = get_colormap("bathymetry")

        # Add filled contours matching station picker levels
        cs_filled = ax.contourf(
            lons_grid,
            lats_grid,
            depths_grid,
            levels=[
                -6000,
                -5000,
                -4000,
                -3000,
                -2000,
                -1500,
                -1000,
                -500,
                -200,
                -100,
                -50,
                0,
                200,
            ],
            cmap=cmap,
            alpha=0.7,
            extend="both",
        )

        # Add colorbar
        cbar = plt.colorbar(cs_filled, ax=ax, shrink=0.8, pad=0.02)
        cbar.set_label("Depth (m)", rotation=270, labelpad=20)

        logger.info("Added bathymetry contours covering full region")
        return True

    except Exception as e:
        logger.warning(f"Bathymetry plotting failed: {e}")
        return False


def plot_cruise_elements(
    ax,
    data_source,
    display_bounds: Tuple[float, float, float, float],
    source_type="cruise",
):
    """
    Plot stations, ports, and cruise tracks on a matplotlib axis.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The matplotlib axis to plot on
    data_source : Cruise or list
        Either a Cruise object or timeline data
    display_bounds : tuple
        (min_lon, max_lon, min_lat, max_lat) for display area
    source_type : str, optional
        "cruise" for Cruise object, "timeline" for timeline data
    """
    # Extract coordinates using unified function
    map_data = extract_map_data(data_source, source_type)
    all_lats = map_data["lats"]
    all_lons = map_data["lons"]
    station_names = map_data["station_names"]
    station_types = map_data["station_types"]
    departure_port = map_data["departure_port"]
    arrival_port = map_data["arrival_port"]
    title = map_data["title"]

    # Set display limits and aspect ratio
    final_min_lon, final_max_lon, final_min_lat, final_max_lat = display_bounds
    ax.set_xlim(final_min_lon, final_max_lon)
    ax.set_ylim(final_min_lat, final_max_lat)

    # Set the computed aspect ratio
    mid_lat_deg = (final_min_lat + final_max_lat) / 2
    mid_lat_deg = max(-85.0, min(85.0, mid_lat_deg))
    mid_lat_rad = math.radians(mid_lat_deg)
    try:
        aspect = 1.0 / math.cos(mid_lat_rad)
    except ZeroDivisionError:
        aspect = 1.0
    aspect = max(1.0, min(aspect, 10.0))
    ax.set_aspect(aspect, adjustable="datalim")

    # Extract only station coordinates for cruise track (exclude ports)
    if source_type == "cruise":
        station_lats = []
        station_lons = []
        for station_name, station in data_source.station_registry.items():
            lat = (
                station.latitude
                if hasattr(station, "latitude")
                else station.position.latitude
            )
            lon = (
                station.longitude
                if hasattr(station, "longitude")
                else station.position.longitude
            )
            station_lats.append(lat)
            station_lons.append(lon)
    else:  # timeline data
        station_lats = all_lats
        station_lons = all_lons

    # Plot transit lines UNDER symbols (lower zorder)
    if departure_port and station_lats:
        dep_lat, dep_lon, _ = departure_port
        # Line from departure port to first station
        ax.plot(
            [dep_lon, station_lons[0]],
            [dep_lat, station_lats[0]],
            "b--",
            linewidth=1.5,
            alpha=0.6,
            zorder=1,
            label="Transit Lines",
        )

    if arrival_port and station_lats and arrival_port != departure_port:
        arr_lat, arr_lon, _ = arrival_port
        # Line from last station to arrival port
        ax.plot(
            [station_lons[-1], arr_lon],
            [station_lats[-1], arr_lat],
            "b--",
            linewidth=1.5,
            alpha=0.6,
            zorder=1,
        )

    # Plot cruise track between stations - only for timeline data (scheduled sequence)
    if source_type == "timeline" and len(station_lats) > 1:
        ax.plot(
            station_lons,
            station_lats,
            "b-",
            linewidth=1,
            alpha=0.8,
            label="Cruise Track",
            zorder=2,
        )

    # Plot ports
    if departure_port:
        dep_lat, dep_lon, dep_name = departure_port
        ax.scatter(
            dep_lon,
            dep_lat,
            c="purple",
            s=100,
            marker="P",
            edgecolors="black",
            alpha=0.7,
            linewidth=1,
            zorder=10,
            label="Departure Port",
        )
        ax.annotate(
            dep_name,
            (dep_lon, dep_lat),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
            color="purple",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

    if arrival_port and arrival_port != departure_port:
        arr_lat, arr_lon, arr_name = arrival_port
        ax.scatter(
            arr_lon,
            arr_lat,
            c="darkmagenta",
            s=100,
            marker="H",
            alpha=0.7,
            edgecolors="black",
            linewidth=1,
            zorder=10,
            label="Arrival Port",
        )
        ax.annotate(
            arr_name,
            (arr_lon, arr_lat),
            xytext=(8, 8),
            textcoords="offset points",
            fontsize=10,
            fontweight="bold",
            color="darkmagenta",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

    # Plot stations by type
    if station_lats:
        # Separate stations and moorings
        station_lats_by_type = {"station": [], "mooring": []}
        station_lons_by_type = {"station": [], "mooring": []}

        for i, (lat, lon, stype) in enumerate(
            zip(station_lats, station_lons, station_types)
        ):
            if "mooring" in stype.lower():
                station_lats_by_type["mooring"].append(lat)
                station_lons_by_type["mooring"].append(lon)
            else:
                station_lats_by_type["station"].append(lat)
                station_lons_by_type["station"].append(lon)

        # Plot regular stations (red circles)
        if station_lats_by_type["station"]:
            ax.scatter(
                station_lons_by_type["station"],
                station_lats_by_type["station"],
                c="red",
                s=50,
                alpha=0.8,
                edgecolors="black",
                linewidth=0.5,
                zorder=15,
                label="Stations",
            )

        # Plot moorings (yellow stars)
        if station_lats_by_type["mooring"]:
            ax.scatter(
                station_lons_by_type["mooring"],
                station_lats_by_type["mooring"],
                c="gold",
                s=120,
                marker="*",
                alpha=0.9,
                edgecolors="black",
                linewidth=0.5,
                zorder=15,
                label="Moorings",
            )

    # Set labels and title
    ax.set_xlabel("Longitude (°)", fontsize=12)
    ax.set_ylabel("Latitude (°)", fontsize=12)
    ax.set_title(title, fontsize=14, fontweight="bold")

    # Add grid and legend
    ax.grid(True, alpha=0.3, zorder=0)
    ax.legend(loc="upper right", fontsize=10, frameon=True, fancybox=True, shadow=True)

    logger.info(f"Map displayed with {len(station_names)} stations")
    if departure_port:
        logger.info(f"Departure: {departure_port[2]}")
    if arrival_port:
        logger.info(f"Arrival: {arrival_port[2]}")


def generate_map(
    data_source,
    source_type: str = "cruise",
    output_file: Union[str, Path] = "cruise_map.png",
    bathymetry_source: str = "gebco2025",
    bathymetry_stride: int = 5,
    bathymetry_dir: str = "data",
    show_plot: bool = False,
    figsize: Tuple[float, float] = (10, 8),
) -> Optional[Path]:
    """
    Generate a static PNG map from either cruise config or timeline data.

    This is a unified function that can handle both cruise configuration objects
    and timeline data from the scheduler.

    Parameters
    ----------
    data_source : Cruise or list
        Either a Cruise object or timeline data
    source_type : str, optional
        "cruise" for Cruise object, "timeline" for timeline data (default: "cruise")
    output_file : str or Path, optional
        Path or string for the output PNG file. Default is "cruise_map.png".
    bathymetry_source : str, optional
        Bathymetry dataset to use ("etopo2022" or "gebco2025"). Default is "gebco2025".
    bathymetry_stride : int, optional
        Downsampling factor for bathymetry (higher = faster but less detailed). Default is 5.
    show_plot : bool, optional
        Whether to display the plot inline (useful for notebooks). Default is False.
    figsize : tuple of float, optional
        Figure size as (width, height) in inches. Default is (10, 8).

    Returns
    -------
    Path or None
        The absolute path to the generated PNG map file, or None if failed.
    """
    # Extract map data using unified function
    map_data = extract_map_data(data_source, source_type)
    all_lats = map_data["lats"]
    all_lons = map_data["lons"]

    if not all_lats:
        logger.warning(f"No coordinates found in {source_type} data")
        return None

    # Ensure output_file is a Path object
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate display bounds (include ports for bounds calculation)
    from cruiseplan.utils.coordinates import calculate_map_bounds

    bounds_lats = all_lats.copy()
    bounds_lons = all_lons.copy()

    # Add ports to bounds calculation
    if map_data["departure_port"]:
        dep_lat, dep_lon, _ = map_data["departure_port"]
        bounds_lats.append(dep_lat)
        bounds_lons.append(dep_lon)
    if map_data["arrival_port"]:
        arr_lat, arr_lon, _ = map_data["arrival_port"]
        bounds_lats.append(arr_lat)
        bounds_lons.append(arr_lon)

    display_bounds = calculate_map_bounds(bounds_lats, bounds_lons)

    # Calculate bathymetry limits with extra padding for coverage
    bathy_limits = calculate_map_bounds(
        bounds_lats,
        bounds_lons,
        padding_degrees=10.0,  # Fixed 10-degree padding for bathymetry
        apply_aspect_ratio=False,  # Don't need aspect correction for bathymetry bounds
        round_to_degrees=False,  # Don't need rounding for bathymetry bounds
    )

    # Create figure and axis
    fig, ax = plt.subplots(figsize=figsize)

    # Plot bathymetry
    plot_bathymetry(
        ax, *bathy_limits, bathymetry_source, bathymetry_stride, bathymetry_dir
    )

    # Plot cruise elements
    plot_cruise_elements(ax, data_source, display_bounds, source_type)

    plt.tight_layout()

    # Show or save
    if show_plot:
        plt.show()
    else:
        plt.savefig(
            output_path,
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
            edgecolor="none",
        )
        plt.close()
        logger.info(f"Map saved to {output_path.resolve()}")

    return output_path.resolve()


def generate_map_from_yaml(
    cruise,
    output_file: Union[str, Path] = "cruise_map.png",
    bathymetry_source: str = "gebco2025",
    bathymetry_stride: int = 5,
    bathymetry_dir: str = "data",
    show_plot: bool = False,
    figsize: Tuple[float, float] = (10, 8),
) -> Optional[Path]:
    """
    Generate a static PNG map directly from a Cruise configuration object.

    This is a high-level function that combines the individual plotting functions.

    Parameters
    ----------
    cruise : Cruise
        Cruise object with station registry and configuration
    output_file : str or Path, optional
        Path or string for the output PNG file. Default is "cruise_map.png".
    bathymetry_source : str, optional
        Bathymetry dataset to use ("etopo2022" or "gebco2025"). Default is "gebco2025".
    bathymetry_stride : int, optional
        Downsampling factor for bathymetry (higher = faster but less detailed). Default is 5.
    show_plot : bool, optional
        Whether to display the plot inline (useful for notebooks). Default is False.
    figsize : tuple of float, optional
        Figure size as (width, height) in inches. Default is (10, 8).

    Returns
    -------
    Path or None
        The absolute path to the generated PNG map file, or None if failed.
    """
    return generate_map(
        data_source=cruise,
        source_type="cruise",
        output_file=output_file,
        bathymetry_source=bathymetry_source,
        bathymetry_stride=bathymetry_stride,
        bathymetry_dir=bathymetry_dir,
        show_plot=show_plot,
        figsize=figsize,
    )


def generate_map_from_timeline(
    timeline,
    output_file: Union[str, Path] = "timeline_map.png",
    bathymetry_source: str = "gebco2025",
    bathymetry_stride: int = 5,
    figsize: Tuple[float, float] = (10, 8),
    config=None,
) -> Optional[Path]:
    """
    Generate a static PNG map from timeline data showing scheduled sequence.

    This function creates a map showing the actual scheduled sequence of operations
    with cruise tracks between stations.

    Parameters
    ----------
    timeline : list
        Timeline data from scheduler with activities and coordinates
    output_file : str or Path, optional
        Path or string for the output PNG file. Default is "timeline_map.png".
    bathymetry_source : str, optional
        Bathymetry dataset to use ("etopo2022" or "gebco2025"). Default is "gebco2025".
    bathymetry_stride : int, optional
        Downsampling factor for bathymetry (higher = faster but less detailed). Default is 5.
    figsize : tuple of float, optional
        Figure size as (width, height) in inches. Default is (10, 8).
    config : CruiseConfig, optional
        Cruise configuration object to extract port information

    Returns
    -------
    Path or None
        The absolute path to the generated PNG map file, or None if failed.
    """
    # Create a timeline data structure that includes config for port extraction
    timeline_data = {"timeline": timeline, "config": config}

    return generate_map(
        data_source=timeline_data,
        source_type="timeline",
        output_file=output_file,
        bathymetry_source=bathymetry_source,
        bathymetry_stride=bathymetry_stride,
        show_plot=False,
        figsize=figsize,
    )


def generate_folium_map(
    tracks: List[Dict[str, Any]], output_file: Union[str, Path] = "cruise_map.html"
) -> Optional[Path]:
    """
    Generates an interactive Leaflet map from merged cruise tracks.

    Parameters
    ----------
    tracks : list of dict
        List of track dictionaries with 'latitude', 'longitude', 'label', 'dois' keys.
        Each track contains coordinate lists and metadata.
    output_file : str or Path, optional
        Path or string for the output HTML file. Default is "cruise_map.html".

    Returns
    -------
    Path
        The absolute path to the generated map file.

    Notes
    -----
    Map is centered on the average position of the first track. Tracks are
    displayed with different colors. Returns None if no valid tracks provided.
    """
    if not tracks:
        logger.warning("No tracks provided to generate map.")
        return None

    # Ensure output_file is a Path object
    output_path = Path(output_file)

    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Determine Map Center (Average of first track's points)
    first_track = tracks[0]

    # Safety check for empty coordinate lists
    if not first_track["latitude"] or not first_track["longitude"]:
        logger.error(f"Track {first_track.get('label')} has no coordinates.")
        return None

    avg_lat = sum(first_track["latitude"]) / len(first_track["latitude"])
    avg_lon = sum(first_track["longitude"]) / len(first_track["longitude"])

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6, tiles="Cartodb Positron")

    # 2. Draw Each Track
    colors = ["blue", "red", "green", "purple", "orange", "darkblue"]

    for i, track in enumerate(tracks):
        lats = track["latitude"]
        lons = track["longitude"]
        label = track.get("label", "Unknown")
        dois = track.get("dois", [])

        if not lats or not lons:
            continue

        # Zip coordinates for Folium (Lat, Lon)
        points = list(zip(lats, lons))

        # Pick a color
        color = colors[i % len(colors)]

        # Add the Line
        folium.PolyLine(
            points,
            color=color,
            weight=2,
            opacity=0.6,
            dash_array="5, 10",  # Optional: Dashed line to differentiate from other layers
        ).add_to(m)

        # B. Draw Discrete Stations (The dots themselves)
        # We step through points. If you have 10,000 points, you might want points[::10]
        for point_idx, point in enumerate(points):
            folium.CircleMarker(
                location=point,
                radius=3,  # Small dot
                color=color,  # Border color
                fill=True,
                fill_color=color,  # Fill color
                fill_opacity=1.0,
                popup=f"{label} (St. {point_idx})",  # Simple popup
                tooltip=f"Station {point_idx}",
            ).add_to(m)

        # HTML for popup
        doi_html = "<br>".join(dois) if dois else "None"
        popup_html = f"<b>{label}</b><br><u>Source DOIs:</u><br>{doi_html}"

        # Add Marker at Start
        folium.Marker(
            location=points[0],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=color, icon="ship", prefix="fa"),
        ).add_to(m)

        # Add Marker at End
        folium.Marker(
            location=points[-1],
            popup=f"End: {label}",
            icon=folium.Icon(color="gray", icon="stop", prefix="fa"),
        ).add_to(m)

    # 3. Save
    m.save(str(output_path))
    logger.info(f"Map successfully saved to {output_path.resolve()}")

    return output_path.resolve()
