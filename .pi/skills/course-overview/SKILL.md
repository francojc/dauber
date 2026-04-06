---
name: course-overview
description: Pull a comprehensive course status dashboard from Canvas
---

# Course Overview - Status Dashboard

Pull a comprehensive snapshot of the current course and present a formatted
summary.

## Task Overview

Gather course details, module structure, assignments with due dates,
enrollment counts, and upcoming deadlines into a single dashboard view.
This replaces running 3-4 separate dauber commands manually.

## Step 1: Load Course Parameters

Read `dauber/config.toml` to get `canvas_course_id`,
`course_title`, `course_code`, `term`, and `year`.

**If missing**: Report error and tell user to run `/course:setup` first. Stop.

## Step 2: Fetch Course Data

Run all four queries. These are independent and can run in parallel:

### 2a. Course Details

```bash
uv run dauber courses show {canvas_course_id} --format json
```

### 2b. Enrollment

```bash
uv run dauber courses enrollments {canvas_course_id} --format json
```

Count by role: student, teacher, ta, observer.

### 2c. Assignments

```bash
uv run dauber assignments list {canvas_course_id} --format json
```

For each assignment, capture: name, due_at, points_possible, published.

### 2d. Modules

```bash
uv run dauber modules list {canvas_course_id} --items --format json
```

For each module, capture: name, position, published, items_count.

## Step 3: Compute Derived Data

### 3a. Upcoming Deadlines

From the assignments list, filter to assignments where `due_at` is in the
future (after today's date). Sort by due date ascending. Take the next 5.

### 3b. Assignment Statistics

- Total assignments
- Published vs. unpublished count
- Assignments with no due date
- Points possible range (min, max, total)

### 3c. Module Statistics

- Total modules
- Published vs. unpublished count
- Total items across all modules

## Step 4: Display Dashboard

```
Course Dashboard
================

{course_title} ({course_code})
Term: {term} {year} | Canvas ID: {canvas_course_id}

Enrollment
----------
  Students: X | Teachers: Y | TAs: Z | Observers: W

Upcoming Deadlines (next 5)
----------------------------
  1. {assignment_name} - {due_date} ({points} pts)
  2. {assignment_name} - {due_date} ({points} pts)
  ...
  (or "No upcoming deadlines" if none)

Assignments ({total})
---------------------
  Published: X | Unpublished: Y | No due date: Z
  Points range: {min} - {max} pts

  All assignments:
  - {name} | Due: {due_at or "none"} | {points} pts | {published}
  - ...

Modules ({total})
-----------------
  Published: X | Unpublished: Y
  Total items: Z

  - {module_name} ({items_count} items) {published_status}
  - ...
```

## Error Handling

- If dauber/config.toml missing: Report error, direct to `/course:setup`
- If any Canvas fetch fails: Report the error for that section, continue
  with remaining sections (partial dashboard is better than none)
- If course has no assignments or modules: Display "None" for those sections

Begin overview now.
