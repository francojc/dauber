# dauber

[![CI](https://github.com/francojc/dauber/actions/workflows/ci.yml/badge.svg)](https://github.com/francojc/dauber/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dauber)](https://pypi.org/project/dauber/)
[![Python versions](https://img.shields.io/pypi/pyversions/dauber)](https://pypi.org/project/dauber/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A command-line interface for the Canvas LMS API. Manage courses,
assignments, grading, and content from the terminal.

dauber also serves as a backend for
[Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill
commands, enabling AI-assisted grading workflows via `--format json`.

## Installation

**Requirements:** Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/francojc/dauber.git
cd dauber
```

Install `dauber` to `~/.local/bin/` so it's available system-wide:

```sh
uv tool install -e .
```

The `-e` (editable) flag means changes to the source take effect
immediately without reinstalling. To update after a `git pull`:

```sh
uv tool install -e . --force
```

If you prefer to run from the project directory without a global
install, use `uv run dauber` instead (after `uv sync`).

Set two environment variables for Canvas API access:

```sh
export CANVAS_API_KEY="your-canvas-api-token"
export CANVAS_BASE_URL="https://your-institution.instructure.com"
```

The `/api/v1` path is appended automatically. Generate an API token
from your Canvas account settings under "Approved Integrations."

Verify the install and connection:

```sh
dauber --version
dauber --test
```

## Quick start

```sh
# List your courses
dauber courses list

# List assignments for a course (accepts codes or numeric IDs)
dauber assignments list --course IS505

# View submissions for an assignment
dauber grading submissions --course IS505 42

# Set up course-level config
dauber config init
```

All commands accept `--format` (`-f`) with four output modes:

| Mode    | Use case                          |
|---------|-----------------------------------|
| `table` | Aligned columns (default)         |
| `json`  | Machine-readable, for piping      |
| `plain` | Simple key-value pairs            |
| `csv`   | Header + rows, pipe to file/tools |

## Configuration

dauber uses two TOML config files. Local values override global.

**Global** (instructor defaults shared across courses):

```
$XDG_CONFIG_HOME/dauber/config.toml    # default: ~/.config/dauber/config.toml
```

Set up interactively or write defaults without prompting:

```sh
dauber config global              # interactive prompts
dauber config global --defaults   # write starter config
```

**Local** (per-course settings in the repo root):

```
./dauber/config.toml
```

```sh
dauber config init                # interactive prompts, pre-fills from global
```

**View merged config:**

```sh
dauber config show                # shows each value with [global] or [local] source
```

## Commands

### courses

```
dauber courses list [--concluded]
dauber courses show [--course COURSE]
dauber courses enrollments [--course COURSE]
```

List, inspect, and view enrollments for your courses. The `--course`
option accepts course codes (e.g., `IS505`) or numeric Canvas IDs.
When omitted, falls back to `canvas_course_id` in your config file.

### assignments

```
dauber assignments list [--course COURSE]
dauber assignments show [--course COURSE] <assignment-id>
dauber assignments create [--course COURSE] <name> [--points N] [--due ISO] [--publish]
dauber assignments update [--course COURSE] <assignment-id> [--name ...] [--points N]
```

Create, update, list, and inspect assignments. For interactive guided
creation with defaults, validation, and rubric handoff, see
`/assignments:create`.

### rubrics

```
dauber rubrics list [--course COURSE]
dauber rubrics show [--course COURSE] <rubric-id>
dauber rubrics create [--course COURSE] --file <path>
dauber rubrics import [--course COURSE] --csv <path>
dauber rubrics attach [--course COURSE] <rubric-id> <assignment-id> [--use-for-grading]
```

List, inspect, create, and attach rubrics. `show` looks up a rubric by
its direct ID. `create` reads a JSON file with `title` and `criteria`
fields. `import` reads a Canvas-format CSV file (the wide-format
template exported from Canvas). `attach` associates an existing rubric
with an assignment; pass `--use-for-grading` to map rubric scores to
the assignment grade. For guided format selection (CSV/JSON/interactive)
and automatic create → attach sequencing, see `/rubrics:create`.

Example JSON for `create`:

```json
{
  "title": "Essay Rubric",
  "criteria": [
    {
      "description": "Thesis",
      "points": 25,
      "ratings": [
        {"description": "Excellent", "points": 25},
        {"description": "Needs work", "points": 10},
        {"description": "Missing", "points": 0}
      ]
    }
  ]
}
```

### grading

```
dauber grading submissions [--course COURSE] <assignment-id> [--anonymize]
dauber grading show [--course COURSE] <assignment-id> <user-id> [--anonymize]
dauber grading submit [--course COURSE] <assignment-id> <user-id> <grade> [--comment ...]
dauber grading submit-rubric [--course COURSE] <assignment-id> <user-id> <file> [--comment ...]
```

View submissions, inspect individual student work, and post grades.
`submit-rubric` reads rubric criterion scores from a JSON file. For
distribution stats and missing-submission flags across a cohort, see
`/grading:overview`.

### assess

```
dauber assess setup [--course COURSE] <assignment-id> [--exclude-graded] [--anonymize]
dauber assess load <file>
dauber assess update <file> <user-id> [--rubric-json ...] [--approved]
dauber assess submit <file> [--course COURSE] <assignment-id> [--confirm]
```

Full rubric-based assessment workflow: fetch assignment data into a
local JSON file, update individual scores, and submit approved grades
back to Canvas. Submit runs in dry-run mode by default; pass
`--confirm` to post grades. These commands are building blocks; for
the full AI grading pipeline use `/assess:setup` → `/assess:ai-pass`
→ `/assess:refine` → `/assess:submit`.

### modules

```
dauber modules list [--course COURSE] [--items] [--search ...]
dauber modules show [--course COURSE] <module-id>
dauber modules create [--course COURSE] <name> [--position N] [--publish]
dauber modules update [--course COURSE] <module-id> [--name ...] [--publish/--unpublish]
dauber modules delete [--course COURSE] <module-id>
```

### pages

```
dauber pages list [--course COURSE] [--search ...] [--sort title|created_at|updated_at]
dauber pages show [--course COURSE] <page-url>
dauber pages create [--course COURSE] <title> [--body ...] [--publish]
dauber pages update [--course COURSE] <page-url> [--title ...] [--body ...]
dauber pages delete [--course COURSE] <page-url>
```

Pages are identified by their URL slug (e.g., `syllabus-spring-2026`).
To publish a local Markdown file with automatic HTML conversion and
module placement, see `/content:publish`.

### discussions

```
dauber discussions list [--course COURSE] [--announcements]
dauber discussions show [--course COURSE] <topic-id>
dauber discussions create [--course COURSE] <title> [--message ...] [--announcement] [--publish]
dauber discussions update [--course COURSE] <topic-id> [--title ...] [--message ...]
```

Pass `--announcements` to list only announcements. Use `--announcement`
when creating to post an announcement rather than a discussion topic.
For AI-drafted announcement text with tone matching and an approval
loop, see `/discuss:announce`.

### config

```
dauber config init [--base .]
dauber config global [--defaults]
dauber config show
```

See [Configuration](#configuration) above for details.

### commands

```
dauber commands install [--overwrite] [--local]
dauber commands install --pi [--overwrite]
dauber commands install --pi --global [--overwrite]
```

Installs bundled skill commands for either Claude Code or Pi.

| Invocation | Target |
|---|---|
| `dauber commands install` | `~/.claude/commands/` (Claude, global) |
| `dauber commands install --local` | `./.claude/commands/` (Claude, project) |
| `dauber commands install --pi` | `./.pi/skills/` (Pi, project) |
| `dauber commands install --pi --global` | `~/.pi/agent/skills/` (Pi, global) |

Pass `--overwrite` to replace existing files. See
[Skill commands](#skill-commands) below.

### Global options

```
dauber --version             # show version
dauber --test                # test Canvas API connection
dauber --config              # show API URL and token (masked)
dauber --format json <cmd>   # JSON output for any command
dauber --install-completion  # install shell tab-completion
```

## Anonymizing student data

Commands that return student information support `--anonymize` to
strip personally identifiable information. When enabled, `user_name`
and `user_email` are replaced with empty strings. The numeric
`user_id` is retained for grade submission round-tripping.

Affected commands: `assess setup`, `grading submissions`, `grading show`.

```sh
dauber assess setup --course IS505 42 --anonymize --format json
dauber grading submissions --course IS505 42 --anonymize
```

This is opt-in. Without `--anonymize`, output includes full names and
emails as returned by the Canvas API.

## Skill commands

Some dauber commands are self-contained: you know the inputs, you run
the command, you get the result. `courses list`, `assignments show`,
`modules create`, and most read/write operations fall into this
category — no skill needed.

Other commands are most useful as building blocks. The skill commands
below orchestrate sequences of dauber calls, inject AI reasoning
(drafting, scoring, normalizing), and manage state across steps.
`--format json` is what makes this work: skills parse structured
output from one command and feed it into the next.

Install all skills with:

```sh
# Claude Code (global)
dauber commands install

# Pi Agent Skills (project-local)
dauber commands install --pi
```

For Claude Code, this copies Markdown command files into
`~/.claude/commands/`. Once installed, invoke them from Claude Code
(e.g., `/assess:setup`, `/course:overview`).

For Pi, this copies `SKILL.md` files into `./.pi/skills/`. Once
installed, the skills are available to the Pi coding agent from that
project tree. Use `--pi --global` to install to `~/.pi/agent/skills/`
for user-wide availability.

| Skill | CLI commands used | What it does |
|---|---|---|
| `/assess:setup` → `/assess:ai-pass` → `/assess:refine` → `/assess:submit` | `assess setup/load/update/submit` | Full AI grading pipeline: fetch submissions → AI-evaluate against rubric → normalize scores → post to Canvas |
| `/assignments:create` | `assignments create` | Interactive parameter collection with defaults, validation, and rubric handoff |
| `/rubrics:create` | `rubrics create/import/attach` | Guides format choice (CSV/JSON/interactive), sequences create → attach |
| `/discuss:announce` | `discussions create --announcement` | AI-drafted announcement text with tone/formality matching and approval loop |
| `/content:publish` | `pages create` | Markdown → HTML conversion, existing-page detection, module placement |
| `/grading:overview` | `grading submissions` | Distribution stats (mean, median, quartiles) and missing-submission flags across the cohort |
| `/course:overview` | `courses show`, `assignments list`, `modules list` | Unified dashboard: enrollment, upcoming deadlines, content counts |
| `/course:setup` | `--test`, `courses show/enrollments`, `config init` | First-time course initialization with guided config creation |

### Writing custom skills

Any script or Claude Code skill can call dauber. A minimal example
that lists ungraded submissions:

```sh
dauber grading submissions --course IS505 42 --format json \
  | jq '[.[] | select(.grade == null)]'
```

Skills that need course context (feedback language, formality, etc.)
read from `./dauber/config.toml`. Run `dauber config init` to set it up.

## Development

```sh
uv sync                         # install dependencies
uv run dauber --help             # verify install
uv run pytest tests/            # run tests
uv run ruff check src/ tests/   # lint
uv run ruff format src/ tests/  # format
```

### Architecture

```
CLI (Typer) -> services (async) -> core (HTTP client, config, cache)
```

- **Core** -- `CanvasClient` (httpx async, pagination, 429 retry),
  `Config` (pydantic-settings), `CourseCache` (bidirectional code/ID
  mapping), config file helpers (TOML).
- **Services** -- Async functions per Canvas entity. Accept a
  `CanvasClient`, return dicts/lists, raise `CanvasError` on failure.
- **CLI** -- Typer commands that bridge async via decorator, format
  output through `format_output()`, and exit with appropriate codes.

### Tests

Tests are organized in two layers:

- `tests/services/` -- mock at the `CanvasClient` transport level
- `tests/cli/` -- mock at the service function level, use
  `typer.testing.CliRunner`

## License

See [LICENSE](LICENSE).
