"""
Station picker CLI subcommand implementation.
"""

import argparse
import sys


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for interactive station placement.
    """
    try:
        # Import here to handle optional matplotlib dependency gracefully
        # Note: load_campaign_data must be implemented in cruiseplan.data.pangaea
        from cruiseplan.data.pangaea import load_campaign_data
        from cruiseplan.interactive.station_picker import StationPicker

    except ImportError as e:
        print(f"❌ Missing required dependencies for interactive station picker: {e}")
        print("Install with: pip install cruiseplan[interactive]")
        sys.exit(1)

    # Load PANGAEA campaign data if provided
    campaign_data = None
    if args.pangaea_file and args.pangaea_file.exists():
        try:
            # Assume load_campaign_data returns a structured list/dict
            campaign_data = load_campaign_data(args.pangaea_file)
            print(f"✅ Loaded {len(campaign_data)} PANGAEA campaigns")
        except Exception as e:
            print(f"⚠️ Warning: Could not load PANGAEA file: {e}")

    # Set up coordinate bounds with defaults if not provided
    lat_bounds = args.lat if args.lat else [45, 70]
    lon_bounds = args.lon if args.lon else [-65, -5]

    # Determine output file
    if args.output_file:
        output_file = args.output_file
    else:
        output_file = args.output_dir / "stations.yaml"

    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("🎯 Starting interactive station picker...")
    print(
        f"   Coordinate bounds: {lat_bounds[0]}-{lat_bounds[1]}°N, {lon_bounds[0]}-{lon_bounds[1]}°E"
    )
    print(f"   Output file: {output_file}")
    print("\nControls:")
    print("  'p' - Place point stations")
    print("  'l' - Draw line transects")
    print("  'a' - Define area operations")
    print("  'n' - Navigation mode")
    print("  'y' - Save to YAML")
    print("  'c' - Clear all operations")
    print("  'esc' - Exit without saving")

    try:
        # Initialize and run the interactive picker
        picker = StationPicker(
            campaign_data=campaign_data, output_file=str(output_file)
        )

        # Set initial coordinate bounds on the map axis
        # Note: The StationPicker class must expose 'ax_map' and '_update_aspect_ratio'
        picker.ax_map.set_xlim(lon_bounds)
        picker.ax_map.set_ylim(lat_bounds)
        picker._update_aspect_ratio()

        # Show the interface (Blocking call)
        picker.show()

    except Exception as e:
        print(f"❌ Error during station picking: {e}")
        sys.exit(1)
