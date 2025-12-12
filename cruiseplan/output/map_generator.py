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
from pathlib import Path
from typing import Any, Dict, List, Union

import folium

logger = logging.getLogger(__name__)


def generate_cruise_map(
    tracks: List[Dict[str, Any]], output_file: Union[str, Path] = "cruise_map.html"
) -> Path:
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
