"""
EEZ Boundary Data Management.

Handles downloading, caching, and processing of Exclusive Economic Zone (EEZ)
boundary data for marine research cruise planning and visualization.

Notes
-----
Uses Marine Regions (marineregions.org) EEZ v12 dataset as the authoritative
source for global EEZ boundaries. Data is cached locally to minimize repeated
downloads.
"""

import logging
import zipfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.request import urlretrieve

import geopandas as gpd
from shapely.geometry import Point, Polygon

logger = logging.getLogger(__name__)

# Marine Regions EEZ v12 (2023) - Global EEZ boundaries
# Alternative URLs for EEZ data (in case main site is down)
EEZ_DOWNLOAD_URLS = [
    "https://github.com/nvkelso/natural-earth-vector/raw/master/packages/natural_earth_vector.gpkg.zip",  # Natural Earth backup
    "https://www.marineregions.org/download_file.php?name=World_EEZ_v12_20231025_gpkg.zip",  # Original URL
]
EEZ_CACHE_DIR = Path.home() / ".cruiseplan" / "eez_data"
EEZ_FILENAME = "eez_boundaries.gpkg"


def ensure_eez_data() -> Path:
    """
    Ensure EEZ boundary data is available locally.

    Downloads and caches Marine Regions EEZ v12 dataset if not already present.
    Creates cache directory structure as needed.

    Returns
    -------
    Path
        Path to the local EEZ GeoPackage file.

    Raises
    ------
    FileNotFoundError
        If download fails or extracted file is not found.
    """
    # Create cache directory
    EEZ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    eez_file_path = EEZ_CACHE_DIR / EEZ_FILENAME

    if eez_file_path.exists():
        logger.debug(f"EEZ data found at: {eez_file_path}")
        return eez_file_path

    logger.info("Downloading EEZ boundary data from Marine Regions...")
    zip_path = EEZ_CACHE_DIR / "eez_data.zip"

    try:
        # Try each download URL until one works
        for url in EEZ_DOWNLOAD_URLS:
            try:
                logger.info(f"Attempting download from: {url}")
                urlretrieve(url, zip_path)
                break
            except Exception as e:
                logger.warning(f"Download failed from {url}: {e}")
                continue
        else:
            raise FileNotFoundError("All EEZ download URLs failed")
        logger.info(f"Downloaded EEZ data to: {zip_path}")

        # Extract the GeoPackage file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Look for .gpkg file in the zip
            gpkg_files = [name for name in zip_ref.namelist() if name.endswith(".gpkg")]
            if not gpkg_files:
                raise FileNotFoundError(
                    "No GeoPackage (.gpkg) file found in downloaded EEZ data"
                )

            # Extract the first .gpkg file found
            gpkg_name = gpkg_files[0]
            zip_ref.extract(gpkg_name, EEZ_CACHE_DIR)

            # Rename to our standard filename
            extracted_path = EEZ_CACHE_DIR / gpkg_name
            extracted_path.rename(eez_file_path)

        # Clean up zip file
        zip_path.unlink()
        logger.info(f"EEZ data extracted to: {eez_file_path}")

    except Exception as e:
        logger.error(f"Failed to download or extract EEZ data: {e}")
        # Clean up partial files
        if zip_path.exists():
            zip_path.unlink()
        raise

    return eez_file_path


