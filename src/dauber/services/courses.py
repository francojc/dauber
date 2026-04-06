"""Courses service — list, details, and enrollments."""

from __future__ import annotations

from typing import Any

import httpx

from dauber.core.client import CanvasClient
from dauber.services import CanvasError


async def list_courses(
    client: CanvasClient,
    include_concluded: bool = False,
) -> list[dict[str, Any]]:
    """Fetch courses where the authenticated user is a teacher.

    Args:
        client: Authenticated Canvas API client.
        include_concluded: If True, include completed courses.

    Returns:
        List of course dicts with id, name, course_code, term,
        total_students.
    """
    states = ["available"]
    if include_concluded:
        states.append("completed")

    try:
        courses = await client.get_paginated(
            "/courses",
            params={
                "enrollment_type": "teacher",
                "state[]": states,
                "include[]": ["term", "teachers", "total_students"],
            },
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to list courses: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return [
        {
            "id": c["id"],
            "name": c.get("name", ""),
            "course_code": c.get("course_code", ""),
            "term": (c.get("term") or {}).get("name", ""),
            "total_students": c.get("total_students", ""),
        }
        for c in courses
    ]


async def get_course(
    client: CanvasClient,
    course_id: str,
) -> dict[str, Any]:
    """Fetch details for a single course.

    Args:
        client: Authenticated Canvas API client.
        course_id: Resolved Canvas course ID.

    Returns:
        Dict with course metadata fields.
    """
    try:
        c = await client.request("get", f"/courses/{course_id}")
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get course {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    return {
        "id": c["id"],
        "course_code": c.get("course_code", ""),
        "name": c.get("name", ""),
        "start_at": c.get("start_at", ""),
        "end_at": c.get("end_at", ""),
        "time_zone": c.get("time_zone", ""),
        "default_view": c.get("default_view", ""),
        "is_public": c.get("is_public", False),
    }


async def get_enrollments(
    client: CanvasClient,
    course_id: str,
) -> list[dict[str, Any]]:
    """Fetch enrolled users for a course.

    Args:
        client: Authenticated Canvas API client.
        course_id: Resolved Canvas course ID.

    Returns:
        List of user dicts with id, name, email, role.
    """
    try:
        users = await client.get_paginated(
            f"/courses/{course_id}/users",
            params={"include[]": ["enrollments", "email"]},
        )
    except httpx.HTTPStatusError as exc:
        raise CanvasError(
            f"Failed to get enrollments for {course_id}: {exc.response.text}",
            status_code=exc.response.status_code,
        ) from exc

    results = []
    for u in users:
        enrollments = u.get("enrollments", [])
        role = enrollments[0].get("role", "") if enrollments else ""
        results.append(
            {
                "id": u["id"],
                "name": u.get("name", ""),
                "email": u.get("email", ""),
                "role": role,
            }
        )
    return results
