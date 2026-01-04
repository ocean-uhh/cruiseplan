"""
Base model classes for cruise configuration validation.

Provides fundamental building blocks for geographic coordinates and
flexible input handling used throughout the validation system.
"""

from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator


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
        """
        Validate latitude is within valid range.

        Parameters
        ----------
        v : float
            Latitude value to validate.

        Returns
        -------
        float
            Validated latitude value.

        Raises
        ------
        ValueError
            If latitude is outside -90 to 90 degrees.
        """
        if not (-90 <= v <= 90):
            msg = f"Latitude {v} must be between -90 and 90"
            raise ValueError(msg)
        return v

    @field_validator("longitude")
    def validate_lon(cls, v):
        """
        Validate longitude is within valid range.

        Parameters
        ----------
        v : float
            Longitude value to validate.

        Returns
        -------
        float
            Validated longitude value.

        Raises
        ------
        ValueError
            If longitude is outside -180 to 360 degrees.
        """
        # Individual point check: Must be valid in at least one system (-180..360 covers both)
        if not (-180 <= v <= 360):
            msg = f"Longitude {v} must be between -180 and 360"
            raise ValueError(msg)
        return v


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
