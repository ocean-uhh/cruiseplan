"""
Custom matplotlib widgets for oceanographic cruise planning interface.
"""

from typing import Callable, Dict, List, Optional

import matplotlib.pyplot as plt
from matplotlib.widgets import Widget


class ModeIndicator(Widget):
    """
    Visual indicator for current interaction mode.
    Shows current mode (navigation/point/line/area) with clear styling.
    """

    def __init__(
        self, ax: plt.Axes, modes: List[str], initial_mode: str = "navigation"
    ):
        self.ax = ax
        self.modes = modes
        self.current_mode = initial_mode
        # Callbacks are for external components (like StationPicker) to react to mode changes
        self.callbacks: Dict[str, Callable] = {}

        # Style configuration aligned with visual distinction
        self.colors = {
            "navigation": "#2E8B57",  # Sea green
            "point": "#4169E1",  # Royal blue
            "line": "#FF6347",  # Tomato
            "area": "#9932CC",  # Dark orchid
        }

        self.text_obj: Optional[plt.Text] = None
        self._setup_display()

    def _setup_display(self):
        """Initialize the mode indicator display."""
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self._update_display()

    def _update_display(self):
        """Update the visual indicator."""
        # Clear the axis content but maintain background properties
        self.ax.clear()
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)

        # Background color based on mode
        color = self.colors.get(self.current_mode, "#808080")
        self.ax.add_patch(plt.Rectangle((0, 0), 1, 1, facecolor=color, alpha=0.3))

        # Mode text
        self.text_obj = self.ax.text(
            0.5,
            0.5,
            f"Mode: {self.current_mode.title()}",
            ha="center",
            va="center",
            fontweight="bold",
            fontsize=10,
            color=color,
        )

        # Restore necessary aesthetic properties
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        self.ax.figure.canvas.draw_idle()

    def set_mode(self, mode: str):
        """Change the current mode."""
        if mode in self.modes:
            old_mode = self.current_mode
            self.current_mode = mode
            self._update_display()

            # Trigger callbacks registered for the new mode
            if mode in self.callbacks:
                self.callbacks[mode](old_mode, mode)

    def on_mode_change(self, mode: str, callback: Callable):
        """Register callback for mode changes."""
        self.callbacks[mode] = callback


class StatusDisplay(Widget):
    """
    Real-time status display for coordinates, depth, and operation counts.
    """

    def __init__(self, ax: plt.Axes):
        self.ax = ax
        self.status_lines: List[plt.Text] = []
        self._setup_display()

    def _setup_display(self):
        """Initialize the status display."""
        self.ax.clear()
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(0, 1)
        self.ax.set_xticks([])
        self.ax.set_yticks([])

        # Initialize status text lines
        self.status_lines = [
            self.ax.text(
                0.05, 0.85, "Coordinates: --", fontsize=9, transform=self.ax.transAxes
            ),
            self.ax.text(
                0.05, 0.70, "Depth: --", fontsize=9, transform=self.ax.transAxes
            ),
            self.ax.text(
                0.05,
                0.55,
                "Stations: 0",
                fontsize=9,
                transform=self.ax.transAxes,
                weight="bold",
            ),
            self.ax.text(
                0.05,
                0.40,
                "Transects: 0",
                fontsize=9,
                transform=self.ax.transAxes,
                weight="bold",
            ),
            self.ax.text(
                0.05,
                0.25,
                "Areas: 0",
                fontsize=9,
                transform=self.ax.transAxes,
                weight="bold",
            ),
        ]

    def update_coordinates(self, lat: Optional[float], lon: Optional[float]):
        """Update coordinate display, using Degrees Decimal Minutes format."""
        if lat is not None and lon is not None:
            # Format: DD MM.mmm Dir, DDD MM.mmm Dir

            # --- Latitude Conversion ---
            lat_deg, lat_frac = divmod(abs(lat), 1)
            lat_min = lat_frac * 60
            lat_dir = "N" if lat >= 0 else "S"

            # --- Longitude Conversion ---
            lon_deg, lon_frac = divmod(abs(lon), 1)
            lon_min = lon_frac * 60
            lon_dir = "E" if lon >= 0 else "W"

            # Format string for display (e.g., 53° 07.40'N, 050° 34.07'W)
            coord_str = f"{lat_deg:02.0f}° {lat_min:05.2f}'{lat_dir}, {lon_deg:03.0f}° {lon_min:05.2f}'{lon_dir}"
            self.status_lines[0].set_text(f"Coordinates: {coord_str}")
        else:
            self.status_lines[0].set_text("Coordinates: --")

    def update_depth(self, depth: Optional[float]):
        """Update depth display, handling positive elevation and negative depth."""
        if depth is not None:
            if depth > 0:
                self.status_lines[1].set_text(f"Elevation: +{depth:.0f} m")
            else:
                self.status_lines[1].set_text(f"Depth: {abs(depth):.0f} m")
        else:
            self.status_lines[1].set_text("Depth: --")

    def update_counts(self, stations: int, transects: int, areas: int):
        """Update operation counters."""
        self.status_lines[2].set_text(f"Stations: {stations}")
        self.status_lines[3].set_text(f"Transects: {transects}")
        self.status_lines[4].set_text(f"Areas: {areas}")

        # Refresh display
        self.ax.figure.canvas.draw_idle()
