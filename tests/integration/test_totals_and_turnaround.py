"""
Leg turnaround of 0 min, and the work-days total against the elapsed time.

tc1_single: STN_001 at 2850 m, 1 m/s down and up, so the cast is
2 x 2850 / 60 = 95 min plus the turnaround (cruise value 30 min).
"""

import logging
import re
import warnings
from pathlib import Path

import pytest
import yaml

import cruiseplan
from cruiseplan.config.yaml_io import load_yaml
from cruiseplan.output.latex_generator import LaTeXGenerator
from cruiseplan.runtime.cruise import CruiseInstance
from cruiseplan.timeline.scheduler import timeline_minutes

ROOT = Path(__file__).parents[2]
TC1 = ROOT / "tests" / "fixtures" / "tc1_single.yaml"
PYCNMIX = ROOT / "data" / "pycnmix-2026-v1.yaml"


def _schedule(path: Path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        logging.disable(logging.WARNING)
        try:
            return cruiseplan.schedule(config_file=path, format=None).timeline
        finally:
            logging.disable(logging.NOTSET)


@pytest.mark.parametrize(("leg_turnaround", "minutes"), [(0.0, 95.0), (None, 125.0)])
def test_leg_turnaround_zero_is_used(tmp_path, leg_turnaround, minutes):
    """A leg turnaround of 0 min is the leg's value, not a missing one."""
    cfg = yaml.safe_load(TC1.read_text())
    if leg_turnaround is not None:
        cfg["legs"][0]["turnaround_time_minutes"] = leg_turnaround
    path = tmp_path / "tc1.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    (stn,) = [r for r in _schedule(path) if r.label == "STN_001"]
    assert stn.duration_minutes == pytest.approx(minutes)


def _work_days_total_h(config, timeline) -> float:
    tex = LaTeXGenerator().generate_work_days_table(config, timeline)
    totals = re.findall(
        r"\\textbf\{Total duration\} & & \\textbf\{([\d.]+)\} & \\textbf\{([\d.]+)\}",
        tex,
    )
    assert totals
    return sum(float(a) + float(b) for a, b in totals)


@pytest.mark.parametrize("leg_delay", [0.0, 120.0])
def test_work_days_total_is_elapsed_time(tmp_path, leg_delay):
    """pycnmix (buffers on every leg), with and without a leg delay."""
    cfg = yaml.safe_load(PYCNMIX.read_text())
    cfg["legs"][1]["delay_start_minutes"] = leg_delay
    path = tmp_path / "pycnmix.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    timeline = _schedule(path)
    config = CruiseInstance.from_dict(load_yaml(path)).config
    elapsed_h = timeline_minutes(timeline) / 60.0
    assert _work_days_total_h(config, timeline) == pytest.approx(elapsed_h, abs=0.5)
