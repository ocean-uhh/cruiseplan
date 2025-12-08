import logging
import pickle
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Simple file-based cache using Pickle.
    """

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache if it exists."""
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
        """Save item to cache."""
        cache_file = self.cache_dir / f"{key}.pkl"
        try:
            with open(cache_file, "wb") as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                logger.debug(f"Cached: {key}")
        except Exception as e:
            logger.error(f"Cache write error for {key}: {e}")

    def clear(self, key: str) -> None:
        """Remove specific item."""
        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            cache_file.unlink()
