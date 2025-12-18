# Contributing to CruisePlan

Thank you for your interest in contributing to CruisePlan! This document provides comprehensive guidelines for contributing to this oceanographic research cruise planning system.

CruisePlan welcomes contributions from oceanographers, software developers, students, and anyone interested in improving scientific cruise planning tools. We value contributions ranging from bug reports and documentation improvements to new features and algorithmic enhancements.

## Types of Contributions

We welcome several types of contributions:

- **🐛 Bug Reports**: Help us identify and fix issues
- **💡 Feature Requests**: Suggest new functionality for cruise planning
- **📖 Documentation**: Improve guides, examples, and API documentation  
- **🧪 Testing**: Add test cases and improve test coverage
- **🔬 Scientific Validation**: Verify calculations and domain accuracy
- **🎨 User Experience**: Enhance interfaces and workflows
- **📊 Performance**: Optimize algorithms and data processing
- **🌐 Integration**: Connect with other oceanographic tools and databases

## Getting Started

### Prerequisites
- **Python 3.9 or later** (3.11+ recommended for development)
- **Git** (for version control)
- **Basic knowledge** of oceanography (helpful for domain-specific contributions)
- **Familiarity** with cruise planning workflows (for feature development)

### Development Environment Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/cruiseplan.git
   cd cruiseplan
   ```

2. **Create isolated development environment and install:**
   ```bash
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

3. **Setup pre-commit hooks:**
   ```bash
   pre-commit install
   ```

4. **Verify installation:**
   ```bash
   pytest --version
   cruiseplan --help
   python -c "import cruiseplan; print('✓ CruisePlan ready for development')"
   ```

## Development Workflow

### Branch Strategy

We use a feature-branch workflow:

1. **Main Branch**: `main` - stable, production-ready code
2. **Feature Branches**: `feature/descriptive-name` - for new development

### Code Standards

