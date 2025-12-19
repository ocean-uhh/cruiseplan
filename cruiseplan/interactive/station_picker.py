"""
Interactive station picker for oceanographic cruise planning.

This module provides the StationPicker class, which creates an interactive
matplotlib-based interface for planning cruise stations, transects, and survey areas.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt

# Local Integrations
from cruiseplan.data.bathymetry import DEPTH_CONTOURS, BathymetryManager
from cruiseplan.data.pangaea import merge_campaign_tracks
from cruiseplan.interactive.campaign_selector import CampaignSelector
from cruiseplan.interactive.colormaps import get_colormap

# --- NEW WIDGET IMPORTS (Instruction 1) ---
from cruiseplan.interactive.widgets import ModeIndicator, StatusDisplay
from cruiseplan.utils.config import (
    format_area_for_yaml,
    format_station_for_yaml,
    format_transect_for_yaml,
    save_cruise_config,
)


class StationPicker:
    """
    Interactive matplotlib-based tool for oceanographic cruise planning.

    Combines the original functionality with modern widget integration
    for enhanced user experience and accessibility. Provides interactive
    tools for placing stations, drawing transects, and defining survey areas
    on a bathymetric map with PANGAEA campaign data overlay.

    Attributes
    ----------
    MODES : List[str]
        Available interaction modes: navigation, point, line, area.
    KEY_BINDINGS : Dict[str, str]
        Keyboard shortcuts for mode switching and actions.
    mode : str
        Current interaction mode.
    output_file : str
        Path for saving cruise configuration.
    stations : List[Dict]
        List of planned sampling stations.
    transects : List[Dict]
        List of planned transects.
    areas : List[Dict]
        List of planned survey areas.
    history : List[Tuple[str, Dict, any]]
        Undo history for operations.
    campaigns : List[Dict]
        PANGAEA campaign data for visualization.
    fig : plt.Figure
        Main matplotlib figure.
    ax_map : plt.Axes
        Main map axes for bathymetry and planning elements.
    """

    # --- Class Attributes (Constants) ---
    MODES = ["navigation", "point", "line", "area"]
    KEY_BINDINGS = {
        "n": "navigation",
        "p": "point",
        "w": "point",  # Shortcut alias
        "l": "line",
        "s": "line",  # Shortcut alias
        "a": "area",
        "u": "remove_last",  # Undo
        "r": "remove",  # Remove by click
        "y": "save",  # Save to YAML
        "escape": "exit",
    }

    def __init__(
        self,
        campaign_data: Optional[List[Dict]] = None,
        output_file: str = "stations.yaml",
        bathymetry_stride: int = 10,
        bathymetry_source: str = "etopo2022",
        bathymetry_dir: str = "data",
        overwrite: bool = False,
    ):
        """
        Initialize the station picker interface.

        Parameters
        ----------
        campaign_data : List[Dict], optional
            Pre-loaded campaign track data from PANGAEA
        output_file : str
            Output filename for saving cruise plans
        bathymetry_stride : int
            Downsampling factor for bathymetry data (default: 10, higher = faster but less detailed)
        bathymetry_source : str
            Bathymetry data source: "etopo2022" or "gebco2025" (default: etopo2022)
        bathymetry_dir : str
            Directory containing bathymetry data files (default: "data")
        overwrite : bool
            Whether to overwrite existing files without prompting (default: False)
        """
        # CRITICAL FIX: Unbind default Matplotlib shortcuts
        self._unbind_default_keys()

        # State Management
        self.mode = "navigation"
        self.output_file = output_file
        self.overwrite = overwrite
        self.bathymetry_stride = bathymetry_stride
        self.bathymetry_colormap = get_colormap("bathymetry")

        # Initialize bathymetry manager with specified source and directory
        self.bathymetry = BathymetryManager(
            source=bathymetry_source, data_dir=bathymetry_dir
        )

        # Data Storage
        self.stations: List[Dict] = []
        self.transects: List[Dict] = []
        self.areas: List[Dict] = []
        self.history: List[Tuple[str, Dict, any]] = []

        # Line Drawing State
        self.line_start: Optional[Tuple[float, float]] = None
        self.temp_line_artist: Optional[any] = None
        self.rubber_band_artist: Optional[any] = None

        # Area Drawing State
        self.current_area_points: List[Tuple[float, float]] = []
        self.temp_area_artist: Optional[any] = None
        self.area_point_artists: List[any] = []

        # Data layers
        self.campaigns = merge_campaign_tracks(campaign_data) if campaign_data else []
        self.campaign_artists = {}

        # --- Widget Instances ---
        self.mode_indicator: Optional[ModeIndicator] = None
        self.status_display: Optional[StatusDisplay] = None
        self.campaign_selector: Optional[CampaignSelector] = None

        # UI Components
        self.fig = None
        self.ax_map = None
        self.ax_mode = None  # Mode indicator axis
        self.ax_status = None  # Status display axis
        self.ax_campaigns = None  # Campaign selector axis
        self.check_buttons = None

        self._setup_interface()
        self._setup_widgets()
        self._setup_callbacks()

        # Set initial view to CLI defaults (will be overridden by CLI args)
        self.ax_map.set_xlim(-65, -5)
        self.ax_map.set_ylim(45, 70)

        self._plot_bathymetry()
        self._plot_initial_campaigns()  # Fixed: Added missing call

        # Update displays
        self._update_status_display()
        self._update_aspect_ratio()

    def _unbind_default_keys(self):
        """Removes conflicting default keymaps from Matplotlib."""
        keys_to_remove = ["l", "L", "k", "K", "p", "o", "s"]

        for key in keys_to_remove:
            for param in [
                "keymap.yscale",
                "keymap.xscale",
                "keymap.pan",
                "keymap.zoom",
                "keymap.save",
            ]:
                if key in plt.rcParams.get(param, []):
                    try:
                        plt.rcParams[param].remove(key)
                    except ValueError:
                        pass

    def _setup_interface(self):
        """Create the matplotlib figure with subplot layout."""
        self.fig = plt.figure(figsize=(16, 9), constrained_layout=True)

        # Restore original 1:4:1 layout from PROJECT_SPECS.md
        gs = self.fig.add_gridspec(1, 3, width_ratios=[1, 4, 1])

        # Left panel: Campaigns
        self.ax_campaigns = self.fig.add_subplot(gs[0, 0])
        self.ax_campaigns.set_title("Campaigns")
        self.ax_campaigns.axis("off")

        # Center: Map (same as before)
        self.ax_map = self.fig.add_subplot(gs[0, 1])
        # Set title with bathymetry source information
        # Use a mapping dictionary for robust display name formatting
        BATHYMETRY_SOURCE_DISPLAY_NAMES = {
            "ETOPO2022": "ETOPO 2022",
            "GEBCO2025": "GEBCO 2025",
        }
        source_key = self.bathymetry.source.upper()
        bathymetry_source_display = BATHYMETRY_SOURCE_DISPLAY_NAMES.get(
            source_key, source_key
        )
        self.ax_map.set_title(
            f"Cruise Planning Map ({bathymetry_source_display} bathymetry)"
        )
        self.ax_map.set_xlabel("Longitude")
        self.ax_map.set_ylabel("Latitude")
        self.ax_map.grid(True, linestyle=":", alpha=0.3, color="black")

        # Right panel: Controls (subdivided into 3 sections)
        self.ax_controls = self.fig.add_subplot(gs[0, 2])
        self.ax_controls.set_title("Controls")
        self.ax_controls.axis("off")

        # Create sub-areas within the controls panel
        # Mode indicator (top 20%)
        self.mode_text = self.ax_controls.text(
            0.5,
            0.9,
            "Mode: NAVIGATION",
            transform=self.ax_controls.transAxes,
            ha="center",
            va="center",
            fontweight="bold",
            fontsize=12,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#2E8B57", alpha=0.3),
        )

        # Status display (middle 60%)
        self.status_text = self.ax_controls.text(
            0.05,
            0.7,
            "",
            transform=self.ax_controls.transAxes,
            va="top",
            fontfamily="monospace",
            fontsize=9,
        )

        # Instructions (bottom 20%)
        self.instructions_text = self.ax_controls.text(
            0.05,
            0.25,
            "KEYS:\n 'n': Navigation\n 'w','p': Point Mode\n 'l','s': Line Mode\n 'a': Area Mode*\n 'u': Undo\n 'r': Remove\n 'y': Save YAML\n 'esc': Quit\n\n*Press 'a' again\n to complete area",
            transform=self.ax_controls.transAxes,
            va="top",
            fontfamily="monospace",
            fontsize=9,
        )

    def _setup_widgets(self):
        """Initialize the custom widgets."""
        # Campaign selector widget (if campaigns available)
        if self.campaigns:
            self.campaign_selector = CampaignSelector(self.campaigns)
            self.campaign_selector.setup_ui(self.ax_campaigns)
            # Set reference to map axis for visibility updates
            self.campaign_selector.map_ax = self.ax_map
        else:
            # Fallback display when no campaigns
            self.ax_campaigns.text(
                0.1,
                0.5,
                "No Campaigns\nAvailable",
                transform=self.ax_campaigns.transAxes,
                fontsize=10,
                ha="left",
                va="center",
            )

        # Mode and status are now handled by text objects in _setup_interface()
        # Remove the separate widget instances for now to simplify

    def _setup_callbacks(self):
        """Connect matplotlib event handlers."""
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

        # Aspect Ratio Handling
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)
        self.fig.canvas.mpl_connect("resize_event", self._on_resize)

    def _plot_bathymetry(self):
        """Fetches and renders bathymetry contours."""
        # Get current view limits
        xmin, xmax = self.ax_map.get_xlim()
        ymin, ymax = self.ax_map.get_ylim()

        # Add a 10-degree buffer so user can pan slightly
        buffer = 10
        lon_min, lon_max = xmin - buffer, xmax + buffer
        lat_min, lat_max = ymin - buffer, ymax + buffer

        print("Rendering bathymetry layers...")

        xx, yy, zz = self.bathymetry.get_grid_subset(
            lat_min, lat_max, lon_min, lon_max, stride=self.bathymetry_stride
        )

        # 1. Filled Contours (The "Map" feel)
        # Use levels that match the colormap segments for proper color assignment
        cs = self.ax_map.contourf(
            xx,
            yy,
            zz,
            levels=[
                -8000,
                -7000,
                -6000,
                -5000,
                -4000,
                -3000,
                -2000,
                -1000,
                -500,
                -200,
                0,
                200,
            ],
            cmap=self.bathymetry_colormap,
            alpha=0.4,
            extend="both",  # Show under/over colors
        )

        # 2. Line Contours (The "Scientific" context)
        cs = self.ax_map.contour(
            xx, yy, zz, levels=DEPTH_CONTOURS, colors="gray", linewidths=0.5, alpha=0.6
        )

        # Add labels to contour lines
        self.ax_map.clabel(cs, inline=True, fontsize=8, fmt="%d")

    def _plot_initial_campaigns(self):
        """Plot campaign tracks if available."""
        if not self.campaigns:
            return

        from itertools import cycle

        # Style generator for visual distinction
        fill_colors = cycle(["#56B4E9", "#E69F00", "#009E73", "#CC79A7"])
        edge_colors = cycle(["k", "#D55E00", "#0072B2", "#F0E442", "#888888"])
        shapes = cycle(["o", "s", "^", "D", "v", "p"])

        for camp in self.campaigns:
            style = {
                "marker": next(shapes),
                "markerfacecolor": next(fill_colors),
                "markeredgecolor": next(edge_colors),
                "linestyle": "None",
                "markersize": 6,
                "markeredgewidth": 1.5,
                "alpha": 0.7,
            }

            # Ensure campaign has both 'label' and 'name' fields for compatibility
            camp_name = camp.get("name", camp.get("label", "Unknown"))
            camp["name"] = camp_name  # Ensure name field exists for CampaignSelector

            (artist,) = self.ax_map.plot(
                camp["longitude"], camp["latitude"], label=camp_name[:20], **style
            )
            self.campaign_artists[camp_name] = artist

            # Register artist with CampaignSelector if it exists
            if self.campaign_selector:
                self.campaign_selector.campaign_artists[camp_name] = artist

    # --- Mode Management Methods ---

    # --- Event Handlers ---

    def _on_key_press(self, event):
        """Handle keyboard shortcuts."""
        key = event.key.lower() if event.key else ""

        # Handle global shortcuts that work from anywhere
        if key in self.KEY_BINDINGS:
            action = self.KEY_BINDINGS[key]

            # Exit works globally - no need to be over the map
            if action == "exit":
                plt.close(self.fig)
                sys.exit(0)

            # Save also works globally for convenience
            elif action == "save":
                self._save_to_yaml()

        # Other shortcuts only work when mouse is over the map
        if event.inaxes != self.ax_map:
            return

        if key in self.KEY_BINDINGS:
            action = self.KEY_BINDINGS[key]

            if action in self.MODES:
                # Special case: If we're in area mode and press 'a' again, complete the current area
                if (
                    action == "area"
                    and self.mode == "area"
                    and len(self.current_area_points) >= 3
                ):
                    self._complete_area()
                else:
                    self.set_mode(action)
            elif action == "remove_last":
                self._remove_last_item()
            elif action == "remove":
                self.set_mode("remove")

        self._update_status_display()
        self.fig.canvas.draw_idle()

    def _on_click(self, event):
        """Handle mouse click events based on current mode."""
        if (
            event.button != 1
            or event.inaxes != self.ax_map
            or self.mode == "navigation"
        ):
            return

        if self.mode == "point":
            self._add_station(event.xdata, event.ydata)
        elif self.mode == "line":
            self._handle_line_click(event.xdata, event.ydata)
        elif self.mode == "area":
            self._handle_area_click(event.xdata, event.ydata)
        elif self.mode == "remove":
            station_data, _ = self._find_nearest_station(event.xdata, event.ydata)
            if station_data:
                self._remove_specific_station(station_data)
            else:
                self._update_status_display(
                    message="No station close enough to remove."
                )

    def _on_mouse_move(self, event):
        """Handle mouse movement for real-time coordinate and depth display."""
        if event.inaxes != self.ax_map:
            return

        lat, lon = event.ydata, event.xdata
        if lat is None or lon is None:
            return

        # Get depth from bathymetry
        depth = self.bathymetry.get_depth_at_point(lat, lon)

        # Update status display with current coordinates
        status_msg = ""
        if self.mode == "line" and self.line_start is not None:
            status_msg = "Click to set end point"

        self._update_status_display(lat, lon, depth, message=status_msg)

        # Handle rubber band line drawing for line mode
        if self.mode == "line" and self.line_start is not None:
            start_lon, start_lat = self.line_start

            if self.rubber_band_artist is None:
                (self.rubber_band_artist,) = self.ax_map.plot(
                    [start_lon, lon],
                    [start_lat, lat],
                    "b--",
                    alpha=0.6,
                    linewidth=1.5,
                    zorder=15,
                )
            else:
                self.rubber_band_artist.set_data([start_lon, lon], [start_lat, lat])

            self.fig.canvas.draw_idle()

    def _on_release(self, event):
        """Handle mouse button release events."""
        if event.inaxes == self.ax_map:
            self._update_aspect_ratio()

    def _on_resize(self, event):
        """Handle figure resize events."""
        self._update_aspect_ratio()

    # --- Mode and State Management ---

    def set_mode(self, new_mode: str):
        """
        Change the current interaction mode and update the display.

        Parameters
        ----------
        new_mode : str
            New interaction mode. Must be one of MODES or "remove".
        """
        if new_mode in self.MODES or new_mode == "remove":
            self.mode = new_mode
            self._update_mode_display()
            if new_mode != "line":
                self._reset_line_state()
            if new_mode != "area":
                self._reset_area_state()
        else:
            print(f"Warning: Attempted to set invalid mode: {new_mode}")

    def _reset_line_state(self):
        """Reset line drawing state."""
        self.line_start = None

        if hasattr(self, "temp_line_artist") and self.temp_line_artist:
            self.temp_line_artist.remove()
            self.temp_line_artist = None

        if self.rubber_band_artist:
            self.rubber_band_artist.remove()
            self.rubber_band_artist = None

        self.ax_map.figure.canvas.draw_idle()

    # --- Operation Management ---

    def _add_station(self, lon, lat):
        """
        Add a new station at the specified coordinates.

        Parameters
        ----------
        lon : float
            Longitude coordinate.
        lat : float
            Latitude coordinate.
        """
        depth = self.bathymetry.get_depth_at_point(lat, lon)
        (artist,) = self.ax_map.plot(
            lon, lat, "ro", markersize=8, markeredgecolor="k", zorder=10
        )

        data = {"lat": lat, "lon": lon, "depth": abs(depth)}
        self.stations.append(data)
        self.history.append(("station", data, artist))
        self._update_status_display(lat, lon, depth, message="Station added.")

    def _handle_line_click(self, lon, lat):
        """Handle click events in line drawing mode."""
        if self.line_start is None:
            self.line_start = (lon, lat)
            (self.temp_line_artist,) = self.ax_map.plot(
                lon, lat, "y+", markersize=12, markeredgewidth=2, zorder=15
            )
        else:
            start_lon, start_lat = self.line_start
            (artist,) = self.ax_map.plot(
                [start_lon, lon], [start_lat, lat], "b-", linewidth=2, zorder=9
            )
            data = {
                "start": {"lat": start_lat, "lon": start_lon},
                "end": {"lat": lat, "lon": lon},
                "type": "transect",
            }
            self.transects.append(data)
            self.history.append(("transect", data, artist))

            self._reset_line_state()
            self._update_status_display(message="Transect added.")

    def _handle_area_click(self, lon, lat):
        """Handle click events in area drawing mode."""
        # Add point to current area
        self.current_area_points.append((lon, lat))
        depth = self.bathymetry.get_depth_at_point(lat, lon)

        # Draw a point marker
        (point_artist,) = self.ax_map.plot(
            lon, lat, "go", markersize=6, markeredgecolor="darkgreen", zorder=12
        )
        data = {"lat": lat, "lon": lon, "depth": depth}
        self.area_point_artists.append(point_artist)

        # Update area polygon if we have 2+ points
        if len(self.current_area_points) >= 2:
            self._update_temp_area()

        # Update status with instruction (2-line format for consistent layout)
        if len(self.current_area_points) == 1:
            self._update_status_display(
                message="Area: 1 point\nAdd 2+ more, then press 'a'"
            )
        elif len(self.current_area_points) == 2:
            self._update_status_display(
                message="Area: 2 points\nAdd 1+ more, then press 'a'"
            )
        else:
            self._update_status_display(
                message=f"Area: {len(self.current_area_points)} points\nReady! Press 'a' to complete"
            )

    def _update_temp_area(self):
        """Update the temporary area polygon display."""
        if len(self.current_area_points) < 2:
            return

        # Remove existing temp area
        if self.temp_area_artist:
            self.temp_area_artist.remove()

        # Create polygon from current points
        lons, lats = zip(*self.current_area_points)

        # Add the current mouse position to close the polygon visually
        # For now, just draw the current polygon
        self.temp_area_artist = self.ax_map.plot(
            list(lons) + [lons[0]],
            list(lats) + [lats[0]],
            "g--",
            alpha=0.6,
            linewidth=2,
            zorder=11,
        )[0]

        self.fig.canvas.draw_idle()

    def _complete_area(self):
        """Complete the current area and add it to the areas list."""
        if len(self.current_area_points) < 3:
            return

        # Remove temporary visualization
        self._reset_area_state()

        # Create polygon patch for the completed area
        from matplotlib.patches import Polygon

        lons, lats = zip(*self.current_area_points)
        polygon_coords = list(zip(lons, lats))

        polygon = Polygon(
            polygon_coords,
            alpha=0.3,
            facecolor="green",
            edgecolor="darkgreen",
            linewidth=2,
            zorder=8,
        )
        self.ax_map.add_patch(polygon)

        # Store area data
        area_data = {
            "points": self.current_area_points.copy(),
            "type": "survey_area",
            "center": (sum(lons) / len(lons), sum(lats) / len(lats)),
        }
        self.areas.append(area_data)
        self.history.append(("area", area_data, polygon))

        # Reset state
        self.current_area_points = []
        self._update_status_display(
            message=f"Area completed! Total areas: {len(self.areas)}"
        )

    def _reset_area_state(self):
        """Reset area drawing state."""
        # Remove temporary area polygon
        if self.temp_area_artist:
            self.temp_area_artist.remove()
            self.temp_area_artist = None

        # Remove temporary point markers
        for artist in self.area_point_artists:
            artist.remove()
        self.area_point_artists = []

        self.fig.canvas.draw_idle()

    def _find_nearest_station(self, target_lon, target_lat, threshold=2.0):
        """
        Find the station closest to the click coordinates.

        Parameters
        ----------
        target_lon : float
            Target longitude coordinate.
        target_lat : float
            Target latitude coordinate.
        threshold : float, optional
            Maximum distance threshold for station detection (default: 2.0).

        Returns
        -------
        Tuple[Optional[Dict], Optional[int]]
            Tuple of (station_data, station_index) if found within threshold, (None, None) otherwise.
        """
        if not self.stations:
            return None, None

        closest_dist = float("inf")
        closest_data = None
        closest_index = -1

        for i, station in enumerate(self.stations):
            dist = (
                (station["lon"] - target_lon) ** 2 + (station["lat"] - target_lat) ** 2
            ) ** 0.5

            if dist < closest_dist:
                closest_dist = dist
                closest_data = station
                closest_index = i

        if closest_dist < threshold:
            return closest_data, closest_index
        return None, None

    def _remove_specific_station(self, station_data):
        """Remove a specific station from the display and data."""
        self.stations.remove(station_data)

        history_item_to_remove = None
        for item in self.history:
            if item[1] == station_data:
                history_item_to_remove = item
                break

        if history_item_to_remove:
            history_item_to_remove[2].remove()
            self.history.remove(history_item_to_remove)

        self.ax_map.figure.canvas.draw_idle()
        self._update_status_display(
            message=f"Removed station at {station_data['lat']:.2f}, {station_data['lon']:.2f}"
        )

    def _remove_last_item(self):
        """Remove the most recently added operation."""
        if not self.history:
            return

        item_type, item_data, artist = self.history.pop()

        if artist:
            artist.remove()

        if item_type == "station":
            if item_data in self.stations:
                self.stations.remove(item_data)
        elif item_type == "transect":
            if item_data in self.transects:
                self.transects.remove(item_data)
        elif item_type == "area":
            if item_data in self.areas:
                self.areas.remove(item_data)

        self.ax_map.figure.canvas.draw_idle()
        self._update_status_display(message=f"Removed last {item_type}")

    # --- Display Updates ---

    def _update_mode_display(self):
        """Update the mode indicator display."""
        # Color mapping for modes
        mode_colors = {
            "navigation": "#2E8B57",  # Sea green
            "point": "#4169E1",  # Royal blue
            "line": "#FF6347",  # Tomato
            "area": "#9932CC",  # Dark orchid
            "remove": "#DC143C",  # Crimson
        }

        color = mode_colors.get(self.mode, "#808080")
        self.mode_text.set_text(f"Mode: {self.mode.upper()}")
        self.mode_text.set_bbox(
            dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.3)
        )
        self.fig.canvas.draw_idle()

    def _update_status_display(self, lat=0, lon=0, depth=0, message=""):
        """Update the status display with coordinates and operation counts."""
        text = (
            f"Lat: {lat:.4f}\n"
            f"Lon: {lon:.4f}\n"
            f"Depth: {depth:.0f} m\n"
            f"----------------\n"
            f"Stations: {len(self.stations)}\n"
            f"Transects: {len(self.transects)}\n"
            f"Areas: {len(self.areas)}\n"
        )

        if message:
            text += f"\n[{message}]"
        elif self.mode == "line" and self.line_start:
            text += "\n[Waiting for 2nd point...]"

        self.status_text.set_text(text)
        self.fig.canvas.draw_idle()

    def _sanitize_limits(self):
        """Prevents non-physical zooming."""
        min_lat, max_lat = self.ax_map.get_ylim()
        min_lon, max_lon = self.ax_map.get_xlim()
        dirty = False

        # Check for absurd values (latitude or longitude)
        if (
            abs(min_lat) > 180
            or abs(max_lat) > 180
            or abs(min_lon) > 360
            or abs(max_lon) > 360
        ):
            print(
                f"⚠️ Limits exploded (lat: {min_lat:.1e}, {max_lat:.1e}; lon: {min_lon:.1e}, {max_lon:.1e}). Resetting view."
            )
            self.ax_map.set_xlim(-65, -5)
            self.ax_map.set_ylim(45, 70)
            self.ax_map.set_yscale("linear")
            self.ax_map.set_xscale("linear")
            return

        # Hard clamp for Mercator safety
        if min_lat < -85:
            min_lat = -85
            dirty = True
        if max_lat > 85:
            max_lat = 85
            dirty = True

        if dirty:
            self.ax_map.set_ylim(min_lat, max_lat)

    def _update_aspect_ratio(self):
        """Update aspect ratio based on latitude for proper geographic projection."""
        import math

        self._sanitize_limits()

        min_lat, max_lat = self.ax_map.get_ylim()
        mid_lat_deg = (min_lat + max_lat) / 2

        # Clamp input to cos()
        mid_lat_deg = max(-85.0, min(85.0, mid_lat_deg))
        mid_lat_rad = math.radians(mid_lat_deg)

        try:
            aspect = 1.0 / math.cos(mid_lat_rad)
        except ZeroDivisionError:
            aspect = 1.0

        aspect = max(1.0, min(aspect, 10.0))

        # Use "box" adjustable to prevent data limits from changing during interactions
        # This maintains geographic projection while keeping map bounds stable
        self.ax_map.set_aspect(aspect, adjustable="box")

        self.fig.canvas.draw_idle()

    # --- File Operations ---

    def _save_to_yaml(self):
        """Save current cruise plan to YAML format."""
        if not self.stations and not self.transects:
            return

        # Format data for YAML export
        yaml_stations = [
            format_station_for_yaml(stn, i) for i, stn in enumerate(self.stations, 1)
        ]

        yaml_sections = [
            format_transect_for_yaml(tr, i) for i, tr in enumerate(self.transects, 1)
        ]

        yaml_areas = [format_area_for_yaml(ar, i) for i, ar in enumerate(self.areas, 1)]

        current_name = getattr(self, "cruise_name", "Interactive_Session")

        # Add minimal defaults for required cruise configuration fields
        # This allows the output to be used directly with 'cruiseplan enrich'
        output_data = {
            "cruise_name": current_name,
            "description": "Cruise plan created with interactive station picker",
            "default_vessel_speed": 10.0,
            "default_distance_between_stations": 40.0,
            "calculate_transfer_between_sections": True,
            "calculate_depth_via_bathymetry": True,
            "start_date": "1970-01-01T00:00:00Z",
            # Global catalog sections (stations, transits, areas) come BEFORE legs
            "stations": yaml_stations,
            "transits": yaml_sections,  # Schema expects 'transits' not 'sections'
            "areas": yaml_areas,
            # Scheduling/sequencing logic comes after catalog
            # IMPORTANT: No global departure_port, arrival_port, first_station, last_station
            # These fields are now defined at leg level to avoid validation conflicts
            "legs": (
                [
                    {
                        "name": "Interactive_Survey",
                        "departure_port": "port_update",  # Move from global to leg level
                        "arrival_port": "port_update",  # Move from global to leg level
                        "first_waypoint": (  # Renamed from first_station
                            yaml_stations[0]["name"]
                            if yaml_stations
                            else "UPDATE-first-station-name"
                        ),
                        "last_waypoint": (  # Renamed from last_station
                            yaml_stations[-1]["name"]
                            if yaml_stations
                            else "UPDATE-last-station-name"
                        ),
                        "strategy": "sequential",
                        "activities": (  # Use activities instead of sequence
                            [station["name"] for station in yaml_stations]
                            + [section["name"] for section in yaml_sections]
                            + [area["name"] for area in yaml_areas]
                        ),
                    }
                ]
                if (yaml_stations or yaml_sections or yaml_areas)
                else []
            ),
        }

        try:
            # Check if file exists and handle overwrite
            output_path = Path(self.output_file)
            if output_path.exists() and not self.overwrite:
                response = self._prompt_overwrite(output_path)
                if response == "rename":
                    # Generate new filename with timestamp
                    import datetime

                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    stem = output_path.stem
                    suffix = output_path.suffix
                    new_name = f"{stem}_backup_{timestamp}{suffix}"
                    backup_path = output_path.parent / new_name
                    self.output_file = str(backup_path)
                    print(f"📁 Saving to new file: {backup_path}")
                elif response == "cancel":
                    print("💾 Save cancelled by user.")
                    return
                # If response is "overwrite", proceed with original filename

            save_cruise_config(output_data, self.output_file)
            print(
                f"✅ Saved {len(yaml_stations)} stations, {len(yaml_sections)} transits, {len(yaml_areas)} areas."
            )
        except Exception as e:
            print(f"❌ Save Error: {e}")

    def _prompt_overwrite(self, file_path: Path) -> str:
        """
        Prompt user about overwriting existing file.

        Parameters
        ----------
        file_path : Path
            Path to the existing file.

        Returns
        -------
        str
            User choice: "overwrite", "rename", or "cancel"
        """
        import sys

        print(f"⚠️  File {file_path} already exists.")
        print("What would you like to do?")
        print("  [o] Overwrite existing file")
        print("  [r] Rename and save as backup")
        print("  [c] Cancel save operation")

        # Handle non-interactive environments
        if not sys.stdin.isatty():
            print("Non-interactive environment detected. Creating backup file...")
            return "rename"

        while True:
            try:
                choice = input("Enter choice (o/r/c): ").lower().strip()
                if choice in ["o", "overwrite"]:
                    return "overwrite"
                elif choice in ["r", "rename"]:
                    return "rename"
                elif choice in ["c", "cancel"]:
                    return "cancel"
                else:
                    print("Invalid choice. Please enter 'o', 'r', or 'c'.")
            except (EOFError, KeyboardInterrupt):
                print("\nOperation cancelled.")
                return "cancel"

    # --- Public Interface ---

    def show(self):
        """Display the interactive cruise planning interface."""
        plt.show()

    def get_cruise_data(self) -> Dict:
        """
        Get the current cruise plan data.

        Returns
        -------
        Dict
            Dictionary containing current stations and transects data.
        """
        return {
            "stations": self.stations,
            "transects": self.transects,
        }


# Backward compatibility for tests: lazy import bathymetry when requested
def __getattr__(name):
    if name == "bathymetry":
        from cruiseplan.data.bathymetry import bathymetry

        return bathymetry
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


if __name__ == "__main__":
    picker = StationPicker()
    picker.show()
