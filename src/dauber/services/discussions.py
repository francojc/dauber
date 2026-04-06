"""Discussions service — list, detail, create, and update."""

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


async def list_discussions(
    client: CanvasClient,
    course_id: str,
    *,
    only_announcements: bool = False,
) -> list[dict[str, Any]]:
    """Fetch all discussion topics for a course.

    Returns:
        List of discussion dicts with projected fields.
    """
    params: dict[str, Any] = {}
    if only_announcements:
        params["only_announcements"] = True

    try:
        topics = await client.get_paginated(
            f"/courses/{course_id}/discussion_topics",
            params=params,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list discussions for course {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return [
        {
            "id": t["id"],
            "title": t.get("title", ""),
            "published": t.get("published", False),
            "posted_at": t.get("posted_at", ""),
            "is_announcement": t.get("is_announcement", False),
        }
        for t in topics
    ]


async def get_discussion(
    client: CanvasClient,
    course_id: str,
    topic_id: str,
) -> dict[str, Any]:
    """Fetch a single discussion topic."""
    try:
        t = await client.request(
            "get",
            f"/courses/{course_id}/discussion_topics/{topic_id}",
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get discussion {topic_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": t["id"],
        "title": t.get("title", ""),
        "message": _strip_html(t.get("message", "") or ""),
        "published": t.get("published", False),
        "posted_at": t.get("posted_at", ""),
        "is_announcement": t.get("is_announcement", False),
        "pinned": t.get("pinned", False),
        "discussion_type": t.get("discussion_type", ""),
    }


async def create_discussion(
    client: CanvasClient,
    course_id: str,
    title: str,
    message: str = "",
    *,
    is_announcement: bool = False,
    published: bool = False,
    pinned: bool = False,
    discussion_type: str | None = None,
) -> dict[str, Any]:
    """Create a new discussion topic in a course."""
    payload: dict[str, Any] = {
        "title": title,
        "message": message,
        "is_announcement": is_announcement,
        "published": published,
        "pinned": pinned,
    }
    if discussion_type is not None:
        payload["discussion_type"] = discussion_type

    try:
        t = await client.request(
            "post",
            f"/courses/{course_id}/discussion_topics",
            data=payload,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to create discussion: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": t["id"],
        "title": t.get("title", ""),
        "published": t.get("published", False),
        "is_announcement": t.get("is_announcement", False),
    }


async def update_discussion(
    client: CanvasClient,
    course_id: str,
    topic_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update an existing discussion topic. Only non-None kwargs are sent."""
    payload = {k: v for k, v in kwargs.items() if v is not None}
    if not payload:
        raise CanvasError("No fields to update.")

    try:
        t = await client.request(
            "put",
            f"/courses/{course_id}/discussion_topics/{topic_id}",
            data=payload,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to update discussion {topic_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": t["id"],
        "title": t.get("title", ""),
        "published": t.get("published", False),
        "is_announcement": t.get("is_announcement", False),
    }
