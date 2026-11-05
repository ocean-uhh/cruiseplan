"""Unit tests for forecast CLI helper functions."""

from argparse import Namespace
from pathlib import Path

from cruiseplan.cli.forecast import _resolve_output_path


class TestResolveOutputPath:
    def test_returns_none_when_output_not_set(self):
        args = Namespace(output=None, output_dir=Path())
        assert _resolve_output_path(args, ".kml") is None

    def test_plain_path_concatenation(self):
        args = Namespace(output=Path("result.kml"), output_dir=Path("out"))
        assert _resolve_output_path(args, ".kml") == Path("out/result.kml")

    def test_swaps_bad_suffix(self):
        args = Namespace(output=Path("result.txt"), output_dir=Path("out"))
        result = _resolve_output_path(args, ".kml", {".txt", ".tex", ".png"})
        assert result == Path("out/result.kml")

    def test_keeps_correct_suffix_when_bad_suffixes_given(self):
        args = Namespace(output=Path("result.kml"), output_dir=Path("out"))
        result = _resolve_output_path(args, ".kml", {".txt", ".tex", ".png"})
        assert result == Path("out/result.kml")

    def test_no_bad_suffixes_passes_filename_unchanged(self):
        args = Namespace(output=Path("plan.tex"), output_dir=Path("route"))
        assert _resolve_output_path(args, ".tex") == Path("route/plan.tex")

    def test_swaps_case_insensitive(self):
        args = Namespace(output=Path("result.TXT"), output_dir=Path("out"))
        result = _resolve_output_path(args, ".kml", {".txt", ".tex", ".png"})
        assert result == Path("out/result.kml")


class TestPositionArguments:
    """--current-position parsing and argv joining."""

    def test_parse_forms(self):
        from cruiseplan.cli.forecast import parse_position

        assert parse_position("-74.62,164.30") == (-74.62, 164.30)
        assert parse_position("-74.62 164.30") == (-74.62, 164.30)
        assert parse_position(" 65.0268, -31.3702 ") == (65.0268, -31.3702)

    def test_parse_rejects_bad_values(self):
        import pytest

        from cruiseplan.cli.forecast import parse_position

        for text in ("65.0", "1,2,3", "95,10", "abc,def"):
            with pytest.raises(ValueError):
                parse_position(text)

    def test_join_argv(self):
        from cruiseplan.cli.forecast import join_position_argv

        assert join_position_argv(["--current-position", "-74.6,164.3", "x"]) == [
            "--current-position=-74.6,164.3",
            "x",
        ]
        assert join_position_argv(["--current-position", "-74.6", "-164.3"]) == [
            "--current-position=-74.6,-164.3"
        ]
        unchanged = ["--current-position", "65.0,-31.3", "--lat", "-5", "5"]
        assert join_position_argv(unchanged) == unchanged
