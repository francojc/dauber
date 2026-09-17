# Development Project Progress

**Project:** dauber
**Status:** v0.1.13 released; v0.1.14 ready for release
**Last Updated:** 2026-09-15

## Current Status Overview

### Development Phase

- **Current Phase:** v0.1.14 in progress (unreleased)
- **Phase Progress:** v0.1.14 combines assignment availability windows
  (implemented, pending guarded sandbox verification) with Classic Quiz
  report export (spec complete, implementation not started); v0.1.13 added
  assignment-group metadata
- **Overall Project Progress:** Phases 0–6 + v0.1.0–v0.1.13 milestones
  complete; published on PyPI as 0.1.8, 0.1.9, 0.1.11–0.1.13

### Recent Accomplishments

- Phase 0 complete: pyproject.toml, src/dauber/ package structure,
  Typer app skeleton, async bridge, output formatting, CanvasError
- Phase 1 complete: Config (pydantic-settings), CanvasClient (httpx
  async with pagination and 429 retry), CourseCache (bidirectional
  code/ID mapping), DauberContext (lazy init), --test and --config
  callbacks wired to real implementations, 27 tests passing, ruff clean
- Phase 2 complete: Courses service (list_courses, get_course,
  get_enrollments), courses CLI sub-app (list, show, enrollments),
  service tests mocking CanvasClient, CLI tests mocking services,
  44 tests passing, ruff clean
- Phase 3 complete: Assignments service (list, get, create, update),
  rubrics service (list, get, bracket-notation form builder), grading
  service (submissions, get, submit grade, submit rubric grade),
  assignments CLI (list, show, create, update, rubrics, rubric),
  grading CLI (submissions, show, submit, submit-rubric),
  99 tests passing, ruff clean
- Phase 4 complete: Assessment service (fetch assignment+rubric, fetch
  submissions with content, build/load/save/update assessment JSON,
  stats, submit approved assessments to Canvas), assessment CLI
  (setup, load, update, submit with dry-run), 133 tests passing,
  ruff clean
- Phase 5 complete: Modules service (list, get, create, update,
  delete), pages service (list, get, create, update, delete with
  slug-based IDs), discussions service (list, get, create, update
  with announcement support), CLI sub-apps for all three, HTML
  stripping in pages and discussions, 210 tests passing, ruff clean

### Recent Accomplishments (v0.1.6)

- `rubrics import --csv <path>` command: parses Canvas wide-format CSV
  into title + criteria, creates rubric via existing `create_rubric`
- `rubrics attach <rubric_id> <assignment_id>` command: `PUT` association
  with optional `--use-for-grading`; returns summary dict
- `parse_rubric_csv` service: positional CSV parsing (avoids
  `DictReader` duplicate-header issue), validates rubric name
  uniqueness, numeric points, required columns
- `attach_rubric` service: wraps `PUT /courses/:id/rubrics/:rubric_id`
  with `rubric_association` JSON body, raises `CanvasError` on failure
- `.claude/commands/rubrics/create.md` skill: end-to-end guided workflow
  (CSV / JSON / interactive), captures rubric ID, offers attach,
  suggests `/assess:setup` next
- `assignments/create.md` Step 5 simplified: inline JSON + Option A/B
  replaced with one-line handoff to `/rubrics:create`
- DOCX/PDF attachment text extraction: `_extract_attachment_text()`
  downloads Canvas file attachments and returns plain text for `.docx`
  and `.pdf`; `python-docx` and `pypdf` added as runtime dependencies
- Fix: `rubrics` added to `_COMMAND_GROUPS` so `dauber commands install`
  now installs `rubrics/create.md`
- 288 total tests, all passing, ruff clean

### Recent Accomplishments (v0.1.8)

- Package renamed from `easel` to `dauber` — all internal imports, entry
  points, config paths (`dauber/config.toml`, `~/.config/dauber/config.toml`),
  and documentation updated
- First public release published to PyPI
- `pyproject.toml` expanded with description, license, authors, keywords,
  classifiers, and `[project.urls]` for PyPI metadata
- `LICENSE` (MIT) added
- `justfile` with setup, dev, quality, test, build/release, Nix, and utility recipes
- `.github/workflows/ci.yml`: lint, type-check, test (Python 3.11 + 3.12),
  build, and trusted-publisher PyPI publish on release
- PDF text extraction fix: `_normalize_extracted_text()` collapses
  inter-word newlines from `pypdf` positional layouts into spaces
