"""The library leaves the caller's logging configuration alone."""

import logging
from pathlib import Path

import pytest

import cruiseplan
from cruiseplan.utils.logging import debug_logging

FIXTURES = Path(__file__).parent.parent / "fixtures"
TC1 = FIXTURES / "tc1_single.yaml"


@pytest.fixture
def caller_root_handler():
    """Install a root handler the way a notebook user would, then remove it."""
    root = logging.getLogger()
    handler = logging.StreamHandler()
    saved_handlers, saved_level = root.handlers[:], root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    yield handler
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


@pytest.mark.parametrize("verbose", [False, True])
def test_api_keeps_root_handlers(tmp_path, caller_root_handler, verbose):
    """API verbs do not replace the root logger's handlers or level."""
    root = logging.getLogger()
    handlers_before = root.handlers[:]

    cruiseplan.validate(config_file=TC1, check_depths=False, verbose=verbose)
    cruiseplan.schedule(
        config_file=TC1, output_dir=str(tmp_path), format=None, verbose=verbose
    )

    assert root.handlers == handlers_before
    assert caller_root_handler in root.handlers
    assert root.level == logging.INFO


def test_verbose_restores_package_level(tmp_path):
    """verbose=True lowers the cruiseplan logger only for the call."""
    package_logger = logging.getLogger("cruiseplan")
    level_before = package_logger.level

    cruiseplan.schedule(
        config_file=TC1, output_dir=str(tmp_path), format=None, verbose=True
    )

    assert package_logger.level == level_before


def test_debug_logging_sets_and_restores():
    """debug_logging sets DEBUG inside the block and restores the previous level."""
    package_logger = logging.getLogger("cruiseplan")
    package_logger.setLevel(logging.WARNING)
    try:
        with debug_logging():
            assert package_logger.level == logging.DEBUG
        assert package_logger.level == logging.WARNING
        with debug_logging(enabled=False):
            assert package_logger.level == logging.WARNING
    finally:
        package_logger.setLevel(logging.NOTSET)
