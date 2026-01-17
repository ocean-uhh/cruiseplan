"""
Cruise map generation API.

This module provides the main map() function that generates cruise track maps
in various formats (PNG, KML).
"""

import logging
from pathlib import Path
from typing import Optional, Union

from cruiseplan.types import MapResult

logger = logging.getLogger(__name__)


def map(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    format: str = "all",
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data",
    bathy_stride: int = 5,
    figsize: Optional[list] = None,
    show_plot: bool = False,
    no_ports: bool = False,
    verbose: bool = False,
) -> MapResult:
    """
    Generate cruise track map (mirrors: cruiseplan map).

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    output_dir : str
        Output directory for map files (default: "data")
    output : str, optional
        Base filename for output maps (default: use config filename)
    format : str
        Map output format: "png", "kml", or "all" (default: "all")
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    bathy_stride : int
        Bathymetry contour stride for map background (default: 5)
    figsize : list
        Figure size for PNG maps [width, height] (default: [12, 8])
    show_plot : bool
        Display plot interactively (default: False)
    no_ports : bool
        Suppress plotting of departure and arrival ports (default: False)
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    MapResult
        Structured result containing generated map files and summary information.

    Examples
    --------
    >>> import cruiseplan
    >>> # Generate PNG map
    >>> cruiseplan.map(config_file="cruise.yaml")
    >>> # Generate KML map with custom size
    >>> cruiseplan.map(config_file="cruise.yaml", format="kml", figsize=[16, 10])
    """
    from cruiseplan.core.cruise import CruiseInstance
    from cruiseplan.init_utils import _parse_map_formats, _setup_verbose_logging
    from cruiseplan.output.kml_generator import generate_kml_catalog
    from cruiseplan.output.map_generator import generate_map

    _setup_verbose_logging(verbose)

    if figsize is None:
        figsize = [12, 8]

    try:
        # Load cruise configuration - direct core call
        cruise = CruiseInstance(Path(config_file))

        # Setup output paths using helper function
        from cruiseplan.utils.io import setup_output_paths

        output_path, base_name = setup_output_paths(config_file, output_dir, output)

        # Parse formats to generate
        formats = _parse_map_formats(format)

        generated_files = []

        # Generate maps based on format - direct core calls
        if "png" in formats:
            png_file = output_path / f"{base_name}_map.png"
            result = generate_map(
                data_source=cruise,
                source_type="cruise",
                output_file=png_file,
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                bathy_stride=bathy_stride,
                figsize=tuple(figsize),
                show_plot=show_plot,
                include_ports=not no_ports,  # Convert no_ports to include_ports
            )
            if result:
                generated_files.append(result)

        if "kml" in formats:
            kml_file = output_path / f"{base_name}_catalog.kml"
            generate_kml_catalog(cruise.config, kml_file)
            generated_files.append(kml_file)

        # Create structured result
        summary = {
            "config_file": str(config_file),
            "format": format,
            "files_generated": len(generated_files),
            "output_dir": str(output_path),
        }

        return MapResult(map_files=generated_files, format=format, summary=summary)

    except Exception as e:
        from cruiseplan.init_utils import _handle_error_with_logging

        _handle_error_with_logging(e, "Map generation failed", verbose)

        # Return failed result
        summary = {
            "config_file": str(config_file),
            "format": format,
            "files_generated": 0,
            "error": str(e),
        }

        return MapResult(map_files=[], format=format, summary=summary)
