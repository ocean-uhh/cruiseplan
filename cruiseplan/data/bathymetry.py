"""
Bathymetry data download and management.

This module provides functionality for downloading, caching, and accessing
bathymetry data from ETOPO and GEBCO datasets for depth lookups.

When the file for the requested source is missing, too small or unreadable,
depth lookups return the fill value ``DEFAULT_DEPTH`` (-9999.0) and a warning
names the file and how to obtain it. No other source is substituted.
"""

import logging
import shutil
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

import netCDF4 as nc
import numpy as np
import requests
from tqdm import tqdm

from cruiseplan.config.values import DEFAULT_BATHY_DIR, DEFAULT_DEPTH

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

# GEBCO 2023 Constants
GEBCO_2023_NC_FILENAME = "GEBCO_2023.nc"

# MSM142 Bathymetry Constants
MSM142_JJ_NC_FILENAME = "MSM142_bathyJJ.nc"
MSM142_DT_NC_FILENAME = "MSM142_bathyDT.nc"
MSM142_LEGACY_NC_FILENAME = "msm142.nc"  # Legacy filename

# Constants from Spec
DEPTH_CONTOURS = [-5000, -4000, -3000, -2000, -1000, -750, -500, -200, -100, -50, 0]

# Source identifier -> (file name in the bathymetry directory, minimum size in MB).
# A file smaller than the minimum is treated as a partial download.
SOURCE_FILES: dict[str, tuple[str, float]] = {
    "etopo2022": (ETOPO_FILENAME, 450),  # ~491 MB
    "gebco2025": (GEBCO_NC_FILENAME, 6900),  # ~7.5 GB
    "gebco2023": (GEBCO_2023_NC_FILENAME, 6900),  # ~7.5 GB
    "msm142": (MSM142_LEGACY_NC_FILENAME, 2.0),  # ~2.8 MB
    "msm142_jj": (MSM142_JJ_NC_FILENAME, 0.1),  # ~167 KB regional grid
    "msm142_dt": (MSM142_DT_NC_FILENAME, 2.0),  # ~2.8 MB
}

# Sources that `cruiseplan bathymetry` can download; the others must be placed
# in the bathymetry directory by hand.
DOWNLOADABLE_SOURCES = ("etopo2022", "gebco2025")


def source_file(source: str) -> tuple[str, float]:
    """
    Return the expected file name and minimum size for a bathymetry source.

    Parameters
    ----------
    source : str
        Bathymetry source identifier (e.g. ``"gebco2025"``). An unknown
        identifier maps to ``"<source>.nc"`` with a 10 MB minimum.

    Returns
    -------
    tuple of (str, float)
        File name inside the bathymetry directory and minimum size in MB.
    """
    return SOURCE_FILES.get(source, (f"{source}.nc", 10))


def _how_to_get(source: str, data_dir: Path) -> str:
    """Return a one-line instruction for obtaining the file for ``source``."""
    if source in DOWNLOADABLE_SOURCES:
        return (
            f"Download it with: cruiseplan bathymetry --bathy-source {source} "
            f"--output-dir {data_dir}"
        )
    filename, _ = source_file(source)
    return f"This source is not downloadable; place {filename} in {data_dir}"


def _available_alternatives(exclude: str, data_dir: Path) -> list[str]:
    """Return known bathymetry sources other than ``exclude`` whose file is present."""
    alternatives = []
    for name in SOURCE_FILES:
        if name == exclude:
            continue
        try:
            if check_bathymetry_availability(name, str(data_dir)):
                alternatives.append(name)
        except OSError:
            # Probing the filesystem for a warning hint must never raise.
            continue
    return alternatives


