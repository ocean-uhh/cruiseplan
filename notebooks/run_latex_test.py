import logging
from pathlib import Path
from typing import Any, Dict

from cruiseplan.calculators.duration import DurationCalculator
from cruiseplan.core.validation import CruiseConfigurationError
from cruiseplan.output.latex_generator import generate_latex_tables

# Assuming these imports are correct based on Phase 1 completion
from cruiseplan.utils.config import ConfigLoader

# Configure logging to see status messages
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- Mock Data Structures ---
# NOTE: This test uses mock data for demonstration purposes.
# Complete cruise scheduling logic will be implemented in Phase 3c,
# which will provide proper timing calculations, transit times,
# and operation sequencing to replace these placeholder values.


def create_mock_cruise_object(config_path: str) -> Dict[str, Any]:
    """
    Loads YAML config, validates it, and augments it with necessary
    'operations' and 'summary_breakdown' data required by the LaTeX generator.
    """
    try:
        loader = ConfigLoader(config_path)
        config = loader.load()
    except CruiseConfigurationError as e:
        logger.error(f"Configuration Validation Failed for {config_path}: {e}")
        return None

    # --- MOCKING: Flattened Operations List (For stations_table) ---

    # We flatten the structure to provide the generator a list of items to draw
    mock_operations = []

    # Simple Mocking based on config for demonstration purposes:
    station_refs = []
    if config.legs:
        leg = config.legs[0]

        # Try stations first (if present)
        if hasattr(leg, "stations") and leg.stations:
            station_refs = leg.stations
        # Fall back to extracting stations from sequence
        elif hasattr(leg, "sequence") and leg.sequence:
            # Filter only station names from sequence
            station_refs = [
                item
                for item in leg.sequence
                if isinstance(item, str)
                and any(s.name == item for s in config.stations)
            ]

    for stn_ref in station_refs:
        # Find the full definition in the catalog (simple search assumed)
        station_def = next((s for s in config.stations if s.name == stn_ref), None)

        if station_def:
            # Handle both position object and direct lat/lon attributes
            if hasattr(station_def, "position") and station_def.position:
                lat = station_def.position.latitude
                lon = station_def.position.longitude
            else:
                lat = getattr(station_def, "latitude", None)
                lon = getattr(station_def, "longitude", None)

            if lat is not None and lon is not None:
                mock_operations.append(
                    {
                        "type": "CTD profile",
                        "name": station_def.name,
                        "latitude": lat,
                        "longitude": lon,
                        "depth": getattr(station_def, "depth", 1000.0),
                    }
                )

    # --- MOCKING: Summary Breakdown (For work_days_table) ---
    # Note: Do not include a 'Total duration' row as the template adds this automatically

    # Calculate realistic CTD time using the proper DurationCalculator
    total_ctd_minutes = 0.0
    calculator = DurationCalculator(config)

    for op in mock_operations:
        if op["type"] == "CTD profile":
            depth = op["depth"]
            station_time_minutes = calculator.calculate_ctd_time(depth)
            total_ctd_minutes += station_time_minutes

    total_ctd_hours = total_ctd_minutes / 60.0

    mock_summary_breakdown = [
        {
            "area": "Transit to Port",
            "activity": "",
            "duration_h": "",
            "transit_h": 35.0,
        },
        {
            "area": config.legs[0].name,
            "activity": "CTD stations",
            "duration_h": round(total_ctd_hours, 1),
            "transit_h": "",
        },
        {
            "area": "Transit within area",
            "activity": "",
            "duration_h": 10.0,
            "transit_h": "",
        },
    ]

    # Only add mooring operations if there are moorings in the config
    if hasattr(config, "moorings") and config.moorings:
        mock_summary_breakdown.insert(
            -1,
            {
                "area": config.legs[0].name,
                "activity": "Mooring operations",
                "duration_h": 15.0,
                "transit_h": "",
            },
        )

    # Combine config data with mock processed data
    cruise_object = {
        "cruise_name": config.cruise_name,
        "operations": mock_operations,
        "summary_breakdown": mock_summary_breakdown,
        # Pass necessary config data
        "default_vessel_speed": config.default_vessel_speed,
    }

    return cruise_object


# --- Main Test Execution ---


def main():
    # Define the list of YAML files to test (update paths as necessary)
    yaml_files = [
        "tests/fixtures/cruise_simple.yaml",
        "tests/fixtures/cruise_mixed_ops.yaml",
        "tests/fixtures/cruise_multi_leg.yaml",
    ]

    # Define output location
    output_base_dir = Path("tests_output/latex_reports")
    output_base_dir.mkdir(parents=True, exist_ok=True)

    print("Starting LaTeX Generation Test...")
    print(f"Output directory: {output_base_dir.resolve()}")
    print("-" * 40)

    for filename in yaml_files:
        try:
            # 1. Prepare Mocked Cruise Data
            cruise_data = create_mock_cruise_object(filename)
            if cruise_data is None:
                continue

            # 2. Generate Tables
            output_dir = output_base_dir / cruise_data["cruise_name"]

            generated_files = generate_latex_tables(cruise_data, output_dir)

            print(f"✅ Generated reports for {cruise_data['cruise_name']}:")
            for f in generated_files:
                print(f"   -> {f.name}")

        except Exception as e:
            logger.error(f"Critical Error processing {filename}: {e}")


if __name__ == "__main__":
    # Ensure fixture YAML files are available in the specified path before running!
    main()
