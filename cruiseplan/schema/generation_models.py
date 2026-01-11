"""
Generation utilities for cruise configuration.

Provides models for auto-generating operations from high-level specifications.
These utilities create individual operations (waypoints, transects) from
simplified input parameters.
"""

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator

from .activities import GeoPoint


class GenerateTransect(BaseModel):
    """
    Parameters for generating a transect of stations.

    Defines how to create a series of stations along a line between two points.
    This is the original transect generation utility.

    Attributes
    ----------
    start : GeoPoint
        Starting point of the transect.
    end : GeoPoint
        Ending point of the transect.
    spacing : float
        Distance between stations in kilometers.
    id_pattern : str
        Pattern for generating station IDs.
    start_index : int
        Starting index for station numbering (default: 1).
    reversible : bool
        Whether the transect can be traversed in reverse (default: True).
    """

    start: GeoPoint
    end: GeoPoint
    spacing: float
    id_pattern: str
    start_index: int = 1
    reversible: bool = True

    @model_validator(mode="before")
    @classmethod
    def handle_string_positions(cls, data):
        """
        Convert string positions to GeoPoint objects.

        Parameters
        ----------
        data : dict
            Input data potentially containing string positions.

        Returns
        -------
        dict
            Data with GeoPoint objects.
        """
        if isinstance(data, dict):
            for field in ["start", "end"]:
                if field in data and isinstance(data[field], str):
                    try:
                        lat, lon = map(float, data[field].split(","))
                        data[field] = {"latitude": lat, "longitude": lon}
                    except ValueError as exc:
                        msg = f"Invalid {field} position: '{data[field]}'. Expected 'lat,lon'"
                        raise ValueError(msg) from exc
        return data

    @field_validator("spacing")
    @classmethod
    def validate_spacing(cls, v):
        """Validate spacing is positive."""
        if v <= 0:
            msg = "Spacing must be positive"
            raise ValueError(msg)
        return v

    @field_validator("start_index")
    @classmethod
    def validate_start_index(cls, v):
        """Validate start_index is positive."""
        if v < 1:
            msg = "Start index must be at least 1"
            raise ValueError(msg)
        return v


class GenerateSection(BaseModel):
    """
    Parameters for generating a CTD section (transect → individual stations).

    Takes a transect definition with op_type="CTD" and action="section"
    and creates individual waypoint stations along the path. This implements
    the oceanographically correct workflow where a "section" is the 2D data
    slice created from measurements along a "transect" path.

    Attributes
    ----------
    transect_name : str
        Name of the source transect definition.
    station_spacing : float
        Distance between CTD stations in kilometers.
    id_pattern : str
        Pattern for generating station IDs (e.g., "CTD_{:03d}").
    start_index : int
        Starting index for station numbering (default: 1).
    operation_depth : Optional[float]
        Target CTD cast depth in meters.
    reversible : bool
        Whether the section can be traversed in reverse (default: True).
    """

    transect_name: str
    station_spacing: float
    id_pattern: str
    start_index: int = 1
    operation_depth: Optional[float] = None
    reversible: bool = True

    @field_validator("station_spacing")
    @classmethod
    def validate_spacing(cls, v):
        """Validate station spacing is positive."""
        if v <= 0:
            msg = "Station spacing must be positive"
            raise ValueError(msg)
        return v

    @field_validator("start_index")
    @classmethod
    def validate_start_index(cls, v):
        """Validate start_index is positive."""
        if v < 1:
            msg = "Start index must be at least 1"
            raise ValueError(msg)
        return v

    @field_validator("operation_depth")
    @classmethod
    def validate_depth(cls, v):
        """Validate operation depth is positive if provided."""
        if v is not None and v <= 0:
            msg = "Operation depth must be positive"
            raise ValueError(msg)
        return v


# Legacy model for backward compatibility (deprecated)
class SectionDefinition(BaseModel):
    """
    DEPRECATED: Definition of a section with start/end points.

    This class is deprecated in favor of the new GenerateSection utility
    which uses the correct oceanographic terminology. Use TransectDefinition
    for the spatial path and GenerateSection to create individual stations.

    Represents a geographic section along which stations may be placed.
    """

    name: str
    start: GeoPoint
    end: GeoPoint
    distance_between_stations: Optional[float] = None
    reversible: bool = True
    stations: Optional[list] = None

    def __init__(self, **data):
        """Initialize with deprecation warning."""
        super().__init__(**data)
        # In production, would emit deprecation warning here

    @model_validator(mode="before")
    @classmethod
    def handle_string_positions(cls, data):
        """
        Convert string positions to GeoPoint objects.

        Parameters
        ----------
        data : dict
            Input data potentially containing string positions.

        Returns
        -------
        dict
            Data with GeoPoint objects.
        """
        if isinstance(data, dict):
            for field in ["start", "end"]:
                if field in data and isinstance(data[field], str):
                    try:
                        lat, lon = map(float, data[field].split(","))
                        data[field] = {"latitude": lat, "longitude": lon}
                    except ValueError as exc:
                        msg = f"Invalid {field} position: '{data[field]}'. Expected 'lat,lon'"
                        raise ValueError(msg) from exc
        return data
