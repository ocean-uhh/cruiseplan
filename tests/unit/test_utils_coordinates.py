"""
Tests for coordinate formatting utilities.
"""

import pytest

from cruiseplan.utils.coordinates import (
    UnitConverter,
    calculate_map_bounds,
    compute_final_limits,
    extract_coordinates_from_cruise,
    format_dmm_comment,
    format_geographic_bounds,
    format_position_latex,
    format_position_string,
    parse_dmm_format,
)


class TestUnitConverter:
    """Test coordinate unit conversion utilities."""

    def test_decimal_degrees_to_dmm_positive(self):
        """Test conversion of positive decimal degrees to DMM."""
        degrees, minutes = UnitConverter.decimal_degrees_to_dmm(65.7458)
        assert degrees == 65.0
        assert minutes == pytest.approx(44.75, abs=0.01)

    def test_decimal_degrees_to_dmm_negative(self):
        """Test conversion of negative decimal degrees to DMM."""
        degrees, minutes = UnitConverter.decimal_degrees_to_dmm(-24.4792)
        assert degrees == 24.0
        assert minutes == pytest.approx(28.75, abs=0.01)

    def test_decimal_degrees_to_dmm_zero(self):
        """Test conversion of zero degrees."""
        degrees, minutes = UnitConverter.decimal_degrees_to_dmm(0.0)
        assert degrees == 0.0
        assert minutes == 0.0

    def test_decimal_degrees_to_dmm_exact_degrees(self):
        """Test conversion of exact degree values."""
        degrees, minutes = UnitConverter.decimal_degrees_to_dmm(45.0)
        assert degrees == 45.0
        assert minutes == 0.0


class TestFormatDmmComment:
    """Test DMM format comment generation."""

    def test_format_dmm_comment_north_west(self):
        """Test formatting coordinates in NW quadrant."""
        result = format_dmm_comment(65.7458, -24.4792)
        assert result == "65 44.75'N, 024 28.75'W"

    def test_format_dmm_comment_south_east(self):
        """Test formatting coordinates in SE quadrant."""
        result = format_dmm_comment(-33.8568, 151.2153)
        assert result == "33 51.41'S, 151 12.92'E"

    def test_format_dmm_comment_zero_coordinates(self):
        """Test formatting zero coordinates."""
        result = format_dmm_comment(0.0, 0.0)
        assert result == "00 00.00'N, 000 00.00'E"

    def test_format_dmm_comment_precise_minutes(self):
        """Test formatting with precise decimal minutes."""
        result = format_dmm_comment(50.1234, -40.5678)
        assert result == "50 07.40'N, 040 34.07'W"

    def test_format_dmm_comment_leading_zeros(self):
        """Test that longitude gets proper leading zeros."""
        result = format_dmm_comment(5.1234, -8.5678)
        assert result == "05 07.40'N, 008 34.07'W"


class TestFormatPositionString:
    """Test position string formatting with different formats."""

    def test_format_position_string_dmm_default(self):
        """Test default DMM formatting."""
        result = format_position_string(65.7458, -24.4792)
        assert result == "65 44.75'N, 024 28.75'W"

    def test_format_position_string_dmm_explicit(self):
        """Test explicit DMM formatting."""
        result = format_position_string(65.7458, -24.4792, "dmm")
        assert result == "65 44.75'N, 024 28.75'W"

    def test_format_position_string_decimal(self):
        """Test decimal degrees formatting."""
        result = format_position_string(65.7458, -24.4792, "decimal")
        assert result == "65.7458°N, 24.4792°W"

    def test_format_position_string_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format_type: invalid"):
            format_position_string(65.7458, -24.4792, "invalid")

    def test_format_position_string_south_east_decimal(self):
        """Test decimal formatting for southern/eastern coordinates."""
        result = format_position_string(-33.8568, 151.2153, "decimal")
        assert result == "33.8568°S, 151.2153°E"


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
        # Get DMM values from UnitConverter
        lat_deg, lat_min = UnitConverter.decimal_degrees_to_dmm(lat)
        lon_deg, lon_min = UnitConverter.decimal_degrees_to_dmm(lon)

        # Test DMM comment format
        dmm_result = format_dmm_comment(lat, lon)
        assert f"{abs(int(lat_deg)):02d} {lat_min:05.2f}'" in dmm_result
        assert f"{abs(int(lon_deg)):03d} {lon_min:05.2f}'" in dmm_result

        # Test LaTeX format contains same numeric values
        latex_result = format_position_latex(lat, lon)
        assert f"{abs(int(lat_deg)):02d}$^\\circ${lat_min:05.2f}'" in latex_result
        assert f"{abs(int(lon_deg)):03d}$^\\circ${lon_min:05.2f}'" in latex_result

        # Test decimal format contains original values
        decimal_result = format_position_string(lat, lon, "decimal")
        assert f"{abs(lat):.4f}°" in decimal_result
        assert f"{abs(lon):.4f}°" in decimal_result


