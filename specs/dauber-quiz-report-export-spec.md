# Dauber quiz report export

## Purpose

Add Canvas Classic Quiz report support to `dauber`. Instructors need reproducible exports of per-student quiz responses, especially Canvas's **Student Analysis** CSV.

Primary use case:

```sh
dauber quizzes reports download --assignment 614873 --course 74806 --type student_analysis --output _data/autoevaluaciones/F25/
```

This command creates or reuses the Student Analysis report for quiz assignment `614873`, waits for Canvas to generate it, and saves its CSV in given directory.

## Scope

- Discover Classic Quizzes in a course.
- Create, inspect, wait for, and download Canvas quiz reports.
- Support `student_analysis` first.
- Preserve CSV bytes returned by Canvas. No parsing, normalization, or re-serialization.
- Support report generation delay through polling.

Out of scope:

- New Quizzes / Quizzes.Next report exports.
- CSV transformations, anonymization, aggregation, or grade changes.
- Browser automation.

## CLI design

Add top-level `quizzes` command.

```text
dauber quizzes list --course COURSE [--search TEXT] [--format table|json|plain]
dauber quizzes show QUIZ_ID --course COURSE
dauber quizzes reports list QUIZ_ID --course COURSE
dauber quizzes reports create QUIZ_ID --course COURSE --type student_analysis [--all-versions]
dauber quizzes reports show QUIZ_ID REPORT_ID --course COURSE
dauber quizzes reports download QUIZ_ID --course COURSE --type student_analysis --output PATH [--wait|--no-wait] [--all-versions] [--force]
```

Defaults:

- `--type student_analysis`
- `--wait`
- `--output .`
- Current configured course when `--course` omitted.

`download` is high-level command. It must:

1. Resolve `QUIZ_ID`.
2. Reuse a completed compatible report unless `--force` passed.
3. Create report when no reusable report exists.
4. Wait for generation when `--wait` passed.
5. Download report attachment to output path.

`--no-wait` must return after report request. It prints report ID and polling URL. Exit success because request was accepted, not because file exists.

## Quiz identifiers

Canvas Assignment ID and Canvas Classic Quiz ID are different identifiers. `dauber` must not assume equality.

For `quizzes` commands, positional `QUIZ_ID` means Canvas Classic Quiz ID. Add assignment resolution to support instructor workflow:

```sh
dauber quizzes resolve-assignment 614873 --course 74806
```

This prints matching Classic Quiz ID and metadata. `reports download` may accept `--assignment ASSIGNMENT_ID` as alternative to positional quiz ID:

```sh
dauber quizzes reports download --assignment 614873 --course 74806 --output exports/
```

Passing both positional `QUIZ_ID` and `--assignment` is error.

`quizzes list` output must include `id`, `assignment_id`, `title`, `quiz_type`, `published`, and `due_at`.

## Canvas API behavior

Verified against course `74806` on 2026-09-16. Field names below are observed,
not assumed.

Use authenticated Canvas API client already configured by `dauber`.

Classic Quiz discovery:

- `GET /api/v1/courses/{course_id}/quizzes`
- Follow pagination.
- Match an assignment through quiz `assignment_id`, not title matching.

Report lifecycle:

- `GET /api/v1/courses/{course_id}/quizzes/{quiz_id}/reports`
- `POST /api/v1/courses/{course_id}/quizzes/{quiz_id}/reports` with `quiz_report[report_type]=student_analysis` and optional `quiz_report[includes_all_versions]=true`.
- Poll report or Canvas-provided progress URL until completed or failed.
- Download report attachment URL only after completed state and attachment URL are present.

Implementation must use Canvas links/URLs returned by API rather than constructing attachment URLs.

### Verified response shapes

`GET /courses/{course_id}/quizzes` returns a **bare JSON array** (no wrapper).
Quiz fields of interest: `id`, `assignment_id`, `title`, `quiz_type`
(`graded_survey` for the autoevaluaciones), `published`, `due_at`,
`permissions`, `quiz_reports_url`.

`GET /courses/{course_id}/quizzes/{quiz_id}/reports` returns a **bare JSON
array** of report stubs:

```json
{ "id": 71956, "report_type": "student_analysis",
  "readable_type": "Análisis de estudiantes", "includes_all_versions": false,
  "includes_sis_ids": true, "generatable": true, "anonymous": false,
  "url": ".../reports/71956", "created_at": "...", "updated_at": "...",
  "quiz_id": 98732 }
```

`POST .../reports` with `quiz_report[report_type]=student_analysis` is
**get-or-create**: posting when a report already exists for that
(`report_type`, `includes_all_versions`) pair returns the same report `id` and
re-triggers generation (`updated_at` advances). Response adds `progress_url`;
it does **not** include `file` until generation finishes.

`GET .../reports/{report_id}` returns the same object; when complete it gains a
`file` key (not `attachment`):

```json
"file": { "id": 6821649, "display_name": "Capítulo 2: Autoevaluación Survey Student Analysis Report.csv",
  "filename": "quiz_student_analysis_report.csv", "content-type": "text/csv",
  "url": "https://.../files/6821649/download?...", "size": 2779, "upload_status": "success" }
```

