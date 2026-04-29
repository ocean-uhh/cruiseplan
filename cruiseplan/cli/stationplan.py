"""
Station plan generation command.

This module implements the 'cruiseplan stationplan' command for listing
activities and generating station plan forecasts from NetCDF schedule files.

Thin CLI layer that delegates all business logic to the API layer.
"""

import argparse
import sys
from pathlib import Path

from cruiseplan.api.stationplan_api import stationplan_list, stationplan_forecast, stationplan_tex, stationplan_forecast_tex, stationplan_waypoints


def main(args: argparse.Namespace) -> None:
    """
    Thin CLI wrapper for stationplan command.
    
    Delegates all business logic to the cruiseplan.api.stationplan_api functions.
    
    Parameters
    ----------
    args : argparse.Namespace
        Parsed command-line arguments containing schedule file and operation mode.
    """
    try:
        # Validate schedule file exists
        schedule_file = Path(args.schedule)
        if not schedule_file.exists():
            print(f"❌ Schedule file not found: {schedule_file}", file=sys.stderr)
            sys.exit(1)
            
        # List mode
        if args.list:
            result = stationplan_list(schedule_file)
            
            if result.success:
                print(result.output)
            else:
                print(f"❌ {result.message}", file=sys.stderr)
                sys.exit(1)
        
        # Forecast mode with optional format
        elif args.start_index is not None and args.start_time is not None:
            # Check format type
            format_type = getattr(args, 'format', None)
            
            if format_type == 'tex':
                # Determine output path
                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output
                
                result = stationplan_forecast_tex(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    output_path=output_path
                )
                
                if result.success:
                    print(f"✅ Generated TeX forecast: {result.output}")
                else:
                    print(f"❌ {result.message}", file=sys.stderr)
                    sys.exit(1)
            
            elif format_type == 'waypoints':
                # Parse current position if provided
                current_position = None
                if hasattr(args, 'current_position') and args.current_position:
                    try:
                        lat_str, lon_str = args.current_position.split(',')
                        current_position = (float(lat_str.strip()), float(lon_str.strip()))
                    except (ValueError, AttributeError) as e:
                        print(f"❌ Invalid current position format. Use 'lat,lon' like '65.123,-30.456': {e}", file=sys.stderr)
                        sys.exit(1)
                
                # Determine output path
                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output
                
                result = stationplan_waypoints(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    current_position=current_position,
                    output_path=output_path
                )
                
                if result.success:
                    if output_path:
                        print(f"✅ Generated bridge waypoints: {result.output}")
                    else:
                        print(result.output)
                else:
                    print(f"❌ {result.message}", file=sys.stderr)
                    sys.exit(1)
            
            else:
                # Regular text forecast
                result = stationplan_forecast(
                    schedule_file=schedule_file,
                    start_index=args.start_index,
                    start_time=args.start_time,
                    duration_hours=args.duration,
                    transit_speed=args.transit_speed
                )
                
                if result.success:
                    # Handle output - either to file or stdout
                    if args.output:
                        output_path = args.output_dir / args.output
                        try:
                            with open(output_path, 'w') as f:
                                f.write(result.output)
                            print(f"✅ Forecast written to: {output_path}")
                        except Exception as e:
                            print(f"❌ Error writing to {output_path}: {e}", file=sys.stderr)
                            sys.exit(1)
                    else:
                        # Output to stdout
                        print(result.output)
                else:
                    print(f"❌ {result.message}", file=sys.stderr)
                    sys.exit(1)
                    
        # Format mode without forecast parameters
        elif getattr(args, 'format', None) in ['tex', 'waypoints']:
            format_type = getattr(args, 'format', None)
            
            if format_type == 'tex':
                # Determine output path
                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output
                
                result = stationplan_tex(schedule_file, output_path)
                
                if result.success:
                    print(f"✅ Generated TeX station table: {result.output}")
                else:
                    print(f"❌ {result.message}", file=sys.stderr)
                    sys.exit(1)
            
            elif format_type == 'waypoints':
                # Parse current position if provided
                current_position = None
                if hasattr(args, 'current_position') and args.current_position:
                    try:
                        lat_str, lon_str = args.current_position.split(',')
                        current_position = (float(lat_str.strip()), float(lon_str.strip()))
                    except (ValueError, AttributeError) as e:
                        print(f"❌ Invalid current position format. Use 'lat,lon' like '65.123,-30.456': {e}", file=sys.stderr)
                        sys.exit(1)
                
                # Determine output path
                output_path = None
                if args.output:
                    output_path = args.output_dir / args.output
                
                result = stationplan_waypoints(
                    schedule_file=schedule_file,
                    start_index=None,  # Defaults to 0 (full cruise)
                    start_time=None,  # Defaults to now
                    duration_hours=None,  # Will use default 48h
                    current_position=current_position,
                    output_path=output_path
                )
                
                if result.success:
                    if output_path:
                        print(f"✅ Generated bridge waypoints: {result.output}")
                    else:
                        print(result.output)
                else:
                    print(f"❌ {result.message}", file=sys.stderr)
                    sys.exit(1)
                
        # No valid mode specified
        else:
            print("❌ Must specify either --list or both --start-index and --start-time", file=sys.stderr)
            print("   Use 'cruiseplan stationplan --help' for usage information", file=sys.stderr)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)