class TestRealWorldCoordinates:
    """Test with real-world oceanographic coordinates."""

    def test_north_atlantic_station(self):
        """Test typical North Atlantic research station coordinates."""
        # Example: OSNAP mooring site
        lat, lon = 59.7583, -39.7333

        dmm = format_dmm_comment(lat, lon)
        assert dmm == "59 45.50'N, 039 44.00'W"

        latex = format_position_latex(lat, lon)
        assert latex == "59$^\\circ$45.50'N, 039$^\\circ$44.00'W"

    def test_arctic_station(self):
        """Test Arctic research station coordinates."""
        # Example: Fram Strait moorings
        lat, lon = 78.8333, 0.0

        dmm = format_dmm_comment(lat, lon)
        assert dmm == "78 50.00'N, 000 00.00'E"

    def test_southern_ocean_station(self):
        """Test Southern Ocean coordinates."""
        # Example: Drake Passage
        lat, lon = -60.5, -65.0

        dmm = format_dmm_comment(lat, lon)
        assert dmm == "60 30.00'S, 065 00.00'W"


class TestParseDmmFormat:
    """Test parsing of DMM coordinate strings."""

    def test_parse_dmm_standard_format(self):
        """Test parsing standard DMM format with degree symbols."""
        result = parse_dmm_format("52° 49.99' N, 51° 32.81' W")
        assert result[0] == pytest.approx(52.83316666666667, abs=0.0001)
        assert result[1] == pytest.approx(-51.54683333333333, abs=0.0001)

    def test_parse_dmm_compact_format(self):
        """Test parsing compact DMM format without spaces."""
        result = parse_dmm_format("52°49.99'N,51°32.81'W")
        assert result[0] == pytest.approx(52.83316666666667, abs=0.0001)
        assert result[1] == pytest.approx(-51.54683333333333, abs=0.0001)

    def test_parse_dmm_european_comma(self):
        """Test parsing European format with comma as decimal separator."""
        result = parse_dmm_format("56° 34,50' N, 52° 40,33' W")
        assert result[0] == pytest.approx(56.575, abs=0.0001)
        assert result[1] == pytest.approx(-52.672166666667, abs=0.0001)

    def test_parse_dmm_south_east_quadrant(self):
        """Test parsing coordinates in SE quadrant."""
        result = parse_dmm_format("33° 51.41' S, 151° 12.92' E")
        assert result[0] == pytest.approx(-33.8568333, abs=0.0001)
        assert result[1] == pytest.approx(151.215333, abs=0.0001)

    def test_parse_dmm_different_quote_chars(self):
        """Test parsing with different quote characters."""
        # Test with prime symbol
        result1 = parse_dmm_format("52° 49.99′ N, 51° 32.81′ W")
        # Test with regular single quote (which the parser expects)
        result2 = parse_dmm_format("52° 49.99' N, 51° 32.81' W")

        expected_lat = pytest.approx(52.83316666666667, abs=0.0001)
        expected_lon = pytest.approx(-51.54683333333333, abs=0.0001)

        assert result1[0] == expected_lat and result1[1] == expected_lon
        assert result2[0] == expected_lat and result2[1] == expected_lon

    def test_parse_dmm_zero_coordinates(self):
        """Test parsing zero coordinates."""
        result = parse_dmm_format("0° 00.00' N, 0° 00.00' E")
        assert result[0] == pytest.approx(0.0, abs=0.0001)
        assert result[1] == pytest.approx(0.0, abs=0.0001)

    def test_parse_dmm_invalid_format(self):
        """Test that invalid format raises ValueError."""
        with pytest.raises(ValueError, match="DMM format not recognized"):
            parse_dmm_format("invalid coordinate string")

    def test_parse_dmm_missing_direction(self):
        """Test that missing direction raises ValueError."""
        with pytest.raises(ValueError, match="DMM format not recognized"):
            parse_dmm_format("52° 49.99', 51° 32.81'")

    def test_parse_dmm_roundtrip_consistency(self):
        """Test that parsing and formatting are consistent."""
        # Original coordinates
        orig_lat, orig_lon = 65.7458, -24.4792

        # Format to DMM
        dmm_str = format_dmm_comment(orig_lat, orig_lon)
        # Add degree symbols for parsing
        dmm_str_with_degrees = (
            dmm_str.replace(" ", "° ", 1)
            .replace("'N", "' N")
            .replace("'S", "' S")
            .replace("'E", "' E")
            .replace("'W", "' W")
        )
        dmm_str_with_degrees = dmm_str_with_degrees.replace(", ", ", ").replace(
            ", ", "° ", 1
        )
        dmm_str_with_degrees = dmm_str_with_degrees.replace("° °", "°")

        # Properly format for parsing (add degree symbol to longitude)
        parts = dmm_str.split(", ")
        lat_part = parts[0].replace(" ", "° ", 1)
        lon_part = parts[1].replace(" ", "° ", 1)
        dmm_str_parseable = f"{lat_part}, {lon_part}"

        # Parse back
        parsed_lat, parsed_lon = parse_dmm_format(dmm_str_parseable)

        # Should be very close to original (within rounding precision)
        assert parsed_lat == pytest.approx(orig_lat, abs=0.001)
        assert parsed_lon == pytest.approx(orig_lon, abs=0.001)

    def test_parse_dmm_various_spacing(self):
        """Test parsing with various spacing patterns."""
        coords_list = [
            "52°49.99'N, 51°32.81'W",  # No spaces
            "52° 49.99' N, 51° 32.81' W",  # Standard spacing
            "52°  49.99'  N,  51°  32.81'  W",  # Extra spaces
        ]

        expected_lat = pytest.approx(52.83316666666667, abs=0.0001)
        expected_lon = pytest.approx(-51.54683333333333, abs=0.0001)

        for coords_str in coords_list:
            result = parse_dmm_format(coords_str)
            assert result[0] == expected_lat
            assert result[1] == expected_lon


