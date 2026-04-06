"""Assignments service — list, detail, create, and update."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any

import httpx

from dauber.core.client import CanvasClient
from dauber.services import CanvasError


class _HTMLStripper(HTMLParser):
    """Minimal HTML tag stripper using stdlib HTMLParser."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts).strip()


def _strip_html(text: str) -> str:
    """Remove HTML tags from *text*, returning plain text."""
    if not text:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(text)
    return stripper.get_text()


async def list_assignments(
    client: CanvasClient,
    course_id: str,
) -> list[dict[str, Any]]:
    """Fetch all assignments for a course.

    Returns:
        List of assignment dicts with projected fields.
    """
    try:
        assignments = await client.get_paginated(
            f"/courses/{course_id}/assignments",
            params={"order_by": "due_at"},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list assignments for course {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return [
        {
            "id": a["id"],
            "name": a.get("name", ""),
            "due_at": a.get("due_at", ""),
            "points_possible": a.get("points_possible", ""),
            "published": a.get("published", False),
            "submission_types": ", ".join(a.get("submission_types", [])),
        }
        for a in assignments
    ]


async def get_assignment(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
) -> dict[str, Any]:
    """Fetch a single assignment with its rubric (if attached).

    Uses ``include[]=rubric,rubric_settings`` so the rubric is
    embedded in the response when one exists.
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

    return {
        "id": a["id"],
        "name": a.get("name", ""),
        "description": _strip_html(a.get("description", "") or ""),
        "due_at": a.get("due_at", ""),
        "points_possible": a.get("points_possible", ""),
        "published": a.get("published", False),
        "submission_types": ", ".join(a.get("submission_types", [])),
        "rubric": a.get("rubric"),
        "rubric_settings": a.get("rubric_settings"),
    }


async def create_assignment(
    client: CanvasClient,
    course_id: str,
    name: str,
    *,
    points_possible: float | None = None,
    due_at: str | None = None,
    submission_types: list[str] | None = None,
    published: bool = False,
) -> dict[str, Any]:
    """Create a new assignment in a course."""
    payload: dict[str, Any] = {
        "name": name,
        "published": published,
    }
    if points_possible is not None:
        payload["points_possible"] = points_possible
    if due_at is not None:
        payload["due_at"] = due_at
    if submission_types is not None:
        payload["submission_types"] = submission_types

    try:
        a = await client.request(
            "post",
            f"/courses/{course_id}/assignments",
            data={"assignment": payload},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to create assignment: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": a["id"],
        "name": a.get("name", ""),
        "due_at": a.get("due_at", ""),
        "points_possible": a.get("points_possible", ""),
        "published": a.get("published", False),
    }


async def update_assignment(
    client: CanvasClient,
    course_id: str,
    assignment_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update an existing assignment. Only non-None kwargs are sent."""
    payload = {k: v for k, v in kwargs.items() if v is not None}
    if not payload:
        raise CanvasError("No fields to update.")

    try:
        a = await client.request(
            "put",
            f"/courses/{course_id}/assignments/{assignment_id}",
            data={"assignment": payload},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to update assignment {assignment_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": a["id"],
        "name": a.get("name", ""),
        "due_at": a.get("due_at", ""),
        "points_possible": a.get("points_possible", ""),
        "published": a.get("published", False),
    }
