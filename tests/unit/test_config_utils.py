from cruiseplan.utils.config import format_station_for_yaml, format_transect_for_yaml


def test_format_station_standard():
    """Test standard station formatting with depth."""
    input_data = {'lat': 47.1234567, 'lon': -52.9876543, 'depth': 250.55}
    index = 5

    result = format_station_for_yaml(input_data, index)

    expected = {
        "name": "STN_005",             # Padding check (03d)
        "latitude": 47.12346,         # Rounding check (5 decimals)
        "longitude": -52.98765,       # Rounding check (5 decimals)
        "depth": 250.6,                # Depth rounding (1 decimal)
        "comment": "Interactive selection"
    }

    assert result == expected

def test_format_station_missing_depth():
    """Test fallback when depth is missing (e.g. bathymetry failed)."""
    input_data = {'lat': 10.0, 'lon': 10.0} # No depth key
    index = 1

    result = format_station_for_yaml(input_data, index)

    # Should default to -9999
    assert result['depth'] == -9999

def test_format_transect_standard():
    """Test standard transect formatting."""
    input_data = {
        'start': {'lat': 10.12345678, 'lon': 20.12345678},
        'end':   {'lat': 30.98765432, 'lon': 40.98765432}
    }
    index = 2

    result = format_transect_for_yaml(input_data, index)

    expected_structure = {
        "name": "Section_02",          # Padding check (02d)
        "start": {
            "latitude": 10.12346,     # Rounding check
            "longitude": 20.12346
        },
        "end": {
            "latitude": 30.98765,
            "longitude": 40.98765
        },
        "reversible": True
    }

    assert result == expected_structure
    # Double check it matches the structure exactly
    assert result['start']['latitude'] == 10.12346
    assert result['end']['longitude'] == 40.98765
