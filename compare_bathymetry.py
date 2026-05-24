#!/usr/bin/env python3
"""
Compare bathymetry depths from multiple sources at a given position.

This script compares depth values from GEBCO_2025, MSM142_JJ, and MSM142_DT
bathymetry datasets at a specified latitude and longitude position.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from cruiseplan.data.bathymetry import BathymetryManager


def compare_bathymetry(lat: float, lon: float, data_dir: str = "data/bathymetry"):
    """
    Compare bathymetry depths from multiple sources at a given position.

    Parameters
    ----------
    lat : float
        Latitude in decimal degrees
    lon : float
        Longitude in decimal degrees
    data_dir : str, optional
        Directory containing bathymetry files (default: "data/bathymetry")
    """
    sources = ["gebco2025", "msm142", "msm142_jj", "msm142_dt"]
    results = {}

    print(f"\nBathymetry comparison at position: {lat:.6f}°N, {lon:.6f}°E")
    print("=" * 60)

    for source in sources:
        try:
            manager = BathymetryManager(source=source, data_dir=data_dir)

            if manager._is_mock:
                depth = "N/A (mock mode - file not available)"
                status = "❌"
            else:
                depth = manager.get_depth_at_point(lat, lon)
                # Check for NaN or invalid values
                if isinstance(depth, (int, float)) and not np.isnan(depth):
                    depth_str = f"{depth:.2f} m"
                    status = "✅"
                elif np.isnan(depth):
                    depth_str = "N/A (outside coverage area)"
                    status = "⚠️ "
                else:
                    depth_str = str(depth)
                    status = "✅"
                depth = depth_str

            results[source] = depth
            print(f"{status} {source.upper():12s}: {depth}")

            # Clean up
            if not manager._is_mock:
                manager.close()

        except Exception as e:
            results[source] = f"Error: {e}"
            print(f"❌ {source.upper():12s}: Error: {e}")

    print("=" * 60)

    # Calculate differences if we have numeric values
    numeric_results = {}
    for source, depth in results.items():
        if isinstance(depth, str) and depth.endswith(" m"):
            try:
                value = float(depth.replace(" m", ""))
                if not np.isnan(value):
                    numeric_results[source] = value
            except ValueError:
                pass

    if len(numeric_results) >= 2:
        print("\nDifferences between sources:")
        print("-" * 30)
        sources_with_data = list(numeric_results.keys())

        for i, source1 in enumerate(sources_with_data):
            for source2 in sources_with_data[i + 1 :]:
                diff = numeric_results[source1] - numeric_results[source2]
                print(f"{source1.upper()} - {source2.upper()}: {diff:+.2f} m")

        # Show range
        depths = list(numeric_results.values())
        depth_range = max(depths) - min(depths)
        print(f"\nDepth range across sources: {depth_range:.2f} m")

    return results


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(
        description="Compare bathymetry depths from multiple sources",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("lat", type=float, help="Latitude in decimal degrees")
    parser.add_argument("lon", type=float, help="Longitude in decimal degrees")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/bathymetry",
        help="Directory containing bathymetry files",
    )

    args = parser.parse_args()

    # Validate coordinate ranges
    if not (-90 <= args.lat <= 90):
        print(f"Error: Latitude {args.lat} is out of range [-90, 90]", file=sys.stderr)
        sys.exit(1)

    if not (-180 <= args.lon <= 180):
        print(
            f"Error: Longitude {args.lon} is out of range [-180, 180]", file=sys.stderr
        )
        sys.exit(1)

    # Check if data directory exists
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"Warning: Data directory {data_path} does not exist")
        print("Creating directory...")
        data_path.mkdir(parents=True, exist_ok=True)

    try:
        results = compare_bathymetry(args.lat, args.lon, args.data_dir)

        # Check if any sources worked
        working_sources = sum(
            1
            for depth in results.values()
            if not isinstance(depth, str) or not depth.startswith(("N/A", "Error"))
        )

        if working_sources == 0:
            print("\n⚠️  No bathymetry sources are available.")
            print(
                "   Run 'cruiseplan download --source gebco2025' to download GEBCO data,"
            )
            print(
                "   or ensure MSM142 files are present in the data/bathymetry directory."
            )
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
