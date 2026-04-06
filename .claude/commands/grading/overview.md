---
description: Grade distribution analysis with score statistics and missing submission tracking
args:
  - name: assignment_id
    description: Canvas assignment ID (if omitted, shows overview across all assignments)
    required: false
argument-hint: "[assignment_id]"
allowed-tools: Read, Bash, Glob
---

# Grading Overview - Grade Distribution Analysis

Fetch submissions and compute score distributions for one or all assignments.

## Task Overview

Pull submission data from Canvas, compute statistical summaries (mean, median,
range, quartiles), identify missing submissions, and present a formatted
report. Provides analytics not available in the Canvas UI.

## Step 1: Load Course Parameters

Read `dauber/config.toml` to get `canvas_course_id` and
`course_title`.

**If missing**: Report error and tell user to run `/course:setup` first. Stop.

## Step 2: Fetch Assignment Data

### If assignment_id provided:

Fetch submissions for the specific assignment:

```bash
uv run dauber grading submissions {canvas_course_id} {{assignment_id}} --format json
```

Also fetch assignment details for context:

```bash
uv run dauber assignments show {canvas_course_id} {{assignment_id}} --format json
```

### If no assignment_id provided:

Fetch all assignments first:

```bash
uv run dauber assignments list {canvas_course_id} --format json
```

Then fetch submissions for each assignment that has a due date in the past
or has existing submissions. For efficiency, limit to published assignments.
Fetch sequentially to avoid rate limiting:

```bash
uv run dauber grading submissions {canvas_course_id} {assignment_id} --format json
```

## Step 3: Compute Statistics

For each assignment's submissions:

### 3a. Score Distribution

From submissions where `score` is not null:

- **Count**: number of graded submissions
- **Mean**: average score
- **Median**: middle value
- **Std Dev**: standard deviation
- **Min / Max**: range
- **Q1 / Q3**: first and third quartiles

### 3b. Submission Status

Categorize all submissions by `workflow_state`:

- **Graded**: has a score
- **Submitted**: submitted but not yet graded
- **Unsubmitted**: no submission
- **Late**: submitted after due date

### 3c. Score Brackets

Group scores into brackets relative to points_possible:

- A (90-100%)
- B (80-89%)
- C (70-79%)
- D (60-69%)
- F (below 60%)

Count students in each bracket.

## Step 4: Display Report

### Single Assignment Report

```
Grade Distribution: {assignment_name}
=====================================

Course: {course_title} ({course_code})
Assignment ID: {assignment_id}
Points Possible: {points_possible}
Due Date: {due_date}

Submission Status
-----------------
  Total enrolled: X
  Submitted: Y (Z graded, W pending)
  Missing: M students
    IDs: {list of user_ids with no submission}
  Late: L students

Score Statistics (N = {graded_count})
-------------------------------------
  Mean:   {mean:.1f} / {points_possible} ({pct:.0f}%)
  Median: {median:.1f} / {points_possible}
  Std Dev: {std:.1f}
  Range:  {min:.1f} - {max:.1f}
  Q1:     {q1:.1f} | Q3: {q3:.1f}

Score Distribution
------------------
  A (90-100%): {count} students  {"#" * count}
  B (80-89%):  {count} students  {"#" * count}
  C (70-79%):  {count} students  {"#" * count}
  D (60-69%):  {count} students  {"#" * count}
  F (< 60%):   {count} students  {"#" * count}
```

### Multi-Assignment Summary

```
Grade Overview: {course_title}
==============================

{total_assignments} assignments analyzed

Assignment Summary
------------------
  {name:<30} | Mean     | Median   | Graded | Missing
  -----------+----------+----------+--------+--------
  {name}     | {mean}   | {median} | {n}    | {m}
  ...

Assignments Needing Attention
-----------------------------
  - {assignment}: {missing_count} missing submissions
  - {assignment}: {ungraded_count} submitted but ungraded
  - {assignment}: mean below 70% ({mean}%)
```

## Error Handling

- If dauber/config.toml missing: Direct to `/course:setup`
- If assignment not found: Report error with the ID attempted
- If no submissions exist: Report "No submissions yet" rather than empty stats
- If Canvas API rate limited: Wait briefly and retry (up to 3 attempts)

Begin grade analysis now.
