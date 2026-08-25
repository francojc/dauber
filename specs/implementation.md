# Development Implementation Details

**Project:** dauber
**Status:** v0.1.13 released (current)
**Last Updated:** 2026-08-24

## Architecture

### System Design

- **Architecture Pattern:** CLI pipeline
- **Primary Language:** Python 3.11+
- **Framework:** Typer (CLI), httpx (HTTP), pydantic (validation)
- **Build System:** hatchling via pyproject.toml

### Component Overview

```
dauber/
├── src/dauber/            # Application source
│   ├── __init__.py       # __version__
│   ├── core/             # HTTP client, config, caching
│   │   ├── client.py     # CanvasClient (httpx async)
│   │   ├── config.py     # Config (pydantic-settings)
│   │   ├── config_files.py # TOML config file I/O
│   │   └── cache.py      # CourseCache (code/ID mapping)
│   ├── services/         # Async business logic per entity
│   │   ├── __init__.py   # CanvasError exception
│   │   ├── courses.py    # list, details, enrollments
│   │   ├── assignments.py
│   │   ├── rubrics.py
│   │   ├── grading.py
│   │   ├── assessments.py
│   │   ├── modules.py
│   │   ├── pages.py
│   │   └── discussions.py
│   └── cli/              # Typer commands and helpers
│       ├── __init__.py
│       ├── app.py        # Main Typer app, global options
│       ├── _async.py     # asyncio.run() bridge decorator
│       ├── _output.py    # OutputFormat enum, format_output()
│       ├── _context.py   # Lazy init of client, cache, config
│       ├── courses.py    # Courses sub-app
│       ├── assignments.py
│       ├── grading.py
│       ├── assessments.py
│       ├── config.py      # Config sub-app (init, global, show)
│       ├── modules.py
│       ├── pages.py
│       ├── discussions.py
│       ├── rubrics.py    # Rubrics sub-app (list, show, create, import, attach)
│       ├── _config_defaults.py # Config-driven CLI defaults
│       └── commands.py    # Commands sub-app (install, --pi)
├── .claude/commands/     # Claude Code slash-command format
│   ├── assess/           # setup, ai-pass, refine, submit
│   ├── assignments/      # create
│   ├── content/          # publish
│   ├── course/           # overview, setup
│   ├── discuss/          # announce
│   ├── grading/          # overview
│   └── rubrics/          # create
├── .pi/skills/           # Pi Agent Skills format (v0.1.7)
│   ├── assess-setup/SKILL.md
│   ├── assess-ai-pass/SKILL.md
│   ├── assess-refine/SKILL.md
│   ├── assess-submit/SKILL.md
│   ├── assignments-create/SKILL.md
│   ├── content-publish/SKILL.md
│   ├── course-overview/SKILL.md
│   ├── course-setup/SKILL.md
│   ├── discuss-announce/SKILL.md
│   ├── grading-overview/SKILL.md
│   └── rubrics-create/SKILL.md
├── tests/
│   ├── conftest.py       # Shared fixtures
│   ├── services/         # Service tests (mock CanvasClient)
│   └── cli/              # CLI tests (mock services, CliRunner)
├── specs/                # Planning and tracking
├── logs/                 # Session and weekly logs
├── pyproject.toml        # Build config and dependencies
├── flake.nix             # Nix development environment
├── .github/workflows/ci.yml # GitHub Actions CI + PyPI publish
├── justfile              # Developer task recipes
└── AGENTS.md             # Agent project instructions
```

### Key Modules

1. **core/client.py (CanvasClient)**
   - **Purpose:** Async HTTP client wrapping httpx for Canvas API
   - **Public Interface:** `request()`, `get_paginated()`,
     `test_connection()`, `close()`
   - **Dependencies:** httpx, core/config.py

2. **core/config.py (Config)**
   - **Purpose:** Load and validate Canvas API configuration
   - **Public Interface:** `Config` (pydantic BaseSettings),
     `validate_config()` method
   - **Dependencies:** pydantic-settings

3. **core/cache.py (CourseCache)**
   - **Purpose:** Bidirectional mapping between course codes and IDs
   - **Public Interface:** `resolve()`, `refresh()`, `get_code()`,
     `get_id()`
   - **Dependencies:** core/client.py

