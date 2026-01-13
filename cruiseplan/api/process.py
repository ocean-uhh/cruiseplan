"""
Cruise processing workflow API.

This module provides the main process() function that runs the complete
processing workflow: enrichment -> validation -> map generation.
"""

import logging
from pathlib import Path
from typing import Optional, Union

from cruiseplan.types import ProcessResult

logger = logging.getLogger(__name__)


def process(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    add_depths: bool = True,
    add_coords: bool = True,
    expand_sections: bool = True,
    run_validation: bool = True,
    run_map_generation: bool = True,
    depth_check: bool = True,
    tolerance: float = 10.0,
    format: str = "all",
    bathy_stride: int = 10,
    figsize: Optional[list] = None,
    no_port_map: bool = False,
    verbose: bool = False,
) -> ProcessResult:
    """
    Process cruise configuration with unified workflow (mirrors: cruiseplan process).

    This function runs the complete processing workflow: enrichment -> validation -> map generation.

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    output_dir : str
        Output directory for generated files (default: "data")
    output : str, optional
        Base filename for outputs (default: use cruise name from config)
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    add_depths : bool
        Add missing depth values to stations using bathymetry data (default: True)
    add_coords : bool
        Add formatted coordinate fields (default: True)
    expand_sections : bool
        Expand CTD sections into individual station definitions (default: True)
    run_validation : bool
        Run validation step (default: True)
    run_map_generation : bool
        Generate maps after processing (default: True)
    depth_check : bool
        Compare existing depths with bathymetry data during validation (default: True)
    tolerance : float
        Depth difference tolerance in percent for validation (default: 10.0)
    format : str
        Map output formats: "png", "kml", or "all" (default: "all")
    bathy_stride : int
        Bathymetry contour stride for map generation (default: 10)
    figsize : list
        Figure size for PNG maps [width, height] (default: [12, 8])
    no_port_map : bool
        Skip plotting ports on generated maps (default: False)
    verbose : bool
        Enable verbose logging (default: False)

    Examples
    --------
    >>> import cruiseplan
    >>> # Process with default settings (full workflow)
    >>> config, files = cruiseplan.process(config_file="cruise.yaml")
    >>> print(f"Processed cruise: {config.cruise_name}")
    >>> print(f"Generated {len(files)} files: {[f.name for f in files]}")
    >>> # Use processed config for further analysis
    >>> print(f"Cruise has {len(config.stations)} stations")
    >>> # Find specific generated files
    >>> enriched_file = next(f for f in files if 'enriched' in f.name)
    >>> map_file = next((f for f in files if f.suffix == '.png'), None)
    """
    from cruiseplan.api.enrich import enrich
    from cruiseplan.api.map import map
    from cruiseplan.api.validate import validate
    from cruiseplan.init_utils import _setup_verbose_logging

    _setup_verbose_logging(verbose)

    if figsize is None:
        figsize = [12, 8]

    try:
        # Initialize with the original config file
        enriched_config_path = config_file
        generated_files = []

        # Step 1: Enrichment (optional - runs if any enrichment options are enabled)
        if add_depths or add_coords or expand_sections:
            logger.info("🔧 Enriching cruise configuration...")
            try:
                enrich_result = enrich(
                    config_file=config_file,
                    output_dir=output_dir,
                    output=output,
                    add_depths=add_depths,
                    add_coords=add_coords,
                    bathy_source=bathy_source,
                    bathy_dir=bathy_dir,
                    expand_sections=expand_sections,
                    verbose=verbose,
                )
                enriched_config_path = enrich_result.output_file
                generated_files.append(enriched_config_path)
            except Exception:
                logger.exception("❌ Enrichment failed")
                logger.info("💡 Try running validation only on your original config:")
                logger.info(f"   cruiseplan.validate(config_file='{config_file}')")
                logger.info("   Or use the CLI: cruiseplan validate {config_file}")
                raise

        # Step 2: Validation (optional)
        if run_validation:
            logger.info("✅ Validating cruise configuration...")
            is_valid = validate(
                config_file=enriched_config_path,  # Use enriched config if available
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                check_depths=depth_check,
                tolerance=tolerance,
                verbose=verbose,
            )
            if not is_valid:
                logger.warning("⚠️ Validation completed with warnings/errors")

        # Step 3: Map generation (optional)
        if run_map_generation:
            logger.info("🗺️ Generating cruise maps...")
            map_result = map(
                config_file=enriched_config_path,  # Use enriched config if available
                output_dir=output_dir,
                output=output,
                format=format,
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                bathy_stride=bathy_stride,
                figsize=figsize,
                no_ports=no_port_map,  # Pass through the no_port_map flag as no_ports
                verbose=verbose,
            )
            if map_result.map_files:
                generated_files.extend(map_result.map_files)

        # Load the final config object for return
        from cruiseplan.core.cruise import CruiseInstance

        cruise = CruiseInstance(enriched_config_path)

        logger.info("✅ Processing workflow completed successfully!")

        # Create structured result
        summary = {
            "config_file": str(config_file),
            "files_generated": len(generated_files),
            "enrichment_run": add_depths or add_coords,
            "validation_run": run_validation,
            "map_generation_run": run_map_generation,
        }

        return ProcessResult(
            config=cruise.config, files_created=generated_files, summary=summary
        )

    except Exception as e:
        from cruiseplan.init_utils import _handle_error_with_logging

        _handle_error_with_logging(e, "Processing failed", verbose)
        raise