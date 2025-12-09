"""
Tests for coordinate formatting utilities.
"""

import pytest

from cruiseplan.utils.coordinates import (
    UnitConverter,
    format_dmm_comment,
    format_position_latex,
    format_position_string,
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
