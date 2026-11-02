# Contributing

cruiseplan is developed in the Experimental Oceanography group at the University of Hamburg. Bug reports are welcome as issues; code changes are agreed with the maintainer before a pull request.

Set up and check:

```bash
pip install -e ".[dev]"
pytest -m "not slow"
ruff check . && ruff format --check .
```

Conventions and tests: [developer guide](https://ocean-uhh.github.io/cruiseplan/advanced/developer_guide.html).
