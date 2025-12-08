import math
from itertools import cycle
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons

# Local Integrations
from cruiseplan.data.bathymetry import DEPTH_CONTOURS, bathymetry
from cruiseplan.data.pangaea import merge_campaign_tracks
from cruiseplan.utils.config import (
    format_station_for_yaml,
    format_transect_for_yaml,
    save_cruise_config,
)


class StationPicker:
    """
    Main interactive controller for Phase 2.
    """

    def __init__(
        self,
        campaign_data: Optional[List[Dict]] = None,
        output_file: str = "stations.yaml",
    ):
        # -----------------------------------------------------------
        # CRITICAL FIX: Unbind default Matplotlib shortcuts
        # 'l' defaults to log-scale toggle, causing axis explosion.
        # -----------------------------------------------------------
        self._unbind_default_keys()

        # State Management
        self.mode = "navigation"
        self.output_file = output_file

        # Data Storage
        self.stations: List[Dict] = []
        self.transects: List[Dict] = []
        self.history: List[Tuple[str, Dict, Any]] = []

        # Line Drawing State
        self.line_start: Optional[Tuple[float, float]] = None
        self.temp_line_artist: Optional[Any] = None

        # Data layers
        self.campaigns = merge_campaign_tracks(campaign_data) if campaign_data else []
        self.campaign_artists = {}
        self.style_gen = self._create_style_generator()

        # UI Components
        self.fig = None
        self.ax_map = None
        self.ax_campaign = None
        self.ax_controls = None
        self.status_text = None
        self.check_buttons = None

        self._setup_interface()
        self.ax_map.set_xlim(-60, -10)
        self.ax_map.set_ylim(40, 65)

        self._plot_bathymetry()
        self._connect_events()

        self._plot_initial_campaigns()

        # for the line clicker
        self.rubber_band_artist = None  # Will hold the dashed line object

        # Connect the motion listener
        self.cid_move = self.ax_map.figure.canvas.mpl_connect(
            "motion_notify_event", self._on_mouse_move
        )

        # Initial View
        self._update_aspect_ratio()

    def _plot_bathymetry(self):
        """Fetches and renders bathymetry contours."""
        # Define region to fetch (cover likely area)
        # Get current view limits
        xmin, xmax = self.ax_map.get_xlim()
        ymin, ymax = self.ax_map.get_ylim()

        #  Add a 10-degree buffer so user can pan slightly
        buffer = 10
        lon_min, lon_max = xmin - buffer, xmax + buffer
        lat_min, lat_max = ymin - buffer, ymax + buffer

        print("Rendering bathymetry layers...")

        xx, yy, zz = bathymetry.get_grid_subset(
            lat_min, lat_max, lon_min, lon_max, stride=10
        )

        # 1. Filled Contours (The "Map" feel)
        # Using a standard ocean colormap
        self.ax_map.contourf(
            xx,
            yy,
            zz,
            levels=[-6000, -4000, -2000, -1000, -200, 0],
            cmap="Blues_r",
            alpha=0.4,
        )

        # 2. Line Contours (The "Scientific" context)
        cs = self.ax_map.contour(
            xx, yy, zz, levels=DEPTH_CONTOURS, colors="gray", linewidths=0.5, alpha=0.6
        )

        # Add labels to contour lines
        self.ax_map.clabel(cs, inline=True, fontsize=8, fmt="%d")

    def _unbind_default_keys(self):
        """Removes conflicting default keymaps from Matplotlib."""
        # 'l' toggles Y-axis log scale -> Causes aspect ratio explosion
        # 'k' toggles X-axis log scale
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

    def _create_style_generator(self):
        """Generates distinct styles."""
        fill_colors = cycle(["#56B4E9", "#E69F00", "#009E73", "#CC79A7"])
        edge_colors = cycle(["k", "#D55E00", "#0072B2", "#F0E442", "#888888"])
        shapes = cycle(["o", "s", "^", "D", "v", "p"])

        while True:
            yield {
                "marker": next(shapes),
                "markerfacecolor": next(fill_colors),
                "markeredgecolor": next(edge_colors),
                "linestyle": "None",
                "markersize": 6,
                "markeredgewidth": 1.5,
                "alpha": 0.7,
            }

    def _setup_interface(self):
        self.fig = plt.figure(figsize=(16, 9), constrained_layout=True)
        gs = gridspec.GridSpec(1, 3, figure=self.fig, width_ratios=[1, 4, 1])

        # 1. Campaigns
        self.ax_campaign = self.fig.add_subplot(gs[0, 0])
        self.ax_campaign.set_title("Campaigns")
        self.ax_campaign.axis("off")

        if self.campaigns:
            labels = [c["label"][:20] for c in self.campaigns]
            self.check_buttons = CheckButtons(
                self.ax_campaign, labels, [True] * len(labels)
            )
            self.check_buttons.on_clicked(self._toggle_campaign)
        else:
            self.ax_campaign.text(
                0.1, 0.9, "No Campaigns", transform=self.ax_campaign.transAxes
            )

        # 2. Map
        self.ax_map = self.fig.add_subplot(gs[0, 1])
        self.ax_map.set_xlabel("Longitude")
        self.ax_map.set_ylabel("Latitude")
        self.ax_map.grid(True, linestyle=":", alpha=0.3, color="black")
        self.ax_map.set_title("Station Planning Map")

        # 3. Controls
        self.ax_controls = self.fig.add_subplot(gs[0, 2])
        self.ax_controls.set_title("Controls")
        self.ax_controls.axis("off")

        self.status_text = self.ax_controls.text(
            0.05,
            0.95,
            "",
            transform=self.ax_controls.transAxes,
            va="top",
            fontfamily="monospace",
        )
        self._update_status_display()

    def _plot_initial_campaigns(self):
        for camp in self.campaigns:
            style = next(self.style_gen)
            (artist,) = self.ax_map.plot(
                camp["longitude"], camp["latitude"], label=camp["label"], **style
            )
            self.campaign_artists[camp["label"][:20]] = artist

    def _toggle_campaign(self, label):
        if label in self.campaign_artists:
            self.campaign_artists[label].set_visible(
                not self.campaign_artists[label].get_visible()
            )
            self.fig.canvas.draw_idle()

    def _connect_events(self):
        self.fig.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.fig.canvas.mpl_connect("button_press_event", self._on_click)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

        # Aspect Ratio Handling
        self.fig.canvas.mpl_connect("button_release_event", self._on_release)
        self.fig.canvas.mpl_connect("resize_event", self._on_resize)

    def _sanitize_limits(self):
        """
        Prevents non-physical zooming.
        """
        min_lat, max_lat = self.ax_map.get_ylim()

        dirty = False

        # Check for Infinity/NaN/Absurd values
        if abs(min_lat) > 180 or abs(max_lat) > 180:
            print(f"⚠️ Limits exploded ({min_lat:.1e}, {max_lat:.1e}). Resetting view.")
            self.ax_map.set_xlim(-60, -10)
            self.ax_map.set_ylim(40, 65)
            # Force linear scale back if it somehow switched
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
        # 1. Sanitize first!
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

        self.ax_map.set_aspect(aspect, adjustable="datalim")
        self.fig.canvas.draw_idle()

    def _on_release(self, event):
        if event.inaxes == self.ax_map:
            self._update_aspect_ratio()

    def _on_resize(self, event):
        self._update_aspect_ratio()

    def _on_key_press(self, event):
        """Handle key presses."""
        if event.inaxes != self.ax_map:
            return
        if event.key == "p":
            self.mode = "point"
            self._reset_line_state()
        elif event.key == "l":
            self.mode = "line"
        elif event.key == "n":
            self.mode = "navigation"
            self._reset_line_state()
        elif event.key == "u":
            self._remove_last_item()
        elif event.key == "r":
            self.mode = "remove"
            self._update_status_display(
                message="Mode: REMOVE. Click near a station to delete it."
            )
        elif event.key == "y":
            self._save_to_yaml()
        elif event.key == "escape":
            plt.close(self.fig)

        self._update_status_display()
        self.fig.canvas.draw_idle()

    def _reset_line_state(self):
        self.line_start = None

        # Remove the yellow '+' start marker
        if hasattr(self, "temp_line_artist") and self.temp_line_artist:
            self.temp_line_artist.remove()
            self.temp_line_artist = None

        # NEW: Remove the rubber band line
        if self.rubber_band_artist:
            self.rubber_band_artist.remove()
            self.rubber_band_artist = None

        self.ax_map.figure.canvas.draw_idle()

    def _remove_last_item(self):
        if not self.history:
            self._update_status_display(message="Nothing to remove")
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

        self._update_status_display(message=f"Removed last {item_type}")
        self.ax_map.figure.canvas.draw_idle()

    def _on_click(self, event):
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

        elif self.mode == "remove":
            # Try to find a station near the click
            station_data, _ = self._find_nearest_station(event.xdata, event.ydata)

            if station_data:
                self._remove_specific_station(station_data)
            else:
                self._update_status_display(
                    message="No station close enough to remove."
                )
            return

    def _find_nearest_station(self, target_lon, target_lat, threshold=2.0):
        """
        Finds the station closest to the click coordinates.
        Returns the data dict and the index if found within threshold.
        """
        if not self.stations:
            return None, None

        closest_dist = float("inf")
        closest_data = None
        closest_index = -1

        for i, station in enumerate(self.stations):
            # Simple Euclidean distance (ok for picking, rough for geography)
            # For precise geo-distance, use haversine, but this is usually fine for UI.
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

    def _add_station(self, lon, lat):
        depth = bathymetry.get_depth_at_point(lat, lon)
        (artist,) = self.ax_map.plot(
            lon, lat, "ro", markersize=8, markeredgecolor="k", zorder=10
        )

        data = {"lat": lat, "lon": lon, "depth": depth}
        self.stations.append(data)
        self.history.append(("station", data, artist))
        self._update_status_display(lat, lon, depth)

    def _remove_specific_station(self, station_data):
        # 1. Remove from data list
        self.stations.remove(station_data)

        # 2. Find and remove the visual artist (tricky part!)
        # We have to search the history to find the artist associated with this data
        history_item_to_remove = None

        for item in self.history:
            # item structure: (type, data, artist)
            if item[1] == station_data:
                history_item_to_remove = item
                break

        if history_item_to_remove:
            # Remove the dot from the screen
            history_item_to_remove[2].remove()
            # Remove from history so "Undo" doesn't get confused later
            self.history.remove(history_item_to_remove)

        self.ax_map.figure.canvas.draw_idle()
        self._update_status_display(
            message=f"Removed station at {station_data['lat']:.2f}, {station_data['lon']:.2f}"
        )

    def _handle_line_click(self, lon, lat):
        if self.line_start is None:
            self.line_start = (lon, lat)
            (self.temp_line_artist,) = self.ax_map.plot(
                lon, lat, "y+", markersize=12, markeredgewidth=2, zorder=15
            )
            self._update_status_display(message="Start point set. Click end point.")
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

    def _save_to_yaml(self):
        """Compiles current state and delegates to the core save function."""
        if not self.stations and not self.transects:
            self._update_status_display(message="⚠️ No data to save.")
            return

        self._update_status_display(message="Saving data...")

        # 1. Delegate Station Formatting
        yaml_stations = [
            format_station_for_yaml(stn, i) for i, stn in enumerate(self.stations, 1)
        ]

        # 2. Delegate Transect Formatting (Consistency!)
        yaml_sections = [
            format_transect_for_yaml(tr, i) for i, tr in enumerate(self.transects, 1)
        ]

        # 3. Preserve Metadata (Don't overwrite the cruise name if we have one)
        # Assuming self.metadata was passed in __init__, otherwise fallback
        current_name = getattr(self, "cruise_name", "Interactive_Session")

        output_data = {
            "cruise_name": current_name,
            "stations": yaml_stations,
            "sections": yaml_sections,
        }

        try:
            # delegated I/O function
            save_cruise_config(output_data, self.output_file)

            # Success Feedback
            print(f"✅ Saved {len(yaml_stations)} stations, {len(yaml_sections)} sections.")
            self._update_status_display(message=f"SAVED TO {self.output_file}")

        except Exception as e:
            # Error Feedback
            print(f"❌ Save Error: {e}")
            self._update_status_display(message="SAVE FAILED. Check console.")

    def _on_mouse_move(self, event):
        """Updates depth readout AND handles rubber band line drawing."""
        if event.inaxes != self.ax_map:
            return

        # 1. Existing Logic: Get Depth
        depth = bathymetry.get_depth_at_point(event.ydata, event.xdata)

        # Determine if we have a special status message to show
        status_msg = ""

        # 2. New Logic: Rubber Banding
        # Only runs if we are in 'line' mode AND have started drawing
        if self.mode == "line" and self.line_start is not None:
            start_lon, start_lat = self.line_start
            end_lon, end_lat = event.xdata, event.ydata

            # Create or Update the visual line
            if self.rubber_band_artist is None:
                (self.rubber_band_artist,) = self.ax_map.plot(
                    [start_lon, end_lon],
                    [start_lat, end_lat],
                    "b--",
                    alpha=0.6,
                    linewidth=1.5,
                    zorder=15
                )
            else:
                # Fast update
                self.rubber_band_artist.set_data(
                    [start_lon, end_lon],
                    [start_lat, end_lat]
                )

            self.ax_map.figure.canvas.draw_idle()
            status_msg = "Click to set end point"

        # 3. Update Status Display (Merged)
        # We pass the status_msg so the user knows they are in the middle of an action
        self._update_status_display(event.ydata, event.xdata, depth, message=status_msg)

    def _update_status_display(self, lat=0, lon=0, depth=0, message=""):
        # Helper to safely format numbers, returning "N/A" if they aren't numbers
        def safe_fmt(val, fmt):
            try:
                return f"{float(val):{fmt}}"
            except (ValueError, TypeError):
                return "N/A"

        text = (
            f"Mode: {self.mode.upper()}\n"
            f"----------------\n"
            f"Lat: {lat:.4f}\n"
            f"Lon: {lon:.4f}\n"
            f"Z:   {depth:.0f} m\n"
            f"----------------\n"
            f"Stations: {len(self.stations)}\n"
            f"Transects:{len(self.transects)}\n"
        )
        if message:
            text += f"\n[{message}]"
        elif self.mode == "line" and self.line_start:
            text += "\n[Waiting for 2nd point...]"

        text += (
            "\n\nKEYS:\n"
            " 'n': Navigation\n"
            " 'p': Point Mode\n"
            " 'l': Line Mode\n"
            " 'r': Remove Last\n"
            " 'y': Save YAML\n"
            " 'esc': Quit"
        )
        self.status_text.set_text(text)

    def show(self):
        plt.show()


if __name__ == "__main__":
    picker = StationPicker()
    picker.show()
