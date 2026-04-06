# Development Project Planning

**Project:** dauber
**Status:** v0.1.7 complete
**Last Updated:** 2026-03-24

## Project Overview

### Software Description

- **Application Type:** CLI tool
- **Target Platform:** macOS / Linux (cross-platform Python)
- **Primary Language:** Python 3.11+
- **Key Libraries/Frameworks:** Typer, httpx, pydantic, pydantic-settings,
  rich, python-dateutil, tomli-w

### Problem Statement

- Canvas LMS operations (grading, course management, assignments) lack
  a terminal-native interface for scripting and automation.
- The canvas-mcp project proves the business logic works but couples it
  to FastMCP, limiting use outside MCP-aware clients.
- Instructors and Claude Code skills need a composable CLI that pipes
  JSON, runs in scripts, and works from any terminal.

### Goals and Non-Goals

#### Goals

- [x] Full Canvas API coverage for common instructor workflows
      (courses, assignments, rubrics, grading, modules, discussions)
- [x] Four output formats: table (human), JSON (machine), plain (simple),
      CSV (pipeable)
- [x] Scriptable and composable -- exit codes, stderr for errors,
      stdout for data
- [x] Usable as a backend for Claude Code assess/* skills via
      `dauber <cmd> --format json`
- [ ] Native support for Pi coding agent via Agent Skills format
      (`.pi/skills/`) alongside the existing Claude Code format

#### Non-Goals

- No GUI or TUI beyond formatted terminal output
- No MCP integration -- dauber is a standalone CLI
- No audit logging or sandbox config (canvas-mcp concerns)
- No runtime dependency on canvas-mcp (reference only)

## Architecture and Design

### High-Level Architecture

- **Pattern:** CLI pipeline
- **Data Flow:** `Typer CLI -> services (async) -> core (HTTP, config, cache)`
- **Key Components:**
  - Core: `CanvasClient` (httpx), `Config` (pydantic-settings),
    `CourseCache` (code/ID mapping)
  - Services: async functions per Canvas entity, raise `CanvasError`
  - CLI: Typer commands that bridge async, format output, handle errors

### External Dependencies

- **APIs and Services:** Canvas LMS REST API
- **Data Sources:** Canvas API via httpx, local course cache
- **Build Tools:** uv (package manager), hatchling (build backend),
  ruff (linting/formatting)

### Technical Constraints

- Python 3.11+ required (asyncio improvements, ExceptionGroup)
- Canvas API rate limits: retry with backoff on HTTP 429
- Canvas API token required via environment variable
- Canvas rubric grading uses bracket-notation form data encoding

## Timeline and Milestones

### Phase 0: Scaffolding (COMPLETE)

- [x] Create pyproject.toml with hatchling build and entry point
- [x] Set up src/dauber/ directory structure (core, services, cli)
- [x] Create Typer app skeleton with --version, --test, --config
- [x] Implement async bridging and output formatting
- [x] Verify `uv sync && uv run dauber --help`

### Phase 1: Core Layer (COMPLETE)

- [x] Implement Config (pydantic-settings, env var loading)
- [x] Implement CanvasClient (httpx, pagination, retry on 429)
- [x] Implement CourseCache (bidirectional code/ID mapping)
- [x] Create CLI context (lazy init of client, cache, config)
- [x] Unit tests for core modules (24 tests)

### Phase 2: Courses (Proving Ground) (COMPLETE)

- [x] Implement courses service (list, details, enrollments)
- [x] Implement courses CLI commands
- [x] Service tests with mocked client
- [x] CLI tests with mocked services

### Phase 3: Assignments + Rubrics + Grading (COMPLETE)

- [x] Assignments service (list, get, create, update) with HTML stripping
- [x] Assignments CLI (list, show, create, update)
- [x] Rubrics service (list, get, create, parse_rubric_csv, attach_rubric)
- [x] Rubrics CLI (`dauber rubrics list|show|create|import|attach`)
- [x] Grading service (submissions, get, submit grade, submit rubric grade)
- [x] Grading CLI (submissions, show, submit, submit-rubric)
- [x] Tests: 14 assignments svc, 8 rubrics svc, 10 grading svc,
  13 assignments CLI, 10 grading CLI (99 total)

### Phase 4: Assessment Workflow (COMPLETE)

- [x] Assessment service: fetch_assignment_with_rubric,
  fetch_submissions_with_content, build_assessment_structure,
  load/save/update_assessment, get_assessment_stats,
  submit_assessments
- [x] Assessment CLI: `dauber assess setup|load|update|submit`
- [x] Setup builds full assessment JSON (metadata + rubric + submissions)
- [x] Submit uses dry-run by default, requires --confirm
- [x] Tests: 22 service, 12 CLI (133 total)

### Phase 5: Modules, Pages, Discussions (COMPLETE)

- [x] Modules service (list, get, create, update, delete) and CLI
- [x] Pages service (list, get, create, update, delete) and CLI
  (slug-based identification, HTML stripping)
- [x] Discussions service (list, get, create, update) and CLI
  (announcements, HTML stripping)
- [x] All three sub-apps registered in app.py
- [x] Tests: 14 modules svc, 11 modules CLI, 15 pages svc,
  12 pages CLI, 15 discussions svc, 12 discussions CLI (210 total)
- Student commands deferred (not needed for instructor workflows)

### Phase 6: Polish (COMPLETE)

- [x] Wire --test and --config callbacks (done in Phase 1)
- [x] Migrate assess/* skill commands from MCP to dauber CLI
- [x] Add `dauber commands install` CLI for distributing skill commands
- [x] `dauber config` sub-app (init, global, show)
- [x] Live smoke test against Canvas API (all 17 commands passed)
- [x] Bug fix: --test event loop crash
- [x] Shell completion support (Typer built-in --install-completion)
- [x] README with full CLI reference and "Extending with AI" section
- [x] Final documentation pass

### v0.1.2: XDG Configuration (COMPLETE)

- [x] Global config respects `$XDG_CONFIG_HOME` (default `~/.config`)
- [x] Local config moved from `.claude/course_parameters.yaml` to
      `./dauber/config.toml` (TOML, not YAML)
- [x] `--defaults` flag on `dauber config global` for non-interactive setup
- [x] `dauber commands install` covers all 6 command groups
- [x] pyyaml dependency removed

### v0.1.3: Config-Driven Defaults (COMPLETE)

- [x] `course` argument optional on all commands — falls back to
      `canvas_course_id` in local/global config
- [x] `resolve_course()` and `resolve_assess_defaults()` helpers in
      `cli/_config_defaults.py`
- [x] `assess setup` options read defaults from config
- [x] `grading submissions` and `grading show` read `anonymize` from
      config
- [x] Tests for config-resolution helpers (254 tests total)

### v0.1.4: Course Option Fix (COMPLETE)

- [x] Changed `course` from positional `Argument` to named
      `--course`/`-c` `Option` across all 29 commands in 7 CLI modules
- [x] Fixes greedy positional parsing where required args were
      swallowed by optional `course` (Issue #6)
- [x] Updated all CLI tests to use `--course` flag

### v0.1.6: Rubrics Subcommand (COMPLETE)

- [x] `dauber rubrics` sub-app replacing `assignments rubrics|rubric`
- [x] `rubrics list` — list all course rubrics
- [x] `rubrics show <id>` — show rubric by direct ID (no assignment needed)
- [x] `rubrics create --file <path>` — create rubric from JSON file
- [x] `rubrics import --csv <path>` — create rubric from Canvas wide-format CSV
- [x] `rubrics attach <rubric_id> <assignment_id>` — associate rubric with
      assignment via `PUT` with `rubric_association` body
- [x] `parse_rubric_csv` service: positional CSV parsing, validates columns
      and numeric points, handles variable-length rating triplets
- [x] `attach_rubric` service: wraps Canvas PUT endpoint, raises CanvasError
- [x] `.claude/commands/rubrics/create.md` skill: CSV/JSON/guided paths,
      capture rubric ID, offer attach, suggest `/assess:setup`
- [x] `assignments/create.md` Step 5 simplified: hands off to `/rubrics:create`
- [x] DOCX/PDF attachment text extraction in assessment service:
      `_extract_attachment_text()` downloads and parses `.docx`/`.pdf`
      attachments; submission fetch includes `attachments` param so
      file-upload submissions appear in assessment JSON
- [x] `python-docx` and `pypdf` added as runtime dependencies
- [x] Fix: `rubrics` added to `_COMMAND_GROUPS` so `dauber commands install`
      copies `rubrics/create.md` to the target commands directory
- [x] 288 tests total, ruff clean

### v0.1.7: Pi Agent Skills Support (COMPLETE)

Add native support for the Pi coding agent harness alongside existing
Claude Code slash-command support. Ship both formats in the repo
(Option A) and extend `dauber commands install` with a `--pi` flag.

- [x] Add `.pi/skills/` directory with pre-converted `SKILL.md` files
      for all 11 commands (assess-setup, assess-ai-pass, assess-refine,
      assess-submit, assignments-create, content-publish, course-overview,
      course-setup, discuss-announce, grading-overview, rubrics-create)
- [x] Extend `cli/commands.py`: add `--pi` and `--global` flags,
      `_install_pi_skills()` helper, refactor existing Claude path into
      `_install_claude_commands()` for symmetry
- [x] `--pi` defaults to local install (`./.pi/skills/` in cwd);
      `--global` installs to `~/.pi/agent/skills/`
- [x] Mutual-exclusion validation: `--pi` and `--local` are incompatible;
      `--global` is only valid with `--pi`
- [x] 6 new tests in `tests/cli/test_commands.py` covering local, global,
      skip-existing, overwrite, and both validation errors
- [x] 294 tests total, ruff clean

#### CLI interface (new behaviour)

```
dauber commands install              # Claude → ~/.claude/commands/ (unchanged)
dauber commands install --local      # Claude → ./.claude/commands/ (unchanged)
dauber commands install --pi         # Pi     → ./.pi/skills/       (new)
dauber commands install --pi --global# Pi     → ~/.pi/agent/skills/ (new)
```

#### Pi skill naming convention

Each Claude `{group}/{file}.md` maps to a `{group}-{file}/SKILL.md`
directory with a minimal frontmatter header (`name`, `description`).
Body content is copied verbatim — the instructions call `dauber` CLI
commands which work identically under either harness.

### v0.1.5: Output and Usability Improvements (COMPLETE)

- [x] Add `--format csv` output format for pipeable tabular data
      (Issue #8). Header row + data rows via `csv.writer` to stdout.
      262 tests passing.
- [x] Change `grading submit-rubric` `assessment_json` argument from
      inline JSON text to a file path (Issue #9). Reads and parses
      JSON from the specified file with file-not-found and invalid-JSON
      error handling.

## Resources and Requirements

### Development Environment

- Python 3.11 via nix flake
- uv for package management and virtual environment
- ruff for linting and formatting
- direnv for automatic environment activation

### Infrastructure

- Local CLI tool -- no hosting required
- No CI/CD initially (single developer)
- Distribution via `uv pip install -e .`

### Collaboration

- Solo development with Claude Code assistance
- Feature branches, rebase workflow, squash merges

## Risk Assessment

### Technical Risks

- Canvas API changes could break assumptions copied from canvas-mcp.
  Mitigation: test against live API early (Phase 2).
- Async bridging in Typer can be tricky. Mitigation: isolate in
  `_async.py` decorator, test thoroughly.
- Rate limiting during batch grading. Mitigation: backoff in
  CanvasClient, respect 429 headers.

### Scope Risks

- Feature creep from canvas-mcp's full feature set. Guardrail:
  one-category-per-PR approach, defer non-essential entities.
- Assessment workflow complexity. Mitigation: Phase 4 is self-contained,
  can ship without it.

## Success Metrics

### Functional Criteria

- [x] `dauber courses list` returns live data in all three formats
- [x] `dauber assignments list <course> --format json` works for skills
- [x] All implemented commands have service + CLI tests passing

### Quality Criteria

- [x] ruff check and ruff format pass with no warnings
- [ ] Test coverage measured (pytest-cov not yet added)
- [x] No critical defects in core HTTP/auth handling

### Adoption Criteria

- [x] assess/* skills can call dauber via Bash instead of MCP tools
- [x] `dauber --help` documents all available commands
- [x] Setup requires only `uv pip install -e .` and a Canvas API token
- [x] Pi users can install skills with `dauber commands install --pi`
      and use them without manual format conversion
