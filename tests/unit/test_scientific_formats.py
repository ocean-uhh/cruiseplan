from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import netCDF4 as nc
import numpy as np
import pandas as pd
import pytest

# Import the functions under test
from cruiseplan.output.scientific_formats import (
    generate_csv_output,
    generate_netcdf_output,
)


# Mock modules used by the functions
@patch(
    "cruiseplan.output.scientific_formats.format_position_string",
    return_value="50°00.00'N, 040°00.00'W",
)
@patch(
    "cruiseplan.output.scientific_formats.minutes_to_hours",
    side_effect=lambda m: m / 60.0,
)
class TestScientificFormats:

    @pytest.fixture
    def mock_config(self):
        """Mock CruiseConfig object."""
        config = MagicMock()
        config.cruise_name = "TEST_CRUISE_001"
        config.default_vessel_speed = 12.0
        return config

    @pytest.fixture
    def mock_timeline(self):
        """Mock timeline data for testing. Includes Transit and Station types."""
        start_time = datetime(2025, 1, 1, 12, 0, 0)

        # NOTE: Transit records should be filtered out for NetCDF station dimension
        return [
            # 1. Mobilization Transit (Should be excluded from NetCDF station dimension)
            {
                "activity": "Transit",
                "label": "Mobilization",
                "lat": 49.0,
                "lon": -50.0,
                "depth": 0.0,
                "start_time": start_time,
                "end_time": start_time + timedelta(hours=5),
                "duration_minutes": 300.0,
                "transit_dist_nm": 60.0,
                "vessel_speed_kt": 12.0,
                "leg_name": "Mobilization",
                "operation_type": "Transit",
            },
            # 2. CTD Station 1 (Should be INCLUDED)
            {
                "activity": "Station",
                "label": "STN_001",
                "lat": 50.0,
                "lon": -40.0,
                "depth": 1000.0,
                "start_time": start_time + timedelta(hours=6),
                "end_time": start_time + timedelta(hours=8),
                "duration_minutes": 120.0,
                "transit_dist_nm": 120.0,
                "vessel_speed_kt": 12.0,
                "leg_name": "Leg A",
                "operation_type": "station",
            },
            # 3. Mooring Recovery (Should be INCLUDED)
            {
                "activity": "Mooring",
                "label": "M_REC_02",
                "lat": 51.0,
                "lon": -41.0,
                "depth": 2500.0,
                "start_time": start_time + timedelta(hours=10),
                "end_time": start_time + timedelta(hours=13),
                "duration_minutes": 180.0,
                "transit_dist_nm": 60.0,
                "vessel_speed_kt": 12.0,
                "leg_name": "Leg A",
                "operation_type": "mooring",
            },
            # 4. Demobilization Transit (Should be excluded)
            {
                "activity": "Transit",
                "label": "Demobilization",
                "lat": 52.0,
                "lon": -42.0,
                "depth": 0.0,
                "start_time": start_time + timedelta(hours=14),
                "end_time": start_time + timedelta(hours=20),
                "duration_minutes": 360.0,
                "transit_dist_nm": 100.0,
                "vessel_speed_kt": 12.0,
                "leg_name": "Demobilization",
                "operation_type": "Transit",
            },
        ]

    # --- NetCDF Tests ---

    @patch("netCDF4.Dataset")
    def test_netcdf_generation_structure(
        self, MockNetCDF, mock_hours, mock_pos, mock_config, mock_timeline, tmp_path
    ):
        """Verify dimensions, global attributes, and variables are correctly created."""
        # Act
        generate_netcdf_output(mock_config, mock_timeline, tmp_path)

        # Get the mock instance and calls
        MockNetCDF.assert_called_once()
        ds = MockNetCDF.return_value.__enter__.return_value

        # 1. Dimensions Check: Should only include 2 sampling stations
        ds.createDimension.assert_any_call("station", 2)

        # 2. Global Attributes Check
        assert ds.title == "TEST_CRUISE_001"
        assert ds.vessel_speed_kt == 12.0
        assert ds.Conventions == "CF-1.6"

        # 3. Variable Creation Check
        # Check for presence and correct dimension ('station',)
        ds.createVariable.assert_any_call("longitude", "f4", ("station",))
        ds.createVariable.assert_any_call("depth", "f4", ("station",))
        ds.createVariable.assert_any_call("duration_minutes", "f4", ("station",))
        ds.createVariable.assert_any_call("distance_from_start", "f4", ("station",))

        # Check operation type variable array size
        # ['mooring', 'station'] -> 2 unique types
        op_name_call = ds.createVariable.call_args_list[-1]
        assert op_name_call[0][0] == "operation_type_names"

    def test_netcdf_data_content(
        self, mock_hours, mock_pos, mock_config, mock_timeline, tmp_path
    ):
        """Verify derived data arrays (cumulative distance, categories) are correct."""
        # Use a real nc.Dataset instance written to disk for content verification
        output_path = tmp_path / "test_data.nc"
        generate_netcdf_output(mock_config, mock_timeline, tmp_path, "test_data.nc")

        with nc.Dataset(output_path, "r") as ds:
            # 1. Check Station Count (Should be 2: STN_001 and M_REC_02)
            assert ds.dimensions["station"].size == 2

            # 2. Check Cumulative Distance
            # Station 1 transit_dist_nm: 120.0 (cumulative starts at this value)
            # Station 2 transit_dist_nm: 60.0
            # Cumulative should be: [120.0, 120.0 + 60.0 = 180.0]
            cumulative_dist = ds.variables["distance_from_start"][:]
            assert np.allclose(cumulative_dist, [120.0, 180.0])

            # 3. Check Operation Type Categories
            # op_types: ['mooring', 'station'] (mooring=0, station=1)
            # Order in timeline: station, mooring
            # Expected categories: [1, 0]
            op_idx = ds.variables["operation_type_index"][:]
            assert np.all(op_idx == np.array([1, 0]))  # Note: numpy comparison

    # --- CSV Tests ---

    def test_csv_generation_structure_and_content(
        self, mock_hours, mock_pos, mock_config, mock_timeline, tmp_path
    ):
        """Verify all timeline records are included and headers/formatting are correct."""
        # Act
        output_path = generate_csv_output(
            mock_config, mock_timeline, tmp_path, "test_schedule.csv"
        )

        # Read the generated CSV back into a pandas DataFrame
        df = pd.read_csv(output_path)

        # 1. Check Row Count: Should include ALL 4 timeline records
        assert len(df) == 4

        # 2. Check Column Headers (At least the key ones)
        expected_cols = [
            "Activity",
            "Label (name)",
            "Activity duration [h]",
            "Transit distance [nm]",
        ]
        assert all(col in df.columns for col in expected_cols)

        # 3. Check Formatting (using the first row/Mobilization Transit)
        # Duration: 300 minutes / 60 = 5.0 hours
        # Transit time: 60.0 nm / 12.0 kt = 5.0 hours

        # Locate the Transit row
        transit_row = df[df["Activity"] == "Transit"].iloc[0]

        assert transit_row["Activity duration [h]"] == pytest.approx(5.0)
        assert transit_row["Transit distance [nm]"] == pytest.approx(60.0)
        assert transit_row["Transit time [h]"] == pytest.approx(5.0)
        assert transit_row["Start (date)"] == "2025-01-01"

    def test_output_generation_handles_empty_timeline(
        self, mock_hours, mock_pos, mock_config, tmp_path
    ):
        """Verify both functions handle an empty timeline without crashing."""
        empty_timeline = []

        # NetCDF should not generate a file or should return the expected path
        nc_path = generate_netcdf_output(
            mock_config, empty_timeline, tmp_path, "empty.nc"
        )
        assert not nc_path.exists()

        # CSV should not generate a file or should return the expected path
        csv_path = generate_csv_output(
            mock_config, empty_timeline, tmp_path, "empty.csv"
        )
        assert not csv_path.exists()
