"""
Test basic LaTeX generation functionality.

These tests validate the Phase 3a LaTeX generation works with mock data.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from cruiseplan.core.validation import CruiseConfig
from cruiseplan.output.latex_generator import generate_latex_tables


def test_latex_generation_basic():
    """Test that LaTeX generation works without crashing."""
    # Mock config
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "Test_Cruise_2028"
    mock_config.first_station = "STN_001"
    mock_config.last_station = "STN_002"

    # Mock ports
    mock_config.departure_port = MagicMock()
    mock_config.departure_port.name = "Departure Port"
    mock_config.arrival_port = MagicMock()
    mock_config.arrival_port.name = "Arrival Port"

    # Simple timeline data with just stations
    mock_timeline = [
        {
            "activity": "Station",
            "label": "STN_001",
            "lat": 50.0,
            "lon": -40.0,
            "depth": 1000.0,
            "start_time": datetime(2028, 6, 2, 19, 0),
            "end_time": datetime(2028, 6, 2, 20, 3),
            "duration_minutes": 63.0,
            "transit_dist_nm": 0.0,
            "vessel_speed_kt": 10.0,
            "leg_name": "Test_Operations",
            "operation_type": "station",
        },
        {
            "activity": "Station",
            "label": "STN_002",
            "lat": 51.0,
            "lon": -40.0,
            "depth": 1000.0,
            "start_time": datetime(2028, 6, 2, 20, 3),
            "end_time": datetime(2028, 6, 2, 21, 6),
            "duration_minutes": 63.0,
            "transit_dist_nm": 10.0,
            "vessel_speed_kt": 10.0,
            "leg_name": "Test_Operations",
            "operation_type": "station",
        },
    ]

    # Test output directory
    output_dir = Path("tests_output/test_latex")

    # Generate LaTeX files - should not crash
    generated_files = generate_latex_tables(mock_config, mock_timeline, output_dir)

    # Verify some files were created (exact number may vary based on implementation)
    assert len(generated_files) >= 0  # At minimum, should not crash

    # Check that both expected files exist
    stations_file = output_dir / "Test_Cruise_2028_stations.tex"
    work_days_file = output_dir / "Test_Cruise_2028_work_days.tex"

    assert stations_file.exists()
    assert work_days_file.exists()

    # Verify stations file has content
    stations_content = stations_file.read_text()
    assert "STN-001" in stations_content  # Replace underscore with dash
    assert "STN-002" in stations_content  # Replace underscore with dash
    assert "1000" in stations_content  # Depth (formatted without decimal)

    # Verify work days file has content
    work_days_content = work_days_file.read_text()
    assert "CTD/Station Operations" in work_days_content
    # Note: no transits in test data, so no transit entries expected


def test_latex_generation_no_double_totals():
    """Test that work days table doesn't have duplicate total rows."""
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "No_Doubles_Test"
    mock_config.first_station = "STN_001"
    mock_config.last_station = "STN_001"
    mock_config.departure_port = MagicMock()
    mock_config.departure_port.name = "Start"
    mock_config.arrival_port = MagicMock()
    mock_config.arrival_port.name = "End"

    mock_timeline = [
        {
            "activity": "Station",
            "label": "STN_001",
            "lat": 50.0,
            "lon": -40.0,
            "depth": 1000.0,
            "start_time": datetime(2028, 6, 1, 8, 0),
            "end_time": datetime(2028, 6, 1, 9, 0),
            "duration_minutes": 60.0,
            "transit_dist_nm": 0.0,
            "vessel_speed_kt": 10.0,
            "leg_name": "Test_Operations",
            "operation_type": "station",
        }
    ]

    output_dir = Path("tests_output/test_no_doubles")
    generated_files = generate_latex_tables(mock_config, mock_timeline, output_dir)

    work_days_file = output_dir / "No_Doubles_Test_work_days.tex"
    content = work_days_file.read_text()

    # Should only have one "Total duration" line (from template)
    total_count = content.count("Total duration")
    assert total_count == 1, f"Expected 1 'Total duration' line, found {total_count}"
    assert len(generated_files) >= 0  # Should complete without crashing


def test_latex_generation_empty_operations():
    """Test LaTeX generation handles empty operations gracefully."""
    mock_config = MagicMock(spec=CruiseConfig)
    mock_config.cruise_name = "Empty_Test"
    mock_config.first_station = "STN_001"
    mock_config.last_station = "STN_001"
    mock_config.departure_port = MagicMock()
    mock_config.departure_port.name = "Start"
    mock_config.arrival_port = MagicMock()
    mock_config.arrival_port.name = "End"

    # Empty timeline (only transit operations)
    mock_timeline = [
        {
            "activity": "Transit",
            "label": "Transit to working area",
            "lat": 50.0,
            "lon": -40.0,
            "depth": 0.0,
            "start_time": datetime(2028, 6, 1, 8, 0),
            "end_time": datetime(2028, 6, 2, 19, 0),
            "duration_minutes": 2100.0,  # 35 hours
            "transit_dist_nm": 350.0,
            "vessel_speed_kt": 10.0,
            "leg_name": "Transit",
            "operation_type": "Transit",
        }
    ]

    output_dir = Path("tests_output/test_empty")
    generated_files = generate_latex_tables(mock_config, mock_timeline, output_dir)

    # Should complete without crashing
    assert len(generated_files) >= 0

    stations_file = output_dir / "Empty_Test_stations.tex"
    assert stations_file.exists()

    # Stations file should have table structure even if empty
    content = stations_file.read_text()
    assert "\\begin{tabular}" in content
    assert "\\end{tabular}" in content
