"""
cruiseplan.cli package.

This package contains command-line interface modules for cruiseplan:

- :mod:`main`: Primary CLI entry point and command dispatcher
- :mod:`stations`: Commands for managing and validating station definitions
- :mod:`schedule`: Commands for generating and displaying cruise schedules
- :mod:`download`: Commands for downloading external data sources
- :mod:`enrich`: Commands for enriching cruise data with additional information
- :mod:`pangaea`: Commands for interacting with Pangaea data repository
- :mod:`validate`: Commands for validating cruise configuration files
- :mod:`utils`: Shared utility functions for CLI operations

These modules provide the user interface for interacting with cruiseplan functionality
through the command line, supporting the full workflow from configuration to output generation.
"""

import sys
from contextlib import contextmanager


@contextmanager
def handle_cli_errors(command_name: str, verbose: bool = False):
    """
    Context manager that catches and formats standard cruiseplan CLI errors.

    Parameters
    ----------
    command_name : str
        Name shown in RuntimeError messages (e.g. "map", "schedule").
    verbose : bool
        If True, print a full traceback on unexpected errors.
    """
    import cruiseplan

    try:
        yield
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
        print(f"❌ {command_name} error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
