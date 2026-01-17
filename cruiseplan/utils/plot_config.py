"""
Centralized plotting configuration for consistent visualization across cruiseplan.

This module provides:
1. Colormaps for bathymetry and oceanographic data (moved from interactive/colormaps.py)
2. Centralized styling configuration for all plot elements
3. Symbol definitions for consistent plotting across PNG, KML, and interactive maps
"""

from typing import Any, Optional

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

# Note: Colormap constants defined after function definitions to avoid forward references

# ============================================================================
# MATPLOTLIB DEPENDENCY MANAGEMENT
# ============================================================================


def check_matplotlib_available() -> None:
    """
    Check that matplotlib is available for interactive plotting.

    Raises
    ------
    ImportError
        If matplotlib is not available with installation instructions
    """
    try:
        import matplotlib.pyplot  # noqa: F401
    except ImportError:
        raise ImportError(
            "Interactive plotting requires matplotlib. "
            "Install with: pip install matplotlib"
        )


# ============================================================================
# COLORMAPS
# ============================================================================


def create_bathymetry_colormap() -> mcolors.LinearSegmentedColormap:
    """
    Create the Flemish Cap bathymetry colormap matching the CPT specification.

    This creates a colormap with constant colors within each depth range,
    exactly matching the CPT specification.

    Returns
    -------
    matplotlib.colors.LinearSegmentedColormap
        Bathymetry colormap with proper depth-color mapping
    """
    # Overall depth range for normalization
    depth_min, depth_max = -8000, 200

    # Create color dictionary for LinearSegmentedColormap
    # Each segment needs: (position, start_color, end_color)
    # For constant colors within ranges, start_color == end_color
    cdict = {"red": [], "green": [], "blue": [], "alpha": []}

    # Define segments with constant colors within each range
    segments = [
        # (depth_start, depth_end, hex_color)
        (-8000, -7000, "#032d44"),  # Abyssal depths (darkest blue)
        (-7000, -6000, "#2A5780"),  # Very deep (darker blue)
        (-6000, -5000, "#2A5780"),  # Very deep (darker blue)
        (-5000, -4000, "#3E8AA4"),  # Deep water (blue)
        (-4000, -3000, "#469AB2"),  # Deep water (blue)
        (-3000, -2000, "#4FAEC5"),  # Deep shelf edge (darker blue)
        (-2000, -1000, "#5DB9D2"),  # Moderate depths (medium blue)
        (-1000, -500, "#77C1D4"),  # Shallow continental shelf (light blue)
        (-500, -200, "#94CBD1"),  # Shallow continental shelf (light blue)
        (-200, 0, "#addbd1"),  # Very shallow water (very light blue/cyan)
        (0, 200, "#F7CE55"),  # Land/shallow areas (yellow/tan)
    ]

    for depth_start, depth_end, hex_color in segments:
        # Convert hex to RGB
        r = int(hex_color[1:3], 16) / 255.0
        g = int(hex_color[3:5], 16) / 255.0
        b = int(hex_color[5:7], 16) / 255.0

        # Normalize depths to 0-1 range
        pos_start = (depth_start - depth_min) / (depth_max - depth_min)
        pos_end = (depth_end - depth_min) / (depth_max - depth_min)

        # Add constant color segments
        cdict["red"].append((pos_start, r, r))
        cdict["red"].append((pos_end, r, r))
        cdict["green"].append((pos_start, g, g))
        cdict["green"].append((pos_end, g, g))
        cdict["blue"].append((pos_start, b, b))
        cdict["blue"].append((pos_end, b, b))
        cdict["alpha"].append((pos_start, 1.0, 1.0))
        cdict["alpha"].append((pos_end, 1.0, 1.0))

    cmap = mcolors.LinearSegmentedColormap("bathymetry_custom", cdict, 256)

    # Set under and over colors
    # Under: for depths deeper than -8000m (darker than colormap range)
    cmap.set_under("#032d44")  # Dark blue for abyssal depths
    # Over: for elevations higher than 200m (shallower than colormap range)
    cmap.set_over("#F7CE55")  # Yellow for land areas

    return cmap


