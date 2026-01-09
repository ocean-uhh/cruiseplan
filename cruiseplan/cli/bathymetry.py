"""
Bathymetry data download command.

This module implements the 'cruiseplan bathymetry' command for downloading
bathymetry data assets required for cruise planning.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for bathymetry command.

    Delegates all business logic to the cruiseplan.bathymetry() API function.
    """
    try:
        # Call the API function with CLI arguments
        result = cruiseplan.bathymetry(
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            output_dir=(
                str(getattr(args, "output_dir", None))
                if getattr(args, "output_dir", None)
                else None
            ),
            citation=getattr(args, "citation", False),
        )

        # Display results
        print("")
        print("=" * 50)
        print("Bathymetry Download Results")
        print("=" * 50)

        if result.data_file:
            print(f"✅ {result}")
            print("📁 Downloaded file:")
            print(f"  • {result.data_file}")

            # Show download summary
            print("📊 Download summary:")
            print(f"  • Data source: {result.source}")
            print(f"  • Output directory: {result.summary.get('output_dir', 'N/A')}")
            if result.summary.get("file_size_mb"):
                print(f"  • File size: {result.summary.get('file_size_mb')} MB")

            # Show citation if requested
            if getattr(args, "citation", False):
                print("")
                print("📖 Citation Information:")
                if result.source == "etopo2022":
                    print(
                        "  NOAA National Centers for Environmental Information. 2022."
                    )
                    print("  ETOPO 2022 15 Arc-Second Global Relief Model.")
                    print("  https://doi.org/10.25921/fd45-gt74")
                elif result.source == "gebco2025":
                    print("  GEBCO Compilation Group (2025) GEBCO 2025 Grid")
                    print(
                        "  https://doi.org/10.5285/c6612cbe-50b3-0cff-e053-6c86abc09f8f"
                    )
        else:
            print("❌ Bathymetry download failed")
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
        print(f"❌ Download error: {e}", file=sys.stderr)
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
    parser = argparse.ArgumentParser(description="Download bathymetry data")
    parser.add_argument(
        "--source",
        dest="bathy_source",
        choices=["etopo2022", "gebco2025"],
        default="etopo2022",
        help="Bathymetry data source (default: etopo2022)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Output directory for bathymetry files (default: data/bathymetry)",
    )
    parser.add_argument(
        "--citation",
        action="store_true",
        help="Show citation information for the bathymetry source",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    main(args)
