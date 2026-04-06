"""Config sub-app — manage global and local dauber configuration."""

from __future__ import annotations

from pathlib import Path

import typer

from dauber.core.config_files import (
    GLOBAL_FIELDS,
    LOCAL_FIELDS,
    merge_configs,
    read_global_config,
    read_local_config,
    write_global_config,
    write_local_config,
)

config_app = typer.Typer(
    name="config",
    help="Manage global and local configuration (TOML).",
)


def _prompt_bool(prompt: str, default: bool) -> bool:
    """Prompt for a yes/no value."""
    suffix = " [Y/n]" if default else " [y/N]"
    raw = typer.prompt(prompt + suffix, default="y" if default else "n")
    return raw.strip().lower() in ("y", "yes", "true")


def _coerce_value(key: str, raw: str) -> object:
    """Coerce a string prompt value to the appropriate type."""
    if key == "canvas_course_id":
        return int(raw)
    if key == "year":
        return int(raw)
    if key in ("language_learning", "anonymize"):
        return raw.strip().lower() in ("true", "yes", "y")
    return raw


@config_app.command("init")
def config_init(
    base: str = typer.Option(".", "--base", help="Repository root directory."),
) -> None:
    """Create or update local course config (./dauber/config.toml).

    Prompts for course title, code, Canvas ID, term, feedback language,
    and other per-course settings. Pre-fills from global config when
    available.
    """
    base_path = Path(base).resolve()
    global_cfg = read_global_config()
    existing = read_local_config(base_path)

    data: dict[str, object] = {}
    for key, description in LOCAL_FIELDS.items():
        default = existing.get(key) or global_cfg.get(key, "")
        if isinstance(default, bool):
            data[key] = _prompt_bool(description, default)
        else:
            raw = typer.prompt(description, default=str(default) if default else "")
            data[key] = _coerce_value(key, raw)

    path = write_local_config(data, base_path)
    typer.echo(f"Wrote {path}")


DEFAULT_GLOBAL = {
    "name": "",
    "institution": "",
    "level": "undergraduate",
    "feedback_language": "English",
    "formality": "casual",
    "language_learning": False,
}


@config_app.command("global")
def config_global(
    defaults: bool = typer.Option(
        False,
        "--defaults",
        help="Write default config without prompting.",
    ),
) -> None:
    """Set instructor-level defaults ($XDG_CONFIG_HOME/dauber/config.toml).

    Prompts for name, institution, educational level, feedback language,
    and other defaults shared across all courses. Use --defaults to
    write a starter config without prompting.
    """
    existing = read_global_config()

    if defaults:
        data = {**DEFAULT_GLOBAL, **existing}
        path = write_global_config(data)
        typer.echo(f"Wrote {path}")
        return

    data: dict[str, object] = {}
    for key, description in GLOBAL_FIELDS.items():
        default = existing.get(key, "")
        if key == "language_learning":
            data[key] = _prompt_bool(
                description, bool(default) if default != "" else False
            )
        else:
            raw = typer.prompt(description, default=str(default) if default else "")
            data[key] = raw

    path = write_global_config(data)
    typer.echo(f"Wrote {path}")


@config_app.command("show")
def config_show() -> None:
    """Show merged configuration with source annotations.

    Displays all config keys with their values and whether each comes
    from global config, local config, or is not set. Local values
    override global.
    """
    global_cfg = read_global_config()
    local_cfg = read_local_config()
    merged = merge_configs(global_cfg, local_cfg)

    if not global_cfg and not local_cfg:
        typer.echo("No configuration found.")
        typer.echo("Run 'dauber config global' or 'dauber config init' to get started.")
        typer.echo(
            "Global: $XDG_CONFIG_HOME/dauber/config.toml  Local: ./dauber/config.toml"
        )
        raise typer.Exit()

    max_key = max(len(t[0]) for t in merged)
    for key, value, source in merged:
        if value is None:
            display = "(not set)"
        else:
            display = str(value)
        tag = f"[{source}]"
        typer.echo(f"  {key:<{max_key}}  {display:<30}  {tag}")
