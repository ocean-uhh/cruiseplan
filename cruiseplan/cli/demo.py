import logging

from cruiseplan.data.bathymetry import bathymetry
from cruiseplan.data.pangaea import PangaeaManager
from cruiseplan.interactive.station_picker import StationPicker

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


def main():
    """
    Interactive demonstration of CruisePlan functionality.

    Provides a guided demo that:
    1. Tests bathymetry data access
    2. Demonstrates PANGAEA data fetching
    3. Launches the interactive station picker UI

    This function is primarily for testing and demonstration purposes,
    showing how the main components of CruisePlan work together.
    """
    print("========================================")
    print("   CRUISEPLAN - INTERACTIVE DEMO")
    print("========================================")

    # 1. Test Bathymetry
    print("\n1. Testing Bathymetry Layer...")
    depth = bathymetry.get_depth_at_point(47.5, -52.0)
    print(f"   - Depth at St. Johns (47.5, -52.0): {depth}m")
    if depth == -9999.0 or depth == -2750.0:  # -2750 is from the mock logic
        print("   - (Using Mock/Dev Data)")

    # 2. Test Pangaea
    print("\n2. Fetching Campaign Data...")
    pm = PangaeaManager()

    # Try fetching a real DOI (MSM cruise), fallback to dummy if offline/no lib
    test_dois = ["10.1594/PANGAEA.890663"]
    datasets = pm.fetch_datasets(test_dois)

    if not datasets:
        print("   - ⚠️  Real fetch failed (offline?), using Dummy Data.")
        datasets = [
            {
                "label": "Expedition_A",
                "latitude": [50, 51, 52],
                "longitude": [-45, -44, -43],
                "doi": "10.dummy/a",
            },
            {
                "label": "Expedition_B",
                "latitude": [53, 53.5, 54],
                "longitude": [-40, -38, -36],
                "doi": "10.dummy/b",
            },
        ]
    else:
        print(f"   - ✅ Fetched {len(datasets)} campaigns.")

    # 3. Launch UI
    print("\n3. Launching Station Picker UI...")
    print("   ----------------------------------")
    print("   INSTRUCTIONS:")
    print("   1. Press 'p' to enter Point Mode")
    print("   2. Click on the map to add stations")
    print("   3. Press 'y' to Save to 'demo_stations.yaml'")
    print("   4. Close window to finish")
    print("   ----------------------------------")

    picker = StationPicker(campaign_data=datasets, output_file="demo_stations.yaml")
    picker.show()

    print("\nDemo Complete. Check 'demo_stations.yaml' for results.")


if __name__ == "__main__":
    main()
