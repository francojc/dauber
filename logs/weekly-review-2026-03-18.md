# Weekly review: dauber

**Period:** 2026-02-23 to 2026-03-18

## Accomplished

- **v0.1.1 -- Anonymization + skill commands:** Added opt-in `--anonymize`
  flag across grading and assessment commands. Strips `user_name` and
  `user_email` at the service layer; retains `user_id` for grade
  round-tripping. Expanded `.claude/commands/` with skill files for
  assignments, content, course, discuss, and grading workflows.
  `anonymize` field added to local config and `dauber config init`.

- **v0.1.2 -- XDG config system:** Global config relocated to
  `$XDG_CONFIG_HOME/dauber/config.toml` (default `~/.config/dauber/`).
  Local config moved from `.claude/course_parameters.yaml` to
  `./dauber/config.toml` (TOML throughout). `--defaults` flag on
  `dauber config global` for non-interactive setup. pyyaml removed.

- **v0.1.3 -- Config-driven defaults:** `course` argument made optional
  on all commands; falls back to `canvas_course_id` in config.
  `resolve_course()`, `resolve_assess_defaults()`, and
  `resolve_anonymize()` helpers extracted into `cli/_config_defaults.py`.
  254 tests passing.

- **v0.1.4 -- Course option fix (issue #6):** `course` changed from
  positional `Argument` to named `--course`/`-c` `Option` across all 29
  commands in 7 CLI modules. Fixes greedy positional parsing where
  required args were swallowed by the optional course value.

- **v0.1.5 -- Output and usability improvements:** `--format csv` added
  (issue #8) — header + data rows via `csv.writer` to stdout, no Rich
  markup. `grading submit-rubric` assessment_json argument changed from
  inline JSON text to a file path (issue #9) with file-not-found and
  invalid-JSON error handling. 262 tests passing.

- **Documentation:** README rewritten with full CLI reference and
  "Extending with AI" section. CHANGELOG added covering v0.1.0–v0.1.5.
  Install instructions added. CLAUDE.md updated with async event-loop
  and config-file gotchas.

## In progress

(none)

## Stalled or blocked

(none)

## Recommended next steps

1. Add `pytest-cov` and measure test coverage — 262 tests is solid but
   coverage is unquantified.
2. Review `logs/brainstorm-2026-02-25.md` for v0.1.6 candidates; the
   FERPA anonymization brainstorm surfaced open questions worth revisiting.
3. Consider integration tests against a Canvas sandbox to complement the
   existing unit test suite.
