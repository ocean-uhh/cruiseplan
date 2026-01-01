#!/usr/bin/env python
"""
Test script to process and schedule all fixture YAML files.

This script runs cruiseplan process and schedule commands on all tc*.yaml files
in the tests/fixtures directory.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Command failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error output:\n{result.stderr}")
            if result.stdout:
                print(f"Standard output:\n{result.stdout}")
            return False
        else:
            print("✅ Command succeeded")
            if result.stdout:
                # Show just the last few lines of output for confirmation
                lines = result.stdout.strip().split("\n")
                if len(lines) > 5:
                    print("... (showing last 5 lines)")
                    for line in lines[-5:]:
                        print(line)
                else:
                    print(result.stdout)
            return True

    except Exception as e:
        print(f"❌ Exception running command: {e}")
        return False


def main():
    """Process and schedule all test fixtures."""
    # Setup paths
    fixtures_dir = Path("tests/fixtures")
    bathy_dir = Path("data/bathymetry")
    enriched_dir = Path("data")
    output_dir = Path("tests_output/fixtures")

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all tc*.yaml files
    fixture_files = sorted(fixtures_dir.glob("tc*.yaml"))

    if not fixture_files:
        print(f"❌ No tc*.yaml files found in {fixtures_dir}")
        sys.exit(1)

    print(f"Found {len(fixture_files)} fixture files to process:")
    for f in fixture_files:
        print(f"  - {f.name}")

    # Track results
    successes = []
    failures = []

    # Process each fixture
    for fixture_file in fixture_files:
        print(f"\n{'#'*70}")
        print(f"# Processing: {fixture_file.name}")
        print(f"{'#'*70}")

        # Derive the enriched filename
        base_name = fixture_file.stem  # e.g., "tc1_mooring"
        enriched_file = enriched_dir / f"{base_name}_enriched.yaml"

        # Step 1: Process the fixture
        process_cmd = [
            "cruiseplan",
            "process",
            "-c",
            str(fixture_file),
            "--bathy-dir",
            str(bathy_dir),
        ]

        if not run_command(process_cmd):
            failures.append(f"{fixture_file.name} (process)")
            print(
                f"⚠️  Skipping schedule for {fixture_file.name} due to process failure"
            )
            continue

        # Check if enriched file was created
        if not enriched_file.exists():
            print(f"❌ Expected enriched file not found: {enriched_file}")
            failures.append(f"{fixture_file.name} (enriched file missing)")
            continue

        print(f"📄 Enriched file created: {enriched_file}")

        # Step 2: Schedule the enriched file
        schedule_cmd = [
            "cruiseplan",
            "schedule",
            "-c",
            str(enriched_file),
            "--bathy-dir",
            str(bathy_dir),
            "-o",
            str(output_dir),
        ]

        if not run_command(schedule_cmd):
            failures.append(f"{fixture_file.name} (schedule)")
        else:
            successes.append(fixture_file.name)

    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Total fixtures processed: {len(fixture_files)}")
    print(f"✅ Successful: {len(successes)}")
    print(f"❌ Failed: {len(failures)}")

    if successes:
        print("\nSuccessful fixtures:")
        for s in successes:
            print(f"  ✅ {s}")

    if failures:
        print("\nFailed fixtures:")
        for f in failures:
            print(f"  ❌ {f}")
        sys.exit(1)
    else:
        print("\n🎉 All fixtures processed successfully!")
        print(f"📁 Output files are in: {output_dir}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
