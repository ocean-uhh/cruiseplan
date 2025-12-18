import logging
import sys
from pathlib import Path

from cruiseplan.data.bathymetry import download_bathymetry

# Configure basic logging so the user sees what's happening
logging.basicConfig(level=logging.INFO, format="%(message)s")


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
    Entry point for downloading cruiseplan data assets.

    Parameters
    ----------
    args : argparse.Namespace, optional
        Parsed command-line arguments containing bathymetry source selection.
    """
    # Extract arguments
    source = getattr(args, "bathymetry_source", "etopo2022")
    show_citation_only = getattr(args, "citation", False)
    output_dir = getattr(args, "output_dir", Path("data/bathymetry"))

    # If citation flag is set, show citation and exit
    if show_citation_only:
        show_citation(source)
        return

    print("========================================")
    print("   CRUISEPLAN ASSET DOWNLOADER")
    print("========================================")

    if source == "etopo2022":
        print("This utility will fetch the ETOPO 2022 bathymetry data (~500MB).\n")
    elif source == "gebco2025":
        print(
            "This utility will fetch the GEBCO 2025 high-resolution bathymetry data (~7.5GB).\n"
        )
    else:
        print(f"Unknown bathymetry source: {source}")
        sys.exit(1)

    try:
        success = download_bathymetry(target_dir=str(output_dir), source=source)
        if source == "gebco2025" and not success:
            sys.exit(1)

        # Show citation info after successful download
        print("\n" + "=" * 60)
        print("📚 CITATION INFORMATION")
        print("=" * 60)
        print("Please cite this data in your publications:")
        citation = get_citation_info(source)
        if citation:
            print(f"\nShort citation: {citation['short_citation']}")
            print(f"DOI: {citation['doi']}")
            print("\nFor full citation details, run:")
            print(f"  cruiseplan download --bathymetry-source {source} --citation")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
