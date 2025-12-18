"""
Map generation CLI command for creating cruise track visualizations.

This module provides command-line functionality for generating PNG maps
directly from YAML cruise configuration files, independent of scheduling.
"""

import argparse
import logging

from cruiseplan.core.cruise import Cruise
from cruiseplan.output.map_generator import generate_map_from_yaml

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> int:
    """
    Generate PNG map from cruise configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing config_file, output options, etc.
    """
    try:
        # Load cruise configuration
        logger.info(f"Loading cruise configuration from {args.config_file}")
        cruise = Cruise(args.config_file)

        # Determine output file path
        if args.output_file:
            output_file = args.output_file
        else:
            # Auto-generate filename based on cruise name
            cruise_name = cruise.config.cruise_name.replace(" ", "_").replace("/", "-")
            output_file = args.output_dir / f"{cruise_name}_map.png"

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Generate the map
        logger.info(f"Generating map with bathymetry source: {args.bathymetry_source}")
        result_path = generate_map_from_yaml(
            cruise,
            output_file=output_file,
            bathymetry_source=args.bathymetry_source,
            bathymetry_stride=args.bathymetry_stride,
            bathymetry_dir=str(args.bathymetry_dir),
            show_plot=args.show_plot,
            figsize=tuple(args.figsize),
        )

        if result_path:
            logger.info(f"✅ Map generated successfully: {result_path}")
            print(f"🗺️ Map saved to: {result_path}")

            # Print some basic stats
            station_count = len(cruise.station_registry)
            print(f"📍 Stations plotted: {station_count}")

            if (
                hasattr(cruise.config, "departure_port")
                and cruise.config.departure_port
            ):
                print(f"🚢 Departure: {cruise.config.departure_port.name}")
            if hasattr(cruise.config, "arrival_port") and cruise.config.arrival_port:
                print(f"🏁 Arrival: {cruise.config.arrival_port.name}")
        else:
            logger.error("❌ Map generation failed")
            return 1

    except FileNotFoundError:
        logger.error(f"❌ Configuration file not found: {args.config_file}")
        return 1
    except Exception as e:
        logger.error(f"❌ Map generation failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0