Report objects carry **no `workflow_state` and no `progress` object**. State
lives at `progress_url` (`GET /api/v1/progress/{id}`):

```json
{ "id": 1423744, "context_type": "Quizzes::QuizStatistics",
  "workflow_state": "completed", "completion": 100.0, "message": null }
```

Observed states: `queued`, `running`, `completed`, `failed`. Generation for a
survey with a handful of submissions took ~26 seconds.

`file.filename` is generic (`quiz_student_analysis_report.csv`) and must not be
used for output naming. `file.display_name` is human-readable but inherits the
quiz title verbatim, including `:` and stray trailing whitespace
(`"Capítulo 8: Autoevaluación "` → double space in display_name), so derive the
on-disk name from the stripped quiz title per the Output files section and keep
display_name only as fallback.

Downloads: `GET file.url` with the normal bearer header returns the CSV bytes
directly (HTTP 200, `text/csv`). No HTML/JSON envelope. Canvas CSVs include SIS
ID columns (`sis_id`, `section_sis_id`) by default.

### Assignment → quiz map (course 74806)

| Quiz ID | Assignment ID | Title | quiz_type |
|---------|---------------|-------|-----------|
| 98659 | 613133 | Capítulo 1: Autoevaluación | graded_survey |
| 98732 | 614873 | Capítulo 2: Autoevaluación | graded_survey |
| 98892 | 616448 | Capítulo 3: Autoevaluación | graded_survey |
| 99160 | 618813 | Capítulo 4: Autoevaluación | graded_survey |
| 99461 | 621808 | Capítulo 5: Autoevaluación | graded_survey |
| 99654 | 623863 | Capítulo 6: Autoevaluación | graded_survey |
| 99767 | 625931 | Capítulo 7: Autoevaluación | graded_survey |
| 99873 | 626694 | Capítulo 8: Autoevaluación (title has trailing space) | graded_survey |

All seven assignment IDs in the acceptance criteria resolve to Classic Quizzes.

Polling:

- Poll the report object for a `file` key **and** the `progress_url` for
  `workflow_state`; `failed` progress carries the Canvas `message`.
- Initial interval: 1 second.
- Exponential backoff capped at 10 seconds.
- Default timeout: 5 minutes; configurable with `--timeout SECONDS`.
- Print concise progress only for terminal output. JSON output must remain machine-readable.
- On failure or timeout, return non-zero and include report ID, last known state, and Canvas error message when available.

## Output files

When `--output` is directory, use Canvas report filename when available. Otherwise derive:

```text
{quiz title with ':' replaced by '_', surrounding whitespace trimmed} Survey Student Analysis Report.csv
```

Example:

```text
Capítulo 2: Autoevaluación
→ Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv
```

When `--output` has `.csv` suffix, treat it as exact file path.

Safety rules:

- Create output directory when missing.
- Refuse overwrite by default.
- `--force` permits overwrite and forces new report generation.
- Write to temporary sibling file, then atomically rename after successful download.
- Preserve UTF-8, quoting, delimiter, columns, row order, and line endings returned by Canvas.

## Compatibility and errors

- Detect non-Classic Quiz objects. Explain New Quizzes report export is unsupported; return non-zero.
- Verify instructor-level report access before report creation where Canvas authorization response permits diagnosis.
- Map Canvas 401, 403, 404, validation, and asynchronous-generation failures to clear errors.
- Never print API tokens, authorization headers, signed attachment URLs, or CSV contents to terminal.

## Acceptance criteria

Against course `74806`, this workflow succeeds for seven remaining Fall 2025 autoevaluaciones after resolving their assignment IDs:

```sh
for assignment in 614873 616448 618813 621808 623863 625931 626694; do
  dauber quizzes reports download --assignment "$assignment" --course 74806 --type student_analysis --output _data/autoevaluaciones/F25/
done
```

Expected files:

- `Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv`
- `Capítulo 3_ Autoevaluación Survey Student Analysis Report.csv`
- `Capítulo 4_ Autoevaluación Survey Student Analysis Report.csv`
- `Capítulo 5_ Autoevaluación Survey Student Analysis Report.csv`
- `Capítulo 6_ Autoevaluación Survey Student Analysis Report.csv`
- `Capítulo 7_ Autoevaluación Survey Student Analysis Report.csv`
- `Capítulo 8_ Autoevaluación Survey Student Analysis Report.csv`

Tests must cover:

- Paginated quiz discovery and assignment-to-quiz resolution.
- Create report, pending polling, completed download, failure, and timeout.
- Reuse vs `--force` behavior.
- Directory filename derivation, exact filename path, overwrite refusal, and atomic write.
- Classic Quiz / New Quiz distinction.
- CSV byte-for-byte preservation from mocked response.
- JSON output with no progress noise on stdout.

## Release notes

Add: “Export Canvas Classic Quiz reports, including Student Analysis CSVs, with asynchronous report generation and safe file output.”
