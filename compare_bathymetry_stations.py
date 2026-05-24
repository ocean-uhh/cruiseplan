#!/usr/bin/env python3
"""
Compare bathymetry depths for all stations in a cruise configuration YAML file.

This script reads station coordinates from CruisePlan YAML configuration files
and compares bathymetry depths from GEBCO_2025, MSM142_JJ, and MSM142_DT datasets
for each station position.
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import yaml

from cruiseplan.data.bathymetry import BathymetryManager


def parse_decmin_coordinate(decmin_str: str) -> float:
    """
    Parse decimal minutes coordinate format to decimal degrees.

    Examples
    --------
        "65 32.746 N" -> 65.545767
        "29 22.132 W" -> -29.36887

    Parameters
    ----------
    decmin_str : str
        Coordinate in "DD MM.mmm N/S/E/W" format

    Returns
    -------
    float
        Coordinate in decimal degrees
    """
    # Remove extra whitespace and normalize
    decmin_str = re.sub(r"\s+", " ", decmin_str.strip())

    # Parse format: "DD MM.mmm DIR"
    parts = decmin_str.split()
    if len(parts) != 3:
        raise ValueError(f"Invalid decmin format: {decmin_str}")

    degrees = float(parts[0])
    minutes = float(parts[1])
    direction = parts[2].upper()

    # Convert to decimal degrees
    decimal = degrees + minutes / 60.0

    # Apply sign based on direction
    if direction in ["S", "W"]:
        decimal = -decimal
    elif direction not in ["N", "E"]:
        raise ValueError(f"Invalid direction: {direction}")

    return decimal


def extract_station_coordinates(yaml_data: dict) -> list:
    """
    Extract station coordinates from YAML configuration.

    Parameters
    ----------
    yaml_data : dict
        Parsed YAML data

    Returns
    -------
    list
        List of tuples (name, lat, lon) for each station
    """
    stations = []

    # Look for points section
    if "points" not in yaml_data:
        raise ValueError("No 'points' section found in YAML file")

    for point in yaml_data["points"]:
        name = point.get("name", "Unknown")

        # Try to get coordinates - prefer decimal degrees first
        lat = lon = None

        if "latitude" in point and "longitude" in point:
            lat = float(point["latitude"])
            lon = float(point["longitude"])
        elif "latitude_decmin" in point and "longitude_decmin" in point:
            try:
                lat = parse_decmin_coordinate(point["latitude_decmin"])
                lon = parse_decmin_coordinate(point["longitude_decmin"])
            except ValueError as e:
                print(f"Warning: Could not parse coordinates for {name}: {e}")
                continue
        else:
            print(f"Warning: No coordinates found for station {name}")
            continue

        stations.append((name, lat, lon))

    return stations


def get_bathymetry_depth(source: str, lat: float, lon: float, data_dir: str) -> tuple:
    """
    Get bathymetry depth from a specific source.

    Parameters
    ----------
    source : str
        Bathymetry source name
    lat : float
        Latitude in decimal degrees
    lon : float
        Longitude in decimal degrees
    data_dir : str
        Directory containing bathymetry files

    Returns
    -------
    tuple
        (formatted_depth_string, numeric_depth_value or None)
    """
    try:
        manager = BathymetryManager(source=source, data_dir=data_dir)

        if manager._is_mock:
            return "N/A", None

        depth = manager.get_depth_at_point(lat, lon)

        # Clean up
        if not manager._is_mock:
            manager.close()

        # Check for NaN or invalid values
        if isinstance(depth, (int, float)) and not np.isnan(depth):
            # Check for default/mock values that indicate no coverage
            if depth == -9999.0 or abs(depth + 9999.0) < 0.1:
                return "N/A", None
            return f"{depth:.1f}", depth
        else:
            return "N/A", None

    except Exception:
        return "Error", None


def compare_stations_bathymetry(
    yaml_file: str, data_dir: str = "data/bathymetry", output_file: str = None
):
    """
    Compare bathymetry depths for all stations in a YAML configuration file.

    Parameters
    ----------
    yaml_file : str
        Path to YAML configuration file
    data_dir : str, optional
        Directory containing bathymetry files (default: "data/bathymetry")
    output_file : str, optional
        Output file path (if None, prints to stdout)
    """
    # Read YAML file
    yaml_path = Path(yaml_file)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_file}")

    with open(yaml_path) as f:
        yaml_data = yaml.safe_load(f)

    # Extract station coordinates
    stations = extract_station_coordinates(yaml_data)

    if not stations:
        print("No stations with valid coordinates found in YAML file")
        return

    print(f"Found {len(stations)} stations with coordinates")

    # Prepare output
    output_lines = []

    # Header
    cruise_name = yaml_data.get("cruise_name", yaml_path.stem)
    output_lines.append(f"Bathymetry Comparison for {cruise_name}")
    output_lines.append("=" * 80)
    output_lines.append("")

    # Table header
    header = f"{'Station':<15} {'Latitude':<10} {'Longitude':<11} {'MSM142_JJ':<10} {'MSM142_DT':<10} {'GEBCO2025':<10} {'JJ-DT':<7} {'JJ-GB':<7} {'DT-GB':<7}"
    output_lines.append(header)
    output_lines.append("-" * 115)

    # Process each station
    sources = ["msm142_jj", "msm142_dt", "gebco2025"]
    all_depths = {source: [] for source in sources}

    for name, lat, lon in stations:
        # Get depths from all sources
        depths_str = {}
        depths_num = {}
        for source in sources:
            depth_str, depth_num = get_bathymetry_depth(source, lat, lon, data_dir)
            depths_str[source] = depth_str
            depths_num[source] = depth_num

            # Collect numeric values for statistics
            if depth_num is not None:
                all_depths[source].append(depth_num)

        # Calculate absolute differences
        jj = depths_num["msm142_jj"]
        dt = depths_num["msm142_dt"]
        gb = depths_num["gebco2025"]

        # Format signed differences (only if both values are available)
        diff_jj_dt = f"{jj - dt:+6.1f}" if jj is not None and dt is not None else "N/A"
        diff_jj_gb = f"{jj - gb:+6.1f}" if jj is not None and gb is not None else "N/A"
        diff_dt_gb = f"{dt - gb:+6.1f}" if dt is not None and gb is not None else "N/A"

        # Format row
        row = f"{name:<15} {lat:>9.4f} {lon:>10.4f} {depths_str['msm142_jj']:>9s} {depths_str['msm142_dt']:>9s} {depths_str['gebco2025']:>9s} {diff_jj_dt:>7s} {diff_jj_gb:>7s} {diff_dt_gb:>7s}"
        output_lines.append(row)

    # Add summary statistics
    output_lines.append("")
    output_lines.append("Summary Statistics:")
    output_lines.append("-" * 40)

    for source in sources:
        depths = all_depths[source]
        if depths:
            count = len(depths)
            min_depth = min(depths)
            max_depth = max(depths)
            mean_depth = sum(depths) / len(depths)
            depth_range = max_depth - min_depth

            source_name = source.replace("_", " ").upper()
            output_lines.append(
                f"{source_name:12s}: {count:2d} stations, "
                f"range {min_depth:6.1f} to {max_depth:6.1f} m, "
                f"mean {mean_depth:6.1f} m, span {depth_range:5.1f} m"
            )
        else:
            source_name = source.replace("_", " ").upper()
            output_lines.append(f"{source_name:12s}: No data available")

    output_lines.append("")
    output_lines.append("Notes:")
    output_lines.append("- Depths in meters (negative = below sea level)")
    output_lines.append(
        "- Difference columns show signed differences (positive = first dataset deeper)"
    )
    output_lines.append("- JJ-DT: MSM142_JJ minus MSM142_DT")
    output_lines.append("- JJ-GB: MSM142_JJ minus GEBCO2025")
    output_lines.append("- DT-GB: MSM142_DT minus GEBCO2025")
    output_lines.append("- N/A = No data available or outside coverage area")
    output_lines.append("- Error = Failed to load bathymetry data")

    # Output results
    output_text = "\n".join(output_lines)

    if output_file:
        output_path = Path(output_file)
        with open(output_path, "w") as f:
            f.write(output_text)
        print(f"Results written to: {output_path}")
    else:
        print(output_text)


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(
        description="Compare bathymetry depths for stations in a YAML configuration file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("yaml_file", type=str, help="Path to YAML configuration file")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/bathymetry",
        help="Directory containing bathymetry files",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (if not specified, prints to stdout)",
    )

    args = parser.parse_args()

    # Check if YAML file exists
    if not Path(args.yaml_file).exists():
        print(f"Error: YAML file not found: {args.yaml_file}", file=sys.stderr)
        sys.exit(1)

    # Check if data directory exists
    data_path = Path(args.data_dir)
    if not data_path.exists():
        print(f"Warning: Data directory {data_path} does not exist")
        print("Creating directory...")
        data_path.mkdir(parents=True, exist_ok=True)

    try:
        compare_stations_bathymetry(args.yaml_file, args.data_dir, args.output)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
