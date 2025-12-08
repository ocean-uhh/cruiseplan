import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Button, CheckButtons
import numpy as np
import math
from typing import Optional, List, Dict

class StationPicker:
    """
    Main interactive controller for Phase 2.
    Uses standard Matplotlib with spherical geometry for aspect ratio.
    """

    def __init__(self, bathymetry_source: str = "etopo2022"):
        self.bathymetry_source = bathymetry_source

        # State Management
        self.mode = 'navigation'
        self.stations: List[Dict] = []
        self.transects: List[Dict] = []
        self.areas: List[Dict] = []

        # UI Components
        self.fig = None
        self.ax_map = None      # Center
        self.ax_campaign = None # Left
        self.ax_controls = None # Right
        self.status_text = None

        # Initialize the GUI
        self._setup_interface()
        self._connect_events()

        # Set initial bounds (Example: North Atlantic) and apply aspect ratio
        self.ax_map.set_xlim(-60, -10)
        self.ax_map.set_ylim(40, 65)
        self._update_aspect_ratio()

    def _setup_interface(self):
        """Builds the Three-Panel Layout."""
        self.fig = plt.figure(figsize=(16, 9), constrained_layout=True)

        # Grid layout: 1 row, 3 columns
        gs = gridspec.GridSpec(1, 3, figure=self.fig, width_ratios=[1, 4, 1])

        # 1. Left Panel: Campaign Selection
        self.ax_campaign = self.fig.add_subplot(gs[0, 0])
        self.ax_campaign.set_title("Campaigns")
        self.ax_campaign.axis('off')
        self.ax_campaign.text(0.1, 0.9, "Loading PANGAEA...", transform=self.ax_campaign.transAxes)

        # 2. Center Panel: Interactive Map
        self.ax_map = self.fig.add_subplot(gs[0, 1])
        self.ax_map.set_xlabel("Longitude")
        self.ax_map.set_ylabel("Latitude")
        self.ax_map.grid(True, linestyle='--', alpha=0.5)
        self.ax_map.set_title("Station Planning Map")

        # 3. Right Panel: Controls & Status
        self.ax_controls = self.fig.add_subplot(gs[0, 2])
        self.ax_controls.set_title("Controls")
        self.ax_controls.axis('off')

        self.status_text = self.ax_controls.text(
            0.05, 0.95,
            f"Mode: {self.mode.upper()}\nStations: 0",
            transform=self.ax_controls.transAxes,
            va='top', fontfamily='monospace'
        )

    def _connect_events(self):
        """Connects matplotlib event handlers."""
        self.fig.canvas.mpl_connect('key_press_event', self._on_key_press)
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)
        self.fig.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)

        # Connect to zoom/pan events
        self.ax_map.callbacks.connect('xlim_changed', self._on_limits_changed)
        self.ax_map.callbacks.connect('ylim_changed', self._on_limits_changed)

    def _calculate_aspect_ratio_spherical(self):
        """
        Calculates aspect ratio using simple spherical geometry.
        R = 6371 km
        Dist_Lat = R * delta_lat_radians
        Dist_Lon = R * delta_lon_radians * cos(mean_lat_radians)
        """
        min_lon, max_lon = self.ax_map.get_xlim()
        min_lat, max_lat = self.ax_map.get_ylim()

        # Earth radius in km
        R = 6371.0

        # Degrees to Radians
        lat_diff_rad = math.radians(max_lat - min_lat)
        lon_diff_rad = math.radians(max_lon - min_lon)
        mid_lat_rad = math.radians((min_lat + max_lat) / 2)

        # Calculate physical distances
        distance_lat = R * lat_diff_rad
        distance_lon = R * lon_diff_rad * math.cos(mid_lat_rad)

        # Avoid division by zero
        if distance_lon <= 0:
            return 1.0

        physical_ratio = distance_lat / distance_lon

        # Visual ratio (degrees)
        degrees_ratio = abs((max_lat - min_lat) / (max_lon - min_lon))

        if degrees_ratio == 0:
            return 1.0

        # The aspect required for the plot
        return physical_ratio / degrees_ratio

    def _update_aspect_ratio(self):
        """Applies the calculated aspect ratio to the plot axis."""
        aspect = self._calculate_aspect_ratio_spherical()
        self.ax_map.set_aspect(aspect, adjustable='box')
        self.fig.canvas.draw_idle()

    def _on_limits_changed(self, event_ax):
        """Callback when user zooms/pans."""
        if event_ax == self.ax_map:
            self._update_aspect_ratio()

    def _on_key_press(self, event):
        """Handles keyboard shortcuts p/l/n/esc."""
        if event.key == 'p':
            self.mode = 'point'
        elif event.key == 'l':
            self.mode = 'line'
        elif event.key == 'n':
            self.mode = 'navigation'
        elif event.key == 'escape':
            plt.close(self.fig)
            return

        self._update_status_display()
        self.fig.canvas.draw_idle()

    def _on_mouse_move(self, event):
        """Real-time coordinate feedback."""
        if event.inaxes != self.ax_map:
            return
        # Placeholder for future depth lookup
        pass

    def _on_click(self, event):
        """Click-to-place logic."""
        if event.inaxes != self.ax_map or self.mode == 'navigation':
            return

        if event.button == 1: # Left click
            if self.mode == 'point':
                self._add_station(event.xdata, event.ydata)

    def _add_station(self, lon, lat):
        print(f"Adding station at {lat:.4f}N, {lon:.4f}E")
        self.ax_map.plot(lon, lat, 'ro', markersize=8, markeredgecolor='k')
        self.stations.append({'lat': lat, 'lon': lon})
        self._update_status_display()

    def _update_status_display(self):
        status_str = (
            f"Mode: {self.mode.upper()}\n"
            f"----------------\n"
            f"Stations:  {len(self.stations)}\n"
            f"Transects: {len(self.transects)}\n"
            f"Areas:     {len(self.areas)}"
        )
        self.status_text.set_text(status_str)

    def show(self):
        plt.show()

if __name__ == "__main__":
    picker = StationPicker()
    picker.show()
