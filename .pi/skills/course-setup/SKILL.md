---
name: course-setup
description: Initialize course workspace with config, connectivity check, and course parameters
---

# Course Setup - Initialize Course Workspace

Guide the user through first-time course configuration, validate Canvas
connectivity, and create `dauber/config.toml`.

## Task Overview

Set up the local workspace for a Canvas course. This chains together config
initialization, course detail retrieval, enrollment verification, and
parameter file creation so that all downstream workflows have valid context.

## Step 1: Check Existing Configuration

Look for `dauber/config.toml` in the current repository.

**If present**: Read and display current values. Use `AskUserQuestion` to ask:

- "Course parameters already exist. What would you like to do?"
- Options: ["Reconfigure from scratch", "Update specific fields", "Keep existing and verify connectivity"]

If keeping existing, skip to Step 3. If updating, ask which fields to change
and update the file, then continue to Step 3.

**If missing**: Continue to Step 2.

## Step 2: Collect Course Parameters

### 2a. Test Canvas Connectivity

Run a quick connectivity check:

```bash
uv run dauber --test
```

If this fails, report the error and tell the user to verify `CANVAS_API_KEY`
and `CANVAS_BASE_URL` environment variables are set. Do not read `.env` files.
Stop here until connectivity is confirmed.

### 2b. List Available Courses

Fetch the user's courses to help them identify the right one:

```bash
uv run dauber courses list --format json
```

Display the results as a readable list showing course code, name, and term.

### 2c. Collect Course Selection

Use `AskUserQuestion` to ask the user to identify their course. Present the
top courses from the list as options. Include an "Other" path for entering a
course code or ID directly.

### 2d. Fetch Course Details

Once the user selects a course, fetch full details:

```bash
uv run dauber courses show {course_identifier} --format json
```

Extract: `id`, `course_code`, `name`, and `term` (from `enrollment_term_id`
or `term` field if present).

### 2e. Collect Remaining Parameters

Use `AskUserQuestion` to collect fields not derivable from Canvas. Ask up to
four questions across one or two rounds:

1. **Educational level**: "What level is this course?"
   - Options: ["undergraduate", "graduate", "professional"]

2. **Feedback language**: "What language should feedback be written in?"
   - Options: ["English", "Spanish"]

3. **Language learning course?**: "Is this a language learning course?"
   - Options: ["Yes", "No"]

4. **If language learning = Yes**: "What is the expected proficiency level?"
   - Options: ["ACTFL Novice Mid", "ACTFL Intermediate Low", "ACTFL Intermediate Mid", "ACTFL Intermediate High"]

5. **Formality**: "What tone should feedback use?"
   - Options: ["casual (tú / conversational)", "formal (usted / academic)"]

6. **Anonymize**: "Strip student names and emails from assessment files (FERPA compliance for LLM workflows)?"
   - Options: ["Yes", "No"]

For non-language-learning courses, set `language_level: "NA"`.

### 2f. Write dauber/config.toml

Create `dauber/config.toml` with all collected values:

```toml
course_title = "{course_name}"
course_code = "{course_code}"
canvas_course_id = {course_id}
term = "{term}"
year = {current_year}
level = "{level}"
feedback_language = "{feedback_language}"
language_learning = {true_or_false}
language_level = "{language_level}"
formality = "{formality}"
anonymize = {true_or_false}
```

## Step 3: Verify Course Access

### 3a. Fetch Enrollment Summary

```bash
uv run dauber courses enrollments {canvas_course_id} --format json
```

Count enrollments by role (student, teacher, ta, observer).

### 3b. Fetch Assignment Overview

```bash
uv run dauber assignments list {canvas_course_id} --format json
```

Count total assignments and note how many are published.

### 3c. Fetch Module Overview

```bash
uv run dauber modules list {canvas_course_id} --format json
```

Count total modules.

## Step 4: Display Summary

```
Course Setup Complete
=====================

Course: {course_title} ({course_code})
Canvas ID: {canvas_course_id}
Term: {term} {year}
Level: {level}
Feedback Language: {feedback_language}
Formality: {formality}

Enrollment:
  Students: X
  Teachers: Y
  TAs: Z

Course Content:
  Assignments: A (B published)
  Modules: C

Parameters saved to: dauber/config.toml

Available workflows:
  /course:overview  - Course status dashboard
  /content:publish  - Publish local content to Canvas
  /assign:create    - Create assignments with guided defaults
  /grade:overview   - Grade distribution analysis
  /discuss:announce - Draft and post announcements
  /assess:setup     - Initialize rubric-based assessment grading
```

## Error Handling

- If Canvas connectivity fails: Report error, ask user to check environment variables
- If course not found: Report error with available courses list
- If enrollment fetch fails: Report warning but continue (non-critical)
- If `dauber/` directory missing: Create it before writing config file

Begin setup now.
