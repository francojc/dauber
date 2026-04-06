# Changelog

All notable changes to dauber are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.8] - 2026-03-24

### Fixed

- PDF text extraction now collapses inter-word newlines into spaces via
  `_normalize_extracted_text()`. `pypdf` emits a newline at every glyph
  boundary in positional PDF layouts, producing fragmented
  `\nword\n \nword\n` output; the normalizer folds single-newline runs
  into a single space while preserving real paragraph breaks (double
  newlines)
- Assessment JSON files now written with `ensure_ascii=False` so accented
  and non-Latin characters (e.g. `í`, `é`, `ñ`) are stored as literal
  UTF-8 rather than `\uXXXX` escape sequences

## [0.1.7] - 2026-03-24

### Added

- `.pi/skills/` directory with 11 pre-converted Pi Agent Skills (`SKILL.md`)
  covering all existing Claude Code skill commands: `assess-setup`,
  `assess-ai-pass`, `assess-refine`, `assess-submit`, `assignments-create`,
  `content-publish`, `course-overview`, `course-setup`, `discuss-announce`,
  `grading-overview`, `rubrics-create`
- `dauber commands install --pi` installs Pi skills to `./.pi/skills/` (local)
- `dauber commands install --pi --global` installs to `~/.pi/agent/skills/`
- `--global` flag on `commands install` (Pi-only; raises error without `--pi`)
- Mutual-exclusion guard: `--pi` and `--local` raise an error (different
  harnesses and different directory conventions)
- 6 new tests in `tests/cli/test_commands.py`; 294 total

### Changed

- `commands install` help text updated: "Install agent skill commands
  (Claude Code or Pi)."
- Claude install logic refactored into `_install_claude_commands()` for
  symmetry with new `_install_pi_skills()`

## [0.1.6] - 2026-03-24

### Added

- `dauber rubrics` sub-app with five commands: `list`, `show <id>`,
  `create --file <path>`, `import --csv <path>`, `attach <rubric_id> <assignment_id>`
- `create_rubric` service: validates criteria schema before any network
  call, encodes bracket-notation form-data, raises `CanvasError` on HTTP
  errors
- `parse_rubric_csv` service: parses Canvas wide-format CSV template into
  `(title, criteria)` using positional column slicing; handles variable-length
  rating triplets, validates rubric name uniqueness and numeric points
- `attach_rubric` service: `PUT /courses/:id/rubrics/:rubric_id` with
  `rubric_association` body; optional `use_for_grading` flag
- `.claude/commands/rubrics/create.md` skill: guided end-to-end workflow
  (CSV / JSON / interactive), captures rubric ID, offers attachment,
  suggests `/assess:setup` as next step
- DOCX and PDF attachment text extraction in the assessment service:
  `_extract_docx_text()`, `_extract_pdf_text()`, `_extract_attachment_text()`;
  submission fetch now includes `attachments` in Canvas API params so
  file-upload submissions are included in assessment JSON
- `python-docx` and `pypdf` added as runtime dependencies
- 18 new tests (7 service + 5 CLI + 6 assessment attachment); 288 total

### Changed

- `assignments rubrics` and `assignments rubric` commands removed from
  `dauber assignments`; all rubric commands now live under `dauber rubrics`
- `assignments/create.md` Step 5 simplified: inline JSON example and
  Option A/B branching replaced with a one-line handoff to `/rubrics:create`

### Fixed

- `rubrics` command group missing from `_COMMAND_GROUPS` in
  `cli/commands.py`; `dauber commands install` now copies
  `rubrics/create.md` to the target commands directory

## [0.1.5] - 2026-02-25

### Added

