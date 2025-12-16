from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cruiseplan.interactive.station_picker import StationPicker

# The string must match the full path to the module where 'bathymetry' is USED
BATHY_MOCK_PATH = "cruiseplan.interactive.station_picker.bathymetry.get_depth_at_point"


@pytest.fixture
def picker():
    """
    Creates a StationPicker instance with all Matplotlib backend calls mocked out.
    """
    # Patch all the dependencies needed for our simplified StationPicker
    with (
        patch("matplotlib.pyplot.figure") as mock_fig_cls,
        patch("matplotlib.pyplot.show"),  # Prevent actual UI display
        patch(
            "cruiseplan.interactive.station_picker.CampaignSelector"
        ) as MockCampaignSelector,
        patch("cruiseplan.interactive.station_picker.bathymetry") as mock_bathy,
    ):

        # 1. Setup the main axes mocks
        mock_ax_campaigns = MagicMock()
        mock_ax_map = MagicMock()
        mock_ax_controls = MagicMock()

        # CRITICAL: Configure .plot() to return a list with 1 item
        # This allows the syntax:  (artist,) = ax.plot(...)  to work
        mock_ax_map.plot.return_value = [MagicMock()]

        # Configure return values for logic checks
        mock_ax_map.get_xlim.return_value = (-60, -10)
        mock_ax_map.get_ylim.return_value = (40, 65)

        # Mock text objects for the simplified interface
        mock_ax_controls.text.return_value = MagicMock()

        # 2. Setup Figure Mock to return the axes in correct order
        mock_fig = mock_fig_cls.return_value
        mock_fig.add_gridspec.return_value = MagicMock()
        mock_fig.add_subplot.side_effect = [
            mock_ax_campaigns,  # ax_campaigns
            mock_ax_map,  # ax_map
            mock_ax_controls,  # ax_controls
        ]
        mock_fig.canvas = MagicMock()

        # 3. Setup Bathymetry Mock
        mock_bathy.get_grid_subset.return_value = (
            MagicMock(),  # lons
            MagicMock(),  # lats
            MagicMock(),  # depths
        )
        mock_bathy.get_depth_at_point.return_value = -1000.0

        # 4. Setup CampaignSelector Mock
        MockCampaignSelector.return_value.setup_ui = MagicMock()
        MockCampaignSelector.return_value.campaign_artists = {}

        # 5. Instantiate
        output_dir = Path("tests_output")
        output_dir.mkdir(parents=True, exist_ok=True)
        sp = StationPicker(output_file=str(output_dir / "test_output.yaml"))

        # 6. Ensure proper references (safety)
        sp.ax_map = mock_ax_map
        sp.ax_campaigns = mock_ax_campaigns
        sp.ax_controls = mock_ax_controls

        return sp


def test_initial_state(picker):
    """Verify default mode and empty containers."""
    assert picker.mode == "navigation"
    assert len(picker.stations) == 0
    assert len(picker.transects) == 0
    assert len(picker.history) == 0


def test_mode_switching(picker):
    # Expect 'navigation' initially
    assert picker.mode == "navigation"

    # Switch to point
    picker.mode = "point"
    assert picker.mode == "point"

    # Switch back (optional)
    picker.mode = "navigation"
    assert picker.mode == "navigation"


def test_mode_switching_via_keypress(picker):
    """Test that pressing 'p', 'r', 'n' actually changes the mode."""
    # 1. Verify default start state
    assert picker.mode == "navigation"

    # 2. Create a proper Mock Event
    mock_event = Mock()
    mock_event.inaxes = picker.ax_map  # Passes the guard clause
    mock_event.key = "p"

    # 3. Simulate pressing "p" (point mode)
    picker._on_key_press(mock_event)
    assert picker.mode == "point"

    # 4. Simulate pressing "r" (remove mode)
    mock_event.key = "r"
    picker._on_key_press(mock_event)
    assert picker.mode == "remove"

    # 5. Simulate pressing "n" (navigation mode)
    mock_event.key = "n"
    picker._on_key_press(mock_event)
    assert picker.mode == "navigation"


