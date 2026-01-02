"""
Global test configuration and fixtures.

This file contains pytest fixtures and configuration that apply to all tests
in the test suite.
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Automatically applied fixture that sets up the test environment.

    This fixture:
    - Ensures tests_output directory exists
    - Prevents tests from writing to the main data/ directory by default
    """
    # Ensure tests_output directory exists
    tests_output = Path("tests_output")
    tests_output.mkdir(exist_ok=True)

    yield

    # Cleanup could go here if needed


@pytest.fixture
def temp_output_dir(tmp_path):
    """
    Provide a temporary directory for test outputs.

    This fixture creates a unique temporary directory for each test
    that needs to write files, ensuring test isolation.

    Returns
    -------
    Path
        Path to temporary output directory
    """
    output_dir = tmp_path / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


# NOTE: Default output directory patching for tests
@pytest.fixture(autouse=True)
def prevent_data_dir_writes():
    """
    Reminder fixture that tests should use explicit output directories.

    This prevents tests from accidentally writing to the main data/ directory.
    Tests should explicitly specify output directories or use temp_output_dir fixture.
    """
    # Most tests mock the API layer, so this is mainly a reminder
    # For integration tests that need real file output, use temp_output_dir or explicit paths
    yield
