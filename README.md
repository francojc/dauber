# dauber

[![CI](https://github.com/francojc/dauber/actions/workflows/ci.yml/badge.svg)](https://github.com/francojc/dauber/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dauber)](https://pypi.org/project/dauber/)
[![Python versions](https://img.shields.io/pypi/pyversions/dauber)](https://pypi.org/project/dauber/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Canvas LMS from your terminal. `dauber` lets instructors list courses, create assignments, manage pages and modules, inspect submissions, post grades, work with rubrics, and run AI-assisted grading workflows without clicking through Canvas.

You do not need to be a programmer to use it. You need a terminal, Python, and a Canvas API token.

## Contents

- [Installation](#installation)
- [First-time setup](#first-time-setup)
- [Quick start](#quick-start)
- [Global flags](#global-flags)
- [Commands](#commands)
  - [courses](#dauber-courses)
  - [assignments](#dauber-assignments)
  - [rubrics](#dauber-rubrics)
  - [grading](#dauber-grading)
  - [assess](#dauber-assess)
  - [modules](#dauber-modules)
  - [pages](#dauber-pages)
  - [discussions](#dauber-discussions)
  - [config](#dauber-config)
  - [commands](#dauber-commands)
- [Configuration](#configuration)
- [Output formats](#output-formats)
- [Anonymizing student data](#anonymizing-student-data)
- [AI skill commands](#ai-skill-commands)
- [Shell completions](#shell-completions)
- [Development](#development)

---

## Installation

### PyPI with uv, recommended

[`uv`](https://docs.astral.sh/uv/) is a fast Python package installer. If you already have `uv`, install `dauber` as a command-line tool:

```bash
uv tool install dauber
dauber --version
```

If your shell cannot find `dauber`, run:

```bash
uv tool update-shell
```

Then restart your terminal.

### Run once with uvx

Use `uvx` when you want to try `dauber` without installing it permanently:

```bash
uvx dauber --version
uvx dauber --help
```

You can run any command this way:

```bash
uvx dauber courses list
```

For regular use, `uv tool install dauber` is nicer because you can type `dauber` directly.

### PyPI with pip

If you prefer standard Python tooling:

```bash
pip install dauber
dauber --version
```

Depending on your Python setup, you may need:

```bash
python -m pip install dauber
dauber --version
```

If `dauber` is installed but not found, your Python scripts directory is probably not on your `PATH`.

### From source

Use this if you want latest code from GitHub or plan to edit `dauber` itself:

```bash
git clone https://github.com/francojc/dauber.git
cd dauber
uv tool install .
dauber --version
```

For editable development install, where local code changes take effect immediately:

```bash
uv tool install -e .
```

### Requirements

- Python 3.11 or newer
- Canvas account with permission to use Canvas API
- Canvas API token
- Canvas base URL, usually something like `https://your-institution.instructure.com`

---

## First-time setup

### 1. Get Canvas API token

In Canvas, open:

```text
Account > Settings > Approved Integrations > New Access Token
```

Create a token, copy it, and keep it private. Treat it like a password.

### 2. Set environment variables

`dauber` reads Canvas credentials from environment variables.

```bash
export CANVAS_API_KEY="your-canvas-api-token"
export CANVAS_BASE_URL="https://your-institution.instructure.com"
```

Do not include `/api/v1`; `dauber` adds that automatically.

To make these available every time you open your terminal, add those two lines to your shell config, such as `~/.zshrc` or `~/.bashrc`.

### 3. Test connection

```bash
dauber --test
```

If connection works, try:

```bash
dauber courses list
```

### 4. Optional course config

Inside a course project folder, run:

```bash
dauber config init
```

This creates `./dauber/config.toml`, so you do not need to pass `--course` on every command.

---

## Quick start

```bash
# Show help
dauber --help

# List your Canvas courses
dauber courses list

# Show one course, using course code or Canvas numeric ID
dauber courses show --course IS505

# List assignments in a course
dauber assignments list --course IS505

# Show assignment details
dauber assignments show --course IS505 42

# View submissions
dauber grading submissions --course IS505 42

# View submissions without student names/emails
dauber grading submissions --course IS505 42 --anonymize

# Save machine-readable JSON
dauber grading submissions --course IS505 42 --format json > submissions.json
```

`IS505` is example course code. `42` is example Canvas assignment ID.

---

## Global flags

These flags work from top-level `dauber` command.

| Flag | Short | Description |
|---|---|---|
| `--help` | | Show help |
| `--version` | `-V` | Print installed version |
| `--format <mode>` | `-f` | Output format: `table`, `json`, `plain`, or `csv` |
| `--test` | | Test Canvas API connection |
| `--config` | | Show current API URL and masked token |
| `--install-completion` | | Install shell tab-completion |
| `--show-completion` | | Print completion script |

---

## Commands

### `dauber courses`

List courses, inspect one course, and view enrollments.

```text
dauber courses list [--concluded]
dauber courses show [--course COURSE]
dauber courses enrollments [--course COURSE]
```

Examples:

```bash
dauber courses list
dauber courses list --concluded
dauber courses show --course IS505
dauber courses enrollments --course IS505
```

`--course` accepts course code, such as `IS505`, or numeric Canvas course ID.

---

### `dauber assignments`

Create, update, list, and inspect assignments.

```text
dauber assignments list [--course COURSE]
dauber assignments show [--course COURSE] ASSIGNMENT_ID
dauber assignments create [--course COURSE] NAME [--points N] [--due ISO] [--publish]
dauber assignments update [--course COURSE] ASSIGNMENT_ID [--name NAME] [--points N]
```

Examples:

```bash
dauber assignments list --course IS505
dauber assignments show --course IS505 42
dauber assignments create --course IS505 "Reflection 1" --points 10 --publish
dauber assignments update --course IS505 42 --points 15
```

For guided AI-assisted assignment creation, install skill commands and use `/assignments:create`.

---

### `dauber rubrics`

List, inspect, create, import, and attach rubrics.

```text
dauber rubrics list [--course COURSE]
dauber rubrics show [--course COURSE] RUBRIC_ID
dauber rubrics create [--course COURSE] --file PATH
dauber rubrics import [--course COURSE] --csv PATH
dauber rubrics attach [--course COURSE] RUBRIC_ID ASSIGNMENT_ID [--use-for-grading]
```

Examples:

```bash
dauber rubrics list --course IS505
dauber rubrics show --course IS505 123
dauber rubrics create --course IS505 --file rubric.json
dauber rubrics import --course IS505 --csv rubric.csv
dauber rubrics attach --course IS505 123 42 --use-for-grading
```

Minimal rubric JSON:

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

---

### `dauber grading`

View submissions, inspect individual student work, and post grades.

```text
dauber grading submissions [--course COURSE] ASSIGNMENT_ID [--anonymize]
dauber grading show [--course COURSE] ASSIGNMENT_ID USER_ID [--anonymize]
dauber grading submit [--course COURSE] ASSIGNMENT_ID USER_ID GRADE [--comment TEXT]
dauber grading submit-rubric [--course COURSE] ASSIGNMENT_ID USER_ID FILE [--comment TEXT]
```

Examples:

```bash
dauber grading submissions --course IS505 42
dauber grading submissions --course IS505 42 --anonymize
dauber grading show --course IS505 42 1001
dauber grading submit --course IS505 42 1001 9.5 --comment "Nice work."
dauber grading submit-rubric --course IS505 42 1001 assessment.json
```

---

### `dauber assess`

Rubric-based assessment workflow. Useful for staged grading and AI-assisted grading.

```text
dauber assess setup [--course COURSE] ASSIGNMENT_ID [--exclude-graded] [--anonymize]
dauber assess load FILE
dauber assess update FILE USER_ID [--rubric-json JSON] [--approved]
dauber assess submit FILE [--course COURSE] ASSIGNMENT_ID [--confirm]
```

Typical flow:

```bash
dauber assess setup --course IS505 42 --anonymize --format json > assess.json
dauber assess load assess.json
dauber assess submit assess.json --course IS505 42        # dry run
dauber assess submit assess.json --course IS505 42 --confirm
```

`submit` runs dry-run by default. It only posts grades when `--confirm` is present.

---

### `dauber modules`

Manage Canvas modules and module items.

```text
dauber modules list [--course COURSE] [--items] [--search TEXT]
dauber modules show [--course COURSE] MODULE_ID
dauber modules create [--course COURSE] NAME [--position N] [--publish]
dauber modules update [--course COURSE] MODULE_ID [--name NAME] [--publish/--unpublish]
dauber modules delete [--course COURSE] MODULE_ID

dauber modules items list [--course COURSE] MODULE_ID
dauber modules items show [--course COURSE] MODULE_ID ITEM_ID
dauber modules items create [--course COURSE] MODULE_ID TITLE --type TYPE [--content-id ID] [--page-url SLUG] [--url URL]
dauber modules items update [--course COURSE] MODULE_ID ITEM_ID [--title TITLE] [--position N]
dauber modules items delete [--course COURSE] MODULE_ID ITEM_ID
```

Module item types:

| Type | Needed option |
|---|---|
| `Page` | `--page-url` |
| `Assignment` | `--content-id` |
| `Discussion` | `--content-id` |
| `File` | `--content-id` |
| `ExternalUrl` | `--url` |
| `SubHeader` | none |

For an `ExternalUrl` item, retain familiar `--url`; dauber sends Canvas API field `external_url`.

Example:

```bash
dauber modules items create --course IS505 2 "Plan del día" --type ExternalUrl --url https://example.org/plan.html
```

---

### `dauber pages`

Create, update, list, inspect, and delete Canvas pages.

```text
dauber pages list [--course COURSE] [--search TEXT] [--sort title|created_at|updated_at]
dauber pages show [--course COURSE] PAGE_URL
dauber pages create [--course COURSE] TITLE [--body TEXT] [--publish]
dauber pages update [--course COURSE] PAGE_URL [--title TITLE] [--body TEXT]
dauber pages delete [--course COURSE] PAGE_URL
```

Example:

```bash
dauber pages create --course IS505 "Week 1 Overview" --body "Welcome to week 1." --publish
```

Canvas pages use URL slugs, such as `week-1-overview`.

---

### `dauber discussions`

Manage Canvas discussions and announcements.

```text
dauber discussions list [--course COURSE] [--announcements]
dauber discussions show [--course COURSE] TOPIC_ID
dauber discussions create [--course COURSE] TITLE [--message TEXT] [--announcement] [--publish]
dauber discussions update [--course COURSE] TOPIC_ID [--title TITLE] [--message TEXT]
```

Examples:

```bash
dauber discussions list --course IS505
dauber discussions list --course IS505 --announcements
dauber discussions create --course IS505 "Reminder" --message "Project due Friday." --announcement --publish
```

---

### `dauber config`

Manage global and course-local config files.

```text
dauber config init [--base PATH]
dauber config global [--defaults]
dauber config show
```

Examples:

```bash
dauber config global              # interactive global setup
dauber config global --defaults   # write starter global config
dauber config init                # create local ./dauber/config.toml
dauber config show                # show merged config and sources
```

---

### `dauber commands`

Install bundled AI skill commands for Claude Code or Pi.

```text
dauber commands install [--overwrite] [--local]
dauber commands install --pi [--overwrite]
dauber commands install --pi --global [--overwrite]
```

| Invocation | Target |
|---|---|
| `dauber commands install` | `~/.claude/commands/` |
| `dauber commands install --local` | `./.claude/commands/` |
| `dauber commands install --pi` | `./.pi/skills/` |
| `dauber commands install --pi --global` | `~/.pi/agent/skills/` |

Use `--overwrite` to replace existing files.

---

## Configuration

`dauber` uses environment variables for Canvas credentials and TOML files for course defaults.

### Required environment variables

| Variable | Description |
|---|---|
| `CANVAS_API_KEY` | Canvas API token |
| `CANVAS_BASE_URL` | Institution Canvas URL, without `/api/v1` |

Example:

```bash
export CANVAS_API_KEY="your-canvas-api-token"
export CANVAS_BASE_URL="https://your-institution.instructure.com"
```

### Config files

Local config overrides global config.

| Scope | Path | Purpose |
|---|---|---|
| Global | `~/.config/dauber/config.toml` | Instructor-wide defaults |
| Local | `./dauber/config.toml` | Course/project-specific defaults |

Create them with:

```bash
dauber config global
dauber config init
```

Show active settings:

```bash
dauber config show
```

---

## Output formats

Most commands support `--format` / `-f`.

| Format | Best for |
|---|---|
| `table` | Reading in terminal, default |
| `json` | Saving, piping to tools, AI workflows |
| `plain` | Simple text output |
| `csv` | Spreadsheets and data tools |

Examples:

```bash
dauber courses list --format table
dauber assignments list --course IS505 --format json
dauber grading submissions --course IS505 42 --format csv > submissions.csv
```

---

## Anonymizing student data

Use `--anonymize` when output may be shared with an AI tool or saved outside Canvas.

```bash
dauber assess setup --course IS505 42 --anonymize --format json
dauber grading submissions --course IS505 42 --anonymize
dauber grading show --course IS505 42 1001 --anonymize
```

With `--anonymize`, `user_name` and `user_email` are removed. `user_id` remains because Canvas needs it to submit grades back to correct student.

Affected commands:

- `assess setup`
- `grading submissions`
- `grading show`

---

## AI skill commands

Some workflows need multiple `dauber` commands plus judgment, drafting, or normalization. `dauber commands install` copies ready-made skills for Claude Code or Pi.

Install for Claude Code:

```bash
dauber commands install
```

Install for Pi in current project:

```bash
dauber commands install --pi
```

Skills included:

| Skill | What it does |
|---|---|
| `/assess:setup` | Fetch submissions and rubric into local assessment file |
| `/assess:ai-pass` | Draft AI rubric assessments |
| `/assess:refine` | Normalize scores across cohort |
| `/assess:submit` | Submit approved grades to Canvas |
| `/assignments:create` | Guided assignment creation |
| `/rubrics:create` | Guided rubric creation/import and attachment |
| `/discuss:announce` | Draft and post announcement |
| `/content:publish` | Publish Markdown/HTML as Canvas page |
| `/grading:overview` | Analyze grade distribution and missing submissions |
| `/course:overview` | Show course status dashboard |
| `/course:setup` | First-time course setup |

---

## Shell completions

Install tab-completion for your current shell:

```bash
dauber --install-completion
```

Then restart your terminal.

To inspect completion script instead:

```bash
dauber --show-completion
```

---

## Development

```bash
uv sync                         # install dependencies
uv run dauber --help             # run from source
uv run pytest tests/             # run tests
uv run ruff check src/ tests/    # lint
uv run ruff format src/ tests/   # format
```

With coverage:

```bash
uv run python -m pytest --cov=dauber --cov-report=term-missing tests/
```

Integration tests require live Canvas sandbox credentials. They create and delete temporary unpublished module content, so use a dedicated sandbox course:

```bash
CANVAS_SANDBOX_COURSE_ID=123 \
CANVAS_API_KEY=... \
CANVAS_BASE_URL=https://your-institution.instructure.com \
uv run python -m pytest tests/integration/ -m integration
```

### Architecture

```text
CLI (Typer) -> services (async) -> core (HTTP client, config, cache)
```

- `src/dauber/core/`: HTTP client, settings, Canvas cache, config files
- `src/dauber/services/`: async Canvas business logic
- `src/dauber/cli/`: Typer commands, async bridge, output formatting
- `tests/services/`: service tests, mocked at Canvas client layer
- `tests/cli/`: CLI tests, mocked at service layer

## License

See [LICENSE](LICENSE).