def test_station_placement(picker):
    """Test adding a station updates data and history."""
    picker.mode = "point"

    # Mock the instance bathymetry method instead of the global one
    with patch.object(picker.bathymetry, "get_depth_at_point", return_value=-1000.0):
        # Run the method
        picker._add_station(-50.0, 45.0)

    # Assertions
    assert len(picker.stations) == 1
    assert picker.stations[0]["lat"] == 45.0
    assert picker.stations[0]["lon"] == -50.0

    # Station picker now uses absolute depth values (positive)
    assert picker.stations[0]["depth"] == 1000.0

    assert len(picker.history) == 1
    assert picker.history[0][0] == "station"

    # 1. Verify 'plot' was called with the correct coordinates and style
    #    This ensures you didn't break the UI (e.g., making dots invisible or blue)
    picker.ax_map.plot.assert_called_once_with(
        -50.0, 45.0, "ro", markersize=8, markeredgecolor="k", zorder=10
    )

    # 2. Verify the artist stored in history is valid
    #    The mock 'plot' returns a list of artists (e.g. [MockArtist])
    #    We check that the item saved in history is indeed that mock.

    # Get the mock object that .plot() returned
    mock_artist_returned = picker.ax_map.plot.return_value[0]

    # Check that this specific artist is what ended up in the history tuple
    # history structure: ("station", data, artist)
    assert picker.history[0][2] == mock_artist_returned


def test_undo_functionality(picker):
    """Test that 'r' removes the last item correctly."""
    # Setup: Add one station
    picker.mode = "point"
    picker._add_station(-50, 45)
    assert len(picker.stations) == 1

    # Act: Remove it
    picker._remove_last_item()

    # Assert
    assert len(picker.stations) == 0
    assert len(picker.history) == 0


def test_aspect_ratio_clamping(picker):
    """Test the math sanity check."""
    picker.ax_map.get_ylim.side_effect = None

    # Case 1: Normal Latitude (45 deg)
    picker.ax_map.get_ylim.return_value = (40, 50)
    picker._update_aspect_ratio()
    args, _ = picker.ax_map.set_aspect.call_args
    # 1/cos(45) is approx 1.41
    assert 1.4 < args[0] < 1.5

    # Case 2: Extreme Latitude (Clamp to 85)
    picker.ax_map.get_ylim.return_value = (88, 90)
    picker._update_aspect_ratio()
    # Should clamp to max 10.0
    args, _ = picker.ax_map.set_aspect.call_args
    assert args[0] == 10.0


def test_sanitize_limits_explosion(picker):
    """Test the safety reset for exploded view coordinates."""
    picker.ax_map.get_ylim.return_value = (-1e19, 1e19)
    picker.ax_map.get_xlim.return_value = (-1e19, 1e19)

    picker._sanitize_limits()

    # Should reset to North Atlantic defaults
    picker.ax_map.set_xlim.assert_called_with(-65, -5)
    picker.ax_map.set_ylim.assert_called_with(45, 70)


def test_undo_last_item(picker):
    """Test 'u' key removes the last added station (LIFO)."""
    with patch.object(picker.bathymetry, "get_depth_at_point", return_value=-1000.0):
        picker._add_station(-50.0, 45.0)  # 1st
        picker._add_station(-60.0, 45.0)  # 2nd

    assert len(picker.stations) == 2

    # Run the Undo logic directly (simulating 'u' press)
    picker._remove_last_item()

    assert len(picker.stations) == 1
    assert picker.stations[0]["lon"] == -50.0  # The 1st station should remain


def test_remove_last_item_empty_safe(picker):
    """Ensure removing from an empty state doesn't crash."""
    # Ensure history is empty to start
    assert len(picker.history) == 0

    # Run the method - should just return silently or print a status
    # without raising an IndexError or AttributeError
    picker._remove_last_item()

    # Assert nothing changed
    assert len(picker.history) == 0

    # Optional: If you want to be thorough, check that no stations were somehow deleted
    assert len(picker.stations) == 0


def test_remove_specific_station_by_click(picker):
    """Test clicking near a station in remove mode deletes it."""
    # 1. Setup: Add two stations
    with patch.object(picker.bathymetry, "get_depth_at_point", return_value=-1000.0):
        picker._add_station(-50.0, 45.0)  # Station 0
        picker._add_station(-52.0, 46.0)  # Station 1

    assert len(picker.stations) == 2

    # 2. Switch to remove mode
    picker.mode = "remove"

    # 3. Simulate click NEAR Station 0 (-50.0, 45.0)
    #    We click at -50.1, 45.1 (close enough)

    # We need to mock the event object
    from unittest.mock import Mock

    mock_event = Mock()
    mock_event.button = 1  # Must look like a left-click
    mock_event.inaxes = picker.ax_map
    mock_event.xdata = -50.1
    mock_event.ydata = 45.1

    # 4. Action
    picker._on_click(mock_event)

    # 5. Assertions
    assert len(picker.stations) == 1
    # Ensure the remaining station is Station 1 (-52.0)
    assert picker.stations[0]["lon"] == -52.0


