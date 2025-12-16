# cruiseplan/data/bathymetry.py
import logging
import shutil
import zipfile
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

# GEBCO 2025 Constants
GEBCO_URL = "https://data.ceda.ac.uk/bodc/gebco/global/gebco_2025/ice_surface_elevation/netcdf/gebco_2025.zip"
GEBCO_ZIP_FILENAME = "gebco_2025.zip"
GEBCO_NC_FILENAME = "GEBCO_2025.nc"

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
        self._depth_var_name = self._get_depth_variable_name()

        self._initialize_data()

    def _get_depth_variable_name(self) -> str:
        """
        Get the depth variable name for the current dataset.

        Returns
        -------
        str
            'z' for ETOPO, 'elevation' for GEBCO
        """
        if self.source == "gebco2025":
            return "elevation"
        else:
            return "z"  # Default for ETOPO and other sources

    def _initialize_data(self):
        """
        Attempt to load NetCDF data, falling back to mock mode on failure.

        Tries to load the specified bathymetry dataset. If the file doesn't
        exist, is too small (corrupted/partial), or cannot be loaded, switches
        to mock mode for testing. Offers user option to redownload corrupt files.
        """
        # Map source name to actual filename and expected size
        if self.source == "etopo2022":
            filename = ETOPO_FILENAME
            min_size_mb = 450  # ETOPO is ~491 MB
        elif self.source == "gebco2025":
            filename = GEBCO_NC_FILENAME
            min_size_mb = 6900  # GEBCO is ~7.5 GB, use 6.9GB threshold
        else:
            filename = f"{self.source}.nc"
            min_size_mb = 10  # Generic minimum for custom sources

        file_path = self.data_dir / filename

        if file_path.exists():
            # Check file size based on source type
            file_size_mb = file_path.stat().st_size / (1024 * 1024)

            if file_size_mb < min_size_mb:
                logger.warning(
                    f"⚠️ Bathymetry file at {file_path} is too small ({file_size_mb:.1f} MB). "
                    f"Expected at least {min_size_mb} MB. Using MOCK mode. Run 'cruiseplan download' to fix."
                )
                self._is_mock = True
                return

            try:
                # Load using netCDF4 for efficient lazy slicing
                self._dataset = nc.Dataset(file_path, "r")
                # Cache coordinate arrays for fast search
                # (These are 1D arrays, so they fit easily in memory)
                self._lats = self._dataset.variables["lat"][:]
                self._lons = self._dataset.variables["lon"][:]
                # Determine depth variable name based on source
                self._depth_var_name = self._get_depth_variable_name()
                self._is_mock = False
                logger.info(f"✅ Loaded bathymetry from {file_path}")
            except Exception as e:
                logger.warning(
                    f"❌ Failed to load bathymetry file: {e}. Using MOCK mode. Run 'cruiseplan download' to fix."
                )
                self._is_mock = True
        else:
            # Don't log about mock mode if we're in a download context
            # (the download function will handle this better)
            import traceback

            stack = traceback.extract_stack()
            is_download_context = any(
                "download" in frame.name.lower() for frame in stack[-10:]
            )

            if not is_download_context:
                logger.info(
                    f"⚠️ No bathymetry file found at {file_path}. Using MOCK mode."
                )
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
        z = self._dataset.variables[self._depth_var_name][
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
        z_grid = self._dataset.variables[self._depth_var_name][
            [y0_idx, y1_idx], [x0_idx, x1_idx]
        ]
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

    def ensure_gebco_2025(self, silent_if_exists=False):
        """
        Ensure GEBCO 2025 dataset is available for high-resolution bathymetry.

        Downloads and extracts GEBCO 2025 data if not present or corrupted.
        The full dataset is ~7.5GB uncompressed, downloaded as ~4GB zip.

        Parameters
        ----------
        silent_if_exists : bool, optional
            If True, don't log when file already exists (default: False).

        Returns
        -------
        bool
            True if GEBCO 2025 is available, False if download failed or cancelled.
        """
        gebco_nc_path = self.data_dir / GEBCO_NC_FILENAME

        # Check if file exists and has correct size (~7.5GB)
        if gebco_nc_path.exists():
            file_size_gb = gebco_nc_path.stat().st_size / (1024**3)
            if (
                file_size_gb >= 6.9
            ):  # 6.9GB threshold (allows for slight compression differences)
                if not silent_if_exists:
                    logger.info(
                        f"✅ GEBCO 2025 already available at {gebco_nc_path} ({file_size_gb:.1f} GB)"
                    )
                return True
            else:
                logger.warning(
                    f"⚠️ GEBCO 2025 file is incomplete ({file_size_gb:.1f} GB). Re-downloading..."
                )
                gebco_nc_path.unlink()

        # Check disk space (need ~12GB: 4GB zip + 7.5GB extracted + buffer)
        try:
            free_space_gb = shutil.disk_usage(self.data_dir).free / (1024**3)
            if free_space_gb < 12:
                logger.error(
                    f"❌ Insufficient disk space. Need ~12GB, have {free_space_gb:.1f}GB free."
                )
                return False
        except Exception as e:
            logger.warning(f"⚠️ Could not check disk space: {e}")

        # User confirmation for large download
        # Check if running in test environment
        import sys

        if "pytest" in sys.modules or "unittest" in sys.modules:
            logger.info("Test environment detected. Skipping GEBCO download.")
            return False

        try:
            response = (
                input(
                    "\nDownload GEBCO 2025 high-resolution bathymetry?\n"
                    "  • Size: ~4GB download, ~7.5GB extracted\n"
                    "  • Time: May take 10-30 minutes depending on connection\n"
                    "  • Space: Requires ~12GB free disk space\n"
                    "Continue? (y/n): "
                )
                .lower()
                .strip()
            )

            if response not in ("y", "yes"):
                logger.info("Download cancelled by user.")
                return False
        except (EOFError, KeyboardInterrupt):
            logger.info("Download cancelled.")
            return False

        # Download and extract
        success = self._download_and_extract_gebco()
        if success:
            print("✅ GEBCO 2025 download completed successfully.")
        return success

    def _download_and_extract_gebco(self) -> bool:
        """
        Download GEBCO 2025 zip file and extract the NetCDF.

        Returns
        -------
        bool
            True if successful, False otherwise.
        """
        self.data_dir.mkdir(parents=True, exist_ok=True)
        zip_path = self.data_dir / GEBCO_ZIP_FILENAME
        nc_path = self.data_dir / GEBCO_NC_FILENAME

        try:
            # Download zip file
            logger.info(f"Downloading GEBCO 2025 from {GEBCO_URL}...")
            response = requests.get(GEBCO_URL, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))

            with (
                open(zip_path, "wb") as file,
                tqdm(
                    desc="Downloading GEBCO 2025",
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar,
            ):
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
                    bar.update(len(chunk))

            logger.info("✅ Download complete. Extracting...")

            # Extract NetCDF from zip
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Find the .nc file in the zip
                nc_files = [name for name in zip_ref.namelist() if name.endswith(".nc")]
                if not nc_files:
                    logger.error("❌ No NetCDF file found in GEBCO zip archive.")
                    return False

                # Extract the first .nc file found (with path validation)
                nc_file_in_zip = nc_files[0]

                # Validate filename to prevent path traversal attacks
                nc_filename = Path(
                    nc_file_in_zip
                ).name  # Only get filename, no path components
                if nc_filename != nc_file_in_zip:
                    logger.warning(
                        f"⚠️ Suspicious filename in zip: {nc_file_in_zip}. Expected flat structure."
                    )
                    return False

                logger.info(f"Extracting {nc_file_in_zip}...")

                # Extract with progress (for large files)
                with (
                    zip_ref.open(nc_file_in_zip) as source,
                    open(nc_path, "wb") as target,
                ):
                    shutil.copyfileobj(source, target)

            # Cleanup: remove zip file to save space
            zip_path.unlink()
            logger.info(f"✅ GEBCO 2025 ready at {nc_path}")

            # Verify extracted file size
            file_size_gb = nc_path.stat().st_size / (1024**3)
            if file_size_gb < 6.9:
                logger.warning(
                    f"⚠️ Extracted file seems small ({file_size_gb:.1f} GB). May be corrupted."
                )
                return False

            logger.info(f"✅ GEBCO 2025 extraction complete ({file_size_gb:.1f} GB)")
            return True

        except requests.RequestException as e:
            logger.error(f"❌ Download failed: {e}")
            if zip_path.exists():
                zip_path.unlink()
            return False
        except zipfile.BadZipFile as e:
            logger.error(f"❌ Invalid zip file: {e}")
            if zip_path.exists():
                zip_path.unlink()
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            # Cleanup on failure
            for path in [zip_path, nc_path]:
                if path.exists():
                    path.unlink()
            return False

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


def download_bathymetry(target_dir: str = "data", source: str = "etopo2022"):
    """
    Download bathymetry dataset with progress bar.

    Downloads either ETOPO 2022 (60s resolution) or GEBCO 2025 (15s resolution)
    bathymetry data based on the source parameter.

    Parameters
    ----------
    target_dir : str, optional
        Target directory relative to project root (default: "data").
        The file will be saved in a "bathymetry" subdirectory.
    source : str, optional
        Bathymetry source to download (default: "etopo2022").
        Options: "etopo2022", "gebco2025".

    Returns
    -------
    bool or None
        For GEBCO 2025: True if download/file check was successful, False if failed or cancelled.
        For ETOPO 2022: Returns None (legacy behavior).
    """
    if source == "gebco2025":
        # Handle GEBCO 2025 download
        root = Path(__file__).parent.parent.parent
        output_dir = root / target_dir / "bathymetry"
        output_dir.mkdir(parents=True, exist_ok=True)

        gebco_path = output_dir / GEBCO_NC_FILENAME

        # Check if file already exists and is complete
        if gebco_path.exists():
            file_size_gb = gebco_path.stat().st_size / (1024**3)
            if file_size_gb >= 6.9:  # 6.9GB threshold for ~7.5GB file
                print(f"File already exists at {gebco_path} ({file_size_gb:.1f} GB)")
                return True
            else:
                print(
                    f"Existing file at {gebco_path} is incomplete ({file_size_gb:.1f} GB)"
                )
                try:
                    response = (
                        input("Delete incomplete file and redownload? (y/n): ")
                        .lower()
                        .strip()
                    )
                    if response in ("y", "yes"):
                        gebco_path.unlink()
                        print("Deleted incomplete file. Starting download...")
                    else:
                        print("Keeping incomplete file. Download cancelled.")
                        return False
                except (EOFError, KeyboardInterrupt):
                    print("Non-interactive environment. Keeping incomplete file.")
                    return False

        # File doesn't exist or is incomplete, need to download
        # Use a fresh BathymetryManager instance for downloading
        # Pass only the directory relative to the project root (e.g., "data") as data_dir.
        # BathymetryManager will append "/bathymetry" itself.
        manager = BathymetryManager(source="gebco2025", data_dir=target_dir)
        success = manager.ensure_gebco_2025(silent_if_exists=True)
        if not success:
            print("❌ GEBCO 2025 download failed.")
        return success

    # Handle ETOPO 2022 download (existing logic)
    root = Path(__file__).parent.parent.parent
    output_dir = root / target_dir / "bathymetry"
    output_dir.mkdir(parents=True, exist_ok=True)

    local_path = output_dir / ETOPO_FILENAME

    if local_path.exists():
        # Check if existing file is complete (actual file is ~491 MB)
        file_size_mb = local_path.stat().st_size / (1024 * 1024)
        if file_size_mb >= 450:
            print(f"File already exists at {local_path} ({file_size_mb:.1f} MB)")
            return
        else:
            print(
                f"Existing file at {local_path} is incomplete ({file_size_mb:.1f} MB)"
            )
            try:
                response = (
                    input("Delete incomplete file and redownload? (y/n): ")
                    .lower()
                    .strip()
                )
                if response in ("y", "yes"):
                    local_path.unlink()
                    print("Deleted incomplete file. Starting download...")
                else:
                    print("Keeping incomplete file. Download cancelled.")
                    return
            except (EOFError, KeyboardInterrupt):
                print("Non-interactive environment. Keeping incomplete file.")
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


# Lazy singleton instance - only created when first accessed
_bathymetry_instance = None


def get_bathymetry_singleton():
    """Get the singleton BathymetryManager instance (lazy initialization)."""
    global _bathymetry_instance
    if _bathymetry_instance is None:
        _bathymetry_instance = BathymetryManager()
    return _bathymetry_instance


# For backward compatibility, create the singleton on first access
def __getattr__(name):
    if name == "bathymetry":
        return get_bathymetry_singleton()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
