"""
cruiseplan.timeline package.

This package contains scheduling and timeline generation modules for cruise planning:

- :mod:`distance`: Geographic distance calculations using Haversine formula
- :mod:`duration`: Time duration calculations for cruise operations and activities
- :mod:`routing`: Route optimization and spatial planning algorithms
- :mod:`scheduler`: Core scheduling logic for generating cruise timelines

These modules provide the mathematical and algorithmic foundation for determining
distances, durations, optimal routes, and scheduling sequences in oceanographic cruises.
"""

from .scheduler import CruiseSchedule, generate_timeline

__all__ = ["CruiseSchedule", "generate_timeline"]
