"""Modules service — list, detail, create, update, and delete."""

from __future__ import annotations

from typing import Any

import httpx

from dauber.core.client import CanvasClient
from dauber.services import CanvasError


async def list_modules(
    client: CanvasClient,
    course_id: str,
    *,
    include_items: bool = False,
    search_term: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all modules for a course.

    Returns:
        List of module dicts with projected fields.
    """
    params: dict[str, Any] = {}
    if include_items:
        params["include[]"] = "items"
    if search_term:
        params["search_term"] = search_term

    try:
        modules = await client.get_paginated(
            f"/courses/{course_id}/modules",
            params=params,
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list modules for course {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    result = []
    for m in modules:
        entry: dict[str, Any] = {
            "id": m["id"],
            "name": m.get("name", ""),
            "position": m.get("position", ""),
            "published": m.get("published", False),
            "items_count": m.get("items_count", 0),
        }
        if include_items:
            entry["items"] = m.get("items", [])
        result.append(entry)
    return result


async def get_module(
    client: CanvasClient,
    course_id: str,
    module_id: str,
) -> dict[str, Any]:
    """Fetch a single module with its items."""
    try:
        m = await client.request(
            "get",
            f"/courses/{course_id}/modules/{module_id}",
        )
        items = await client.get_paginated(
            f"/courses/{course_id}/modules/{module_id}/items",
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get module {module_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": m["id"],
        "name": m.get("name", ""),
        "position": m.get("position", ""),
        "published": m.get("published", False),
        "unlock_at": m.get("unlock_at"),
        "require_sequential_progress": m.get("require_sequential_progress", False),
        "items_count": m.get("items_count", 0),
        "items": [
            {
                "id": i["id"],
                "title": i.get("title", ""),
                "type": i.get("type", ""),
                "position": i.get("position", ""),
                "indent": i.get("indent", 0),
            }
            for i in items
        ],
    }


async def create_module(
    client: CanvasClient,
    course_id: str,
    name: str,
    *,
    position: int | None = None,
    unlock_at: str | None = None,
    require_sequential_progress: bool = False,
    published: bool = False,
) -> dict[str, Any]:
    """Create a new module in a course."""
    payload: dict[str, Any] = {
        "name": name,
        "published": published,
        "require_sequential_progress": require_sequential_progress,
    }
    if position is not None:
        payload["position"] = position
    if unlock_at is not None:
        payload["unlock_at"] = unlock_at

    try:
        m = await client.request(
            "post",
            f"/courses/{course_id}/modules",
            data={"module": payload},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to create module: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": m["id"],
        "name": m.get("name", ""),
        "position": m.get("position", ""),
        "published": m.get("published", False),
    }


async def update_module(
    client: CanvasClient,
    course_id: str,
    module_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Update an existing module. Only non-None kwargs are sent."""
    payload = {k: v for k, v in kwargs.items() if v is not None}
    if not payload:
        raise CanvasError("No fields to update.")

    try:
        m = await client.request(
            "put",
            f"/courses/{course_id}/modules/{module_id}",
            data={"module": payload},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to update module {module_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": m["id"],
        "name": m.get("name", ""),
        "position": m.get("position", ""),
        "published": m.get("published", False),
    }


async def delete_module(
    client: CanvasClient,
    course_id: str,
    module_id: str,
) -> dict[str, Any]:
    """Delete a module from a course."""
    try:
        await client.request(
            "delete",
            f"/courses/{course_id}/modules/{module_id}",
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to delete module {module_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {"id": module_id, "deleted": True}
