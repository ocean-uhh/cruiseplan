import logging
import pickle
from pathlib import Path
from typing import Any, Optional

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

    def __init__(self, cache_dir: str = ".cache"):
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

    def get(self, key: str) -> Optional[Any]:
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
                with open(cache_file, "rb") as f:
                    data = pickle.load(f)
                    logger.debug(f"Cache hit: {key}")
                    return data
            except Exception as e:
                logger.warning(f"Cache read error for {key}: {e}")
        return None

    def set(self, key: str, data: Any) -> None:
        """
        Save item to cache.

        Parameters
        ----------
        key : str
            Cache key identifier.
        data : Any
            Data to cache. Must be pickle-serializable.
        """
        cache_file = self.cache_dir / f"{key}.pkl"
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                logger.debug(f"Cached: {key}")
        except Exception as e:
            logger.error(f"Cache write error for {key}: {e}")

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
