# Contributing to CruisePlan

Bug reports, documentation improvements, and code contributions are welcome.

## Development setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/cruiseplan.git
cd cruiseplan

# Using conda/mamba
conda env create -f environment.yml
conda activate cruiseplan
pip install -e ".[dev]"

# Or using venv
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Verify:

```bash
pytest --version
cruiseplan --help
```

## Code standards

- **Formatter**: `ruff format .`
- **Linter**: `ruff check . --fix`
- **Type checking**: `mypy cruiseplan/`
- **Docstrings**: NumPy style; required for all public functions and classes
- **Type hints**: required for all public function signatures
- **Function length**: <75 statements (Ruff PLR0915)
- **Units**: always document in docstrings

Run all checks:

```bash
ruff format .
ruff check . --fix
mypy cruiseplan/
pytest --cov=cruiseplan
```

## Testing

```bash
pytest                          # full suite
pytest -m "not slow"            # skip slow tests
pytest tests/unit/              # unit tests only
pytest tests/integration/       # integration tests only
pytest -k "calculate"           # by name pattern
pytest --cov=cruiseplan --cov-report=html
```

Minimum coverage: 80% for new code. Use realistic oceanographic values in test data.

Example:

```python
from cruiseplan.timeline.distance import haversine_distance

def test_zero_distance():
    assert haversine_distance((60.0, -30.0), (60.0, -30.0)) == pytest.approx(0.0, abs=1e-6)

def test_known_distance():
    # Reykjavik to London, approx 1887 km
    dist = haversine_distance((64.1466, -21.9426), (51.5074, -0.1278))
    assert dist == pytest.approx(1887, rel=0.01)
```

## Pull requests

1. Create a feature branch: `git checkout -b feature/descriptive-name`
2. Make changes; add tests for new functionality
3. Run the full check suite (format, lint, mypy, pytest)
4. Submit a PR against `upstream/main` (the `ocean-uhh/cruiseplan` repo, not your fork)

One PR per logical change. Include a short description of what changed and why.

## Reporting issues

Use GitHub Issues. For bugs, include:
- Steps to reproduce
- Full error message or traceback
- Minimal YAML configuration that triggers the issue
- `cruiseplan --version` output

For calculation errors, include a reference to the correct method and an example showing expected vs actual output.

## Licence

Contributions are accepted under the MIT Licence.
