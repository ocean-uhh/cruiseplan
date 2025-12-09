"""
Test basic LaTeX generation functionality.

These tests validate the Phase 3a LaTeX generation works with mock data.
Complete cruise scheduling logic will be implemented in Phase 3c.
"""

from pathlib import Path

from cruiseplan.output.latex_generator import generate_latex_tables


def test_latex_generation_basic():
    """Test that LaTeX generation produces valid output files."""
    # Mock cruise data as would be provided by Phase 3c scheduling
    mock_cruise_data = {
        "cruise_name": "Test_Cruise_2028",
        "operations": [
            {
                "type": "CTD profile",
                "name": "STN_001",
                "latitude": 50.0,
                "longitude": -40.0,
                "depth": 1000.0,
            },
            {
                "type": "CTD profile",
                "name": "STN_002",
                "latitude": 51.0,
                "longitude": -40.0,
                "depth": 1000.0,
            },
        ],
        "summary_breakdown": [
            {
                "area": "Transit to Port",
                "activity": "",
                "duration_h": "",
                "transit_h": 35.0,
            },
            {
                "area": "Test Operations",
                "activity": "CTD stations",
                "duration_h": 2.1,
                "transit_h": "",
            },
            {
                "area": "Transit within area",
                "activity": "",
                "duration_h": 10.0,
                "transit_h": "",
            },
        ],
        "default_vessel_speed": 10.0,
    }

    # Test output directory
    output_dir = Path("tests_output/test_latex")

    # Generate LaTeX files
    generated_files = generate_latex_tables(mock_cruise_data, output_dir)

    # Verify files were created
    assert len(generated_files) == 2

    # Check that both expected files exist
    stations_file = output_dir / "Test_Cruise_2028_stations.tex"
    work_days_file = output_dir / "Test_Cruise_2028_work_days.tex"

    assert stations_file.exists()
    assert work_days_file.exists()

    # Verify stations file has content
    stations_content = stations_file.read_text()
    assert "STN_001" in stations_content
    assert "STN_002" in stations_content
    assert "1000" in stations_content  # Depth (formatted without decimal)

    # Verify work days file has content
    work_days_content = work_days_file.read_text()
    assert "CTD stations" in work_days_content
    assert "2.1" in work_days_content  # Duration
    assert "Total duration" in work_days_content


def test_latex_generation_no_double_totals():
    """Test that work days table doesn't have duplicate total rows."""
    mock_cruise_data = {
        "cruise_name": "No_Doubles_Test",
        "operations": [
            {
                "type": "CTD profile",
                "name": "STN_001",
                "latitude": 50.0,
                "longitude": -40.0,
                "depth": 1000.0,
            }
        ],
        "summary_breakdown": [
            {
                "area": "Test Area",
                "activity": "CTD stations",
                "duration_h": 1.0,
                "transit_h": "",
            },
        ],
        "default_vessel_speed": 10.0,
    }

    output_dir = Path("tests_output/test_no_doubles")
    generated_files = generate_latex_tables(mock_cruise_data, output_dir)

    work_days_file = output_dir / "No_Doubles_Test_work_days.tex"
    content = work_days_file.read_text()

    # Should only have one "Total duration" line (from template)
    total_count = content.count("Total duration")
    assert total_count == 1, f"Expected 1 'Total duration' line, found {total_count}"


def test_latex_generation_empty_operations():
    """Test LaTeX generation handles empty operations gracefully."""
    mock_cruise_data = {
        "cruise_name": "Empty_Test",
        "operations": [],  # No operations
        "summary_breakdown": [
            {
                "area": "Transit to Port",
                "activity": "",
                "duration_h": "",
                "transit_h": 35.0,
            },
        ],
        "default_vessel_speed": 10.0,
    }

    output_dir = Path("tests_output/test_empty")
    generated_files = generate_latex_tables(mock_cruise_data, output_dir)

    # Files should still be generated
    assert len(generated_files) == 2

    stations_file = output_dir / "Empty_Test_stations.tex"
    assert stations_file.exists()

    # Stations file should have table structure even if empty
    content = stations_file.read_text()
    assert "\\begin{tabular}" in content
    assert "\\end{tabular}" in content
