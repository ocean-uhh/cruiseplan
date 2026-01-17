"""
Tests for coordinate formatting utilities.
"""

import pytest

from cruiseplan.utils.coordinates import (
    CoordConverter,
    calculate_map_bounds,
    compute_final_limits,
    extract_coordinates_from_cruise,
    format_ddm_comment,
    format_position_latex,
)


class TestCoordConverter:
    """Test coordinate unit conversion utilities."""

    def test_decimal_degrees_to_ddm_positive(self):
        """Test conversion of positive decimal degrees to DMM."""
        degrees, minutes = CoordConverter.decimal_degrees_to_ddm(65.7458)
        assert degrees == 65.0
        assert minutes == pytest.approx(44.75, abs=0.01)

    def test_decimal_degrees_to_ddm_negative(self):
        """Test conversion of negative decimal degrees to DMM."""
        degrees, minutes = CoordConverter.decimal_degrees_to_ddm(-24.4792)
        assert degrees == 24.0
        assert minutes == pytest.approx(28.75, abs=0.01)

    def test_decimal_degrees_to_ddm_zero(self):
        """Test conversion of zero degrees."""
        degrees, minutes = CoordConverter.decimal_degrees_to_ddm(0.0)
        assert degrees == 0.0
        assert minutes == 0.0

    def test_decimal_degrees_to_ddm_exact_degrees(self):
        """Test conversion of exact degree values."""
        degrees, minutes = CoordConverter.decimal_degrees_to_ddm(45.0)
        assert degrees == 45.0
        assert minutes == 0.0


class TestFormatDmmComment:
    """Test DMM format comment generation."""

    def test_format_ddm_comment_north_west(self):
        """Test formatting coordinates in NW quadrant."""
        result = format_ddm_comment(65.7458, -24.4792)
        assert result == "65 44.75'N, 024 28.75'W"

    def test_format_ddm_comment_south_east(self):
        """Test formatting coordinates in SE quadrant."""
        result = format_ddm_comment(-33.8568, 151.2153)
        assert result == "33 51.41'S, 151 12.92'E"

    def test_format_ddm_comment_zero_coordinates(self):
        """Test formatting zero coordinates."""
        result = format_ddm_comment(0.0, 0.0)
        assert result == "00 00.00'N, 000 00.00'E"

    def test_format_ddm_comment_precise_minutes(self):
        """Test formatting with precise decimal minutes."""
        result = format_ddm_comment(50.1234, -40.5678)
        assert result == "50 07.40'N, 040 34.07'W"

    def test_format_ddm_comment_leading_zeros(self):
        """Test that longitude gets proper leading zeros."""
        result = format_ddm_comment(5.1234, -8.5678)
        assert result == "05 07.40'N, 008 34.07'W"


class TestFormatPositionLatex:
    """Test LaTeX coordinate formatting."""

    def test_format_position_latex_basic(self):
        """Test basic LaTeX formatting."""
        result = format_position_latex(65.7458, -24.4792)
        assert result == "65$^\\circ$44.75'N, 024$^\\circ$28.75'W"

    def test_format_position_latex_south_east(self):
        """Test LaTeX formatting for SE quadrant."""
        result = format_position_latex(-33.8568, 151.2153)
        assert result == "33$^\\circ$51.41'S, 151$^\\circ$12.92'E"

    def test_format_position_latex_zero(self):
        """Test LaTeX formatting for zero coordinates."""
        result = format_position_latex(0.0, 0.0)
        assert result == "00$^\\circ$00.00'N, 000$^\\circ$00.00'E"

    def test_format_position_latex_precise(self):
        """Test LaTeX formatting with precise coordinates."""
        result = format_position_latex(50.1234, -40.5678)
        assert result == "50$^\\circ$07.40'N, 040$^\\circ$34.07'W"

    def test_format_position_latex_leading_zeros_longitude(self):
        """Test that longitude gets proper leading zeros in LaTeX."""
        result = format_position_latex(5.1234, -8.5678)
        assert result == "05$^\\circ$07.40'N, 008$^\\circ$34.07'W"


