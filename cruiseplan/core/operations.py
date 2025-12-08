from abc import ABC, abstractmethod
from typing import Optional, List, Any, Union
from cruiseplan.core.validation import (
    StationDefinition,
    MooringDefinition,
    TransitDefinition,
)


class BaseOperation(ABC):
    """Abstract base class for all cruise operations."""

    def __init__(self, name: str, comment: Optional[str] = None):
        self.name = name
        self.comment = comment

    @abstractmethod
    def calculate_duration(self, rules: Any) -> float:
        """Calculate duration in minutes based on provided rules."""
        pass


class PointOperation(BaseOperation):
    """
    Atomic activity at a fixed location.
    Handles both Stations (CTD) and Moorings (Deploy/Recover).
    """

    def __init__(
        self,
        name: str,
        position: tuple,
        depth: float = 0.0,
        duration: float = 0.0,
        comment: str = None,
        op_type: str = "station",
        action: str = None,
    ):
        super().__init__(name, comment)
        self.position = position  # (lat, lon)
        self.depth = depth
        self.manual_duration = duration
        self.op_type = op_type
        self.action = action  # Specific to Moorings

    def calculate_duration(self, rules: Any) -> float:
        # Phase 2 Logic: Manual duration always wins
        if self.manual_duration > 0:
            return self.manual_duration

        # Placeholder for Phase 2 depth-based calculation
        return 0.0

    @classmethod
    def from_pydantic(
        cls, obj: Union[StationDefinition, MooringDefinition]
    ) -> "PointOperation":
        """
        Factory to create a logical operation from a validated Pydantic model.
        Handles the internal 'position' normalization done by FlexibleLocationModel.
        """
        # 1. Extract Position (Guaranteed by validation.py to exist)
        pos = (obj.position.latitude, obj.position.longitude)

        # 2. Extract specific fields based on type
        op_type = "station"
        action = None

        if isinstance(obj, MooringDefinition):
            op_type = "mooring"
            action = obj.action.value  # Enum -> String

        return cls(
            name=obj.name,
            position=pos,
            depth=obj.depth if obj.depth else 0.0,
            duration=obj.duration if obj.duration else 0.0,
            comment=obj.comment,
            op_type=op_type,
            action=action,
        )


class LineOperation(BaseOperation):
    """
    Continuous activity involving movement (Transit, Towyo).
    """

    def __init__(
        self, name: str, route: List[tuple], speed: float = 10.0, comment: str = None
    ):
        super().__init__(name, comment)
        self.route = route  # List of (lat, lon)
        self.speed = speed

    def calculate_duration(self, rules: Any) -> float:
        # Placeholder for Phase 2 distance calculation
        return 0.0

    @classmethod
    def from_pydantic(
        cls, obj: TransitDefinition, default_speed: float
    ) -> "LineOperation":
        # Convert List[GeoPoint] -> List[tuple]
        route_tuples = [(p.latitude, p.longitude) for p in obj.route]

        return cls(
            name=obj.name,
            route=route_tuples,
            speed=obj.vessel_speed if obj.vessel_speed else default_speed,
            comment=obj.comment,
        )
