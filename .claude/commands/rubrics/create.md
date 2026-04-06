---
description: Guided rubric creation and assignment attachment
allowed-tools: Read, Bash, AskUserQuestion
---

# Rubrics: Create — Guided Rubric Creation and Attachment

End-to-end workflow: create a rubric (from CSV, JSON, or interactively)
and optionally attach it to an assignment.

## Step 1: Load Course Parameters

Read `dauber/config.toml` to get `canvas_course_id`.

**If missing**: Report error and tell user to run `/course:setup` first. Stop.

## Step 2: Choose Input Path

Use `AskUserQuestion`:

- "How would you like to provide the rubric?"
- Options:
  - "I have a Canvas CSV file"
  - "I have a JSON file"
  - "Guide me through building one"

## Step 3: Create the Rubric

### CSV path

Run:

```bash
uv run dauber rubrics import --course {canvas_course_id} --csv {path} --format json
```

### JSON path

Run:

```bash
uv run dauber rubrics create --course {canvas_course_id} --file {path} --format json
```

### Guided path

Collect rubric details interactively.

**Round 1**: Ask for the rubric title.

**Round 2+**: For each criterion, ask:

1. "Criterion description (or 'done' to finish):"
2. "Points possible for this criterion:"
3. "How many rating levels? (e.g., 3)"
4. For each rating level: "Rating description and points (e.g., 'Excellent: 25'):"

Repeat until user enters 'done' for the criterion description.

Write the collected data to a temp file `/tmp/rubric_{canvas_course_id}.json`:

```json
{
  "title": "{title}",
  "criteria": [
    {
      "description": "{description}",
      "points": {points},
      "ratings": [
        {"description": "{name}", "points": {pts}},
        ...
      ]
    }
  ]
}
```

Then run:

```bash
uv run dauber rubrics create --course {canvas_course_id} --file /tmp/rubric_{canvas_course_id}.json --format json
```

## Step 4: Capture Rubric ID

Parse the JSON output to extract the created rubric `id` and `title`.

Report to user:

```
Rubric created: {title} (ID: {id})
```

## Step 5: Attach to Assignment

Use `AskUserQuestion`:

- "Attach this rubric to an assignment? Enter the assignment ID, or leave blank to skip."
- Options: ["Skip"]

**If assignment ID provided**, run:

```bash
uv run dauber rubrics attach --course {canvas_course_id} {rubric_id} {assignment_id} --format json
```

Report result:

```
Rubric {rubric_id} attached to assignment {assignment_id}.
```

## Step 6: Next Steps

Suggest:

```
Next steps:
  - View rubric:  uv run dauber rubrics show --course {canvas_course_id} {rubric_id}
  - Start grading: /assess:setup {assignment_id}
```

## Error Handling

- CSV/JSON parse errors: display the error and stop
- Canvas API errors: display the error message and stop
- If attach fails: report error; rubric was still created (show its ID)
