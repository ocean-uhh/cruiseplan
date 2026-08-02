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
from cruiseplan.config.values import (
    BATHY_SOURCES,
    DEFAULT_BATHY_DIR,
    DEFAULT_BATHY_SOURCE,
)


def _display_validation_results(result, warnings_only: bool) -> None:
    """Display validation results in formatted output."""
    print("")
    print("=" * 50)
    print("Validation Results")
    print("=" * 50)

    if result.errors:
        print("Validation errors:")
        for error in result.errors:
            print(f"  • {error}")

    if result.warnings:
        if warnings_only:
            print("Validation warnings (informational only):")
        else:
            print("Validation warnings:")
        for warning in result.warnings:
            print(f"  • {warning}")


def _print_summary_and_exit(result, warnings_only: bool) -> None:
    """Print validation summary and exit with appropriate code."""
    if result.success:
        print(f"Validation passed ({len(result.warnings)} warnings)")
        if result.warnings and warnings_only:
            print("Treating warnings as informational only")
        sys.exit(0)
    else:
        print(
            f"Validation failed ({len(result.errors)} errors, {len(result.warnings)} warnings)"
        )
        sys.exit(1)


def _handle_exceptions(args: argparse.Namespace) -> None:
    """Handle common exceptions with appropriate error messages."""

    def handle_error(message: str, exit_code: int = 1) -> None:
        print(message, file=sys.stderr)
        sys.exit(exit_code)

    try:
        raise
    except cruiseplan.ValidationError as e:
        handle_error(f"ERROR: Configuration validation error: {e}")
    except cruiseplan.FileError as e:
        handle_error(f"ERROR: File operation error: {e}")
    except cruiseplan.BathymetryError as e:
        handle_error(f"ERROR: Bathymetry error: {e}")
    except FileNotFoundError as e:
        handle_error(f"ERROR: File not found: {e}")
    except KeyboardInterrupt:
        handle_error("\nOperation cancelled by user.")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


def run(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for validate command.

    Delegates all business logic to the cruiseplan.validate() API function.
    """
    try:
        result = cruiseplan.validate(
            config_file=args.config_file,
            bathy_source=getattr(args, "bathy_source", "gebco2025"),
            bathy_dir=getattr(args, "bathy_dir", "data/bathymetry"),
            check_depths=getattr(args, "check_depths", True),
            tolerance=getattr(args, "tolerance", 10.0),
            warnings_only=getattr(args, "warnings_only", False),
            verbose=getattr(args, "verbose", False),
        )

        warnings_only = getattr(args, "warnings_only", False)
        _display_validation_results(result, warnings_only)
        _print_summary_and_exit(result, warnings_only)

    except Exception:
        _handle_exceptions(args)


def build_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """Add the validate subparser and return it."""
    p = subparsers.add_parser(
        "validate", help="Validate configuration files (read-only)"
    )
    p.add_argument(
        "config_file",
        type=Path,
        metavar="CONFIG_FILE",
        help="Input YAML configuration file",
    )
    p.add_argument(
        "--no-depth-check",
        action="store_false",
        dest="check_depths",
        help="Skip comparison of existing depths with bathymetry data",
    )
    p.add_argument(
        "--tolerance",
        type=float,
        default=10.0,
        help="Depth difference tolerance in percent (default: 10.0)",
    )
    p.add_argument(
        "--bathy-source",
        choices=BATHY_SOURCES,
        default=DEFAULT_BATHY_SOURCE,
        help="Bathymetry dataset (default: gebco2025)",
    )
    p.add_argument(
        "--bathy-dir",
        type=Path,
        default=Path(DEFAULT_BATHY_DIR),
        help="Directory containing bathymetry data (default: data/bathymetry)",
    )
    p.add_argument(
        "--warnings-only",
        action="store_true",
        help="Show warnings without failing",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    return p
