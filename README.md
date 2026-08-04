# CruisePlan

[![Tests](https://github.com/ocean-uhh/cruiseplan/actions/workflows/tests.yml/badge.svg)](https://github.com/ocean-uhh/cruiseplan/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-sphinx-blue)](https://ocean-uhh.github.io/cruiseplan/)

CruisePlan is a Python tool for planning oceanographic research cruises. It takes a YAML cruise description and produces enriched configurations, cruise schedules, maps (PNG/KML), LaTeX station tables, and real-time workplans.

Full documentation: https://ocean-uhh.github.io/cruiseplan/

---

## Installation

### pip

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install cruiseplan
```

### conda / mamba

```bash
conda create -n cruiseplan -c conda-forge python=3.11
conda activate cruiseplan
pip install cruiseplan
```

### Development install

```bash
git clone https://github.com/ocean-uhh/cruiseplan.git
cd cruiseplan

# Using conda/mamba (includes dev dependencies)
conda env create -f environment.yml
conda activate cruiseplan
pip install -e ".[dev]"

# Using venv
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Quick start

```bash
# Enrich a YAML config, generate schedule and map
cruiseplan process cruise.yaml
cruiseplan schedule cruise_enriched.yaml
cruiseplan map cruise_enriched.yaml
```

Or use the Python API:

```python
import cruiseplan

# Process and schedule in one step
process_result, schedule_result = cruiseplan.run("cruise.yaml")
print(schedule_result.files_created)
```

See the [Usage Guide](https://ocean-uhh.github.io/cruiseplan/usage.html) and [API Reference](https://ocean-uhh.github.io/cruiseplan/api/modules.html) for details.

---

## Breaking changes

**v0.3.0:** Commands `cruiseplan download` and `cruiseplan pandoi` removed. Bathymetry flags shortened (`--bathymetry-*` → `--bathy-*`).

**v0.3.3:** YAML now uses `transects:` (not `transits:`) for line operations and `waypoints:` (not `stations:`) for point operations.

**v0.3.6:** Module renames — `cruiseplan.schema` → `cruiseplan.config`, `cruiseplan.core` → `cruiseplan.runtime`, `cruiseplan.calculators` → `cruiseplan.timeline`.

**v0.4.0:** `cruiseplan stationplan` renamed to `cruiseplan forecast`. New `cruiseplan list` and `cruiseplan run` subcommands added.

---

## Development

```bash
pytest tests/
cd docs && make html
```

**Disclaimer:** This software is provided without warranty. Users are responsible for validating all calculations, timing estimates, and operational feasibility before finalising cruise plans.

---

## Acknowledgments

The original timing algorithms were developed by [Yves Sorge](https://orcid.org/0009-0007-0043-9207) and [Sunke Trace-Kleeberg](https://orcid.org/0000-0002-5980-2492). CruisePlan was initially developed by [Yves Sorge](https://orcid.org/0009-0007-0043-9207) and redesigned by [Eleanor Frajka-Williams](https://orcid.org/0000-0001-8773-7838).

If you use CruisePlan in your research, please cite it using [CITATION.cff](CITATION.cff).

---

## Related software

The following tools may also be useful (*untested*):

**Python/GIS:**
- [cruisetools](https://github.com/simondreutter/cruisetools) — QGIS plugin

**Python:**
- [dreamcoat](https://github.com/mvdh7/dreamcoat) — personal cruise planning tools

**R:**
- [cruisePlanning](https://github.com/clayton33/cruisePlanning) — DFO AZMP-based cruise planning
- [cruisetrack-planner](https://github.com/fribalet/cruisetrack-planner) — cruise track planning with Shiny app

**MATLAB:**
- [PlanCampanha](https://github.com/PedroVelez/PlanCampanha) — cruise planning from CSV input
