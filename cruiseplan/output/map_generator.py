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


# ============================================================================
# MAP DATA EXTRACTION FUNCTIONS
# ============================================================================


def extract_points_from_cruise(cruise, include_ports=True) -> List[Dict[str, Any]]:
    """
    Extract point features (stations, moorings, optionally ports) from cruise configuration.

    Parameters
    ----------
    cruise : Cruise
        Cruise object with station registry and configuration
    include_ports : bool, optional
        Whether to include departure/arrival ports (default True)

    Returns
    -------
    List[Dict[str, Any]]
        List of point dictionaries with keys: name, lat, lon, entity_type, operation_type, action
    """
    points = []

    # Extract stations
    if hasattr(cruise, "station_registry") and cruise.station_registry:
        for station_name, station in cruise.station_registry.items():
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
            # Determine entity type based on operation type
            operation_type = getattr(station, "operation_type", "station")
            if operation_type == "mooring":
                entity_type = "mooring"
            else:
                entity_type = "station"

            points.append(
                {
                    "name": station_name,
                    "lat": lat,
                    "lon": lon,
                    "entity_type": entity_type,
                    "operation_type": operation_type,
                    "action": getattr(station, "action", None),
                    "depth": getattr(
                        station, "water_depth", getattr(station, "depth", None)
                    ),
                }
            )

    # Extract moorings
    if hasattr(cruise, "mooring_registry") and cruise.mooring_registry:
        for mooring_name, mooring in cruise.mooring_registry.items():
            lat = (
                mooring.latitude
                if hasattr(mooring, "latitude")
                else mooring.position.latitude
            )
            lon = (
                mooring.longitude
                if hasattr(mooring, "longitude")
                else mooring.position.longitude
            )
            points.append(
                {
                    "name": mooring_name,
                    "lat": lat,
                    "lon": lon,
                    "entity_type": "mooring",
                    "operation_type": getattr(mooring, "operation_type", "mooring"),
                    "action": getattr(mooring, "action", None),
                    "depth": getattr(
                        mooring, "water_depth", getattr(mooring, "depth", None)
                    ),
                }
            )

    # Extract ports (optional)
    if include_ports:
        # Extract departure port
        if hasattr(cruise.config, "departure_port") and cruise.config.departure_port:
            port = cruise.config.departure_port
            if hasattr(port, "latitude"):
                points.append(
                    {
                        "name": port.name,
                        "lat": port.latitude,
                        "lon": port.longitude,
                        "entity_type": "departure_port",
                        "operation_type": "port",
                        "action": None,
                        "depth": None,
                    }
                )

        # Extract arrival port
        if hasattr(cruise.config, "arrival_port") and cruise.config.arrival_port:
            port = cruise.config.arrival_port
            if hasattr(port, "latitude"):
                points.append(
                    {
                        "name": port.name,
                        "lat": port.latitude,
                        "lon": port.longitude,
                        "entity_type": "arrival_port",
                        "operation_type": "port",
                        "action": None,
                        "depth": None,
                    }
                )

    return points


def extract_lines_from_cruise(cruise) -> List[Dict[str, Any]]:
    """
    Extract line features (scientific transits, cruise tracks) from cruise configuration.

    Parameters
    ----------
    cruise : Cruise
        Cruise object with config containing transits

    Returns
    -------
    List[Dict[str, Any]]
        List of line dictionaries with keys: name, waypoints, entity_type, operation_type, action
    """
    lines = []

    # Extract scientific transits with routes from config
    if (
        hasattr(cruise, "config")
        and hasattr(cruise.config, "transits")
        and cruise.config.transits
    ):
        for transit in cruise.config.transits:
            if hasattr(transit, "route") and transit.route and len(transit.route) >= 2:
                waypoints = []
                for waypoint in transit.route:
                    waypoints.append(
                        {"lat": waypoint.latitude, "lon": waypoint.longitude}
                    )

                lines.append(
                    {
                        "name": transit.name,
                        "waypoints": waypoints,
                        "entity_type": "transit",
                        "operation_type": getattr(transit, "operation_type", "transit"),
                        "action": getattr(transit, "action", None),
                        "vessel_speed": getattr(transit, "vessel_speed", None),
                    }
                )

    return lines


