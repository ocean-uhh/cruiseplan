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
from cruiseplan.cli import handle_cli_errors


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for schedule command.

    Delegates all business logic to the cruiseplan.schedule() API function.
    """
    verbose = getattr(args, "verbose", False)
    with handle_cli_errors("schedule", verbose):
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

        result = cruiseplan.schedule(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            format=getattr(args, "format", "all"),
            leg=getattr(args, "leg", None),
            derive_netcdf=derive_netcdf,
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            bathy_stride=getattr(args, "bathy_stride", 10),
            bathy_contours=getattr(args, "bathy_contours", None),
            lat_bounds=getattr(args, "lat", None),
            lon_bounds=getattr(args, "lon", None),
            figsize=getattr(args, "figsize", None),
            no_ports=getattr(args, "no_ports", False),
            no_title=getattr(args, "no_title", False),
            no_labels=getattr(args, "no_labels", False),
            no_legend=getattr(args, "no_legend", False),
            verbose=verbose,
            max_depth=getattr(args, "max_depth", None),
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

            total_duration_hours = (
                sum(activity.get("duration_minutes", 0) for activity in result.timeline)
                / 60.0
            )
            print(f"⏱️  Total timeline duration: {total_duration_hours:.1f} hours")
            print(f"📊 Timeline activities: {len(result.timeline)}")
        else:
            print("❌ Schedule generation failed")
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
        choices=["html", "latex", "csv", "netcdf", "png", "all"],
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