4. **services/ (per-entity modules)**
   - **Purpose:** Async functions that call Canvas API, return
     structured data
   - **Public Interface:** Pure functions accepting CanvasClient,
     returning dicts/lists
   - **Dependencies:** core/client.py, raise CanvasError on failure

5. **cli/app.py (main app)**
   - **Purpose:** Typer app entry point, global options, sub-app
     registration
   - **Public Interface:** `app` (Typer instance), `--version`,
     `--test`, `--config`, `--format`
   - **Dependencies:** All cli/ sub-apps, cli/_context.py

6. **services/courses.py**
   - **Purpose:** Courses business logic (list, details, enrollments)
   - **Public Interface:** `list_courses()`, `get_course()`,
     `get_enrollments()` -- all async, accept CanvasClient
   - **Dependencies:** core/client.py, CanvasError

7. **cli/courses.py**
   - **Purpose:** Typer sub-app for course commands
   - **Public Interface:** `courses_app` with `list`, `show`,
     `enrollments` commands
   - **Dependencies:** services/courses.py, cli/_context.py,
     cli/_async.py, cli/_output.py

8. **services/assignments.py**
   - **Purpose:** Assignments business logic (list, get, create, update)
   - **Public Interface:** `list_assignments()`, `get_assignment()`,
     `create_assignment()`, `update_assignment()` -- all async
   - **Dependencies:** core/client.py, CanvasError
   - **Notes:** Includes `_strip_html()` helper for description cleanup.
     Availability windows support `unlock_at`, `due_at`, and `lock_at`;
     omitted update dates remain unchanged and explicit clear flags send `null`.

9. **services/rubrics.py**
   - **Purpose:** Rubrics business logic and form data encoding
   - **Public Interface:** `list_rubrics()`, `get_rubric()`, `create_rubric()`,
     `parse_rubric_csv()`, `attach_rubric()`,
     `build_rubric_assessment_form_data()` (sync helper)
   - **Dependencies:** core/client.py, CanvasError
   - **Notes:** `build_rubric_assessment_form_data()` handles Canvas
     bracket-notation encoding for rubric assessments. `parse_rubric_csv()`
     parses Canvas wide-format CSV templates; `attach_rubric()` PUTs a
     `rubric_association` to link a rubric to an assignment.

10. **services/grading.py**
    - **Purpose:** Submissions and grade posting
    - **Public Interface:** `list_submissions()`, `get_submission()`,
      `submit_grade()`, `submit_rubric_grade()` -- all async
    - **Dependencies:** core/client.py, services/rubrics.py, CanvasError
    - **Notes:** `list_submissions()` and `get_submission()` accept
      `anonymize` kwarg to blank `user_name` for FERPA compliance

11. **cli/assignments.py**
    - **Purpose:** Typer sub-app for assignment commands
    - **Public Interface:** `assignments_app` with `list`, `show`,
      `create`, `update` commands
    - **Dependencies:** services/assignments.py
    - **Notes:** Rubric workflow moved to the dedicated `dauber rubrics`
      sub-app (v0.1.6).

12. **cli/grading.py**
    - **Purpose:** Typer sub-app for grading commands
    - **Public Interface:** `grading_app` with `submissions`, `show`,
      `submit`, `submit-rubric` commands
    - **Dependencies:** services/grading.py
    - **Notes:** `submit-rubric` accepts a file path (not inline JSON)
      for the rubric assessment argument

13. **services/assessments.py**
    - **Purpose:** Assessment workflow — build, load, save, update,
      submit assessment JSON files
    - **Public Interface:** `fetch_assignment_with_rubric()`,
      `fetch_submissions_with_content()`,
      `build_assessment_structure()`, `load_assessment()`,
      `save_assessment()`, `update_assessment_record()`,
      `get_assessment_stats()`, `submit_assessments()`
    - **Private helpers:** `_extract_docx_text()`, `_extract_pdf_text()`,
      `_extract_attachment_text()` — download Canvas file attachments
      and return plain text for `.docx` and `.pdf` files;
      unsupported types return a bracketed placeholder string
    - **Dependencies:** core/client.py, services/assignments.py
      (_strip_html), services/grading.py (submit_rubric_grade),
      python-docx, pypdf
    - **Notes:** `fetch_submissions_with_content()` requests
      `include[]=attachments` from Canvas and calls
      `_extract_attachment_text()` for each attachment so file-upload
      submissions appear as text in assessment JSON. Accepts
      `anonymize` kwarg to blank `user_name` and `user_email`
      for FERPA compliance; blanked values propagate through
      `build_assessment_structure()` automatically

