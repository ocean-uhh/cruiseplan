# CruisePlan Coding Conventions

## File Naming Conventions

### Utility/Helper Files

The project follows a clear naming convention for utility and helper files:

1. **Module-level shared utilities**: `<module>_utils.py`
   - Used when utilities are shared across multiple files within a module
   - Example: `cli/cli_utils.py` - contains utilities used by multiple CLI commands

2. **File-specific utilities**: `<filename>_utils.py`
   - Used when utilities are specific to a single file
   - Example: `init_utils.py` - contains helpers for functions in `__init__.py`
   - Example: `activity_utils.py` - contains helpers for activity processing

3. **Package-wide utilities**: Place in `utils/` directory
   - Used for utilities shared across the entire package
   - Examples:
     - `utils/coordinates.py` - coordinate manipulation utilities
     - `utils/config.py` - configuration handling utilities
     - `utils/global_ports.py` - global port definitions

### Benefits

- **Clear ownership**: It's immediately obvious whether utilities are shared or specific
- **Easy discovery**: Developers can quickly find related helper functions
- **Better organization**: Prevents utility files from becoming dumping grounds
- **Simpler testing**: File-specific utils can be tested alongside their main file

### Guidelines

- If a utility function is used by 2+ files in the same module → put in `<module>_utils.py`
- If a utility function is used by only 1 file → put in `<filename>_utils.py`
- If a utility function is used across different modules → put in `utils/` directory
- Keep utility files focused and cohesive - split if they grow too large

## Function Complexity Guidelines

Functions should not exceed 75 statements. If a function is too complex:

1. Extract helper functions for distinct sub-tasks
2. Create utility modules for related operations
3. Use descriptive function names that clearly indicate purpose
4. Each function should have a single, clear responsibility

## Type Annotations

- Always use type hints for function parameters and return values
- Prefer modern Python 3.9+ syntax (`list[str]` over `List[str]`)
- Use `Optional[T]` explicitly instead of `T = None`
- Add type stubs for external libraries when available

## Import Organization

1. Standard library imports
2. Third-party library imports
3. Local package imports
4. Relative imports (sparingly)

Group imports within each section alphabetically.