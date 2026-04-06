---
description: Initialize Canvas assignment grading workflow and create assessment JSON file
args:
  - name: assignment_id
    description: Canvas assignment ID (auto-discovers if not provided)
    required: false
argument-hint: <Canvas assignment ID>
allowed-tools: Read, Write, AskUserQuestion, Bash, Glob
---

# Assessment Setup - Initialize Grading Workflow

Initialize the grading workflow for Canvas assignment {{assignment_id}}.

## Task Overview

Create the assessment JSON file with all student submissions and rubric structure, ready for AI evaluation.

## Step 1: Validate dauber/config.toml

Check for `dauber/config.toml` in the current repository.

**If missing**: Use `AskUserQuestion` to collect all fields, then create the file:

```toml
course_title = "Exploring the Hispanic World"
course_code = "SPA-212-T"
canvas_course_id = 79384
term = "Spring"
year = 2026
level = "undergraduate"
feedback_language = "Spanish"
language_learning = true
language_level = "ACTFL Intermediate Mid"
formality = "casual"
anonymize = true
```

Notes on field values:

- `level` specifies the educational setting: "undergraduate", "graduate", "professional", etc. This informs the depth and rigor of feedback expectations.
- `formality` controls tone across all feedback: "casual" or "formal". For Spanish courses, "casual" implies tú and "formal" implies usted. For English feedback, "casual" means academic casual tone and "formal" means standard academic tone.
- `language_learning: false` means `language_level` should be `"NA"`
- `feedback_language` accepts full names ("Spanish", "English")
- `anonymize` controls FERPA-compliant PII stripping: when `true`, student names and emails are blanked in the assessment JSON. The numeric `user_id` is retained for grade submission. Default `false`.

**If present**: Parse TOML and validate all fields are populated. If any field is missing, prompt user for the missing values and update the file.

**Extract values for downstream use**:

- `canvas_course_id` becomes the `course_id` for all Canvas API calls
- Map `feedback_language` to language code: "Spanish" → `"es"`, "English" → `"en"`
- `level` carries through to metadata for agent context

## Step 2: Generate Assessment Structure

Fetch data from Canvas using the dauber CLI, then construct the assessment file.

### 2a. Run dauber assess setup

Use the Bash tool to run the dauber CLI:

```bash
uv run dauber assess setup {canvas_course_id} {assignment_id} \
  --course-name "{course_title}" \
  --level "{level}" \
  --feedback-language "{feedback_language_code}" \
  --language-learning \
  --language-level "{language_level}" \
  --formality "{formality}" \
  --exclude-graded \
  --anonymize \
  --format json
```

Notes:

- `{canvas_course_id}` comes from `dauber/config.toml`
- `{assignment_id}` is the argument passed to this command
- Only include `--language-learning` if `language_learning: true` in dauber/config.toml
- Only include `--anonymize` if `anonymize: true` in dauber/config.toml
- `--feedback-language` uses the mapped code ("es" or "en")
- `--exclude-graded` skips already-graded submissions (default behavior)
- `--format json` returns structured output for parsing

The CLI will:

- Fetch assignment details, rubric structure, and student submissions
- Build the assessment JSON combining all three data sources
- Save to `.claude/assessments/{course_id}_{assignment_id}_{timestamp}.json`
- Return a JSON summary with the file path and statistics

### 2b. Parse CLI Output

Extract from the JSON response:

- `file`: path to the created assessment file
- `course_id`: resolved course ID
- `assignment`: assignment name
- `points_possible`: total points
- `submissions`: number of submissions
- `criteria`: number of rubric criteria

### 2c. Read the Created Assessment File

Use the Read tool to load the assessment file created by the CLI. This gives you access to the full assessment structure including:

- Assignment instructions (prompt)
- Complete rubric with criteria and ratings
- All student submissions with extracted text
- Metadata fields

## Step 3: Display Summary

Read the assessment file and report the following information:

```
Assessment Setup Complete
========================

Course: {course_title} ({course_code})
Level: {level}
Term: {term} {year}
Feedback Language: {feedback_language}

Assignment: [assignment name]
Due Date: [due date]
Points Possible: [total points]

Course Enrollment: X students enrolled in this course

Submissions Found: Y students
- On time: A students
- Late: B students
- Already graded: C students (excluded by default)
- No submission: D students (skipped)
  Student IDs: [list of student IDs with no submissions]

Assignment Prompt: Captured ({word_count} words)

Rubric Structure:
- Number of criteria: [count]
- Total points: [points]
- Criteria overview:
  1. [criterion 1 name] - [max points] pts
  2. [criterion 2 name] - [max points] pts
  ...

Assessment File Created:
  assessments_{course_id}_{assignment_id}_{timestamp}.json

Note: Already-graded submissions were excluded to prevent overwriting existing grades.

Next Steps:
  Run `/assess:ai-pass` to begin AI evaluation of submissions
```

## Step 4: Save State

Create `.claude/state/assessment_state.json` with:

```json
{
  "last_assessment_file": "assessments_{course_id}_{assignment_id}_{timestamp}.json",
  "course_id": "{course_id}",
  "assignment_id": "{assignment_id}",
  "created_at": "{timestamp}",
  "total_submissions": X
}
```

This allows subsequent commands to auto-discover the assessment file.

## Error Handling

- If course_id or assignment_id invalid: Report error and ask user to verify
- If no submissions found: Report warning but create file anyway
- If rubric not found: Report error - assignment must have rubric for this workflow
- If file already exists: Ask user if they want to overwrite or use existing file

## Important Notes

- Supports `online_upload` submission types with automatic text extraction from DOCX and PDF files
- Supports `online_text_entry` submission types
- Automatically skips students who haven't submitted
- **Excludes already-graded submissions by default** to prevent overwriting existing grades
- **FERPA COMPLIANCE: Enrollment filtering enabled** - Only includes submissions from students enrolled in the specified course, preventing cross-section contamination in cross-listed assignments
- **FERPA COMPLIANCE: PII anonymization** - When `anonymize: true` in dauber/config.toml, student names and emails are stripped from the assessment JSON. The numeric `user_id` is retained for grade submission back to Canvas
- Creates fresh assessment file each time (timestamped to avoid conflicts)
- Preserves all rubric details for AI evaluation step

Begin setup now.