def get_colormap(name: str) -> mcolors.Colormap:
    """
    Get a colormap by name.

    Parameters
    ----------
    name : str
        Name of the colormap ('bathymetry' or 'blues_r')

    Returns
    -------
    matplotlib.colors.Colormap
        The requested colormap

    Raises
    ------
    ValueError
        If the colormap name is not recognized
    """
    if name not in AVAILABLE_COLORMAPS:
        available = list(AVAILABLE_COLORMAPS.keys())
        raise ValueError(f"Unknown colormap '{name}'. Available: {available}")

    return AVAILABLE_COLORMAPS[name]


# ============================================================================
# PLOT STYLING CONFIGURATION
# ============================================================================

# Centralized plot styling for all entity types
PLOT_STYLES = {
    # Ports
    "departure_port": {
        "marker": "P",  # plus (filled)
        "color": "#8B008B",  # dark purple
        "edgecolor": "#4B0082",  # indigo
        "size": 60,
        "alpha": 0.9,
        "linewidth": 1,
        "label": "Port",
    },
    "arrival_port": {
        "marker": "P",  # plus (filled)
        "color": "#8B008B",  # dark purple
        "edgecolor": "#4B0082",  # indigo
        "size": 60,
        "alpha": 0.9,
        "linewidth": 1,
        "label": "",
    },
    # Stations
    "station": {
        "marker": "o",  # circle
        "color": "#FF0000",  # red
        "edgecolor": "#800000",  # maroon
        "size": 60,
        "alpha": 0.8,
        "linewidth": 1,
        "label": "Stations",
    },
    "CTD": {
        "marker": "o",  # circle
        "color": "#FF0000",  # red
        "edgecolor": "#800000",  # maroon
        "size": 20,
        "alpha": 0.8,
        "linewidth": 1.5,
        "label": "CTD Stations",
    },
    # Moorings
    "mooring": {
        "marker": "*",  # star
        "color": "#DED833",  # yellow
        "edgecolor": "#020202",  # black
        "size": 110,
        "alpha": 0.8,
        "linewidth": 1,
        "label": "Moorings",
    },
    # Scientific Transits (lines)
    "transit": {
        "color": "#0000FF",  # blue
        "linewidth": 3,
        "linestyle": "-",  # solid
        "alpha": 0.7,
        "label": "Scientific Transits",
    },
    "underway": {
        "color": "#0000FF",  # blue
        "linewidth": 2,
        "linestyle": "-",  # solid
        "alpha": 0.7,
        "label": "Underway Operations",
    },
    "ADCP": {
        "color": "#FF6600",  # orange
        "linewidth": 4,  # thicker for visibility
        "linestyle": "-",  # solid
        "alpha": 0.8,
        "label": "ADCP Surveys",
    },
    # Navigation cruise tracks (dashed lines)
    "cruise_track": {
        "color": "#4169E1",  # royal blue
        "linewidth": 1,
        "linestyle": "--",  # dashed
        "alpha": 0.6,
        "label": "Cruise Track",
    },
    # Areas (polygons)
    "area": {
        "facecolor": "#FFD700",  # gold
        "edgecolor": "#B8860B",  # dark goldenrod
        "alpha": 0.4,
        "linewidth": 2,
        "linestyle": "-",
        "label": "Survey Areas",
    },
    "survey": {
        "facecolor": "#FFD700",  # gold
        "edgecolor": "#B8860B",  # dark goldenrod
        "alpha": 0.4,
        "linewidth": 2,
        "linestyle": "-",
        "label": "Survey Areas",
    },
    "bathymetry": {
        "facecolor": "#26901D",  # green
        "edgecolor": "#215D11",  # dark green
        "alpha": 0.3,
        "linewidth": 1,
        "linestyle": "-",
        "label": "Bathymetry Survey",
    },
}


