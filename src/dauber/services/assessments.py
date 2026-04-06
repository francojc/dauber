"""Assessment service — build, load, save, update, and submit assessments."""

from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import docx
import httpx
from pypdf import PdfReader

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.assignments import _strip_html
from dauber.services.grading import submit_rubric_grade


def _extract_docx_text(data: bytes) -> str:
    doc = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _normalize_extracted_text(text: str) -> str:
    """Collapse whitespace artifacts from PDF/DOCX extraction.

    Converters often emit a newline (or newline + space) between every token.
    Collapse those runs into a single space, then restore paragraph breaks
    (two or more consecutive blank lines → one blank line).
    """
    # Replace sequences of whitespace that contain at least one newline with a
    # single space, UNLESS the sequence contains two or more newlines (a real
    # paragraph break).
    text = re.sub(r"(?<!\n)\n[ \t]*(?!\n)", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    # Normalize paragraph breaks to a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_pdf_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            parts.append(t)
    return _normalize_extracted_text("\n".join(parts))


async def _extract_attachment_text(client: CanvasClient, attachment: dict) -> str:
    """Download one Canvas attachment and return its plain text."""
    content_type = attachment.get("content-type", "")
    url = attachment.get("url", "")
    filename = attachment.get("filename", "")
    if not url:
        return f"[attachment: {filename} — no download URL]"
    try:
        data = await client.download(url)
    except Exception as exc:
        return f"[attachment: {filename} — download failed: {exc}]"
    if "wordprocessingml" in content_type or filename.endswith(".docx"):
        try:
            return _extract_docx_text(data)
        except Exception as exc:
            return f"[attachment: {filename} — DOCX parse failed: {exc}]"
    if content_type == "application/pdf" or filename.endswith(".pdf"):
        try:
            return _extract_pdf_text(data)
        except Exception as exc:
            return f"[attachment: {filename} — PDF parse failed: {exc}]"
    return f"[attachment: {filename} ({content_type}) — text extraction not supported]"


async def fetch_assignment_with_rubric(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
) -> dict[str, Any]:
    """Fetch assignment details with embedded rubric.

    Returns dict with assignment metadata and rubric criteria.
    Raises CanvasError if assignment has no rubric attached.
    """
    try:
        a = await client.request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}",
            params={"include[]": ["rubric", "rubric_settings"]},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get assignment {assignment_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    rubric_data = a.get("rubric")
    if not rubric_data:
        raise CanvasError(
            f"Assignment {assignment_id} has no rubric attached. "
            "The assessment workflow requires a rubric.",
        )

    criteria: dict[str, Any] = {}
    total_points = 0.0
    for c in rubric_data:
        cid = c.get("id", "")
        max_pts = c.get("points", 0)
        total_points += max_pts
        criteria[cid] = {
            "description": c.get("description", ""),
            "max_points": max_pts,
            "ratings": [
                {
                    "id": rt.get("id", ""),
                    "description": rt.get("description", ""),
                    "points": rt.get("points", 0),
                }
                for rt in c.get("ratings", [])
            ],
        }

    discussion = a.get("discussion_topic") or {}
    discussion_topic_id = str(discussion["id"]) if discussion.get("id") else None

    return {
        "assignment_id": a["id"],
        "assignment_name": a.get("name", ""),
        "description": _strip_html(a.get("description", "") or ""),
        "due_at": a.get("due_at", ""),
        "points_possible": a.get("points_possible", 0),
        "discussion_topic_id": discussion_topic_id,
        "rubric": {
            "total_points": total_points,
            "criteria_count": len(criteria),
            "criteria": criteria,
        },
    }


async def fetch_submissions_with_content(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    *,
    exclude_graded: bool = True,
    anonymize: bool = False,
) -> list[dict[str, Any]]:
    """Fetch submissions with user info and body text.

    Filters to only submitted/graded workflow states. When
    *exclude_graded* is True (default), graded submissions are
    excluded to avoid overwriting existing Canvas grades.
    """
    try:
        subs = await client.get_paginated(
            f"/courses/{course_id}/assignments/{assignment_id}/submissions",
            params={
                "include[]": [
                    "user",
                    "submission_comments",
                    "attachments",
                    "discussion_entries",
                ]
            },
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to fetch submissions for assignment "
            f"{assignment_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    results: list[dict[str, Any]] = []
    for s in subs:
        state = s.get("workflow_state", "")
        if state == "unsubmitted":
            continue
        if exclude_graded and state == "graded":
            continue

        sub_type = s.get("submission_type") or ""

        if sub_type == "online_text_entry":
            text = _strip_html(s.get("body") or "")
        elif sub_type == "online_upload":
            attachments = s.get("attachments") or []
            parts = []
            for att in attachments:
                parts.append(await _extract_attachment_text(client, att))
            text = "\n\n".join(parts)
        elif sub_type == "online_url":
            text = f"[url submission: {s.get('url', '')}]"
        elif sub_type == "discussion_topic":
            # Canvas returns the student's discussion entries when
            # include[]=discussion_entries is requested.  Each entry
            # has a HTML `message` and an optional `attachments` list.
            entries = s.get("discussion_entries") or []
            parts = []
            for entry in entries:
                msg = _strip_html(entry.get("message") or "")
                if msg:
                    parts.append(msg)
                for att in entry.get("attachments") or []:
                    parts.append(await _extract_attachment_text(client, att))
            text = "\n\n".join(parts)
        else:
            text = f"[submission type: {sub_type or 'unknown'}]"

        word_count = len(text.split()) if text.strip() else 0

        user = s.get("user") or {}
        submitted_at = s.get("submitted_at", "")
        late = s.get("late", False)

        results.append(
            {
                "user_id": s.get("user_id", ""),
                "user_name": "" if anonymize else user.get("name", ""),
                "user_email": "" if anonymize else user.get("email", ""),
                "submission_id": s["id"],
                "submitted_at": submitted_at,
                "late": late,
                "word_count": word_count,
                "submission_text": text,
            }
        )

    return results


def build_assessment_structure(
    course_id: str,
    course_name: str,
    assignment_data: dict[str, Any],
    submissions: list[dict[str, Any]],
    *,
    level: str = "undergraduate",
    feedback_language: str = "en",
    language_learning: bool = False,
    language_level: str = "NA",
    formality: str = "casual",
) -> dict[str, Any]:
    """Assemble the full assessment JSON structure.

    This is a pure function — no I/O.
    """
    rubric = assignment_data["rubric"]
    criteria_ids = list(rubric["criteria"].keys())

    assessments = []
    for sub in submissions:
        rubric_assessment = {}
        for cid in criteria_ids:
            rubric_assessment[cid] = {
                "points": None,
                "rating_id": None,
                "justification": "",
            }

        assessments.append(
            {
                "user_id": sub["user_id"],
                "user_name": sub["user_name"],
                "user_email": sub.get("user_email", ""),
                "submission_id": sub["submission_id"],
                "submitted_at": sub["submitted_at"],
                "late": sub.get("late", False),
                "word_count": sub.get("word_count", 0),
                "submission_text": sub.get("submission_text", ""),
                "rubric_assessment": rubric_assessment,
                "overall_comment": "",
                "reviewed": False,
                "approved": False,
            }
        )

    now = datetime.now(timezone.utc).isoformat()

    return {
        "metadata": {
            "course_id": str(course_id),
            "course_name": course_name,
            "assignment_id": str(assignment_data["assignment_id"]),
            "assignment_name": assignment_data["assignment_name"],
            "due_date": assignment_data.get("due_at", ""),
            "points_possible": assignment_data.get("points_possible", 0),
            "total_submissions": len(assessments),
            "created_at": now,
            "assignment_instructions": assignment_data.get("description", ""),
            "level": level,
            "feedback_language": feedback_language,
            "language_learning": language_learning,
            "language_level": language_level,
            "formality": formality,
            "workflow_version": "1.0",
        },
        "rubric": rubric,
        "assessments": assessments,
        "ai_instructions": "",
    }


def load_assessment(file_path: str | Path) -> dict[str, Any]:
    """Load and validate an assessment JSON file.

    Returns the parsed data. Raises CanvasError on problems.
    """
    path = Path(file_path)
    if not path.exists():
        raise CanvasError(f"Assessment file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CanvasError(f"Invalid JSON in assessment file: {exc}") from exc

    for key in ("metadata", "rubric", "assessments"):
        if key not in data:
            raise CanvasError(f"Assessment file missing required key: {key}")

    return data


def save_assessment(
    data: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write assessment JSON to disk, creating parent dirs.

    Returns the path written to.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=str, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def update_assessment_record(
    data: dict[str, Any],
    user_id: int | str,
    *,
    rubric_assessment: dict[str, dict[str, Any]] | None = None,
    overall_comment: str | None = None,
    reviewed: bool | None = None,
    approved: bool | None = None,
) -> dict[str, Any]:
    """Update one student's assessment in the in-memory structure.

    Finds the assessment entry matching *user_id* and applies the
    provided updates. Returns the updated assessment entry.
    Raises CanvasError if user_id not found.
    """
    uid = str(user_id)
    for entry in data["assessments"]:
        if str(entry["user_id"]) == uid:
            if rubric_assessment is not None:
                for cid, values in rubric_assessment.items():
                    if cid in entry["rubric_assessment"]:
                        entry["rubric_assessment"][cid].update(values)
                    else:
                        entry["rubric_assessment"][cid] = values
            if overall_comment is not None:
                entry["overall_comment"] = overall_comment
            if reviewed is not None:
                entry["reviewed"] = reviewed
            if approved is not None:
                entry["approved"] = approved
            return entry

    raise CanvasError(f"User {user_id} not found in assessment data.")


def get_assessment_stats(data: dict[str, Any]) -> dict[str, Any]:
    """Compute summary statistics from assessment data."""
    assessments = data["assessments"]
    total = len(assessments)
    reviewed = sum(1 for a in assessments if a.get("reviewed"))
    approved = sum(1 for a in assessments if a.get("approved"))

    scores = []
    for a in assessments:
        if not a.get("reviewed"):
            continue
        total_pts = 0.0
        for cid, vals in a.get("rubric_assessment", {}).items():
            pts = vals.get("points")
            if pts is not None:
                total_pts += float(pts)
        scores.append(total_pts)

    stats: dict[str, Any] = {
        "total_submissions": total,
        "reviewed": reviewed,
        "approved": approved,
        "not_reviewed": total - reviewed,
    }

    if scores:
        scores.sort()
        stats["score_avg"] = round(sum(scores) / len(scores), 2)
        stats["score_min"] = scores[0]
        stats["score_max"] = scores[-1]
    else:
        stats["score_avg"] = None
        stats["score_min"] = None
        stats["score_max"] = None

    return stats


async def submit_assessments(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    data: dict[str, Any],
    *,
    only_approved: bool = True,
    overwrite_existing: bool = False,
) -> dict[str, Any]:
    """Submit assessments to Canvas via rubric grading.

    Iterates through assessment entries, calling submit_rubric_grade
    for each eligible student. Returns a summary of results.
    """
    submitted = []
    skipped = []
    failed = []

    for entry in data["assessments"]:
        uid = str(entry["user_id"])

        if only_approved and not entry.get("approved"):
            skipped.append({"user_id": uid, "reason": "not approved"})
            continue

        # Build the rubric assessment dict for Canvas
        rubric_assessment: dict[str, dict[str, Any]] = {}
        for cid, vals in entry.get("rubric_assessment", {}).items():
            pts = vals.get("points")
            if pts is None:
                continue
            ra: dict[str, Any] = {"points": pts}
            if vals.get("justification"):
                ra["comments"] = vals["justification"]
            if vals.get("rating_id"):
                ra["rating_id"] = vals["rating_id"]
            rubric_assessment[cid] = ra

        if not rubric_assessment:
            skipped.append({"user_id": uid, "reason": "no rubric data"})
            continue

        comment = entry.get("overall_comment") or None

        try:
            result = await submit_rubric_grade(
                client,
                course_id,
                assignment_id,
                uid,
                rubric_assessment,
                comment=comment,
            )
            submitted.append(
                {
                    "user_id": uid,
                    "score": result.get("score", ""),
                }
            )
        except CanvasError as exc:
            failed.append({"user_id": uid, "error": exc.message})

    return {
        "submitted": submitted,
        "skipped": skipped,
        "failed": failed,
        "total_submitted": len(submitted),
        "total_skipped": len(skipped),
        "total_failed": len(failed),
    }
