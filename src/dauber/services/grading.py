"""Grading service — submissions, grade submission, rubric grading."""

from __future__ import annotations

from typing import Any

import httpx

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.rubrics import build_rubric_assessment_form_data


async def list_submissions(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    *,
    anonymize: bool = False,
) -> list[dict[str, Any]]:
    """Fetch all submissions for an assignment."""
    try:
        subs = await client.get_paginated(
            f"/courses/{course_id}/assignments/{assignment_id}/submissions",
            params={"include[]": ["user"]},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list submissions for assignment {assignment_id}: "
            f"{exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return [
        {
            "id": s["id"],
            "user_id": s.get("user_id", ""),
            "user_name": "" if anonymize else (s.get("user") or {}).get("name", ""),
            "workflow_state": s.get("workflow_state", ""),
            "score": s.get("score", ""),
            "grade": s.get("grade", ""),
            "submitted_at": s.get("submitted_at", ""),
        }
        for s in subs
    ]


async def get_submission(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    user_id: str,
    *,
    anonymize: bool = False,
) -> dict[str, Any]:
    """Fetch a single submission with rubric assessment detail."""
    try:
        s = await client.request(
            "get",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}",
            params={"include[]": ["rubric_assessment", "user"]},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get submission for user {user_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": s["id"],
        "user_id": s.get("user_id", ""),
        "user_name": "" if anonymize else (s.get("user") or {}).get("name", ""),
        "workflow_state": s.get("workflow_state", ""),
        "score": s.get("score", ""),
        "grade": s.get("grade", ""),
        "submitted_at": s.get("submitted_at", ""),
        "rubric_assessment": s.get("rubric_assessment"),
    }


async def submit_grade(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    user_id: str,
    grade: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Submit a simple grade (points or letter) for a submission."""
    form_data: list[tuple[str, str]] = [
        ("submission[posted_grade]", grade),
    ]
    if comment is not None:
        form_data.append(("comment[text_comment]", comment))

    try:
        s = await client.request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}",
            form_data=form_data,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to submit grade for user {user_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": s["id"],
        "user_id": s.get("user_id", ""),
        "score": s.get("score", ""),
        "grade": s.get("grade", ""),
    }


async def submit_rubric_grade(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    user_id: str,
    rubric_assessment: dict[str, dict[str, Any]],
    comment: str | None = None,
) -> dict[str, Any]:
    """Submit a rubric-based grade for a submission.

    Args:
        rubric_assessment: Mapping of criterion_id -> {points, comments?, rating_id?}.
        comment: Overall submission comment.
    """
    form_data = build_rubric_assessment_form_data(rubric_assessment, comment)

    try:
        s = await client.request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}",
            form_data=form_data,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to submit rubric grade for user {user_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": s["id"],
        "user_id": s.get("user_id", ""),
        "score": s.get("score", ""),
        "grade": s.get("grade", ""),
    }
