"""Tests for dauber.services.modules."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.modules import (
    create_module,
    delete_module,
    get_module,
    list_modules,
    update_module,
)


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


# -- list_modules --


async def test_list_modules(client):
    client.get_paginated.return_value = [
        {
            "id": 1,
            "name": "Week 1",
            "position": 1,
            "published": True,
            "items_count": 3,
        },
        {
            "id": 2,
            "name": "Week 2",
            "position": 2,
            "published": False,
            "items_count": 0,
        },
    ]

    result = await list_modules(client, "1")
    assert len(result) == 2
    assert result[0]["name"] == "Week 1"
    assert result[1]["published"] is False
    assert "items" not in result[0]


async def test_list_modules_with_items(client):
    client.get_paginated.return_value = [
        {
            "id": 1,
            "name": "Week 1",
            "position": 1,
            "published": True,
            "items_count": 1,
            "items": [{"id": 10, "title": "Intro", "type": "Page"}],
        },
    ]

    result = await list_modules(client, "1", include_items=True)
    assert "items" in result[0]
    assert result[0]["items"][0]["title"] == "Intro"

    call_params = client.get_paginated.call_args.kwargs["params"]
    assert call_params["include[]"] == "items"


async def test_list_modules_with_search(client):
    client.get_paginated.return_value = []

    await list_modules(client, "1", search_term="week")
    call_params = client.get_paginated.call_args.kwargs["params"]
    assert call_params["search_term"] == "week"


async def test_list_modules_empty(client):
    client.get_paginated.return_value = []
    result = await list_modules(client, "1")
    assert result == []


async def test_list_modules_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses/1/modules"),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await list_modules(client, "1")
    assert exc_info.value.status_code == 403


# -- get_module --


async def test_get_module(client):
    client.request.return_value = {
        "id": 1,
        "name": "Week 1",
        "position": 1,
        "published": True,
        "unlock_at": None,
        "require_sequential_progress": False,
        "items_count": 2,
    }
    client.get_paginated.return_value = [
        {"id": 10, "title": "Intro", "type": "Page", "position": 1, "indent": 0},
        {"id": 11, "title": "Quiz", "type": "Quiz", "position": 2, "indent": 0},
    ]

    result = await get_module(client, "1", "1")
    assert result["id"] == 1
    assert result["name"] == "Week 1"
    assert len(result["items"]) == 2
    assert result["items"][0]["title"] == "Intro"


async def test_get_module_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "GET", "https://canvas.test/api/v1/courses/1/modules/999"
        ),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await get_module(client, "1", "999")
    assert exc_info.value.status_code == 404


# -- create_module --


async def test_create_module(client):
    client.request.return_value = {
        "id": 3,
        "name": "Week 3",
        "position": 3,
        "published": False,
    }

    result = await create_module(client, "1", "Week 3", position=3)
    assert result["id"] == 3
    assert result["name"] == "Week 3"

    call_data = client.request.call_args.kwargs["data"]["module"]
    assert call_data["name"] == "Week 3"
    assert call_data["position"] == 3


async def test_create_module_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("POST", "https://canvas.test/api/v1/courses/1/modules"),
        response=httpx.Response(422, text="invalid"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await create_module(client, "1", "Bad")
    assert exc_info.value.status_code == 422


# -- update_module --


async def test_update_module(client):
    client.request.return_value = {
        "id": 1,
        "name": "Updated",
        "position": 1,
        "published": True,
    }

    result = await update_module(client, "1", "1", name="Updated")
    assert result["name"] == "Updated"

    call_data = client.request.call_args.kwargs["data"]["module"]
    assert "name" in call_data


async def test_update_module_filters_none(client):
    client.request.return_value = {
        "id": 1,
        "name": "Same",
        "position": 1,
        "published": True,
    }

    await update_module(client, "1", "1", name="Same", position=None)
    call_data = client.request.call_args.kwargs["data"]["module"]
    assert "name" in call_data
    assert "position" not in call_data


async def test_update_module_no_fields():
    client = AsyncMock(spec=CanvasClient)
    with pytest.raises(CanvasError, match="No fields to update"):
        await update_module(client, "1", "1")


# -- delete_module --


async def test_delete_module(client):
    client.request.return_value = None

    result = await delete_module(client, "1", "1")
    assert result["deleted"] is True
    assert result["id"] == "1"


async def test_delete_module_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "DELETE", "https://canvas.test/api/v1/courses/1/modules/999"
        ),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await delete_module(client, "1", "999")
    assert exc_info.value.status_code == 404
