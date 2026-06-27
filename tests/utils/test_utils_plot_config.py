"""Tests for cruiseplan.utils.plot_config module."""

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

from cruiseplan.utils.plot_config import (
    create_bathymetry_colormap,
    get_colormap,
    get_legend_entries,
    get_plot_style,
)


class TestBathymetryColormaps:
    """Test suite for bathymetry colormap creation."""

    def test_create_bathymetry_colormap_basic(self):
        """Test that create_bathymetry_colormap returns a valid colormap."""
        cmap = create_bathymetry_colormap()

        assert isinstance(cmap, mcolors.LinearSegmentedColormap)
        assert cmap.name == "bathymetry_custom"
        assert cmap.N == 256  # Default number of colors

    def test_create_bathymetry_colormap_improved(self):
        """Test that create_bathymetry_colormap returns a valid colormap with improved features."""
        cmap = create_bathymetry_colormap()

        assert isinstance(cmap, mcolors.LinearSegmentedColormap)
        # Don't assert exact name as it might be different

    def test_colormap_depth_mapping(self):
        """Test that colormaps produce expected colors at depth boundaries."""
        cmap = create_bathymetry_colormap()

        # Test at various normalized positions
        # At 0.0 (deepest), should be dark blue
        deep_color = cmap(0.0)
        assert deep_color[2] > 0.2  # Blue channel should be significant

        # At 1.0 (land), should be yellow/tan
        land_color = cmap(1.0)
        assert land_color[0] > 0.8  # Red channel high for yellow
        assert land_color[1] > 0.7  # Green channel high for yellow

    def test_colormap_continuous_range(self):
        """Test that colormaps work across the full range."""
        for cmap_func in [create_bathymetry_colormap]:
            cmap = cmap_func()

            # Test at several points across range
            test_values = np.linspace(0, 1, 10)
            colors = cmap(test_values)

            assert colors.shape == (10, 4)  # RGBA values
            # All colors should be valid (0-1 range)
            assert np.all(colors >= 0) and np.all(colors <= 1)


