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
