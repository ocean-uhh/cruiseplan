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

    Input: {'lat': 47.5, 'lon': -52.0, 'depth': 200}
    Output: {
        'name': 'STN_001',
        'latitude': 47.5,
        'longitude': -52.0,
        'depth': 200,
        'comment': 'Interactive selection'
    }
    """
    return {
        "name": f"STN_{index:03d}",  # Default naming pattern
        "latitude": round(station_data["lat"], 6),
        "longitude": round(station_data["lon"], 6),
        "depth": round(station_data.get("depth", -9999), 1),
        "comment": "Interactive selection",
    }
