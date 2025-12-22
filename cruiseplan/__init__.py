"""
CruisePlan: Oceanographic Research Cruise Planning System

This package provides tools for planning oceanographic research cruises,
including bathymetry data management, station planning, and schedule generation.

Notebook-Friendly API
=====================

For interactive use in Jupyter notebooks, use these simplified functions
that mirror the CLI commands:

    import cruiseplan

    # Download bathymetry data (mirrors: cruiseplan bathymetry)
    bathy_file = cruiseplan.bathymetry(bathy_source="etopo2022", output_dir="data/bathymetry")

    # Search PANGAEA database (mirrors: cruiseplan pangaea)
    stations, files = cruiseplan.pangaea("CTD", lat_bounds=[70, 80], lon_bounds=[-10, 10])

    # Process configuration workflow (mirrors: cruiseplan process)
    config, files = cruiseplan.process(config_file="cruise.yaml", add_depths=True, add_coords=True)

    # Validate configuration (mirrors: cruiseplan validate)
    is_valid = cruiseplan.validate(config_file="cruise.yaml")

    # Generate schedule (mirrors: cruiseplan schedule)
    timeline, files = cruiseplan.schedule(config_file="cruise.yaml", format="html")

For more advanced usage, import the underlying classes directly:

    from cruiseplan.data.bathymetry import BathymetryManager, download_bathymetry
    from cruiseplan.core.cruise import Cruise
    from cruiseplan.calculators.scheduler import generate_timeline
"""

import logging
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from cruiseplan.data.bathymetry import BathymetryManager, download_bathymetry

logger = logging.getLogger(__name__)


def _setup_output_paths(
    config_file: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    output: Optional[str] = None,
) -> Tuple[Path, str]:
    """
    Internal helper function to setup output directory and base filename.

    Parameters
    ----------
    config_file : str or Path
        Path to the configuration file
    output_dir : str or Path, optional
        Output directory (default: "data")
    output : str, optional
        Base filename for outputs (default: extracted from config_file)

    Returns
    -------
    tuple[Path, str]
        Tuple of (output_directory, base_filename)
    """
    # Handle config file path
    config_path = Path(config_file)

    # Setup output directory
    if output_dir is None:
        output_dir_path = Path("data")
    else:
        output_dir_path = Path(output_dir)

    # Resolve to absolute path and create directory
    output_dir_path = output_dir_path.resolve()
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Setup base filename
    if output is None:
        base_name = config_path.stem
    else:
        base_name = output

    return output_dir_path, base_name


def bathymetry(
    bathy_source: str = "etopo2022", output_dir: str = None, citation: bool = False
) -> Path:
    """
    Download bathymetry data (mirrors: cruiseplan bathymetry).

    Parameters
    ----------
    bathy_source : str
        Bathymetry dataset to download ("etopo2022" or "gebco2025")
    output_dir : str, optional
        Output directory for bathymetry files (default: "data/bathymetry" relative to project root)
    citation : bool
        Show citation information for the bathymetry source (default: False)

    Returns
    -------
    Path
        Path to downloaded bathymetry file

    Examples
    --------
    >>> import cruiseplan
    >>> # Download ETOPO2022 data to project root data/bathymetry/
    >>> cruiseplan.bathymetry()
    >>> # Download GEBCO2025 data to custom location
    >>> cruiseplan.bathymetry(bathy_source="gebco2025", output_dir="my_data/bathymetry")
    """
    # Use default path relative to project root if none provided
    if output_dir is None:
        # Find project root (directory containing cruiseplan package)
        package_dir = Path(__file__).parent.parent  # Go up from cruiseplan/__init__.py
        output_dir = package_dir / "data" / "bathymetry"
    else:
        output_dir = Path(output_dir)

    data_dir = Path(output_dir).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"=� Downloading {bathy_source} bathymetry data to {data_dir}")
    return download_bathymetry(target_dir=str(data_dir), source=bathy_source)