def extract_areas_from_timeline(timeline_data) -> List[Dict[str, Any]]:
    """
    Extract area features from timeline data.

    Parameters
    ----------
    timeline_data : List[Dict]
        Timeline activity records

    Returns
    -------
    List[Dict[str, Any]]
        List of area dictionaries with keys: name, corners, entity_type, operation_type, action
    """
    areas = []

    for activity in timeline_data:
        # Check if this activity represents an area operation
        if (
            activity.get("category") == "area_operation"
            and activity.get("corners")
            and len(activity.get("corners", [])) >= 3
        ):

            # Convert corners to the expected format
            corners = []
            for corner in activity["corners"]:
                corners.append(
                    {
                        "lat": corner.get("latitude", corner.get("lat")),
                        "lon": corner.get("longitude", corner.get("lon")),
                    }
                )

            areas.append(
                {
                    "name": activity.get("name", "Unknown Area"),
                    "corners": corners,
                    "entity_type": "area",
                    "operation_type": activity.get("operation_type", "survey"),
                    "action": activity.get("action", None),
                    "duration": activity.get("duration", None),
                }
            )

    return areas


def extract_areas_from_cruise(cruise) -> List[Dict[str, Any]]:
    """
    Extract area features (survey areas, polygons) from cruise configuration.

    Parameters
    ----------
    cruise : Cruise
        Cruise object with config containing areas

    Returns
    -------
    List[Dict[str, Any]]
        List of area dictionaries with keys: name, corners, entity_type, operation_type, action
    """
    areas = []

    # Extract survey areas with corners from config
    if (
        hasattr(cruise, "config")
        and hasattr(cruise.config, "areas")
        and cruise.config.areas
    ):
        for area in cruise.config.areas:
            if hasattr(area, "corners") and area.corners and len(area.corners) >= 3:
                corners = []
                for corner in area.corners:
                    corners.append({"lat": corner.latitude, "lon": corner.longitude})

                areas.append(
                    {
                        "name": area.name,
                        "corners": corners,
                        "entity_type": "area",
                        "operation_type": getattr(area, "operation_type", "survey"),
                        "action": getattr(area, "action", None),
                        "duration": getattr(area, "duration", None),
                    }
                )

    return areas


def calculate_optimal_figsize(
    display_bounds: Tuple[float, float, float, float],
    base_width: float = 12.0,  # inches
    max_height: float = 10.0,  # inches
    min_height: float = 4.0,  # inches
) -> Tuple[float, float]:
    """
    Calculate figure size that matches geographic aspect ratio.

    This prevents aspect ratio conflicts between matplotlib's figure
    and the geographic extent of the map.

    Parameters
    ----------
    display_bounds : tuple
        (min_lon, max_lon, min_lat, max_lat) in degrees
    base_width : float, optional
        Preferred figure width in inches (default 12.0)
    max_height : float, optional
        Maximum figure height in inches (default 10.0)
    min_height : float, optional
        Minimum figure height in inches (default 4.0)

    Returns
    -------
    tuple
        (width, height) in inches optimized for geographic extent
    """
    min_lon, max_lon, min_lat, max_lat = display_bounds

    # Calculate geographic ranges
    lat_range = max_lat - min_lat
    lon_range = max_lon - min_lon

    if lat_range <= 0 or lon_range <= 0:
        return (base_width, base_width * 0.75)  # Default 4:3 ratio

    # Adjust longitude range for latitude compression at mid-latitude
    mid_lat = (min_lat + max_lat) / 2
    mid_lat = max(-85.0, min(85.0, mid_lat))  # Clamp to avoid polar issues
    cos_lat = math.cos(math.radians(abs(mid_lat)))
    effective_lon_range = lon_range * cos_lat

    # Calculate geographic aspect ratio (width / height)
    geo_aspect = effective_lon_range / lat_range
    geo_aspect = max(0.1, min(geo_aspect, 10.0))  # Reasonable bounds

    # Calculate figure dimensions
    width = base_width
    height = width / geo_aspect

    # Apply constraints
    if height > max_height:
        height = max_height
        width = height * geo_aspect
    elif height < min_height:
        height = min_height
        width = height * geo_aspect

    logger.debug(
        f"Geographic aspect ratio: {geo_aspect:.2f}, Figure size: {width:.1f}x{height:.1f}"
    )
    return (width, height)


