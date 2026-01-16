"""
Tests for BaseResult class and standardized result type functionality.

Tests both backward compatibility and new features provided by the BaseResult base class.
"""

from pathlib import Path

import pytest

from cruiseplan.types import (
    BaseResult,
    BathymetryResult,
    EnrichResult,
    MapResult,
    PangaeaResult,
    ProcessResult,
    ScheduleResult,
    ValidationResult,
)


class TestBaseResultCore:
    """Test core BaseResult functionality."""

    def test_base_result_initialization(self):
        """Test BaseResult can be created with all parameters."""
        result = BaseResult(
            summary={"test": "data"},
            success_indicator=True,
            files_created=[Path("test.txt")],
            errors=["error1"],
            warnings=["warning1"],
        )

        assert result.summary == {"test": "data"}
        assert result.files_created == [Path("test.txt")]
        assert result.errors == ["error1"]
        assert result.warnings == ["warning1"]
        assert result._success_indicator == True

    def test_base_result_defaults(self):
        """Test BaseResult defaults to empty lists."""
        result = BaseResult(summary={"test": "data"})

        assert result.files_created == []
        assert result.errors == []
        assert result.warnings == []
        assert result._success_indicator is None

    def test_success_logic(self):
        """Test boolean success logic."""
        # Success: no errors + truthy success indicator
        success_result = BaseResult({"test": "data"}, success_indicator=True)
        assert bool(success_result) == True

        # Failure: has errors
        error_result = BaseResult(
            {"test": "data"}, success_indicator=True, errors=["error"]
        )
        assert bool(error_result) == False

        # Failure: no success indicator
        no_indicator = BaseResult({"test": "data"})
        assert bool(no_indicator) == False

        # Failure: both errors and no indicator
        double_fail = BaseResult({"test": "data"}, errors=["error"])
        assert bool(double_fail) == False

    def test_error_warning_management(self):
        """Test error and warning management methods."""
        result = BaseResult({"test": "data"})

        # Initially no issues
        assert result.has_issues == False

        # Add error
        result.add_error("Something went wrong")
        assert len(result.errors) == 1
        assert result.errors[0] == "Something went wrong"
        assert result.has_issues == True

        # Add warning
        result.add_warning("Potential issue")
        assert len(result.warnings) == 1
        assert result.warnings[0] == "Potential issue"
        assert result.has_issues == True

    def test_file_management(self):
        """Test file creation tracking."""
        result = BaseResult({"test": "data"})

        # Initially no files
        assert result.files_count == 0

        # Add files
        result.add_file(Path("output1.txt"))
        result.add_file(Path("output2.csv"))

        assert result.files_count == 2
        assert len(result.files_created) == 2
        assert Path("output1.txt") in result.files_created
        assert Path("output2.csv") in result.files_created

    def test_string_representations(self):
        """Test standardized string output."""
        # Success with files and warnings
        success_result = BaseResult(
            {"test": "data"},
            success_indicator=True,
            files_created=[Path("out1.txt"), Path("out2.txt")],
            warnings=["warning1"],
        )
        expected = "✅ Base complete (2 files) (1 warnings)"
        assert str(success_result) == expected

        # Success with no files or warnings
        clean_success = BaseResult({"test": "data"}, success_indicator=True)
        assert str(clean_success) == "✅ Base complete"

        # Failure with errors and warnings
        failure_result = BaseResult(
            {"test": "data"}, errors=["error1", "error2"], warnings=["warning1"]
        )
        expected = "❌ Base failed (2 errors, 1 warnings)"
        assert str(failure_result) == expected


