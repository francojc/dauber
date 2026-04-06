"""Read and write dauber config files (TOML)."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

_xdg = Path(os.environ.get("XDG_CONFIG_HOME", "") or (Path.home() / ".config"))
GLOBAL_CONFIG_DIR = _xdg / "dauber"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "config.toml"
LOCAL_CONFIG_PATH = Path("dauber") / "config.toml"

GLOBAL_FIELDS = {
    "name": "Instructor name",
    "institution": "Institution name",
    "level": "Default educational level (undergraduate/graduate/professional)",
    "feedback_language": "Default feedback language (e.g., English, Spanish)",
    "formality": "Default feedback tone (casual/formal)",
    "language_learning": "Language learning course by default (true/false)",
}

LOCAL_FIELDS = {
    "course_title": "Course title",
    "course_code": "Course code (e.g., SPA-212-T)",
    "canvas_course_id": "Canvas course ID (numeric)",
    "term": "Term (e.g., Spring, Fall)",
    "year": "Year (e.g., 2026)",
    "level": "Educational level (undergraduate/graduate/professional)",
    "feedback_language": "Feedback language (e.g., English, Spanish)",
    "language_learning": "Language learning course (true/false)",
    "language_level": "ACTFL proficiency level (or NA)",
    "formality": "Feedback tone (casual/formal)",
    "anonymize": "Anonymize student PII in assessment files (true/false)",
}


def read_global_config() -> dict[str, Any]:
    """Read global config from $XDG_CONFIG_HOME/dauber/config.toml.

    Returns empty dict if file does not exist.
    """
    if not GLOBAL_CONFIG_PATH.is_file():
        return {}
    with open(GLOBAL_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def write_global_config(data: dict[str, Any]) -> Path:
    """Write global config to $XDG_CONFIG_HOME/dauber/config.toml.

    Creates parent directories if needed. Returns the path written.
    """
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_CONFIG_PATH, "wb") as f:
        tomli_w.dump(data, f)
    return GLOBAL_CONFIG_PATH


def read_local_config(base: Path | None = None) -> dict[str, Any]:
    """Read local config from dauber/config.toml.

    Args:
        base: Repository root. Defaults to cwd.

    Returns empty dict if file does not exist.
    """
    path = (base or Path.cwd()) / LOCAL_CONFIG_PATH
    if not path.is_file():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def write_local_config(data: dict[str, Any], base: Path | None = None) -> Path:
    """Write local config to dauber/config.toml.

    Creates parent directories if needed. Returns the path written.
    """
    path = (base or Path.cwd()) / LOCAL_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
    return path


def merge_configs(
    global_cfg: dict[str, Any], local_cfg: dict[str, Any]
) -> list[tuple[str, Any, str]]:
    """Merge global and local configs into annotated triples.

    Returns a list of (key, value, source) where source is
    "local", "global", or "not set".
    """
    result: list[tuple[str, Any, str]] = []

    # All known keys: global-only first, then local (preserving order,
    # skipping duplicates that appear in both).
    seen: set[str] = set()
    all_keys: list[str] = []
    for key in GLOBAL_FIELDS:
        all_keys.append(key)
        seen.add(key)
    for key in LOCAL_FIELDS:
        if key not in seen:
            all_keys.append(key)
            seen.add(key)

    for key in all_keys:
        if key in local_cfg and local_cfg[key] != "":
            result.append((key, local_cfg[key], "local"))
        elif key in global_cfg and global_cfg[key] != "":
            result.append((key, global_cfg[key], "global"))
        else:
            result.append((key, None, "not set"))

    return result
