"""Tests for dauber.services.courses."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.courses import get_course, get_enrollments, list_courses


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


# -- list_courses --


async def test_list_courses(client):
    client.get_paginated.return_value = [
        {
            "id": 1,
            "name": "Intro to Data Science",
            "course_code": "IS505",
            "term": {"name": "Spring 2026"},
            "total_students": 25,
        },
        {
            "id": 2,
            "name": "NLP Seminar",
            "course_code": "IS610",
            "term": None,
            "total_students": 12,
        },
    ]

    result = await list_courses(client)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["course_code"] == "IS505"
    assert result[0]["term"] == "Spring 2026"
    assert result[1]["term"] == ""

    call_params = client.get_paginated.call_args
    assert call_params.args[0] == "/courses"
    assert "available" in call_params.kwargs["params"]["state[]"]
    assert "completed" not in call_params.kwargs["params"]["state[]"]


async def test_list_courses_include_concluded(client):
    client.get_paginated.return_value = []

    await list_courses(client, include_concluded=True)

    call_params = client.get_paginated.call_args
    states = call_params.kwargs["params"]["state[]"]
    assert "available" in states
    assert "completed" in states


async def test_list_courses_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses"),
        response=httpx.Response(403, text="forbidden"),
    )

    with pytest.raises(CanvasError) as exc_info:
        await list_courses(client)
    assert exc_info.value.status_code == 403


# -- get_course --


async def test_get_course(client):
    client.request.return_value = {
        "id": 1,
        "course_code": "IS505",
        "name": "Intro to Data Science",
        "start_at": "2026-01-15T00:00:00Z",
        "end_at": "2026-05-15T00:00:00Z",
        "time_zone": "America/New_York",
        "default_view": "feed",
        "is_public": False,
    }

    result = await get_course(client, "1")
    assert result["id"] == 1
    assert result["course_code"] == "IS505"
    assert result["start_at"] == "2026-01-15T00:00:00Z"
    client.request.assert_called_once_with("get", "/courses/1")


async def test_get_course_missing_fields(client):
    client.request.return_value = {"id": 1}

    result = await get_course(client, "1")
    assert result["course_code"] == ""
    assert result["name"] == ""
    assert result["is_public"] is False


async def test_get_course_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses/99"),
        response=httpx.Response(404, text="not found"),
    )

    with pytest.raises(CanvasError) as exc_info:
        await get_course(client, "99")
    assert exc_info.value.status_code == 404


# -- get_enrollments --


async def test_get_enrollments(client):
    client.get_paginated.return_value = [
        {
            "id": 10,
            "name": "Alice Smith",
            "email": "alice@example.com",
            "enrollments": [{"role": "StudentEnrollment"}],
        },
        {
            "id": 20,
            "name": "Bob Jones",
            "email": "bob@example.com",
            "enrollments": [{"role": "TeacherEnrollment"}],
        },
    ]

    result = await get_enrollments(client, "1")
    assert len(result) == 2
    assert result[0]["name"] == "Alice Smith"
    assert result[0]["role"] == "StudentEnrollment"
    assert result[1]["role"] == "TeacherEnrollment"


async def test_get_enrollments_no_enrollments(client):
    client.get_paginated.return_value = [
        {"id": 10, "name": "No Role User", "email": "none@example.com"},
    ]

    result = await get_enrollments(client, "1")
    assert result[0]["role"] == ""


async def test_get_enrollments_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses/1/users"),
        response=httpx.Response(500, text="server error"),
    )

    with pytest.raises(CanvasError) as exc_info:
        await get_enrollments(client, "1")
    assert exc_info.value.status_code == 500
