"""Canvas sandbox connectivity integration test.

Run explicitly with:
    uv run python -m pytest tests/integration/ -m integration
"""

from __future__ import annotations

import os

import pytest

from dauber.core.client import CanvasClient
from dauber.core.config import Config
from dauber.services.courses import get_course

pytestmark = pytest.mark.integration


def _missing_env() -> list[str]:
    return [
        name
        for name in ("CANVAS_API_KEY", "CANVAS_BASE_URL", "CANVAS_SANDBOX_COURSE_ID")
        if not os.getenv(name)
    ]


@pytest.mark.skipif(
    bool(_missing_env()),
    reason="requires CANVAS_API_KEY, CANVAS_BASE_URL, and CANVAS_SANDBOX_COURSE_ID",
)
async def test_canvas_sandbox_course_connectivity() -> None:
    """Verify credentials can read the configured sandbox course."""
    config = Config()
    course_id = os.environ["CANVAS_SANDBOX_COURSE_ID"]
    client = CanvasClient(config)
    try:
        course = await get_course(client, course_id)
    finally:
        await client.close()

    assert str(course["id"])
    assert course["name"]
