---
description: Use pedagogy agent to evaluate all submissions with AI-generated assessments
args:
  - name: course_id
    description: Canvas course ID (auto-discovers from state if not provided)
    required: false
  - name: assignment_id
    description: Canvas assignment ID (auto-discovers from state if not provided)
    required: false
allowed-tools: Read, Write, Bash, Glob, Task, AskUserQuestion
---

# AI Preliminary Assessment - Evaluate Submissions

Use the appropriate pedagogy agent to evaluate all student submissions and populate the assessment JSON file.

## Task Overview

Process each submission chronologically, using the agent to provide rubric-based evaluation with concise feedback in the assignment's feedback language (from `metadata.feedback_language` in the assessment JSON).

## Step 1: Locate Assessment File

**If course_id and assignment_id provided**:

- Look for `.claude/assessments/{{course_id}}_{{assignment_id}}_*.json` in the current repository
- Use most recent file matching that pattern

**If no arguments provided**:

- Check `.claude/state/assessment_state.json` for last used file
- If state file exists, use that assessment file
- If not found, search for `assessments_*.json` and use most recent
- If no files found, report error and tell user to run `/assess:setup` first

Load the assessment file using the Read tool.

## Step 2: Process Each Submission

For each student in the assessment file who has submitted (process in chronological order by submission time):

