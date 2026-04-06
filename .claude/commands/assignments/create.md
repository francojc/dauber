---
description: Guided assignment creation with sensible defaults and parameter validation
allowed-tools: Read, Bash, AskUserQuestion
---

# Assignment Create - Guided Assignment Creation

Walk through assignment creation with interactive parameter collection,
sensible defaults, and validation.

## Task Overview

Collect assignment details interactively, validate inputs, create the
assignment via the dauber CLI, and report the result. Provides guardrails
for common mistakes like missing submission types or forgetting to publish.

## Step 1: Load Course Parameters

Read `dauber/config.toml` to get `canvas_course_id` and
`course_title`.

**If missing**: Report error and tell user to run `/course:setup` first. Stop.

## Step 2: Collect Assignment Details

Use `AskUserQuestion` across multiple rounds to gather parameters. Group
related questions together (max 4 per round).

### Round 1: Core Details

1. **Assignment name**: "What is the assignment name?"
   - Free text (use "Other" option path)

2. **Points possible**: "How many points is this assignment worth?"
   - Options: ["10", "25", "50", "100"]

3. **Due date**: "When is this assignment due? (ISO 8601 format, e.g., 2026-03-15T23:59:00Z)"
   - Options: ["No due date"]
   - Otherwise free text via "Other"

### Round 2: Submission and Publishing

4. **Submission types**: "What submission types should be allowed?"
   - Options:
     - "online_text_entry (Recommended)"
     - "online_upload"
     - "online_text_entry,online_upload"
     - "none (no submission)"

5. **Publish immediately?**: "Should this assignment be published now?"
   - Options:
     - "Yes - publish immediately"
     - "No - save as draft"

## Step 3: Confirm Before Creating

Display a confirmation summary:

```
Assignment Preview
==================

Course: {course_title} ({canvas_course_id})
Name: {assignment_name}
Points: {points_possible}
Due: {due_date or "No due date"}
Submission Types: {types}
Publish: {Yes/No}
```

Use `AskUserQuestion`:

- "Create this assignment?"
- Options: ["Yes - create it", "Edit details", "Cancel"]

If "Edit details", return to Step 2 and let the user change specific fields.

## Step 4: Create Assignment

Build and run the CLI command:

```bash
uv run dauber assignments create {canvas_course_id} "{assignment_name}" \
  --points {points_possible} \
  --due "{due_date}" \
  --types "{submission_types}" \
  --publish \
  --format json
```

Notes:

- Omit `--due` if no due date selected
- Omit `--publish` if saving as draft
- Omit `--types` if not specified (Canvas defaults apply)
- Quote the assignment name to handle spaces

Parse the JSON response to extract the created assignment's `id`, `name`,
`html_url`, and `published` status.

## Step 5: Rubric Guidance

Use `AskUserQuestion`:

- "Does this assignment need a rubric?"
- Options: ["Yes", "No"]

**If yes**: Run the `/rubrics:create` skill now.
It will guide rubric creation and offer to attach it to this assignment
(ID: {assignment_id}).

## Step 6: Display Summary

```
Assignment Created
==================

Course: {course_title} ({course_code})
Assignment: {assignment_name}
ID: {assignment_id}
Points: {points_possible}
Due: {due_date or "No due date"}
Submission Types: {types}
Published: {Yes/No}

To view:
  uv run dauber assignments show {canvas_course_id} {assignment_id}

To update later:
  uv run dauber assignments update {canvas_course_id} {assignment_id} --name "..." --points ...

Next steps:
  - Add a rubric in Canvas UI if needed
  - Run /assess:setup {assignment_id} to start grading workflow
```

## Error Handling

- If dauber/config.toml missing: Direct to `/course:setup`
- If assignment creation fails: Report the Canvas API error
- If invalid date format: Ask user to re-enter in ISO 8601 format
- If duplicate assignment name: Warn but proceed (Canvas allows duplicates)

Begin assignment creation now.
