"""
Integration tests for the complete process() workflow.

These tests ensure the full process() function works end-to-end,
particularly the map generation code path that uses internal imports.
"""

import tempfile
from pathlib import Path

import cruiseplan


class TestProcessIntegration:
    """Test the full process() workflow with map generation."""

    def test_process_with_map_generation(self):
        """Test process() function with map generation enabled."""
        # Create a minimal but complete cruise configuration
        cruise_config = {
            "cruise_name": "Process Integration Test",
            "default_vessel_speed": 10.0,
            "start_date": "2025-06-01T00:00:00Z",
            "points": [
                {
                    "name": "STN_001",
                    "latitude": 60.0,
                    "longitude": -30.0,
                    "operation_type": "CTD",
                    "action": "profile",
                },
                {
                    "name": "STN_002",
                    "latitude": 61.0,
                    "longitude": -28.0,
                    "operation_type": "CTD",
                    "action": "profile",
                },
            ],
            "legs": [
                {
                    "name": "Test_Leg",
                    "departure_port": "port_reykjavik",
                    "arrival_port": "port_reykjavik",
                    "first_activity": "STN_001",
                    "last_activity": "STN_002",
                    "activities": ["STN_001", "STN_002"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save config file
            config_file = temp_path / "test_cruise.yaml"
            from cruiseplan.schema.yaml_io import save_yaml

            save_yaml(cruise_config, config_file)

            # Test process() with map generation (this is what was failing)
            result = cruiseplan.process(
                config_file=config_file,
                output_dir=str(temp_path),
                output="test_process",
                format="png",  # This triggers map generation
                depth_check=False,  # Skip depth validation for simplicity
            )

            # Verify the result
            assert result is not None
            assert bool(result) is True  # Should indicate success
            assert len(result.files_created) >= 2  # At least enriched config + map

            # Verify files were actually created
            for file_path in result.files_created:
                assert file_path.exists(), f"File not created: {file_path}"

    def test_process_without_map(self):
        """Test process() function without map generation for comparison."""
        cruise_config = {
            "cruise_name": "Process Test No Map",
            "points": [
                {
                    "name": "STN_001",
                    "latitude": 60.0,
                    "longitude": -30.0,
                    "operation_type": "CTD",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            config_file = temp_path / "test_cruise.yaml"
            from cruiseplan.schema.yaml_io import save_yaml

            save_yaml(cruise_config, config_file)

            # Test process() without map generation
            result = cruiseplan.process(
                config_file=config_file,
                output_dir=str(temp_path),
                format=None,  # No map generation
                depth_check=False,
            )

            assert result is not None
            assert bool(result) is True
            # Should have at least the enriched config file
            assert len(result.files_created) >= 1