#### Style Guidelines
- **Formatter**: [Black](https://black.readthedocs.io/) (line length: 88 characters)
- **Linter**: [Ruff](https://github.com/astral-sh/ruff) with scientific Python settings and import sorting
- **Type Checking**: [mypy](http://mypy-lang.org/) (gradual typing with scientific package overrides)
- **Spell Checking**: [Codespell](https://github.com/codespell-project/codespell) for catching typos
- **Pre-commit Hooks**: Automated code quality checks before commits

#### Code Quality Requirements
- **Type Hints**: Required for all new functions and class methods
- **Docstrings**: [NumPy style](https://numpydoc.readthedocs.io/en/latest/format.html) for all public functions
- **Variable Naming**: Descriptive names, avoid abbreviations
- **Function Length**: Generally <75 statements; refactor longer functions (enforced by Ruff PLR0915)
- **Complexity**: McCabe complexity <15; avoid deeply nested code (enforced by Ruff C901)
- **Function Parameters**: Maximum 8 parameters; use dataclasses/configs for more (enforced by Ruff PLR0913)
- **Branch Complexity**: Maximum 20 branches per function (enforced by Ruff PLR0912)

#### Scientific Code Guidelines
- **Units**: Always document units in docstrings and variable names
- **Coordinate Systems**: Clearly specify (lat/lon, x/y, coordinate reference systems)
- **Physical Constants**: Use well-documented constants with references
- **Algorithms**: Include citations for oceanographic calculations
- **Validation**: Cross-check calculations with established tools where possible

#### Example Function Template
```python
def calculate_ctd_time(
    depth: float, 
    cast_type: str = "profile",
    descent_rate: float = 1.0
) -> float:
    """
    Calculate CTD operation time based on depth and cast parameters.
    
    Parameters
    ----------
    depth : float
        Water depth in meters (positive downward from surface).
    cast_type : str, optional
        Type of CTD cast: "profile" or "yo-yo" (default: "profile").
    descent_rate : float, optional
        CTD descent rate in meters per second (default: 1.0 m/s).
        
    Returns
    -------
    float
        Total operation time in minutes.
        
    Notes
    -----
    Calculation includes descent time, bottom time for sampling,
    and ascent time. 
       
    Examples
    --------
    >>> calculate_ctd_time(2000)  # 2000m depth, standard profile
    85.0
    >>> calculate_ctd_time(1000, cast_type="yo-yo")  # Multiple profiles
    150.0
    """
    # Implementation with clear variable names and comments
    pass
```

### Testing Requirements

#### Test Coverage
- **Minimum Coverage**: 80% for new code, 75% overall
- **Critical Functions**: 95%+ coverage for calculation functions
- **Test Types**: Unit tests, integration tests, property-based tests

#### Testing Strategy
```bash
# Run full test suite
pytest

# Run with coverage report
pytest --cov=cruiseplan --cov-report=html

# Run specific test categories
pytest -m "not slow"          # Skip slow tests during development
pytest tests/unit/            # Unit tests only
pytest tests/integration/     # Integration tests only

# Run tests matching pattern
pytest -k "calculate"         # Tests with 'calculate' in the name
```

#### Writing Tests
- **Test Structure**: Arrange-Act-Assert pattern
- **Test Data**: Use realistic oceanographic values
- **Edge Cases**: Test boundary conditions (0°N, 180°E, max depths)
- **Error Handling**: Test invalid inputs and error conditions
- **Performance**: Include timing tests for critical algorithms

#### Example Test
```python
import pytest
from cruiseplan.calculators.distance import haversine_distance

class TestHaversineDistance:
    """Test haversine distance calculations."""
    
    def test_zero_distance(self):
        """Same point should return zero distance."""
        result = haversine_distance(60.0, -30.0, 60.0, -30.0)
        assert result == pytest.approx(0.0, abs=1e-6)
    
    def test_known_distance(self):
        """Test against known geographic distance."""
        # Distance from Reykjavik to London (approx 1887 km)
        reykjavik_lat, reykjavik_lon = 64.1466, -21.9426
        london_lat, london_lon = 51.5074, -0.1278
        
        distance = haversine_distance(
            reykjavik_lat, reykjavik_lon, 
            london_lat, london_lon
        )
        
        assert distance == pytest.approx(1887, rel=0.01)  # Within 1%
        
    @pytest.mark.parametrize("lat1,lon1,lat2,lon2", [
        (91.0, 0.0, 0.0, 0.0),    # Invalid latitude
        (0.0, 181.0, 0.0, 0.0),   # Invalid longitude  
    ])
    def test_invalid_coordinates(self, lat1, lon1, lat2, lon2):
        """Test error handling for invalid coordinates."""
        with pytest.raises(ValueError, match="Invalid coordinates"):
            haversine_distance(lat1, lon1, lat2, lon2)
```

### Documentation Standards

#### Documentation Types
1. **API Documentation**: Auto-generated from docstrings
2. **User Guides**: Step-by-step workflows and tutorials
3. **Examples**: Jupyter notebooks and practical use cases
4. **Developer Documentation**: Architecture, design decisions, algorithms

#### Building Documentation
```bash
# Install development dependencies (includes documentation tools)
pip install -e ".[dev]"

# Build HTML documentation
cd docs
make html

# Serve locally for review
python -m http.server --directory build/html 8080
# View at http://localhost:8080

# Alternative: use a different port if 8080 is busy
python -m http.server --directory build/html 9000
# View at http://localhost:9000
```

#### Documentation Guidelines
- **Audience-Specific**: Separate content for users vs developers
- **Complete Examples**: All code examples must be runnable
- **Screenshots**: Include for interactive components
- **Cross-References**: Link between related concepts
- **Scientific Context**: Explain oceanographic relevance

### Pull Request Process

#### Before Submitting
1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/descriptive-name
   ```

2. **Development Checklist**:
   - [ ] Code follows style guidelines
   - [ ] All tests pass locally
   - [ ] New tests added for new functionality
   - [ ] Documentation updated
   - [ ] Type hints added
   - [ ] Docstrings written/updated
   - [ ] Pre-commit hooks pass

3. **Run Quality Checks**:
   ```bash
   # Format and lint
   black .
   ruff check . --fix
   
   # Type checking
   mypy cruiseplan/
   
   # Full test suite
   pytest --cov=cruiseplan
   
   # Documentation build
   cd docs && make html
   ```

#### Pull Request Submission

When creating a pull request, GitHub will automatically populate a comprehensive template that guides you through documenting your changes, testing, and scientific validation requirements.

#### Review Process
1. **Automated Checks**: All CI tests must pass
2. **Code Review**: At least one [maintainer](https://github.com/orgs/ocean-uhh/teams/cruiseplan-maintainers) review required



## Reporting Issues

CruisePlan uses structured GitHub issue templates to streamline bug reports and feature requests. When you create a new issue, GitHub will guide you through the appropriate template:

### 🐛 Bug Reports
**Template covers**: Bug description, reproduction steps, expected vs actual behavior, error messages, sample data, and system environment.

**Prepare beforehand**:
- Clear description of the issue and steps to reproduce
- Complete error messages or traceback
- Minimal YAML configuration that reproduces the issue
- System information:
  ```bash
  python --version
  cruiseplan --version
  pip show cruiseplan
  uname -a  # Linux/macOS
  ```

### 💡 Feature Requests  
**Template covers**: Use case, problem description, proposed solution, alternatives considered, implementation ideas, and scientific requirements.

**Prepare beforehand**:
- Scientific motivation and user story
- Clear description of the problem this feature would solve
- Detailed description of desired functionality
- Alternative approaches you've considered
- Technical suggestions if available

### 🔬 Scientific Accuracy Issues
**Template covers**: Calculation/domain issues, reference methods, comparison of expected vs actual results, impact assessment, and validation data.

**Prepare beforehand**:
- References to correct methods or published standards
- Specific examples showing expected vs actual results
- Assessment of scientific impact
- Test cases or validation data

## Community Guidelines

### Code of Conduct
CruisePlan is committed to providing a welcoming, inclusive environment for all contributors regardless of background, experience level, or affiliation. We expect:

- **Respectful Communication**: Professional, constructive interactions
- **Scientific Integrity**: Honest reporting of results and limitations
- **Collaborative Spirit**: Willingness to help others and accept feedback
- **Inclusive Participation**: Welcoming to newcomers and diverse perspectives

### Getting Help
- **Documentation**: Start with official documentation
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Create GitHub Issues for bugs and feature requests
- **Email**: Contact maintainers for security issues or sensitive topics

### Contributing Guidelines Summary
- Follow established coding standards and scientific best practices
- Include comprehensive tests for new functionality
- Update documentation for all changes
- Engage constructively in code review process
- Respect intellectual property and licensing requirements

## Licensing and Attribution

### Contributor License Agreement
By contributing to CruisePlan, you agree that:

1. **License Compatibility**: Your contributions will be licensed under the MIT License
2. **Original Work**: Contributions are your original work or properly attributed
3. **Legal Authority**: You have the right to submit the contributions
4. **No Additional Restrictions**: Contributions don't impose additional licensing restrictions

### Scientific Attribution
- **Citations**: Include appropriate scientific citations in code and documentation
- **Data Sources**: Clearly attribute external datasets and algorithms  
- **Collaboration**: Acknowledge collaborative contributions appropriately
- **Academic Use**: Support proper citation in scientific publications

### Recognition
Contributors are recognized through:
- **GitHub Contributors**: Automatic recognition in repository
- **Release Notes**: Acknowledgment in version release documentation
- **CITATION.cff**: Major contributors included in citation metadata

## Release Process

### Version Strategy
- **Semantic Versioning**: MAJOR.MINOR.PATCH (e.g., 1.2.3)
  - MAJOR: Breaking changes to API or configuration format
  - MINOR: New features, backward compatible
  - PATCH: Bug fixes, backward compatible
- **Release Tags**: GitHub releases with tagged versions for stability

### Release Checklist
- [ ] All tests pass on supported Python versions
- [ ] Documentation updated and builds successfully
- [ ] Performance benchmarks within expected ranges
- [ ] Scientific validation completed for calculation changes
- [ ] Breaking changes documented with migration guides
- [ ] Release notes prepared with contributor acknowledgments

Thank you for contributing to CruisePlan! Your efforts help advance oceanographic research and improve the tools available to the scientific community.