1. **Check if already evaluated**:
   - Skip if assessment already has scores (don't re-evaluate)
   - Report: "Skipping user {user_id} - already evaluated"

2. **Select agent based on `metadata.language_learning`**:
   - If `true`: use `spanish-pedagogy-expert` agent via Task tool
   - If `false`: use `pedagogy-expert` agent via Task tool

   **Launch the selected agent** with this prompt:

```
You are evaluating a student's submission for a {level} course.

Feedback language: {feedback_language} (write ALL feedback in this language)
Formality: {formality}

## Student Submission

User ID: {user_id}
Submission Time: {submitted_at}
Word Count: {word_count}

### Submission Text:
{submission_text}

## Assignment Prompt

The following is the assignment prompt that the student was asked to respond to. Use this as essential context when applying rubric criteria — it defines the task the student was expected to complete.

{assignment_instructions_from_metadata}

## Rubric Criteria

You must evaluate this submission against the rubric criteria. For EACH criterion, provide:
- Points awarded (based on rating levels, half-points acceptable)
- Rating ID (the specific ID matching the points)
- Concise feedback (`justification`) in {feedback_language_name} (EXACTLY 15-20 words)
- A final summary of all criteria at the end in the overall comments section.

{full_rubric_details_here}

## Your Task

Provide your assessment in this EXACT format:

**CRITERION: {criterion_name} [{criterion_id}]**
Points: {points_awarded}
Rating ID: {rating_id}
Justification: {15-20 word feedback in {feedback_language_name} focusing ONLY on main positive/negative attributes}
Overall Comments: {final summary of all criteria in {feedback_language_name}, 30-40 words}

## Feedback Requirements

- EXACTLY 15-20 words in {feedback_language_name} per criterion
- Focus ONLY on the main strength OR weakness (not both if space-constrained)
- Use clear, comprehensible phrases (need not be complete sentences)
- Directly address the specific criterion
- Provide actionable insight

*Note: no need to report the word count in your feedback, only mention it if the student's submission is very short or very long.*

## Evaluation Guidelines

- Use the assignment prompt as essential context: it defines what the student was asked to do and informs how rubric criteria should be applied to this specific submission
- Use the language of the rubric levels to guide your scoring and justification feedback
- Be lenient in applying rubric criteria and lean toward higher points when borderline
- Use partial credit when appropriate
- Ensure feedback helps student understand the assessment

### Language-specific guidelines

**If language_learning is true (language course)**:
- Value attempts at grammatical and lexical complexity; do not penalize these
- Consider this is a language course ({language_level} proficiency expected)
- Apply formality setting: if "casual", use tú (Spanish) or conversational academic tone (English); if "formal", use usted (Spanish) or standard academic tone (English)
- Calibrate feedback depth and vocabulary to the {level} setting
- Tone: supportive and encouraging, motivating the student to improve their language skills

**If language_learning is false (non-language course)**:
- Evaluate content, reasoning, and adherence to assignment requirements
- Apply formality setting: if "casual", use a conversational academic tone; if "formal", use standard academic tone
- Calibrate feedback depth and expectations to the {level} setting
- Tone: constructive and professional, motivating the student to improve

## Final Summary

- Summarize the individual criterion ratings and justification comments in the overall comments section.
- Provide praise for strengths and constructive suggestions for improvement.
- Write the summary in {feedback_language_name}.

The tone for all written feedback should be supportive and encouraging, directed at the student.

Provide complete assessment for all criteria now.
```

3. **Parse agent response** to extract:
   - Points for each criterion
   - Rating ID for each criterion
   - 15-20 word feedback for each criterion (in the feedback language)
   - Overall comments summary

4. **Validate agent output**:
   - Verify all criteria have assessments
   - Check that rating IDs match the rubric structure
   - Count words in each feedback (must be 15-20)
   - Verify feedback is in the correct language (matches `metadata.feedback_language`)

5. **Save assessment** using the dauber CLI via Bash:

   ```bash
   uv run dauber assess update {assessment_file_path} {user_id} \
     --rubric-json '{"criterion_id": {"points": X, "justification": "..."}, ...}' \
     --comment "Overall comment text" \
     --reviewed \
     --format json
   ```

   Notes on shell quoting:
   - Single-quote the `--rubric-json` value to prevent shell expansion
   - If the JSON value itself contains single quotes, use `$'...'` quoting or escape them
   - The `--reviewed` flag marks as reviewed by AI
   - Do NOT include `--approved` (requires human review before submission)

6. **Report progress**:

   ```
   Evaluated User {user_id} - {total_points}/{points_possible} pts
     [{criterion1}: {pts1}, {criterion2}: {pts2}, ...]
   ```

## Step 3: Display Summary

After processing all submissions, report:

```
AI Preliminary Assessment Complete
===================================

Submissions Evaluated: X/Y
- Newly evaluated: X students
- Previously evaluated (skipped): Y students
- No submission (skipped): Z students
- Already graded in Canvas (excluded during setup): A students

Score Distribution:
  Average: {avg} / {points_possible} pts
  Range: {min} - {max} pts

  Criterion Averages:
  - {criterion1}: {avg1} / {max1} pts
  - {criterion2}: {avg2} / {max2} pts
  - ...
  (list all criteria from rubric)

Assessment File Updated:
  {assessment_file_path}

Status:
  All assessments marked as "reviewed"
  None marked as "approved" yet

Note: Already-graded submissions were excluded during setup to prevent overwriting.

Next Steps:
  1. Review the assessment file manually
  2. Edit any assessments as needed using review tools or JSON editing
  3. Mark assessments as "approved" when ready
  4. Run `/assess:submit` to submit approved grades to Canvas
```

## Error Handling

- If agent fails to evaluate: Report error, continue with next student
- If feedback not 15-20 words: Report warning, ask agent to revise
- If feedback in wrong language: Report warning, ask agent to revise
- If rating ID invalid: Report error, ask agent to provide valid ID
- If assessment file not found: Report error, tell user to run `/assess:setup`

## Important Notes

- Process submissions chronologically (earliest first)
- Skip students without submissions (already filtered by setup)
- **Already-graded submissions excluded during setup** to prevent overwriting Canvas grades
- Never overwrite existing assessments (skip if already evaluated)
- All assessments marked as "reviewed" but NOT "approved"
- Human review required before submission to Canvas
- Agent selection is based on `metadata.language_learning`: `spanish-pedagogy-expert` for language courses, `pedagogy-expert` for non-language courses

Begin AI evaluation now.
