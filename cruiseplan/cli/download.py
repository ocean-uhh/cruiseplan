import logging
import sys

from cruiseplan.data.bathymetry import download_bathymetry

# Configure basic logging so the user sees what's happening
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    """
    Entry point for downloading cruiseplan data assets.
    """
    print("========================================")
    print("   CRUISEPLAN ASSET DOWNLOADER")
    print("========================================")
    print("This utility will fetch the required ETOPO 2022 bathymetry data (~1GB).\n")

    try:
        download_bathymetry()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
