"""Live Canvas sandbox module-item CRUD tests.

Run explicitly with write access enabled:
    CANVAS_SANDBOX_WRITE_ENABLED=1 uv run python -m pytest tests/integration/test_module_items.py -m integration
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
    list_module_items,
    update_module_item,
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
    return missing


@pytest.mark.skipif(
    bool(_missing_env()),
    reason=(
        "requires CANVAS_API_KEY, CANVAS_BASE_URL, CANVAS_SANDBOX_COURSE_ID, "
        "and CANVAS_SANDBOX_WRITE_ENABLED=1"
    ),
)
async def test_module_item_external_url_crud() -> None:
    """Create, read, list, update, and delete an ExternalUrl module item."""
    course_id = os.environ["CANVAS_SANDBOX_COURSE_ID"]
    create_url = "https://example.com/dauber-module-item-create"
    updated_url = "https://example.com/dauber-module-item-updated"
    client = CanvasClient(Config())
    module_id: str | None = None

    try:
        module = await create_module(
            client,
            course_id,
            f"Dauber module-item integration {uuid4().hex}",
            published=True,
        )
        module_id = str(module["id"])

        created = await create_module_item(
            client,
            course_id,
            module_id,
            "Dauber External URL",
            "ExternalUrl",
            url=create_url,
            position=1,
            indent=1,
            published=True,
            new_tab=True,
        )
        item_id = str(created["id"])

        assert created["type"] == "ExternalUrl"
        assert created["external_url"] == create_url
        assert created["published"] is True
        assert created["new_tab"] is True

        fetched = await get_module_item(client, course_id, module_id, item_id)
        assert fetched["external_url"] == create_url
        assert fetched["position"] == 1
        assert fetched["indent"] == 1

        items = await list_module_items(client, course_id, module_id)
        assert any(str(item["id"]) == item_id for item in items)

        updated = await update_module_item(
            client,
            course_id,
            module_id,
            item_id,
            title="Dauber External URL updated",
            url=updated_url,
            indent=2,
            published=False,
            new_tab=False,
        )
        assert updated["title"] == "Dauber External URL updated"
        assert updated["external_url"] == updated_url
        assert updated["indent"] == 2
        assert updated["published"] is False
        assert updated["new_tab"] is False

        await delete_module_item(client, course_id, module_id, item_id)
        items = await list_module_items(client, course_id, module_id)
        assert all(str(item["id"]) != item_id for item in items)
    finally:
        try:
            if module_id is not None:
                await delete_module(client, course_id, module_id)
        finally:
            await client.close()
