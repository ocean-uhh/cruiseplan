import math
from itertools import cycle
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons

# Local Integrations
from cruiseplan.data.bathymetry import bathymetry
from cruiseplan.data.pangaea import merge_campaign_tracks
from cruiseplan.utils.config import format_station_for_yaml, save_cruise_config


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

        # UI Components
        self.fig = None
        self.ax_map = None
        self.ax_campaign = None
        self.ax_controls = None
        self.status_text = None
        self.check_buttons = None

        self.style_gen = self._create_style_generator()

        self._setup_interface()
        self._connect_events()
        self._plot_initial_campaigns()

        # Initial View
        self.ax_map.set_xlim(-60, -10)
        self.ax_map.set_ylim(40, 65)
        self._update_aspect_ratio()

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
        self.ax_map.grid(True, linestyle="--", alpha=0.5)
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
        if event.key == "p":
            self.mode = "point"
            self._reset_line_state()
        elif event.key == "l":
            self.mode = "line"
        elif event.key == "n":
            self.mode = "navigation"
            self._reset_line_state()
        elif event.key == "r":
            self._remove_last_item()
        elif event.key == "y":
            self._save_to_yaml()
        elif event.key == "escape":
            plt.close(self.fig)

        self._update_status_display()
        self.fig.canvas.draw_idle()

    def _reset_line_state(self):
        if self.temp_line_artist:
            self.temp_line_artist.remove()
            self.temp_line_artist = None
        self.line_start = None

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

    def _on_click(self, event):
        if event.inaxes != self.ax_map or self.mode == "navigation":
            return

        if event.button == 1:
            if self.mode == "point":
                self._add_station(event.xdata, event.ydata)
            elif self.mode == "line":
                self._handle_line_click(event.xdata, event.ydata)

    def _add_station(self, lon, lat):
        depth = bathymetry.get_depth_at_point(lat, lon)
        (artist,) = self.ax_map.plot(
            lon, lat, "ro", markersize=8, markeredgecolor="k", zorder=10
        )

        data = {"lat": lat, "lon": lon, "depth": depth}
        self.stations.append(data)
        self.history.append(("station", data, artist))
        self._update_status_display(lat, lon, depth)

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
        if not self.stations and not self.transects:
            print("⚠️ No data to save.")
            return

        print(
            f"Saving {len(self.stations)} stations and {len(self.transects)} transects..."
        )

        yaml_stations = [
            format_station_for_yaml(stn, i) for i, stn in enumerate(self.stations, 1)
        ]

        yaml_sections = []
        for i, tr in enumerate(self.transects, 1):
            yaml_sections.append(
                {
                    "name": f"Section_{i:02d}",
                    "start": {
                        "latitude": round(tr["start"]["lat"], 6),
                        "longitude": round(tr["start"]["lon"], 6),
                    },
                    "end": {
                        "latitude": round(tr["end"]["lat"], 6),
                        "longitude": round(tr["end"]["lon"], 6),
                    },
                    "reversible": True,
                }
            )

        output_data = {
            "cruise_name": "Interactive_Session",
            "stations": yaml_stations,
            "sections": yaml_sections,
        }

        try:
            save_cruise_config(output_data, self.output_file)
            self._update_status_display(message=f"SAVED TO {self.output_file}")
        except Exception as e:
            self._update_status_display(message=f"SAVE FAILED: {e}")

    def _on_mouse_move(self, event):
        if event.inaxes != self.ax_map:
            return
        depth = bathymetry.get_depth_at_point(event.ydata, event.xdata)
        self._update_status_display(event.ydata, event.xdata, depth)

    def _update_status_display(self, lat=0, lon=0, depth=0, message=""):
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
