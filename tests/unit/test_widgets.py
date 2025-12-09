from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import pytest

# Import the system under test
from cruiseplan.interactive.widgets import ModeIndicator, StatusDisplay

# --- Mocking Fixture for Matplotlib Axes ---


@pytest.fixture
def mock_axes():
    """Returns a mock Axes object with necessary figure and canvas attributes."""
    mock_canvas = MagicMock()
    mock_figure = MagicMock()
    mock_figure.canvas = mock_canvas

    mock_ax = MagicMock(spec=plt.Axes)
    mock_ax.figure = mock_figure
    # Create separate mock objects for each text call
    mock_ax.text.side_effect = lambda *args, **kwargs: MagicMock()
    mock_ax.transAxes = MagicMock()

    return mock_ax


# --- ModeIndicator Tests ---


@patch("cruiseplan.interactive.widgets.plt.Rectangle")
def test_mode_indicator_initialization(mock_rect, mock_axes: MagicMock):
    """Test initialization and display setup."""
    modes = ["navigation", "point"]
    indicator = ModeIndicator(mock_axes, modes, initial_mode="point")

    assert indicator.current_mode == "point"

    # Check that setup display was called once (which calls _update_display)
    assert mock_axes.set_xticks.call_count >= 1
    assert mock_axes.clear.call_count >= 1

    # Check that the text was created for the initial mode
    mock_axes.text.assert_called_with(
        0.5,
        0.5,
        "Mode: Point",
        ha="center",
        va="center",
        fontweight="bold",
        fontsize=10,
        color="#4169E1",  # Royal blue for 'point'
    )

    # Check that canvas was drawn
    mock_axes.figure.canvas.draw_idle.assert_called_once()


@patch("cruiseplan.interactive.widgets.plt.Rectangle")
def test_mode_indicator_set_mode_update(mock_rect, mock_axes: MagicMock):
    """Test mode switching and visual update."""
    modes = ["navigation", "point"]
    indicator = ModeIndicator(mock_axes, modes, initial_mode="navigation")

    # Reset mocks after initialization calls
    mock_axes.clear.reset_mock()
    mock_axes.figure.canvas.draw_idle.reset_mock()

    indicator.set_mode("line")  # Invalid mode, should not change
    assert indicator.current_mode == "navigation"

    indicator.set_mode("point")
    assert indicator.current_mode == "point"

    # Assert clear and draw_idle were called once each
    mock_axes.clear.assert_called_once()
    mock_axes.figure.canvas.draw_idle.assert_called_once()

    # Check update for the new mode color
    mock_axes.text.assert_called_with(
        0.5,
        0.5,
        "Mode: Point",
        ha="center",
        va="center",
        fontweight="bold",
        fontsize=10,
        color="#4169E1",  # Royal blue for 'point'
    )


def test_mode_indicator_callbacks(mock_axes: MagicMock):
    """Test that callbacks are triggered correctly on mode change."""
    modes = ["navigation", "point"]
    indicator = ModeIndicator(mock_axes, modes, initial_mode="navigation")

    mock_callback = MagicMock()
    indicator.on_mode_change("point", mock_callback)

    indicator.set_mode("point")

    # Assert callback was called with old and new modes
    mock_callback.assert_called_once_with("navigation", "point")


# --- StatusDisplay Tests ---


def test_status_display_initialization(mock_axes: MagicMock):
    """Test initialization creates the five required text lines."""
    display = StatusDisplay(mock_axes)

    # Check initial setup
    mock_axes.clear.assert_called_once()
    mock_axes.set_xticks.assert_called_once()

    # Check that 5 status lines were created
    assert len(display.status_lines) == 5

    # Check initialization of one line (e.g., Stations)
    mock_axes.text.assert_any_call(
        0.05,
        0.55,
        "Stations: 0",
        fontsize=9,
        transform=mock_axes.transAxes,
        weight="bold",
    )


def test_status_display_update_coordinates(mock_axes: MagicMock):
    """Test coordinate display, focusing on Degrees Decimal Minutes formatting."""
    display = StatusDisplay(mock_axes)

    # Case 1: Positive Lat/Negative Lon (Atlantic Ocean)
    lat_in = 47.5
    lon_in = -52.7

    # Expected DDM format: 47° 30.00'N, 052° 42.00'W
    expected_str = "47° 30.00'N, 052° 42.00'W"

    display.update_coordinates(lat_in, lon_in)

    # Check the first status line (index 0)
    display.status_lines[0].set_text.assert_called_once_with(
        f"Coordinates: {expected_str}"
    )
    display.status_lines[0].set_text.reset_mock()

    # Case 2: Negative Lat/Positive Lon (South East Pacific)
    lat_in_s = -35.25
    lon_in_e = 175.4

    # Expected DDM format: 35° 15.00'S, 175° 24.00'E
    expected_str_2 = "35° 15.00'S, 175° 24.00'E"

    display.update_coordinates(lat_in_s, lon_in_e)

    display.status_lines[0].set_text.assert_called_once_with(
        f"Coordinates: {expected_str_2}"
    )


def test_status_display_update_depth(mock_axes: MagicMock):
    """Test depth display handles depth (negative) and elevation (positive)."""
    display = StatusDisplay(mock_axes)

    # Case 1: Ocean Depth (Negative)
    # Here's a funny one - depth is negative, but we display positive depth value. But there is a material difference when
    # rounding negative vs positive numbers.
    display.update_depth(-3500.5)
    display.status_lines[1].set_text.assert_called_once_with(
        "Depth: 3500 m"
    )  # Rounded up
    display.status_lines[1].set_text.reset_mock()

    # Case 2: Land Elevation (Positive)
    display.update_depth(500.1)
    display.status_lines[1].set_text.assert_called_once_with(
        "Elevation: +500 m"
    )  # Rounded down
    display.status_lines[1].set_text.reset_mock()

    # Case 3: None
    display.update_depth(None)
    display.status_lines[1].set_text.assert_called_once_with("Depth: --")


def test_status_display_update_counts(mock_axes: MagicMock):
    """Test updating the operation counters."""
    display = StatusDisplay(mock_axes)

    display.update_counts(stations=5, transects=2, areas=1)

    # Check the counter lines (indices 2, 3, 4)
    display.status_lines[2].set_text.assert_called_with("Stations: 5")
    display.status_lines[3].set_text.assert_called_with("Transects: 2")
    display.status_lines[4].set_text.assert_called_with("Areas: 1")

    # Assert canvas draw was called
    mock_axes.figure.canvas.draw_idle.assert_called_once()