def get_plot_style(
    entity_type: str, operation_type: Optional[str] = None, action: Optional[str] = None
) -> dict[str, Any]:
    """
    Get plot styling for a specific entity type.

    Parameters
    ----------
    entity_type : str
        Type of entity ('station', 'mooring', 'transit', 'area', 'departure_port', 'arrival_port')
    operation_type : str, optional
        Operation type (e.g., 'CTD', 'mooring', 'underway', 'survey')
    action : str, optional
        Specific action (e.g., 'profile', 'deployment', 'ADCP', 'bathymetry')

    Returns
    -------
    Dict[str, Any]
        Dictionary of matplotlib styling parameters
    """
    # Priority order: action -> operation_type -> entity_type
    for key in [action, operation_type, entity_type]:
        if key and key in PLOT_STYLES:
            return PLOT_STYLES[key].copy()

    # Fallback to generic styling
    if entity_type.endswith("_port"):
        return PLOT_STYLES["departure_port"].copy()
    elif entity_type in ["station", "mooring", "transit", "area"]:
        return PLOT_STYLES[entity_type].copy()
    else:
        # Ultimate fallback
        return PLOT_STYLES["station"].copy()


def get_legend_entries() -> dict[str, dict[str, Any]]:
    """
    Get legend entries for all plot styles.

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Dictionary mapping labels to style dictionaries for legend creation
    """
    legend_entries = {}
    for style_dict in PLOT_STYLES.values():
        if "label" in style_dict:
            legend_entries[style_dict["label"]] = style_dict.copy()

    return legend_entries


# ============================================================================
# GREAT CIRCLE ROUTE UTILITIES
# ============================================================================


def interpolate_great_circle_position(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float, fraction: float
) -> tuple[float, float]:
    """
    Interpolate position along great circle route using spherical geometry.

    This function is useful for generating smooth great circle routes for map visualization,
    which provides more accurate geographic representation than straight line interpolation.

    Parameters
    ----------
    start_lat : float
        Starting latitude in decimal degrees.
    start_lon : float
        Starting longitude in decimal degrees.
    end_lat : float
        Ending latitude in decimal degrees.
    end_lon : float
        Ending longitude in decimal degrees.
    fraction : float
        Interpolation fraction (0.0 = start, 1.0 = end).

    Returns
    -------
    Tuple[float, float]
        Interpolated (latitude, longitude) in decimal degrees.
    """
    import math

    # Convert degrees to radians
    lat1 = math.radians(start_lat)
    lon1 = math.radians(start_lon)
    lat2 = math.radians(end_lat)
    lon2 = math.radians(end_lon)

    # Calculate angular distance
    d = math.acos(
        min(
            1,
            math.sin(lat1) * math.sin(lat2)
            + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1),
        )
    )

    # Handle edge case for very short distances
    if d < 1e-9:
        return start_lat, start_lon

    # Spherical interpolation
    A = math.sin((1 - fraction) * d) / math.sin(d)
    B = math.sin(fraction * d) / math.sin(d)

    x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
    y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
    z = A * math.sin(lat1) + B * math.sin(lat2)

    # Convert back to lat/lon
    lat_result = math.atan2(z, math.sqrt(x * x + y * y))
    lon_result = math.atan2(y, x)

    return math.degrees(lat_result), math.degrees(lon_result)


# ============================================================================
# PRE-DEFINED COLORMAP CONSTANTS
# ============================================================================

# Pre-defined colormaps (defined here to avoid forward references)
BATHYMETRY_COLORMAP = create_bathymetry_colormap()
BLUES_R_COLORMAP = plt.cm.Blues_r  # Fallback to matplotlib's Blues_r

# Available colormaps dictionary
AVAILABLE_COLORMAPS = {
    "bathymetry": BATHYMETRY_COLORMAP,
    "blues_r": BLUES_R_COLORMAP,
}