class TestCoordinateParsingIntegration:
    """Test integration between parsing and formatting functions."""

    def test_format_parse_roundtrip_dmm(self):
        """Test that DMM formatting and parsing are inverse operations."""
        test_coords = [
            (65.7458, -24.4792),  # North Atlantic
            (-33.8568, 151.2153),  # Sydney
            (0.0, 0.0),  # Null Island
            (78.8333, 0.0),  # Arctic
            (-60.5, -65.0),  # Southern Ocean
        ]

        for orig_lat, orig_lon in test_coords:
            # Format to DMM comment
            dmm_comment = format_dmm_comment(orig_lat, orig_lon)

            # Convert to parseable format (add degree symbols)
            parts = dmm_comment.split(", ")
            lat_part = parts[0].replace(" ", "° ", 1)
            lon_part = parts[1].replace(" ", "° ", 1)
            dmm_parseable = f"{lat_part}, {lon_part}"

            # Parse back
            parsed_lat, parsed_lon = parse_dmm_format(dmm_parseable)

            # Should match within reasonable precision (0.001 degrees ≈ 100m)
            assert parsed_lat == pytest.approx(orig_lat, abs=0.001)
            assert parsed_lon == pytest.approx(orig_lon, abs=0.001)

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
            # Test all formatting functions don't crash
            dmm = format_dmm_comment(lat, lon)
            latex = format_position_latex(lat, lon)
            decimal = format_position_string(lat, lon, "decimal")

            # Basic validation that strings are properly formatted
            assert "'" in dmm  # Contains minute symbol
            assert "$" in latex  # Contains LaTeX formatting
            assert "°" in decimal  # Contains degree symbol


