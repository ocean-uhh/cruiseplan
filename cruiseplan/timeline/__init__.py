"""
cruiseplan.timeline package.

This package contains scheduling and timeline generation modules for cruise planning:

- :mod:`record`: the timeline record (:class:`ActivityRecord`) and :data:`Timeline`
- :mod:`distance`: Geographic distance calculations using Haversine formula
- :mod:`duration`: Time duration calculations for cruise operations and activities
- :mod:`scheduler`: Core scheduling logic for generating cruise timelines

These modules provide the mathematical and algorithmic foundation for determining
distances, durations and scheduling sequences in oceanographic cruises.
"""

from .record import ActivityRecord, Timeline
from .scheduler import generate_timeline

__all__ = ["ActivityRecord", "Timeline", "generate_timeline"]


def __getattr__(name: str) -> object:
    """Resolve deprecated names (CruiseSchedule) with a warning."""
    from cruiseplan import _deprecated

    return _deprecated.module_getattr(__name__, name, {"CruiseSchedule": Timeline})
