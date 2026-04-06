---
description: Draft and post a course announcement with AI-assisted writing and tone matching
args:
  - name: topic
    description: Topic or rough notes for the announcement
    required: true
argument-hint: <topic or notes>
allowed-tools: Read, Bash, AskUserQuestion
---

# Announce - Draft and Post Announcement

Draft a course announcement with AI assistance and post it to Canvas after
user approval.

## Task Overview

Take a topic or rough notes, draft an announcement matching the course's
tone and formality settings, present it for approval and editing, then post
via the dauber CLI. Keeps the instructor in the loop while saving time on
routine communications.

## Step 1: Load Course Parameters

Read `dauber/config.toml` to get `canvas_course_id`,
`course_title`, `course_code`, `feedback_language`, and `formality`.

**If missing**: Report error and tell user to run `/course:setup` first. Stop.

## Step 2: Gather Context

### 2a. Parse the Topic Input

The user provides `{{topic}}` which may be:

- A brief topic phrase (e.g., "deadline reminder for essay 2")
- Rough bullet points or notes
- A specific request (e.g., "class cancelled Thursday")

### 2b. Fetch Recent Announcements (for tone reference)

```bash
uv run dauber discussions list {canvas_course_id} --announcements --format json
```

If there are recent announcements, note their titles and style to maintain
consistency. Do not display these to the user unless asked.

## Step 3: Draft the Announcement

Using the topic input, course context, and formality setting, draft the
announcement. Follow these guidelines:

**Title**: Short, clear subject line (under 60 characters).

**Body**: Write in the language specified by `feedback_language`.

- **If formality = "casual"**: Conversational tone, direct address ("Hi
  everyone"), contractions OK. For Spanish: use tú/ustedes.
- **If formality = "formal"**: Professional academic tone, no contractions.
  For Spanish: use usted/ustedes formal.

**Content structure**:

- Open with the key information (what students need to know)
- Provide context or details in the middle
- Close with any action items or deadlines
- Keep it concise: 50-150 words for routine announcements

**Do not**:

- Use AI-tell words (delve, crucial, leverage, robust, nuanced)
- Use stock phrases (rich tapestry, pave the way, at its core)
- Use moreover/furthermore/additionally as paragraph openers
- Add emojis unless the user's topic notes include them

## Step 4: Present Draft for Approval

Display the drafted announcement clearly:

```
Announcement Draft
==================

Title: {title}
Language: {feedback_language}
Tone: {formality}

---
{announcement_body}
---
```

Use `AskUserQuestion`:

- "How does this draft look?"
- Options: ["Post as-is", "Edit the draft", "Start over with different approach", "Cancel"]

**If "Edit the draft"**: Ask the user what changes they want. Revise and
present the updated draft again. Repeat until approved or cancelled.

**If "Start over"**: Ask for new direction and return to Step 3.

## Step 5: Post to Canvas

Once approved, post the announcement:

```bash
uv run dauber discussions create {canvas_course_id} "{title}" \
  --message "{announcement_body}" \
  --announcement \
  --publish \
  --format json
```

Notes:

- The `--announcement` flag creates it as an announcement rather than a
  discussion topic
- The `--publish` flag makes it immediately visible
- If the body contains quotes or special characters, handle shell escaping
  carefully. For long bodies, write to a temp file and use command substitution.

Parse the JSON response to extract the announcement `id` and `posted_at`.

## Step 6: Display Summary

```
Announcement Posted
===================

Course: {course_title} ({course_code})
Title: {title}
Posted: {posted_at}
ID: {announcement_id}

The announcement is now visible to all enrolled students.

To view:
  uv run dauber discussions show {canvas_course_id} {announcement_id}

To edit later:
  uv run dauber discussions update {canvas_course_id} {announcement_id} --message "..."
```

## Error Handling

- If dauber/config.toml missing: Direct to `/course:setup`
- If posting fails: Report the Canvas API error, offer to retry or save
  the draft text so the user doesn't lose it
- If shell escaping issues with body text: Write body to temp file and use
  `$(cat /tmp/dauber_announcement.html)` pattern

Begin drafting now.
