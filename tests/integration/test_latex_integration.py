"""
Integration tests for LaTeX generator with scheduler timeline output.
"""

from pathlib import Path

import pytest

from cruiseplan.calculators.scheduler import generate_timeline
from cruiseplan.output.latex_generator import generate_latex_tables
from cruiseplan.utils.config import ConfigLoader


class TestLatexGeneratorIntegration:
    """Integration tests for LaTeX generator with scheduler output."""