def pangaea(
    query_terms: str,
    output_dir: str = "data",
    output: Optional[str] = None,
    lat_bounds: Optional[List[float]] = None,
    lon_bounds: Optional[List[float]] = None,
    max_results: int = 100,
    rate_limit: float = 1.0,
    merge_campaigns: bool = True,
    verbose: bool = False,
) -> Tuple[Optional[Any], Optional[List[Path]]]:
    """
    Search and download PANGAEA oceanographic data (mirrors: cruiseplan pangaea).

    Parameters
    ----------
    query_terms : str
        Search terms for PANGAEA database
    output_dir : str
        Output directory for station files (default: "data")
    output : str, optional
        Base filename for outputs (default: derived from query)
    lat_bounds : List[float], optional
        Latitude bounds [min_lat, max_lat]
    lon_bounds : List[float], optional
        Longitude bounds [min_lon, max_lon]
    max_results : int
        Maximum number of results to process (default: 100)
    rate_limit : float
        API request rate limit in requests per second (default: 1.0)
    merge_campaigns : bool
        Merge campaigns with the same name (default: True)
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    tuple[Optional[object], Optional[List[Path]]]
        Tuple of (pangaea_stations_data, list_of_generated_files).
        Stations data is None if search failed, file list is None if no files generated.
        Stations data contains the loaded PANGAEA campaign data for analysis.
        File list contains paths to all generated files (DOI list, stations pickle).

    Examples
    --------
    >>> import cruiseplan
    >>> # Search for CTD data in Arctic
    >>> stations, files = cruiseplan.pangaea("CTD", lat_bounds=[70, 80], lon_bounds=[-10, 10])
    >>> print(f"Found {len(stations)} campaigns in {len(files)} files")
    >>> # Search with custom output directory and filename
    >>> stations, files = cruiseplan.pangaea("temperature", output_dir="pangaea_data", output="arctic_temp")
    >>> # Access the data directly
    >>> for campaign in stations:
    ...     print(f"Campaign: {campaign['Campaign']}, Stations: {len(campaign['Stations'])}")
    """
    import re

    from cruiseplan.cli.pangaea import (
        fetch_pangaea_data,
        save_pangaea_pickle,
        search_pangaea_datasets,
        validate_dois,
    )

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    try:
        # Validate lat/lon bounds if provided
        if lat_bounds or lon_bounds:
            if not (lat_bounds and lon_bounds):
                logger.error(
                    "Both lat_bounds and lon_bounds must be provided for geographic search"
                )
                return None

            # Validate bounds format (similar to CLI validation)
            if len(lat_bounds) != 2 or len(lon_bounds) != 2:
                logger.error(
                    "lat_bounds and lon_bounds must each contain exactly 2 values [min, max]"
                )
                return None

            bbox = (
                lon_bounds[0],
                lat_bounds[0],
                lon_bounds[1],
                lat_bounds[1],
            )  # (min_lon, min_lat, max_lon, max_lat)
        else:
            bbox = None

        # Setup output paths
        output_dir_path = Path(output_dir).resolve()
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # Generate base filename if not provided (similar to CLI logic)
        if not output:
            safe_query = "".join(c if c.isalnum() else "_" for c in query_terms)
            safe_query = re.sub(r"_+", "_", safe_query).strip("_")
            base_name = safe_query
        else:
            base_name = output

        # Define output files
        dois_file = output_dir_path / f"{base_name}_dois.txt"
        stations_file = output_dir_path / f"{base_name}_stations.pkl"
        generated_files = []

        # Search PANGAEA database
        logger.info(f"🔍 Searching PANGAEA for: '{query_terms}'")
        if bbox:
            logger.info(f"📍 Geographic bounds: lat {lat_bounds}, lon {lon_bounds}")

        dois = search_pangaea_datasets(query=query_terms, bbox=bbox, limit=max_results)

        if not dois:
            logger.warning("❌ No DOIs found. Try broadening your search criteria.")
            return None, None

        logger.info(f"✅ Found {len(dois)} datasets")

        # Save DOI list (intermediate file)
        with open(dois_file, "w") as f:
            for doi in dois:
                f.write(f"{doi}\n")
        generated_files.append(dois_file)

        logger.info(f"📂 DOI file: {dois_file}")
        logger.info(f"📂 Stations file: {stations_file}")

        # Validate and process DOIs
        logger.info(f"⚙️ Processing {len(dois)} DOIs...")
        logger.info(f"🕐 Rate limit: {rate_limit} requests/second")

        valid_dois = validate_dois(dois)

        # Fetch PANGAEA data with proper rate limiting
        datasets = fetch_pangaea_data(
            valid_dois, rate_limit=rate_limit, merge_campaigns=merge_campaigns
        )

        if not datasets:
            logger.warning(
                "⚠️ No datasets retrieved. Check DOI list and network connection."
            )
            return None, generated_files

        # Save results using CLI function
        save_pangaea_pickle(datasets, stations_file, len(valid_dois))
        generated_files.append(stations_file)

        logger.info("✅ PANGAEA processing completed successfully!")
        logger.info(f"🚀 Next step: cruiseplan stations -p {stations_file}")

        return datasets, generated_files

    except Exception as e:
        logger.error(f"❌ PANGAEA search failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return None, None


def enrich(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    add_depths: bool = True,
    add_coords: bool = True,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    coord_format: str = "ddm",
    expand_sections: bool = True,
    expand_ports: bool = True,
    verbose: bool = False,
) -> Path:
    """
    Enrich a cruise configuration file (mirrors: cruiseplan enrich).

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    output_dir : str
        Output directory for enriched file (default: "data")
    output : str, optional
        Base filename for output (default: use input filename)
    add_depths : bool
        Add missing depth values to stations using bathymetry data (default: True)
    add_coords : bool
        Add formatted coordinate fields (default: True)
    expand_sections : bool
        Expand CTD sections into individual station definitions (default: True)
    expand_ports : bool
        Expand global port references (default: True)

    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    coord_format : str
        Coordinate format (default: "ddm")
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    Path
        Path to enriched output file

    Examples
    --------
    >>> import cruiseplan
    >>> # Add depths and coordinates to cruise.yaml
    >>> cruiseplan.enrich(config_file="cruise.yaml", add_depths=True, add_coords=True)
    >>> # Enrich and save to custom output directory
    >>> cruiseplan.enrich(config_file="cruise.yaml", output_dir="enriched", add_depths=True)
    >>> # Enrich with custom filename but note output will be "enhanced_cruise_enriched.yaml"
    >>> cruiseplan.enrich(config_file="cruise.yaml", output="enhanced_cruise", add_depths=True)
    """
    from cruiseplan.core.validation import enrich_configuration

    config_path = Path(config_file).resolve()

    # Setup output paths using helper function
    from cruiseplan.utils.config import setup_output_paths

    output_dir_path, base_name = setup_output_paths(config_file, output_dir, output)

    # Determine final output file path - CLI behavior is to append "_enriched"
    # Always append "_enriched" to maintain consistency with CLI and other commands
    output_path = output_dir_path / f"{base_name}_enriched.yaml"

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    logger.info(f"🔧 Enriching {config_path}")
    logger.info(f"📁 Output will be saved to: {output_path}")

    enrich_configuration(
        config_path,
        output_path=output_path,
        add_depths=add_depths,
        add_coords=add_coords,
        expand_sections=expand_sections,
        expand_ports=expand_ports,
        bathymetry_source=bathy_source,
        bathymetry_dir=bathy_dir,
        coord_format=coord_format,
    )

    return output_path


def validate(
    config_file: Union[str, Path],
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    check_depths: bool = True,
    tolerance: float = 10.0,
    strict: bool = False,
    warnings_only: bool = False,
    verbose: bool = False,
) -> bool:
    """
    Validate a cruise configuration file (mirrors: cruiseplan validate).

    Parameters
    ----------
    config_file : str or Path
        Input YAML configuration file
    bathy_source : str
        Bathymetry dataset (default: "etopo2022")
    bathy_dir : str
        Directory containing bathymetry data (default: "data")
    check_depths : bool
        Compare existing depths with bathymetry data (default: True)
    tolerance : float
        Depth difference tolerance in percent (default: 10.0)
    strict : bool
        Enable strict validation mode (default: False)
    warnings_only : bool
        Show warnings without failing - warnings don't affect return value (default: False)
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    bool
        True if validation passed (no errors), False if errors found.
        When warnings_only=True, warnings don't affect the result.

    Examples
    --------
    >>> import cruiseplan
    >>> # Validate cruise configuration with depth checking
    >>> is_valid = cruiseplan.validate(config_file="cruise.yaml", check_depths=True)
    >>> # Strict validation with custom tolerance
    >>> is_valid = cruiseplan.validate(config_file="cruise.yaml", strict=True, tolerance=5.0)
    >>> if is_valid:
    ...     print(" Configuration is valid")
    """
    from cruiseplan.core.validation import validate_configuration_file

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    config_path = Path(config_file).resolve()
    logger.info(f" Validating {config_path}")

    try:
        success, errors, warnings = validate_configuration_file(
            config_path=config_path,
            check_depths=check_depths,
            tolerance=tolerance,
            bathymetry_source=bathy_source,
            bathymetry_dir=bathy_dir,
            strict=strict,
        )

        # Report results (similar to CLI)
        if errors:
            logger.error("❌ Validation Errors:")
            for error in errors:
                logger.error(f"  • {error}")

        if warnings:
            logger.warning("⚠️ Validation Warnings:")
            for warning in warnings:
                logger.warning(f"  • {warning}")

        if success:
            logger.info("✅ Validation passed")

        return success

    except Exception as e:
        logger.error(f"L Validation failed: {e}")
        return False


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
    figsize: list = [12, 8],
    verbose: bool = False,
) -> Tuple[Optional[List[Any]], Optional[List[Path]]]:
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
    tuple[Optional[Timeline], Optional[List[Path]]]
        Tuple of (timeline_object, list_of_generated_files).
        Timeline is None if generation failed, file list is None if no files generated.
        Timeline contains computed schedule data for programmatic use.
        File list contains paths to all generated files (HTML, CSV, NetCDF, etc.).

    Examples
    --------
    >>> import cruiseplan
    >>> # Generate all formats and get timeline for analysis
    >>> timeline, files = cruiseplan.schedule(config_file="cruise.yaml", format="all")
    >>> print(f"Generated files: {files}")
    >>> print(f"Timeline has {len(timeline)} activities")
    >>>
    >>> # Find specific file type from generated files
    >>> netcdf_file = next(f for f in files if f.suffix == '.nc')
    >>> html_file = next(f for f in files if f.suffix == '.html')
    >>>
    >>> # Get only timeline data without generating files
    >>> timeline, _ = cruiseplan.schedule(config_file="cruise.yaml", format=None)
    >>> for activity in timeline:
    ...     print(f"{activity['label']}: {activity['start_time']} -> {activity['end_time']}")
    >>>
    >>> # Load NetCDF file with xarray
    >>> timeline, files = cruiseplan.schedule(config_file="cruise.yaml", format="netcdf")
    >>> netcdf_file = files[0]  # NetCDF file
    >>> import xarray as xr
    >>> ds = xr.open_dataset(netcdf_file)
    """
    from cruiseplan.calculators.scheduler import generate_timeline
    from cruiseplan.core.cruise import Cruise

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    config_path = Path(config_file).resolve()
    logger.info(f"📅 Generating schedule from {config_path}")

    try:
        # Load and validate cruise configuration
        cruise = Cruise(config_path)

        # Handle specific leg processing if requested
        target_legs = cruise.runtime_legs
        if leg:
            target_legs = [l for l in cruise.runtime_legs if l.name == leg]
            if not target_legs:
                logger.error(f"Leg '{leg}' not found in cruise configuration")
                return None, None
            logger.info(f"Processing specific leg: {leg}")

        if not target_legs:
            logger.error("No legs found in cruise configuration")
            return None, None

        # Generate timeline (use first leg for now - extend for multi-leg support later)
        timeline = generate_timeline(cruise.config, target_legs[0])

        if not timeline:
            logger.error("Failed to generate timeline")
            return None, None

        # Handle format=None case (timeline only)
        if format is None:
            logger.info("📊 Computing timeline only (no file output)")
            return timeline, None

        # Setup output paths using helper function
        from cruiseplan.utils.config import setup_output_paths

        output_dir_path, base_name = setup_output_paths(config_file, output_dir, output)

        # Parse format list
        formats = []
        if format == "all":
            formats = ["html", "latex", "csv", "netcdf", "png"]
            if derive_netcdf:
                formats.append("netcdf_specialized")
        else:
            formats = [fmt.strip() for fmt in format.split(",")]

        generated_files = []

        # Generate each requested format
        for fmt in formats:
            if fmt == "html":
                output_path = output_dir_path / f"{base_name}_schedule.html"
                from cruiseplan.output.html_generator import generate_html_schedule

                generate_html_schedule(cruise.config, timeline, output_path)
                generated_files.append(output_path)
                logger.info(f"✅ Generated HTML schedule: {output_path}")

            elif fmt == "latex":
                from cruiseplan.output.latex_generator import generate_latex_tables

                latex_files = generate_latex_tables(
                    cruise.config, timeline, output_dir_path
                )
                output_path = (
                    latex_files[0]
                    if latex_files
                    else output_dir_path / f"{base_name}_schedule.tex"
                )
                generated_files.append(output_path)
                logger.info(f"✅ Generated LaTeX schedule: {output_path}")

            elif fmt == "csv":
                output_path = output_dir_path / f"{base_name}_schedule.csv"
                from cruiseplan.output.csv_generator import generate_csv_schedule

                generate_csv_schedule(cruise.config, timeline, output_path)
                generated_files.append(output_path)
                logger.info(f"✅ Generated CSV schedule: {output_path}")

            elif fmt == "netcdf":
                output_path = output_dir_path / f"{base_name}_schedule.nc"
                from cruiseplan.output.netcdf_generator import NetCDFGenerator

                logger.info(
                    f"📄 NetCDF Generator: Starting generation of {output_path}"
                )
                logger.info(f"   Timeline contains {len(timeline)} activities")
                generator = NetCDFGenerator()
                generator.generate_ship_schedule(timeline, cruise.config, output_path)
                generated_files.append(output_path)
                logger.info(f"✅ Generated NetCDF schedule: {output_path}")

            elif fmt == "netcdf_specialized" and derive_netcdf:
                from cruiseplan.output.netcdf_generator import NetCDFGenerator

                generator = NetCDFGenerator()
                specialized_files = generator.generate_all_netcdf_outputs(
                    cruise.config, output_dir_path, base_name
                )
                generated_files.extend(specialized_files)
                logger.info(
                    f"✅ Generated specialized NetCDF files: {len(specialized_files)} files"
                )

            elif fmt == "png":
                output_path = output_dir_path / f"{base_name}_map.png"
                from cruiseplan.output.map_generator import generate_map_from_timeline

                logger.info(
                    f"🗺️ PNG Map Generator: Starting generation of {output_path}"
                )
                map_file = generate_map_from_timeline(
                    timeline=timeline,
                    output_file=output_path,
                    bathy_source=bathy_source,
                    bathy_dir=bathy_dir,
                    bathy_stride=bathy_stride,
                    figsize=tuple(figsize) if isinstance(figsize, list) else figsize,
                    config=cruise,
                )
                if map_file:
                    generated_files.append(map_file)
                    logger.info(f"✅ Generated PNG map: {map_file}")
                else:
                    logger.warning("PNG map generation failed")

            else:
                logger.warning(
                    f"Format '{fmt}' not supported or generator not available"
                )

        if generated_files:
            logger.info(
                f"📅 Schedule generation complete! Generated {len(generated_files)} files"
            )
            return (
                timeline,
                generated_files,
            )  # Return timeline and list of all generated files
        else:
            logger.error("No schedule files were generated")
            raise RuntimeError(
                "Schedule generation failed: No output files were created"
            )

    except Exception as e:
        logger.error(f"❌ Schedule generation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise  # Re-raise the exception so caller knows it failed


def process(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data/bathymetry",
    add_depths: bool = True,
    add_coords: bool = True,
    expand_sections: bool = True,
    expand_ports: bool = True,
    run_validation: bool = True,
    run_map_generation: bool = True,
    depth_check: bool = True,
    tolerance: float = 10.0,
    format: str = "all",
    bathy_stride: int = 10,
    figsize: list = [12, 8],
    verbose: bool = False,
) -> Tuple[Optional[Any], Optional[List[Path]]]:
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
    expand_ports : bool
        Expand global port references (default: True)
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
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    try:
        # Initialize with the original config file
        enriched_config_path = config_file
        generated_files = []

        # Step 1: Enrichment (optional - runs if any enrichment options are enabled)
        if add_depths or add_coords or expand_sections or expand_ports:
            logger.info("🔧 Enriching cruise configuration...")
            try:
                enriched_config_path = enrich(
                    config_file=config_file,
                    output_dir=output_dir,
                    output=output,
                    add_depths=add_depths,
                    add_coords=add_coords,
                    bathy_source=bathy_source,
                    bathy_dir=bathy_dir,
                    expand_sections=expand_sections,
                    expand_ports=expand_ports,
                    verbose=verbose,
                )
                generated_files.append(enriched_config_path)
            except Exception as e:
                logger.error(f"❌ Enrichment failed: {e}")
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
            map_file = map(
                config_file=enriched_config_path,  # Use enriched config if available
                output_dir=output_dir,
                output=output,
                format=format,
                bathy_source=bathy_source,
                bathy_dir=bathy_dir,
                bathy_stride=bathy_stride,
                figsize=figsize,
                verbose=verbose,
            )
            if map_file:
                generated_files.append(map_file)

        # Load the final config object for return
        from cruiseplan.core.cruise import Cruise

        cruise = Cruise(enriched_config_path)

        logger.info("✅ Processing workflow completed successfully!")
        return cruise.config, generated_files

    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        raise


def map(
    config_file: Union[str, Path],
    output_dir: str = "data",
    output: Optional[str] = None,
    format: str = "all",
    bathy_source: str = "etopo2022",
    bathy_dir: str = "data",
    bathy_stride: int = 5,
    figsize: list = [12, 8],
    show_plot: bool = False,
    verbose: bool = False,
) -> Optional[Path]:
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
    verbose : bool
        Enable verbose logging (default: False)

    Returns
    -------
    Path or None
        Path to generated map file, or None if generation failed

    Examples
    --------
    >>> import cruiseplan
    >>> # Generate PNG map
    >>> cruiseplan.map(config_file="cruise.yaml")
    >>> # Generate KML map with custom size
    >>> cruiseplan.map(config_file="cruise.yaml", format="kml", figsize=[16, 10])
    """
    from cruiseplan.core.cruise import Cruise
    from cruiseplan.output.kml_generator import generate_kml_catalog
    from cruiseplan.output.map_generator import generate_map

    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    try:
        # Load cruise configuration - direct core call
        cruise = Cruise(Path(config_file))

        # Setup output paths using helper function
        from cruiseplan.utils.config import setup_output_paths

        output_path, base_name = setup_output_paths(config_file, output_dir, output)

        # Generate maps based on format - direct core calls
        if format == "png" or format == "all":
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
            )

            if format == "png":
                return result

        if format == "kml" or format == "all":
            kml_file = output_path / f"{base_name}_catalog.kml"
            generate_kml_catalog(cruise.config, kml_file)

            if format == "kml":
                return kml_file

        # If "all" format, return PNG file path
        if format == "all":
            return output_path / f"{base_name}_map.png"

        return None

    except Exception as e:
        logger.error(f"Map generation failed: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return None
