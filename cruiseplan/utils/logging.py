"""
Logging helpers for the cruiseplan package.

The library never configures logging handlers: modules log through
``logging.getLogger(__name__)`` and the application (the ``cruiseplan``
command line, a script or a notebook) decides where messages go. The
API functions' ``verbose=`` parameter only lowers the level of the
``cruiseplan`` logger for the duration of the call.
"""

import functools
import inspect
import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import ParamSpec, TypeVar

PACKAGE_LOGGER = "cruiseplan"

P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def debug_logging(enabled: bool = True) -> Iterator[None]:
    """
    Set the ``cruiseplan`` logger to DEBUG inside the block, then restore it.

    Handlers are left alone, so the messages reach whatever handlers the
    application configured.

    Parameters
    ----------
    enabled : bool, optional
        If False, the block runs with the logger unchanged (default True).
    """
    package_logger = logging.getLogger(PACKAGE_LOGGER)
    previous = package_logger.level
    if enabled:
        package_logger.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        package_logger.setLevel(previous)


def honors_verbose(func: Callable[P, R]) -> Callable[P, R]:
    """
    Run *func* under :func:`debug_logging` when it is called with ``verbose=True``.

    Parameters
    ----------
    func : callable
        A function with a ``verbose`` parameter.

    Returns
    -------
    callable
        The wrapped function, with the same signature and docstring.
    """
    signature = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        bound = signature.bind_partial(*args, **kwargs)
        verbose = bound.arguments.get(
            "verbose", signature.parameters["verbose"].default
        )
        with debug_logging(bool(verbose)):
            return func(*args, **kwargs)

    return wrapper