14. **cli/assessments.py**
    - **Purpose:** Typer sub-app for assessment workflow commands
    - **Public Interface:** `assess_app` with `setup`, `load`,
      `update`, `submit` commands
    - **Dependencies:** services/assessments.py

15. **services/modules.py**
    - **Purpose:** Modules and module item business logic
    - **Public Interface:** `list_modules()`, `get_module()`,
      `create_module()`, `update_module()`, `delete_module()`,
      `list_module_items()`, `get_module_item()`,
      `create_module_item()`, `update_module_item()`,
      `delete_module_item()`
    - **Dependencies:** core/client.py, CanvasError
    - **Notes:** `get_module()` fetches items via separate paginated
      endpoint. Module payloads wrapped as `{"module": {...}}`; item
      payloads wrapped as `{"module_item": {...}}`. Item creation
      supports Page, Assignment, Discussion, File, ExternalUrl, and
      SubHeader types. `url` function argument maps to Canvas
      `external_url` for ExternalUrl creation. Item create/update use
      Canvas bracket-notation form encoding (v0.1.12); `--publish`
      routes through the update endpoint (create ignores `published`).

16. **cli/modules.py**
    - **Purpose:** Typer sub-app for module and module item commands
    - **Public Interface:** `modules_app` with `list`, `show`,
      `create`, `update`, `delete`, plus nested `items` commands:
      `list`, `show`, `create`, `update`, `delete`
    - **Dependencies:** services/modules.py

17. **services/pages.py**
    - **Purpose:** Pages business logic (list, get, create, update, delete)
    - **Public Interface:** `list_pages()`, `get_page()`,
      `create_page()`, `update_page()`, `delete_page()`
    - **Dependencies:** core/client.py, CanvasError
    - **Notes:** Pages identified by URL slug, not numeric ID.
      Includes `_strip_html()` for body cleanup. Payload wrapped
      as `{"wiki_page": {...}}`

18. **cli/pages.py**
    - **Purpose:** Typer sub-app for page commands
    - **Public Interface:** `pages_app` with `list`, `show`,
      `create`, `update`, `delete` commands
    - **Dependencies:** services/pages.py

19. **services/discussions.py**
    - **Purpose:** Discussions business logic (list, get, create, update)
    - **Public Interface:** `list_discussions()`, `get_discussion()`,
      `create_discussion()`, `update_discussion()`
    - **Dependencies:** core/client.py, CanvasError
    - **Notes:** Includes `_strip_html()` for message cleanup.
      Supports `only_announcements` filter. Flat JSON payload
      (no wrapper key). Planned v0.1.15 extension: scheduled announcement
      publication, locking, message-file input, and richer projected fields.

20. **cli/discussions.py**
    - **Purpose:** Typer sub-app for discussion commands
    - **Public Interface:** `discussions_app` with `list`, `show`,
      `create`, `update` commands
    - **Dependencies:** services/discussions.py

21. **core/config_files.py**
    - **Purpose:** Read/write TOML config files for dauber
    - **Public Interface:** `read_global_config()`,
      `write_global_config()`, `read_local_config()`,
      `write_local_config()`, `merge_configs()`
    - **Dependencies:** tomli-w, tomllib (stdlib)
    - **Notes:** Global config at `$XDG_CONFIG_HOME/dauber/config.toml`,
      local config at `./dauber/config.toml`.
      `LOCAL_FIELDS` defines the schema for the local config
      including `anonymize` (boolean) for FERPA PII stripping

22. **cli/config.py**
    - **Purpose:** Typer sub-app for config management
    - **Public Interface:** `config_app` with `init`, `global`,
      `show` commands
    - **Dependencies:** core/config_files.py
    - **Notes:** `init` creates local TOML with interactive prompts,
      pre-filling from global config. `global` manages instructor
      defaults with optional `--defaults` flag. `show` displays
      merged view with source annotations.

23. **cli/_config_defaults.py**
    - **Purpose:** Resolve CLI argument defaults from config files
    - **Public Interface:** `resolve_course()`, `resolve_assess_defaults()`,
      `resolve_anonymize()`
    - **Dependencies:** core/config_files.py
    - **Notes:** Checks local config first, then global. Explicit CLI
      arguments always win. `resolve_course()` exits with code 1 if
      no course is available from any source.

