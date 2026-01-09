"""
Configuration validation command.

This module implements the 'cruiseplan validate' command for comprehensive
validation of YAML configuration files without modification.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

import cruiseplan


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for validate command.

    Delegates all business logic to the cruiseplan.validate() API function.
    """
    try:
        # Call the API function with CLI arguments
        result = cruiseplan.validate(
            config_file=args.config_file,
            bathy_source=getattr(args, "bathy_source", "etopo2022"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            check_depths=getattr(args, "check_depths", True),
            tolerance=getattr(args, "tolerance", 10.0),
            strict=getattr(args, "strict", False),
            warnings_only=getattr(args, "warnings_only", False),
            verbose=getattr(args, "verbose", False),
        )

        # Display validation results
        print("")
        print("=" * 50)
        print("Validation Results")
        print("=" * 50)

        if result.errors:
            print("❌ Validation Errors:")
            for error in result.errors:
                print(f"  • {error}")

        if result.warnings:
            if getattr(args, "warnings_only", False):
                print("ℹ️ Validation Warnings (informational only):")
                for warning in result.warnings:
                    print(f"  • {warning}")
            else:
                print("⚠️ Validation Warnings:")
                for warning in result.warnings:
                    print(f"  • {warning}")

        # Print summary and exit
        if result.success:
            print(f"✅ Validation passed ({len(result.warnings)} warnings)")
            if result.warnings and getattr(args, "warnings_only", False):
                print("ℹ️ Treating warnings as informational only")
            sys.exit(0)
        else:
            print(
                f"❌ Validation failed ({len(result.errors)} errors, {len(result.warnings)} warnings)"
            )
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

    parser = argparse.ArgumentParser(description="Validate cruise configurations")
    parser.add_argument(
        "-c", "--config-file", type=Path, required=True, help="Input YAML file"
    )
    parser.add_argument(
        "--check-depths", action="store_true", help="Check depth accuracy"
    )
    parser.add_argument("--strict", action="store_true", help="Strict validation mode")
    parser.add_argument(
        "--warnings-only", action="store_true", help="Show warnings without failing"
    )
    parser.add_argument(
        "--tolerance", type=float, default=10.0, help="Depth tolerance percentage"
    )
    parser.add_argument("--bathymetry-source", default="etopo2022")

    args = parser.parse_args()
    main(args)
