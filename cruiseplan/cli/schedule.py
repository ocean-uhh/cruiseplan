"""
Cruise schedule generation command.

This module implements the 'cruiseplan schedule' command for generating
comprehensive cruise schedules from YAML configuration files.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for schedule command.

    Delegates all business logic to the cruiseplan.schedule() API function.
    """
    try:
        # Check --derive-netcdf flag compatibility (CLI-specific logic)
        derive_netcdf = getattr(args, "derive_netcdf", False)
        format_str = getattr(args, "format", "all")
        if derive_netcdf and format_str != "all" and "netcdf" not in format_str:
            print(
                "⚠️  --derive-netcdf flag requires NetCDF output format", file=sys.stderr
            )
            print(
                "   Either add 'netcdf' to --format or use --format all",
                file=sys.stderr,
            )
            print("   Ignoring --derive-netcdf flag.", file=sys.stderr)
            derive_netcdf = False

        # Call the API function with CLI arguments
        result = cruiseplan.schedule(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            format=getattr(args, "format", "all"),
            leg=getattr(args, "leg", None),
            derive_netcdf=derive_netcdf,
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            bathy_stride=getattr(args, "bathy_stride", 10),
            figsize=getattr(args, "figsize", None),
            verbose=getattr(args, "verbose", False),
        )

        # Display results
        print("")
        print("=" * 50)
        print("Schedule Generation Results")
        print("=" * 50)

        if result.timeline:
            print(f"✅ {result}")
            print("📁 Generated files:")
            for file_path in result.files_created:
                print(f"  • {file_path}")

            # Show timeline summary
            if result.timeline:
                total_duration_hours = (
                    sum(
                        activity.get("duration_minutes", 0)
                        for activity in result.timeline
                    )
                    / 60.0
                )
                print(f"⏱️  Total timeline duration: {total_duration_hours:.1f} hours")
                print(f"📊 Timeline activities: {len(result.timeline)}")
        else:
            print("❌ Schedule generation failed")
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
        print(f"❌ Schedule generation error: {e}", file=sys.stderr)
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
    parser = argparse.ArgumentParser(description="Generate cruise schedules")
    parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        required=True,
        help="Input YAML configuration file",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, help="Output directory for schedule files"
    )
    parser.add_argument(
        "--format",
        choices=["html", "latex", "csv", "netcdf", "all"],
        default="all",
        help="Output format (default: all)",
    )
    parser.add_argument(
        "--leg", type=str, help="Generate schedule for specific leg only"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", action="store_true", help="Quiet output")
    parser.add_argument(
        "--derive-netcdf", action="store_true", help="Generate specialized NetCDF files"
    )

    args = parser.parse_args()
    main(args)
