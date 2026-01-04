"""
Tests for output formatting utility functions.

This module tests all formatting functions in cruiseplan.utils.output_formatting
to ensure consistent output presentation and path management across CLI commands.
"""

from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from cruiseplan.utils.output_formatting import (
    _construct_output_path,
    _determine_output_basename,
    _determine_output_directory,
    _format_coordinate_summary,
    _format_duration,
    _format_file_list,
    _format_operation_summary,
    _format_output_summary,
    _format_progress_bar,
    _format_section_header,
    _format_size_summary,
    _format_table_row,
    _format_timeline_summary,
    _format_validation_results,
    _generate_multi_format_paths,
    _standardize_output_setup,
    _validate_output_directory,
)


class TestTimelineFormatting:
    """Test timeline formatting functions."""

    def test_format_timeline_summary_basic(self):
        """Test basic timeline summary formatting."""
        timeline = [
            {"label": "STN_001", "duration_minutes": 120, "op_type": "station"},
            {"label": "Transit_01", "duration_minutes": 60, "op_type": "transit"},
        ]

        result = _format_timeline_summary(timeline, 3.0)
        expected = "Timeline: 2 activities | 3.0 hours total duration | Types: 1 station, 1 transit"
        assert result == expected

    def test_format_timeline_summary_empty(self):
        """Test timeline summary with empty timeline."""
        result = _format_timeline_summary([], 0.0)
        expected = "Timeline: 0 activities | 0.0 hours total duration"
        assert result == expected

    def test_format_timeline_summary_no_types(self):
        """Test timeline summary with no op_type fields."""
        timeline = [
            {"label": "STN_001", "duration_minutes": 120},
            {"label": "STN_002", "duration_minutes": 90},
        ]

        result = _format_timeline_summary(timeline, 3.5)
        expected = (
            "Timeline: 2 activities | 3.5 hours total duration | Types: 2 unknown"
        )
        assert result == expected


