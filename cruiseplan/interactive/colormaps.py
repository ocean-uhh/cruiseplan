"""
Custom colormaps for cruiseplan visualization.

This module provides custom colormaps for bathymetry and other oceanographic
data visualization, including support for GMT-style CPT files.
"""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np


def create_bathymetry_colormap() -> mcolors.LinearSegmentedColormap:
    """
    Create a custom bathymetry colormap based on the Flemish Cap CPT.

    This colormap provides a more oceanographically-appropriate color scheme
    with deeper blues for abyssal depths and yellows for land areas.

    Returns
    -------
    matplotlib.colors.LinearSegmentedColormap
        Custom colormap for bathymetry visualization
    """
    # Color definitions from the Flemish Cap CPT
    # Format: (depth, hex_color)
    color_points = [
        (-8000, "#032d44"),  # Abyssal depths (darkest blue)
        (-7000, "#2A5780"),  # Very deep (darker blue)
        (-6000, "#2A5780"),
        (-5000, "#3E8AA4"),  # Deep water (blue)
        (-4000, "#469AB2"),
        (-3000, "#4FAEC5"),  # Deep shelf edge (darker blue)
        (-2000, "#5DB9D2"),  # Moderate depths (medium blue)
        (-1000, "#77C1D4"),  # Shallow continental shelf (light blue)
        (-500, "#94CBD1"),
        (-200, "#addbd1"),  # Very shallow water (very light blue/cyan)
        (0, "#F7CE55"),  # Land/shallow areas (yellow/tan)
        (200, "#F7CE55"),  # Land areas
    ]

    # Normalize depths to 0-1 range for colormap
    depths = np.array([point[0] for point in color_points])
    colors = [point[1] for point in color_points]

    # Create normalization from depth range to 0-1
    # Using a reasonable depth range from -8000 to 200
    depth_min, depth_max = -8000, 200
    normalized_positions = (depths - depth_min) / (depth_max - depth_min)

    # Create the colormap
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "bathymetry_flemish_cap", list(zip(normalized_positions, colors)), N=256
    )

    return cmap


def create_bathymetry_colormap_v2() -> mcolors.LinearSegmentedColormap:
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


# Pre-defined colormaps
BATHYMETRY_COLORMAP = create_bathymetry_colormap_v2()
BLUES_R_COLORMAP = plt.cm.Blues_r  # Fallback to matplotlib's Blues_r

# Available colormaps dictionary
AVAILABLE_COLORMAPS = {
    "bathymetry": BATHYMETRY_COLORMAP,
    "blues_r": BLUES_R_COLORMAP,
}


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


def load_cpt_colormap(cpt_file: str) -> mcolors.LinearSegmentedColormap:
    """
    Load a colormap from a GMT-style CPT file.

    Parameters
    ----------
    cpt_file : str
        Path to the CPT file

    Returns
    -------
    matplotlib.colors.LinearSegmentedColormap
        Colormap loaded from the CPT file

    Note
    ----
    This is a placeholder for future CPT file support.
    Currently only supports the hardcoded Flemish Cap colormap.
    """
    # TODO: Implement full CPT file parsing
    # For now, return the custom bathymetry colormap
    return create_bathymetry_colormap_v2()