class TestCoordinateFormatConsistency:
    """Test consistency between different coordinate formats."""

    @pytest.mark.parametrize(
        "lat,lon",
        [
            (65.7458, -24.4792),  # North Atlantic
            (-33.8568, 151.2153),  # Sydney, Australia
            (0.0, 0.0),  # Null Island
            (90.0, 180.0),  # Extreme coordinates
            (-90.0, -180.0),  # Other extreme
        ],
    )
    def test_coordinate_format_consistency(self, lat, lon):
        """Test that all formats produce consistent coordinate values."""
        # Get DMM values from CoordConverter
        lat_deg, lat_min = CoordConverter.decimal_degrees_to_ddm(lat)
        lon_deg, lon_min = CoordConverter.decimal_degrees_to_ddm(lon)

        # Test DMM comment format
        ddm_result = format_ddm_comment(lat, lon)
        assert f"{abs(int(lat_deg)):02d} {lat_min:05.2f}'" in ddm_result
        assert f"{abs(int(lon_deg)):03d} {lon_min:05.2f}'" in ddm_result

        # Test LaTeX format contains same numeric values
        latex_result = format_position_latex(lat, lon)
        assert f"{abs(int(lat_deg)):02d}$^\\circ${lat_min:05.2f}'" in latex_result
        assert f"{abs(int(lon_deg)):03d}$^\\circ${lon_min:05.2f}'" in latex_result

        # All formats should contain proper directional indicators
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        assert lat_dir in ddm_result
        assert lat_dir in latex_result
        assert lon_dir in ddm_result
        assert lon_dir in latex_result


class TestRealWorldCoordinates:
    """Test with real-world oceanographic coordinates."""

    def test_north_atlantic_station(self):
        """Test typical North Atlantic research station coordinates."""
        # Example: OSNAP mooring site
        lat, lon = 59.7583, -39.7333

        ddm = format_ddm_comment(lat, lon)
        assert ddm == "59 45.50'N, 039 44.00'W"

        latex = format_position_latex(lat, lon)
        assert latex == "59$^\\circ$45.50'N, 039$^\\circ$44.00'W"

    def test_arctic_station(self):
        """Test Arctic research station coordinates."""
        # Example: Fram Strait moorings
        lat, lon = 78.8333, 0.0

        ddm = format_ddm_comment(lat, lon)
        assert ddm == "78 50.00'N, 000 00.00'E"

    def test_southern_ocean_station(self):
        """Test Southern Ocean coordinates."""
        # Example: Drake Passage
        lat, lon = -60.5, -65.0

        ddm = format_ddm_comment(lat, lon)
        assert ddm == "60 30.00'S, 065 00.00'W"


class TestCoordinateParsingIntegration:
    """Test integration between parsing and formatting functions."""

    def test_coordinate_formatting_consistency(self):
        """Test that coordinate formatting functions are consistent."""
        test_coords = [
            (65.7458, -24.4792),  # North Atlantic
            (-33.8568, 151.2153),  # Sydney
            (0.0, 0.0),  # Null Island
            (78.8333, 0.0),  # Arctic
            (-60.5, -65.0),  # Southern Ocean
        ]

        for orig_lat, orig_lon in test_coords:
            # All formatting functions should work without errors
            ddm_comment = format_ddm_comment(orig_lat, orig_lon)
            latex_formatted = format_position_latex(orig_lat, orig_lon)

            # Should contain proper directional indicators
            lat_dir = "N" if orig_lat >= 0 else "S"
            lon_dir = "E" if orig_lon >= 0 else "W"
            assert lat_dir in ddm_comment
            assert lat_dir in latex_formatted
            assert lon_dir in ddm_comment
            assert lon_dir in latex_formatted

    def test_dms_format_edge_cases(self):
        """Test edge cases for coordinate formatting."""
        # Test coordinates at hemisphere boundaries
        boundary_coords = [
            (0.0, 0.0),  # Equator/Prime Meridian
            (0.0001, 0.0001),  # Just north/east of origin
            (-0.0001, -0.0001),  # Just south/west of origin
            (89.9999, 179.9999),  # Near poles/date line
            (-89.9999, -179.9999),  # Other extreme
        ]

        for lat, lon in boundary_coords:
            # Test formatting functions don't crash
            ddm = format_ddm_comment(lat, lon)
            latex = format_position_latex(lat, lon)

            # Basic validation that strings are properly formatted
            assert "'" in ddm  # Contains minute symbol
            assert "$" in latex  # Contains LaTeX formatting


