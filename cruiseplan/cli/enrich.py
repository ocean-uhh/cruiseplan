"""
Configuration enrichment command.

This module implements the 'cruiseplan enrich' command for adding missing
data to existing YAML configuration files.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for enrich command.

    Delegates all business logic to the cruiseplan.enrich() API function.
    """
    try:
        # Call the API function with CLI arguments
        result = cruiseplan.enrich(
            config_file=args.config_file,
            output_dir=(
                str(args.output_dir)
                if hasattr(args, "output_dir") and args.output_dir
                else "data"
            ),
            output=getattr(args, "output", None),
            add_depths=getattr(args, "add_depths", False),
            add_coords=getattr(args, "add_coords", False),
            expand_sections=getattr(args, "expand_sections", False),
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_dir=(
                str(args.bathy_dir)
                if hasattr(args, "bathy_dir") and args.bathy_dir
                else "data/bathymetry"
            ),
            verbose=getattr(args, "verbose", False),
        )

        print(f"✅ Configuration enriched successfully: {result}")

    except cruiseplan.ValidationError as e:
        print(f"❌ Configuration validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except cruiseplan.FileError as e:
        print(f"❌ File operation error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}", file=sys.stderr)
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
    import argparse

    parser = argparse.ArgumentParser(description="Enrich cruise configurations")
    parser.add_argument(
        "-c", "--config-file", type=Path, required=True, help="Input YAML file"
    )
    parser.add_argument("--add-depths", action="store_true", help="Add missing depths")
    parser.add_argument(
        "--add-coords", action="store_true", help="Add coordinate fields"
    )
    parser.add_argument(
        "--expand-sections", action="store_true", help="Expand CTD sections"
    )
    parser.add_argument(
        "--expand-ports", action="store_true", help="Expand global port references"
    )
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("."))
    parser.add_argument(
        "--output", type=str, help="Base filename for output (without extension)"
    )
    parser.add_argument("--bathy-source", default="etopo2022")
    parser.add_argument("--bathy-dir", type=Path, default=Path("data"))
    # Keep deprecated parameters for backward compatibility
    parser.add_argument(
        "--bathymetry-source", dest="bathymetry_source", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--bathymetry-dir", type=Path, dest="bathymetry_dir", help=argparse.SUPPRESS
    )

    args = parser.parse_args()
    main(args)
