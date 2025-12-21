# CruisePlan

> 🌊 **Comprehensive Oceanographic Research Cruise Planning System** — Streamlining the  process of planning oceanographic research expeditions.

[![Tests](https://github.com/ocean-uhh/cruiseplan/actions/workflows/tests.yml/badge.svg)](https://github.com/ocean-uhh/cruiseplan/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-sphinx-blue)](https://ocean-uhh.github.io/cruiseplan/)

## Background & Context

**The Challenge:** Oceanographic cruise planning involves complex route and timing calculations, frequent unit conversions (nautical miles <-> kilometers, decimal degrees <-> degrees decimal minutes), and rapid plan updates.  Different people may need different formats--spreadsheets for quick calculations, degrees/decimal minutes for navigation, kilometers for station spacing, knots for voyage timing.  Using historical station locations may be preferred, but can be tricky to access.

- **Fragmented Tools**: Scattered spreadsheets, manual calculations, custom code snippets
- **Time-Intensive Processes**: Semi-manual station planning, timing calculations, and proposal formatting  
- **Error-Prone Workflows**: Manual depth lookups, coordinate formatting, and schedule validation

**The Solution:** CruisePlan provides an integrated, semi-automated system for an efficient cruise-planning workflow.


## Target Audience

**Primary Users:**
- **🔬 Oceanographic Researchers**: Principal investigators designing research expeditions
- **📊 Students**: Graduate students learning cruise planning methodology
- **📋 Proposal Writers**: Scientists preparing funding proposals with detailed cruise plans

**Research Domains:**
The primary development of CruisePlan is for physical oceanographers, with CTD stations, mooring deployments and glider operations as default.  However, it is possible to incorporate any type of point, line or area operation of a ship with a specified manual duration based on your own experience.

CruisePlan transforms complex cruise planning from a weeks-long manual process into a structured, validated workflow that produces proposal-ready documentation with some checks on operational feasibility.



**Important - Version 0.2.0 Release:** This release includes breaking changes to depth field semantics. See our [Development Roadmap](https://ocean-uhh.github.io/cruiseplan/roadmap.html) for future plans.

**Disclaimer:** This software is provided "as is" without warranty of any kind. Users are responsible for validating all calculations, timing estimates, and operational feasibility for their specific cruise requirements. Always consult with marine operations staff and verify all outputs before finalizing cruise plans.

📘 Full documentation available at:  
👉 https://ocean-uhh.github.io/cruiseplan/

### Related Software

The following cruise planning tools may also be of interest (*Disclaimer: We have not tested these*):

**Python/GIS:**
- [cruisetools](https://github.com/simondreutter/cruisetools) - Python plugin for QGIS.

**Python:**
- [dreamcoat](https://github.com/mvdh7/dreamcoat) - Personal tools for cruise planning

**R:**
- [cruisePlanning](https://github.com/clayton33/cruisePlanning) - R package for cruise planning based on DFO's AZMP
- [cruisePlanningStatic](https://github.com/clayton33/cruisePlanningStatic) - similar to the above
- [cruisetrack-planner](https://github.com/fribalet/cruisetrack-planner) - Cruise track planning in R plus Shiny App (https://seaflow.shinyapps.io/cruisetrackplanner/)

**MATLAB:**
- [PlanCampanha](https://github.com/PedroVelez/PlanCampanha) - Cruise planning with CSV as input
---

## 🚀 What's Included

- ✅ **Interactive station planning**: Click-to-place stations on bathymetric maps with real-time depth feedback
- 📓 **PANGAEA integration**: Browse and incorporate past cruise data for context
- 📄 **Multi-format outputs**: Generate NetCDF, LaTeX reports, PNG maps, KML files, and CSV data
- 🔍 **Cruise validation**: Automated checking of cruise configurations and operational feasibility
- 🎨 **Documentation**: Sphinx-based docs with API references and usage guides
- 📦 **Modern Python packaging**: Complete with testing, linting, and CI/CD workflows
- 🧾 **Scientific citation support**: CITATION.cff for academic attribution

---

## Project structure

For a detailed breakdown of the package architecture and module descriptions, see the [Project Structure Documentation](https://ocean-uhh.github.io/cruiseplan/project_structure.html).

```text
cruiseplan/
├── .github/
│   └── workflows/              # GitHub Actions for tests, docs, PyPI
├── docs/                       # Sphinx-based documentation
│   ├── source/                 # reStructuredText + MyST Markdown + _static
│   └── Makefile                # for building HTML docs
├── notebooks/                  # Example notebooks and demos
├── cruiseplan/                 # Main Python package
│   ├── cli/                    # Command-line interface modules
│   ├── core/                   # Core cruise planning logic
│   ├── calculators/            # Distance, duration, routing calculators
│   ├── data/                   # Bathymetry and PANGAEA data handling
│   ├── interactive/            # Interactive station picking tools
│   ├── output/                 # Multi-format output generators
│   └── utils/                  # Utilities and coordinate handling
├── tests/                      # Comprehensive pytest test suite
├── data/                       # Bathymetry datasets
├── .gitignore
├── .pre-commit-config.yaml
├── CITATION.cff                # Citation file for academic use
├── CONTRIBUTING.md             # Contribution guidelines
├── LICENSE                     # MIT license
├── README.md
├── pyproject.toml              # Modern packaging config
├── requirements.txt            # Core package dependencies
├── requirements-dev.txt        # Development and testing tools
├── environment.yml             # Conda environment specification
└── PROJECT_SPECS.md            # Development roadmap and specifications
```

---

## 🔧 Installation

### Option 1: Install from PyPI (Most Users)

For general use, install the latest stable release from PyPI. **Note**: CruisePlan is in active development (0.x versions) with occasional breaking changes.

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install CruisePlan
pip install cruiseplan
```

### Option 2: Install Latest from GitHub

For the latest features and bug fixes:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install directly from GitHub
pip install git+https://github.com/ocean-uhh/cruiseplan.git
```

### Option 3: Development Installation

For development or contributing to CruisePlan:

```bash
# Clone the repository
git clone https://github.com/ocean-uhh/cruiseplan.git
cd cruiseplan

# Option A: Using conda/mamba
conda env create -f environment.yml
conda activate cruiseplan
pip install -e ".[dev]"

# Option B: Using pip with virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

**Dependencies**: Core packages are listed in `requirements.txt`, development tools in `requirements-dev.txt`. The conda `environment.yml` loads from these files automatically.

To run tests:

```bash
pytest tests/
```

To build the documentation locally:

```bash
cd docs
make html
```

---

## 📚 Learn More

- [Installation Guide](https://ocean-uhh.github.io/cruiseplan/installation.html)
- [Usage Guide](https://ocean-uhh.github.io/cruiseplan/usage.html)
- [API Reference](https://ocean-uhh.github.io/cruiseplan/api/modules.html)
- [Development Roadmap](https://ocean-uhh.github.io/cruiseplan/roadmap.html)

---

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guidelines](https://github.com/ocean-uhh/cruiseplan/blob/main/CONTRIBUTING.md) for details on how to get started.

For information about planned improvements and development priorities, see our [Development Roadmap](https://ocean-uhh.github.io/cruiseplan/roadmap.html).

---

## 🙏 Acknowledgments & Citation

The original timing algorithms were developed by [Yves Sorge](https://orcid.org/0009-0007-0043-9207) and [Sunke Trace-Kleeberg](https://orcid.org/0000-0002-5980-2492).  CruisePlan initial software development by [Yves Sorge](https://orcid.org/0009-0007-0043-9207) and redesigned by [Eleanor Frajka-Williams](https://orcid.org/0000-0001-8773-7838).

If you use CruisePlan in your research, please cite it using the information in [CITATION.cff](CITATION.cff).

