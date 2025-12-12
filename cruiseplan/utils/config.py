# cruiseplan/utils/config.py
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import ValidationError

# Centralized imports for configuration models and the custom error
from cruiseplan.core.validation import CruiseConfig, CruiseConfigurationError

logger = logging.getLogger(__name__)


# --- YAML SAVING UTILITIES (Existing Functions) ---


def save_cruise_config(data: Dict, filepath: Union[str, Path]) -> None:
    """
    Save a dictionary to a YAML file with standard formatting.

    Parameters
    ----------
    data : dict
        The dictionary containing cruise configuration data.
    filepath : str or Path
        Destination path for the YAML file.

    Notes
    -----
    Ensures the parent directory exists and uses consistent YAML formatting
    with preserved key ordering.
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
    Transform internal station data into the YAML schema format.

    Parameters
    ----------
    station_data : dict
        Internal station data from the picker interface.
    index : int
        Station index for naming.

    Returns
    -------
    dict
        Formatted station data conforming to the YAML schema.

    Notes
    -----
    Converts coordinates to native Python floats to avoid NumPy serialization issues.
    """
    return {
        "name": f"STN_{index:03d}",
        # FIX: Cast to float() BEFORE rounding. Rounding alone may not be enough.
        "latitude": round(float(station_data["lat"]), 5),
        "longitude": round(float(station_data["lon"]), 5),
        "depth": round(float(station_data.get("depth", -9999)), 1),
        "comment": "Interactive selection",
        "operation_type": "CTD",  # CTD | mooring | calibration
        "action": "profile",  # profile | deploy | recover
    }


def format_transect_for_yaml(transect_data, index):
    """
    Format internal transect data into the standardized YAML schema.

    Parameters
    ----------
    transect_data : dict
        Internal transect data from the interactive interface.
    index : int
        Transect index for naming.

    Returns
    -------
    dict
        Formatted transect data conforming to the YAML schema.

    Notes
    -----
    Ensures coordinates are native Python floats for proper YAML serialization.
    """
    return {
        "name": f"Section_{index:02d}",
        "comment": "Interactive transect",
        "operation_type": "underway",
        "action": "ADCP",
        "vessel_speed": "10.0",
        "route": [
            {
                "latitude": round(float(transect_data["start"]["lat"]), 5),
                "longitude": round(float(transect_data["start"]["lon"]), 5),
            },
            {
                "latitude": round(float(transect_data["end"]["lat"]), 5),
                "longitude": round(float(transect_data["end"]["lon"]), 5),
            },
        ],
        "reversible": True,
    }


def format_area_for_yaml(area_data, index):
    """
    Format internal area survey data into the standardized YAML schema.

    Parameters
    ----------
    area_data : dict
        Internal area survey data from the interactive interface.
    index : int
        Area index for naming.

    Returns
    -------
    dict
        Formatted area data conforming to the YAML schema.

    Notes
    -----
    Ensures coordinates are native Python floats for proper YAML serialization.
    """
    return {
        "name": f"Area_{index:02d}",
        "corners": [
            {
                "latitude": round(float(lat), 5),
                "longitude": round(float(lon), 5),
            }
            for lon, lat in area_data["points"]
        ],
        "comment": "Interactive area survey",
        "operation_type": "survey",
        "action": "bathymetry",
        "duration": 0.0,
    }


# --- YAML LOADING CLASS (New Implementation) ---


class ConfigLoader:
    """
    Utility class to load, validate, and parse YAML cruise configuration files.

    This class provides a complete workflow for loading cruise configuration data
    from YAML files, validating it against the schema, and returning structured
    CruiseConfig objects.

    Attributes
    ----------
    config_path : Path
        Path to the YAML configuration file.
    raw_data : dict or None
        Raw dictionary data loaded from the YAML file.
    cruise_config : CruiseConfig or None
        Validated and parsed configuration object.
    """

    def __init__(self, config_path: Union[str, Path]):
        """
        Initializes the loader with the path to the configuration file.

        Parameters
        ----------
        config_path : Union[str, Path]
            Path to the YAML configuration file.
        """
        self.config_path = Path(config_path)
        self.raw_data: Optional[Dict[str, Any]] = None
        self.cruise_config: Optional[CruiseConfig] = None

    def load_raw_data(self) -> Dict[str, Any]:
        """
        Loads the raw data from the YAML file, handling file system errors.

        Returns
        -------
        Dict[str, Any]
            The raw dictionary loaded from the YAML file.

        Raises
        ------
        CruiseConfigurationError
            If the file cannot be found, read, or is not valid YAML.
        """
        if not self.config_path.exists():
            raise CruiseConfigurationError(
                f"Configuration file not found: {self.config_path}"
            )

        try:
            with open(self.config_path, encoding="utf-8") as f:
                raw_data = yaml.safe_load(f)
        except Exception as e:
            # Catch I/O errors and generic YAML parsing errors (not validation errors)
            raise CruiseConfigurationError(
                f"Failed to load or parse YAML file {self.config_path}: {e}"
            ) from e

        if not isinstance(raw_data, dict):
            raise CruiseConfigurationError(
                f"YAML content in {self.config_path} is not a valid dictionary (Root structure error)."
            )

        self.raw_data = raw_data
        return self.raw_data

    def validate_and_parse(
        self, raw_data: Optional[Dict[str, Any]] = None
    ) -> CruiseConfig:
        """
        Validates the raw dictionary data against the CruiseConfig schema.

        Parameters
        ----------
        raw_data : Optional[Dict[str, Any]], optional
            The raw data to validate. If None, uses data loaded by load_raw_data.

        Returns
        -------
        CruiseConfig
            A fully validated and structured configuration object.

        Raises
        ------
        CruiseConfigurationError
            If Pydantic validation fails, wraps the error for user clarity.
        """
        if raw_data is None:
            raw_data = self.raw_data

        if raw_data is None:
            # Ensure data is loaded if this method is called directly
            raw_data = self.load_raw_data()

        try:
            # Pydantic does the heavy lifting here, applying all validators
            config = CruiseConfig(**raw_data)
            self.cruise_config = config
            return config
        except ValidationError as e:
            # Catch Pydantic's ValidationError and re-raise it with a user-friendly message
            error_details = "\n".join(
                [
                    f"  -> {'.'.join(str(l) for l in err['loc'])}: {err['msg']}"
                    for err in e.errors()
                ]
            )
            raise CruiseConfigurationError(
                f"Configuration Validation Failed in {self.config_path} "
                f"({len(e.errors())} errors):\n{error_details}"
            ) from e

    def load(self) -> CruiseConfig:
        """
        Performs the complete load-and-validate workflow.

        Returns
        -------
        CruiseConfig
            The validated configuration object.
        """
        self.load_raw_data()
        return self.validate_and_parse()