def _extract_and_validate_eez_data(zip_path: Path, eez_file_path: Path) -> bool:
    """
    Extract GeoPackage from zip and validate it contains expected EEZ schema.

    Parameters
    ----------
    zip_path : Path
        Path to the downloaded zip file
    eez_file_path : Path
        Target path for the validated EEZ GeoPackage

    Returns
    -------
    bool
        True if extraction and validation succeeded, False otherwise
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Look for .gpkg files in the zip
            gpkg_files = [name for name in zip_ref.namelist() if name.endswith(".gpkg")]
            if not gpkg_files:
                logger.warning("No GeoPackage (.gpkg) file found in downloaded zip")
                return False

            # Try each GeoPackage file until we find one with valid EEZ data
            for gpkg_name in gpkg_files:
                try:
                    # Extract to temporary location for validation
                    temp_path = eez_file_path.parent / f"temp_{gpkg_name}"
                    zip_ref.extract(gpkg_name, eez_file_path.parent)
                    extracted_path = eez_file_path.parent / gpkg_name
                    extracted_path.rename(temp_path)

                    # Validate the GeoPackage contains expected EEZ schema
                    if _validate_eez_schema(temp_path):
                        # Valid EEZ data found - move to final location
                        temp_path.rename(eez_file_path)
                        logger.info(f"Successfully validated EEZ data from {gpkg_name}")
                        return True
                    else:
                        # Invalid schema - clean up and try next file
                        logger.warning(
                            f"GeoPackage {gpkg_name} does not contain valid EEZ schema"
                        )
                        temp_path.unlink(missing_ok=True)

                except Exception as e:
                    logger.warning(f"Failed to process {gpkg_name}: {e}")
                    continue

            logger.error("No valid EEZ GeoPackage found in zip file")
            return False

    except Exception as e:
        logger.error(f"Failed to extract GeoPackage: {e}")
        return False


def _validate_eez_schema(gpkg_path: Path) -> bool:
    """
    Validate that a GeoPackage contains expected EEZ fields and data.

    Parameters
    ----------
    gpkg_path : Path
        Path to the GeoPackage file to validate

    Returns
    -------
    bool
        True if the GeoPackage contains valid EEZ data with expected schema
    """
    try:
        import geopandas as gpd

        # Try to read the GeoPackage
        gdf = gpd.read_file(gpkg_path)

        # Check if it has the expected EEZ fields
        missing_fields = [
            field for field in EXPECTED_EEZ_FIELDS if field not in gdf.columns
        ]
        if missing_fields:
            logger.warning(f"GeoPackage missing expected EEZ fields: {missing_fields}")
            return False

        # Check if it has geometry data
        if gdf.empty or gdf.geometry.isna().all():
            logger.warning("GeoPackage contains no valid geometry data")
            return False

        # Basic sanity check - should have reasonable number of EEZ zones
        if len(gdf) < 100:  # Real EEZ data should have 200+ zones globally
            logger.warning(
                f"GeoPackage contains suspiciously few EEZ zones: {len(gdf)}"
            )
            return False

        logger.debug(
            f"EEZ validation successful: {len(gdf)} zones, expected fields present"
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to validate EEZ schema: {e}")
        return False


def load_eez_data(
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> gpd.GeoDataFrame:
    """
    Load EEZ boundary data as a GeoDataFrame.

    Parameters
    ----------
    bbox : tuple of float, optional
        Bounding box to filter EEZ data (min_lon, min_lat, max_lon, max_lat).
        If None, loads global EEZ dataset. Spatial filtering is applied at
        read-time for optimal performance.

    Returns
    -------
    geopandas.GeoDataFrame
        EEZ boundaries with country information and geometry.

    Notes
    -----
    For large study areas, the full global dataset is used. For smaller regions,
    provide a bounding box to improve performance.
    """
    eez_file = ensure_eez_data()

    logger.debug(f"Loading EEZ data from: {eez_file}")

    # Load the full dataset first
    eez_gdf = gpd.read_file(eez_file)

    # Filter by bounding box if provided
    if bbox is not None:
        min_lon, min_lat, max_lon, max_lat = bbox
        bbox_polygon = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
                (min_lon, min_lat),
            ]
        )

        # Filter EEZ boundaries that intersect with the bounding box
        eez_gdf = eez_gdf[eez_gdf.geometry.intersects(bbox_polygon)]
        logger.debug(f"Filtered to {len(eez_gdf)} EEZ zones in bounding box")

    return eez_gdf


def get_eez_for_point(lat: float, lon: float) -> Optional[dict]:
    """
    Determine which EEZ contains a given point.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees.
    lon : float
        Longitude in decimal degrees.

    Returns
    -------
    dict or None
        Dictionary with EEZ information (country, zone name, etc.) if point
        is within an EEZ, None if in international waters.

    Notes
    -----
    For single point queries, this function loads only EEZ zones near the
    point to optimize performance.
    """
    # Create a small bounding box around the point for efficient loading
    buffer = 1.0  # degrees
    bbox = (lon - buffer, lat - buffer, lon + buffer, lat + buffer)

    eez_gdf = load_eez_data(bbox=bbox)

    if eez_gdf.empty:
        return None

    # Create point geometry
    point = Point(lon, lat)

    # Find EEZ containing the point
    containing_eez = eez_gdf[eez_gdf.geometry.contains(point)]

    if containing_eez.empty:
        return None

    # Return information about the first matching EEZ
    eez_info = containing_eez.iloc[0]
    return {
        "country": eez_info.get("SOVEREIGN1", "Unknown"),
        "eez_name": eez_info.get("GEONAME", "Unknown"),
        "area_km2": eez_info.get("AREA_KM2", 0),
        "iso_code": eez_info.get("ISO_SOV1", "Unknown"),
    }


def get_cruise_area_bbox(cruise) -> Tuple[float, float, float, float]:
    """
    Calculate bounding box for cruise area based on all station positions.

    Parameters
    ----------
    cruise : Cruise
        Cruise object with station registry.

    Returns
    -------
    tuple of float
        Bounding box (min_lon, min_lat, max_lon, max_lat) with 5% padding.
    """
    from cruiseplan.output.map_generator import extract_points_from_cruise

    points = extract_points_from_cruise(cruise, include_ports=True)

    if not points:
        # Default to global bounds if no points
        return (-180, -90, 180, 90)

    lats = [p["lat"] for p in points if p["lat"] is not None]
    lons = [p["lon"] for p in points if p["lon"] is not None]

    if not lats or not lons:
        return (-180, -90, 180, 90)

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # Add 5% padding
    lat_padding = (max_lat - min_lat) * 0.05
    lon_padding = (max_lon - min_lon) * 0.05

    return (
        min_lon - lon_padding,
        min_lat - lat_padding,
        max_lon + lon_padding,
        max_lat + lat_padding,
    )
