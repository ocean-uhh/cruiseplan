"""
PANGAEA campaign selection and management interface.
"""

import logging
import pickle
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
from matplotlib.widgets import CheckButtons

logger = logging.getLogger(__name__)


class CampaignSelector:
    """
    Manages PANGAEA campaign data loading and selection interface.

    Provides checkbox interface for toggling campaign visibility on interactive maps.
    Allows users to selectively display or hide PANGAEA cruise tracks for better
    visualization and planning.

    Attributes
    ----------
    campaign_data : List[Dict]
        List of campaign datasets with coordinate and metadata information.
    selected_campaigns : Dict[str, bool]
        Dictionary mapping campaign names to their visibility state.
    campaign_artists : Dict[str, Any]
        Dictionary mapping campaign names to their matplotlib artist objects.
    ax_campaign : Optional[plt.Axes]
        Matplotlib axes for the campaign selection interface.
    check_buttons : Optional[CheckButtons]
        Matplotlib CheckButtons widget for campaign selection.
    map_ax : Optional[plt.Axes]
        Reference to the main map axes for updating campaign display.
    """

    def __init__(self, campaign_data: Optional[List[Dict]] = None):
        """
        Initialize the campaign selector.

        Parameters
        ----------
        campaign_data : Optional[List[Dict]], optional
            Pre-loaded campaign track data from PANGAEA (default: None).
        """
        self.campaign_data = campaign_data or []
        # Stores the name -> boolean state (True = visible)
        self.selected_campaigns: Dict[str, bool] = {}
        # Stores the name -> matplotlib artist object (the scatter plot)
        self.campaign_artists: Dict[str, Any] = {}

        # UI components
        self.ax_campaign: Optional[plt.Axes] = None
        self.check_buttons: Optional[CheckButtons] = None
        self.map_ax: Optional[plt.Axes] = None  # Reference to the map axis

        # Initialize selection state (all are visible by default)
        for campaign in self.campaign_data:
            campaign_name = campaign.get("name", "Unknown")
            self.selected_campaigns[campaign_name] = True

    def setup_ui(self, ax_campaign: plt.Axes) -> None:
        """
        Initialize the campaign selection interface.

        Parameters
        ----------
        ax_campaign : plt.Axes
            Matplotlib axes where the campaign selector will be displayed.
        """
        self.ax_campaign = ax_campaign
        self.ax_campaign.set_title("PANGAEA Campaigns", fontsize=10)

        if not self.campaign_data:
            ax_campaign.text(
                0.5,
                0.5,
                "No PANGAEA\ncampaigns loaded",
                ha="center",
                va="center",
                transform=ax_campaign.transAxes,
            )
            return

        # Prepare names and initial states
        campaign_names = [
            camp.get("label", f"Campaign {i}")
            for i, camp in enumerate(self.campaign_data)
        ]

        # Limit display for space constraints
        max_display = 15
        if len(campaign_names) > max_display:
            campaign_names = campaign_names[:max_display]
            ax_campaign.text(
                0.02,
                0.02,
                f"Showing {max_display}/{len(self.campaign_data)} campaigns",
                transform=ax_campaign.transAxes,
                fontsize=8,
            )

        # Get initial state for displayed names
        initial_state = [
            self.selected_campaigns.get(name, True) for name in campaign_names
        ]

        # Hide axis ticks and labels for cleaner widget display
        ax_campaign.set_xticks([])
        ax_campaign.set_yticks([])

        # Create checkbox interface
        self.check_buttons = CheckButtons(ax_campaign, campaign_names, initial_state)
        # Connect the toggle handler
        self.check_buttons.on_clicked(self._on_campaign_toggle)

    def _on_campaign_toggle(self, label: str) -> None:
        """
        Handle campaign visibility toggle.

        Parameters
        ----------
        label : str
            Name of the campaign that was toggled.
        """
        # Flip the state in the internal dictionary
        self.selected_campaigns[label] = not self.selected_campaigns.get(label, True)

        # Update map display
        if self.map_ax:
            self._update_campaign_display()
        else:
            # If map_ax isn't set yet, the update will happen when it is drawn later
            pass

    def _update_campaign_display(self) -> None:
        """Update campaign visibility on map by setting the artist's visibility."""
        for campaign_name, is_visible in self.selected_campaigns.items():
            if campaign_name in self.campaign_artists:
                artist = self.campaign_artists[campaign_name]
                artist.set_visible(is_visible)

        # Refresh map
        if self.map_ax and self.map_ax.figure.canvas:
            self.map_ax.figure.canvas.draw_idle()

    def get_selected_campaigns(self) -> List[Dict]:
        """
        Return list of currently selected campaigns.

        Returns
        -------
        List[Dict]
            List of campaign dictionaries that are currently visible/selected.
        """
        selected = []
        for campaign in self.campaign_data:
            campaign_name = campaign.get("name", "Unknown")
            # Check if this campaign is selected
            if self.selected_campaigns.get(campaign_name, True):
                selected.append(campaign)
        return selected

    def save_selection(self, file_path: str) -> None:
        """
        Save current campaign selection to a pickle file.

        Parameters
        ----------
        file_path : str
            Path where the selected campaign data will be saved.
        """
        selected_campaigns = self.get_selected_campaigns()
        try:
            with open(file_path, "wb") as f:
                pickle.dump(selected_campaigns, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(
                f"💾 Saved {len(selected_campaigns)} selected campaigns to {file_path}"
            )
        except Exception as e:
            logger.error(f"Failed to save campaign selection to {file_path}: {e}")

    def toggle_all(self, state: bool) -> None:
        """
        Toggle all campaigns on/off.

        Parameters
        ----------
        state : bool
            True to show all campaigns, False to hide all campaigns.
        """
        for campaign_name in self.selected_campaigns:
            self.selected_campaigns[campaign_name] = state

        # Update checkbox interface visuals
        if self.check_buttons:
            # self.check_buttons.set_active() is a private method in older matplotlib
            # This logic mimics the manual toggle of the visual state
            for i in range(len(self.check_buttons.rectangles)):
                self.check_buttons.set_active(
                    i, state
                )  # Assumes set_active exists and controls visuals

        self._update_campaign_display()
