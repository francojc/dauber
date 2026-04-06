"""Resolve CLI defaults from local/global config files."""

from __future__ import annotations

from typing import Any

import typer

from dauber.core.config_files import read_global_config, read_local_config

# Keys in config that map to assess setup CLI options.
_ASSESS_CONFIG_KEYS = {
    "course_name": "course_title",
    "level": "level",
    "feedback_language": "feedback_language",
    "language_learning": "language_learning",
    "language_level": "language_level",
    "formality": "formality",
    "anonymize": "anonymize",
}


def resolve_course(course: str | None) -> str:
    """Return *course* if given, else fall back to config.

    Checks local config ``canvas_course_id`` first, then global.
    Exits with code 1 if neither provides a value.
    """
    if course is not None:
        return course

    local = read_local_config()
    value = local.get("canvas_course_id")
    if value is not None:
        return str(value)

    global_cfg = read_global_config()
    value = global_cfg.get("canvas_course_id")
    if value is not None:
        return str(value)

    typer.echo(
        "Error: no course specified and no canvas_course_id in config.",
        err=True,
    )
    raise typer.Exit(1)


def resolve_assess_defaults(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Fill *kwargs* with config values for keys still at None.

    Only overwrites keys whose current value is ``None``, so explicit
    CLI flags always win.  Checks local config first, then global.

    Returns the (mutated) *kwargs* dict for convenience.
    """
    local = read_local_config()
    global_cfg = read_global_config()

    for kwarg_key, config_key in _ASSESS_CONFIG_KEYS.items():
        if kwargs.get(kwarg_key) is not None:
            continue
        value = local.get(config_key)
        if value is None:
            value = global_cfg.get(config_key)
        if value is not None:
            kwargs[kwarg_key] = value

    return kwargs


def resolve_anonymize(anonymize: bool | None) -> bool:
    """Return *anonymize* if explicitly set, else fall back to config.

    Defaults to ``False`` when config has no value.
    """
    if anonymize is not None:
        return anonymize

    local = read_local_config()
    value = local.get("anonymize")
    if value is not None:
        return bool(value)

    global_cfg = read_global_config()
    value = global_cfg.get("anonymize")
    if value is not None:
        return bool(value)

    return False
