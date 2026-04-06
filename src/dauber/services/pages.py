"""Pages service — list, detail, create, update, and delete."""

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


async def list_pages(
    client: CanvasClient,
    course_id: str,
    *,
    published: bool | None = None,
    search_term: str | None = None,
    sort: str = "title",
) -> list[dict[str, Any]]:
    """Fetch all pages for a course.

    Returns:
        List of page dicts with projected fields.
    """
    params: dict[str, Any] = {"sort": sort}
    if published is not None:
        params["published"] = published
    if search_term:
        params["search_term"] = search_term

    try:
        pages = await client.get_paginated(
            f"/courses/{course_id}/pages",
            params=params,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list pages for course {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return [
        {
            "url": p.get("url", ""),
            "title": p.get("title", ""),
            "published": p.get("published", False),
            "updated_at": p.get("updated_at", ""),
        }
        for p in pages
    ]


async def get_page(
    client: CanvasClient,
    course_id: str,
    page_url: str,
) -> dict[str, Any]:
    """Fetch a single page by its URL slug."""
    try:
        p = await client.request(
            "get",
            f"/courses/{course_id}/pages/{page_url}",
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get page {page_url}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "url": p.get("url", ""),
        "title": p.get("title", ""),
        "body": _strip_html(p.get("body", "") or ""),
        "published": p.get("published", False),
        "front_page": p.get("front_page", False),
        "updated_at": p.get("updated_at", ""),
        "editing_roles": p.get("editing_roles", ""),
    }


async def create_page(
    client: CanvasClient,
    course_id: str,
    title: str,
    body: str = "",
    *,
    published: bool = False,
    front_page: bool = False,
    editing_roles: str | None = None,
) -> dict[str, Any]:
    """Create a new page in a course."""
    payload: dict[str, Any] = {
        "title": title,
        "body": body,
        "published": published,
        "front_page": front_page,
    }
    if editing_roles is not None:
        payload["editing_roles"] = editing_roles

    try:
        p = await client.request(
            "post",
            f"/courses/{course_id}/pages",
            data={"wiki_page": payload},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to create page: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "url": p.get("url", ""),
        "title": p.get("title", ""),
        "published": p.get("published", False),
    }


async def update_page(
    client: CanvasClient,
    course_id: str,
    page_url: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update an existing page. Only non-None kwargs are sent."""
    payload = {k: v for k, v in kwargs.items() if v is not None}
    if not payload:
        raise CanvasError("No fields to update.")

    try:
        p = await client.request(
            "put",
            f"/courses/{course_id}/pages/{page_url}",
            data={"wiki_page": payload},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to update page {page_url}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "url": p.get("url", ""),
        "title": p.get("title", ""),
        "published": p.get("published", False),
    }


async def delete_page(
    client: CanvasClient,
    course_id: str,
    page_url: str,
) -> dict[str, Any]:
    """Delete a page from a course."""
    try:
        await client.request(
            "delete",
            f"/courses/{course_id}/pages/{page_url}",
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to delete page {page_url}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {"url": page_url, "deleted": True}
