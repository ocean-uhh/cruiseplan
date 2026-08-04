# CruisePlan Coding Conventions

## Utility file naming

| Scope | Location |
|---|---|
| Used by 2+ files in the same module | `<module>_utils.py` |
| Used by one file only | `<filename>_utils.py` |
| Used across multiple modules | `utils/` directory |

## Function complexity

75-statement limit (Ruff PLR0915). Extract helper functions when a function grows too long.

## Type annotations

Use Python 3.10+ syntax: `list[str]` not `List[str]`, `T | None` not `Optional[T]`.

## Import order

1. Standard library
2. Third-party
3. Local package
4. Relative (sparingly)

Alphabetical within each group.
