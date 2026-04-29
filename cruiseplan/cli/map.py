"""
Map generation command.

This module implements the 'cruiseplan map' command for generating
cruise track visualizations (PNG maps and KML files).

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for map command.

    Delegates all business logic to the cruiseplan.map() API function.
    """
    try:
        # Call the API function with CLI arguments
        result = cruiseplan.map(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            format=getattr(args, "format", "all"),
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_dir=getattr(args, "bathy_dir", "data"),
            bathy_stride=getattr(args, "bathy_stride", 5),
            bathy_contours=getattr(args, "bathy_contours", None),
            lat_bounds=getattr(args, "lat", None),
            lon_bounds=getattr(args, "lon", None),
            figsize=getattr(args, "figsize", None),
            show_plot=getattr(args, "show_plot", False),
            no_ports=getattr(args, "no_ports", False),
            verbose=getattr(args, "verbose", False),
        )

        # Display results
        print("")
        print("=" * 50)
        print("Map Generation Results")
        print("=" * 50)

        if result.map_files:
            print(f"✅ {result}")
            print("📁 Generated files:")
            for file_path in result.map_files:
                print(f"  • {file_path}")

            # Show map generation summary
            print("📊 Generation summary:")
            print(f"  • Config file: {result.summary.get('config_file', 'N/A')}")
            print(f"  • Output format: {result.format}")
            print(f"  • Files generated: {result.summary.get('files_generated', 0)}")
            print(f"  • Output directory: {result.summary.get('output_dir', 'N/A')}")
        else:
            print("❌ Map generation failed")
            if "error" in result.summary:
                print(f"Error: {result.summary['error']}")
            sys.exit(1)

    except cruiseplan.ValidationError as e:
        print(f"❌ Configuration validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except cruiseplan.FileError as e:
        print(f"❌ File operation error: {e}", file=sys.stderr)
        sys.exit(1)
    except cruiseplan.BathymetryError as e:
        print(f"❌ Bathymetry error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Map generation error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    parser = argparse.ArgumentParser(description="Generate cruise maps")
    parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        required=True,
        help="Input YAML configuration file",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for map files",
    )
    parser.add_argument(
        "--output", help="Base filename for outputs (without extension)"
    )
    parser.add_argument(
        "--format",
        choices=["png", "kml", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--bathy-source",
        default="etopo2022",
        help="Bathymetry data source (default: etopo2022)",
    )
    parser.add_argument("--bathy-dir", default="data", help="Bathymetry data directory")
    parser.add_argument(
        "--bathy-stride",
        type=int,
        default=5,
        help="Bathymetry data stride (default: 5)",
    )
    parser.add_argument(
        "--bathy-contours",
        type=float,
        nargs="+",
        metavar="DEPTH",
        help="Custom bathymetry contour levels in meters (space-separated positive values), e.g., '500 400 300'",
    )
    parser.add_argument(
        "--lat",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Latitude bounds for map extent (e.g., --lat -75 -70)",
    )
    parser.add_argument(
        "--lon",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="Longitude bounds for map extent (e.g., --lon 170 175)",
    )
    parser.add_argument(
        "--figsize",
        type=float,
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        help="Figure size in inches (width height)",
    )
    parser.add_argument(
        "--show-plot", action="store_true", help="Display plot interactively"
    )
    parser.add_argument(
        "--no-ports", action="store_true", help="Exclude ports from map"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    main(args)