def extract_points_from_timeline(timeline) -> List[Dict[str, Any]]:
    """
    Extract point features (stations, ports) from timeline activities.

    Parameters
    ----------
    timeline : List[ActivityRecord]
        List of timeline activity records

    Returns
    -------
    List[Dict[str, Any]]
        List of point dictionaries with keys: name, lat, lon, entity_type, operation_type, action, depth
    """
    points = []

    for activity in timeline:
        # Extract coordinates and metadata from timeline activity
        if (
            "lat" in activity
            and "lon" in activity
            and activity["lat"] is not None
            and activity["lon"] is not None
            and not (activity["lat"] == 0.0 and activity["lon"] == 0.0)
        ):  # Skip zero coordinates

            # Determine entity type from activity type
            activity_type = activity.get("activity", "Unknown")
            if activity_type == "Port_Departure":
                entity_type = "departure_port"
                operation_type = "port"
            elif activity_type == "Port_Arrival":
                entity_type = "arrival_port"
                operation_type = "port"
            elif activity_type in ["Station"]:
                entity_type = "station"
                operation_type = activity.get(
                    "operation_type", activity.get("op_type", "station")
                )
            elif activity_type in ["Mooring"]:
                entity_type = "mooring"
                operation_type = activity.get(
                    "operation_type", activity.get("op_type", "mooring")
                )
            elif activity_type in ["Transit"]:
                # Skip transit activities - they should be shown as lines, not points
                continue
            elif activity.get("category") == "area_operation":
                # Skip area operations - they should be shown as polygons, not points
                continue
            else:
                entity_type = "activity"
                operation_type = activity.get(
                    "operation_type", activity.get("op_type", "unknown")
                )

            # Extract clean port name for port activities
            if activity_type in ["Port_Departure", "Port_Arrival"]:
                # Extract port name from verbose labels like "Departure: Halifax to Operations"
                label = activity.get("label", f"{activity_type}_{len(points)+1}")
                if ":" in label and " to " in label:
                    # Extract port name between ":" and " to "
                    if activity_type == "Port_Departure":
                        # "Departure: Halifax to Operations" -> "Halifax"
                        port_name = label.split(": ", 1)[1].split(" to ", 1)[0]
                    else:  # Port_Arrival
                        # "Arrival: Operations to Halifax" -> "Halifax"
                        port_name = label.split(" to ", 1)[1]
                else:
                    port_name = label
            else:
                port_name = activity.get("label", f"{activity_type}_{len(points)+1}")

            points.append(
                {
                    "name": port_name,
                    "lat": float(activity["lat"]),
                    "lon": float(activity["lon"]),
                    "entity_type": entity_type,
                    "operation_type": operation_type,
                    "action": activity.get("action", None),
                    "depth": activity.get("depth", activity.get("water_depth", None)),
                }
            )

    return points


def extract_lines_from_timeline(timeline) -> List[Dict[str, Any]]:
    """
    Extract line features (cruise tracks) from timeline activities by connecting sequential positions.

    Parameters
    ----------
    timeline : List[ActivityRecord]
        List of timeline activity records

    Returns
    -------
    List[Dict[str, Any]]
        List of line dictionaries with waypoints showing cruise track progression
    """
    lines = []

    # Create cruise track by connecting sequential activities with coordinates
    waypoints = []
    for activity in timeline:
        if (
            "lat" in activity
            and "lon" in activity
            and activity["lat"] is not None
            and activity["lon"] is not None
            and not (activity["lat"] == 0.0 and activity["lon"] == 0.0)
        ):  # Skip zero coordinates
            waypoints.append(
                {"lat": float(activity["lat"]), "lon": float(activity["lon"])}
            )

    # Only create line if we have at least 2 waypoints
    if len(waypoints) >= 2:
        lines.append(
            {
                "name": "Cruise Track",
                "waypoints": waypoints,
                "entity_type": "cruise_track",
                "operation_type": "cruise_track",
                "action": None,
            }
        )

    return lines