class BathymetryManager:
    """
    Handles ETOPO bathymetry data with lazy loading and bilinear interpolation.

    Manages bathymetric data from ETOPO and GEBCO datasets, providing depth
    lookups and grid subsets for oceanographic applications. When the file for
    ``source`` is missing, too small or unreadable, depth lookups return
    ``DEFAULT_DEPTH`` and grid subsets are empty; a warning names the file.

    Attributes
    ----------
    source : str
        Bathymetry data source identifier.
    data_dir : Path
        Directory containing bathymetry data files.
    file_path : Path
        Expected path of the bathymetry file for ``source``.
    available : bool
        True when the bathymetry file was loaded.
    _dataset : Optional[nc.Dataset]
        NetCDF dataset object when loaded.
    _lats : Optional[np.ndarray]
        Latitude coordinate array.
    _lons : Optional[np.ndarray]
        Longitude coordinate array.
    """

    def __init__(
        self, source: str = "gebco2025", data_dir: str = "data/bathymetry"
    ) -> None:
        """
        Initialize the bathymetry manager.

        Parameters
        ----------
        source : str, optional
            Bathymetry data source (default: "gebco2025").
        data_dir : str, optional
            Data directory. Can be absolute path or relative to current working directory (default: "data/bathymetry").
        """
        self.source = source
        # Use the provided data_dir exactly as specified - no automatic modifications
        self.data_dir = Path(data_dir).resolve()

        self.file_path = self.data_dir / source_file(source)[0]
        self.available = False
        self._dataset = None
        self._lats = None
        self._lons = None
        self._lat_flipped = False
        self._lon_flipped = False
        self._depth_var_name = self._get_depth_variable_name()

        self._initialize_data()

    def _file_lat_idx(self, idx: int) -> int:
        """Map a cached (ascending) latitude index to the file's row index."""
        return len(self._lats) - 1 - idx if self._lat_flipped else idx

    def _file_lon_idx(self, idx: int) -> int:
        """Map a cached (ascending) longitude index to the file's column index."""
        return len(self._lons) - 1 - idx if self._lon_flipped else idx

    def _get_depth_variable_name(self) -> str:
        """
        Get the depth variable name for the current dataset.

        Returns
        -------
        str
            'z' for ETOPO, 'elevation' for GEBCO and MSM142
        """
        if self.source in [
            "gebco2025",
            "gebco2023",
            "msm142",
            "msm142_jj",
            "msm142_dt",
        ]:
            return "elevation"
        return "z"  # Default for ETOPO and other sources

    def _initialize_data(self) -> None:
        """Open the bathymetry file, or warn and leave the manager unavailable."""
        filename, min_size_mb = source_file(self.source)
        file_path = self.file_path = self.data_dir / filename
        self.available = False

        if not file_path.exists():
            # The download command constructs a manager before the file exists.
            import traceback

            stack = traceback.extract_stack()
            if not any("download" in frame.name.lower() for frame in stack[-10:]):
                self._warn_unavailable(f"No bathymetry file found at {file_path}")
            return

        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb < min_size_mb:
            self._warn_unavailable(
                f"Bathymetry file at {file_path} is too small "
                f"({file_size_mb:.1f} MB, expected at least {min_size_mb} MB)"
            )
            return

        try:
            # Load using netCDF4 for efficient lazy slicing
            self._dataset = nc.Dataset(file_path, "r")
            # Cache 1D coordinate arrays for fast search. np.searchsorted and the
            # bounds checks below require ascending coordinates; some grids
            # (e.g. hand-placed regional files) store latitude north-to-south, so
            # flip to ascending and remember it to map indices back to the file.
            lat_arr = self._dataset.variables["lat"][:]
            lon_arr = self._dataset.variables["lon"][:]
            self._lat_flipped = bool(np.size(lat_arr) > 1 and lat_arr[0] > lat_arr[-1])
            self._lon_flipped = bool(np.size(lon_arr) > 1 and lon_arr[0] > lon_arr[-1])
            self._lats = lat_arr[::-1] if self._lat_flipped else lat_arr
            self._lons = lon_arr[::-1] if self._lon_flipped else lon_arr
            self._depth_var_name = self._get_depth_variable_name()
            self.available = True
            logger.info(f"Loaded bathymetry from {file_path}")
        except (OSError, KeyError, RuntimeError) as e:
            self._warn_unavailable(f"Failed to read bathymetry file {file_path}: {e}")

    def _warn_unavailable(self, reason: str) -> None:
        """Log why depths will be the fill value and how to get the file."""
        hint = _how_to_get(self.source, self.data_dir)
        alternatives = _available_alternatives(self.source, self.data_dir)
        if alternatives:
            hint = (
                f"{', '.join(alternatives)} is available in {self.data_dir}; "
                f"use --bathy-source {alternatives[0]} to use it instead. {hint}"
            )
        logger.warning(
            f"{reason}. Depth lookups for '{self.source}' return the fill value "
            f"{DEFAULT_DEPTH}. {hint}"
        )

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
            Depth in meters (negative for below sea level), or
            ``DEFAULT_DEPTH`` when the file is unavailable or the point is
            outside the grid.
        """
        if not self.available:
            return DEFAULT_DEPTH

        try:
            return self._interpolate_depth(lat, lon)
        except Exception:
            logger.exception(f"Error interpolating depth at {lat}, {lon}")
            return DEFAULT_DEPTH

    def get_grid_subset(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        stride: int = 1,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
        tuple of numpy.ndarray
            (lons, lats, depths) as 2D arrays for contour plotting. All three
            are empty when the file is unavailable or the region is outside it.

        Notes
        -----
        This method performs expensive NetCDF grid slicing operations. Consider using
        cruiseplan.utils.cache.CacheManager for repeated grid subset requests with
        overlapping geographic bounds, especially in interactive applications like
        station_picker and map generation workflows.
        """
        if not self.available:
            return np.array([]), np.array([]), np.array([])

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

        # Select with stride on the cached (ascending) indices, then map to the
        # file's row/column order so a north-to-south grid reads correctly.
        lat_sel = np.arange(lat_idx_min, lat_idx_max, stride)
        lon_sel = np.arange(lon_idx_min, lon_idx_max, stride)
        lats = self._lats[lat_sel]
        lons = self._lons[lon_sel]

        # Read subset from disk (orthogonal indexing returns a lat x lon block)
        z = self._dataset.variables[self._depth_var_name][
            [self._file_lat_idx(i) for i in lat_sel],
            [self._file_lon_idx(i) for i in lon_sel],
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
            return DEFAULT_DEPTH
        if lon < self._lons[0] or lon > self._lons[-1]:
            return DEFAULT_DEPTH

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
            return DEFAULT_DEPTH

        # 3. Extract 2x2 Grid (Lazy Load from Disk)
        # Note: z(lat, lon) -> z(y, x). Cached indices are ascending; map them to
        # the file's row/column order (netCDF4 accepts decreasing index lists).
        z_grid = self._dataset.variables[self._depth_var_name][
            [self._file_lat_idx(y0_idx), self._file_lat_idx(y1_idx)],
            [self._file_lon_idx(x0_idx), self._file_lon_idx(x1_idx)],
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

    def ensure_gebco_2025(self, silent_if_exists: bool = False) -> bool:
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
        except OSError as e:
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
                    "Continue? (y/N): "
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
                zip_path.open("wb") as file,
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
                    nc_path.open("wb") as target,
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

        except requests.RequestException:
            logger.exception("❌ Download failed")
            if zip_path.exists():
                zip_path.unlink()
            return False
        except zipfile.BadZipFile:
            logger.exception("❌ Invalid zip file")
            if zip_path.exists():
                zip_path.unlink()
            return False
        except Exception:
            logger.exception("❌ Unexpected error")
            # Cleanup on failure
            for path in [zip_path, nc_path]:
                if path.exists():
                    path.unlink()
            return False

    def close(self) -> None:
        """
        Close the NetCDF dataset if open.

        Should be called when the manager is no longer needed to free resources.
        """
        if self._dataset and self._dataset.isopen():
            self._dataset.close()


def _check_local_bathy_file(target_dir: str, filename: str, label: str) -> str | bool:
    """Check whether a local-only bathymetry file exists and print its size.

    Returns the file path string if found, False otherwise.
    """
    output_dir = Path(target_dir).resolve()
    file_path = output_dir / filename
    if file_path.exists():
        file_size_kb = file_path.stat().st_size / 1024
        print(f"{label} bathymetry available at {file_path} ({file_size_kb:.1f} KB)")
        return str(file_path)
    print(f"ERROR: {label} bathymetry file not found at {file_path}")
    print(
        "   This is a local dataset that should be manually placed in the data/bathymetry directory."
    )
    return False


def _download_gebco2025(target_dir: str) -> str | bool:
    """Download GEBCO 2025 bathymetry, or return the existing file path if already present.

    Returns the file path on success, False if cancelled or download failed.
    """
    output_dir = Path(target_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    gebco_path = output_dir / GEBCO_NC_FILENAME

    if gebco_path.exists():
        file_size_gb = gebco_path.stat().st_size / (1024**3)
        if file_size_gb >= 6.9:
            print(f"File already exists at {gebco_path} ({file_size_gb:.1f} GB)")
            return str(gebco_path)
        print(f"Existing file at {gebco_path} is incomplete ({file_size_gb:.1f} GB)")
        try:
            response = (
                input("Delete incomplete file and redownload? (y/N): ").lower().strip()
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

    manager = BathymetryManager(source="gebco2025", data_dir=target_dir)
    if not manager.ensure_gebco_2025(silent_if_exists=True):
        print("ERROR: GEBCO 2025 download failed.")
        return False
    return str(gebco_path)


def _download_etopo2022(target_dir: str) -> str | bool | None:
    """Download ETOPO 2022 bathymetry.

    Returns the file path on success, the path string if incomplete and kept,
    False if cancelled, None if all download URLs failed.
    """
    output_dir = Path(target_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = output_dir / ETOPO_FILENAME

    if local_path.exists():
        file_size_mb = local_path.stat().st_size / (1024 * 1024)
        if file_size_mb >= 450:
            print(f"File already exists at {local_path} ({file_size_mb:.1f} MB)")
            return str(local_path)
        print(f"Existing file at {local_path} is incomplete ({file_size_mb:.1f} MB)")
        try:
            response = (
                input("Delete incomplete file and redownload? (y/N): ").lower().strip()
            )
            if response in ("y", "yes"):
                local_path.unlink()
                print("Deleted incomplete file. Starting download...")
            else:
                print("Keeping incomplete file. Download cancelled.")
                return str(local_path)
        except (EOFError, KeyboardInterrupt):
            print("Non-interactive environment. Keeping incomplete file.")
            return str(local_path)

    print(f"Downloading ETOPO dataset to {local_path}...")
    for url in ETOPO_URLS:
        try:
            print(f"Attempting download from: {url}")
            resp = requests.get(url, stream=True, timeout=10)
            resp.raise_for_status()
            total_size = int(resp.headers.get("Content-Length", 0))
            with (
                local_path.open("wb") as file,
                tqdm(
                    desc="Downloading ETOPO",
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar,
            ):
                for chunk in resp.iter_content(chunk_size=8192):
                    file.write(chunk)
                    bar.update(len(chunk))
            print("\nDownload complete!")
            return str(local_path)
        except Exception as e:  # noqa: BLE001 - download fallback: try the next URL
            print(f"Failed to download from {url}")
            print(f"   Error: {e}")
            if local_path.exists():
                local_path.unlink()

    print("\n" + "=" * 60)
    print("⛔ AUTOMATIC DOWNLOAD FAILED")
    print("=" * 60)
    print("Please download the file manually using your browser:")
    print(f"URL: {ETOPO_URLS[0]}")
    print(f"Save to: {local_path}")
    print("=" * 60 + "\n")
    return None


def download_bathymetry(
    target_dir: str = "data/bathymetry", source: str = "gebco2025"
) -> str | bool | None:
    """
    Download bathymetry dataset with progress bar.

    Downloads ETOPO 2022 (60 s resolution) or GEBCO 2025 (15 s resolution).
    For the local-only sources (``msm142``, ``msm142_jj``, ``msm142_dt``) the
    file is not downloaded; its presence is checked instead.

    Parameters
    ----------
    target_dir : str, optional
        Target directory for bathymetry files (default: "data/bathymetry").
        Files will be saved directly in this directory.
    source : str, optional
        Bathymetry source to download (default: "gebco2025").
        Options: "etopo2022", "gebco2025", "msm142", "msm142_jj", "msm142_dt".

    Returns
    -------
    str, bool, or None
        Returns file path (str) if successful or file exists, False if explicitly cancelled,
        None if download failed completely.

    Raises
    ------
    ValueError
        If ``source`` cannot be downloaded (for example ``"gebco2023"``, which
        has no download location here and must be placed by hand).
    """
    if source == "gebco2025":
        return _download_gebco2025(target_dir)
    if source == "etopo2022":
        return _download_etopo2022(target_dir)
    if source == "msm142":
        return _check_local_bathy_file(
            target_dir, MSM142_LEGACY_NC_FILENAME, "MSM142 (legacy)"
        )
    if source == "msm142_jj":
        return _check_local_bathy_file(target_dir, MSM142_JJ_NC_FILENAME, "MSM142_JJ")
    if source == "msm142_dt":
        return _check_local_bathy_file(target_dir, MSM142_DT_NC_FILENAME, "MSM142_DT")
    filename, _ = source_file(source)
    raise ValueError(
        f"Bathymetry source '{source}' cannot be downloaded by cruiseplan. "
        f"Downloadable sources: {', '.join(DOWNLOADABLE_SOURCES)}. "
        f"To use '{source}', place {filename} in {Path(target_dir).resolve()}."
    )


def check_bathymetry_availability(
    source: str, data_dir: str = DEFAULT_BATHY_DIR
) -> bool:
    """
    Check if the bathymetry file for the specified source is present and complete.

    Parameters
    ----------
    source : str
        Bathymetry source identifier (e.g. "etopo2022", "gebco2025").
    data_dir : str, optional
        Directory containing bathymetry files (default: "data/bathymetry").

    Returns
    -------
    bool
        True if the file exists and is at least the minimum expected size.
    """
    filename, min_size_mb = source_file(source)
    file_path = Path(data_dir) / filename
    if not file_path.is_file():
        return False
    return file_path.stat().st_size / (1024 * 1024) >= min_size_mb


# Managers shared within one pipeline call (see shared_bathymetry)
_shared_managers: ContextVar[dict[tuple[str, str], BathymetryManager] | None] = (
    ContextVar("_shared_managers", default=None)
)


@contextmanager
def shared_bathymetry() -> Iterator[None]:
    """
    Share one BathymetryManager per source and directory inside the block.

    ``get_bathymetry_manager`` calls inside the block return the same open
    manager, so a pipeline run opens each bathymetry file once and warns about
    a missing file once. Managers are closed when the block exits.

    Yields
    ------
    None
        Control returns to the caller with sharing active.
    """
    token = _shared_managers.set({})
    try:
        yield
    finally:
        managers = _shared_managers.get() or {}
        for manager in managers.values():
            manager.close()
        _shared_managers.reset(token)


def get_bathymetry_manager(
    source: str = "gebco2025", data_dir: str = DEFAULT_BATHY_DIR
) -> BathymetryManager:
    """
    Return a BathymetryManager, shared within a ``shared_bathymetry`` block.

    Parameters
    ----------
    source : str, optional
        Bathymetry source identifier (default: "gebco2025").
    data_dir : str, optional
        Directory containing bathymetry files (default: "data/bathymetry").

    Returns
    -------
    BathymetryManager
        A new manager, or the one already opened for the same source and
        directory inside the current ``shared_bathymetry`` block.
    """
    managers = _shared_managers.get()
    if managers is None:
        return BathymetryManager(source=source, data_dir=data_dir)
    key = (source, str(Path(data_dir).resolve()))
    if key not in managers:
        managers[key] = BathymetryManager(source=source, data_dir=data_dir)
    return managers[key]


# Lazy singleton instance - only created when first accessed
_bathymetry_instance: BathymetryManager | None = None


def get_bathymetry_singleton() -> BathymetryManager:
    """Get the singleton BathymetryManager instance (lazy initialization)."""
    global _bathymetry_instance
    if _bathymetry_instance is None:
        _bathymetry_instance = BathymetryManager()
    return _bathymetry_instance


# For backward compatibility, create the singleton on first access
def __getattr__(name: str) -> BathymetryManager:
    if name == "bathymetry":
        return get_bathymetry_singleton()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
