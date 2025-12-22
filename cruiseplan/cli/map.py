"""
Map generation CLI command for creating cruise track visualizations.

This module provides command-line functionality for generating PNG maps
directly from YAML cruise configuration files, independent of scheduling.
"""

import argparse
import logging

from cruiseplan.cli.utils import load_cruise_with_pretty_warnings
from cruiseplan.output.map_generator import generate_map_from_yaml

logger = logging.getLogger(__name__)


def main(args: argparse.Namespace) -> int:
    """
    Generate PNG maps and/or KML files from cruise configuration.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing config_file, output options, etc.
    """
    try:
        # Handle legacy parameter deprecation warnings and parameter mapping
        if hasattr(args, "bathymetry_source_legacy") and args.bathymetry_source_legacy:
            logger.warning(
                "⚠️  WARNING: '--bathymetry-source' is deprecated. Use '--bathy-source' instead."
            )
            args.bathy_source = args.bathymetry_source_legacy

        if hasattr(args, "bathymetry_dir_legacy") and args.bathymetry_dir_legacy:
            logger.warning(
                "⚠️  WARNING: '--bathymetry-dir' is deprecated. Use '--bathy-dir' instead."
            )
            args.bathy_dir = args.bathymetry_dir_legacy

        if hasattr(args, "bathymetry_stride_legacy") and args.bathymetry_stride_legacy:
            logger.warning(
                "⚠️  WARNING: '--bathymetry-stride' is deprecated. Use '--bathy-stride' instead."
            )
            args.bathy_stride = args.bathymetry_stride_legacy

        # Load cruise configuration with pretty warning formatting
        logger.info(f"Loading cruise configuration from {args.config_file}")
        cruise = load_cruise_with_pretty_warnings(args.config_file)

        # Parse format selection
        formats = []
        if args.format == "all":
            formats = ["png", "kml"]
        else:
            formats = [args.format]

        # Ensure output directory exists
        args.output_dir.mkdir(parents=True, exist_ok=True)

        # Handle deprecated --output-file parameter
        if hasattr(args, "output_file") and args.output_file:
            logger.warning(
                "⚠️  WARNING: '--output-file' is deprecated. Use '--output' for base filename and '--output-dir' for the path."
            )

        # Determine base filename (use --output if provided, otherwise cruise name)
        if hasattr(args, "output") and args.output:
            base_name = args.output
        else:
            base_name = cruise.config.cruise_name.replace(" ", "_").replace("/", "-")

        # Track generated files
        generated_files = []

        # Generate PNG map if requested
        if "png" in formats:
            if (
                hasattr(args, "output_file")
                and args.output_file
                and args.format == "png"
            ):
                # Use legacy specific output file for PNG only
                png_output_file = args.output_file
            else:
                # Use base filename pattern
                png_output_file = args.output_dir / f"{base_name}_map.png"

            logger.info(
                f"Generating PNG map with bathymetry source: {args.bathy_source}"
            )
            png_result = generate_map_from_yaml(
                cruise,
                output_file=png_output_file,
                bathy_source=args.bathy_source,
                bathy_stride=args.bathy_stride,
                bathy_dir=str(args.bathy_dir),
                show_plot=args.show_plot,
                figsize=tuple(args.figsize),
                include_ports=False,  # Focus on scientific operations only
            )

            if png_result:
                generated_files.append(("PNG map", png_result))
                logger.info(f"✅ PNG map generated: {png_result}")
            else:
                logger.error("❌ PNG map generation failed")
                return 1

        # Generate KML file if requested
        if "kml" in formats:
            if (
                hasattr(args, "output_file")
                and args.output_file
                and args.format == "kml"
            ):
                # Use legacy specific output file for KML only
                kml_output_file = args.output_file
            else:
                # Use base filename pattern
                kml_output_file = args.output_dir / f"{base_name}_catalog.kml"

            logger.info("Generating KML catalog from YAML configuration")
            from cruiseplan.output.kml_generator import generate_kml_catalog

            kml_result = generate_kml_catalog(cruise.config, kml_output_file)

            if kml_result:
                generated_files.append(("KML catalog", kml_result))
                logger.info(f"✅ KML catalog generated: {kml_result}")
            else:
                logger.error("❌ KML catalog generation failed")
                return 1

        # Print summary of generated files
        print("✅ Map generation complete!")
        for file_type, file_path in generated_files:
            print(f"📁 {file_type}: {file_path}")

        # Print statistics based on operation types
        station_count = 0
        mooring_count = 0

        # Count stations by operation type
        if hasattr(cruise, "station_registry") and cruise.station_registry:
            for station in cruise.station_registry.values():
                operation_type = getattr(station, "operation_type", "station")
                if operation_type == "mooring":
                    mooring_count += 1
                else:
                    station_count += 1

        # Add dedicated moorings from mooring_registry
        if hasattr(cruise, "mooring_registry") and cruise.mooring_registry:
            mooring_count += len(cruise.mooring_registry)
        transit_count = (
            len(cruise.transit_registry)
            if hasattr(cruise, "transit_registry") and cruise.transit_registry
            else 0
        )
        area_count = (
            len(cruise.area_registry)
            if hasattr(cruise, "area_registry") and cruise.area_registry
            else 0
        )

        print("\n📊 Catalog summary:")
        print(f"   📍 Stations: {station_count}")
        print(f"   ⚓ Moorings: {mooring_count}")
        print(f"   🚢 Transits: {transit_count}")
        print(f"   📐 Areas: {area_count}")

        if hasattr(cruise.config, "departure_port") and cruise.config.departure_port:
            print(f"   🚢 Departure: {cruise.config.departure_port.name}")
        if hasattr(cruise.config, "arrival_port") and cruise.config.arrival_port:
            print(f"   🏁 Arrival: {cruise.config.arrival_port.name}")

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
