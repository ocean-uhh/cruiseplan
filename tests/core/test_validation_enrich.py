"""
Tests for enrichment and validation functions in core/validation.py.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.api.process_cruise import (
    enrich_configuration,
    validate_configuration,
    validate_depth_accuracy,
)
from cruiseplan.schema import POINTS_FIELD


class TestEnrichConfiguration:
    """Test the enrich_configuration core function."""

    @patch("cruiseplan.api.process_cruise.save_yaml")
    @patch("cruiseplan.data.bathymetry.BathymetryManager")
    @patch("cruiseplan.core.cruise.CruiseInstance")
    @patch("builtins.open")
    @patch("cruiseplan.api.process_cruise.load_yaml")
    def test_enrich_depths_only(
        self,
        mock_yaml_load,
        mock_open,
        mock_cruise_class,
        mock_bathymetry_class,
        mock_save_yaml,
    ):
        """Test enriching depths only."""
        # Setup file reading mocks
        config_data = {
            "points": [{"name": "STN_001", "latitude": 50.0, "longitude": -40.0}]
        }
        mock_yaml_load.return_value = config_data

        # Setup mocks - now mocking from_dict instead of constructor
        mock_cruise = MagicMock()
        mock_cruise_class.from_dict.return_value = mock_cruise
        mock_cruise.raw_data = config_data

        # Mock station without water_depth
        mock_station = MagicMock()
        mock_station.depth = None
        mock_station.water_depth = None
        mock_station.latitude = 50.0
        mock_station.longitude = -40.0
        mock_cruise.point_registry = {"STN_001": mock_station}

        # Mock the new enrich_depths method to return the expected set
        mock_cruise.enrich_depths.return_value = {"STN_001"}
        mock_cruise.add_coordinate_displays.return_value = 0
        mock_cruise.add_station_defaults.return_value = 0
        mock_cruise.expand_sections.return_value = {
            "sections_expanded": 0,
            "stations_from_expansion": 0,
        }

        # Mock to_commented_dict method for output generation
        mock_cruise.to_commented_dict.return_value = config_data

        # Mock bathymetry (not needed for new approach but keeping for compatibility)
        mock_bathymetry = MagicMock()
        mock_bathymetry_class.return_value = mock_bathymetry
        mock_bathymetry.get_depth_at_point.return_value = (
            -1000.0
        )  # Negative depth (typical bathymetry)

        # Test
        result = enrich_configuration(
            config_path=Path("test.yaml"),
            add_depths=True,
            add_coords=False,
            output_path=Path("output.yaml"),
        )

        # Verify
        assert result["stations_with_depths_added"] == 1
        assert result["stations_with_coords_added"] == 0
        # save_yaml is called once: only for output (no more temp files)
        assert mock_save_yaml.call_count == 1

    @patch("cruiseplan.api.process_cruise.save_yaml")
    @patch("cruiseplan.utils.coordinates.format_ddm_comment")
    @patch("cruiseplan.core.cruise.CruiseInstance")
    @patch("builtins.open")
    @patch("cruiseplan.api.process_cruise.load_yaml")
    def test_enrich_coords_only(
        self,
        mock_yaml_load,
        mock_open,
        mock_cruise_class,
        mock_format_ddm,
        mock_save_yaml,
    ):
        """Test enriching coordinates only."""
        # Setup file reading mocks
        config_data = {
            "points": [{"name": "STN_001", "latitude": 50.0, "longitude": -40.0}]
        }
        mock_yaml_load.return_value = config_data

        # Setup mocks - now mocking from_dict instead of constructor
        mock_cruise = MagicMock()
        mock_cruise_class.from_dict.return_value = mock_cruise
        mock_cruise.raw_data = config_data

        mock_station = MagicMock()
        mock_station.latitude = 50.0
        mock_station.longitude = -40.0
        mock_cruise.point_registry = {"STN_001": mock_station}

        # Mock enrich methods
        mock_cruise.enrich_depths.return_value = set()
        mock_cruise.add_station_defaults.return_value = 0
        mock_cruise.expand_sections.return_value = {
            "sections_expanded": 0,
            "stations_from_expansion": 0,
        }

        # Let add_coordinate_displays work normally but mock its dependency
        def mock_add_coordinate_displays(coord_format):
            # Call the format function as the real method would
            mock_format_ddm(50.0, -40.0)
            return 1

        mock_cruise.add_coordinate_displays.side_effect = mock_add_coordinate_displays

        # Mock to_commented_dict method for output generation
        mock_cruise.to_commented_dict.return_value = config_data

        mock_format_ddm.return_value = "50 00.00'N, 040 00.00'W"

        # Test
        result = enrich_configuration(
            config_path=Path("test.yaml"),
            add_depths=False,
            add_coords=True,
            coord_format="ddm",
            output_path=Path("output.yaml"),
        )

        # Verify
        assert result["stations_with_depths_added"] == 0
        assert result["stations_with_coords_added"] == 1
        mock_format_ddm.assert_called_once_with(50.0, -40.0)
        # save_yaml is called once: only for output (no more temp files)
        assert mock_save_yaml.call_count == 1

    @patch("cruiseplan.core.cruise.CruiseInstance")
    @patch("builtins.open")
    @patch("cruiseplan.api.process_cruise.load_yaml")
    def test_enrich_no_changes_needed(
        self, mock_yaml_load, mock_open, mock_cruise_class
    ):
        """Test when no enrichment is needed."""
        # Setup file reading mocks
        config_data = {POINTS_FIELD: []}
        mock_yaml_load.return_value = config_data

        # Setup mocks - now mocking from_dict instead of constructor
        mock_cruise = MagicMock()
        mock_cruise_class.from_dict.return_value = mock_cruise
        mock_cruise.raw_data = config_data
        mock_cruise.point_registry = {}

        # Mock enrich methods to return empty sets/dicts
        mock_cruise.enrich_depths.return_value = set()
        mock_cruise.add_coordinate_displays.return_value = 0
        mock_cruise.add_station_defaults.return_value = 0
        mock_cruise.expand_sections.return_value = {
            "sections_expanded": 0,
            "stations_from_expansion": 0,
        }

        # Mock to_commented_dict method for output generation
        mock_cruise.to_commented_dict.return_value = config_data

        # Test
        result = enrich_configuration(
            config_path=Path("test.yaml"),
            add_depths=True,
            add_coords=True,
            output_path=Path("output.yaml"),
        )

        # Verify
        assert result["stations_with_depths_added"] == 0
        assert result["stations_with_coords_added"] == 0
        assert result["total_stations_processed"] == 0


class TestValidateConfigurationFile:
    """Test the validate_configuration core function."""

    @patch("cruiseplan.api.process_cruise.format_validation_warnings")
    @patch("cruiseplan.api.process_cruise.check_unexpanded_ctd_sections")
    @patch("cruiseplan.api.process_cruise.check_cruise_metadata")
    @patch("cruiseplan.api.process_cruise._check_cruise_metadata_raw")
    @patch("cruiseplan.api.process_cruise.check_complete_duplicates")
    @patch("cruiseplan.api.process_cruise.check_duplicate_names")
    @patch("cruiseplan.api.process_cruise.validate_depth_accuracy")
    @patch("cruiseplan.data.bathymetry.BathymetryManager")
    @patch("cruiseplan.core.cruise.CruiseInstance")
    def test_validate_success_no_depth_check(
        self,
        mock_cruise_class,
        mock_bathymetry_class,
        mock_validate_depth,
        mock_check_duplicates,
        mock_check_complete_duplicates,
        mock_check_metadata_raw,
        mock_check_metadata,
        mock_check_unexpanded_ctd,
        mock_format_warnings,
    ):
        """Test successful validation without depth checking."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise

        # Mock all validation functions to return no errors/warnings
        mock_check_duplicates.return_value = ([], [])
        mock_check_complete_duplicates.return_value = ([], [])
        mock_check_metadata.return_value = []
        mock_check_metadata_raw.return_value = []
        mock_check_unexpanded_ctd.return_value = []
        mock_format_warnings.return_value = []

        # Test
        success, errors, warnings = validate_configuration(
            config_path=Path("test.yaml"), check_depths=False
        )

        # Verify
        assert success is True
        assert errors == []
        assert warnings == []
        mock_validate_depth.assert_not_called()

    @patch("cruiseplan.api.process_cruise.format_validation_warnings")
    @patch("cruiseplan.api.process_cruise.check_unexpanded_ctd_sections")
    @patch("cruiseplan.api.process_cruise.check_cruise_metadata")
    @patch("cruiseplan.api.process_cruise._check_cruise_metadata_raw")
    @patch("cruiseplan.api.process_cruise.check_complete_duplicates")
    @patch("cruiseplan.api.process_cruise.check_duplicate_names")
    @patch("cruiseplan.api.process_cruise.validate_depth_accuracy")
    @patch("cruiseplan.data.bathymetry.BathymetryManager")
    @patch("cruiseplan.core.cruise.CruiseInstance")
    def test_validate_success_with_depth_check(
        self,
        mock_cruise_class,
        mock_bathymetry_class,
        mock_validate_depth,
        mock_check_duplicates,
        mock_check_complete_duplicates,
        mock_check_metadata_raw,
        mock_check_metadata,
        mock_check_unexpanded_ctd,
        mock_format_warnings,
    ):
        """Test successful validation with depth checking."""
        # Setup mocks
        mock_cruise = MagicMock()
        mock_cruise_class.return_value = mock_cruise

        mock_bathymetry = MagicMock()
        mock_bathymetry_class.return_value = mock_bathymetry

        # Mock all validation functions
        mock_check_duplicates.return_value = ([], [])
        mock_check_complete_duplicates.return_value = ([], [])
        mock_check_metadata.return_value = []
        mock_check_metadata_raw.return_value = []
        mock_check_unexpanded_ctd.return_value = []
        mock_format_warnings.return_value = []
        mock_validate_depth.return_value = (2, ["Warning about Station A"])

        # Test
        success, errors, warnings = validate_configuration(
            config_path=Path("test.yaml"),
            check_depths=True,
            tolerance=15.0,
            bathymetry_source="gebco2025",
        )

        # Verify
        assert success is True
        assert errors == []
        assert warnings == ["Warning about Station A"]
        # Verify that the depth validation function was called
        mock_validate_depth.assert_called_once()

    @patch("cruiseplan.core.cruise.CruiseInstance")
    def test_validate_pydantic_error(self, mock_cruise_class):
        """Test validation with Pydantic validation error."""
        from pydantic import ValidationError

        # Create a realistic validation error
        try:
            # This will create a proper ValidationError with the expected structure
            from pydantic import BaseModel, Field

            class TestModel(BaseModel):
                depth: float = Field(..., gt=0)

            TestModel(depth=-100)  # This should trigger validation error
        except ValidationError as validation_error:
            mock_cruise_class.side_effect = validation_error

        # Test
        success, errors, warnings = validate_configuration(
            config_path=Path("test.yaml")
        )

        # Verify
        assert success is False
        assert len(errors) == 1
        assert "depth" in errors[0]
        assert "greater than 0" in errors[0]
        assert warnings == []

    @patch("cruiseplan.core.cruise.CruiseInstance")
    def test_validate_general_error(self, mock_cruise_class):
        """Test validation with general error."""
        mock_cruise_class.side_effect = RuntimeError("File not found")

        # Test
        success, errors, warnings = validate_configuration(
            config_path=Path("test.yaml")
        )

        # Verify
        assert success is False
        assert len(errors) == 1
        assert "Configuration loading error: File not found" in errors[0]
        assert warnings == []


