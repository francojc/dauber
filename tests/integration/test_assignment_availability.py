"""Live Canvas sandbox assignment availability-window tests.

Run explicitly with write access enabled:
    CANVAS_SANDBOX_WRITE_ENABLED=1 uv run python -m pytest tests/integration/test_assignment_availability.py -m integration
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from dauber.core.client import CanvasClient
from dauber.core.config import Config
from dauber.services.assignments import (
    create_assignment,
    get_assignment,
    update_assignment,
)

pytestmark = pytest.mark.integration

_REQUIRED_ENV = (
    "CANVAS_API_KEY",
    "CANVAS_BASE_URL",
    "CANVAS_SANDBOX_COURSE_ID",
)


def _missing_env() -> list[str]:
    missing = [name for name in _REQUIRED_ENV if not os.getenv(name)]
    if os.getenv("CANVAS_SANDBOX_WRITE_ENABLED") != "1":
        missing.append("CANVAS_SANDBOX_WRITE_ENABLED=1")
    if os.getenv("CANVAS_SANDBOX_ID") and not os.getenv("CANVAS_SANDBOX_COURSE_ID"):
        missing.append("(CANVAS_SANDBOX_ID set; expected CANVAS_SANDBOX_COURSE_ID)")
    return missing


@pytest.mark.skipif(
    bool(_missing_env()),
    reason=f"missing required environment: {', '.join(_missing_env())}",
)
async def test_assignment_availability_dates_create_update_and_clear() -> None:
    """Create, update, clear, and delete a sandbox assignment's dates."""
    course_id = os.environ["CANVAS_SANDBOX_COURSE_ID"]
    client = CanvasClient(Config())
    assignment_id: str | None = None

    try:
        created = await create_assignment(
            client,
            course_id,
            f"Dauber availability integration {uuid4().hex}",
            unlock_at="2030-01-01T00:00:00Z",
            due_at="2030-01-08T00:00:00Z",
            lock_at="2030-01-15T00:00:00Z",
        )
        assignment_id = str(created["id"])
        assert created["unlock_at"] == "2030-01-01T00:00:00Z"
        assert created["due_at"] == "2030-01-08T00:00:00Z"
        assert created["lock_at"] == "2030-01-15T00:00:00Z"

        updated = await update_assignment(
            client,
            course_id,
            assignment_id,
            due_at="2030-01-10T00:00:00Z",
        )
        assert updated["due_at"] == "2030-01-10T00:00:00Z"

        cleared = await update_assignment(
            client,
            course_id,
            assignment_id,
            clear_unlock_at=True,
            clear_due_at=True,
            clear_lock_at=True,
        )
        assert cleared["unlock_at"] is None
        assert cleared["due_at"] is None
        assert cleared["lock_at"] is None

        fetched = await get_assignment(client, course_id, assignment_id)
        assert fetched["unlock_at"] is None
        assert fetched["due_at"] is None
        assert fetched["lock_at"] is None
    finally:
        try:
            if assignment_id is not None:
                await client.request(
                    "delete",
                    f"/courses/{course_id}/assignments/{assignment_id}",
                )
        finally:
            await client.close()
