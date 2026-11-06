"""Old names kept for one release, in one table each; every use warns.

Each entry still works in this release and is removed in :data:`REMOVED_IN`.
The migration page lists every entry (a test checks it).
"""

import warnings

#: The release that removes every name in this module's tables.
REMOVED_IN = "0.7.0"

#: Old dotted API name -> what to use instead.
RENAMED: dict[str, str] = {
    "cruiseplan.CruiseSchedule": "cruiseplan.Timeline",
    "cruiseplan.timeline.CruiseSchedule": "cruiseplan.timeline.Timeline",
    "cruiseplan.timeline.scheduler.CruiseSchedule": "cruiseplan.timeline.Timeline",
}

#: Old dictionary key of a timeline record -> ActivityRecord attribute.
RECORD_KEYS: dict[str, str] = {
    "time": "start_time",
    "lat": "entry_lat",
    "lon": "entry_lon",
    "operation_type": "op_type",
    "delay_start": "delay_start_minutes",
    "water_depth": "water_depth_m",
    "operation_depth": "operation_depth_m",
}


def message(old: str) -> str:
    """Return the warning text for the deprecated API name *old*."""
    return f"{old} is deprecated and is removed in {REMOVED_IN}; use {RENAMED[old]}."


def warn(old: str, *, stacklevel: int = 3) -> None:
    """Warn that the API name *old* (a key of :data:`RENAMED`) is deprecated."""
    warnings.warn(message(old), DeprecationWarning, stacklevel=stacklevel)


def record_key_message(key: str) -> str:
    """Return the warning text for dictionary access to a record."""
    attribute = RECORD_KEYS.get(key, key)
    return (
        f"ActivityRecord[{key!r}] is deprecated and is removed in {REMOVED_IN}; "
        f"use the attribute record.{attribute}."
    )


def warn_record_key(key: str) -> None:
    """Warn that a timeline record was read like a dictionary."""
    warnings.warn(record_key_message(key), DeprecationWarning, stacklevel=3)


def module_getattr(module: str, name: str, replacements: dict[str, object]) -> object:
    """
    Resolve a deprecated module attribute, warning once per use.

    Parameters
    ----------
    module : str
        Dotted name of the module whose ``__getattr__`` calls this.
    name : str
        The attribute asked for.
    replacements : dict
        Old attribute name -> the object that replaces it.

    Returns
    -------
    object
        The replacement object.

    Raises
    ------
    AttributeError
        If *name* is not a deprecated attribute of *module*.
    """
    old = f"{module}.{name}"
    if old in RENAMED and name in replacements:
        warn(old, stacklevel=4)
        return replacements[name]
    raise AttributeError(f"module {module!r} has no attribute {name!r}")
