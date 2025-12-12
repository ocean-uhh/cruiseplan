# Contributing to CruisePlan

Thank you for your interest in contributing to CruisePlan! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites
- Python 3.9 or later
- Git

### Installation for Development

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cruiseplan.git
   cd cruiseplan
   ```

2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the package in development mode with all dependencies:
   ```bash
   pip install -e .[dev]
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

## Development Workflow

### Code Style
- We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints where possible
- Write docstrings following [NumPy style](https://numpydoc.readthedocs.io/en/latest/format.html)

### Testing
- Write tests for new functionality
- Ensure all tests pass before submitting a PR
- Run tests with: `pytest`
- Check code coverage: `pytest --cov=cruiseplan`

### Documentation
- Update docstrings for any modified functions
- Add examples for new features in the demo notebook
- Build documentation locally: `cd docs && make html`

### Pull Requests
1. Create a feature branch from `main`
2. Make your changes
3. Run tests and linting: `pytest && ruff check .`
4. Update documentation if needed
5. Submit a pull request with a clear description

## Project Structure

```
cruiseplan/
├── cli/           # Command-line interface
├── core/          # Core cruise planning logic
├── calculators/   # Distance, duration, routing calculations
├── data/          # Data loading and caching
├── interactive/   # Interactive widgets and tools
├── output/        # Report generation (HTML, LaTeX, KML, NetCDF)
└── utils/         # Utilities and helpers
```

## Reporting Issues

When reporting bugs or requesting features:
- Use GitHub Issues
- Provide a clear description and steps to reproduce
- Include relevant error messages and system information
- For bugs, include a minimal reproducible example

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. Please be respectful and constructive in all interactions.

## License

By contributing to CruisePlan, you agree that your contributions will be licensed under the same license as the project (MIT License).
