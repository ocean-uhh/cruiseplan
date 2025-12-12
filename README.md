# CruisePlan

> 🌊 Oceanographic Research Cruise Planning System — comprehensive software for planning, documenting, and optimizing oceanographic research cruises.

[![Tests](https://github.com/ocean-uhh/cruiseplan/actions/workflows/tests.yml/badge.svg)](https://github.com/ocean-uhh/cruiseplan/actions/workflows/tests.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-sphinx-blue)](https://ocean-uhh.github.io/cruiseplan/)

CruisePlan assists oceanographic researchers in designing optimal station layouts, calculating precise operational timings, and generating professional proposal outputs adhering to scientific standards like CF conventions.

📘 Full documentation available at:  
👉 https://ocean-uhh.github.io/cruiseplan/

---

## 🚀 What's Included

- ✅ **Interactive station planning**: Click-to-place stations on bathymetric maps with real-time depth feedback
- 📓 **PANGAEA integration**: Browse and incorporate past cruise data for context
- 📄 **Multi-format outputs**: Generate NetCDF, LaTeX reports, HTML maps, KML files, and CSV data
- 🔍 **Comprehensive validation**: Automated checking of cruise configurations and operational feasibility
- 🎨 **Professional documentation**: Sphinx-based docs with API references and usage guides
- 📦 **Modern Python packaging**: Complete with testing, linting, and CI/CD workflows
- 🧾 **Scientific citation support**: CITATION.cff for academic attribution

---

## Project structure

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

---

## 🔧 Quickstart

Install CruisePlan in development mode:

```bash
git clone https://github.com/ocean-uhh/cruiseplan.git
cd cruiseplan

# Option A: Using conda/mamba (recommended)
conda env create -f environment.yml
conda activate cruiseplan
pip install -e .

# Option B: Using pip
pip install -r requirements-dev.txt
pip install -e .
```

To run tests:

```bash
pytest
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
- [Development Roadmap](https://github.com/ocean-uhh/cruiseplan/blob/main/PROJECT_SPECS.md)
- [Contributing Guidelines](https://github.com/ocean-uhh/cruiseplan/blob/main/CONTRIBUTING.md)

---

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guidelines](https://github.com/ocean-uhh/cruiseplan/blob/main/CONTRIBUTING.md) for details on how to get started.

For information about planned improvements and the development roadmap, see [PROJECT_SPECS.md](PROJECT_SPECS.md).

---

## 📣 Citation

If you use CruisePlan in your research, please cite it using the information in [CITATION.cff](CITATION.cff).

For BibTeX format:

```bibtex
@software{cruiseplan,
  author = {Frajka-Williams, Eleanor},
  title = {CruisePlan: Oceanographic Research Cruise Planning System},
  url = {https://github.com/ocean-uhh/cruiseplan},
  year = {2025}
}
```
