import logging
import sys

from cruiseplan.data.bathymetry import download_bathymetry

# Configure basic logging so the user sees what's happening
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main(args=None):
    """
    Entry point for downloading cruiseplan data assets.

    Parameters
    ----------
    args : argparse.Namespace, optional
        Parsed command-line arguments containing bathymetry source selection.
    """
    # Extract bathymetry source from args
    source = getattr(args, "bathymetry_source", "etopo2022")

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
        success = download_bathymetry(source=source)
        if source == "gebco2025" and not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