def extract_map_data(data_source, source_type="cruise", include_ports=True):
    """
    Extract all map features (points, lines, areas) from cruise config or timeline.

    Parameters
    ----------
    data_source : Cruise or list
        Either a Cruise object or timeline list
    source_type : str, optional
        "cruise" for Cruise object, "timeline" for timeline list
    include_ports : bool, optional
        Whether to include departure/arrival ports (default True)

    Returns
    -------
    dict
        Dictionary with keys: points, lines, areas, title, bounds
    """
    if source_type == "cruise":
        # Extract structured data using new functions
        points = extract_points_from_cruise(data_source, include_ports=include_ports)
        lines = extract_lines_from_cruise(data_source)
        areas = extract_areas_from_cruise(data_source)
        title = f"{data_source.config.cruise_name}\nCruise Track with Bathymetry"

    elif source_type == "timeline":
        # Handle both dictionary with 'timeline' key and direct list formats
        if isinstance(data_source, dict) and "timeline" in data_source:
            timeline_data = data_source["timeline"]
            # Try to access cruise object for area geometry
            cruise_obj = data_source.get("cruise", None)
        elif isinstance(data_source, list):
            timeline_data = data_source
            cruise_obj = None
        else:
            timeline_data = []
            cruise_obj = None

        # Extract points from timeline activities
        points = extract_points_from_timeline(timeline_data)

        # Extract lines from both sources to get complete transit picture
        if cruise_obj:
            # Get scientific transits from cruise config
            scientific_lines = extract_lines_from_cruise(cruise_obj)
            # Get navigation transits from timeline
            navigation_lines = extract_lines_from_timeline(timeline_data)
            # Combine both types of lines
            lines = scientific_lines + navigation_lines
            areas = extract_areas_from_cruise(cruise_obj)
        else:
            lines = extract_lines_from_timeline(timeline_data)
            areas = extract_areas_from_timeline(timeline_data)

        title = "Cruise Schedule\nOperations Timeline with Bathymetry"

    else:
        raise ValueError(f"Unknown source_type: {source_type}")

    # Calculate bounds from all coordinate data
    all_lats = []
    all_lons = []

    # Add point coordinates
    for point in points:
        all_lats.append(point["lat"])
        all_lons.append(point["lon"])

    # Add line coordinates
    for line in lines:
        for waypoint in line["waypoints"]:
            all_lats.append(waypoint["lat"])
            all_lons.append(waypoint["lon"])

    # Add area coordinates
    for area in areas:
        for corner in area["corners"]:
            all_lats.append(corner["lat"])
            all_lons.append(corner["lon"])

    # Calculate bounds
    bounds = None
    if all_lats and all_lons:
        bounds = (min(all_lons), max(all_lons), min(all_lats), max(all_lats))

    return {
        "points": points,
        "lines": lines,
        "areas": areas,
        "title": title,
        "bounds": bounds,
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

        logger.info("Added bathymetry contours covering full region")
        return cs_filled  # Return contour object for colorbar creation later

    except Exception as e:
        logger.warning(f"Bathymetry plotting failed: {e}")
        return False


def plot_cruise_elements(
    ax, map_data: Dict[str, Any], display_bounds: Tuple[float, float, float, float]
):
    """
    Plot stations, ports, transit lines, and areas on a matplotlib axis using structured map data.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The matplotlib axis to plot on
    map_data : Dict[str, Any]
        Structured map data with 'points', 'lines', 'areas', 'title', and 'bounds'
    display_bounds : tuple
        (min_lon, max_lon, min_lat, max_lat) for display area
    """
    from cruiseplan.utils.plot_config import get_plot_style

    # Set display limits
    final_min_lon, final_max_lon, final_min_lat, final_max_lat = display_bounds
    ax.set_xlim(final_min_lon, final_max_lon)
    ax.set_ylim(final_min_lat, final_max_lat)

    # Set geographic aspect ratio
    mid_lat_deg = (final_min_lat + final_max_lat) / 2
    mid_lat_deg = max(-85.0, min(85.0, mid_lat_deg))
    mid_lat_rad = math.radians(mid_lat_deg)
    try:
        aspect = 1.0 / math.cos(mid_lat_rad)
    except ZeroDivisionError:
        aspect = 1.0
    aspect = max(1.0, min(aspect, 10.0))
    ax.set_aspect(aspect, adjustable="box")

    # Track which legend labels have been added
    legend_labels_added = set()

    # Plot areas (polygons) first so they appear behind other elements
    for area in map_data.get("areas", []):
        if not area.get("corners"):
            continue

        # Extract polygon coordinates
        poly_lons = [corner["lon"] for corner in area["corners"]]
        poly_lats = [corner["lat"] for corner in area["corners"]]

        # Close the polygon by connecting back to first point
        poly_lons.append(poly_lons[0])
        poly_lats.append(poly_lats[0])

        # Get styling for areas
        style = get_plot_style("area", area.get("operation_type"), area.get("action"))

        # Plot filled polygon
        ax.fill(
            poly_lons,
            poly_lats,
            facecolor=style.get("facecolor", "#FFD700"),
            edgecolor=style.get("edgecolor", "#B8860B"),
            alpha=style.get("alpha", 0.4),
            linewidth=style.get("linewidth", 2),
            zorder=2,
        )

        # Add to legend if not already added
        label = style.get("label", "Areas")
        if label not in legend_labels_added:
            ax.fill(
                [],
                [],
                facecolor=style.get("facecolor", "#FFD700"),
                edgecolor=style.get("edgecolor", "#B8860B"),
                alpha=style.get("alpha", 0.4),
                label=label,
            )
            legend_labels_added.add(label)

    # Plot lines (scientific transits)
    for line in map_data.get("lines", []):
        if not line.get("waypoints") or len(line["waypoints"]) < 2:
            continue

        # Extract line coordinates
        line_lons = [wp["lon"] for wp in line["waypoints"]]
        line_lats = [wp["lat"] for wp in line["waypoints"]]

        # Get styling for transits
        style = get_plot_style(
            "transit", line.get("operation_type"), line.get("action")
        )

        # Plot line
        ax.plot(
            line_lons,
            line_lats,
            color=style.get("color", "#0000FF"),
            linewidth=style.get("linewidth", 3),
            linestyle=style.get("linestyle", "-"),
            alpha=style.get("alpha", 0.7),
            zorder=5,
        )

        # Add to legend if not already added
        label = style.get("label", "Scientific Transits")
        if label not in legend_labels_added:
            ax.plot(
                [],
                [],
                color=style.get("color", "#0000FF"),
                linewidth=style.get("linewidth", 3),
                linestyle=style.get("linestyle", "-"),
                alpha=style.get("alpha", 0.7),
                label=label,
            )
            legend_labels_added.add(label)

    # Plot points (stations, moorings, ports)
    for point in map_data.get("points", []):
        lat, lon = point["lat"], point["lon"]
        if lat == 0.0 and lon == 0.0:
            continue

        # Get styling based on entity type and operation type
        style = get_plot_style(
            point["entity_type"], point.get("operation_type"), point.get("action")
        )

        # Plot point
        ax.scatter(
            lon,
            lat,
            s=style.get("size", 80),
            c=style.get("color", "#FF0000"),
            marker=style.get("marker", "o"),
            alpha=style.get("alpha", 0.8),
            edgecolors=style.get("edgecolor", "black"),
            linewidth=style.get("linewidth", 1),
            zorder=10,
        )

        # Add point name annotation for all scientific operations
        ax.annotate(
            point["name"],
            (lon, lat),
            xytext=(3, 3),
            textcoords="offset points",
            fontsize=8,
            color="black",
            weight="bold",
            zorder=20,
        )

        # Add to legend if not already added
        label = style.get("label", point["entity_type"].title())
        if label not in legend_labels_added:
            ax.scatter(
                [],
                [],
                s=style.get("size", 80),
                c=style.get("color", "#FF0000"),
                marker=style.get("marker", "o"),
                alpha=style.get("alpha", 0.8),
                edgecolors=style.get("edgecolor", "black"),
                linewidth=style.get("linewidth", 1),
                label=label,
            )
            legend_labels_added.add(label)

    # Set labels and title
    ax.set_xlabel("Longitude (°)", fontsize=12)
    ax.set_ylabel("Latitude (°)", fontsize=12)
    ax.set_title(
        map_data.get("title", "Cruise Plan Map"), fontsize=14, fontweight="bold"
    )

    # Add grid and legend
    ax.grid(True, alpha=0.3, zorder=0)
    if legend_labels_added:
        ax.legend(
            loc="upper right", fontsize=10, frameon=True, fancybox=True, shadow=True
        )

    logger.info(
        f"Map displayed with {len(map_data.get('points', []))} points, {len(map_data.get('lines', []))} lines, {len(map_data.get('areas', []))} areas"
    )


def generate_map(
    data_source,
    source_type: str = "cruise",
    output_file: Union[str, Path] = "cruise_map.png",
    bathymetry_source: str = "gebco2025",
    bathymetry_stride: int = 5,
    bathymetry_dir: str = "data",
    show_plot: bool = False,
    figsize: Tuple[float, float] = (10, 8.1),
    include_ports: bool = True,
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
    include_ports : bool, optional
        Whether to include departure/arrival ports in the map. Default is True.

    Returns
    -------
    Path or None
        The absolute path to the generated PNG map file, or None if failed.
    """
    # Extract map data using unified function
    map_data = extract_map_data(data_source, source_type, include_ports=include_ports)

    if not map_data["points"]:
        logger.warning(f"No coordinates found in {source_type} data")
        return None

    # Ensure output_file is a Path object
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Calculate display bounds from the bounds in map_data
    bounds = map_data.get("bounds")
    if bounds:
        min_lon, max_lon, min_lat, max_lat = bounds
    else:
        # Fallback: calculate from points
        all_lats = [point["lat"] for point in map_data["points"]]
        all_lons = [point["lon"] for point in map_data["points"]]
        if not all_lats:
            logger.warning("No valid coordinates found")
            return None
        min_lat, max_lat = min(all_lats), max(all_lats)
        min_lon, max_lon = min(all_lons), max(all_lons)

    # Add padding to bounds
    padding_deg = 5.0  # degrees padding around data points
    min_lat -= padding_deg
    max_lat += padding_deg
    min_lon -= padding_deg
    max_lon += padding_deg

    display_bounds = (min_lon, max_lon, min_lat, max_lat)

    logger.info(
        f"Display bounds: {min_lat:.1f}°-{max_lat:.1f}°N, {min_lon:.1f}°-{max_lon:.1f}°E"
    )

    # Calculate optimal figure size to match geographic extent
    optimal_figsize = calculate_optimal_figsize(display_bounds)

    # Override the passed figsize with the optimal one for this geographic extent
    if figsize == (10, 8.1):  # Only override if using default figsize
        figsize = optimal_figsize
        logger.info(
            f"Using dynamic figure size: {figsize[0]:.1f}x{figsize[1]:.1f} inches"
        )

    # Calculate bathymetry bounds with additional padding for coverage
    min_lon, max_lon, min_lat, max_lat = display_bounds
    bathy_padding = (
        3.0  # Additional padding for bathymetry coverage beyond display area
    )
    bathy_limits = (
        min_lon - bathy_padding,  # min_lon
        max_lon + bathy_padding,  # max_lon
        min_lat - bathy_padding,  # min_lat
        max_lat + bathy_padding,  # max_lat
    )

    # Create figure and axis with optimized size
    fig, ax = plt.subplots(figsize=figsize)

    # Plot bathymetry and get contour object for colorbar
    cs_filled = plot_bathymetry(
        ax, *bathy_limits, bathymetry_source, bathymetry_stride, bathymetry_dir
    )

    # Plot cruise elements using new structured data (this applies the final aspect ratio)
    plot_cruise_elements(ax, map_data, display_bounds)

    # Apply tight layout BEFORE colorbar to finalize axes positioning
    plt.tight_layout()

    # Create colorbar with direct axes manipulation for full height
    if cs_filled and cs_filled is not False:
        # Get current axes position after layout is finalized
        fig = ax.get_figure()
        pos = ax.get_position()

        # Create colorbar axes manually with exact positioning
        # Position: right of main axes, 2% width, full height, small gap
        cbar_ax = fig.add_axes(
            [
                pos.x1
                + 0.02,  # X position: right edge + slightly larger gap (2% of figure width)
                pos.y0,  # Y position: same as main axes bottom
                0.02,  # Width: 2% of figure width
                pos.height,  # Height: exact same as main axes
            ]
        )

        # Create colorbar in the manually positioned axes
        cbar = plt.colorbar(cs_filled, cax=cbar_ax)
        cbar.set_label("Depth (m)", rotation=270, labelpad=15)

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
    include_ports: bool = True,
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
    include_ports : bool, optional
        Whether to include departure/arrival ports in the map. Default is True.

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
        include_ports=include_ports,
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
    timeline_data = {"timeline": timeline, "cruise": config}

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
