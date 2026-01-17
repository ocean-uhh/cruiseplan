"""Tests for cruiseplan package API (__init__.py) functions."""

from pathlib import Path
from unittest.mock import patch

import cruiseplan


class TestBathymetryAPI:
    """Test the cruiseplan.bathymetry() API function."""

    @patch("cruiseplan.data.bathymetry.download_bathymetry")
    def test_bathymetry_default_parameters(self, mock_download):
        """Test bathymetry function with default parameters."""
        mock_download.return_value = Path("/data/etopo2022/bathymetry/etopo2022.nc")

        result = cruiseplan.bathymetry()

        # Check that download_bathymetry was called with correct parameters
        mock_download.assert_called_once()
        call_args = mock_download.call_args[1]  # keyword arguments
        assert call_args["source"] == "etopo2022"
        assert isinstance(result, cruiseplan.BathymetryResult)
        assert result.data_file == Path("/data/etopo2022/bathymetry/etopo2022.nc")

    @patch("cruiseplan.data.bathymetry.download_bathymetry")
    @patch("pathlib.Path.mkdir")
    def test_bathymetry_custom_parameters(self, mock_mkdir, mock_download):
        """Test bathymetry function with custom parameters."""
        mock_download.return_value = Path("/custom/gebco2025.nc")

        result = cruiseplan.bathymetry(bathy_source="gebco2025", output_dir="/custom")

        mock_download.assert_called_once()
        call_args = mock_download.call_args[1]
        assert call_args["source"] == "gebco2025"
        assert isinstance(result, cruiseplan.BathymetryResult)
        assert result.data_file == Path("/custom/gebco2025.nc")
        mock_mkdir.assert_called_once()


class TestValidateAPI:
    """Test the cruiseplan.validate() API function."""

    @patch("cruiseplan.api.process_cruise._validate_configuration")
    @patch("cruiseplan.utils.io.validate_input_file")
    def test_validate_success(self, mock_file_validate, mock_validate):
        """Test successful validation."""
        mock_file_validate.return_value = Path("test.yaml")  # Mock file validation
        mock_validate.return_value = (True, [], [])  # success, errors, warnings

        result = cruiseplan.validate("test.yaml")

        mock_validate.assert_called_once()
        assert isinstance(result, cruiseplan.ValidationResult)
        assert bool(result) is True
        assert result.success is True

    @patch("cruiseplan.api.process_cruise._validate_configuration")
    @patch("cruiseplan.utils.io.validate_input_file")
    def test_validate_failure(self, mock_file_validate, mock_validate):
        """Test failed validation."""
        mock_file_validate.return_value = Path("test.yaml")  # Mock file validation
        mock_validate.return_value = (False, ["Error message"], [])

        result = cruiseplan.validate("test.yaml")

        assert isinstance(result, cruiseplan.ValidationResult)
        assert bool(result) is False
        assert result.success is False

    @patch("cruiseplan.api.process_cruise._validate_configuration")
    @patch("cruiseplan.utils.io.validate_input_file")
    def test_validate_custom_parameters(self, mock_file_validate, mock_validate):
        """Test validation with custom parameters."""
        mock_file_validate.return_value = Path("custom.yaml")  # Mock file validation
        mock_validate.return_value = (True, [], [])

        result = cruiseplan.validate(
            config_file="custom.yaml",
            check_depths=True,
            tolerance=15.0,
            bathy_source="gebco2025",
        )

        mock_validate.assert_called_once()
        call_args = mock_validate.call_args[1]
        assert call_args["check_depths"] is True
        assert call_args["tolerance"] == 15.0
        assert call_args["bathymetry_source"] == "gebco2025"
        assert isinstance(result, cruiseplan.ValidationResult)
        assert bool(result) is True
        assert result.success is True


