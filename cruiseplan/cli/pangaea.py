"""
PANGAEA DOI processing command.

This module implements the 'cruiseplan pangaea' command for processing
PANGAEA DOI lists into campaign datasets with progress tracking and
rate limiting.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from cruiseplan.cli.utils import (
    CLIError,
    read_doi_list,
    setup_logging,
    validate_input_file,
    validate_output_path,
)
from cruiseplan.data.pangaea import PangaeaManager

logger = logging.getLogger(__name__)


def fetch_pangaea_data(
    doi_list: List[str], rate_limit: float = 1.0, merge_campaigns: bool = True
) -> List[dict]:
    """
    CLI wrapper for fetching PANGAEA datasets with logging.

    Args:
        doi_list: List of DOI strings to fetch
        rate_limit: Requests per second limit
        merge_campaigns: Whether to merge campaigns with same name

    Returns
    -------
        List of dataset dictionaries
    """

    def progress_callback(current: int, total: int, message: str) -> None:
        """Progress callback that logs to CLI logger."""
        if current == 0:
            logger.info(message)
            logger.info(f"Rate limit: {rate_limit} requests/second")
        elif "✓" in message or "⚠" in message or "✗" in message:
            logger.info(f"[{current}/{total}] {message}")
        elif "Merged" in message or "Completed" in message:
            logger.info(message)
        elif "interrupted" in message:
            logger.info(f"\n\n{message}")
        else:
            logger.info(f"[{current}/{total}] {message}")

    pangaea = PangaeaManager()
    return pangaea.fetch_datasets(
        doi_list=doi_list,
        rate_limit=rate_limit,
        merge_campaigns=merge_campaigns,
        progress_callback=progress_callback,
    )


def save_pangaea_pickle(
    datasets: List[dict], output_path: Path, original_count: int = None
) -> None:
    """
    CLI wrapper for saving PANGAEA datasets to pickle file.

    Args:
        datasets: List of dataset dictionaries
        output_path: Output file path
        original_count: Count of datasets before any merging (for accurate summary)
    """
    from cruiseplan.data.pangaea import save_campaign_data

    def progress_callback(message: str) -> None:
        """Progress callback that logs to CLI logger."""
        logger.info(message)

    try:
        save_campaign_data(datasets, output_path, progress_callback, original_count)
    except ValueError as e:
        raise CLIError(str(e))


def validate_dois(doi_list: List[str]) -> List[str]:
    """
    Validate DOI format and filter invalid entries.

    Uses the existing DOI validation from data.pangaea module with
    CLI-friendly prefix cleanup.

    Args:
        doi_list: List of DOI strings

    Returns
    -------
        List of valid DOIs
    """
    from cruiseplan.data.pangaea import _is_valid_doi

    valid_dois = []

    for doi in doi_list:
        # Clean up common prefixes that users might include
        clean_doi = doi.strip()

        if clean_doi.startswith("https://doi.org/"):
            clean_doi = clean_doi.replace("https://doi.org/", "")
        elif clean_doi.startswith("doi:"):
            clean_doi = clean_doi.replace("doi:", "")

        # Use the strict validation from data module
        if _is_valid_doi(clean_doi):
            valid_dois.append(clean_doi)
        else:
            logger.warning(f"Skipping invalid DOI format: {doi}")

    if not valid_dois:
        raise CLIError("No valid DOIs found in input file")

    if len(valid_dois) != len(doi_list):
        logger.info(f"Filtered {len(doi_list) - len(valid_dois)} invalid DOIs")

    return valid_dois


def main(args: argparse.Namespace) -> None:
    """
    Main entry point for PANGAEA command.

    Args:
        args: Parsed command line arguments
    """
    try:
        # Setup logging
        setup_logging(
            verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False)
        )

        # Validate input file
        doi_file = validate_input_file(args.doi_file)

        # Determine output path
        if args.output_file:
            output_path = validate_output_path(output_file=args.output_file)
        else:
            output_dir = validate_output_path(output_dir=args.output_dir)
            # Generate filename from input file
            output_filename = f"{doi_file.stem}_pangaea_data.pkl"
            output_path = output_dir / output_filename

        logger.info("=" * 50)
        logger.info("PANGAEA DOI Processor")
        logger.info("=" * 50)
        logger.info(f"Input file: {doi_file}")
        logger.info(f"Output file: {output_path}")
        logger.info(f"Rate limit: {args.rate_limit} requests/second")
        logger.info("")

        # Read and validate DOI list
        doi_list = read_doi_list(doi_file)
        valid_dois = validate_dois(doi_list)

        # Fetch PANGAEA data
        datasets = fetch_pangaea_data(
            valid_dois, rate_limit=args.rate_limit, merge_campaigns=args.merge_campaigns
        )

        if not datasets:
            logger.warning(
                "No datasets retrieved. Check DOI list and network connection."
            )
            return

        # Save results (pass original DOI count for accurate summary)
        save_pangaea_pickle(datasets, output_path, len(valid_dois))

        logger.info("")
        logger.info("✓ PANGAEA processing completed successfully!")

    except CLIError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Operation cancelled by user.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # This allows the module to be run directly for testing
    import argparse

    parser = argparse.ArgumentParser(description="Process PANGAEA DOI lists")
    parser.add_argument("doi_file", type=Path, help="DOI list file")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--rate-limit", type=float, default=1.0)
    parser.add_argument("--merge-campaigns", action="store_true", default=True)

    args = parser.parse_args()
    main(args)
