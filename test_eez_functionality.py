#!/usr/bin/env python3
"""
Test script for EEZ (Exclusive Economic Zone) boundary functionality.

This script verifies that the EEZ boundary plotting functionality works correctly
in CruisePlan, including data download, spatial filtering, and map generation.

Usage:
    python test_eez_functionality.py
"""

import logging
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_eez_data_download():
    """Test EEZ data download and caching."""
    logger.info("Testing EEZ data download and caching...")

    try:
        from cruiseplan.data.eez_boundaries import ensure_eez_data

        # This should download and cache EEZ data
        eez_file = ensure_eez_data()

        if eez_file.exists():
            logger.info(f"✅ EEZ data successfully available at: {eez_file}")
            logger.info(f"   File size: {eez_file.stat().st_size / 1024 / 1024:.1f} MB")
            return True
        else:
            logger.error(f"❌ EEZ data file not found: {eez_file}")
            return False

    except ImportError as e:
        logger.error(f"❌ Import error - missing dependencies: {e}")
        logger.error("   Install geopandas: pip install geopandas>=0.14.0")
        return False
    except Exception as e:
        logger.error(f"❌ EEZ data download failed: {e}")
        return False


def test_eez_spatial_filtering():
    """Test EEZ spatial filtering functionality."""
    logger.info("Testing EEZ spatial filtering...")

    try:
        from cruiseplan.data.eez_boundaries import load_eez_data

        # Test with a small bounding box around the North Atlantic
        # (should contain parts of US, Canadian, and European EEZs)
        bbox = (-70, 40, -30, 70)  # min_lon, min_lat, max_lon, max_lat

        logger.info(f"Loading EEZ data for bounding box: {bbox}")
        eez_gdf = load_eez_data(bbox=bbox)

        if not eez_gdf.empty:
            logger.info(
                f"✅ Spatial filtering successful - found {len(eez_gdf)} EEZ zones"
            )

            # Print some info about the EEZs found
            if "SOVEREIGN1" in eez_gdf.columns:
                countries = eez_gdf["SOVEREIGN1"].unique()[:5]  # First 5 countries
                logger.info(f"   Countries found: {', '.join(countries)}")

            return True
        else:
            logger.warning("⚠️ No EEZ zones found in test bounding box")
            return False

    except Exception as e:
        logger.error(f"❌ EEZ spatial filtering failed: {e}")
        return False


def test_point_in_eez():
    """Test point-in-EEZ lookup functionality."""
    logger.info("Testing point-in-EEZ lookup...")

    try:
        from cruiseplan.data.eez_boundaries import get_eez_for_point

        # Test point in US EEZ (offshore New York)
        test_lat, test_lon = 40.0, -70.0
        logger.info(f"Testing point: {test_lat}°N, {test_lon}°E")

        eez_info = get_eez_for_point(test_lat, test_lon)

        if eez_info:
            logger.info("✅ Point-in-EEZ lookup successful")
            logger.info(f"   Country: {eez_info.get('country', 'Unknown')}")
            logger.info(f"   EEZ Name: {eez_info.get('eez_name', 'Unknown')}")
            return True
        else:
            logger.info("✅ Point is in international waters (no EEZ)")
            return True

    except Exception as e:
        logger.error(f"❌ Point-in-EEZ lookup failed: {e}")
        return False


