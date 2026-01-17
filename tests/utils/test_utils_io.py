from pathlib import Path


class TestSetupOutputPaths:
    """Test the setup_output_paths function."""

    def test_setup_output_paths_with_explicit_output(self):
        """Test setup_output_paths with explicit output parameter."""
        from cruiseplan.utils.io import setup_output_paths

        # Create a temporary config file
        config_file = Path("tests_output/temp_config.yaml")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("cruise_name: Test Cruise\n")

        try:
            output_dir, base_name = setup_output_paths(
                config_file, output_dir="tests_output/demo", output="custom_name"
            )

            assert output_dir == Path("tests_output/demo").resolve()
            assert base_name == "custom_name"
            assert output_dir.exists()  # Directory should be created
        finally:
            # Cleanup
            if config_file.exists():
                config_file.unlink()

    def test_setup_output_paths_from_cruise_name(self):
        """Test setup_output_paths extracting cruise name from YAML."""
        from cruiseplan.utils.io import setup_output_paths

        # Create a temporary config file with cruise name
        config_file = Path("tests_output/temp_config.yaml")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("cruise_name: 'Test Cruise With Spaces'\n")

        try:
            output_dir, base_name = setup_output_paths(
                config_file, output_dir="tests_output/demo"
            )

            assert output_dir == Path("tests_output/demo").resolve()
            assert base_name == "Test_Cruise_With_Spaces"  # Spaces replaced
            assert output_dir.exists()
        finally:
            # Cleanup
            if config_file.exists():
                config_file.unlink()

    def test_setup_output_paths_fallback_to_filename(self):
        """Test setup_output_paths fallback to filename when cruise_name missing."""
        from cruiseplan.utils.io import setup_output_paths

        # Create a temporary config file without cruise name
        config_file = Path("tests_output/test_config_file.yaml")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("other_field: value\n")

        try:
            output_dir, base_name = setup_output_paths(
                config_file, output_dir="tests_output/demo"
            )

            assert output_dir == Path("tests_output/demo").resolve()
            assert base_name == "test_config_file"  # Based on filename
            assert output_dir.exists()
        finally:
            # Cleanup
            if config_file.exists():
                config_file.unlink()

    def test_setup_output_paths_yaml_error_fallback(self):
        """Test setup_output_paths fallback when YAML reading fails."""
        from cruiseplan.utils.io import setup_output_paths

        # Create a temporary config file with invalid YAML
        config_file = Path("tests_output/invalid_config.yaml")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("invalid: yaml: content:\n")

        try:
            output_dir, base_name = setup_output_paths(
                config_file, output_dir="tests_output/demo"
            )

            assert output_dir == Path("tests_output/demo").resolve()
            assert base_name == "invalid_config"  # Fallback to filename
            assert output_dir.exists()
        finally:
            # Cleanup
            if config_file.exists():
                config_file.unlink()

    def test_setup_output_paths_nonexistent_file_fallback(self):
        """Test setup_output_paths fallback when file doesn't exist."""
        from cruiseplan.utils.io import setup_output_paths

        # Use a nonexistent file
        config_file = Path("tests_output/nonexistent.yaml")

        output_dir, base_name = setup_output_paths(
            config_file, output_dir="tests_output/demo"
        )

        assert output_dir == Path("tests_output/demo").resolve()
        assert base_name == "nonexistent"  # Fallback to filename stem
        assert output_dir.exists()

    def test_setup_output_paths_special_chars_in_cruise_name(self):
        """Test setup_output_paths handles special characters in cruise name."""
        from cruiseplan.utils.io import setup_output_paths

        # Create a temporary config file with special characters
        config_file = Path("tests_output/temp_config.yaml")
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("cruise_name: 'Test/Cruise With/Slashes'\n")

        try:
            output_dir, base_name = setup_output_paths(
                config_file, output_dir="tests_output/demo"
            )

            assert output_dir == Path("tests_output/demo").resolve()
            assert (
                base_name == "Test-Cruise_With-Slashes"
            )  # Spaces and slashes replaced
            assert output_dir.exists()
        finally:
            # Cleanup
            if config_file.exists():
                config_file.unlink()
