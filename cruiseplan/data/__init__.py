"""
cruiseplan.data package.

This package contains data management and external data integration modules:

- :mod:`bathymetry`: Bathymetry data handling using ETOPO datasets with interpolation
- :mod:`cache`: File-based caching system for expensive computations and downloads
- :mod:`eez_boundaries`: EEZ boundary data management and spatial operations
- :mod:`pangaea`: Integration with Pangaea data repository for oceanographic data

These modules handle external data sources, caching strategies, and data processing
required for cruise planning, including bathymetric information and scientific datasets.
"""

# Note: submodules are intentionally not imported here to keep optional dependencies lazy.