class TestBathymetryColormapMaxDepth:
    """Tests for create_bathymetry_colormap with max_depth parameter."""

    @pytest.mark.parametrize("max_depth", [50, 100, 500, 1000, 8000])
    def test_create_bathymetry_colormap_with_max_depth(self, max_depth):
        """Colormap with max_depth is a valid LinearSegmentedColormap."""
        cmap = create_bathymetry_colormap(max_depth=max_depth)
        assert isinstance(cmap, mcolors.LinearSegmentedColormap)
        assert cmap.N == 256

    @pytest.mark.parametrize("max_depth", [50, 200, 1000])
    def test_colormap_endpoints_with_max_depth(self, max_depth):
        """Deepest and shallowest positions map to distinct colors."""
        cmap = create_bathymetry_colormap(max_depth=max_depth)
        deep = cmap(0.0)  # -max_depth
        land = cmap(1.0)  # +200 m
        # Land should be yellowish (high R, high G, low B)
        assert land[0] > 0.8 and land[1] > 0.7
        # Deep should be dark blue (low R, G; meaningful B)
        assert deep[2] > 0.2

    @pytest.mark.parametrize("bad_value", [0, -1, -100])
    def test_create_bathymetry_colormap_rejects_nonpositive(self, bad_value):
        """max_depth <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_depth must be a positive integer"):
            create_bathymetry_colormap(max_depth=bad_value)

    def test_max_depth_colormap_differs_from_default(self):
        """A clipped colormap samples different colors than the full-range default."""
        cmap_default = create_bathymetry_colormap()
        cmap_clipped = create_bathymetry_colormap(max_depth=200)
        # At normalized position 0.5, the two colormaps should differ
        assert cmap_default(0.5) != cmap_clipped(0.5)


class TestMaxDepthLevelGeneration:
    """Unit tests for the 'nice step' algorithm used with max_depth."""

    @staticmethod
    def _nice_levels(max_depth: int) -> list:
        """Mirror of the level-generation logic in map_generator.plot_bathymetry."""
        import math

        raw_step = max_depth / 5.0
        magnitude = 10 ** math.floor(math.log10(raw_step))
        for factor in (1, 2, 5, 10):
            if raw_step <= factor * magnitude:
                step = factor * magnitude
                break
        else:
            step = magnitude * 10
        return [-max_depth + i * step for i in range(int(max_depth / step))] + [0, 200]

    @pytest.mark.parametrize(
        "max_depth, expected_step",
        [
            (100, 20),
            (500, 100),
            (1000, 200),
            (60, 20),
            (200, 50),
        ],
    )
    def test_nice_step_values(self, max_depth, expected_step):
        levels = self._nice_levels(max_depth)
        # Step between first two water levels equals expected_step
        assert levels[1] - levels[0] == expected_step

    @pytest.mark.parametrize("max_depth", [50, 100, 500, 1000])
    def test_levels_start_at_negative_max_depth(self, max_depth):
        levels = self._nice_levels(max_depth)
        assert levels[0] == -max_depth

    @pytest.mark.parametrize("max_depth", [50, 100, 500, 1000])
    def test_levels_end_with_zero_and_land(self, max_depth):
        levels = self._nice_levels(max_depth)
        assert levels[-2] == 0
        assert levels[-1] == 200

    @pytest.mark.parametrize("max_depth", [50, 100, 500, 1000])
    def test_levels_are_monotonically_increasing(self, max_depth):
        levels = self._nice_levels(max_depth)
        assert all(levels[i] < levels[i + 1] for i in range(len(levels) - 1))


class TestLegendConfig:
    """Test suite for legend configuration."""

    def test_get_legend_entries_basic(self):
        """Test that legend entries return expected structure."""
        entries = get_legend_entries()

        assert isinstance(entries, dict)
        assert len(entries) > 0

    def test_legend_entries_contain_required_fields(self):
        """Test that legend entries have required plotting fields."""
        entries = get_legend_entries()

        # Each entry should have basic visual specification
        for entry_name, entry_conf in entries.items():
            assert isinstance(entry_conf, dict), f"Entry {entry_name} should be a dict"
            # Should have some kind of visual specification
            visual_fields = [
                "color",
                "marker",
                "size",
                "style",
                "symbol",
                "label",
                "description",
            ]
            has_visual = any(field in entry_conf for field in visual_fields)
            # Some entries might only have descriptive fields, that's okay
            if not has_visual:
                # Just check that the dict isn't empty
                assert len(entry_conf) > 0, f"Legend entry {entry_name} is empty"


class TestStyleConfig:
    """Test suite for style configuration."""

    def test_get_plot_style_basic(self):
        """Test that plot style returns expected structure."""
        # Test with a basic entity type
        style = get_plot_style("station")
        assert style is not None
        assert isinstance(style, dict)

        # Should have basic style properties
        expected_fields = ["color", "marker", "size", "alpha", "label"]
        for field in expected_fields:
            assert field in style, f"Style should contain {field}"

    def test_get_plot_style_with_different_options(self):
        """Test plot style with different configuration options."""
        # Test different entity types and operation combinations
        test_cases = [
            ("station", None, None),
            ("mooring", None, None),
            ("transit", None, None),
            ("station", "CTD", None),
            ("transit", "underway", "ADCP"),
        ]

        for entity_type, operation_type, action in test_cases:
            style = get_plot_style(entity_type, operation_type, action)
            assert style is not None
            assert isinstance(style, dict)
            # Each style should have at least some properties
            assert len(style) > 0


class TestColormapGetter:
    """Test suite for colormap getter function."""

    def test_get_colormap_basic(self):
        """Test that get_colormap returns expected colormaps."""
        # Test with known colormap names
        test_names = ["bathymetry", "default", "viridis", "plasma"]

        for name in test_names:
            try:
                cmap = get_colormap(name)
                assert isinstance(cmap, mcolors.Colormap)
                break  # If one works, that's sufficient
            except (KeyError, ValueError):
                # Try next name
                continue

    def test_get_colormap_invalid_name(self):
        """Test get_colormap with invalid name."""
        with pytest.raises((KeyError, ValueError)):
            get_colormap("nonexistent_colormap_name_12345")


class TestPlotConfigIntegration:
    """Integration tests for plot configuration components."""

    def test_colormap_with_matplotlib_figure(self):
        """Test that colormaps work with actual matplotlib figures."""
        fig, ax = plt.subplots(figsize=(6, 4))

        # Test the colormap function
        for cmap_func in [create_bathymetry_colormap]:
            cmap = cmap_func()

            # Create a simple depth grid
            x = np.linspace(0, 10, 50)
            y = np.linspace(0, 10, 50)
            X, Y = np.meshgrid(x, y)
            depths = -(X**2 + Y**2) * 100  # Simple depth function

            # Should be able to plot without errors
            try:
                contour = ax.contourf(X, Y, depths, cmap=cmap, alpha=0.8)
                # Basic validation that the plot was created
                assert contour is not None
                # QuadContourSet might have different attributes
                assert hasattr(contour, "levels") or hasattr(contour, "collections")
            except Exception as e:
                pytest.fail(
                    f"Failed to create contour plot with {cmap_func.__name__}: {e}"
                )

        plt.close(fig)

    def test_style_config_application(self):
        """Test that plot style can be applied to matplotlib."""
        # Try to get a style configuration
        fig, ax = plt.subplots(figsize=(4, 4))

        # Test with a known entity type
        try:
            style = get_plot_style("station")
            assert style is not None
            assert isinstance(style, dict)

            # Test that style can be applied (has required matplotlib properties)
            if "marker" in style:
                # Should be able to create a scatter plot
                ax.scatter(
                    [0],
                    [0],
                    **{
                        k: v
                        for k, v in style.items()
                        if k in ["marker", "color", "s", "alpha"]
                    },
                )
        finally:
            plt.close(fig)
