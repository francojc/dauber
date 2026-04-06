# Feature Spec: Pi Skills Support for `dauber commands install`

**Status:** Proposed
**Date:** 2026-03-24
**Target version:** v0.1.7

## Problem Statement

Easel bundles Claude Code slash commands (`.claude/commands/`) and can
install them globally or locally via `dauber commands install`. However,
Pi (another coding agent harness) uses a different skill format — the
[Agent Skills standard](https://agentskills.io/specification) — with
`SKILL.md` files inside named directories under `.pi/skills/`.

Users who work with Pi cannot use the bundled commands without manually
converting them. Easel should support both harnesses natively.

## Proposed Solution

Add a `--pi` flag to `dauber commands install` that installs skills in
Pi's Agent Skills format instead of Claude Code's slash-command format.

### CLI Interface

```
dauber commands install              # Claude → ~/.claude/commands/ (unchanged)
dauber commands install --local      # Claude → ./.claude/commands/ (unchanged)
dauber commands install --pi         # Pi     → ./.pi/skills/       (new)
dauber commands install --pi --global# Pi     → ~/.pi/agent/skills/ (new)
```

The `--pi` flag:
- Defaults to **local** install (`./.pi/skills/` in cwd) because Pi
  skills are typically project-scoped
- Accepts `--global` to install to `~/.pi/agent/skills/` instead
- Is mutually exclusive with `--local` (which is Claude-specific
  terminology)

Note: the existing `--local` flag remains Claude-only. For Pi, local
is the default; `--global` is the opt-in override.

### Dual-Format Source Files

Easel needs to ship **both** formats. The conversion between Claude
commands and Pi skills is mechanical but not trivial — the frontmatter
schemas differ and Pi requires a specific directory structure.

#### Option A: Ship both formats in the repo (recommended)

```
dauber/
├── .claude/commands/           # Claude Code format (existing)
│   ├── assess/
│   │   ├── setup.md
│   │   ├── ai-pass.md
│   │   ├── refine.md
│   │   └── submit.md
│   ├── assignments/create.md
│   ├── content/publish.md
│   ├── course/overview.md
│   ├── course/setup.md
│   ├── discuss/announce.md
│   ├── grading/overview.md
│   └── rubrics/create.md
└── .pi/skills/                 # Pi Agent Skills format (new)
    ├── assess-setup/SKILL.md
    ├── assess-ai-pass/SKILL.md
    ├── assess-refine/SKILL.md
    ├── assess-submit/SKILL.md
    ├── assignments-create/SKILL.md
    ├── content-publish/SKILL.md
    ├── course-overview/SKILL.md
    ├── course-setup/SKILL.md
    ├── discuss-announce/SKILL.md
    ├── grading-overview/SKILL.md
    └── rubrics-create/SKILL.md
```

**Rationale:** Avoids runtime conversion, both formats are reviewable
in the repo, and the install command is a simple copy like the existing
Claude path.

#### Option B: Ship Claude format only, convert at install time

A converter function would rewrite frontmatter during install. Simpler
repo structure but adds code complexity and a potential point of failure.

**Recommendation:** Option A. The files are small and rarely change.
Maintaining both avoids runtime complexity.

### Frontmatter Mapping

Each Claude command maps to one Pi skill. The conversion rules:

| Claude field | Pi field | Notes |
|---|---|---|
| — | `name` | Derived: `{group}-{filename}` (e.g., `assess-setup`) |
| `description` | `description` | Copied as-is; Pi requires this |
| `args` | — | Dropped (Pi has no args spec; args go in the body) |
| `argument-hint` | — | Dropped |
| `allowed-tools` | — | Dropped (Pi doesn't use this) |

The body content (everything after the closing `---`) is copied
verbatim. No changes needed — the instructions reference `dauber` CLI
commands which work identically regardless of harness.

### Pi Skill Naming Convention

Pi requires:
- Directory name matches `name` frontmatter field
- Lowercase letters, numbers, hyphens only
- No leading/trailing hyphens, no consecutive hyphens
- Max 64 characters

Mapping from Claude's `{group}/{filename}.md`:
- `assess/setup.md` → `assess-setup/SKILL.md` (name: `assess-setup`)
- `assess/ai-pass.md` → `assess-ai-pass/SKILL.md`
- `assignments/create.md` → `assignments-create/SKILL.md`
- `content/publish.md` → `content-publish/SKILL.md`
- `course/overview.md` → `course-overview/SKILL.md`
- `course/setup.md` → `course-setup/SKILL.md`
- `discuss/announce.md` → `discuss-announce/SKILL.md`
- `grading/overview.md` → `grading-overview/SKILL.md`
- `rubrics/create.md` → `rubrics-create/SKILL.md`

## Implementation Plan

### 1. Create Pi skill files in the dauber repo

Add `.pi/skills/` directory to the dauber repo with pre-converted
SKILL.md files for all 11 commands. Each has:

```markdown
---
name: {group}-{command}
description: {description from Claude command}
---

{body from Claude command, unchanged}
```

### 2. Update `commands.py`

#### New constants

```python
_PI_SKILLS_DIR = ".pi" / "skills"  # relative to repo root

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
```

#### Updated `install` command signature

```python
@commands_app.command("install")
def commands_install(
    overwrite: bool = typer.Option(
        False, "--overwrite",
        help="Overwrite existing files without asking.",
    ),
    local: bool = typer.Option(
        False, "--local",
        help="Install to ./.claude/commands/ instead of ~/.claude/commands/.",
    ),
    pi: bool = typer.Option(
        False, "--pi",
        help="Install as Pi Agent Skills instead of Claude Code commands.",
    ),
    global_: bool = typer.Option(
        False, "--global",
        help="Install Pi skills to ~/.pi/agent/skills/ (global).",
    ),
) -> None:
```

#### Dispatch logic

```python
if pi:
    _install_pi_skills(repo_root, overwrite, global_)
else:
    _install_claude_commands(repo_root, overwrite, local)
```

#### `_install_pi_skills()` function

```python
def _install_pi_skills(
    repo_root: Path, overwrite: bool, global_install: bool
) -> None:
    if global_install:
        dst_root = Path.home() / ".pi" / "agent" / "skills"
    else:
        dst_root = Path.cwd() / ".pi" / "skills"

    src_root = repo_root / ".pi" / "skills"
    installed, skipped = [], []

    for skill_name in _PI_SKILL_NAMES:
        src_dir = src_root / skill_name
        src_file = src_dir / "SKILL.md"
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
```

#### Refactor existing code

Extract the current Claude install logic into `_install_claude_commands()`
for symmetry.

### 3. Update help text

```python
commands_app = typer.Typer(
    name="commands",
    help="Install agent skill commands (Claude Code or Pi).",
)
```

### 4. Validation

Add a check: `--pi` and `--local` are mutually exclusive (they target
different harnesses). `--global` is only valid with `--pi`.

```python
if local and pi:
    typer.echo("Error: --local is for Claude Code. Use --pi without"
               " --global for project-local Pi skills.", err=True)
    raise typer.Exit(1)
if global_ and not pi:
    typer.echo("Error: --global is only valid with --pi.", err=True)
    raise typer.Exit(1)
```

### 5. Tests

Add to `tests/cli/test_commands.py`:

```python
def _setup_pi_source(tmp_path: Path) -> Path:
    """Create a fake repo root with one Pi skill."""
    repo = tmp_path / "repo"
    skill = repo / ".pi" / "skills" / "assess-setup"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: assess-setup\n---\n# setup")
    return repo


def test_commands_install_pi_local(tmp_path):
    """--pi installs to ./.pi/skills/ in cwd."""
    repo = _setup_pi_source(tmp_path)
    project = tmp_path / "project"
    project.mkdir()

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi"])

    assert result.exit_code == 0
    assert "Installed assess-setup/SKILL.md" in result.output
    dst = project / ".pi" / "skills" / "assess-setup" / "SKILL.md"
    assert dst.is_file()


def test_commands_install_pi_global(tmp_path):
    """--pi --global installs to ~/.pi/agent/skills/."""
    repo = _setup_pi_source(tmp_path)
    home = tmp_path / "home"

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.home", return_value=home),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi", "--global"])

    assert result.exit_code == 0
    dst = home / ".pi" / "agent" / "skills" / "assess-setup" / "SKILL.md"
    assert dst.is_file()


def test_commands_install_pi_skip_existing(tmp_path):
    """Pi skills: existing files skipped without --overwrite."""
    repo = _setup_pi_source(tmp_path)
    project = tmp_path / "project"
    existing = project / ".pi" / "skills" / "assess-setup"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("# old")

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi"])

    assert result.exit_code == 0
    assert "Skipping assess-setup" in result.output
    assert (existing / "SKILL.md").read_text() == "# old"


def test_commands_install_pi_overwrite(tmp_path):
    """Pi skills: --overwrite replaces existing."""
    repo = _setup_pi_source(tmp_path)
    project = tmp_path / "project"
    existing = project / ".pi" / "skills" / "assess-setup"
    existing.mkdir(parents=True)
    (existing / "SKILL.md").write_text("# old")

    with (
        patch("dauber.cli.commands._get_repo_root", return_value=repo),
        patch("dauber.cli.commands._PI_SKILL_NAMES", ["assess-setup"]),
        patch("pathlib.Path.cwd", return_value=project),
    ):
        result = runner.invoke(app, ["commands", "install", "--pi", "--overwrite"])

    assert result.exit_code == 0
    assert "Installed assess-setup/SKILL.md" in result.output


def test_commands_install_pi_local_mutual_exclusion(tmp_path):
    """--pi and --local are mutually exclusive."""
    result = runner.invoke(app, ["commands", "install", "--pi", "--local"])
    assert result.exit_code == 1
    assert "--local is for Claude Code" in result.output


def test_commands_install_global_without_pi(tmp_path):
    """--global without --pi is an error."""
    result = runner.invoke(app, ["commands", "install", "--global"])
    assert result.exit_code == 1
    assert "--global is only valid with --pi" in result.output
```

## Summary of Changes

| File | Change |
|---|---|
| `.pi/skills/*/SKILL.md` (×11) | **New** — Pi-format skill files |
| `src/dauber/cli/commands.py` | Add `--pi` and `--global` flags, `_install_pi_skills()`, refactor existing into `_install_claude_commands()` |
| `tests/cli/test_commands.py` | 6 new tests for Pi install paths |
| `specs/planning.md` | Add v0.1.7 milestone |
| `specs/progress.md` | Track Pi skills feature |

## Open Questions

1. **Should `--pi` also support `--local` semantics for a non-cwd path?**
   Probably not for v0.1.7. Pi discovers skills from `.pi/skills/` in
   the project tree, so cwd is the natural target.

2. **Should we add a `--list` subcommand to show available skills?**
   Nice to have but not blocking. Could be `dauber commands list` showing
   both Claude and Pi formats with their install status.

3. **Should the Pi skill descriptions be enhanced beyond the Claude
   versions?** Pi's descriptions drive agent auto-discovery, so richer
   descriptions (with "Use when..." guidance) are valuable. The initial
   conversion can copy descriptions as-is and iterate.
