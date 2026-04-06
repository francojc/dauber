# dauber - Canvas LMS CLI

## Commands

- Build: `uv sync`
- Run: `uv run dauber <command>`
- Test: `uv run pytest tests/`
- Lint: `uv run ruff check src/ tests/`
- Format: `uv run ruff format src/ tests/`

## File structure

```
src/dauber/
├── core/         # HTTP client, config, caching, date utils, config files
├── services/     # Async business logic per Canvas entity
└── cli/          # Typer commands, async bridging, output formatting

tests/
├── services/     # Service tests — mock at CanvasClient level
└── cli/          # CLI tests — mock at service level, use CliRunner

.claude/commands/
├── assess/        # Rubric-based grading pipeline (setup, ai-pass, refine, submit)
├── assignments/   # Assignment creation workflows
├── content/       # Local-to-Canvas content publishing
├── course/        # Course setup and status dashboard
├── discuss/       # Announcement drafting and posting
└── grading/       # Grade distribution analysis
```

## Architecture

CLI -> services -> core. Services are async functions that accept a
CanvasClient and return dicts/lists. CLI commands bridge async with
`asyncio.run()`, format output, and handle errors with exit codes.

## Reference repo

canvas-mcp (`~/.local/mcp/canvas-mcp/`) contains the business logic
patterns dauber adapts. Reference only -- no runtime dependency.

## Gotchas

- Canvas API uses bracket-notation for rubric assessment form data
  (e.g., `rubric_assessment[criterion_id][points]`). The rubrics
  service must encode these correctly.
- Course identifiers can be codes (e.g., "IS505") or numeric IDs.
  The CourseCache handles bidirectional mapping. Always resolve
  through the cache.
- Never read .env files directly. Canvas API token comes from
  `CANVAS_API_KEY` env var via pydantic-settings. The base URL
  comes from `CANVAS_BASE_URL`; `/api/v1` is appended automatically.
- Async bridging: services are async, Typer callbacks are sync.
  Use the `_async.py` bridge decorator to call services from CLI.
- Output formatting: all commands support `--format` (table/json/plain/csv).
  Use `_output.py`'s `format_output()` for consistent rendering. CSV
  writes header + data rows to stdout via `csv.writer` (no Rich markup).
- Config files: global config is TOML at
  `$XDG_CONFIG_HOME/dauber/config.toml` (default `~/.config/dauber/config.toml`),
  local config is TOML at `./dauber/config.toml`. The config sub-app
  (cli/config.py) handles both; core/config_files.py has the read/write
  helpers. No service layer needed (pure file I/O).
- Event loop lifecycle: never call `asyncio.run()` twice for the same
  httpx client. The client must be created and closed on the same loop.
  See the `--test` callback pattern in app.py.
- Anonymization (`--anonymize`): opt-in flag on `assess setup`,
  `grading submissions`, and `grading show`. Strips `user_name` and
  `user_email` at the service layer. Retains `user_id` (Canvas opaque
  integer) for grade submission round-tripping. Does not scan
  submission text.
