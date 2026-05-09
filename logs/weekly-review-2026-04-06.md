# Weekly review: dauber

**Period:** 2026-03-18 to 2026-04-06

## Accomplished

- **v0.1.6 -- Rubrics subcommand + DOCX/PDF extraction:** `dauber rubrics`
  sub-app ships `list`, `show`, `create`, `import`, and `attach` commands.
  `rubrics import --csv <path>` parses Canvas wide-format CSV into title +
  criteria; `rubrics attach <rubric_id> <assignment_id>` posts a
  `rubric_association` via PUT. `_extract_attachment_text()` downloads Canvas
  file attachments and returns plain text for `.docx` and `.pdf` submissions;
  `python-docx` and `pypdf` added as runtime dependencies. 288 tests passing.

- **v0.1.7 -- Pi Agent Skills support:** `.pi/skills/` directory ships 11
  pre-converted `SKILL.md` files covering all existing Claude Code skill
  commands. `dauber commands install --pi` installs to `./.pi/skills/`;
  `--pi --global` installs to `~/.pi/agent/skills/`. Mutual-exclusion guards
  prevent `--pi`+`--local` and `--global`-without-`--pi` misuse. Claude install
  logic refactored into `_install_claude_commands()` for symmetry. 294 tests
  passing.

- **v0.1.8 -- Rename to dauber + PyPI publish + CI:** Package renamed from
  `easel` to `dauber` across all imports, entry points, config paths, and
  documentation. First public release published to PyPI. `pyproject.toml`
  expanded with full metadata. `LICENSE` (MIT) added. `justfile` added with
  setup, dev, quality, test, build/release, Nix, and utility recipes.
  `.github/workflows/ci.yml` added: lint, type-check, test on Python 3.11
  and 3.12, build, and trusted-publisher PyPI publish on tagged release.

  Assessment service fixes: `_normalize_extracted_text()` collapses
  inter-word newlines that `pypdf` emits for positional PDF layouts. JSON
  serialization switched to `ensure_ascii=False` so accented and non-Latin
  characters (e.g. `í`, `é`, `ñ`) appear as literal UTF-8 in assessment
  files. Discussion topic submissions added to assessment fetch.

  `CLAUDE.md` renamed to `AGENTS.md` for multi-agent harness compatibility.

## In progress

(none)

## Stalled or blocked

(none)

## Recommended next steps

1. Add `pytest-cov` and run first coverage report -- 294 tests is solid
   but coverage is unquantified.
2. Rename `EaselContext` to `DauberContext` in `cli/_context.py` -- the
   internal class name was missed in the v0.1.8 package rename.
3. Confirm CI green after the rename: check GitHub Actions run for the
   v0.1.8 tag.
4. Plan v0.1.9: candidates include module item CRUD, announcement threading,
   batch grading improvements, and integration tests against a Canvas sandbox.