24. **cli/commands.py** *(v0.1.7 additions)*
    - **Purpose:** Install agent skill commands in Claude Code or Pi format
    - **Public Interface:** `commands_app` with `install` command; flags
      `--overwrite`, `--local`, `--pi`, `--global`
    - **Dependencies:** pathlib, shutil
    - **Notes:** `_install_claude_commands()` handles the existing Claude
      path (refactored from inline logic for symmetry). `_install_pi_skills()`
      copies `.pi/skills/{name}/SKILL.md` from the repo root to either
      `./.pi/skills/` (default) or `~/.pi/agent/skills/` (`--global`).
      `_PI_SKILL_NAMES` lists the 11 skill directory names. Validation
      guards: `--pi` and `--local` are mutually exclusive; `--global`
      requires `--pi`.

25. **`.pi/skills/` (static files, v0.1.7)**
    - **Purpose:** Pre-converted Pi Agent Skills versions of all 11
      Claude Code commands; shipped in the repo and installed via
      `dauber commands install --pi`
    - **Format:** Each skill is a directory named `{group}-{command}`
      containing a single `SKILL.md` with minimal frontmatter (`name`,
      `description`) and the original command body verbatim
    - **Naming:** `{group}/{file}.md` → `{group}-{file}/SKILL.md`
      (e.g., `assess/ai-pass.md` → `assess-ai-pass/SKILL.md`)
    - **Notes:** Body content is copied verbatim from the Claude
      originals. `args`, `argument-hint`, and `allowed-tools` frontmatter
      fields are dropped (Pi has no equivalent). This duplicated-source model
      has drifted from current CLI syntax; planned v0.2.0 work replaces it
      with one canonical source, generated harness adapters, and CI checks
      for embedded `dauber` invocations.

### Data Model

- **Primary Data Structures:** Dicts and lists from Canvas API
  responses (no ORM)
- **Persistence Layer:** In-memory CourseCache, no local database
- **Serialization Format:** JSON for API communication and --format json
  output
- **Migration Strategy:** n/a (no local schema)

## Development Environment

### Setup

- **Language Runtime:** Python 3.11 via nix flake
- **Package Manager:** uv with pyproject.toml
- **Environment Management:** nix flake + direnv (`use flake`)
- **Local Services:** None (Canvas API is external)

### Build and Run

```bash
# Install dependencies
uv sync

# Run CLI
uv run dauber --help
uv run dauber courses list

# Run with specific format
uv run dauber courses list --format json
```

### Code Standards

- **Formatting:** ruff format (`uv run ruff format src/ tests/`)
- **Linting:** ruff check (`uv run ruff check src/ tests/`)
- **Type Checking:** pyright (v0.1.10) via `uv run pyright src/`;
  runs in CI on Python 3.11/3.12; pydantic handles runtime validation
- **Naming Conventions:** snake_case for functions/variables,
  PascalCase for classes

## Testing Strategy

### Test Levels

- **Service Tests:** pytest + pytest-asyncio, mock at CanvasClient
  level. Location: `tests/services/test_<entity>.py`
- **CLI Tests:** pytest + typer.testing.CliRunner, mock at service
  level. Location: `tests/cli/test_<entity>.py`

### Running Tests

```bash
# All tests
uv run pytest tests/

# Service tests only
uv run pytest tests/services/

# CLI tests only
uv run pytest tests/cli/

# With coverage (v0.1.9 baseline)
uv run python -m pytest --cov=dauber --cov-report=term-missing tests/

# Opt-in Canvas sandbox integration tests; creates and deletes temporary unpublished content
uv run python -m pytest tests/integration/ -m integration

# Module-item unit and CLI tests
uv run pytest tests/services/test_modules.py tests/cli/test_modules.py
```

### Coverage Targets

- **Current Baseline:** 90% statement/branch coverage measured for v0.1.9
- **Overall:** 80%+ long-term target
- **Critical Paths:** 90%+ for core/ (client, config, cache)
- **Exclusions:** CLI output formatting details and generated/irrelevant files

### Test Data

- **Fixtures:** `tests/conftest.py` for shared fixtures
- **Mocks/Stubs:** unittest.mock for CanvasClient in service tests,
  service functions in CLI tests
