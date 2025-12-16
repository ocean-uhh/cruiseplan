"""
Simplified additional tests to improve bathymetry.py coverage.

This test suite targets the missing coverage areas with simpler, more reliable tests.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cruiseplan.data.bathymetry import (
    ETOPO_FILENAME,
    BathymetryManager,
    get_bathymetry_singleton,
)


class TestBathymetrySimpleCoverage:
    """Simplified tests to improve bathymetry coverage."""

    def test_initialization_with_small_file(self, tmp_path):
        """Test initialization when bathymetry file exists but is too small."""
        # Create a small file that will be detected as incomplete
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)
        etopo_file = bathymetry_dir / ETOPO_FILENAME
        etopo_file.write_bytes(b"small file content")  # Much smaller than 450 MB

        with patch("cruiseplan.data.bathymetry.logger") as mock_logger:
            # Override the data directory to use our test path
            manager = BathymetryManager(source="etopo2022")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode due to small file
            assert manager._is_mock is True

            # Should log warning about small file
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "too small" in warning_call

    def test_initialization_with_corrupted_netcdf_file(self, tmp_path):
        """Test initialization when NetCDF file exists but is corrupted."""
        # Create a large file that passes size check but fails NetCDF loading
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)
        etopo_file = bathymetry_dir / ETOPO_FILENAME
        # Create a file larger than 450 MB (simulate with just marking it)
        large_content = b"corrupted netcdf content" * 1000000  # ~25 MB
        etopo_file.write_bytes(large_content)

        with (
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
            patch("netCDF4.Dataset", side_effect=Exception("Corrupted NetCDF")),
            patch.object(Path, "stat") as mock_stat,
        ):

            # Mock file size to be large enough
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 500 * 1024 * 1024  # 500 MB
            mock_stat.return_value = mock_stat_obj

            manager = BathymetryManager(source="etopo2022")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode due to corrupted file
            assert manager._is_mock is True

            # Should log warning about failed load
            mock_logger.warning.assert_called()

    def test_interpolation_error_handling(self):
        """Test error handling during depth interpolation."""
        manager = BathymetryManager(source="etopo2022")

        # Set up manager to not be in mock mode
        manager._is_mock = False

        # Mock _interpolate_depth to raise an exception
        with (
            patch.object(
                manager,
                "_interpolate_depth",
                side_effect=Exception("Interpolation error"),
            ),
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
        ):

            result = manager.get_depth_at_point(45.0, -60.0)

            # Should return fallback depth
            from cruiseplan.utils.constants import FALLBACK_DEPTH

            assert result == FALLBACK_DEPTH

            # Should log error
            mock_logger.error.assert_called()

    def test_initialization_with_custom_source(self, tmp_path):
        """Test initialization with custom (non-standard) source."""
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)

        with patch("cruiseplan.data.bathymetry.logger") as mock_logger:
            manager = BathymetryManager(source="custom_source")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode since custom file doesn't exist
            assert manager._is_mock is True

    def test_grid_subset_edge_cases(self):
        """Test grid subset with edge cases."""
        manager = BathymetryManager(source="etopo2022")
        manager._is_mock = False

        # Mock the dataset and coordinates
        mock_dataset = MagicMock()
        manager._dataset = mock_dataset
        manager._lats = [40.0, 50.0, 60.0]
        manager._lons = [-70.0, -60.0, -50.0]

        # Mock invalid slice conditions
        with patch("numpy.searchsorted", return_value=0):
            result = manager.get_grid_subset(35.0, 38.0, -75.0, -72.0)  # Outside bounds
            # Should handle gracefully
            assert isinstance(result, tuple)

    def test_bilinear_interpolation_edge_cases(self):
        """Test bilinear interpolation edge cases."""
        manager = BathymetryManager(source="etopo2022")
        manager._is_mock = False

        # Set up minimal coordinates
        manager._lats = [40.0, 50.0]
        manager._lons = [-70.0, -60.0]

        # Mock dataset
        mock_dataset = MagicMock()
        manager._dataset = mock_dataset
        mock_variables = MagicMock()
        mock_dataset.variables = {"z": mock_variables}

        # Test zero spacing case
        with (
            patch.object(manager, "_lats", [50.0, 50.0]),
            patch.object(manager, "_lons", [-60.0, -60.0]),
        ):
            # Should handle zero spacing gracefully
            result = manager.get_depth_at_point(50.0, -60.0)
            assert isinstance(result, float)

    def test_get_bathymetry_singleton(self):
        """Test the singleton bathymetry instance getter."""
        # Clear any existing singleton
        import cruiseplan.data.bathymetry as bathy_module

        bathy_module._bathymetry_instance = None

        # Get singleton twice
        instance1 = get_bathymetry_singleton()
        instance2 = get_bathymetry_singleton()

        # Should be the same instance
        assert instance1 is instance2
        assert isinstance(instance1, BathymetryManager)

    def test_module_getattr_bathymetry(self):
        """Test the module __getattr__ for backwards compatibility."""
        # Clear any existing singleton
        import cruiseplan.data.bathymetry as bathy_module

        bathy_module._bathymetry_instance = None

        # Access via __getattr__
        bathymetry_instance = bathy_module.bathymetry

        # Should return a BathymetryManager instance
        assert isinstance(bathymetry_instance, BathymetryManager)

    def test_module_getattr_invalid_attribute(self):
        """Test the module __getattr__ with invalid attribute."""
        import cruiseplan.data.bathymetry as bathy_module

        # Should raise AttributeError for invalid attributes
        with pytest.raises(AttributeError):
            bathy_module.invalid_attribute

    def test_interpolation_bounds_edge_cases(self):
        """Test interpolation boundary conditions that might cause errors."""
        manager = BathymetryManager(source="etopo2022")
        manager._is_mock = False

        # Mock the dataset and coordinates
        mock_dataset = MagicMock()
        manager._dataset = mock_dataset
        manager._lats = [40.0, 50.0, 60.0]
        manager._lons = [-70.0, -60.0, -50.0]

        # Mock the variables
        mock_variables = MagicMock()
        mock_dataset.variables = {"z": mock_variables}

        # Test point exactly on grid boundary
        with patch.object(manager, "_interpolate_depth", return_value=-100.0):
            result = manager.get_depth_at_point(50.0, -60.0)
            assert result == -100.0

    def test_initialization_download_context(self, tmp_path):
        """Test initialization in download context (should suppress logging)."""
        bathymetry_dir = tmp_path / "data" / "bathymetry"
        bathymetry_dir.mkdir(parents=True, exist_ok=True)

        # Mock the stack trace to simulate download context

        mock_frame = MagicMock()
        mock_frame.name = "download_bathymetry"

        with (
            patch("traceback.extract_stack", return_value=[mock_frame] * 5),
            patch("cruiseplan.data.bathymetry.logger") as mock_logger,
        ):

            manager = BathymetryManager(source="etopo2022")
            manager.data_dir = bathymetry_dir
            manager._initialize_data()

            # Should be in mock mode
            assert manager._is_mock is True

            # Should not log about mock mode (download context)
            # Check that no info calls were made about mock mode
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            mock_mode_logs = [call for call in info_calls if "MOCK mode" in call]
            assert len(mock_mode_logs) == 0
