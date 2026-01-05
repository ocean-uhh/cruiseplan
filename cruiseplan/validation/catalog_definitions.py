"""
Global catalog definitions for cruise configuration.

Defines all reusable operation definitions that users can define in the
"Global Catalog" section of their YAML configuration. These correspond
to the three main operation types: waypoints (point operations),
transects (line operations), and areas (area operations).
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from cruiseplan.utils.coordinates import format_ddm_comment

from .base_models import FlexibleLocationModel, GeoPoint
from .enums import (
    ActionEnum,
    AreaOperationTypeEnum,
    LineOperationTypeEnum,
    OperationTypeEnum,
)


class WaypointDefinition(FlexibleLocationModel):
    """
    Definition of a waypoint location with operation details.

    Unified definition for all point operations including CTD stations,
    moorings, ports, and navigation waypoints. Represents a specific
    geographic point where operations will be performed.

    Attributes
    ----------
    name : str
        Unique identifier for the waypoint.
    operation_type : OperationTypeEnum
        Type of scientific operation to perform.
    action : ActionEnum
        Specific action for the operation.
    operation_depth : Optional[float]
        Target operation depth (e.g., CTD cast depth) in meters.
    water_depth : Optional[float]
        Water depth at location (seafloor depth) in meters.
    duration : Optional[float]
        Manual duration override in minutes.
    delay_start : Optional[float]
        Time to wait before operation begins in minutes (e.g., for daylight).
    delay_end : Optional[float]
        Time to wait after operation ends in minutes (e.g., for equipment settling).
    comment : Optional[str]
        Human-readable comment or description.
    equipment : Optional[str]
        Equipment required for the operation.
    position_string : Optional[str]
        Original position string for reference.
    display_name : Optional[str]
        Human-readable display name (for ports).
    timezone : Optional[str]
        Timezone identifier (for ports).
    """

    name: str
    operation_type: Optional[OperationTypeEnum] = None
    action: Optional[ActionEnum] = None
    operation_depth: Optional[float] = Field(
        None, description="Target operation depth (e.g., CTD cast depth)"
    )
    water_depth: Optional[float] = Field(
        None, description="Water depth at location (seafloor depth)"
    )
    duration: Optional[float] = None
    delay_start: Optional[float] = (
        None  # Time to wait before operation begins (minutes)
    )
    delay_end: Optional[float] = None  # Time to wait after operation ends (minutes)
    comment: Optional[str] = None
    equipment: Optional[str] = None
    position_string: Optional[str] = None

    # Port-specific fields
    display_name: Optional[str] = None
    timezone: Optional[str] = None

    @field_validator("operation_depth")
    @classmethod
    def validate_operation_depth(cls, v):
        """Validate operation depth is positive."""
        if v is not None and v < 0:
            msg = "Operation depth must be positive"
            raise ValueError(msg)
        return v

    @field_validator("water_depth")
    @classmethod
    def validate_water_depth(cls, v):
        """Validate water depth is positive."""
        if v is not None and v < 0:
            msg = "Water depth must be positive"
            raise ValueError(msg)
        return v

    def get_ddm_comment(self) -> str:
        """
        Generate DDM (Degree Decimal Minutes) position comment.

        Returns
        -------
        str
            Position in DDM format for display.
        """
        if self.latitude is not None and self.longitude is not None:
            return format_ddm_comment(self.latitude, self.longitude)
        return ""


class TransectDefinition(BaseModel):
    """
    Definition of a transect route for line operations.

    Represents a planned path between geographic points for scientific
    operations such as ADCP surveys, CTD sections, or towed instruments.
    Uses oceanographically correct terminology where "transect" refers
    to the spatial sampling path/route.

    Attributes
    ----------
    name : str
        Unique identifier for the transect.
    route : List[GeoPoint]
        List of waypoints defining the transect route.
    comment : Optional[str]
        Human-readable comment or description.
    vessel_speed : Optional[float]
        Speed for this transect in knots.
    operation_type : Optional[LineOperationTypeEnum]
        Type of operation for scientific transects.
    action : Optional[ActionEnum]
        Specific action for scientific transects.
    """

    name: str
    route: List[GeoPoint]
    comment: Optional[str] = None
    vessel_speed: Optional[float] = None
    # Optional fields for scientific transects
    operation_type: Optional[LineOperationTypeEnum] = None
    action: Optional[ActionEnum] = None

    @field_validator("route", mode="before")
    def parse_route_strings(cls, v):
        """
        Parse route strings into GeoPoint objects.

        Parameters
        ----------
        v : List[Union[str, dict]]
            List of route points as strings or dictionaries.

        Returns
        -------
        List[dict]
            List of parsed route points.
        """
        # Allow list of strings ["lat,lon", "lat,lon"]
        parsed = []
        for point in v:
            if isinstance(point, str):
                try:
                    lat, lon = map(float, point.split(","))
                    parsed.append({"latitude": lat, "longitude": lon})
                except ValueError as exc:
                    msg = f"Invalid route point: '{point}'. Expected 'lat,lon'"
                    raise ValueError(msg) from exc
            else:
                parsed.append(point)
        return parsed

    @field_validator("vessel_speed")
    @classmethod
    def validate_vessel_speed(cls, v):
        """Validate vessel speed is positive."""
        if v is not None and v <= 0:
            msg = "Vessel speed must be positive"
            raise ValueError(msg)
        return v


class AreaDefinition(BaseModel):
    """
    Definition of an area for survey operations.

    Represents a polygonal region for area-based scientific operations
    such as bathymetric surveys or habitat mapping.

    Attributes
    ----------
    name : str
        Unique identifier for the area.
    corners : List[GeoPoint]
        List of corner points defining the area boundary.
    comment : Optional[str]
        Human-readable comment or description.
    operation_type : Optional[AreaOperationTypeEnum]
        Type of operation for the area (default: "survey").
    action : Optional[ActionEnum]
        Specific action for the area operation.
    duration : Optional[float]
        Duration for the area operation in minutes.
    """

    name: str
    corners: List[GeoPoint]
    comment: Optional[str] = None
    operation_type: Optional[AreaOperationTypeEnum] = AreaOperationTypeEnum.SURVEY
    action: Optional[ActionEnum] = None
    duration: Optional[float] = None  # Duration in minutes

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v):
        """Validate duration is positive."""
        if v is not None and v <= 0:
            msg = "Duration must be positive"
            raise ValueError(msg)
        return v

    @field_validator("corners")
    @classmethod
    def validate_corners_minimum(cls, v):
        """Validate at least 3 corners for a valid area."""
        if len(v) < 3:
            msg = "Area must have at least 3 corners"
            raise ValueError(msg)
        return v


# Legacy aliases for backward compatibility during migration
# TODO: Remove in v0.4.0 - Use WaypointDefinition instead
StationDefinition = WaypointDefinition  # Stations are now waypoints
PortDefinition = WaypointDefinition  # Ports are now waypoints

# TODO: Remove in v0.4.0 - Use TransectDefinition instead
TransitDefinition = TransectDefinition  # Transits are now transects
