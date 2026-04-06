"""Tests for dauber.services.assignments."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.assignments import (
    _strip_html,
    create_assignment,
    get_assignment,
    list_assignments,
    update_assignment,
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


# -- list_assignments --


async def test_list_assignments(client):
    client.get_paginated.return_value = [
        {
            "id": 101,
            "name": "Homework 1",
            "due_at": "2026-02-01T23:59:00Z",
            "points_possible": 100,
            "published": True,
            "submission_types": ["online_upload", "online_text_entry"],
        },
        {
            "id": 102,
            "name": "Quiz 1",
            "due_at": None,
            "points_possible": 50,
            "published": False,
            "submission_types": ["online_quiz"],
        },
    ]

    result = await list_assignments(client, "1")
    assert len(result) == 2
    assert result[0]["id"] == 101
    assert result[0]["name"] == "Homework 1"
    assert result[0]["submission_types"] == "online_upload, online_text_entry"
    assert result[1]["published"] is False


async def test_list_assignments_empty(client):
    client.get_paginated.return_value = []
    result = await list_assignments(client, "1")
    assert result == []


async def test_list_assignments_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "GET", "https://canvas.test/api/v1/courses/1/assignments"
        ),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await list_assignments(client, "1")
    assert exc_info.value.status_code == 403


# -- get_assignment --


async def test_get_assignment(client):
    client.request.return_value = {
        "id": 101,
        "name": "Homework 1",
        "description": "<p>Write an essay.</p>",
        "due_at": "2026-02-01T23:59:00Z",
        "points_possible": 100,
        "published": True,
        "submission_types": ["online_upload"],
        "rubric": [{"id": "_8027", "points": 10}],
        "rubric_settings": {"points_possible": 10},
    }

    result = await get_assignment(client, "1", "101")
    assert result["id"] == 101
    assert result["description"] == "Write an essay."
    assert result["rubric"] is not None
    assert result["rubric_settings"]["points_possible"] == 10

    call_params = client.request.call_args
    assert "rubric" in call_params.kwargs["params"]["include[]"]


async def test_get_assignment_no_rubric(client):
    client.request.return_value = {
        "id": 101,
        "name": "Homework 1",
        "description": None,
        "due_at": None,
        "points_possible": 0,
        "published": False,
        "submission_types": [],
    }

    result = await get_assignment(client, "1", "101")
    assert result["description"] == ""
    assert result["rubric"] is None


async def test_get_assignment_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "GET", "https://canvas.test/api/v1/courses/1/assignments/999"
        ),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await get_assignment(client, "1", "999")
    assert exc_info.value.status_code == 404


# -- create_assignment --


async def test_create_assignment(client):
    client.request.return_value = {
        "id": 201,
        "name": "New Assignment",
        "due_at": "2026-03-01T23:59:00Z",
        "points_possible": 50,
        "published": False,
    }

    result = await create_assignment(
        client,
        "1",
        "New Assignment",
        points_possible=50,
        due_at="2026-03-01T23:59:00Z",
    )
    assert result["id"] == 201
    assert result["name"] == "New Assignment"

    call_data = client.request.call_args.kwargs["data"]["assignment"]
    assert call_data["name"] == "New Assignment"
    assert call_data["points_possible"] == 50


async def test_create_assignment_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request(
            "POST", "https://canvas.test/api/v1/courses/1/assignments"
        ),
        response=httpx.Response(422, text="invalid"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await create_assignment(client, "1", "Bad")
    assert exc_info.value.status_code == 422


# -- update_assignment --


async def test_update_assignment(client):
    client.request.return_value = {
        "id": 101,
        "name": "Updated Name",
        "due_at": None,
        "points_possible": 75,
        "published": True,
    }

    result = await update_assignment(
        client,
        "1",
        "101",
        name="Updated Name",
        points_possible=75,
    )
    assert result["name"] == "Updated Name"

    call_data = client.request.call_args.kwargs["data"]["assignment"]
    assert "name" in call_data
    assert "points_possible" in call_data


async def test_update_assignment_filters_none(client):
    client.request.return_value = {
        "id": 101,
        "name": "Same",
        "due_at": None,
        "points_possible": 100,
        "published": True,
    }

    await update_assignment(client, "1", "101", name="Same", due_at=None)

    call_data = client.request.call_args.kwargs["data"]["assignment"]
    assert "name" in call_data
    assert "due_at" not in call_data


async def test_update_assignment_no_fields():
    client = AsyncMock(spec=CanvasClient)
    with pytest.raises(CanvasError, match="No fields to update"):
        await update_assignment(client, "1", "101")
