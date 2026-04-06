"""Manage dauber skill commands — install to Claude Code or Pi Agent Skills."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

commands_app = typer.Typer(
    name="commands",
    help="Install agent skill commands (Claude Code or Pi).",
)

_COMMAND_GROUPS = [
    "assess",
    "assignments",
    "content",
    "course",
    "discuss",
    "grading",
    "rubrics",
]

_PI_SKILL_NAMES = [
    "assess-setup",
    "assess-ai-pass",
    "assess-refine",
    "assess-submit",
    "assignments-create",
    "content-publish",
    "course-overview",
    "course-setup",
    "discuss-announce",
    "grading-overview",
    "rubrics-create",
]


def _get_repo_root() -> Path:
    """Return the dauber repository root (four levels above this file)."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _install_claude_commands(repo_root: Path, overwrite: bool, local: bool) -> None:
    """Copy bundled Claude Code command files to the target directory."""
    if local:
        dst_root = Path.cwd() / ".claude" / "commands"
    else:
        dst_root = Path.home() / ".claude" / "commands"

    installed: list[str] = []
    skipped: list[str] = []

    for group in _COMMAND_GROUPS:
        src_dir = repo_root / ".claude" / "commands" / group
        if not src_dir.is_dir():
            typer.echo(f"Source directory not found: {src_dir}", err=True)
            raise typer.Exit(1)

        dst_dir = dst_root / group
        dst_dir.mkdir(parents=True, exist_ok=True)

        for src_file in sorted(src_dir.glob("*.md")):
            dst_file = dst_dir / src_file.name
            if dst_file.exists() and not overwrite:
                typer.echo(
                    f"Skipping {group}/{src_file.name} (exists, use --overwrite)"
                )
                skipped.append(f"{group}/{src_file.name}")
                continue

            shutil.copy2(src_file, dst_file)
            installed.append(f"{group}/{src_file.name}")
            typer.echo(f"Installed {group}/{src_file.name}")

    if installed:
        typer.echo(f"\n{len(installed)} file(s) installed to {dst_root}")
    if skipped:
        typer.echo(f"{len(skipped)} file(s) skipped")
    if not installed and not skipped:
        typer.echo("No command files found to install.")


def _install_pi_skills(repo_root: Path, overwrite: bool, global_install: bool) -> None:
    """Copy bundled Pi Agent Skills to the target directory."""
    if global_install:
        dst_root = Path.home() / ".pi" / "agent" / "skills"
    else:
        dst_root = Path.cwd() / ".pi" / "skills"

    src_root = repo_root / ".pi" / "skills"
    installed: list[str] = []
    skipped: list[str] = []

    for skill_name in _PI_SKILL_NAMES:
        src_file = src_root / skill_name / "SKILL.md"
        if not src_file.is_file():
            typer.echo(f"Source not found: {src_file}", err=True)
            raise typer.Exit(1)

        dst_dir = dst_root / skill_name
        dst_file = dst_dir / "SKILL.md"

        if dst_file.exists() and not overwrite:
            typer.echo(f"Skipping {skill_name} (exists, use --overwrite)")
            skipped.append(skill_name)
            continue

        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dst_file)
        installed.append(skill_name)
        typer.echo(f"Installed {skill_name}/SKILL.md")

    if installed:
        typer.echo(f"\n{len(installed)} skill(s) installed to {dst_root}")
    if skipped:
        typer.echo(f"{len(skipped)} skill(s) skipped")
    if not installed and not skipped:
        typer.echo("No skill files found to install.")


@commands_app.command("install")
def commands_install(
    overwrite: bool = typer.Option(
        False, "--overwrite", help="Overwrite existing files without asking."
    ),
    local: bool = typer.Option(
        False,
        "--local",
        help="Install Claude commands to ./.claude/commands/ instead of ~/.claude/commands/.",
    ),
    pi: bool = typer.Option(
        False,
        "--pi",
        help="Install as Pi Agent Skills instead of Claude Code commands.",
    ),
    global_: bool = typer.Option(
        False,
        "--global",
        help="Install Pi skills to ~/.pi/agent/skills/ (requires --pi).",
    ),
) -> None:
    """Install bundled skill commands for Claude Code or Pi.

    Default (no flags): Claude Code commands → ~/.claude/commands/
    --local:            Claude Code commands → ./.claude/commands/
    --pi:               Pi Agent Skills      → ./.pi/skills/
    --pi --global:      Pi Agent Skills      → ~/.pi/agent/skills/

    Existing files are skipped unless --overwrite is passed.
    """
    if local and pi:
        typer.echo(
            "Error: --local is for Claude Code. Use --pi without --global"
            " for project-local Pi skills.",
            err=True,
        )
        raise typer.Exit(1)
    if global_ and not pi:
        typer.echo("Error: --global is only valid with --pi.", err=True)
        raise typer.Exit(1)

    repo_root = _get_repo_root()

    if pi:
        _install_pi_skills(repo_root, overwrite, global_)
    else:
        _install_claude_commands(repo_root, overwrite, local)
