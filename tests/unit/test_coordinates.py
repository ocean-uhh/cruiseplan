"""
Tests for coordinate formatting utilities.
"""

import pytest

from cruiseplan.utils.coordinates import (
    UnitConverter,
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
        assert result == "65$^\\circ$44.75'$N$, 024$^\\circ$28.75'$W$"

    def test_format_position_latex_south_east(self):
        """Test LaTeX formatting for SE quadrant."""
        result = format_position_latex(-33.8568, 151.2153)
        assert result == "33$^\\circ$51.41'$S$, 151$^\\circ$12.92'$E$"

    def test_format_position_latex_zero(self):
        """Test LaTeX formatting for zero coordinates."""
        result = format_position_latex(0.0, 0.0)
        assert result == "00$^\\circ$00.00'$N$, 000$^\\circ$00.00'$E$"

    def test_format_position_latex_precise(self):
        """Test LaTeX formatting with precise coordinates."""
        result = format_position_latex(50.1234, -40.5678)
        assert result == "50$^\\circ$07.40'$N$, 040$^\\circ$34.07'$W$"

    def test_format_position_latex_leading_zeros_longitude(self):
        """Test that longitude gets proper leading zeros in LaTeX."""
        result = format_position_latex(5.1234, -8.5678)
        assert result == "05$^\\circ$07.40'$N$, 008$^\\circ$34.07'$W$"


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
        assert latex == "59$^\\circ$45.50'$N$, 039$^\\circ$44.00'$W$"

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