def test_save_to_yaml_triggers_io(picker):
    """Test that _save_to_yaml correctly formats data and calls the save function."""
    # 1. Setup Data
    picker.stations = [{"lat": 10.0, "lon": -10.0, "depth": -500.0}]
    picker.transects = []  # Keep it simple
    picker.output_file = "test_cruise.yaml"

    # 2. Mock the external helpers
    # We mock 'format_station_for_yaml' to return a predictable dict
    # We mock 'save_cruise_config' to ensure it gets called

    # Note: Adjust path to where these are imported in station_picker.py
    with (
        patch(
            "cruiseplan.interactive.station_picker.format_station_for_yaml"
        ) as mock_fmt,
        patch("cruiseplan.interactive.station_picker.save_cruise_config") as mock_save,
    ):

        mock_fmt.return_value = {
            "name": "STN_01",
            "lat": 10.0,
        }  # Include required 'name' field

        # 3. Action
        picker._save_to_yaml()

        # 4. Assertions
        # Did it format the station?
        mock_fmt.assert_called_once()

        # Did it try to save?
        mock_save.assert_called_once()

        # specific check: Did it pass the right data structure?
        saved_data = mock_save.call_args[0][0]  # First arg of the call
        assert saved_data["stations"][0]["name"] == "STN_01"  # Use 'name' not 'id'
        assert saved_data["cruise_name"] == "Interactive_Session"  # or whatever default

        # Check filename
        assert mock_save.call_args[0][1] == "test_cruise.yaml"


def test_handle_line_click_workflow(picker):
    """
    Test that two calls to _handle_line_click correctly create one transect,
    store history, and reset the state.
    """
    # Use a dummy artist for the final blue line
    mock_final_artist = MagicMock()

    # --- SETUP ---
    # 1. Ensure the picker starts in the correct state
    picker.mode = "line"
    picker.line_start = None

    # 2. Mock external function calls and internal cleanup method
    # Patch the plotting function to return the artists we expect.
    with (
        patch.object(picker.ax_map, "plot") as mock_plot,
        patch.object(picker, "_reset_line_state") as mock_reset,
    ):

        # Configure mock_plot: First call returns the temp marker, second returns the final line
        mock_plot.side_effect = [
            (MagicMock(),),  # First call (yellow marker)
            (mock_final_artist,),  # Second call (final blue line)
        ]

        # --- ACTION 1: FIRST CLICK (Start Point) ---
        lon1, lat1 = 10.0, 50.0
        picker._handle_line_click(lon1, lat1)

        ## ASSERTIONS AFTER CLICK 1
        assert picker.line_start == (lon1, lat1)
        assert len(picker.transects) == 0
        assert mock_reset.call_count == 0  # Should not have reset yet
        # Check plotting call for the start marker
        mock_plot.assert_called_once_with(
            lon1, lat1, "y+", markersize=12, markeredgewidth=2, zorder=15
        )

        # --- ACTION 2: SECOND CLICK (End Point) ---
        lon2, lat2 = 20.0, 60.0
        picker._handle_line_click(lon2, lat2)

        ## ASSERTIONS AFTER CLICK 2

        # 1. State Verification (The action is complete)
        mock_reset.assert_called_once()  # Must call cleanup

        # 2. Data Verification (One transect added)
        assert len(picker.transects) == 1
        transect_data = picker.transects[0]
        assert transect_data["start"]["lat"] == lat1
        assert transect_data["end"]["lon"] == lon2

        # 3. History Verification (Action stored)
        assert len(picker.history) == 1
        history_entry = picker.history[0]
        assert history_entry[0] == "transect"
        assert (
            history_entry[2] is mock_final_artist
        )  # Ensure the cleanup artist is stored

        # 4. Plotting Verification (Final line drawn)
        # Check the *second* call to plot()
        mock_plot.assert_called_with(
            [lon1, lon2], [lat1, lat2], "b-", linewidth=2, zorder=9
        )
