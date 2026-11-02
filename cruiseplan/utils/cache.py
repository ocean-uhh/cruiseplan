"""
Data caching utilities for CruisePlan.

This module provides caching functionality for storing and retrieving
expensive computations and external data.
"""

import logging
import pickle
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Simple file-based cache using Pickle.

    Provides basic caching functionality with automatic serialization
    using Python's pickle module. Cache files are stored as .pkl files
    in the specified cache directory.

    Attributes
    ----------
    cache_dir : Path
        Directory where cache files are stored.
    """

    def __init__(self, cache_dir: str = ".cache") -> None:
        """
        Initialize cache manager.

        Parameters
        ----------
        cache_dir : str, optional
            Directory path for cache storage (default: ".cache").
            Will be created if it doesn't exist.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Any | None:  # noqa: ANN401 - unpickled data of any type
        """
        Retrieve item from cache if it exists.

        Parameters
        ----------
        key : str
            Cache key identifier.

        Returns
        -------
        Optional[Any]
            Cached data if found and successfully loaded, None otherwise.
        """
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            try:
                with cache_file.open("rb") as f:
                    data = pickle.load(f)
                    logger.debug(f"Cache hit: {key}")
                    return data
            except Exception as e:  # noqa: BLE001 - unreadable cache entry is a cache miss
                logger.warning(f"Cache read error for {key}: {e}")
        return None

    def set(self, key: str, data: object) -> None:
        """
        Save item to cache.

        Parameters
        ----------
        key : str
            Cache key identifier.
        data : object
            Data to cache. Must be pickle-serializable.
        """
        cache_file = self.cache_dir / f"{key}.pkl"
        try:
            with cache_file.open("wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                logger.debug(f"Cached: {key}")
        except Exception:
            logger.exception(f"Cache write error for {key}")

    def clear(self, key: str) -> None:
        """
        Remove specific item from cache.

        Parameters
        ----------
        key : str
            Cache key identifier to remove.
        """
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            cache_file.unlink()
