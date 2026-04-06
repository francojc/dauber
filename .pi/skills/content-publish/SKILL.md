---
name: content-publish
description: Publish a local Markdown or HTML file as a Canvas page, optionally adding it to a module
---

# Content Publish - Push Local Content to Canvas

Publish a local Markdown or HTML file as a Canvas page, with optional
module placement.

## Task Overview

Read a local file, create or update the corresponding Canvas page, and
optionally add it to a module. This bridges local authoring (Markdown,
Quarto output) with Canvas publishing.

## Step 1: Load Course Parameters

Read `dauber/config.toml` to get `canvas_course_id`.

**If missing**: Report error and tell user to run `/course:setup` first. Stop.

## Step 2: Read and Prepare Content

### 2a. Read the Source File

Use the Read tool to load `{{file_path}}`.

**If file not found**: Report error and stop.

Detect file type from extension:

- `.md` / `.markdown`: Markdown content, will need conversion
- `.html`: HTML content, use as-is for page body
- `.qmd`: Quarto source; warn user to render first (`quarto render`)
  and provide the `.html` output path instead

### 2b. Convert Markdown to HTML (if needed)

If the source is Markdown, convert it to HTML. Check if `pandoc` is available:

```bash
which pandoc
```

If available, convert:

```bash
pandoc "{file_path}" -f markdown -t html --no-highlight
```

Capture the HTML output as the page body.

If `pandoc` is not available, pass the raw Markdown as the page body. Canvas
renders Markdown in some contexts but HTML is preferred. Warn the user that
HTML conversion is recommended.

### 2c. Extract Title

Derive the page title from (in order of preference):

1. First `# ` heading in the file
2. YAML frontmatter `title` field (if present)
3. Filename without extension (e.g., `syllabus.md` -> "Syllabus")

## Step 3: Check for Existing Page

Search Canvas for a page with the same title:

```bash
uv run dauber pages list {canvas_course_id} --search "{title}" --format json
```

**If a matching page exists**: Use `AskUserQuestion` to ask:

- "A page titled '{title}' already exists. What would you like to do?"
- Options: ["Update existing page", "Create new page with different title", "Cancel"]

If updating, use the existing page's URL slug for the update command.
If creating with a different title, ask for the new title.

## Step 4: Create or Update Page

### 4a. Create New Page

```bash
uv run dauber pages create {canvas_course_id} "{title}" \
  --body "{html_content}" \
  --publish \
  --format json
```

Note: if the HTML content is long, write it to a temporary file and use
command substitution or pass it via stdin to avoid shell argument limits.
For long content, write to a temp file first:

```bash
uv run dauber pages create {canvas_course_id} "{title}" \
  --body "$(cat /tmp/dauber_page_body.html)" \
  --publish \
  --format json
```

### 4b. Update Existing Page

```bash
uv run dauber pages update {canvas_course_id} "{page_url_slug}" \
  --body "{html_content}" \
  --publish \
  --format json
```

Extract the page URL from the response.

## Step 5: Optional Module Placement

Use `AskUserQuestion` to ask:

- "Add this page to a module?"
- Options: ["Yes - select a module", "No - done"]

**If yes**:

### 5a. List Modules

```bash
uv run dauber modules list {canvas_course_id} --format json
```

Present modules as options via `AskUserQuestion`. Let the user select one.

### 5b. Add Page to Module

The Canvas API requires adding a module item. This is not directly supported
by the current dauber CLI module commands. Report this to the user:

```
Note: Module item addition requires the Canvas API module items endpoint,
which is not yet implemented in the dauber CLI. To add this page to the
module, use the Canvas web interface:

  1. Navigate to the module in Canvas
  2. Click "+" to add an item
  3. Select "Page" and choose "{title}"
```

## Step 6: Display Summary

```
Content Published
=================

Source: {file_path}
Format: {markdown|html}
Title: {title}
Action: {Created|Updated}

Canvas Page URL: {page_url}
Published: Yes

{If module placement attempted:}
Module: {module_name or "Not added (manual step required)"}

To view the page:
  uv run dauber pages show {canvas_course_id} "{page_url_slug}"
```

## Error Handling

- If file not found: Report error with the path attempted
- If Canvas page creation fails: Report the API error
- If content too large for shell argument: Use temp file approach
- If pandoc not available: Warn and proceed with raw Markdown

Begin publishing now.