- Assessment JSON now written with `ensure_ascii=False` — accented and
  non-Latin characters stored as literal UTF-8
- Discussion topic submissions added to assessment service
- AGENTS.md replaces CLAUDE.md

### Recent Accomplishments (v0.1.7)

- `.pi/skills/` directory with 11 SKILL.md files (Pi Agent Skills format)
  converted from all existing Claude Code skill commands
- `dauber commands install --pi` installs skills to `./.pi/skills/`
- `dauber commands install --pi --global` installs to `~/.pi/agent/skills/`
- Mutual-exclusion guards: `--pi`+`--local` and `--global` without `--pi`
- Claude install logic refactored into `_install_claude_commands()` for symmetry
- 6 new tests; 294 total, all passing, ruff clean

### Recent Accomplishments (v0.1.13)

- `assignments list` and `assignments show` output now includes Canvas
  assignment-group ID, name, and weight

### Recent Accomplishments (v0.1.14)

- Live Canvas sandbox verification of assignment availability windows passed
  against course `4341` on 2026-09-15 (create, update, and `null` clears)
- Integration-test environment guards now report only the variables actually
  missing, plus a hint when `CANVAS_SANDBOX_ID` is set instead of
  `CANVAS_SANDBOX_COURSE_ID`
- Added `scripts/probe_quiz_reports.py`: read-only quiz discovery with an
  opt-in `--create` report generation probe
- Probed the live Classic Quiz report API on course `74806` (2026-09-16):
  locked bare-array quiz/report responses, get-or-create `POST`, `file` key as
  the completion signal, `progress_url` as the only failure channel, and the
  assignment→quiz map for all 8 autoevaluaciones
- v0.1.14 scope expanded to include Classic Quiz report export (`dauber
  quizzes`), now implemented; feature spec at
  `specs/dauber-quiz-report-export-spec.md`

### Recent Accomplishments (v0.1.12)

- Guarded live Canvas sandbox coverage for ExternalUrl module-item create,
  show, list, update, and delete operations
- Module-item create/update requests now use Canvas bracket-notation form
  encoding instead of JSON
- ExternalUrl creation maps CLI `--url` to Canvas `external_url`
- Module-item creation with `--publish` publishes through the update
  endpoint; the create endpoint ignores `published`
- Integration test renamed `test_module_external_url.py` →
  `test_module_items.py`; refines the initial v0.1.11 release

### Recent Accomplishments (v0.1.11)

- Initial ExternalUrl module-item CRUD released to PyPI from side commit
  5b0d0d6 (not on main); superseded by v0.1.12's refined version

### Recent Accomplishments (v0.1.10)

Git-tagged and documented, but not published to PyPI — fixes were carried
upstream by the 0.1.11 PyPI publish.

- Added `pyright` development dependency and CI type-check job
- Module-item create validation now returns consistent error messages and exit code 2 across supported Typer/Click versions
- Verified live Canvas sandbox module-item CRUD: created, showed, listed, updated, and deleted a temporary `SubHeader` item; cleanup removed temporary module
- 311 unit tests passing; module-focused suite has 41 passing tests

### Active Work

- v0.1.14 implementation complete: assignment availability windows
  (`unlock_at`, `due_at`, `lock_at`), explicit date clearing, ISO validation,
  unit/CLI tests, and opt-in sandbox coverage.
- Sandbox verification passed 2026-09-15 against course `4341`
  (`CANVAS_SANDBOX_COURSE_ID=4341 CANVAS_SANDBOX_WRITE_ENABLED=1`): all 4
  guarded integration tests pass; 319 unit tests pass, 4 deselected.
- v0.1.14 scope expanded: Classic Quiz report export (`dauber quizzes`) folded
  into this release and implemented. Spec at
  `specs/dauber-quiz-report-export-spec.md`.
- Live quiz-report probe completed 2026-09-16 on course `74806`: response
  shapes, progress endpoint, `file` attachment, and the 8-quiz assignment→quiz
  map recorded in `specs/dauber-quiz-report-export-spec.md`.
- v0.1.14 quiz export implemented 2026-09-16: `services/quizzes.py`,
  `cli/quizzes.py`, 43 new tests, README + CHANGELOG entries; acceptance run
  exported all seven Fall 2025 autoevaluaciones with expected filenames.
