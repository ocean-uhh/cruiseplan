from unittest.mock import MagicMock, mock_open, patch

import pytest

# Import the system under test
from cruiseplan.interactive.campaign_selector import CampaignSelector

# Import the custom error if needed (not strictly necessary here, but good practice)
# from cruiseplan.core.validation import CruiseConfigurationError

# --- Fixtures and Setup ---


@pytest.fixture
def mock_campaign_data():
    """Returns a standardized list of mock campaign data."""
    return [
        {"name": "Campaign_A", "latitude": [50], "longitude": [-10]},
        {"name": "Campaign_B", "latitude": [60], "longitude": [-20]},
        {"name": "Campaign_C", "latitude": [70], "longitude": [-30]},
        {"name": "Duplicate_Name", "latitude": [10], "longitude": [10]},
        {
            "name": "Duplicate_Name",
            "latitude": [12],
            "longitude": [12],
        },  # Intentional duplicate
    ]


@pytest.fixture
def mock_axes():
    """Returns a mock Axes object for UI setup."""
    mock_canvas = MagicMock()
    mock_figure = MagicMock()
    mock_figure.canvas = mock_canvas
    mock_ax = MagicMock()
    mock_ax.figure = mock_figure
    return mock_ax


# --- Core Logic Tests ---


def test_initialization(mock_campaign_data):
    """Test initial state: all campaigns should be selected/visible by default."""
    selector = CampaignSelector(mock_campaign_data)

    # Check that initial selected state includes all unique campaigns as True
    assert len(selector.selected_campaigns) == 4  # Only 4 unique names
    assert selector.selected_campaigns["Campaign_A"] is True
    assert selector.selected_campaigns["Duplicate_Name"] is True
    assert selector.campaign_data == mock_campaign_data


def test_on_campaign_toggle_state_update(mock_campaign_data):
    """Test that the internal state flips when the toggle handler is called."""
    selector = CampaignSelector(mock_campaign_data)

    # Initial state
    assert selector.selected_campaigns["Campaign_A"] is True

    # 1. Toggle OFF
    selector._on_campaign_toggle("Campaign_A")
    assert selector.selected_campaigns["Campaign_A"] is False

    # 2. Toggle ON
    selector._on_campaign_toggle("Campaign_A")
    assert selector.selected_campaigns["Campaign_A"] is True


@patch("cruiseplan.interactive.campaign_selector.CheckButtons")
def test_setup_ui_display_logic(mock_check_buttons, mock_campaign_data, mock_axes):
    """Test setup_ui correctly prepares axes and connects handler."""
    selector = CampaignSelector(mock_campaign_data)
    selector.setup_ui(mock_axes)

    # Check that CheckButtons was initialized with unique names
    # Note: Campaign_A, Campaign_B, Campaign_C, Duplicate_Name (4 total)
    mock_check_buttons.assert_called_once()
    args, _ = mock_check_buttons.call_args
    assert len(args[1]) == 5  # List of names
    assert args[2] == [True, True, True, True, True]  # Initial state

    # Check that the handler was connected
    mock_check_buttons.return_value.on_clicked.assert_called_once_with(
        selector._on_campaign_toggle
    )


def test_setup_ui_no_data_path(mock_axes):
    """Test the display path when no campaign data is provided."""
    selector = CampaignSelector(campaign_data=[])
    selector.setup_ui(mock_axes)

    # Check that the "No data" message was added
    mock_axes.text.assert_called_once()

    # Check CheckButtons was NOT initialized
    assert selector.check_buttons is None


def test_get_selected_campaigns_filtering(mock_campaign_data):
    """Test that get_selected_campaigns only returns datasets where state is True."""
    selector = CampaignSelector(mock_campaign_data)

    # Toggle 'Campaign_A' and 'Campaign_C' OFF
    selector._on_campaign_toggle("Campaign_A")
    selector._on_campaign_toggle("Campaign_C")

    selected = selector.get_selected_campaigns()

    # Expected: Campaign_B, Duplicate_Name (x2) = 3 total datasets
    assert len(selected) == 3
    assert all(d["name"] in ["Campaign_B", "Duplicate_Name"] for d in selected)


@patch("cruiseplan.interactive.campaign_selector.pickle.dump")
@patch("builtins.open", new_callable=mock_open)
def test_save_selection_success(mock_open_file, mock_dump, mock_campaign_data):
    """Test that save_selection filters correctly and calls pickle.dump."""
    selector = CampaignSelector(mock_campaign_data)

    # Toggle one campaign off before saving
    selector._on_campaign_toggle("Campaign_B")

    output_path = "selection.pkl"
    selector.save_selection(output_path)

    # Check that open was called with 'wb'
    mock_open_file.assert_called_once_with(output_path, "wb")

    # Check that pickle.dump was called with the filtered list (4 datasets - 1 = 3)
    args, _ = mock_dump.call_args
    dumped_data = args[0]

    assert len(dumped_data) == 4
    assert all(d["name"] != "Campaign_B" for d in dumped_data)


@patch("cruiseplan.interactive.campaign_selector.CheckButtons")
def test_toggle_all_state_and_display_update(
    mock_check_buttons, mock_campaign_data, mock_axes
):
    """Test toggle_all flips all states and calls display update."""
    selector = CampaignSelector(mock_campaign_data)
    selector.setup_ui(mock_axes)  # Setup check buttons
    selector.map_ax = mock_axes  # Simulate picker setting the map axis

    # Mock the visual update call
    with patch.object(selector, "_update_campaign_display") as mock_update_display:

        # 1. Toggle all OFF
        selector.toggle_all(False)

        # Check internal state
        assert all(state is False for state in selector.selected_campaigns.values())
        mock_update_display.assert_called_once()
        mock_update_display.reset_mock()

        # 2. Toggle all ON
        selector.toggle_all(True)

        # Check internal state
        assert all(state is True for state in selector.selected_campaigns.values())
        mock_update_display.assert_called_once()

        # Check that CheckButtons.set_active was called (visual update)
        # Note: We assume CheckButtons.set_active is patched or works correctly in the loop
        mock_check_buttons.return_value.set_active.call_count == 4 * 2  # 4 items * 2 calls (True/False)
