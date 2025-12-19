"""
cruiseplan.core package

This package contains the core classes and logic for cruise planning:

- :class:`Cruise`: Main container for cruise configuration, validation, and data management
- :class:`Leg`: Represents discrete working areas or time periods in a cruise
- :class:`BaseOperation`: Base class for individual cruise operations
- :class:`Cluster`: Container for operation boundary management and reordering
- :mod:`validation`: Pydantic models and validation schemas for cruise data

The core package provides the fundamental building blocks for defining and managing
oceanographic cruise plans, including station definitions, transit routes, and
operational sequences.
"""
