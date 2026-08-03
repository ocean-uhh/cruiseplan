"""Unit tests for forecast CLI helper functions."""

from argparse import Namespace
from pathlib import Path

from cruiseplan.cli.forecast import _resolve_output_path


class TestResolveOutputPath:
    def test_returns_none_when_output_not_set(self):
        args = Namespace(output=None, output_dir=Path("."))
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
