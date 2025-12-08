# cruiseplan/data/bathymetry.py
import logging
from pathlib import Path

import netCDF4 as nc
import numpy as np
import requests
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Constants
# Primary: NGDC (National Geophysical Data Center)
# Backup: NCEI (National Centers for Environmental Information)
ETOPO_URLS = [
    "https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_bed_elev_netcdf/ETOPO_2022_v1_60s_N90W180_bed.nc",
    "https://www.ncei.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_bed_elev_netcdf/ETOPO_2022_v1_60s_N90W180_bed.nc",
]
ETOPO_FILENAME = "ETOPO_2022_v1_60s_N90W180_bed.nc"

# Constants from Spec
DEPTH_CONTOURS = [-5000, -4000, -3000, -2000, -1000, -500, -200, -100, -50, 0]


class BathymetryManager:
    """
    Handles ETOPO bathymetry data with lazy loading and bilinear interpolation.
    Implements 'Dev Mode' (returns mock depth) if data is missing.
    """

    def __init__(self, source: str = "etopo2022", data_dir: str = "data"):
        self.source = source
        # Resolve path relative to this file's location to be safe
        root = Path(__file__).parent.parent.parent
        self.data_dir = root / data_dir / "bathymetry"

        self._is_mock = True
        self._dataset = None
        self._lats = None
        self._lons = None

        self._initialize_data()

    def _initialize_data(self):
        """
        Attempts to load NetCDF. Falls back to Mock mode on failure.
        """
        # Map simple source name to actual filename
        filename = ETOPO_FILENAME if self.source == "etopo2022" else f"{self.source}.nc"
        file_path = self.data_dir / filename

        if file_path.exists():
            try:
                # Load using netCDF4 for efficient lazy slicing
                self._dataset = nc.Dataset(file_path, "r")
                # Cache coordinate arrays for fast search
                # (These are 1D arrays, so they fit easily in memory)
                self._lats = self._dataset.variables["lat"][:]
                self._lons = self._dataset.variables["lon"][:]
                self._is_mock = False
                logger.info(f"✅ Loaded bathymetry from {file_path}")
            except Exception as e:
                logger.warning(
                    f"❌ Failed to load bathymetry file: {e}. Using MOCK mode."
                )
                self._is_mock = True
        else:
            logger.info(f"⚠️ No bathymetry file found at {file_path}. Using MOCK mode.")
            logger.info(
                "   Run `cruiseplan.data.bathymetry.download_bathymetry()` to fetch it."
            )
            self._is_mock = True

    def get_depth_at_point(self, lat: float, lon: float) -> float:
        """
        Returns depth in meters (negative down).
        Uses bilinear interpolation on the ETOPO grid.
        """
        if self._is_mock:
            return self._get_mock_depth(lat, lon)

        try:
            return self._interpolate_depth(lat, lon)
        except Exception as e:
            logger.error(f"Error interpolating depth at {lat}, {lon}: {e}")
            return -9999.0

    def get_grid_subset(self, lat_min, lat_max, lon_min, lon_max, stride=1):
        """
        Returns (lons, lats, z) 2D arrays for contour plotting.
        Supports 'stride' to downsample large regions for performance.
        """
        if self._is_mock:
            # Generate synthetic grid
            lat_range = np.linspace(lat_min, lat_max, 100)
            lon_range = np.linspace(lon_min, lon_max, 100)
            xx, yy = np.meshgrid(lon_range, lat_range)
            # Same formula as get_mock_depth but vectorized
            zz = -((np.abs(yy) * 100) + (np.abs(xx) * 50)) % 4000 - 100
            return xx, yy, zz

        # Real Data Slicing
        # Find indices
        lat_idx_min = np.searchsorted(self._lats, lat_min)
        lat_idx_max = np.searchsorted(self._lats, lat_max)
        lon_idx_min = np.searchsorted(self._lons, lon_min)
        lon_idx_max = np.searchsorted(self._lons, lon_max)

        # Handle edge cases (if requested area is outside dataset)
        lat_idx_min = max(0, min(lat_idx_min, len(self._lats) - 1))
        lat_idx_max = max(0, min(lat_idx_max, len(self._lats) - 1))
        lon_idx_min = max(0, min(lon_idx_min, len(self._lons) - 1))
        lon_idx_max = max(0, min(lon_idx_max, len(self._lons) - 1))

        if lat_idx_min >= lat_idx_max or lon_idx_min >= lon_idx_max:
            # Return empty grid if invalid slice
            return np.array([]), np.array([]), np.array([])

        # Slice with stride
        lats = self._lats[lat_idx_min:lat_idx_max:stride]
        lons = self._lons[lon_idx_min:lon_idx_max:stride]

        # Read subset from disk
        z = self._dataset.variables["z"][
            lat_idx_min:lat_idx_max:stride, lon_idx_min:lon_idx_max:stride
        ]

        xx, yy = np.meshgrid(lons, lats)
        return xx, yy, z

    def _interpolate_depth(self, lat: float, lon: float) -> float:
        """
        Performs bilinear interpolation logic.
        """
        # 1. Bounds Check
        if lat < self._lats[0] or lat > self._lats[-1]:
            return -9999.0
        if lon < self._lons[0] or lon > self._lons[-1]:
            return -9999.0

        # 2. Find Indices (Fast search on sorted arrays)
        lat_idx = np.searchsorted(self._lats, lat)
        lon_idx = np.searchsorted(self._lons, lon)

        # Ensure indices are within bounds for 2x2 grid
        lat_idx = max(1, min(lat_idx, len(self._lats) - 1))
        lon_idx = max(1, min(lon_idx, len(self._lons) - 1))

        # 3. Extract 2x2 Grid (Lazy Load from Disk)
        y_indices = [lat_idx - 1, lat_idx]
        x_indices = [lon_idx - 1, lon_idx]

        # Read only these 4 values from disk
        z_grid = self._dataset.variables["z"][y_indices, x_indices]
        y_coords = self._lats[y_indices]
        x_coords = self._lons[x_indices]

        # 4. Bilinear Interpolation
        dy = y_coords[1] - y_coords[0]
        dx = x_coords[1] - x_coords[0]

        if dy == 0 or dx == 0:
            return float(z_grid[0, 0])

        u = (lon - x_coords[0]) / dx
        v = (lat - y_coords[0]) / dy

        depth = (
            (1 - u) * (1 - v) * z_grid[0, 0]
            + u * (1 - v) * z_grid[0, 1]
            + (1 - u) * v * z_grid[1, 0]
            + u * v * z_grid[1, 1]
        )

        return float(depth)

    def _get_mock_depth(self, lat: float, lon: float) -> float:
        """
        Deterministic mock depth based on coordinates.
        Useful for testing without needing random numbers.
        """
        val = (abs(lat) * 100) + (abs(lon) * 50)
        return -(val % 4000) - 100

    def close(self):
        if self._dataset and self._dataset.isopen():
            self._dataset.close()