class TestEnrichAPI:
    """Test the cruiseplan.enrich() API function."""

    @patch("cruiseplan.api.process_cruise._enrich_configuration")
    @patch("cruiseplan.utils.io.validate_input_file")
    @patch("cruiseplan.utils.io.validate_output_directory")
    def test_enrich_success(
        self, mock_validate_output, mock_validate_input, mock_enrich
    ):
        """Test successful enrichment."""
        # Mock input file validation
        mock_validate_input.return_value = Path("test.yaml")
        # Mock output directory validation
        mock_validate_output.return_value = Path("data").resolve()

        # Mock enrichment function with proper return
        mock_enrich.return_value = {
            "stations_with_depths_added": 2,
            "stations_with_coords_added": 1,
            "sections_expanded": 0,
            "stations_from_expansion": 0,
            "station_defaults_added": 1,
            "total_stations_processed": 3,
        }

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("pathlib.Path.stat") as mock_stat,
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.touch"),
            patch("pathlib.Path.unlink"),
            patch(
                "cruiseplan.api.process_cruise.load_yaml",
                return_value={"cruise_name": "test"},
            ),
        ):
            mock_stat.return_value.st_size = 100  # Non-empty file
            result = cruiseplan.enrich("test.yaml", add_coords=True, add_depths=True)

        mock_enrich.assert_called_once()
        call_args = mock_enrich.call_args[1]
        assert call_args["add_coords"] is True
        assert call_args["add_depths"] is True

        # Check EnrichResult properties
        assert isinstance(result, cruiseplan.EnrichResult)
        assert result.output_file == Path("data/test_enriched.yaml").resolve()
        assert isinstance(result.files_created, list)
        assert isinstance(result.summary, dict)

    @patch("cruiseplan.api.process_cruise._enrich_configuration")
    @patch("cruiseplan.utils.io.validate_input_file")
    @patch("cruiseplan.utils.io.validate_output_directory")
    def test_enrich_custom_output(
        self, mock_validate_output, mock_validate_input, mock_enrich
    ):
        """Test enrichment with custom output."""
        # Mock input file validation
        mock_validate_input.return_value = Path("custom.yaml")
        # Mock output directory validation
        mock_validate_output.return_value = Path("/custom/path").resolve()

        # Mock enrichment function
        mock_enrich.return_value = {
            "stations_with_depths_added": 0,
            "stations_with_coords_added": 0,
            "sections_expanded": 0,
            "stations_from_expansion": 0,
            "station_defaults_added": 0,
            "total_stations_processed": 1,
        }

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_file", return_value=True),
            patch("pathlib.Path.stat") as mock_stat,
            patch("pathlib.Path.mkdir"),
            patch("pathlib.Path.touch"),
            patch("pathlib.Path.unlink"),
            patch(
                "cruiseplan.api.process_cruise.load_yaml",
                return_value={"cruise_name": "test"},
            ),
        ):
            mock_stat.return_value.st_size = 100  # Non-empty file
            result = cruiseplan.enrich(
                config_file="custom.yaml",
                output_dir="/custom/path",
                output="custom_name",
            )

        mock_enrich.assert_called_once()

        # Check EnrichResult properties
        assert isinstance(result, cruiseplan.EnrichResult)
        assert (
            result.output_file
            == Path("/custom/path/custom_name_enriched.yaml").resolve()
        )


class TestSetupOutputPaths:
    """Test the internal setup_output_paths helper function."""

    @patch("cruiseplan.utils.io.validate_output_directory")
    def test_setup_output_paths_default(self, mock_validate):
        """Test output path setup with defaults."""
        from cruiseplan.utils.io import setup_output_paths

        # Mock the validate function to return the expected path
        expected_path = Path("data").resolve()
        mock_validate.return_value = expected_path

        output_dir, base_name = setup_output_paths("test.yaml")

        assert output_dir == expected_path
        assert base_name == "test"
        mock_validate.assert_called_once_with("data")

    @patch("cruiseplan.utils.io.validate_output_directory")
    def test_setup_output_paths_custom(self, mock_validate):
        """Test output path setup with custom values."""
        from cruiseplan.utils.io import setup_output_paths

        # Mock the validate function to return the expected path
        expected_path = Path("/custom/path").resolve()
        mock_validate.return_value = expected_path

        output_dir, base_name = setup_output_paths(
            "cruise.yaml", output_dir="/custom/path", output="custom_name"
        )

        assert output_dir == expected_path
        assert base_name == "custom_name"
        mock_validate.assert_called_once_with("/custom/path")

    @patch("cruiseplan.utils.io.validate_output_directory")
    def test_setup_output_paths_pathlib_input(self, mock_validate):
        """Test output path setup with pathlib.Path input."""
        from cruiseplan.utils.io import setup_output_paths

        # Mock the validate function to return the expected path
        expected_path = Path("data").resolve()
        mock_validate.return_value = expected_path

        output_dir, base_name = setup_output_paths(Path("test.yaml"))

        assert output_dir == expected_path
        assert base_name == "test"
        mock_validate.assert_called_once_with("data")


# Note: Some API functions like schedule(), process(), pangaea(), map()
# call multiple underlying functions and have more complex workflows.
# These would require more extensive mocking and are candidates for
# integration tests rather than unit tests.
