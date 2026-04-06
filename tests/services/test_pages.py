"""Tests for dauber.services.pages."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.pages import (
    _strip_html,
    create_page,
    delete_page,
    get_page,
    list_pages,
    update_page,
)


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


# -- _strip_html --


def test_strip_html_basic():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_strip_html_empty():
    assert _strip_html("") == ""
    assert _strip_html(None) == ""


def test_strip_html_no_tags():
    assert _strip_html("plain text") == "plain text"


# -- list_pages --


async def test_list_pages(client):
    client.get_paginated.return_value = [
        {
            "url": "syllabus",
            "title": "Syllabus",
            "published": True,
            "updated_at": "2026-01-15T10:00:00Z",
        },
        {
            "url": "resources",
            "title": "Resources",
            "published": False,
            "updated_at": "2026-01-16T10:00:00Z",
        },
    ]

    result = await list_pages(client, "1")
    assert len(result) == 2
    assert result[0]["title"] == "Syllabus"
    assert result[1]["published"] is False


async def test_list_pages_with_filters(client):
    client.get_paginated.return_value = []

    await list_pages(client, "1", published=True, search_term="syl", sort="updated_at")
    call_params = client.get_paginated.call_args.kwargs["params"]
    assert call_params["published"] is True
    assert call_params["search_term"] == "syl"
    assert call_params["sort"] == "updated_at"


async def test_list_pages_empty(client):
    client.get_paginated.return_value = []
    result = await list_pages(client, "1")
    assert result == []


async def test_list_pages_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses/1/pages"),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await list_pages(client, "1")
    assert exc_info.value.status_code == 403


# -- get_page --


async def test_get_page(client):
    client.request.return_value = {
        "url": "syllabus",
        "title": "Syllabus",
        "body": "<p>Welcome to the course.</p>",
        "published": True,
        "front_page": True,
        "updated_at": "2026-01-15T10:00:00Z",
        "editing_roles": "teachers",
    }

    result = await get_page(client, "1", "syllabus")
    assert result["title"] == "Syllabus"
    assert result["body"] == "Welcome to the course."
    assert result["front_page"] is True


async def test_get_page_null_body(client):
    client.request.return_value = {
        "url": "empty",
        "title": "Empty",
        "body": None,
        "published": False,
        "front_page": False,
        "updated_at": "",
        "editing_roles": "",
    }

    result = await get_page(client, "1", "empty")
    assert result["body"] == ""


async def test_get_page_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "GET", "https://canvas.test/api/v1/courses/1/pages/missing"
        ),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await get_page(client, "1", "missing")
    assert exc_info.value.status_code == 404


# -- create_page --


async def test_create_page(client):
    client.request.return_value = {
        "url": "new-page",
        "title": "New Page",
        "published": False,
    }

    result = await create_page(client, "1", "New Page", "Some content")
    assert result["url"] == "new-page"
    assert result["title"] == "New Page"

    call_data = client.request.call_args.kwargs["data"]["wiki_page"]
    assert call_data["title"] == "New Page"
    assert call_data["body"] == "Some content"


async def test_create_page_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("POST", "https://canvas.test/api/v1/courses/1/pages"),
        response=httpx.Response(422, text="invalid"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await create_page(client, "1", "Bad")
    assert exc_info.value.status_code == 422


# -- update_page --


async def test_update_page(client):
    client.request.return_value = {
        "url": "syllabus",
        "title": "Updated Syllabus",
        "published": True,
    }

    result = await update_page(client, "1", "syllabus", title="Updated Syllabus")
    assert result["title"] == "Updated Syllabus"

    call_data = client.request.call_args.kwargs["data"]["wiki_page"]
    assert "title" in call_data


async def test_update_page_filters_none(client):
    client.request.return_value = {
        "url": "syllabus",
        "title": "Same",
        "published": True,
    }

    await update_page(client, "1", "syllabus", title="Same", body=None)
    call_data = client.request.call_args.kwargs["data"]["wiki_page"]
    assert "title" in call_data
    assert "body" not in call_data


async def test_update_page_no_fields():
    client = AsyncMock(spec=CanvasClient)
    with pytest.raises(CanvasError, match="No fields to update"):
        await update_page(client, "1", "syllabus")


# -- delete_page --


async def test_delete_page(client):
    client.request.return_value = None

    result = await delete_page(client, "1", "syllabus")
    assert result["deleted"] is True
    assert result["url"] == "syllabus"


async def test_delete_page_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "DELETE", "https://canvas.test/api/v1/courses/1/pages/missing"
        ),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await delete_page(client, "1", "missing")
    assert exc_info.value.status_code == 404