def download_bathymetry(target_dir: str = "data"):
    """Downloads ETOPO 2022 file with progress bar."""
    root = Path(__file__).parent.parent.parent
    output_dir = root / target_dir / "bathymetry"
    output_dir.mkdir(parents=True, exist_ok=True)

    local_path = output_dir / ETOPO_FILENAME

    if local_path.exists():
        print(f"File already exists at {local_path}")
        return

    print(f"Downloading ETOPO dataset to {local_path}...")

    for url in ETOPO_URLS:
        try:
            print(f"Attempting download from: {url}")
            response = requests.get(
                url, stream=True, timeout=10
            )  # 10s timeout for connect
            response.raise_for_status()

            total_size = int(response.headers.get("Content-Length", 0))

            with (
                open(local_path, "wb") as file,
                tqdm(
                    desc="Downloading ETOPO",
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar,
            ):
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
                    bar.update(len(chunk))

            print("\nDownload complete!")
            return  # Success, exit function
        except Exception as e:
            print(f"Failed to download from {url}")
            print(f"   Error: {e}")
            if local_path.exists():
                local_path.unlink()  # Cleanup partial download

    # If we reach here, all URLs failed
    print("\n" + "=" * 60)
    print("⛔ AUTOMATIC DOWNLOAD FAILED")
    print("=" * 60)
    print("Please download the file manually using your browser:")
    print(f"URL: {ETOPO_URLS[0]}")
    print(f"Save to: {local_path}")
    print("=" * 60 + "\n")


# Singleton instance
bathymetry = BathymetryManager()