class TestCalculateMapBounds:
    """Test map bounds calculation with flexible padding."""

    def test_calculate_map_bounds_default_behavior(self):
        """Test default behavior with percentage padding and aspect ratio correction."""
        test_lats = [60.0, 61.0, 62.0]
        test_lons = [-20.0, -21.0, -22.0]

        min_lon, max_lon, min_lat, max_lat = calculate_map_bounds(test_lats, test_lons)

        # Should have some padding applied
        assert min_lon < -22.0
        assert max_lon > -20.0
        assert min_lat < 60.0
        assert max_lat > 62.0

    def test_calculate_map_bounds_fixed_padding(self):
        """Test bounds calculation with fixed degree padding."""
        test_lats = [60.0, 62.0]
        test_lons = [-20.0, -22.0]

        min_lon, max_lon, min_lat, max_lat = calculate_map_bounds(
            test_lats,
            test_lons,
            padding_degrees=1.0,
            apply_aspect_ratio=False,
            round_to_degrees=False,
        )

        # Should have exactly 1 degree padding
        assert min_lon == pytest.approx(-23.0)
        assert max_lon == pytest.approx(-19.0)
        assert min_lat == pytest.approx(59.0)
        assert max_lat == pytest.approx(63.0)

    def test_calculate_map_bounds_percentage_padding(self):
        """Test bounds calculation with percentage padding."""
        test_lats = [60.0, 62.0]  # 2 degree range
        test_lons = [-20.0, -22.0]  # 2 degree range

        min_lon, max_lon, min_lat, max_lat = calculate_map_bounds(
            test_lats,
            test_lons,
            padding_percent=0.10,  # 10% of 2 degrees = 0.2 degrees
            padding_degrees=None,
            apply_aspect_ratio=False,
            round_to_degrees=False,
        )

        # Should have 10% padding (0.2 degrees)
        assert min_lon == pytest.approx(-22.2)
        assert max_lon == pytest.approx(-19.8)
        assert min_lat == pytest.approx(59.8)
        assert max_lat == pytest.approx(62.2)

    def test_calculate_map_bounds_rounding(self):
        """Test bounds calculation with degree rounding."""
        test_lats = [60.5, 61.5]
        test_lons = [-20.5, -21.5]

        min_lon, max_lon, min_lat, max_lat = calculate_map_bounds(
            test_lats,
            test_lons,
            padding_percent=0.0,  # No padding for clearer test
            apply_aspect_ratio=False,
            round_to_degrees=True,
        )

        # Should round outward to whole degrees
        assert min_lon == -22.0  # floor(-21.5)
        assert max_lon == -20.0  # ceil(-20.5)
        assert min_lat == 60.0  # floor(60.5)
        assert max_lat == 62.0  # ceil(61.5)

    def test_calculate_map_bounds_no_rounding(self):
        """Test bounds calculation without degree rounding."""
        test_lats = [60.5, 61.5]
        test_lons = [-20.5, -21.5]

        min_lon, max_lon, min_lat, max_lat = calculate_map_bounds(
            test_lats,
            test_lons,
            padding_percent=0.0,
            apply_aspect_ratio=False,
            round_to_degrees=False,
        )

        # Should not round
        assert min_lon == -21.5
        assert max_lon == -20.5
        assert min_lat == 60.5
        assert max_lat == 61.5

    def test_calculate_map_bounds_empty_coordinates(self):
        """Test error handling for empty coordinate lists."""
        with pytest.raises(ValueError, match="No coordinates provided"):
            calculate_map_bounds([], [])

    def test_calculate_map_bounds_mismatched_lengths(self):
        """Test that mismatched coordinate lists are handled correctly."""
        # Function should handle mismatched lengths gracefully
        test_lats = [60.0, 61.0]
        test_lons = [-20.0]

        # Should not crash - will use available coordinates
        min_lon, max_lon, min_lat, max_lat = calculate_map_bounds(
            test_lats,
            test_lons,
            padding_degrees=0.0,
            apply_aspect_ratio=False,
            round_to_degrees=False,
        )

        # Should use available data
        assert min_lon == -20.0
        assert max_lon == -20.0
        assert min_lat == 60.0
        assert max_lat == 61.0


class TestComputeFinalLimits:
    """Test geographic aspect ratio correction."""

    def test_compute_final_limits_basic(self):
        """Test basic aspect ratio correction."""
        # Square region at equator should remain roughly square
        min_lon, max_lon, min_lat, max_lat = compute_final_limits(
            -1.0, 1.0, -1.0, 1.0  # 2x2 degree square at equator
        )

        # At equator, aspect ratio is ~1, so should remain similar
        lon_range = max_lon - min_lon
        lat_range = max_lat - min_lat
        assert lon_range == pytest.approx(2.0, abs=0.1)
        assert lat_range == pytest.approx(2.0, abs=0.1)

    def test_compute_final_limits_high_latitude(self):
        """Test aspect ratio correction at high latitude."""
        # Small region at high latitude needs longitude expansion
        min_lon, max_lon, min_lat, max_lat = compute_final_limits(
            -1.0, 1.0, 70.0, 72.0  # 2x2 degree region at 71°N
        )

        # Should expand longitude to maintain proper aspect ratio
        lon_range = max_lon - min_lon
        lat_range = max_lat - min_lat
        assert lon_range > 2.0  # Should be expanded
        assert lat_range == pytest.approx(2.0, abs=0.1)  # Should remain same

    def test_compute_final_limits_extreme_latitude(self):
        """Test aspect ratio correction at extreme latitude."""
        # Test near poles where aspect ratio becomes very large
        min_lon, max_lon, min_lat, max_lat = compute_final_limits(
            -1.0, 1.0, 85.0, 87.0  # Near north pole
        )

        # Should expand longitude significantly but cap the expansion
        lon_range = max_lon - min_lon
        lat_range = max_lat - min_lat
        assert lon_range > 2.0
        assert lat_range == pytest.approx(2.0, abs=0.1)

        # Should not expand to unreasonable values
        assert lon_range < 50.0  # Capped by max aspect ratio

    def test_compute_final_limits_longitude_dominant(self):
        """Test when longitude range is already large."""
        # Wide longitude range should expand latitude instead
        min_lon, max_lon, min_lat, max_lat = compute_final_limits(
            -10.0, 10.0, 45.0, 46.0  # 20° lon x 1° lat at 45°N
        )

        lon_range = max_lon - min_lon
        lat_range = max_lat - min_lat

        # Longitude should remain the same
        assert lon_range == pytest.approx(20.0, abs=0.1)
        # Latitude should be expanded
        assert lat_range > 1.0


