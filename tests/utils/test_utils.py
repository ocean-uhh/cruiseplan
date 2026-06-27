"""
Common test utilities and helpers for cruiseplan test suite.

Provides shared functions for fixture loading, mock creation, and
timeline validation to reduce code duplication across test files.
"""

from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock


def get_fixture_path(test_file_path: Path, filename: str) -> Path:
    """
    Get path to test fixture file relative to test file location.

    Parameters
    ----------
    test_file_path : Path
        Path to the test file (usually __file__)
    filename : str
        Name of the fixture file

    Returns
    -------
    Path
        Full path to fixture file
    """
    return test_file_path.parent.parent / "fixtures" / filename


def create_mock_port(
    name: str, latitude: float, longitude: float, display_name: Optional[str] = None
) -> MagicMock:
    """
    Create a standardized mock port object for testing.

    Parameters
    ----------
    name : str
        Port name/identifier
    latitude : float
        Port latitude
    longitude : float
        Port longitude
    display_name : str, optional
        Human-readable display name

    Returns
    -------
    MagicMock
        Mock port object with standard attributes
    """
    mock_port = MagicMock()
    mock_port.name = name
    mock_port.latitude = latitude
    mock_port.longitude = longitude
    mock_port.display_name = display_name or name
    return mock_port


def validate_timeline_structure(timeline: list[dict[str, Any]]) -> bool:
    """
    Validate that a timeline has the expected structure.

    Parameters
    ----------
    timeline : List[Dict[str, Any]]
        Timeline data structure to validate

    Returns
    -------
    bool
        True if timeline structure is valid

    Raises
    ------
    AssertionError
        If timeline structure is invalid
    """
    assert isinstance(timeline, list), "Timeline must be a list"

    for i, activity in enumerate(timeline):
        assert isinstance(activity, dict), f"Activity {i} must be a dict"

        # Check required fields
        required_fields = ["name", "start_time", "end_time", "duration"]
        for field in required_fields:
            assert field in activity, f"Activity {i} missing required field: {field}"

        # Check that times are properly formatted
        assert isinstance(
            activity["start_time"], str
        ), f"Activity {i} start_time must be string"
        assert isinstance(
            activity["end_time"], str
        ), f"Activity {i} end_time must be string"
        assert isinstance(
            activity["duration"], (int, float)
        ), f"Activity {i} duration must be numeric"

    return True


def count_activities_by_type(timeline: list[dict[str, Any]]) -> dict[str, int]:
    """
    Count activities in timeline by op_type.

    Parameters
    ----------
    timeline : List[Dict[str, Any]]
        Timeline data structure

    Returns
    -------
    Dict[str, int]
        Count of activities by op_type
    """
    counts = {}
    for activity in timeline:
        op_type = activity.get("op_type", "unknown")
        counts[op_type] = counts.get(op_type, 0) + 1
    return counts


def get_activities_by_type(
    timeline: list[dict[str, Any]], op_type: str
) -> list[dict[str, Any]]:
    """
    Filter timeline activities by op_type.

    Parameters
    ----------
    timeline : List[Dict[str, Any]]
        Timeline data structure
    op_type : str
        Operation type to filter by

    Returns
    -------
    List[Dict[str, Any]]
        Activities matching the specified op_type
    """
    return [activity for activity in timeline if activity.get("op_type") == op_type]


def assert_activity_duration_positive(timeline: list[dict[str, Any]]) -> None:
    """
    Assert that all activities in timeline have positive duration.

    Parameters
    ----------
    timeline : List[Dict[str, Any]]
        Timeline data structure to check

    Raises
    ------
    AssertionError
        If any activity has non-positive duration
    """
    for i, activity in enumerate(timeline):
        duration = activity.get("duration", 0)
        assert (
            duration > 0
        ), f"Activity {i} ({activity.get('name', 'unnamed')}) has non-positive duration: {duration}"


def assert_timeline_chronological(timeline: list[dict[str, Any]]) -> None:
    """
    Assert that timeline activities are in chronological order.

    Parameters
    ----------
    timeline : List[Dict[str, Any]]
        Timeline data structure to check

    Raises
    ------
    AssertionError
        If activities are not in chronological order
    """
    from datetime import datetime

    prev_end = None
    for i, activity in enumerate(timeline):
        start_time = datetime.fromisoformat(
            activity["start_time"].replace("Z", "+00:00")
        )

        if prev_end and start_time < prev_end:
            raise AssertionError(
                f"Activity {i} ({activity.get('name', 'unnamed')}) starts before previous activity ends"
            )

        end_time = datetime.fromisoformat(activity["end_time"].replace("Z", "+00:00"))
        prev_end = end_time