- **Integration:** `tests/integration/` is skipped by default and
  requires `CANVAS_API_KEY`, `CANVAS_BASE_URL`, and
  `CANVAS_SANDBOX_COURSE_ID`
- **Test Databases:** None (all external calls mocked)

## Release Implementation

### v0.1.14: Assignment Availability Windows (implemented; pending sandbox verification)

- Assignment service payloads accept `unlock_at`, `due_at`, and `lock_at`;
  all assignment projections include those fields.
- CLI parses ISO 8601 date options and validates ordering only among dates
  supplied in one request; Canvas remains final authority.
- Omitted update dates remain unchanged. Explicit clear flags send `null`.
- Service and CLI tests cover request construction, validation, and clears;
  opt-in sandbox integration test covers create, update, clear, and cleanup.

### v0.1.15: Announcement Operations

- Keep announcements in `discussions` service and CLI: Canvas represents them
  as discussion topics. Do not add separate announcement service prematurely.
- Verify Canvas API support before exposing `delayed_post_at` and `lock_at`.
- Add `--message-file`; CLI reads UTF-8 content before passing message to
  service, avoiding shell quoting failure for long announcement bodies.
- Expand output projections with scheduling, lock, pin, and URL metadata.
- Update announcement workflow skill only after CLI interface is complete.

### v0.2.0: Agent Skill Reset

- Define canonical skill content and generate Claude/Pi adapters during build
  or installation.
- Retain multi-step workflows requiring judgment or coordination; remove thin
  wrappers around one or two CLI calls.
- Add a CI test that discovers embedded `dauber` commands and verifies their
  syntax against fixture-backed CLI execution or maintained command contracts.
- Update all examples to named `--course` syntax; positional course arguments
  were removed in v0.1.4.

## Deployment

### Target Environment

- **Platform:** Local CLI tool (pip/uv installable)
- **Runtime:** Python interpreter
- **Configuration:** `CANVAS_API_KEY` and `CANVAS_BASE_URL` env vars

### CI/CD Pipeline

- GitHub Actions workflow in `.github/workflows/ci.yml`
- Runs ruff format check, ruff lint, pyright, tests on Python 3.11/3.12,
  and package build checks
- Release event supports trusted-publisher PyPI publishing

### Release Process

- **Versioning:** SemVer (0.x.y during initial development)
- **Changelog:** Maintained manually
- **Release Steps:** Tag, build with hatchling, install via uv/pip
- **Rollback Procedure:** `uv pip install` previous version

## Error Handling

- **Error Types:** `CanvasError` (base), HTTP errors from httpx
- **User-Facing Errors:** Formatted to stderr with non-zero exit codes
- **Error Reporting:** stderr output, no external reporting

## Security Considerations

### Authentication and Authorization

- **Auth Method:** Canvas API token via `CANVAS_API_KEY` env var
- **Permission Model:** Inherits Canvas user permissions
- **Secret Management:** Environment variable only, never read .env
  files programmatically in production, pydantic-settings handles
  loading

### Input Validation

- **User Input:** Typer handles CLI argument parsing and type coercion
- **API Boundaries:** pydantic validates config, CanvasClient validates
  HTTP responses

## Decision Log

| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|------------------------|
| 2026-02-22 | Extract from canvas-mcp as reference only | Keeps dauber independent, avoids coupling to MCP framework | Import canvas-mcp as library (rejected: too much MCP baggage) |
| 2026-02-22 | Use hatchling build backend | Lightweight, supports src layout natively | setuptools (heavier), flit (less flexible) |
| 2026-02-22 | Two test layers (services + CLI) | Clean separation, services test logic, CLI tests integration | Single test layer (insufficient coverage), three layers with tools/ (no MCP tools in dauber) |
| 2026-02-22 | Mock httpx at transport level | Tests actual request construction, cleaner than monkeypatching | respx library (extra dep), monkeypatch (fragile) |
| 2026-02-22 | CanvasClient class (not module functions) | Testable via DI, supports multiple configs, clean async lifecycle | Module-level functions like canvas-mcp (harder to test, global state) |
| 2026-02-22 | AsyncMock for service tests, patch get_context for CLI tests | Clean separation: service tests mock client, CLI tests mock services. No real config needed. | Transport-level mocks for CLI tests (too deep, couples layers) |
| 2026-02-22 | Rubric bracket-notation as a sync helper function | Reusable by grading service and future assessment workflow. Isolates Canvas encoding quirk. | Inline in grading service (harder to test), pydantic model (overkill) |
| 2026-02-22 | HTML stripping in assignments service | Canvas returns HTML descriptions; stripping at service level keeps CLI clean | Strip in CLI layer (duplicates logic), use a library like beautifulsoup (heavy dep for simple case) |
| 2026-02-22 | Assessment JSON as file-based interchange | Skills (assess:ai-pass, assess:refine) read/write JSON files; dauber handles Canvas I/O, skills handle AI evaluation | Database (overkill), MCP tools (coupling), in-memory only (no persistence between skill invocations) |
| 2026-02-22 | Dry-run by default for assess submit | Prevents accidental grade submission; --confirm required for actual Canvas write | Auto-submit (dangerous), interactive prompt (harder to script) |
| 2026-02-22 | Copy _strip_html into each service that needs it | Keeps services self-contained, no cross-service imports for a trivial helper | Shared utility module (premature abstraction for 3-line function) |
| 2026-02-22 | Pages identified by URL slug, not numeric ID | Canvas API uses slugs for page endpoints; matches API semantics | Numeric IDs (not how Canvas pages work) |
| 2026-02-22 | Defer student commands | Instructor workflows don't need student-facing endpoints; keeps scope focused for 0.1.0 | Include student commands (scope creep, low priority) |
| 2026-02-22 | TOML for global config, YAML for local | TOML suits key-value instructor defaults; YAML matches existing course_parameters schema used by assess skills | Both TOML (unfamiliar to users for course params), both YAML (no stdlib YAML parser) |
| 2026-02-22 | No service layer for config sub-app | Config commands do local file I/O only (no Canvas API calls); service layer would be unnecessary indirection | Add services/config.py (overkill for pure file ops) |
| 2026-02-22 | Single asyncio.run() for --test callback | Avoids event loop lifecycle issues; httpx client must be created and closed on the same loop | Separate asyncio.run() calls for test and cleanup (caused crash) |
| 2026-02-25 | Opt-in `--anonymize` flag strips PII at service layer | FERPA compliance when assessment JSON passes through LLM; simple strip (not reversible mapping) keeps implementation minimal; service-layer stripping follows existing HTML stripping pattern | Default-on anonymization (breaking change for existing workflows), reversible mapping with lookup table (unnecessary complexity, user_id suffices for round-tripping), submission text scanning (out of scope, low risk for structured fields) |
| 2026-02-25 | `course` changed from positional Argument to `--course`/`-c` Option | Optional positional args greedily consume required args (Typer/Click limitation). Named option eliminates ambiguity. | Keep positional with workaround ordering (fragile), make course required (bad UX with config fallback) |
| 2026-02-25 | CSV output via `csv.writer` to `sys.stdout` (not Rich console) | CSV must be pipe-friendly with no ANSI markup. Writing directly to stdout keeps output clean for `> file.csv` and `\| cut -f2`. | Rich CSV rendering (adds markup), custom string builder (csv module handles quoting correctly) |
| 2026-02-25 | `submit-rubric` accepts file path instead of inline JSON | Assessment JSON is typically in a file from the assess workflow. File path is easier to use and avoids shell quoting issues with complex JSON. | Keep inline JSON (poor UX for large assessments), accept both file and inline (ambiguous, over-engineered) |
| 2026-03-24 | Ship both Claude and Pi skill formats in the repo (Option A) | Avoids runtime conversion logic; both formats are reviewable in the repo; install command stays a simple copy with no frontmatter parsing. Files are small and change infrequently. | Convert at install time (simpler repo structure but adds a conversion code-path and a potential failure mode); ship Pi format only (breaks existing Claude users) |
| 2026-03-24 | `--pi` defaults to local (`./.pi/skills/`), `--global` opt-in | Pi discovers skills from `.pi/skills/` in the project tree, so cwd is the natural default. This mirrors how Pi skills are used in practice and avoids accidental global installs. | Mirror Claude's `--local` default-to-global pattern (inverts Pi conventions); always require explicit scope flag (extra friction) |
| 2026-03-24 | `--local` remains Claude-only; `--pi` and `--local` are mutually exclusive | The two flags target different harnesses and different directory conventions. Allowing both would be ambiguous and serve no real use case. | Reuse `--local` for Pi local installs (confusing: same flag, different paths); silent ignore of conflicting flags (hides user mistakes) |