class TestFileListFormatting:
    """Test file list formatting functions."""

    def test_format_file_list_relative_paths(self, tmp_path):
        """Test file list with relative paths."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.csv"
        files = [file1, file2]

        result = _format_file_list(files, tmp_path)
        expected = "• file1.txt\\n• file2.csv"
        assert result == expected

    def test_format_file_list_absolute_paths(self, tmp_path):
        """Test file list with absolute paths outside base."""
        other_dir = tmp_path.parent / "other"
        file1 = tmp_path / "file1.txt"
        file2 = other_dir / "file2.csv"
        files = [file1, file2]

        result = _format_file_list(files, tmp_path)
        lines = result.split("\\n")
        assert "• file1.txt" in lines[0]
        assert str(file2) in lines[1]  # Absolute path for file outside base

    def test_format_file_list_empty(self):
        """Test file list formatting with empty list."""
        result = _format_file_list([])
        assert result == "No files generated"

    def test_format_file_list_no_base_dir(self, tmp_path):
        """Test file list formatting without base directory."""
        file1 = tmp_path / "file1.txt"
        files = [file1]

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = _format_file_list(files)
            assert result == "• file1.txt"


class TestDurationFormatting:
    """Test duration formatting functions."""

    def test_format_duration_minutes_only(self):
        """Test duration formatting for minutes only."""
        assert _format_duration(45) == "45m"
        assert _format_duration(1.5) == "2m"  # Rounded
        assert _format_duration(59.9) == "60m"

    def test_format_duration_hours_only(self):
        """Test duration formatting for exact hours."""
        assert _format_duration(60) == "1h"
        assert _format_duration(120) == "2h"
        assert _format_duration(180) == "3h"

    def test_format_duration_hours_and_minutes(self):
        """Test duration formatting for hours and minutes."""
        assert _format_duration(90) == "1h 30m"
        assert _format_duration(125) == "2h 5m"
        assert _format_duration(90.5) == "1h 30m"  # 90.5 rounds to 90 minutes = 1h 30m


class TestCoordinateFormatting:
    """Test coordinate formatting functions."""

    def test_format_coordinate_summary_all_positive(self):
        """Test coordinate formatting with all positive values."""
        result = _format_coordinate_summary((10.0, 20.0), (5.0, 15.0))
        expected = "Coordinates: 10.0°N to 20.0°N, 5.0°E to 15.0°E"
        assert result == expected

    def test_format_coordinate_summary_all_negative(self):
        """Test coordinate formatting with all negative values."""
        result = _format_coordinate_summary((-20.0, -10.0), (-15.0, -5.0))
        expected = "Coordinates: 10.0°S to 20.0°S, 5.0°W to 15.0°W"
        assert result == expected

    def test_format_coordinate_summary_mixed(self):
        """Test coordinate formatting with mixed positive/negative."""
        result = _format_coordinate_summary((-10.0, 20.0), (-15.0, 10.0))
        expected = "Coordinates: 10.0°S to 20.0°N, 15.0°W to 10.0°E"
        assert result == expected


class TestValidationFormatting:
    """Test validation result formatting functions."""

    def test_format_validation_results_success_no_warnings(self):
        """Test validation formatting with complete success."""
        result = _format_validation_results(True, [], [])
        expected = "✅ All validations passed - configuration is valid!"
        assert result == expected

    def test_format_validation_results_success_with_warnings(self):
        """Test validation formatting with success but warnings."""
        warnings = ["Warning 1", "Warning 2"]
        result = _format_validation_results(True, [], warnings)
        expected = "✅ Validation passed with 2 warnings"
        assert result == expected

    def test_format_validation_results_failure_errors_only(self):
        """Test validation formatting with errors only."""
        errors = ["Error 1", "Error 2"]
        result = _format_validation_results(False, errors, [])
        expected = "❌ Validation failed with 2 errors"
        assert result == expected

    def test_format_validation_results_failure_errors_and_warnings(self):
        """Test validation formatting with errors and warnings."""
        errors = ["Error 1"]
        warnings = ["Warning 1", "Warning 2"]
        result = _format_validation_results(False, errors, warnings)
        expected = "❌ Validation failed with 1 errors and 2 warnings"
        assert result == expected


class TestProgressBarFormatting:
    """Test progress bar formatting functions."""

    def test_format_progress_bar_basic(self):
        """Test basic progress bar formatting."""
        result = _format_progress_bar(7, 10, "Processing")
        assert "Processing: [" in result
        assert "] 70% (7/10)" in result
        assert "#######..." in result

    def test_format_progress_bar_complete(self):
        """Test progress bar at 100% completion."""
        result = _format_progress_bar(10, 10, "Complete")
        assert "Complete: [" in result
        assert "] 100% (10/10)" in result

    def test_format_progress_bar_no_description(self):
        """Test progress bar without description."""
        result = _format_progress_bar(5, 10)
        assert result == "[##########..........] 50% (5/10)"

    def test_format_progress_bar_zero_total(self):
        """Test progress bar with zero total."""
        result = _format_progress_bar(0, 0, "Done")
        assert result == "Done: 100%"


class TestSizeFormatting:
    """Test file size formatting functions."""

    def test_format_size_summary_bytes(self, tmp_path):
        """Test size formatting for small files (bytes)."""
        file1 = tmp_path / "small.txt"
        file1.write_text("test")  # 4 bytes

        result = _format_size_summary([file1])
        assert result == "1 files, 4 bytes total"

    def test_format_size_summary_kilobytes(self, tmp_path):
        """Test size formatting for KB files."""
        file1 = tmp_path / "medium.txt"
        file1.write_text("x" * 2048)  # 2048 bytes = 2.0 KB

        result = _format_size_summary([file1])
        assert result == "1 files, 2.0 KB total"

    def test_format_size_summary_megabytes(self, tmp_path):
        """Test size formatting for MB files."""
        file1 = tmp_path / "large.txt"
        file1.write_bytes(b"x" * (2 * 1024 * 1024))  # 2 MB

        result = _format_size_summary([file1])
        assert result == "1 files, 2.0 MB total"

    def test_format_size_summary_empty_list(self):
        """Test size formatting with empty file list."""
        result = _format_size_summary([])
        assert result == "No files generated"

    def test_format_size_summary_nonexistent_files(self, tmp_path):
        """Test size formatting with nonexistent files."""
        missing_file = tmp_path / "missing.txt"
        result = _format_size_summary([missing_file])
        assert result == "Files not found"


class TestOperationFormatting:
    """Test operation summary formatting functions."""

    def test_format_operation_summary_success(self):
        """Test operation summary with success status."""
        result = _format_operation_summary("Download", "success")
        assert result == "✅ Download: Success"

    def test_format_operation_summary_with_details(self):
        """Test operation summary with details."""
        details = {"files": 3, "size": "1.2MB"}
        result = _format_operation_summary("Download", "success", details)
        assert result == "✅ Download: Success (files=3, size=1.2MB)"

    def test_format_operation_summary_warning(self):
        """Test operation summary with warning status."""
        result = _format_operation_summary("Validation", "warning")
        assert result == "⚠️ Validation: Warning"

    def test_format_operation_summary_error(self):
        """Test operation summary with error status."""
        result = _format_operation_summary("Process", "error")
        assert result == "❌ Process: Error"

    def test_format_operation_summary_unknown_status(self):
        """Test operation summary with unknown status."""
        result = _format_operation_summary("Custom", "unknown")
        assert result == "• Custom: Unknown"


class TestTableFormatting:
    """Test table formatting functions."""

    def test_format_table_row_normal(self):
        """Test table row formatting with normal content."""
        columns = ["Name", "Type", "Duration"]
        widths = [10, 8, 12]

        result = _format_table_row(columns, widths)
        expected = "Name       | Type     | Duration    "
        assert result == expected

    def test_format_table_row_truncated(self):
        """Test table row formatting with truncated content."""
        columns = ["Very long station name", "Type", "Duration"]
        widths = [10, 8, 12]

        result = _format_table_row(columns, widths)
        expected = "Very lo... | Type     | Duration    "
        assert result == expected


class TestSectionHeaderFormatting:
    """Test section header formatting functions."""

    def test_format_section_header_normal(self):
        """Test section header with normal title."""
        result = _format_section_header("Test Section", 40)
        expected = "============= Test Section ============="
        assert result == expected

    def test_format_section_header_long_title(self):
        """Test section header with long title."""
        long_title = "This is a very long section title that needs truncation"
        result = _format_section_header(long_title, 40)

        assert "This is a very long section title..." in result
        assert len(result) <= 40

    def test_format_section_header_default_width(self):
        """Test section header with default width."""
        result = _format_section_header("Test")
        assert len(result) <= 60
        assert "Test" in result


class TestOutputBasenameHandling:
    """Test output basename determination functions."""

    def test_determine_output_basename_from_args(self):
        """Test basename determination from CLI arguments."""
        args = Namespace(output="my_file")
        result = _determine_output_basename(args)
        assert result == "my_file"

    def test_determine_output_basename_with_spaces(self):
        """Test basename determination with spaces."""
        args = Namespace(output="My Cool File")
        result = _determine_output_basename(args)
        assert result == "My_Cool_File"

    def test_determine_output_basename_from_cruise_name(self):
        """Test basename determination from cruise name."""
        args = Namespace()
        result = _determine_output_basename(args, "Atlantic Survey")
        assert result == "Atlantic_Survey"

    def test_determine_output_basename_fallback(self):
        """Test basename determination with fallback."""
        args = Namespace()
        result = _determine_output_basename(args)
        assert result == "cruise_output"


class TestOutputDirectoryHandling:
    """Test output directory determination functions."""

    def test_determine_output_directory_from_args(self):
        """Test output directory from arguments."""
        args = Namespace(output_dir="results")
        result = _determine_output_directory(args)
        assert result == Path("results")

    def test_determine_output_directory_default(self):
        """Test output directory with default."""
        args = Namespace()
        result = _determine_output_directory(args)
        assert result == Path("data")


class TestOutputPathConstruction:
    """Test output path construction functions."""

    def test_construct_output_path_basic(self):
        """Test basic output path construction."""
        result = _construct_output_path("test", Path("data"), "_enriched", ".yaml")
        expected = Path("data/test_enriched.yaml")
        assert result == expected

    def test_construct_output_path_with_format(self):
        """Test output path construction with format-specific suffix."""
        result = _construct_output_path(
            "cruise", Path("output"), "_schedule", ".html", "_timeline"
        )
        expected = Path("output/cruise_schedule_timeline.html")
        assert result == expected

    def test_construct_output_path_minimal(self):
        """Test output path construction with minimal parameters."""
        result = _construct_output_path("test", Path("data"))
        expected = Path("data/test")
        assert result == expected


class TestMultiFormatPaths:
    """Test multi-format path generation functions."""

    def test_generate_multi_format_paths_default_extensions(self):
        """Test multi-format path generation with default extensions."""
        formats = ["html", "csv", "netcdf"]
        result = _generate_multi_format_paths(
            "cruise", Path("data"), formats, "_schedule"
        )

        expected = {
            "html": Path("data/cruise_schedule.html"),
            "csv": Path("data/cruise_schedule.csv"),
            "netcdf": Path("data/cruise_schedule.nc"),
        }
        assert result == expected

    def test_generate_multi_format_paths_custom_extensions(self):
        """Test multi-format path generation with custom extensions."""
        formats = ["custom"]
        extensions = {"custom": ".xyz"}

        result = _generate_multi_format_paths(
            "test", Path("output"), formats, "", extensions
        )

        expected = {"custom": Path("output/test.xyz")}
        assert result == expected

    def test_generate_multi_format_paths_fallback_extension(self):
        """Test multi-format path generation with fallback extension."""
        formats = ["unknown"]
        result = _generate_multi_format_paths("test", Path("data"), formats)

        expected = {"unknown": Path("data/test.unknown")}
        assert result == expected


class TestOutputDirectoryValidation:
    """Test output directory validation functions."""

    def test_validate_output_directory_existing(self, tmp_path):
        """Test validation of existing directory."""
        with patch(
            "cruiseplan.utils.input_validation._validate_directory_writable"
        ) as mock_validate:
            mock_validate.return_value = tmp_path
            result = _validate_output_directory(tmp_path)
            assert result == tmp_path
            mock_validate.assert_called_once_with(tmp_path, True)


class TestStandardizedOutputSetup:
    """Test complete output setup functions."""

    def test_standardize_output_setup_single_format(self):
        """Test standardized setup for single format output."""
        args = Namespace(output="cruise", output_dir="data")

        with patch(
            "cruiseplan.utils.output_formatting._validate_output_directory"
        ) as mock_validate:
            mock_validate.return_value = Path("data")

            output_dir, base_name, format_paths = _standardize_output_setup(
                args, suffix="_enriched", single_format=".yaml"
            )

            assert output_dir == Path("data")
            assert base_name == "cruise"
            assert "single" in format_paths
            assert format_paths["single"] == Path("data/cruise_enriched.yaml")

    def test_standardize_output_setup_multi_formats(self):
        """Test standardized setup for multiple format output."""
        args = Namespace(output="cruise", output_dir="results")

        with patch(
            "cruiseplan.utils.output_formatting._validate_output_directory"
        ) as mock_validate:
            mock_validate.return_value = Path("results")

            output_dir, base_name, format_paths = _standardize_output_setup(
                args, suffix="_schedule", multi_formats=["html", "csv"]
            )

            assert output_dir == Path("results")
            assert base_name == "cruise"
            assert "html" in format_paths
            assert "csv" in format_paths
            assert format_paths["html"] == Path("results/cruise_schedule.html")

    def test_standardize_output_setup_with_cruise_name(self):
        """Test standardized setup using cruise name for basename."""
        args = Namespace(output_dir="data")  # No output specified

        with patch(
            "cruiseplan.utils.output_formatting._validate_output_directory"
        ) as mock_validate:
            mock_validate.return_value = Path("data")

            output_dir, base_name, format_paths = _standardize_output_setup(
                args, cruise_name="Atlantic Survey", single_format=".yaml"
            )

            assert base_name == "Atlantic_Survey"
            assert format_paths["single"] == Path("data/Atlantic_Survey.yaml")


class TestOutputSummaryFormatting:
    """Test output summary formatting functions."""

    def test_format_output_summary_success(self, tmp_path):
        """Test output summary formatting with successful files."""
        file1 = tmp_path / "test1.yaml"
        file2 = tmp_path / "test2.csv"
        file1.write_text("content")
        file2.write_text("data")

        result = _format_output_summary([file1, file2], "Processing")

        assert "✅ Processing completed:" in result
        assert "test1.yaml" in result
        assert "test2.csv" in result
        assert "2 files" in result

    def test_format_output_summary_no_files(self):
        """Test output summary formatting with no files."""
        result = _format_output_summary([], "Processing")
        assert result == "❌ Processing failed - no files generated"

    def test_format_output_summary_missing_files(self, tmp_path):
        """Test output summary formatting with missing files."""
        missing_file = tmp_path / "missing.txt"
        result = _format_output_summary([missing_file], "Processing")
        assert result == "❌ Processing failed - output files not found"

    def test_format_output_summary_without_size(self, tmp_path):
        """Test output summary formatting without size information."""
        file1 = tmp_path / "test.yaml"
        file1.write_text("content")

        result = _format_output_summary([file1], "Processing", include_size=False)

        assert "✅ Processing completed:" in result
        assert "test.yaml" in result
        assert "bytes" not in result  # No size info
