import warnings
from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from cruiseplan.utils.constants import (
    DEFAULT_START_DATE,
    DEFAULT_STATION_SPACING_KM,
    DEFAULT_TURNAROUND_TIME_MIN,
)

# cruiseplan/core/validation.py


# --- Custom Exception ---
class CruiseConfigurationError(Exception):
    """Raised when cruise configuration is invalid or cannot be processed."""

    pass


# --- Enums ---
class StrategyEnum(str, Enum):
    SEQUENTIAL = "sequential"
    SPATIAL_INTERLEAVED = "spatial_interleaved"
    DAY_NIGHT_SPLIT = "day_night_split"


class ActionEnum(str, Enum):
    DEPLOYMENT = "deployment"
    RECOVERY = "recovery"


# --- Shared Models ---


class GeoPoint(BaseModel):
    """
    Internal representation of a point.
    """

    latitude: float
    longitude: float

    @field_validator("latitude")
    def validate_lat(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError(f"Latitude {v} must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_lon(cls, v):
        # Individual point check: Must be valid in at least one system (-180..360 covers both)
        if not (-180 <= v <= 360):
            raise ValueError(f"Longitude {v} must be between -180 and 360")
        return v


class FlexibleLocationModel(BaseModel):
    """
    Base class that allows users to define location as either:
    1. position: "lat, lon" (Legacy/Fast)
    2. latitude: float, longitude: float (Explicit/Clear)
    """

    position: Optional[GeoPoint] = None  # Internal storage

    @model_validator(mode="before")
    @classmethod
    def unify_coordinates(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Case A: Explicit Lat/Lon
            if "latitude" in data and "longitude" in data:
                data["position"] = {
                    "latitude": data.pop("latitude"),
                    "longitude": data.pop("longitude"),
                }
            # Case B: String Position
            elif "position" in data and isinstance(data["position"], str):
                try:
                    lat, lon = map(float, data["position"].split(","))
                    data["position"] = {"latitude": lat, "longitude": lon}
                except ValueError:
                    raise ValueError(
                        f"Invalid position string: '{data['position']}'. Expected 'lat, lon'"
                    )
        return data


# --- Catalog Definitions ---


class PortDefinition(FlexibleLocationModel):
    name: str
    timezone: Optional[str] = "UTC"


class StationDefinition(FlexibleLocationModel):
    name: str
    depth: Optional[float] = None
    duration: Optional[float] = None
    comment: Optional[str] = None
    position_string: Optional[str] = None

    @field_validator("duration")
    def validate_duration_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Duration must be positive")
        return v


class MooringDefinition(FlexibleLocationModel):
    name: str
    action: ActionEnum
    duration: float
    depth: Optional[float] = None
    comment: Optional[str] = None
    equipment: Optional[str] = None
    position_string: Optional[str] = None

    @field_validator("duration")
    def validate_duration_positive(cls, v):
        if v <= 0:
            raise ValueError("Mooring duration must be positive")
        return v


class TransitDefinition(BaseModel):
    name: str
    route: List[GeoPoint]
    comment: Optional[str] = None
    vessel_speed: Optional[float] = None

    @field_validator("route", mode="before")
    def parse_route_strings(cls, v):
        # Allow list of strings ["lat,lon", "lat,lon"]
        parsed = []
        for point in v:
            if isinstance(point, str):
                lat, lon = map(float, point.split(","))
                parsed.append({"latitude": lat, "longitude": lon})
            else:
                parsed.append(point)
        return parsed


# --- Schedule Definitions ---


class GenerateTransect(BaseModel):
    start: GeoPoint
    end: GeoPoint
    spacing: float
    id_pattern: str
    start_index: int = 1
    reversible: bool = True

    @model_validator(mode="before")
    @classmethod
    def parse_endpoints(cls, data):
        # Helper to parse start/end strings
        for field in ["start", "end"]:
            if field in data and isinstance(data[field], str):
                lat, lon = map(float, data[field].split(","))
                data[field] = {"latitude": lat, "longitude": lon}
        return data


class SectionDefinition(BaseModel):
    name: str
    start: GeoPoint
    end: GeoPoint
    distance_between_stations: Optional[float] = None
    reversible: bool = True
    stations: Optional[List[str]] = []

    @model_validator(mode="before")
    @classmethod
    def parse_endpoints(cls, data):
        for field in ["start", "end"]:
            if field in data and isinstance(data[field], str):
                lat, lon = map(float, data[field].split(","))
                data[field] = {"latitude": lat, "longitude": lon}
        return data


class ClusterDefinition(BaseModel):
    name: str
    strategy: StrategyEnum = StrategyEnum.SEQUENTIAL
    ordered: bool = True
    sequence: Optional[
        List[Union[str, MooringDefinition, StationDefinition, TransitDefinition]]
    ] = None
    moorings: Optional[List[Union[str, MooringDefinition]]] = []
    stations: Optional[List[Union[str, StationDefinition]]] = []
    generate_transect: Optional[GenerateTransect] = None
    activities: Optional[List[dict]] = []


class LegDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    strategy: Optional[StrategyEnum] = None
    ordered: Optional[bool] = None
    stations: Optional[List[Union[str, StationDefinition]]] = []
    clusters: Optional[List[ClusterDefinition]] = []
    sections: Optional[List[SectionDefinition]] = []
    moorings: Optional[List[Union[str, MooringDefinition]]] = []
    sequence: Optional[List[Union[str, MooringDefinition, StationDefinition]]] = []


# --- Root Config ---


class CruiseConfig(BaseModel):
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

    calculate_transfer_between_sections: bool
    calculate_depth_via_bathymetry: bool
    start_date: str = DEFAULT_START_DATE
    start_time: Optional[str] = "08:00"
    station_label_format: str = "C{:03d}"
    mooring_label_format: str = "M{:02d}"

    departure_port: PortDefinition
    arrival_port: PortDefinition
    first_station: str
    last_station: str

    stations: Optional[List[StationDefinition]] = []
    moorings: Optional[List[MooringDefinition]] = []
    transits: Optional[List[TransitDefinition]] = []
    legs: List[LegDefinition]

    model_config = ConfigDict(extra="forbid")

    # --- VALIDATORS ---

    @field_validator("default_vessel_speed")
    def validate_speed(cls, v):
        if v <= 0:
            raise ValueError("Vessel speed must be positive")
        if v > 20:
            raise ValueError(
                f"Vessel speed {v} knots is unrealistic (> 20). Raise an Error."
            )
        if v < 1:
            warnings.warn(f"Vessel speed {v} knots is unusually low (< 1).")
        return v

    @field_validator("default_distance_between_stations")
    def validate_distance(cls, v):
        if v <= 0:
            raise ValueError("Distance must be positive")
        if v > 150:
            raise ValueError(
                f"Station spacing {v} km is too large (> 150). Raise an Error."
            )
        if v < 4 or v > 50:
            warnings.warn(f"Station spacing {v} km is outside typical range (4-50 km).")
        return v

    @field_validator("turnaround_time")
    def validate_turnaround(cls, v):
        if v < 0:
            raise ValueError("Turnaround time cannot be negative")
        if v > 60:
            warnings.warn(
                f"Turnaround time {v} minutes is high (> 60). Ensure units are minutes."
            )
        return v

    @field_validator("ctd_descent_rate", "ctd_ascent_rate")
    def validate_ctd_rates(cls, v):
        if not (0.5 <= v <= 2.0):
            raise ValueError(f"CTD Rate {v} m/s is outside safe limits (0.5 - 2.0).")
        return v

    @field_validator("day_start_hour", "day_end_hour")
    def validate_hours(cls, v):
        if not (0 <= v <= 23):
            raise ValueError("Hour must be between 0 and 23")
        return v

    @model_validator(mode="after")
    def validate_day_window(self):
        if self.day_start_hour >= self.day_end_hour:
            raise ValueError(
                f"Day start ({self.day_start_hour}) must be before day end ({self.day_end_hour})"
            )
        return self

    @model_validator(mode="after")
    def check_longitude_consistency(self):
        """
        Ensures the entire cruise uses EITHER [-180, 180] OR [0, 360], but not both.
        Example: Cannot have one point at -5 (355) and another at 355 (355) if inputs differ.
        """
        lons = []

        # 1. Collect from Global Anchors
        if self.departure_port:
            lons.append(self.departure_port.position.longitude)
        if self.arrival_port:
            lons.append(self.arrival_port.position.longitude)

        # 2. Collect from Catalog
        if self.stations:
            lons.extend([s.position.longitude for s in self.stations])
        if self.moorings:
            lons.extend([m.position.longitude for m in self.moorings])
        if self.transits:
            for t in self.transits:
                lons.extend([p.longitude for p in t.route])

        # 3. Collect from Legs (Inline Definitions)
        for leg in self.legs:
            # Helper to extract GeoPoint from various inline objects
            def extract_from_list(items):
                if not items:
                    return
                for item in items:
                    if hasattr(item, "position") and isinstance(
                        item.position, GeoPoint
                    ):
                        lons.append(item.position.longitude)
                    elif hasattr(item, "start") and isinstance(item.start, GeoPoint):
                        # Sections / Generators
                        lons.append(item.start.longitude)
                        if hasattr(item, "end") and isinstance(item.end, GeoPoint):
                            lons.append(item.end.longitude)

            extract_from_list(leg.moorings)
            extract_from_list(leg.sections)

            if leg.clusters:
                for cluster in leg.clusters:
                    extract_from_list(cluster.moorings)
                    extract_from_list(cluster.stations)
                    if cluster.generate_transect:
                        lons.append(cluster.generate_transect.start.longitude)
                        lons.append(cluster.generate_transect.end.longitude)

        # 4. Perform the Logic Check
        if not lons:
            return self

        is_system_standard = all(-180 <= x <= 180 for x in lons)
        is_system_positive = all(0 <= x <= 360 for x in lons)

        if not (is_system_standard or is_system_positive):
            # Find the culprits for a helpful error message
            min_lon = min(lons)
            max_lon = max(lons)
            raise ValueError(
                f"Inconsistent Longitude Systems detected across the cruise.\n"
                f"Found values ranging from {min_lon} to {max_lon}.\n"
                f"You must use EITHER [-180, 180] OR [0, 360] consistently, but not both.\n"
                f"(Example: Do not mix -5.0 and 355.0 in the same file)"
            )

        return self
