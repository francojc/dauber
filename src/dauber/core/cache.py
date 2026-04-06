"""Bidirectional course code / ID cache."""

from __future__ import annotations

from dauber.core.client import CanvasClient


class CourseCache:
    """Maps course codes (e.g., 'IS505') to Canvas numeric IDs and back.

    Lazily populated on first resolution attempt that requires it.
    """

    def __init__(self, client: CanvasClient) -> None:
        self._client = client
        self._code_to_id: dict[str, str] = {}
        self._id_to_code: dict[str, str] = {}

    async def refresh(self) -> None:
        """Fetch all courses and rebuild both lookup maps."""
        courses = await self._client.get_paginated(
            "/courses",
            params={
                "enrollment_type": "teacher",
                "state[]": ["available", "completed"],
            },
        )
        self._code_to_id.clear()
        self._id_to_code.clear()
        for course in courses:
            cid = str(course.get("id", ""))
            code = course.get("course_code", "")
            if cid and code:
                self._code_to_id[code] = cid
                self._id_to_code[cid] = code

    async def resolve(self, identifier: str | int) -> str:
        """Resolve a course code, numeric ID, or SIS ID to a Canvas ID.

        Resolution order:
          1. Numeric string -> pass through
          2. SIS format (sis_course_id:...) -> pass through
          3. Cache lookup by code
          4. Refresh cache, retry lookup
          5. Fallback to sis_course_id: prefix
        """
        val = str(identifier)

        if val.isdigit():
            return val

        if val.startswith("sis_course_id:"):
            return val

        if val in self._code_to_id:
            return self._code_to_id[val]

        if not self._code_to_id:
            await self.refresh()
            if val in self._code_to_id:
                return self._code_to_id[val]

        return f"sis_course_id:{val}"

    def get_code(self, course_id: str | int) -> str | None:
        """Look up a course code by numeric ID. Returns None if unknown."""
        return self._id_to_code.get(str(course_id))

    def get_id(self, course_code: str) -> str | None:
        """Look up a numeric ID by course code. Returns None if unknown."""
        return self._code_to_id.get(course_code)
