"""
Bathymetry data download command.

This module implements the 'cruiseplan bathymetry' command for downloading
bathymetry data assets required for cruise planning.

Uses the API-first architecture pattern with proper separation of concerns:
- CLI layer handles argument parsing and output formatting
- API layer (cruiseplan.__init__) contains business logic
- Utility functions provide consistent formatting and error handling
"""

import logging
import sys
from pathlib import Path

import cruiseplan
from cruiseplan.cli.cli_utils import (
    _format_error_message,
    _format_progress_header,
    _setup_cli_logging,
)
from cruiseplan.init_utils import (
    _convert_api_response_to_cli,
    _resolve_cli_to_api_params,
)
from cruiseplan.utils.input_validation import _validate_directory_writable

logger = logging.getLogger(__name__)


def get_citation_info(source: str) -> dict:
    """
    Get citation information for bathymetry data sources.

    Parameters
    ----------
    source : str
        Bathymetry source name ('etopo2022' or 'gebco2025')

    Returns
    -------
    dict
        Citation information with formal citation, short citation, and license
    """
    citations = {
        "etopo2022": {
            "name": "ETOPO 2022 15 Arc-Second Global Relief Model",
            "formal_citation": "NOAA National Centers for Environmental Information. 2022: ETOPO 2022 15 Arc-Second Global Relief Model. NOAA National Centers for Environmental Information. https://doi.org/10.25921/fd45-gt74",
            "short_citation": "Bathymetry data from ETOPO 2022 (NOAA NCEI)",
            "doi": "https://doi.org/10.25921/fd45-gt74",
            "license": "Public Domain (US Government Work). Free to use, modify, and distribute.",
            "description": "Global bathymetry and topography at 15 arc-second resolution (~500m)",
        },
        "gebco2025": {
            "name": "GEBCO 2025 Grid",
            "formal_citation": "GEBCO Compilation Group (2025) GEBCO 2025 Grid (doi:10.5285/37c52e96-24ea-67ce-e063-7086abc05f29)",
            "short_citation": "Bathymetry data from GEBCO 2025",
            "doi": "https://doi.org/10.5285/37c52e96-24ea-67ce-e063-7086abc05f29",
            "license": "Public domain. Free to use, copy, publish, distribute, transmit, adapt, and commercially exploit. Users must acknowledge the source and not suggest official endorsement by GEBCO, IHO, or IOC.",
            "description": "High-resolution global bathymetric grid at 15 arc-second resolution",
        },
    }
    return citations.get(source, {})


def show_citation(source: str) -> None:
    """
    Display citation information for a bathymetry source.

    Parameters
    ----------
    source : str
        Bathymetry source name
    """
    citation = get_citation_info(source)

    if not citation:
        print(f"❌ Unknown bathymetry source: {source}")
        sys.exit(1)

    print("=" * 80)
    print(f"   CITATION INFORMATION: {citation['name']}")
    print("=" * 80)
    print()

    print("📖 FORMAL CITATION (for bibliography):")
    print("-" * 50)
    print(f"{citation['formal_citation']}")
    print()

    print("📄 SHORT CITATION (for figure captions):")
    print("-" * 50)
    print(f'"{citation["short_citation"]}"')
    print()

    print("🔗 DOI:")
    print("-" * 50)
    print(f"{citation['doi']}")
    print()

    print("⚖️  LICENSE:")
    print("-" * 50)
    print(f"{citation['license']}")
    print()

    print("📊 DESCRIPTION:")
    print("-" * 50)
    print(f"{citation['description']}")
    print()

    print("=" * 80)
    print("Please include appropriate citation when using this data in publications.")
    print("=" * 80)


def main(args=None):
    """
    Entry point for downloading bathymetry data assets using API-first architecture.

    Parameters
    ----------
    args : argparse.Namespace, optional
        Parsed command-line arguments containing bathymetry source selection.
    """
    try:
        # Setup logging using new utility
        _setup_cli_logging(verbose=getattr(args, "verbose", False))

        # Extract arguments (handle both new "bathy_source" and legacy args)
        # Try new parameter first, then legacy parameters, then default
        source = getattr(args, "bathy_source", None)
        if source is None:
            source = getattr(args, "source", None)  # Legacy --source
            if source is not None:
                logger.warning(
                    "⚠️  WARNING: '--source' is deprecated. Use '--bathy-source' instead."
                )
        if source is None:
            source = getattr(
                args, "bathymetry_source", None
            )  # Legacy --bathymetry-source
            if source is not None:
                logger.warning(
                    "⚠️  WARNING: '--bathymetry-source' is deprecated. Use '--bathy-source' instead."
                )
        if source is None:
            source = "etopo2022"

        show_citation_only = getattr(args, "citation", False)
        output_dir = getattr(args, "output_dir", Path("data/bathymetry"))

        # If citation flag is set, show citation and exit
        if show_citation_only:
            show_citation(source)
            return

        # Validate output directory using new utility
        validated_output_dir = _validate_directory_writable(
            output_dir, create_if_missing=True
        )

        # Format progress header using new utility
        _format_progress_header(
            operation="Bathymetry Data Download",
            config_file=None,
            source=source,
            output_dir=validated_output_dir,
        )

        if source == "etopo2022":
            logger.info(
                "This utility will fetch the ETOPO 2022 bathymetry data (~500MB).\n"
            )
        elif source == "gebco2025":
            logger.info(
                "This utility will fetch the GEBCO 2025 high-resolution bathymetry data (~7.5GB).\n"
            )
        else:
            logger.error(f"Unknown bathymetry source: {source}")
            sys.exit(1)

        # Convert CLI args to API parameters using bridge utility
        api_params = _resolve_cli_to_api_params(args, "bathymetry")

        # Call API function instead of core directly
        api_response = cruiseplan.bathymetry(**api_params)

        # Convert API response to CLI format using bridge utility
        cli_response = _convert_api_response_to_cli(api_response, "bathymetry")

        if cli_response.get("success", True):
            # Show citation info after successful download
            logger.info("\n" + "=" * 60)
            logger.info("📚 CITATION INFORMATION")
            logger.info("=" * 60)
            logger.info("Please cite this data in your publications:")
            citation = get_citation_info(source)
            if citation:
                logger.info(f"\nShort citation: {citation['short_citation']}")
                logger.info(f"DOI: {citation['doi']}")
                logger.info("\nFor full citation details, run:")
                logger.info(
                    f"  cruiseplan bathymetry --bathy-source {source} --citation"
                )
            logger.info("=" * 60)
        else:
            errors = cli_response.get("errors", ["Download failed"])
            for error in errors:
                logger.error(f"❌ {error}")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Download cancelled by user.")
        sys.exit(1)
    except Exception as e:
        _format_error_message(
            "bathymetry",
            e,
            ["Check internet connection", "Verify output directory permissions"],
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
