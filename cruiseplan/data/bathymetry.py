# cruiseplan/data/bathymetry.py
import logging
from pathlib import Path

import netCDF4 as nc
import numpy as np
import requests
from tqdm import tqdm

from cruiseplan.utils.constants import FALLBACK_DEPTH

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

    Manages bathymetric data from ETOPO datasets, providing depth lookups
    and grid subsets for oceanographic applications. Implements fallback
    to mock data when bathymetry files are unavailable.

    Attributes
    ----------
    source : str
        Bathymetry data source identifier.
    data_dir : Path
        Directory containing bathymetry data files.
    _is_mock : bool
        Whether the manager is operating in mock mode.
    _dataset : Optional[nc.Dataset]
        NetCDF dataset object when loaded.
    _lats : Optional[np.ndarray]
        Latitude coordinate array.
    _lons : Optional[np.ndarray]
        Longitude coordinate array.
    """

    def __init__(self, source: str = "etopo2022", data_dir: str = "data"):
        """
        Initialize the bathymetry manager.

        Parameters
        ----------
        source : str, optional
            Bathymetry data source (default: "etopo2022").
        data_dir : str, optional
            Data directory relative to project root (default: "data").
        """
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
        Attempt to load NetCDF data, falling back to mock mode on failure.

        Tries to load the specified bathymetry dataset. If the file doesn't
        exist or cannot be loaded, switches to mock mode for testing.
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
        Get depth at a specific geographic point.

        Returns depth in meters (negative values indicate depth below sea level).
        Uses bilinear interpolation on the ETOPO grid for accurate results.

        Parameters
        ----------
        lat : float
            Latitude in decimal degrees.
        lon : float
            Longitude in decimal degrees.

        Returns
        -------
        float
            Depth in meters (negative for below sea level).
        """
        if self._is_mock:
            return self._get_mock_depth(lat, lon)

        try:
            return self._interpolate_depth(lat, lon)
        except Exception as e:
            logger.error(f"Error interpolating depth at {lat}, {lon}: {e}")
            return FALLBACK_DEPTH

    def get_grid_subset(self, lat_min, lat_max, lon_min, lon_max, stride=1):
        """
        Get a subset of the bathymetry grid for contour plotting.

        Returns 2D arrays suitable for matplotlib contour plotting.
        Supports downsampling with stride parameter for performance.

        Parameters
        ----------
        lat_min : float
            Minimum latitude of the subset.
        lat_max : float
            Maximum latitude of the subset.
        lon_min : float
            Minimum longitude of the subset.
        lon_max : float
            Maximum longitude of the subset.
        stride : int, optional
            Downsampling factor (default: 1, no downsampling).

        Returns
        -------
        tuple
            Tuple of (lons, lats, depths) as 2D numpy arrays for contour plotting.
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
        lat_idx_min = max(0, lat_idx_min)
        lat_idx_max = min(lat_idx_max, len(self._lats))
        lon_idx_min = max(0, lon_idx_min)
        lon_idx_max = min(lon_idx_max, len(self._lons))

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
        Perform bilinear interpolation on the bathymetry grid.

        Parameters
        ----------
        lat : float
            Latitude for interpolation.
        lon : float
            Longitude for interpolation.

        Returns
        -------
        float
            Interpolated depth value.
        """
        # 1. Bounds Check
        if lat < self._lats[0] or lat > self._lats[-1]:
            return FALLBACK_DEPTH
        if lon < self._lons[0] or lon > self._lons[-1]:
            return FALLBACK_DEPTH

        # 2. Find 2x2 Grid Indices
        # np.searchsorted gives the index *after* the point, so the grid is defined by [idx-1, idx]
        lon_idx = np.searchsorted(self._lons, lon)
        lat_idx = np.searchsorted(self._lats, lat)

        # Ensure indices are within bounds for the grid corners
        x0_idx = lon_idx - 1
        x1_idx = lon_idx
        y0_idx = lat_idx - 1
        y1_idx = lat_idx

        # Check against array limits (safety check, should be covered by bounds check)
        if (
            x1_idx >= len(self._lons)
            or y1_idx >= len(self._lats)
            or x0_idx < 0
            or y0_idx < 0
        ):
            return FALLBACK_DEPTH

        # 3. Extract 2x2 Grid (Lazy Load from Disk)
        # Note: z(lat, lon) -> z(y, x)
        z_grid = self._dataset.variables["z"][[y0_idx, y1_idx], [x0_idx, x1_idx]]
        y_coords = self._lats[[y0_idx, y1_idx]]
        x_coords = self._lons[[x0_idx, x1_idx]]

        # 4. Bilinear Interpolation (Corrected Formula)
        x0, x1 = x_coords[0], x_coords[1]
        y0, y1 = y_coords[0], y_coords[1]
        z00, z01, z10, z11 = z_grid[0, 0], z_grid[0, 1], z_grid[1, 0], z_grid[1, 1]

        # Check for zero spacing
        if x1 == x0 or y1 == y0:
            return float(z00)  # Fallback to nearest grid point

        u = (lon - x0) / (x1 - x0)  # Fractional distance in x
        v = (lat - y0) / (y1 - y0)  # Fractional distance in y

        # Bilinear interpolation formula
        depth = (
            z00 * (1 - u) * (1 - v)
            + z10 * u * (1 - v)
            + z01 * (1 - u) * v
            + z11 * u * v
        )

        return float(depth)

    def _get_mock_depth(self, lat: float, lon: float) -> float:
        """
        Generate deterministic mock depth for testing.

        Uses a deterministic formula based on coordinates to provide
        consistent depth values for testing without real bathymetry data.

        Parameters
        ----------
        lat : float
            Latitude coordinate.
        lon : float
            Longitude coordinate.

        Returns
        -------
        float
            Mock depth value.
        """
        val = (abs(lat) * 100) + (abs(lon) * 50)
        return -(val % 4000) - 100

    def close(self):
        """
        Close the NetCDF dataset if open.

        Should be called when the manager is no longer needed to free resources.
        """
        if self._dataset and self._dataset.isopen():
            self._dataset.close()


def download_bathymetry(target_dir: str = "data"):
    """
    Download ETOPO 2022 bathymetry dataset with progress bar.

    Downloads the ETOPO 2022 60-second resolution bathymetry data
    from NOAA servers. Tries multiple mirror URLs if the primary fails.

    Parameters
    ----------
    target_dir : str, optional
        Target directory relative to project root (default: "data").
        The file will be saved in a "bathymetry" subdirectory.
    """
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