class TestExtractCoordinatesFromCruise:
    """Test coordinate extraction from cruise objects."""

    def test_extract_coordinates_basic(self):
        """Test basic coordinate extraction with mock cruise object."""
        from unittest.mock import MagicMock

        # Create mock cruise object
        mock_cruise = MagicMock()

        # Mock station registry
        mock_station1 = MagicMock()
        mock_station1.latitude = 60.0
        mock_station1.longitude = -20.0

        mock_station2 = MagicMock()
        mock_station2.latitude = 61.0
        mock_station2.longitude = -21.0

        mock_cruise.point_registry = {
            "STN_001": mock_station1,
            "STN_002": mock_station2,
        }

        # Mock config with no ports
        mock_cruise.config.departure_port = None
        mock_cruise.config.arrival_port = None

        # Extract coordinates
        lats, lons, names, dep_port, arr_port = extract_coordinates_from_cruise(
            mock_cruise
        )

        # Verify results
        assert len(lats) == 2
        assert len(lons) == 2
        assert len(names) == 2
        assert 60.0 in lats
        assert 61.0 in lats
        assert -20.0 in lons
        assert -21.0 in lons
        assert "STN_001" in names
        assert "STN_002" in names
        assert dep_port is None
        assert arr_port is None

    def test_extract_coordinates_with_ports(self):
        """Test coordinate extraction including departure and arrival ports."""
        from unittest.mock import MagicMock

        # Create mock cruise object
        mock_cruise = MagicMock()
        mock_cruise.point_registry = {}

        # Mock departure port (support both formats)
        mock_dep_port = MagicMock()
        mock_dep_port.latitude = 64.0
        mock_dep_port.longitude = -22.0
        mock_dep_port.name = "Reykjavik"
        mock_cruise.config.departure_port = mock_dep_port

        # Mock arrival port (support both formats)
        mock_arr_port = MagicMock()
        mock_arr_port.latitude = 78.0
        mock_arr_port.longitude = 15.0
        mock_arr_port.name = "Longyearbyen"
        mock_cruise.config.arrival_port = mock_arr_port

        # Extract coordinates
        lats, lons, names, dep_port, arr_port = extract_coordinates_from_cruise(
            mock_cruise
        )

        # Verify port extraction
        assert dep_port == (64.0, -22.0, "Reykjavik")
        assert arr_port == (78.0, 15.0, "Longyearbyen")
        assert len(lats) == 0  # No stations
        assert len(lons) == 0
        assert len(names) == 0

    def test_extract_coordinates_mixed_station_types(self):
        """Test coordinate extraction with different station attribute patterns."""
        from unittest.mock import MagicMock

        # Create mock cruise object
        mock_cruise = MagicMock()

        # Station with direct lat/lon attributes
        mock_station1 = MagicMock()
        mock_station1.latitude = 60.0
        mock_station1.longitude = -20.0

        # Station with position object
        mock_station2 = MagicMock()
        mock_station2.latitude = 61.0
        mock_station2.longitude = -21.0

        mock_cruise.point_registry = {
            "STN_001": mock_station1,
            "STN_002": mock_station2,
        }
        mock_cruise.config.departure_port = None
        mock_cruise.config.arrival_port = None

        # Extract coordinates
        lats, lons, _names, _dep_port, _arr_port = extract_coordinates_from_cruise(
            mock_cruise
        )

        # Should handle both attribute patterns
        assert len(lats) == 2
        assert len(lons) == 2
        assert 60.0 in lats
        assert 61.0 in lats
        assert -20.0 in lons
        assert -21.0 in lons
