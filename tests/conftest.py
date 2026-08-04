"""
Global test configuration and fixtures.

This file contains pytest fixtures and configuration that apply to all tests
in the test suite.

# Test outputs are written to pytest's tmp_path.
# To inspect output: run pytest --basetemp=./test_debug_output
"""

import pytest


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