class TestValidateDepthAccuracy:
    """Test the validate_depth_accuracy core function."""

    def test_depth_accuracy_within_tolerance(self):
        """Test depth accuracy check when depths are within tolerance."""
        # Setup mock cruise and station
        mock_cruise = MagicMock()
        mock_station = MagicMock()
        mock_station.water_depth = 1000.0
        mock_station.depth = None
        mock_station.latitude = 50.0
        mock_station.longitude = -40.0
        mock_cruise.point_registry = {"STN_001": mock_station}

        # Setup mock bathymetry manager
        mock_bathymetry = MagicMock()
        mock_bathymetry.get_depth_at_point.return_value = -1050.0  # 5% difference

        # Test with 10% tolerance
        stations_checked, warnings = validate_depth_accuracy(
            mock_cruise, mock_bathymetry, tolerance=10.0
        )

        # Verify
        assert stations_checked == 1
        assert warnings == []

    def test_depth_accuracy_outside_tolerance(self):
        """Test depth accuracy check when depths are outside tolerance."""
        # Setup mock cruise and station
        mock_cruise = MagicMock()
        mock_station = MagicMock()
        mock_station.water_depth = 1000.0
        mock_station.depth = None
        mock_station.latitude = 50.0
        mock_station.longitude = -40.0
        mock_cruise.point_registry = {"STN_001": mock_station}

        # Setup mock bathymetry manager
        mock_bathymetry = MagicMock()
        mock_bathymetry.get_depth_at_point.return_value = -1200.0  # 20% difference

        # Test with 10% tolerance
        stations_checked, warnings = validate_depth_accuracy(
            mock_cruise, mock_bathymetry, tolerance=10.0
        )

        # Verify
        assert stations_checked == 1
        assert len(warnings) == 1
        assert "STN_001" in warnings[0]
        assert "depth discrepancy" in warnings[0]

    def test_depth_accuracy_no_bathymetry_data(self):
        """Test depth accuracy check when bathymetry data is unavailable."""
        # Setup mock cruise and station
        mock_cruise = MagicMock()
        mock_station = MagicMock()
        mock_station.water_depth = 1000.0
        mock_station.depth = None
        mock_station.latitude = 50.0
        mock_station.longitude = -40.0
        mock_cruise.point_registry = {"STN_001": mock_station}

        # Setup mock bathymetry manager with no data
        mock_bathymetry = MagicMock()
        mock_bathymetry.get_depth_at_point.return_value = None

        # Test
        stations_checked, warnings = validate_depth_accuracy(
            mock_cruise, mock_bathymetry, tolerance=10.0
        )

        # Verify
        assert stations_checked == 1
        assert len(warnings) == 1
        assert "could not verify depth" in warnings[0]

    def test_depth_accuracy_station_no_depth(self):
        """Test depth accuracy check when station has no depth."""
        # Setup mock cruise and station without depth
        mock_cruise = MagicMock()
        mock_station = MagicMock()
        mock_station.water_depth = None
        mock_station.depth = None
        mock_cruise.point_registry = {"STN_001": mock_station}

        mock_bathymetry = MagicMock()

        # Test
        stations_checked, warnings = validate_depth_accuracy(
            mock_cruise, mock_bathymetry, tolerance=10.0
        )

        # Verify
        assert stations_checked == 0
        assert warnings == []


if __name__ == "__main__":
    pytest.main([__file__])
