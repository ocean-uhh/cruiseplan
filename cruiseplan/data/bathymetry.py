# cruiseplan/data/bathymetry.py
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants from Spec
DEPTH_CONTOURS = [0, -50, -100, -200, -500, -1000, -2000, -3000, -4000, -5000]


class BathymetryManager:
    def __init__(self, source: str = "etopo2022", data_dir: str = "data"):
        self.source = source
        self.data_dir = Path(data_dir)
        self._is_mock = True
        self._dataset = None

        self._initialize_data()

    def _initialize_data(self):
        """
        Attempts to load NetCDF. Falls back to Mock mode on failure.
        """
        file_path = self.data_dir / f"{self.source}.nc"

        if file_path.exists():
            try:
                # Placeholder for XArray loading (Phase 3)
                # self._dataset = xr.open_dataset(file_path)
                self._is_mock = False
                logger.info(f"Loaded bathymetry from {file_path}")
            except Exception as e:
                logger.warning(f"Failed to load bathymetry file: {e}. Using MOCK mode.")
                self._is_mock = True
        else:
            logger.info(f"No bathymetry file found at {file_path}. Using MOCK mode.")
            self._is_mock = True

    def get_depth_at_point(self, lat: float, lon: float) -> float:
        """
        Returns depth in meters (negative down).
        """
        if self._is_mock:
            return self._get_mock_depth(lat, lon)

        # Real interpolation logic goes here in Phase 3
        return -9999.0

    def _get_mock_depth(self, lat: float, lon: float) -> float:
        """
        Deterministic mock depth based on coordinates.
        Useful for testing without needing random numbers.
        """
        # Simple formula to give different depths at different places
        # ensuring it's deterministic for tests.
        val = (abs(lat) * 100) + (abs(lon) * 50)
        return -(val % 4000) - 100  # Returns between -100 and -4100m


# Singleton instance
bathymetry = BathymetryManager()
