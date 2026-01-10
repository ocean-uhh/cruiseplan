"""
Base model classes for cruise configuration validation.

Provides fundamental building blocks for geographic coordinates and
flexible input handling used throughout the validation system.
"""

from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator

from cruiseplan.utils.coordinates import _validate_latitude, _validate_longitude


class GeoPoint(BaseModel):
    """
    Internal representation of a geographic point.

    Represents a latitude/longitude coordinate pair with validation.

    Attributes
    ----------
    latitude : float
        Latitude in decimal degrees (-90 to 90).
    longitude : float
        Longitude in decimal degrees (-180 to 360).
    """

    latitude: float
    longitude: float

    @field_validator("latitude")
    def validate_lat(cls, v):
        """Validate latitude using centralized coordinate utilities."""
        return _validate_latitude(v)

    @field_validator("longitude")
    def validate_lon(cls, v):
        """Validate longitude using centralized coordinate utilities."""
        return _validate_longitude(v)


class FlexibleLocationModel(BaseModel):
    """
    Base class that allows users to define location in multiple formats.

    Supports both explicit latitude/longitude fields and string format
    ("lat, lon") in YAML input for user convenience.

    Attributes
    ----------
    latitude : Optional[float]
        Latitude in decimal degrees.
    longitude : Optional[float]
        Longitude in decimal degrees.
    """

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def unify_coordinates(cls, data: Any) -> Any:
        """
        Unify different coordinate input formats.

        Handles both explicit lat/lon fields and string position format.

        Parameters
        ----------
        data : Any
            Input data dictionary to process.

        Returns
        -------
        Any
            Processed data with latitude and longitude fields.

        Raises
        ------
        ValueError
            If position string cannot be parsed as "lat, lon".
        """
        if isinstance(data, dict):
            # Check for incomplete coordinate pairs
            has_lat = "latitude" in data
            has_lon = "longitude" in data

            if has_lat and not has_lon:
                msg = "Both latitude and longitude must be provided together"
                raise ValueError(msg)
            if has_lon and not has_lat:
                msg = "Both latitude and longitude must be provided together"
                raise ValueError(msg)

            # Case B: String Position (convert to lat/lon)
            if "position" in data and isinstance(data["position"], str):
                try:
                    lat, lon = map(float, data["position"].split(","))
                    data["latitude"] = lat
                    data["longitude"] = lon
                    del data["position"]  # Remove the position field
                except ValueError as exc:
                    msg = f"Invalid position string: '{data['position']}'. Expected 'lat, lon'"
                    raise ValueError(msg) from exc
        return data
