"""
cruiseplan.cli package.

This package contains command-line interface modules for cruiseplan:

- :mod:`main`: Primary CLI entry point and command dispatcher
- :mod:`bathymetry`: Download bathymetry data
- :mod:`enrich`: Enrich cruise YAML with computed fields
- :mod:`forecast`: Generate real-time rolling station plan forecasts
- :mod:`list`: List activities in a schedule with indices
- :mod:`map`: Generate cruise track maps
- :mod:`pangaea`: Export data to Pangaea
- :mod:`process`: Process cruise YAML into enriched output
- :mod:`schedule`: Generate cruise schedules
- :mod:`stations`: Validate and display station definitions
- :mod:`validate`: Validate cruise configuration files
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
        print(f"ERROR: Configuration validation error: {e}", file=sys.stderr)
        sys.exit(1)
    except cruiseplan.FileError as e:
        print(f"ERROR: File operation error: {e}", file=sys.stderr)
        sys.exit(1)
    except cruiseplan.BathymetryError as e:
        print(f"ERROR: Bathymetry error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"ERROR: {command_name} error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
