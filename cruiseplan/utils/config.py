# cruiseplan/utils/config.py
import logging
from pathlib import Path
from typing import Dict, Union

import yaml

logger = logging.getLogger(__name__)


def save_cruise_config(data: Dict, filepath: Union[str, Path]) -> None:
    """
    Saves a dictionary to a YAML file, ensuring standard formatting.

    Args:
        data: The dictionary containing 'stations', 'moorings', etc.
        filepath: Destination path.
    """
    path = Path(filepath)

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "w") as f:
            # sort_keys=False preserves insertion order (vital for ordered cruise tracks)
            yaml.dump(
                data, f, sort_keys=False, default_flow_style=False, allow_unicode=True
            )
        logger.info(f"✅ Configuration saved to {path}")
    except Exception as e:
        logger.error(f"❌ Failed to save configuration: {e}")
        raise


def format_station_for_yaml(station_data: Dict, index: int) -> Dict:
    """
    Helper to transform internal picker data into the Spec's YAML schema.
    Converts coordinates to native Python floats to avoid NumPy serialization.
    """
    return {
        "name": f"STN_{index:03d}",
        # FIX: Cast to float() BEFORE rounding. Rounding alone may not be enough.
        "latitude": round(float(station_data["lat"]), 5),
        "longitude": round(float(station_data["lon"]), 5),
        "depth": round(float(station_data.get("depth", -9999)), 1),
        "comment": "Interactive selection",
    }

def format_transect_for_yaml(transect_data, index):
    """
    Formats internal transect data into the standardized YAML schema.
    Ensures coordinates are native Python floats.
    """
    return {
        "name": f"Section_{index:02d}",
        "start": {
            # FIX: Explicitly cast to float() here
            "latitude": round(float(transect_data["start"]["lat"]), 5),
            "longitude": round(float(transect_data["start"]["lon"]), 5),
        },
        "end": {
            # FIX: Explicitly cast to float() here
            "latitude": round(float(transect_data["end"]["lat"]), 5 ),
            "longitude": round(float(transect_data["end"]["lon"]), 5),
        },
        "reversible": True,
    }
