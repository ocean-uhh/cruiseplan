"""
Cruise schedule generation API.

This module provides the main schedule() function that generates cruise timelines
and various output formats (HTML, CSV, NetCDF, PNG, LaTeX).
"""

import logging
from pathlib import Path
from typing import Optional, Union

from cruiseplan.exceptions import FileError, ValidationError
from cruiseplan.types import ScheduleResult

logger = logging.getLogger(__name__)


def schedule(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    format: Optional[str] = "all",
    leg: Optional[str] = None,
    derive_netcdf: bool = False,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    bathy_stride: int = 10,
    figsize: Optional[list] = None,
    verbose: bool = False,
) -> ScheduleResult:
    """
    Generate cruise schedule (mirrors: cruiseplan schedule).

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    output_dir : str
        Output directory for schedule files (default: "data")
    output : str, optional
        Base filename for outputs (default: use cruise name from config)
    format : str or None
        Output formats: "html", "latex", "csv", "kml", "netcdf", "png", "all", or None (default: "all").
        If None, only computes timeline without generating files.
    leg : str, optional
        Process specific leg only (default: process all legs)
    derive_netcdf : bool
        Generate specialized NetCDF files (_points.nc, _lines.nc, _areas.nc) (default: False)
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    bathy_stride : int
        Bathymetry contour stride for PNG maps (default: 10)
    figsize : list
        Figure size for PNG maps [width, height] (default: [12, 8])
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    ScheduleResult
        Structured result containing timeline, generated files, and summary information.
        Timeline contains computed schedule data for programmatic use.
        Files list contains paths to all generated files (HTML, CSV, NetCDF, etc.).
        Summary contains metadata about the generation process.

    Examples
    --------
    >>> import cruiseplan
    >>> # Generate all formats and get timeline for analysis
    >>> result = cruiseplan.schedule(config_file="cruise.yaml", format="all")
    >>> print(f"Generated files: {result.files_created}")
    >>> print(f"Timeline has {len(result.timeline)} activities")
    >>>
    >>> # Find specific file type from generated files
    >>> netcdf_file = next(f for f in result.files_created if f.suffix == '.nc')
    >>> html_file = next(f for f in result.files_created if f.suffix == '.html')
    >>>
    >>> # Get only timeline data without generating files
    >>> result = cruiseplan.schedule(config_file="cruise.yaml", format=None)
    >>> for activity in result.timeline:
    ...     print(f"{activity['label']}: {activity['start_time']} -> {activity['end_time']}")
    >>>
    >>> # Load NetCDF file with xarray
    >>> result = cruiseplan.schedule(config_file="cruise.yaml", format="netcdf")
    >>> netcdf_file = result.files_created[0]  # NetCDF file
    >>> import xarray as xr
    >>> ds = xr.open_dataset(netcdf_file)
    """
    from cruiseplan.calculators.scheduler import generate_timeline
    from cruiseplan.core.cruise import CruiseInstance
    from cruiseplan.init_utils import _parse_schedule_formats, _setup_verbose_logging

    _setup_verbose_logging(verbose)

    if figsize is None:
        figsize = [12, 8]

    # Validate input file path using centralized utility
    from cruiseplan.utils.io import validate_input_file

    try:
        config_path = validate_input_file(config_file)
    except ValueError as e:
        raise FileError(str(e))

    logger.info(f"📅 Generating schedule from {config_path}")

    try:
        # Load and validate cruise configuration
        cruise = CruiseInstance(config_path)

        # Handle specific leg processing if requested
        target_legs = cruise.runtime_legs
        if leg:
            target_legs = [
                runtime_leg
                for runtime_leg in cruise.runtime_legs
                if runtime_leg.name == leg
            ]
            if not target_legs:
                logger.error(f"Leg '{leg}' not found in cruise configuration")
                raise ValidationError(f"Leg '{leg}' not found in cruise configuration")
            logger.info(f"Processing specific leg: {leg}")

        if not target_legs:
            logger.error("No legs found in cruise configuration")
            raise ValidationError("No legs found in cruise configuration")

        # Generate timeline for specified legs
        timeline = generate_timeline(cruise)

        if not timeline:
            logger.error("Failed to generate timeline")
            raise RuntimeError("Failed to generate timeline")

        # Handle format=None case (timeline only)
        if format is None:
            logger.info("📊 Computing timeline only (no file output)")
            return ScheduleResult(
                timeline=timeline,
                files_created=[],
                summary={"activities": len(timeline), "files_generated": 0},
            )

        # Setup output paths using helper function
        from cruiseplan.utils.io import setup_output_paths

        output_dir_path, base_name = setup_output_paths(config_file, output_dir, output)

        # Parse format list
        formats = _parse_schedule_formats(format, derive_netcdf)

        # Import generator helpers
        from cruiseplan.init_utils import (
            generate_csv_format,
            generate_html_format,
            generate_latex_format,
            generate_netcdf_format,
            generate_png_format,
            generate_specialized_netcdf,
        )

        generated_files = []

        # Generate each requested format
        for fmt in formats:
            if fmt == "html":
                output_file = generate_html_format(
                    cruise.config, timeline, output_dir_path, base_name
                )
                if output_file:
                    generated_files.append(output_file)

            elif fmt == "latex":
                output_file = generate_latex_format(
                    cruise.config, timeline, output_dir_path, base_name
                )
                if output_file:
                    generated_files.append(output_file)

            elif fmt == "csv":
                output_file = generate_csv_format(
                    cruise.config, timeline, output_dir_path, base_name
                )
                if output_file:
                    generated_files.append(output_file)

            elif fmt == "netcdf":
                output_file = generate_netcdf_format(
                    cruise.config, timeline, output_dir_path, base_name
                )
                if output_file:
                    generated_files.append(output_file)

            elif fmt == "netcdf_specialized" and derive_netcdf:
                specialized_files = generate_specialized_netcdf(
                    cruise.config, timeline, output_dir_path
                )
                generated_files.extend(specialized_files)

            elif fmt == "png":
                output_file = generate_png_format(
                    cruise,
                    timeline,
                    output_dir_path,
                    base_name,
                    bathy_source,
                    bathy_dir,
                    bathy_stride,
                    tuple(figsize) if isinstance(figsize, list) else figsize,
                    suffix="schedule",
                )
                if output_file:
                    generated_files.append(output_file)

            else:
                logger.warning(
                    f"Format '{fmt}' not supported or generator not available"
                )

        if generated_files:
            logger.info(
                f"📅 Schedule generation complete! Generated {len(generated_files)} files"
            )
            return ScheduleResult(
                timeline=timeline,
                files_created=generated_files,
                summary={
                    "activities": len(timeline),
                    "files_generated": len(generated_files),
                    "formats": list(formats),
                    "leg": leg,
                },
            )
        else:
            logger.error("No schedule files were generated")
            raise RuntimeError(
                "Schedule generation failed: No output files were created"
            )

    except Exception:
        logger.exception("❌ Schedule generation failed")
        if verbose:
            import traceback

            traceback.print_exc()
        raise  # Re-raise the exception so caller knows it failed
