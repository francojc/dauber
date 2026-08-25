"""Tests for dauber.services.assignments."""

from unittest.mock import AsyncMock, call

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
    client.get_paginated.side_effect = [
        [
            {
                "id": 101,
                "name": "Homework 1",
                "assignment_group_id": 10,
                "unlock_at": "2026-01-25T00:00:00Z",
                "due_at": "2026-02-01T23:59:00Z",
                "lock_at": "2026-02-08T00:00:00Z",
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
            {
                "id": 103,
                "name": "Unmatched assignment",
                "assignment_group_id": 99,
                "due_at": None,
                "points_possible": 50,
                "published": False,
                "submission_types": [],
            },
        ],
        [{"id": 10, "name": "Essays", "group_weight": 40}],
    ]

    result = await list_assignments(client, "1")
    assert len(result) == 3
    assert result[0]["id"] == 101
    assert result[0]["name"] == "Homework 1"
    assert result[0]["assignment_group_id"] == 10
    assert result[0]["assignment_group_name"] == "Essays"
    assert result[0]["assignment_group_weight"] == 40.0
    assert result[0]["unlock_at"] == "2026-01-25T00:00:00Z"
    assert result[0]["due_at"] == "2026-02-01T23:59:00Z"
    assert result[0]["lock_at"] == "2026-02-08T00:00:00Z"
    assert result[0]["submission_types"] == "online_upload, online_text_entry"
    assert result[1]["published"] is False
    assert result[1]["assignment_group_id"] is None
    assert result[1]["assignment_group_name"] is None
    assert result[1]["assignment_group_weight"] is None
    assert result[2]["assignment_group_id"] == 99
    assert result[2]["assignment_group_name"] is None
    assert result[2]["assignment_group_weight"] is None
    assert (
        client.get_paginated.await_args_list.count(call("/courses/1/assignment_groups"))
        == 1
    )


async def test_list_assignments_empty(client):
    client.get_paginated.side_effect = [[], []]
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


async def test_list_assignments_group_fetch_http_error(client):
    client.get_paginated.side_effect = [
        [{"id": 101, "name": "Homework 1"}],
        httpx.HTTPStatusError(
            "error",
            request=httpx.Request(
                "GET", "https://canvas.test/api/v1/courses/1/assignment_groups"
            ),
            response=httpx.Response(403, text="forbidden"),
        ),
    ]

    with pytest.raises(CanvasError) as exc_info:
        await list_assignments(client, "1")

    assert exc_info.value.status_code == 403
    assert "assignment groups for course 1" in exc_info.value.message


# -- get_assignment --


async def test_get_assignment(client):
    client.request.return_value = {
        "id": 101,
        "name": "Homework 1",
        "assignment_group_id": 10,
        "description": "<p>Write an essay.</p>",
        "unlock_at": "2026-01-25T00:00:00Z",
        "due_at": "2026-02-01T23:59:00Z",
        "lock_at": "2026-02-08T00:00:00Z",
        "points_possible": 100,
        "published": True,
        "submission_types": ["online_upload"],
        "rubric": [{"id": "_8027", "points": 10}],
        "rubric_settings": {"points_possible": 10},
    }

    client.get_paginated.return_value = [
        {"id": 10, "name": "Essays", "group_weight": 40}
    ]

    result = await get_assignment(client, "1", "101")
    assert result["id"] == 101
    assert result["description"] == "Write an essay."
    assert result["assignment_group_id"] == 10
    assert result["assignment_group_name"] == "Essays"
    assert result["assignment_group_weight"] == 40.0
    assert result["unlock_at"] == "2026-01-25T00:00:00Z"
    assert result["lock_at"] == "2026-02-08T00:00:00Z"
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
        "unlock_at": "2026-02-22T00:00:00Z",
        "due_at": "2026-03-01T23:59:00Z",
        "lock_at": "2026-03-08T00:00:00Z",
        "points_possible": 50,
        "published": False,
    }

    result = await create_assignment(
        client,
        "1",
        "New Assignment",
        points_possible=50,
        unlock_at="2026-02-22T00:00:00Z",
        due_at="2026-03-01T23:59:00Z",
        lock_at="2026-03-08T00:00:00Z",
    )
    assert result["id"] == 201
    assert result["name"] == "New Assignment"

    call_data = client.request.call_args.kwargs["data"]["assignment"]
    assert call_data["name"] == "New Assignment"
    assert call_data["points_possible"] == 50
    assert call_data["unlock_at"] == "2026-02-22T00:00:00Z"
    assert call_data["due_at"] == "2026-03-01T23:59:00Z"
    assert call_data["lock_at"] == "2026-03-08T00:00:00Z"
    assert result["unlock_at"] == "2026-02-22T00:00:00Z"
    assert result["lock_at"] == "2026-03-08T00:00:00Z"


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


async def test_update_assignment_clears_availability_dates(client):
    client.request.return_value = {
        "id": 101,
        "name": "Updated",
        "unlock_at": None,
        "due_at": None,
        "lock_at": None,
        "points_possible": 75,
        "published": True,
    }

    result = await update_assignment(
        client,
        "1",
        "101",
        clear_unlock_at=True,
        clear_due_at=True,
        clear_lock_at=True,
    )

    call_data = client.request.call_args.kwargs["data"]["assignment"]
    assert call_data == {"unlock_at": None, "due_at": None, "lock_at": None}
    assert result["unlock_at"] is None
    assert result["due_at"] is None
    assert result["lock_at"] is None


async def test_update_assignment_no_fields():
    client = AsyncMock(spec=CanvasClient)
    with pytest.raises(CanvasError, match="No fields to update"):
        await update_assignment(client, "1", "101")
