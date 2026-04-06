"""Tests for dauber.services.discussions."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.discussions import (
    _strip_html,
    create_discussion,
    get_discussion,
    list_discussions,
    update_discussion,
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


# -- list_discussions --


async def test_list_discussions(client):
    client.get_paginated.return_value = [
        {
            "id": 1,
            "title": "Introductions",
            "published": True,
            "posted_at": "2026-01-15T10:00:00Z",
            "is_announcement": False,
        },
        {
            "id": 2,
            "title": "Week 1 Discussion",
            "published": False,
            "posted_at": None,
            "is_announcement": False,
        },
    ]

    result = await list_discussions(client, "1")
    assert len(result) == 2
    assert result[0]["title"] == "Introductions"
    assert result[1]["published"] is False


async def test_list_discussions_announcements(client):
    client.get_paginated.return_value = [
        {
            "id": 3,
            "title": "Welcome!",
            "published": True,
            "posted_at": "2026-01-10T10:00:00Z",
            "is_announcement": True,
        },
    ]

    result = await list_discussions(client, "1", only_announcements=True)
    assert len(result) == 1
    assert result[0]["is_announcement"] is True

    call_params = client.get_paginated.call_args.kwargs["params"]
    assert call_params["only_announcements"] is True


async def test_list_discussions_empty(client):
    client.get_paginated.return_value = []
    result = await list_discussions(client, "1")
    assert result == []


async def test_list_discussions_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "GET",
            "https://canvas.test/api/v1/courses/1/discussion_topics",
        ),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await list_discussions(client, "1")
    assert exc_info.value.status_code == 403


# -- get_discussion --


async def test_get_discussion(client):
    client.request.return_value = {
        "id": 1,
        "title": "Introductions",
        "message": "<p>Please introduce yourself.</p>",
        "published": True,
        "posted_at": "2026-01-15T10:00:00Z",
        "is_announcement": False,
        "pinned": True,
        "discussion_type": "threaded",
    }

    result = await get_discussion(client, "1", "1")
    assert result["title"] == "Introductions"
    assert result["message"] == "Please introduce yourself."
    assert result["pinned"] is True
    assert result["discussion_type"] == "threaded"


async def test_get_discussion_null_message(client):
    client.request.return_value = {
        "id": 1,
        "title": "Empty",
        "message": None,
        "published": False,
        "posted_at": "",
        "is_announcement": False,
        "pinned": False,
        "discussion_type": "",
    }

    result = await get_discussion(client, "1", "1")
    assert result["message"] == ""


async def test_get_discussion_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "GET",
            "https://canvas.test/api/v1/courses/1/discussion_topics/999",
        ),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await get_discussion(client, "1", "999")
    assert exc_info.value.status_code == 404


# -- create_discussion --


async def test_create_discussion(client):
    client.request.return_value = {
        "id": 5,
        "title": "New Topic",
        "published": False,
        "is_announcement": False,
    }

    result = await create_discussion(client, "1", "New Topic", "Let's discuss.")
    assert result["id"] == 5
    assert result["title"] == "New Topic"

    call_data = client.request.call_args.kwargs["data"]
    assert call_data["title"] == "New Topic"
    assert call_data["message"] == "Let's discuss."


async def test_create_discussion_announcement(client):
    client.request.return_value = {
        "id": 6,
        "title": "Alert",
        "published": True,
        "is_announcement": True,
    }

    result = await create_discussion(
        client,
        "1",
        "Alert",
        "Important!",
        is_announcement=True,
        published=True,
    )
    assert result["is_announcement"] is True

    call_data = client.request.call_args.kwargs["data"]
    assert call_data["is_announcement"] is True


async def test_create_discussion_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "POST",
            "https://canvas.test/api/v1/courses/1/discussion_topics",
        ),
        response=httpx.Response(422, text="invalid"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await create_discussion(client, "1", "Bad")
    assert exc_info.value.status_code == 422


# -- update_discussion --


async def test_update_discussion(client):
    client.request.return_value = {
        "id": 1,
        "title": "Updated",
        "published": True,
        "is_announcement": False,
    }

    result = await update_discussion(client, "1", "1", title="Updated")
    assert result["title"] == "Updated"

    call_data = client.request.call_args.kwargs["data"]
    assert "title" in call_data


async def test_update_discussion_filters_none(client):
    client.request.return_value = {
        "id": 1,
        "title": "Same",
        "published": True,
        "is_announcement": False,
    }

    await update_discussion(client, "1", "1", title="Same", message=None)
    call_data = client.request.call_args.kwargs["data"]
    assert "title" in call_data
    assert "message" not in call_data


async def test_update_discussion_no_fields():
    client = AsyncMock(spec=CanvasClient)
    with pytest.raises(CanvasError, match="No fields to update"):
        await update_discussion(client, "1", "1")
