"""
Main cruise configuration model.

Defines the root CruiseConfig class that represents the complete
cruise configuration file. This is the top-level YAML structure
that contains all cruise metadata, global catalog definitions,
and schedule organization.
"""

from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cruiseplan.utils.defaults import (
    DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY,
    DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS,
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
)

from .catalog_definitions import AreaDefinition, TransectDefinition, WaypointDefinition
from .schedule_definitions import LegDefinition

# Legacy aliases for backward compatibility
# TODO: Remove in v0.4.0 - Use WaypointDefinition instead
StationDefinition = WaypointDefinition
PortDefinition = WaypointDefinition

# TODO: Remove in v0.4.0 - Use TransectDefinition instead
TransitDefinition = TransectDefinition


class CruiseConfig(BaseModel):
    """
    Root configuration model for cruise planning.

    Contains all the high-level parameters and definitions for a complete
    oceanographic cruise plan. Represents the top-level YAML structure
    with cruise metadata, global catalog, and schedule organization.

    Attributes
    ----------
    cruise_name : str
        Name of the cruise.
    description : Optional[str]
        Human-readable description of the cruise.
    default_vessel_speed : float
        Default vessel speed in knots.
    default_distance_between_stations : float
        Default station spacing in kilometers.
    turnaround_time : float
        Time required for station turnaround in minutes.
    ctd_descent_rate : float
        CTD descent rate in meters per second.
    ctd_ascent_rate : float
        CTD ascent rate in meters per second.
    day_start_hour : int
        Start hour for daytime operations (0-23).
    day_end_hour : int
        End hour for daytime operations (0-23).
    calculate_transfer_between_sections : bool
        Whether to calculate transit times between sections.
    calculate_depth_via_bathymetry : bool
        Whether to calculate depths using bathymetry data.
    start_date : str
        Cruise start date.
    start_time : Optional[str]
        Cruise start time.
    station_label_format : str
        Format string for station labels.
    mooring_label_format : str
        Format string for mooring labels.
    departure_port : Optional[Union[str, WaypointDefinition]]
        Port where the cruise begins.
    arrival_port : Optional[Union[str, WaypointDefinition]]
        Port where the cruise ends.
    stations : Optional[List[WaypointDefinition]]
        Global catalog of waypoint definitions.
    transects : Optional[List[TransectDefinition]]
        Global catalog of transect definitions.
    areas : Optional[List[AreaDefinition]]
        Global catalog of area definitions.
    ports : Optional[List[WaypointDefinition]]
        Global catalog of port definitions.
    legs : Optional[List[LegDefinition]]
        List of cruise legs for schedule organization.

    # Legacy fields for backward compatibility
    transits : Optional[List[TransectDefinition]]
        LEGACY: Use 'transects' instead.
    """

    cruise_name: str
    description: Optional[str] = None

    # --- LOGIC CONSTRAINTS ---
    default_vessel_speed: float
    default_distance_between_stations: float = DEFAULT_STATION_SPACING_KM
    turnaround_time: float = DEFAULT_TURNAROUND_TIME_MIN
    ctd_descent_rate: float = 1.0
    ctd_ascent_rate: float = 1.0

    # Configuration "daylight" or "dayshift" window for moorings
    day_start_hour: int = 8  # Default 08:00
    day_end_hour: int = 20  # Default 20:00

    calculate_transfer_between_sections: bool = (
        DEFAULT_CALCULATE_TRANSFER_BETWEEN_SECTIONS
    )
    calculate_depth_via_bathymetry: bool = DEFAULT_CALCULATE_DEPTH_VIA_BATHYMETRY
    start_date: str = DEFAULT_START_DATE
    start_time: Optional[str] = "08:00"
    station_label_format: str = "C{:03d}"
    mooring_label_format: str = "M{:02d}"

    # Port definitions for single-leg cruises
    departure_port: Optional[Union[str, WaypointDefinition]] = Field(
        None,
        description="Port where the cruise begins (can be global port reference). Required for single-leg cruises, forbidden for multi-leg cruises.",
    )
    arrival_port: Optional[Union[str, WaypointDefinition]] = Field(
        None,
        description="Port where the cruise ends (can be global port reference). Required for single-leg cruises, forbidden for multi-leg cruises.",
    )

    # Global catalog definitions (new oceanographic terminology)
    stations: Optional[list[WaypointDefinition]] = Field(
        default_factory=list, description="Global catalog of waypoint definitions"
    )
    transects: Optional[list[TransectDefinition]] = Field(
        default_factory=list, description="Global catalog of transect definitions"
    )
    areas: Optional[list[AreaDefinition]] = Field(
        default_factory=list, description="Global catalog of area definitions"
    )
    ports: Optional[list[WaypointDefinition]] = Field(
        default_factory=list, description="Global catalog of port definitions"
    )

    # Schedule organization
    legs: Optional[list[LegDefinition]] = Field(
        default_factory=list,
        description="List of cruise legs for schedule organization",
    )

    # Legacy fields (backward compatibility)
    transits: Optional[list[TransectDefinition]] = Field(
        default_factory=list, description="LEGACY: Use 'transects' instead"
    )

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_cruise_structure(self):
        """
        Validate overall cruise configuration structure.

        Returns
        -------
        CruiseConfig
            Validated cruise configuration.

        Raises
        ------
        ValueError
            If cruise structure is invalid.
        """
        # Basic validation - more complex validators can be added later
        if not self.cruise_name.strip():
            msg = "Cruise name cannot be empty"
            raise ValueError(msg)

        if self.default_vessel_speed <= 0:
            msg = "Default vessel speed must be positive"
            raise ValueError(msg)

        if self.default_distance_between_stations <= 0:
            msg = "Default distance between stations must be positive"
            raise ValueError(msg)

        return self