class TestBackwardCompatibility:
    """Test that all existing code patterns still work."""

    def test_enrich_result_backward_compatibility(self):
        """Test EnrichResult preserves all original attributes and behavior."""
        output_file = Path("test_enriched.yaml")
        files_created = [Path("test_enriched.yaml"), Path("log.txt")]
        summary = {"stations_enriched": 5, "warnings": 2}

        result = EnrichResult(output_file, files_created, summary)

        # Original attributes must exist
        assert result.output_file == output_file
        assert result.files_created == files_created
        assert result.summary == summary

        # Original boolean logic (should be True if output_file exists)
        assert bool(result) == True

        # New attributes should also work
        assert result.files_count == 2
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_backward_compatibility(self):
        """Test ValidationResult preserves critical .success attribute."""
        errors = ["Configuration invalid"]
        warnings = ["Deprecated field used"]
        summary = {"rules_checked": 10, "passed": 8}

        # Test successful validation
        success_result = ValidationResult(True, [], warnings, summary)
        assert success_result.success == True  # Critical backward compatibility
        assert success_result.errors == []
        assert success_result.warnings == warnings
        assert success_result.summary == summary
        assert bool(success_result) == True

        # Test failed validation
        fail_result = ValidationResult(False, errors, warnings, summary)
        assert fail_result.success == False  # Critical backward compatibility
        assert fail_result.errors == errors
        assert fail_result.warnings == warnings
        assert bool(fail_result) == False

    def test_bathymetry_result_backward_compatibility(self):
        """Test BathymetryResult preserves data_file and source attributes."""
        data_file = Path("etopo2022.nc")
        source = "etopo2022"
        summary = {"file_size_mb": 500, "download_time": 120}

        result = BathymetryResult(data_file, source, summary)

        # Original attributes must exist
        assert result.data_file == data_file
        assert result.source == source
        assert result.summary == summary

        # File should be converted to list in base class
        assert result.files_created == [data_file]
        assert result.files_count == 1

    def test_map_result_backward_compatibility(self):
        """Test MapResult preserves map_files and format attributes."""
        map_files = [Path("cruise_map.pdf"), Path("cruise_map.png")]
        format_type = "all"
        summary = {"maps_generated": 2, "total_size_mb": 15}

        result = MapResult(map_files, format_type, summary)

        # Original attributes must exist
        assert result.map_files == map_files
        assert result.format == format_type
        assert result.summary == summary

        # Files should be standardized in base class
        assert result.files_created == map_files
        assert result.files_count == 2

    def test_schedule_result_preserves_timeline_logic(self):
        """Test ScheduleResult preserves timeline-based success logic."""
        # Mock timeline data
        timeline_data = [
            {"activity": "transit", "duration_minutes": 60},
            {"activity": "ctd_station", "duration_minutes": 45},
        ]
        files_created = [Path("schedule.html"), Path("timeline.csv")]
        summary = {"total_duration_hours": 1.75, "activities": 2}

        result = ScheduleResult(timeline_data, files_created, summary)

        # Original attributes and logic
        assert result.timeline == timeline_data
        assert result.files_created == files_created
        assert result.summary == summary

        # Success should be based on timeline existence and length
        assert bool(result) == True

        # Test empty timeline
        empty_result = ScheduleResult([], files_created, summary)
        assert bool(empty_result) == False


class TestNewFunctionality:
    """Test new features provided by BaseResult."""

    def test_error_warnings_affect_string_output(self):
        """Test that errors and warnings show up in string representations."""
        result = EnrichResult(Path("test.yaml"), [Path("out.yaml")], {})

        # Add some issues
        result.add_error("Missing bathymetry data")
        result.add_warning("Large file size")
        result.add_warning("Deprecated format")

        # Should show failure due to errors
        output = str(result)
        assert "failed" in output
        assert "1 errors" in output
        assert "2 warnings" in output

    def test_file_tracking_across_operations(self):
        """Test standardized file tracking works for all result types."""
        # Test different result types can all track files consistently
        enrich = EnrichResult(Path("config.yaml"), [], {})
        process = ProcessResult({"config": True}, [], {})
        pangaea = PangaeaResult({"stations": 5}, [], {})

        # All should start with empty files
        for result in [enrich, process, pangaea]:
            assert result.files_count == 0

        # Add files to each
        enrich.add_file(Path("enriched.yaml"))
        process.add_file(Path("timeline.html"))
        process.add_file(Path("summary.csv"))
        pangaea.add_file(Path("stations.json"))

        # Verify counts
        assert enrich.files_count == 1  # Original files_created was [], plus 1 added
        assert process.files_count == 2
        assert pangaea.files_count == 1

    def test_operation_names_are_descriptive(self):
        """Test that _operation_name provides useful context."""
        # Test with specific data to ensure operation names are informative
        bathy = BathymetryResult(Path("data.nc"), "gebco2025", {})
        assert "gebco2025" in str(bathy)

        validation = ValidationResult(True, [], [], {})
        assert "Validation" in str(validation)

        map_result = MapResult([Path("map.pdf")], "pdf", {})
        assert "pdf" in str(map_result)

    def test_has_issues_property(self):
        """Test has_issues property correctly identifies problems."""
        result = ProcessResult({"valid": True}, [], {})

        # No issues initially
        assert result.has_issues == False

        # Add warning - should have issues but still succeed
        result.add_warning("Performance slow")
        assert result.has_issues == True
        assert bool(result) == True  # Still succeeds

        # Add error - should have issues and fail
        result.add_error("Critical failure")
        assert result.has_issues == True
        assert bool(result) == False  # Now fails

    def test_cross_result_error_aggregation(self):
        """Test that errors can be aggregated across multiple operations."""
        # Simulate running multiple operations
        enrich_result = EnrichResult(Path("test.yaml"), [Path("out.yaml")], {})
        enrich_result.add_warning("Large coordinate file")

        validate_result = ValidationResult(False, ["Invalid coordinates"], [], {})

        schedule_result = ScheduleResult([], [], {})
        schedule_result.add_error("Timeline generation failed")
        schedule_result.add_warning("Weather data unavailable")

        # Aggregate all issues
        all_errors = []
        all_warnings = []
        all_files = []

        for result in [enrich_result, validate_result, schedule_result]:
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
            all_files.extend(result.files_created)

        # Verify aggregation worked
        assert len(all_errors) == 2  # 1 from validation, 1 from schedule
        assert len(all_warnings) == 2  # 1 from enrich, 1 from schedule
        assert len(all_files) == 1  # Only enrich created files

        assert "Invalid coordinates" in all_errors
        assert "Timeline generation failed" in all_errors
        assert "Large coordinate file" in all_warnings
        assert "Weather data unavailable" in all_warnings


if __name__ == "__main__":
    pytest.main([__file__])