- Pending: release v0.1.14 (version bump, tag, PyPI publish).
- v0.1.15: announcement operations (scheduling, locking, message-file input)
- v0.2.0: agent-skill reset (canonical source, generated adapters, audit)
- 319 unit tests passing (4 live-sandbox integration tests deselected by
  default)


## Milestone Tracking

### Completed Milestones

- [x] Phase 0: Scaffolding complete -- `dauber --help` works
- [x] Phase 1: Core layer -- config, client, cache tested (27 tests)
- [x] Phase 2: Courses -- service + CLI + tests (44 tests total)
- [x] Phase 3: Assignments + rubrics + grading (99 tests total)
- [x] Phase 4: Assessment workflow (133 tests total)
- [x] Phase 5: Modules, pages, discussions (210 tests total)

### Upcoming Milestones

- [ ] v0.1.14: Assignment availability windows implemented and sandbox verified; Classic Quiz report export implemented and acceptance-run against course `74806`; pending release
- [ ] v0.1.15: Announcement operations — scheduling/locking API verification, `--message-file`, richer outputs, repaired announcement skill
- [ ] v0.2.0: Agent skill reset — audit, remove low-value wrappers, canonical source + generated Claude/Pi adapters, CI command smoke tests
- [x] 0.1.0 release (tagged)
- [x] Phase 6: Polish (shell completion, README, docs) -- complete
- [x] v0.1.10: Pyright type-checking + CI, module-item validation fixes, sandbox CRUD verification — complete
- [x] v0.1.11: Initial ExternalUrl CRUD (off-main side commit) — complete
- [x] v0.1.12: ExternalUrl CRUD + bracket-notation form encoding — complete
- [x] v0.1.13: Assignment-group metadata — complete
- [x] v0.1.1: Anonymize + skill commands (tagged)
- [x] v0.1.2: XDG-compliant config system (tagged)
- [x] v0.1.3: Config-driven defaults (tagged)
- [x] v0.1.4: Course option fix, issue #6 (tagged)
- [x] v0.1.5: CSV output format (#8) + file-based rubric grading (#9)
- [x] v0.1.6: Rubrics subcommand (import CSV, attach, skill, DOCX/PDF extraction) — complete (internal milestone, not released) [x] v0.1.7: Pi Agent Skills support — complete (internal milestone, not released)
- [x] v0.1.8: Rename to dauber, PyPI publish, CI, assessment fixes — complete

### At-Risk Milestones

(none)

## Build and Test Status

### Build Health

- **Last Successful Build:** 2026-09-15 (`uv sync` + `uv run pytest tests/`)
- **Build Warnings:** None

### Test Results

- **Unit Tests:** 362 passing (verified 2026-09-16)
  - services: quizzes 21
  - cli: quizzes 22
  - core: config 4, client 11, cache 9, config_files 9
  - services: courses 9, assignments 14, rubrics 18, grading 12,
    assessments 30, modules 14, pages 15, discussions 15
  - cli: courses 9, assignments 9, rubrics 15, grading 14,
    assessments 13, modules 11, pages 12, discussions 12,
    config 8, config_defaults 14, commands 10, output 6
  - smoke: 3
- **Integration Tests:** 4 passing against sandbox course `4341` on
  2026-09-15 (assignment availability, connectivity, ExternalUrl, module
  items); skipped by default via `addopts = "-m 'not integration'"`; run with
  `-rs` to surface skip reasons
- **Test Coverage:** 90% statement/branch coverage baseline via `uv run python -m pytest --cov=dauber --cov-report=term-missing tests/`

### Open Defects

- **Critical:** 0
- **High:** 0
- **Medium:** 0
- **Low:** 0

## Feature Progress

### Completed Features

- [x] Typer CLI app with global options (--version, --format, --test, --config)
- [x] Async bridge decorator (`_async.py`)
- [x] Output formatting: table, json, plain, csv (`_output.py`)
- [x] CanvasError exception class
- [x] Config via pydantic-settings (env vars, validation)
- [x] CanvasClient (httpx async, pagination, 429 retry, form data)
- [x] CourseCache (bidirectional code/ID mapping, smart resolution)
- [x] DauberContext (lazy init of config, client, cache)
- [x] --test and --config callbacks (real implementations)
- [x] Courses service: list_courses, get_course, get_enrollments
- [x] Courses CLI: `dauber courses list`, `show`, `enrollments`
- [x] Assignments service: list, get, create, update (with HTML stripping)
- [x] Rubrics service: list, get, bracket-notation form data builder
- [x] Grading service: list submissions, get submission, submit grade,
  submit rubric grade
- [x] Assignments CLI: `dauber assignments list|show|create|update`
- [x] Rubrics CLI: `dauber rubrics list|show|create|import|attach`
- [x] `create_rubric` service: POST with bracket-notation form-data, schema validation
- [x] `parse_rubric_csv` service: Canvas wide-format CSV → (title, criteria)
- [x] `attach_rubric` service: PUT rubric_association for assignment linkage
- [x] `.claude/commands/rubrics/create.md` skill: guided create + attach workflow
- [x] DOCX/PDF attachment text extraction: `_extract_attachment_text()` downloads
  and parses `.docx`/`.pdf` Canvas attachments into plain text for assessment JSON;
  `python-docx` and `pypdf` runtime dependencies added
- [x] `.pi/skills/` directory with 11 SKILL.md files (Pi Agent Skills format)
- [x] `dauber commands install --pi` and `--pi --global` flags
- [x] `_install_pi_skills()` and `_install_claude_commands()` helpers in
  `cli/commands.py`; mutual-exclusion guards for `--pi`/`--local` and
  `--global` without `--pi`
- [x] Grading CLI: `dauber grading submissions|show|submit|submit-rubric`
- [x] Assessment service: fetch assignment+rubric, fetch submissions
  with content, build/load/save/update JSON, stats, submit to Canvas
- [x] Assessment CLI: `dauber assess setup|load|update|submit`
- [x] Commands CLI: `dauber commands install` (copies .claude/commands/assess/*.md)
- [x] Assess skill commands migrated from MCP to dauber CLI (setup, ai-pass, refine, submit)
- [x] Config sub-app: `dauber config init|global|show` with TOML
  file management, XDG support, and global-to-local inheritance
- [x] Live smoke test: all 17 CLI commands verified against Canvas API
- [x] Bug fix: --test callback event loop crash (combined into single
  async function)
- [x] Modules service: list, get, create, update, delete
- [x] Modules CLI: `dauber modules list|show|create|update|delete`
- [x] Pages service: list, get, create, update, delete (slug-based IDs)
- [x] Pages CLI: `dauber pages list|show|create|update|delete`
- [x] Discussions service: list, get, create, update (with announcements)
- [x] Discussions CLI: `dauber discussions list|show|create|update`
- [x] `--anonymize` flag for FERPA-compliant PII stripping
- [x] Expanded `.claude/commands/` with skill commands for assignments,
  content, course, discuss, grading
- [x] `anonymize` field in local config and `dauber config init`
- [x] README `--anonymize` documentation and command signature updates
- [x] `assess:setup` and `course:setup` skill commands updated for anonymize
- [x] Config-driven defaults: `course` argument optional, reads from config
- [x] `resolve_course()`, `resolve_assess_defaults()`, `resolve_anonymize()`
  helpers in `cli/_config_defaults.py`
- [x] `assess setup` options read defaults from config files
- [x] `grading submissions`/`grading show` read `anonymize` from config

### In Progress

(none)

### Planned

- Keep announcements under `dauber discussions`; Canvas represents an
  announcement as a discussion topic. Reconsider a separate CLI alias only
  after migration use establishes need.
- Validate assignment-date ordering for dates provided in one operation;
  Canvas remains final authority for date-window policy.
- Add `dauber quizzes` (Classic Quiz reports) without new core-layer changes:
  reuse `CanvasClient.get_paginated()`, bracket-notation `form_data`, and
  `CanvasClient.download()`.
- Hold any `quizzes-export` agent skill until after the v0.2.0 skill reset; a
  skill added now would be rewritten during canonical-source migration.
- Do not overload omitted update date options as clears. Use explicit clear
  flags that send `null` to Canvas.

### Deferred or Cut

- Student commands (deferred -- not needed for instructor workflows)

## Technical Debt

### Known Debt

- Bundled Claude and Pi skills duplicate content and have drifted from current
  CLI syntax: several use positional course arguments removed in v0.1.4.
  v0.2.0 resolves this with canonical source, generated adapters, and CI
  validation of embedded `dauber` commands.

### Recently Resolved

- `EaselContext` renamed to `DauberContext` after the v0.1.8 package rename.
- --test callback used two separate asyncio.run() calls; httpx client
  bound to first event loop caused crash on cleanup. Fixed by combining
  test + close into single async function.

## Dependency Status

### External Dependencies

- **httpx:** async HTTP client for Canvas API
- **typer:** CLI framework with rich integration
- **pydantic / pydantic-settings:** config and data validation
- **rich:** terminal output formatting (tables, panels)
- **tomli-w:** TOML write for config files (stdlib tomllib for reads)
- **ruff:** linting and formatting (dev dependency)
- **pytest / pytest-asyncio:** testing (dev dependency)

### Pending Updates

(none -- dependencies not yet pinned)

## Challenges and Blockers

### Current Blockers

(none)

### Resolved Challenges

- httpx mock transport for client tests: used custom
  `AsyncBaseTransport` subclass instead of `respx` library
- Pagination test hung because URL string matching was fragile;
  switched to parsing `request.url.params` dict directly
- Integration tests appeared to skip for missing API credentials when only the
  sandbox course id was wrong: the skip reason was a static string listing all
  requirements. Fixed by rendering the reason from the missing-variable list,
  plus a `CANVAS_SANDBOX_ID` typo hint

### Lessons Learned

- Mock httpx at transport level, not with monkeypatching -- cleaner
  and tests actual request construction
- Parse URL params from the request object, not string matching
- For CLI tests, mock at the service function level and patch
  get_context to avoid needing real config/credentials
- AsyncMock works well for service functions called from
  async_command-bridged CLI commands
- Probe live Canvas endpoints before coding against them: the quiz-report API
  differs from documented assumptions (bare arrays, `file` rather than
  `attachment`, no `workflow_state` on the report object)
- Static skip reasons hide the real cause; render them from actual state and
  run pytest with `-rs`

## Next Steps

### Immediate Actions (Next Session)

- Release v0.1.14: bump `version` in `pyproject.toml` (and
  `src/dauber/__init__.py`, currently stale at 0.1.11), tag, and publish.

### Medium-term Goals (Next Few Sessions)

- Implement v0.1.15 announcement operations after Canvas API verification.
- Complete v0.2.0 skill audit and canonical-source design.
- Consider coverage threshold after one more baseline release.

### Decisions Needed

- Which non-assessment skills survive v0.2.0 audit: retain only workflows
  demonstrating repeated migration value.

## Release Planning

### Next Release

v0.1.14: Assignment Availability Windows + Classic Quiz Reports. Both feature
sets implemented and verified (sandbox course `4341`; live export on course
`74806`). Blocks release: version bump, tag, and PyPI publish.

### Release History

| Version | Date       | Key Changes                                              |
|---------|------------|----------------------------------------------------------|
| 0.1.14  | 2026-09-16 | Assignment availability windows; Classic Quiz report export (`dauber quizzes`) |
| 0.1.13  | 2026-08-20 | Assignment-group metadata in list/show                    |
| 0.1.12  | 2026-08-20 | ExternalUrl module-item CRUD, bracket-notation form encoding |
| 0.1.11  | 2026-08-19 | Initial ExternalUrl CRUD (off-main side commit, superseded) |
| 0.1.10  | 2026-08-19 | Pyright + CI, module-item validation fixes, sandbox CRUD (tagged, not published to PyPI) |
| 0.1.9   | 2026-05-11 | Coverage baseline and module-item CRUD                   |
| 0.1.8   | 2026-04-06 | Rename to dauber, PyPI publish, CI, PDF/unicode fixes    |
| 0.1.7   | 2026-03-24 | Pi Agent Skills: --pi flag, .pi/skills/, 294 tests  *    |
| 0.1.6   | 2026-03-24 | Rubrics sub-app, DOCX/PDF extraction, commands fix; 288 tests * |
| 0.1.5   | 2026-03-18 | CSV output format (#8), file-based rubric grading (#9)   |
| 0.1.4   | 2026-02-25 | Course changed to --course/-c option (fix #6)            |
| 0.1.3   | 2026-02-25 | Config-driven defaults, optional course arg              |
| 0.1.2   | 2026-02-25 | XDG config, TOML local config, --defaults flag           |
| 0.1.1   | 2026-02-25 | --anonymize flag, expanded skill commands                |
| 0.1.0   | 2026-02-23 | Initial release (all core phases)                        |

* 0.1.6/0.1.7 were internal milestone labels — never git-tagged nor
  published to PyPI; their work shipped in 0.1.8 (first PyPI release).
   v0.1.10 was git-tagged but never published to PyPI (carried upstream
  by 0.1.11).
