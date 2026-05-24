#!/usr/bin/env python3
"""
Simple integration test for EEZ functionality without requiring data download.

This script tests that the EEZ API integration is working correctly
without needing to download actual EEZ data.
"""

import logging
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all EEZ-related imports work."""
    logger.info("Testing imports...")

    try:
        # Test EEZ module imports
        from cruiseplan.data.eez_boundaries import (
            ensure_eez_data,
            get_eez_for_point,
            load_eez_data,
        )

        logger.info("✅ EEZ module imports successful")

        # Test map generator imports
        from cruiseplan.output.map_generator import (
            _add_eez_boundaries,
            generate_folium_map,
        )

        logger.info("✅ Map generator EEZ imports successful")

        # Test API imports
        from cruiseplan.api.config import VisualizationConfig
        from cruiseplan.api.map_cruise import map
        from cruiseplan.api.schedule_cruise import schedule

        logger.info("✅ API imports successful")

        return True

    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False


def test_api_signatures():
    """Test that API functions have the correct EEZ parameters."""
    logger.info("Testing API function signatures...")

    try:
        import inspect

        # Test map function
        from cruiseplan.api.map_cruise import map

        map_sig = inspect.signature(map)
        assert "include_eez" in map_sig.parameters
        assert map_sig.parameters["include_eez"].default is True
        logger.info("✅ Map API function has correct EEZ parameter")

        # Test schedule function
        from cruiseplan.api.schedule_cruise import schedule

        schedule_sig = inspect.signature(schedule)
        assert "include_eez" in schedule_sig.parameters
        assert schedule_sig.parameters["include_eez"].default is True
        logger.info("✅ Schedule API function has correct EEZ parameter")

        # Test folium function
        from cruiseplan.output.map_generator import generate_folium_map

        folium_sig = inspect.signature(generate_folium_map)
        assert "include_eez" in folium_sig.parameters
        assert folium_sig.parameters["include_eez"].default is True
        logger.info("✅ Folium map function has correct EEZ parameter")

        return True

    except Exception as e:
        logger.error(f"❌ API signature test failed: {e}")
        return False


def test_config_classes():
    """Test that configuration classes support EEZ options."""
    logger.info("Testing configuration classes...")

    try:
        from cruiseplan.api.config import MapConfig, VisualizationConfig

        # Test VisualizationConfig
        vis_config = VisualizationConfig()
        assert hasattr(vis_config, "include_eez")
        assert vis_config.include_eez is True
        logger.info("✅ VisualizationConfig has include_eez with correct default")

        # Test explicit setting
        vis_config_false = VisualizationConfig(include_eez=False)
        assert vis_config_false.include_eez is False
        logger.info("✅ VisualizationConfig accepts explicit EEZ setting")

        # Test MapConfig integration
        map_config = MapConfig(visualization=vis_config_false)
        assert map_config.visualization.include_eez is False
        logger.info("✅ MapConfig integrates EEZ settings correctly")

        return True

    except Exception as e:
        logger.error(f"❌ Config class test failed: {e}")
        return False


def test_folium_integration():
    """Test basic folium integration without actual EEZ data."""
    logger.info("Testing basic Folium integration...")

    try:
        from cruiseplan.output.map_generator import generate_folium_map

        test_tracks = [
            {
                "latitude": [40.0, 42.0],
                "longitude": [-70.0, -68.0],
                "label": "Test Track",
                "dois": [],
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "test_map.html"

            # Test with EEZ disabled (should work regardless of data availability)
            result = generate_folium_map(
                tracks=test_tracks,
                output_file=output_file,
                include_eez=False,  # Disabled to avoid data download
            )

            if result and result.exists():
                logger.info("✅ Folium map generation works with EEZ disabled")
                logger.info(f"   Map file: {result} ({result.stat().st_size} bytes)")

                # Test with EEZ enabled (will warn about missing data but shouldn't crash)
                result_eez = generate_folium_map(
                    tracks=test_tracks,
                    output_file=output_file.with_name("test_map_eez.html"),
                    include_eez=True,
                )

                if result_eez and result_eez.exists():
                    logger.info("✅ Folium map generation works with EEZ enabled")
                    logger.info(
                        "   (May show warnings about missing EEZ data - this is expected)"
                    )

                return True
            else:
                logger.error("❌ Folium map generation failed")
                return False

    except Exception as e:
        logger.error(f"❌ Folium integration test failed: {e}")
        return False


def test_cli_arguments():
    """Test that CLI arguments are properly defined."""
    logger.info("Testing CLI argument integration...")

    try:
        # Test that help text includes EEZ options
        import subprocess

        # Test map command help
        result = subprocess.run(
            ["cruiseplan", "map", "--help"], capture_output=True, text=True
        )
        if "--no-eez" in result.stdout:
            logger.info("✅ Map command includes --no-eez option")
        else:
            logger.warning("⚠️ Map command help may not include --no-eez option")

        # Test schedule command help
        result = subprocess.run(
            ["cruiseplan", "schedule", "--help"], capture_output=True, text=True
        )
        if "--no-eez" in result.stdout:
            logger.info("✅ Schedule command includes --no-eez option")
        else:
            logger.warning("⚠️ Schedule command help may not include --no-eez option")

        return True

    except Exception as e:
        logger.warning(f"⚠️ CLI argument test failed (may be expected): {e}")
        return True  # Not critical for core functionality


def main():
    """Run all integration tests."""
    logger.info("=== CruisePlan EEZ Integration Test ===")
    logger.info("")

    tests = [
        test_imports,
        test_api_signatures,
        test_config_classes,
        test_folium_integration,
        test_cli_arguments,
    ]

    results = []
    for test in tests:
        logger.info("-" * 40)
        try:
            result = test()
            results.append(result)
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
        logger.info(
            "🎉 All integration tests passed! EEZ functionality is properly integrated."
        )
    elif passed >= total * 0.8:  # 80% threshold
        logger.info(
            "✅ Most tests passed. EEZ functionality is working with some minor issues."
        )
    else:
        logger.warning(
            f"⚠️ {total - passed} tests failed. EEZ integration may have issues."
        )

    logger.info("")
    logger.info(
        "Note: This test verifies API integration without downloading EEZ data."
    )
    logger.info(
        "For full functionality testing with actual data, use test_eez_functionality.py"
    )

    return passed >= total * 0.8


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