- `--format csv` output mode: writes header row + data rows via
  `csv.writer` to stdout. Pipe-friendly (no Rich markup). Works on
  all commands that support table output (Issue #8)

### Changed

- `grading submit-rubric` now accepts a file path to a JSON file
  instead of an inline JSON string. Errors on missing file or
  invalid JSON with clear messages (Issue #9)

## [0.1.4] - 2026-02-25

### Fixed

- `course` changed from positional argument to `--course`/`-c` option
  across all 29 commands in 7 CLI modules. Fixes greedy positional
  parsing where `dauber assignments rubric 660168` consumed `660168`
  as the course instead of `assignment_id` (Issue #6)

## [0.1.3] - 2026-02-25

### Added

- Config-driven defaults: commands read `canvas_course_id` from
  `dauber/config.toml` when the course argument is omitted
- `resolve_course()` helper falls back to local then global config
- `assess setup` options (`--level`, `--feedback-language`,
  `--language-learning`, `--language-level`, `--formality`,
  `--anonymize`, `--course-name`) now read defaults from config
- `grading submissions` and `grading show` read `anonymize` from config
  when the flag is not explicitly passed

### Changed

- `course` argument is now optional on all commands that accept it
  (25 commands across 7 CLI modules)
- `--anonymize` on grading commands changed from simple flag to
  `--anonymize/--no-anonymize` to support config override

## [0.1.2] - 2026-02-25

### Added

- XDG-compliant global config: respects `$XDG_CONFIG_HOME`
  (default `~/.config/dauber/config.toml`)
- `--defaults` flag on `dauber config global` for non-interactive setup
- `--local` flag on `dauber commands install` to install skill commands
  into the current repo's `.claude/commands/` instead of globally
- `dauber commands install` now covers all 6 command groups (assess,
  assignments, content, course, discuss, grading)

### Changed

- Local config moved from `.claude/course_parameters.yaml` (YAML)
  to `./dauber/config.toml` (TOML)
- Improved `--help` text across all sub-apps and commands
- README rewritten as a user-facing document with standard structure

### Removed

- `pyyaml` dependency (all config is now TOML)

## [0.1.1] - 2026-02-25

### Added

- `--anonymize` flag for FERPA-compliant PII stripping on
  `assess setup`, `grading submissions`, and `grading show`
- `anonymize` field in local course config
- Claude Code skill commands for assignments, content, course,
  discuss, and grading groups

### Changed

- `assess:setup` and `course:setup` skill commands read `anonymize`
  from course config

### Fixed

- Removed deprecated `.direnv/bin/nix-direnv-reload` script

## [0.1.0] - 2026-02-23

Initial release. Full Canvas LMS CLI for instructor workflows.

### Added

- **Core layer:** `CanvasClient` (httpx async, pagination, 429 retry),
  `Config` (pydantic-settings), `CourseCache` (bidirectional code/ID
  mapping)
- **Courses:** `list`, `show`, `enrollments`
- **Assignments:** `list`, `show`, `create`, `update`, `rubrics`,
  `rubric`
- **Grading:** `submissions`, `show`, `submit`, `submit-rubric`
- **Assessment workflow:** `setup`, `load`, `update`, `submit`
  (dry-run by default, `--confirm` to post)
- **Modules:** `list`, `show`, `create`, `update`, `delete`
- **Pages:** `list`, `show`, `create`, `update`, `delete`
  (slug-based identification)
- **Discussions:** `list`, `show`, `create`, `update`
  (with announcement support)
- **Config sub-app:** `init`, `global`, `show` with YAML/TOML
  file management and global-to-local inheritance
- **Commands sub-app:** `install` to copy assess skill commands
  to `~/.claude/commands/`
- Three output formats: `table`, `json`, `plain`
- Shell completion via `--install-completion`
- `--test` flag for Canvas API connectivity check
- 234 tests passing across services and CLI layers

[0.1.8]: https://github.com/francojc/dauber/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/francojc/dauber/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/francojc/dauber/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/francojc/dauber/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/francojc/dauber/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/francojc/dauber/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/francojc/dauber/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/francojc/dauber/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/francojc/dauber/releases/tag/v0.1.0
