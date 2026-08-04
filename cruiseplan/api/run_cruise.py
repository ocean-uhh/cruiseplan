"""
Full pipeline API: process then schedule in a single call.

This module provides the run() function that chains the process and schedule
steps, passing the enriched YAML output from process as input to schedule.
Enrichment runs once; both steps work from the same config.
"""

from pathlib import Path

from cruiseplan.api.process_cruise import process
from cruiseplan.api.schedule_cruise import schedule
from cruiseplan.api.types import ProcessResult, ScheduleResult


def run(
    config_file: str | Path,
    output_dir: str = "data",
    leg: str | None = None,
    bathy_source: str = "gebco2025",
    bathy_dir: str = "data/bathymetry",
    bathy_stride: int = 10,
    bathy_contours: list | None = None,
    lat_bounds: list | None = None,
    lon_bounds: list | None = None,
    figsize: list | None = None,
    no_ports: bool = False,
    no_title: bool = False,
    no_labels: bool = False,
    no_legend: bool = False,
    verbose: bool = False,
    max_depth: int | None = None,
    include_eez: bool = False,
) -> tuple[ProcessResult, ScheduleResult]:
    """
    Run the full cruise planning pipeline: process then schedule.

    Calls process() to enrich, validate, and map, then passes the enriched
    YAML directly to schedule(). Enrichment runs once; both steps use the
    same config. Raises RuntimeError if the process step fails.

    Parameters
    ----------
    config_file : str or Path
        Input YAML cruise configuration file
    output_dir : str, optional
        Output directory for all generated files (default: "data")
    leg : str or None, optional
        Specific leg name to schedule; if None, all legs are scheduled
    bathy_source : str, optional
        Bathymetry dataset: "gebco2025" or "etopo2022" (default: "gebco2025")
    bathy_dir : str, optional
        Directory containing bathymetry files (default: "data/bathymetry")
    bathy_stride : int, optional
        Bathymetry grid downsampling factor; higher is faster (default: 10)
    bathy_contours : list or None, optional
        Depth contour levels in metres for PNG maps; None uses defaults
    lat_bounds : list or None, optional
        [min_lat, max_lat] for map extent; None auto-fits
    lon_bounds : list or None, optional
        [min_lon, max_lon] for map extent; None auto-fits
    figsize : list or None, optional
        [width, height] in inches for PNG maps; None uses defaults
    no_ports : bool, optional
        Exclude ports from PNG maps (default: False)
    no_title : bool, optional
        Omit title from PNG maps (default: False)
    no_labels : bool, optional
        Omit station name labels from PNG maps (default: False)
    no_legend : bool, optional
        Omit legend from PNG maps (default: False)
    verbose : bool, optional
        Enable verbose logging (default: False)
    max_depth : int or None, optional
        Maximum depth in metres for bathymetry colour scale; None auto-scales
    include_eez : bool, optional
        Overlay EEZ boundaries on PNG maps (default: False)

    Returns
    -------
    tuple[ProcessResult, ScheduleResult]
        Results from both pipeline steps. process_result.config is the path
        to the enriched YAML; schedule_result.timeline is the CruiseSchedule.

    Raises
    ------
    RuntimeError
        If the process step fails (process_result.config is None).

    Examples
    --------
    >>> process_result, schedule_result = cruiseplan.run("cruise.yaml")
    >>> print(f"Enriched: {process_result.config}")
    >>> print(f"Schedule activities: {len(schedule_result.timeline)}")
    """
    shared = dict(
        output_dir=output_dir,
        bathy_source=bathy_source,
        bathy_dir=bathy_dir,
        bathy_stride=bathy_stride,
        bathy_contours=bathy_contours,
        lat_bounds=lat_bounds,
        lon_bounds=lon_bounds,
        figsize=figsize,
        no_ports=no_ports,
        no_title=no_title,
        no_labels=no_labels,
        no_legend=no_legend,
        verbose=verbose,
        max_depth=max_depth,
        include_eez=include_eez,
    )

    process_result = process(config_file=config_file, **shared)

    if process_result.config is None:
        raise RuntimeError(f"Process step failed for {config_file}; schedule not run.")

    schedule_result = schedule(
        config_file=process_result.config,
        leg=leg,
        **shared,
    )

    return process_result, schedule_result