class TestFormatGeographicBounds:
    """Test geographic bounds formatting with hemisphere indicators."""

    def test_standard_negative_positive_longitude(self):
        """Test standard -180/180 format with negative to positive longitude."""
        result = format_geographic_bounds(-90, 50, -30, 60)
        assert result == "50.00°N to 60.00°N, 90.00°W to 30.00°W"

    def test_positive_longitude_360_format(self):
        """Test 0-360 format with positive longitudes."""
        result = format_geographic_bounds(270, 50, 330, 60)
        assert result == "50.00°N to 60.00°N, 270.00°E to 330.00°E"

    def test_crossing_prime_meridian(self):
        """Test bounds crossing the prime meridian."""
        result = format_geographic_bounds(-10, -20, 10, 20)
        assert result == "20.00°S to 20.00°N, 10.00°W to 10.00°E"

    def test_edge_case_180_degrees(self):
        """Test 180°/-180° longitude edge case."""
        result = format_geographic_bounds(-180, -45, 180, 45)
        assert result == "45.00°S to 45.00°N, 180.00° to 180.00°"

    def test_zero_coordinates(self):
        """Test zero latitude and longitude."""
        result = format_geographic_bounds(0, 0, 0, 0)
        assert result == "0.00° to 0.00°, 0.00° to 0.00°"

    def test_southern_hemisphere(self):
        """Test coordinates entirely in southern hemisphere."""
        result = format_geographic_bounds(120, -60, 150, -30)
        assert result == "60.00°S to 30.00°S, 120.00°E to 150.00°E"

    def test_western_hemisphere(self):
        """Test coordinates entirely in western hemisphere."""
        result = format_geographic_bounds(-150, 20, -120, 50)
        assert result == "20.00°N to 50.00°N, 150.00°W to 120.00°W"

    def test_crossing_equator(self):
        """Test bounds crossing the equator."""
        result = format_geographic_bounds(-50, -10, -30, 10)
        assert result == "10.00°S to 10.00°N, 50.00°W to 30.00°W"

    def test_single_point(self):
        """Test bounds representing a single point."""
        result = format_geographic_bounds(-75.5, 45.25, -75.5, 45.25)
        assert result == "45.25°N to 45.25°N, 75.50°W to 75.50°W"

    def test_zero_longitude_exactly(self):
        """Test exactly 0° longitude."""
        result = format_geographic_bounds(0, 30, 0, 40)
        assert result == "30.00°N to 40.00°N, 0.00° to 0.00°"

    def test_zero_latitude_exactly(self):
        """Test exactly 0° latitude."""
        result = format_geographic_bounds(-10, 0, 10, 0)
        assert result == "0.00° to 0.00°, 10.00°W to 10.00°E"


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
        # Remove latitude/longitude attributes to force position access
        del mock_station2.latitude
        del mock_station2.longitude
        mock_station2.position.latitude = 61.0
        mock_station2.position.longitude = -21.0

        mock_cruise.station_registry = {
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
        mock_cruise.station_registry = {}

        # Mock departure port (support both formats)
        mock_dep_port = MagicMock()
        mock_dep_port.latitude = 64.0  # Direct attribute format
        mock_dep_port.longitude = -22.0
        mock_dep_port.position.latitude = 64.0  # Nested position format
        mock_dep_port.position.longitude = -22.0
        mock_dep_port.name = "Reykjavik"
        mock_cruise.config.departure_port = mock_dep_port

        # Mock arrival port (support both formats)
        mock_arr_port = MagicMock()
        mock_arr_port.latitude = 78.0  # Direct attribute format
        mock_arr_port.longitude = 15.0
        mock_arr_port.position.latitude = 78.0  # Nested position format
        mock_arr_port.position.longitude = 15.0
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
        # Remove latitude/longitude attributes to force position access
        del mock_station2.latitude
        del mock_station2.longitude
        mock_station2.position.latitude = 61.0
        mock_station2.position.longitude = -21.0

        mock_cruise.station_registry = {
            "STN_001": mock_station1,
            "STN_002": mock_station2,
        }
        mock_cruise.config.departure_port = None
        mock_cruise.config.arrival_port = None

        # Extract coordinates
        lats, lons, names, dep_port, arr_port = extract_coordinates_from_cruise(
            mock_cruise
        )

        # Should handle both attribute patterns
        assert len(lats) == 2
        assert len(lons) == 2
        assert 60.0 in lats
        assert 61.0 in lats
        assert -20.0 in lons
        assert -21.0 in lons