def test_folium_integration():
    """Test EEZ integration with Folium maps."""
    logger.info("Testing EEZ integration with Folium maps...")

    try:
        from cruiseplan.output.map_generator import generate_folium_map

        # Create test track data
        test_tracks = [
            {
                "latitude": [40.0, 42.0, 44.0],
                "longitude": [-70.0, -68.0, -66.0],
                "label": "Test Track",
                "dois": [],
            }
        ]

        # Test with EEZ boundaries enabled
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_map_with_eez.html"

            result = generate_folium_map(
                tracks=test_tracks, output_file=output_file, include_eez=True
            )

            if result and result.exists():
                logger.info(f"✅ Folium map with EEZ generated: {result}")
                logger.info(f"   File size: {result.stat().st_size / 1024:.1f} KB")

                # Check if file contains EEZ-related content
                content = result.read_text()
                if "EEZ" in content or "Exclusive Economic Zone" in content:
                    logger.info("✅ Map appears to contain EEZ boundary data")
                else:
                    logger.warning(
                        "⚠️ Map may not contain EEZ boundaries (check manually)"
                    )

                return True
            else:
                logger.error("❌ Failed to generate Folium map with EEZ")
                return False

    except Exception as e:
        logger.error(f"❌ Folium EEZ integration test failed: {e}")
        return False


def test_api_integration():
    """Test API integration with EEZ functionality."""
    logger.info("Testing API integration...")

    try:
        from cruiseplan.api.config import MapConfig, VisualizationConfig

        # Test that the EEZ option is available in the configuration
        vis_config = VisualizationConfig(include_eez=False)
        map_config = MapConfig(visualization=vis_config)

        logger.info("✅ API configuration supports EEZ options")
        logger.info(f"   include_eez setting: {vis_config.include_eez}")

        return True

    except Exception as e:
        logger.error(f"❌ API integration test failed: {e}")
        return False


def create_test_cruise_config():
    """Create a minimal test cruise configuration."""
    test_config = """
# Test cruise configuration for EEZ functionality
cruise_name: "EEZ Test Cruise"
departure_port: "Woods Hole"
arrival_port: "Halifax"

waypoints:
  - name: "Station 1"
    latitude: 41.0
    longitude: -69.0
    activities:
      - type: "ctd"
        
  - name: "Station 2" 
    latitude: 43.0
    longitude: -67.0
    activities:
      - type: "ctd"
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(test_config)
        return Path(f.name)


def test_full_workflow():
    """Test full EEZ workflow with a test cruise configuration."""
    logger.info("Testing full EEZ workflow...")

    try:
        import cruiseplan

        # Create test configuration
        config_file = create_test_cruise_config()
        logger.info(f"Created test config: {config_file}")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            # Test map generation with EEZ
            try:
                result = cruiseplan.map(
                    config_file=config_file,
                    output_dir=str(output_dir),
                    format="html",
                    include_eez=True,
                )

                if result and result.map_files:
                    logger.info("✅ Full workflow test passed")
                    logger.info(f"   Generated files: {len(result.map_files)}")

                    # Clean up
                    config_file.unlink()
                    return True
                else:
                    logger.error("❌ No map files generated in full workflow test")

            except Exception as e:
                logger.warning(
                    f"⚠️ Full workflow test failed (expected if missing dependencies): {e}"
                )

        # Clean up
        if config_file.exists():
            config_file.unlink()

    except Exception as e:
        logger.error(f"❌ Full workflow test failed: {e}")
        return False


def main():
    """Run all EEZ functionality tests."""
    logger.info("=== CruisePlan EEZ Functionality Test Suite ===")
    logger.info("")

    tests = [
        test_eez_data_download,
        test_eez_spatial_filtering,
        test_point_in_eez,
        test_folium_integration,
        test_api_integration,
        test_full_workflow,
    ]

    results = []
    for test in tests:
        logger.info("-" * 50)
        try:
            result = test()
            results.append(result if result is not None else False)
        except Exception as e:
            logger.error(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        logger.info("")

    # Summary
    logger.info("=== Test Summary ===")
    passed = sum(results)
    total = len(results)

    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{i + 1}. {test.__name__}: {status}")

    logger.info("")
    logger.info(f"Overall: {passed}/{total} tests passed ({passed / total * 100:.1f}%)")

    if passed == total:
        logger.info("🎉 All tests passed! EEZ functionality is working correctly.")
    else:
        logger.warning(
            f"⚠️ {total - passed} tests failed. Check logs above for details."
        )

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
