"""
Unified configuration processing command.

This module implements the 'cruiseplan process' command that runs the complete
workflow: enrichment -> validation -> map generation.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for process command.

    Delegates all business logic to the cruiseplan.process() API function.
    """
    try:
        # Call the API function with CLI arguments
        result = cruiseplan.process(
            config_file=args.config_file,
            output_dir=str(getattr(args, "output_dir", "data")),
            output=getattr(args, "output", None),
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            add_depths=getattr(args, "add_depths", True),
            add_coords=getattr(args, "add_coords", True),
            expand_sections=getattr(args, "expand_sections", True),
            run_validation=getattr(args, "run_validation", True),
            run_map_generation=getattr(args, "run_map_generation", True),
            depth_check=getattr(args, "depth_check", True),
            tolerance=getattr(args, "tolerance", 10.0),
            format=getattr(args, "format", "all"),
            bathy_stride=getattr(args, "bathy_stride", 10),
            figsize=getattr(args, "figsize", None),
            no_port_map=getattr(args, "no_port_map", False),
            verbose=getattr(args, "verbose", False),
        )

        # Display results
        print("")
        print("=" * 50)
        print("Processing Results")
        print("=" * 50)

        if result.config:
            print(f"✅ {result}")
            print("📁 Generated files:")
            for file_path in result.files_created:
                print(f"  • {file_path}")

            # Show processing summary
            print("📊 Processing summary:")
            print(f"  • Config file: {result.summary.get('config_file', 'N/A')}")
            print(f"  • Files generated: {result.summary.get('files_generated', 0)}")
            if result.summary.get("enrichment_run"):
                print("  • ✅ Enrichment completed")
            if result.summary.get("validation_run"):
                print("  • ✅ Validation completed")
            if result.summary.get("map_generation_run"):
                print("  • ✅ Map generation completed")
        else:
            print("❌ Processing failed")
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
        print(f"❌ Processing error: {e}", file=sys.stderr)
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
    parser = argparse.ArgumentParser(description="Process cruise configurations")
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
        help="Output directory for processed files",
    )
    parser.add_argument(
        "--output", help="Base filename for outputs (without extension)"
    )
    parser.add_argument(
        "--bathy-source",
        default="etopo2022",
        help="Bathymetry data source (default: etopo2022)",
    )
    parser.add_argument(
        "--bathy-dir", default="data/bathymetry", help="Bathymetry data directory"
    )
    parser.add_argument(
        "--no-add-depths",
        action="store_false",
        dest="add_depths",
        help="Skip adding depth information",
    )
    parser.add_argument(
        "--no-add-coords",
        action="store_false",
        dest="add_coords",
        help="Skip adding coordinate information",
    )
    parser.add_argument(
        "--no-validation",
        action="store_false",
        dest="run_validation",
        help="Skip validation step",
    )
    parser.add_argument(
        "--no-map-generation",
        action="store_false",
        dest="run_map_generation",
        help="Skip map generation step",
    )
    parser.add_argument(
        "--format",
        choices=["html", "latex", "csv", "netcdf", "all"],
        default="all",
        help="Output format for schedule (default: all)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth tolerance percentage (default: 10.0)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()
    main(args)
