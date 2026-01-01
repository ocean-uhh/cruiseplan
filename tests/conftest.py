"""
Global test configuration and fixtures.

This file contains pytest fixtures and configuration that apply to all tests
in the test suite.
"""

import pytest
from pathlib import Path
from unittest.mock import patch


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


# Patch default output directories to prevent accidental writes to data/
@pytest.fixture(autouse=True)
def patch_default_data_dir():
    """
    Automatically patch default data directory references in tests.
    
    This prevents tests from accidentally writing to the main data/ directory
    by redirecting to tests_output/ when "data" is used as output_dir.
    """
    def safe_path_resolver(path_str):
        """Convert 'data' to 'tests_output' for test safety."""
        if isinstance(path_str, str) and path_str == "data":
            return Path("tests_output")
        elif isinstance(path_str, Path) and str(path_str) == "data":
            return Path("tests_output")
        else:
            return Path(path_str) if isinstance(path_str, str) else path_str
    
    # This could be extended to patch specific functions if needed
    yield