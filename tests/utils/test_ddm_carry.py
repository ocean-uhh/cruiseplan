"""Degrees-decimal-minutes carry and the shared haversine, for every output format."""

import pytest

from cruiseplan.api.stationplan_api import _format_ddm_coordinate
from cruiseplan.forecast.formatter import format_coordinates
from cruiseplan.output.html_generator import _convert_decimal_to_deg_min_html
from cruiseplan.output.latex_generator import LaTeXGenerator
from cruiseplan.timeline.distance import haversine_distance
from cruiseplan.utils.coordinates import (
    CoordConverter,
    ddm_parts,
    distance_nm,
    format_ddm_comment,
    format_position_latex,
)
from cruiseplan.utils.units import NM_PER_KM


@pytest.mark.parametrize(
    ("value", "decimals", "expected"),
    [
        (0.0, 2, (0, 0.0)),
        (-0.0, 2, (0, 0.0)),
        (59.99999, 2, (60, 0.0)),
        (-59.99999, 2, (60, 0.0)),
        (-0.99999, 2, (1, 0.0)),
        (179.99999, 2, (180, 0.0)),
        (-179.999999, 3, (180, 0.0)),
        (180.0, 2, (180, 0.0)),
        (59.9999, 3, (59, 59.994)),
        (65.7458, 2, (65, 44.75)),
        (-24.4792, 2, (24, 28.75)),
    ],
)
def test_ddm_parts(value, decimals, expected):
    """Minutes are rounded first and 60 minutes carry into the degrees."""
    degrees, minutes = ddm_parts(value, decimals)
    assert (degrees, minutes) == expected
    assert 0 <= minutes < 60


def test_latex_station_table_carries():
    """LaTeX letsgo positions: 59.99999 N, 0.99999 W."""
    lat, lon = LaTeXGenerator()._format_lat_lon_dms(59.99999, -0.99999)
    assert lat == "60\\textdegree00.00'N"
    assert lon == "001\\textdegree00.00'W"


def test_latex_proposal_table_carries():
    """LaTeX proposal tables use format_position_latex."""
    assert format_position_latex(59.99999, -0.99999) == (
        "60$^\\circ$00.00'N, 001$^\\circ$00.00'W"
    )


def test_bridge_waypoints_carry():
    """Bridge waypoint DDM: 2/3-digit degrees, space, hemisphere."""
    assert _format_ddm_coordinate(59.99999, "lat") == "60 00.00 N"
    assert _format_ddm_coordinate(-0.99999, "lon") == "001 00.00 W"


def test_forecast_formatter_carries():
    """Forecast letsgo text uses three decimals."""
    assert format_coordinates(59.9999999, -0.9999999) == ("60 00.000 N", "001 00.000 W")


def test_html_and_yaml_formats_carry():
    """HTML report, YAML decmin fields and DDM comments."""
    assert _convert_decimal_to_deg_min_html(59.9999999) == "60 00.000"
    assert _convert_decimal_to_deg_min_html(-0.9999999) == "-01 00.000"
    assert CoordConverter.format_latitude_decmin(59.9999999) == "60 00.000 N"
    assert CoordConverter.format_longitude_decmin(-0.9999999) == "001 00.000 W"
    assert format_ddm_comment(59.99999, -0.99999) == "60 00.00'N, 001 00.00'W"


def test_layout_unchanged_away_from_rollover():
    """Outputs keep their text layout for ordinary positions."""
    assert _format_ddm_coordinate(65.7458, "lat") == "65 44.75 N"
    assert format_coordinates(65.583733, -29.464) == ("65 35.024 N", "029 27.840 W")
    assert format_position_latex(65.7458, -24.4792) == (
        "65$^\\circ$44.75'N, 024$^\\circ$28.75'W"
    )


def test_distance_nm_one_degree_of_latitude():
    """One degree of latitude on the 6371 km sphere is 60.04 nm."""
    assert distance_nm((45.0, -50.0), (46.0, -50.0)) == pytest.approx(60.04, abs=0.01)
    assert distance_nm((45.0, -50.0), (45.0, -50.0)) == 0.0


def test_haversine_distance_matches_distance_nm():
    """The km haversine is the same great circle as distance_nm."""
    start, end = (44.6488, -63.5752), (45.0, -45.0)  # Halifax to tc1 STN_001
    assert haversine_distance(start, end) * NM_PER_KM == pytest.approx(
        distance_nm(start, end)
    )
    assert distance_nm(start, end) == pytest.approx(789.6, abs=0.05)
