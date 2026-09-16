"""Live Canvas smoke test for ExternalUrl module items.

Run explicitly with:
    uv run python -m pytest tests/integration/ -m integration
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from dauber.core.client import CanvasClient
from dauber.core.config import Config
from dauber.services.modules import (
    create_module,
    create_module_item,
    delete_module,
    delete_module_item,
    get_module_item,
)

pytestmark = pytest.mark.integration

_EXTERNAL_URL = "https://example.org/dauber-external-url-smoke-test"


def _missing_env() -> list[str]:
    missing = [
        name
        for name in ("CANVAS_API_KEY", "CANVAS_BASE_URL", "CANVAS_SANDBOX_COURSE_ID")
        if not os.getenv(name)
    ]
    if os.getenv("CANVAS_SANDBOX_ID") and not os.getenv("CANVAS_SANDBOX_COURSE_ID"):
        missing.append("(CANVAS_SANDBOX_ID set; expected CANVAS_SANDBOX_COURSE_ID)")
    return missing


@pytest.mark.skipif(
    bool(_missing_env()),
    reason=f"missing required environment: {', '.join(_missing_env())}",
)
async def test_create_external_url_module_item() -> None:
    """Create, read, and remove ExternalUrl item in temporary unpublished module."""
    config = Config()
    course_id = os.environ["CANVAS_SANDBOX_COURSE_ID"]
    client = CanvasClient(config)
    module_id: str | None = None
    item_id: str | None = None

    try:
        module = await create_module(
            client,
            course_id,
            f"dauber external URL smoke test {uuid4()}",
            published=False,
        )
        module_id = str(module["id"])
        item = await create_module_item(
            client,
            course_id,
            module_id,
            "External URL smoke test",
            "ExternalUrl",
            url=_EXTERNAL_URL,
        )
        item_id = str(item["id"])

        fetched = await get_module_item(client, course_id, module_id, item_id)
        assert fetched["type"] == "ExternalUrl"
        assert fetched["external_url"] == _EXTERNAL_URL
    finally:
        if item_id is not None and module_id is not None:
            await delete_module_item(client, course_id, module_id, item_id)
        if module_id is not None:
            await delete_module(client, course_id, module_id)
        await client.close()
