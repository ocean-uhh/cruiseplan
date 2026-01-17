"""
Result types for CruisePlan API functions.

Provides structured return types for all main API operations.
"""

from pathlib import Path
from typing import Any, Optional

# Import the CruiseSchedule type from calculators
from cruiseplan.calculators import CruiseSchedule


class BaseResult:
    """Base class for all CruisePlan API result types.

    Provides standardized error/warning/file handling and status reporting
    for all API operations. Since 6/7 result types create files, file
    tracking is included in the base class.
    """

    def __init__(
        self,
        summary: dict[str, Any],
        success_indicator: Any = None,
        files_created: list[Path] = None,
        errors: list[str] = None,
        warnings: list[str] = None,
    ):
        self.summary = summary
        self.files_created = (
            files_created or []
        )  # Default empty list for ValidationResult
        self.errors = errors or []
        self.warnings = warnings or []
        self._success_indicator = success_indicator

    def __bool__(self) -> bool:
        """Success check: no errors and success indicator is truthy."""
        return len(self.errors) == 0 and bool(self._success_indicator)

    def __str__(self) -> str:
        """Standard string representation with error/warning/file counts."""
        if self:
            parts = [f"✅ {self._operation_name} complete"]
            if self.files_created:
                parts.append(f"({len(self.files_created)} files)")
            if self.warnings:
                parts.append(f"({len(self.warnings)} warnings)")
            return " ".join(parts)
        else:
            return f"❌ {self._operation_name} failed ({len(self.errors)} errors, {len(self.warnings)} warnings)"

    @property
    def _operation_name(self) -> str:
        """Override in subclasses for better status messages."""
        return self.__class__.__name__.replace("Result", "")

    @property
    def files_count(self) -> int:
        """Number of files created by this operation."""
        return len(self.files_created)

    @property
    def has_issues(self) -> bool:
        """True if there are any errors or warnings."""
        return len(self.errors) > 0 or len(self.warnings) > 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_file(self, file_path: Path) -> None:
        """Add a created file to the result."""
        self.files_created.append(file_path)


class EnrichResult(BaseResult):
    """Structured result from enrich operation."""

    def __init__(
        self, output_file: Path, files_created: list[Path], summary: dict[str, Any]
    ):
        super().__init__(
            summary=summary, success_indicator=output_file, files_created=files_created
        )
        self.output_file = output_file  # Keep for backward compatibility

    @property
    def _operation_name(self) -> str:
        return "Enrichment"


class ValidationResult(BaseResult):
    """Structured result from validate operation."""

    def __init__(
        self,
        success: bool,
        errors: list[str],
        warnings: list[str],
        summary: dict[str, Any],
    ):
        super().__init__(
            summary=summary,
            success_indicator=success,
            files_created=[],  # ValidationResult doesn't create files
            errors=errors,
            warnings=warnings,
        )
        self.success = success  # Keep for backward compatibility

    @property
    def _operation_name(self) -> str:
        return "Validation"


class ScheduleResult(BaseResult):
    """Structured result from schedule operation."""

    def __init__(
        self,
        timeline: Optional[CruiseSchedule],
        files_created: list[Path],
        summary: dict[str, Any],
    ):
        super().__init__(
            summary=summary,
            success_indicator=timeline is not None and len(timeline) > 0,
            files_created=files_created,
        )
        self.timeline = timeline

    @property
    def _operation_name(self) -> str:
        if self.timeline:
            return f"Schedule ({len(self.timeline)} activities)"
        return "Schedule"


class PangaeaResult(BaseResult):
    """Structured result from pangaea operation."""

    def __init__(
        self,
        stations_data: Optional[Any],
        files_created: list[Path],
        summary: dict[str, Any],
    ):
        super().__init__(
            summary=summary,
            success_indicator=stations_data is not None,
            files_created=files_created,
        )
        self.stations_data = stations_data

    @property
    def _operation_name(self) -> str:
        if self.stations_data is not None:
            station_count = (
                len(self.stations_data) if hasattr(self.stations_data, "__len__") else 1
            )
            return f"PANGAEA processing ({station_count} stations)"
        return "PANGAEA processing"


class ProcessResult(BaseResult):
    """Structured result from process operation."""

    def __init__(
        self,
        config: Optional[Any],
        files_created: list[Path],
        summary: dict[str, Any],
        errors: list[str] = None,
        warnings: list[str] = None,
    ):
        super().__init__(
            summary=summary,
            success_indicator=config is not None,
            files_created=files_created,
            errors=errors,
            warnings=warnings,
        )
        self.config = config

    @property
    def _operation_name(self) -> str:
        return "Processing"


class MapResult(BaseResult):
    """Structured result from map operation."""

    def __init__(self, map_files: list[Path], format: str, summary: dict[str, Any]):
        super().__init__(
            summary=summary,
            success_indicator=len(map_files) > 0,
            files_created=map_files,  # Standardized naming
        )
        self.map_files = map_files  # Keep for backward compatibility
        self.format = format

    @property
    def _operation_name(self) -> str:
        return f"Map generation ({self.format})"


class BathymetryResult(BaseResult):
    """Structured result from bathymetry operation."""

    def __init__(self, data_file: Optional[Path], source: str, summary: dict[str, Any]):
        # Convert single file to list for consistency
        files_created = [data_file] if data_file else []
        super().__init__(
            summary=summary,
            success_indicator=data_file and data_file.exists(),
            files_created=files_created,
        )
        self.data_file = data_file  # Keep for backward compatibility
        self.source = source

    @property
    def _operation_name(self) -> str:
        return f"Bathymetry download ({self.source})"


# Import the StationPickerResult at the end to avoid circular imports
from cruiseplan.api.stations_api import StationPickerResult

__all__ = [
    "BaseResult",
    "BathymetryResult",
    "EnrichResult",
    "MapResult",
    "ProcessResult",
    "ScheduleResult",
    "StationPickerResult",
    "ValidationResult",
]
