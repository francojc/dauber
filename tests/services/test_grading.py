"""Tests for dauber.services.grading."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.grading import (
    get_submission,
    list_submissions,
    submit_grade,
    submit_rubric_grade,
)


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


# -- list_submissions --


async def test_list_submissions(client):
    client.get_paginated.return_value = [
        {
            "id": 501,
            "user_id": 10,
            "user": {"name": "Alice Smith"},
            "workflow_state": "submitted",
            "score": None,
            "grade": None,
            "submitted_at": "2026-02-01T12:00:00Z",
        },
        {
            "id": 502,
            "user_id": 20,
            "user": None,
            "workflow_state": "unsubmitted",
            "score": None,
            "grade": None,
            "submitted_at": None,
        },
    ]

    result = await list_submissions(client, "1", "101")
    assert len(result) == 2
    assert result[0]["user_name"] == "Alice Smith"
    assert result[1]["user_name"] == ""


async def test_list_submissions_empty(client):
    client.get_paginated.return_value = []
    result = await list_submissions(client, "1", "101")
    assert result == []


async def test_list_submissions_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/x"),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await list_submissions(client, "1", "101")
    assert exc_info.value.status_code == 403


async def test_list_submissions_anonymize(client):
    client.get_paginated.return_value = [
        {
            "id": 501,
            "user_id": 10,
            "user": {"name": "Alice Smith"},
            "workflow_state": "submitted",
            "score": None,
            "grade": None,
            "submitted_at": "2026-02-01T12:00:00Z",
        },
    ]
    result = await list_submissions(client, "1", "101", anonymize=True)
    assert result[0]["user_name"] == ""
    assert result[0]["user_id"] == 10


# -- get_submission --


async def test_get_submission(client):
    client.request.return_value = {
        "id": 501,
        "user_id": 10,
        "user": {"name": "Alice Smith"},
        "workflow_state": "graded",
        "score": 95,
        "grade": "95",
        "submitted_at": "2026-02-01T12:00:00Z",
        "rubric_assessment": {"_8027": {"points": 25, "comments": "Good"}},
    }

    result = await get_submission(client, "1", "101", "10")
    assert result["user_name"] == "Alice Smith"
    assert result["rubric_assessment"]["_8027"]["points"] == 25

    call_params = client.request.call_args
    assert "rubric_assessment" in call_params.kwargs["params"]["include[]"]


async def test_get_submission_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/x"),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await get_submission(client, "1", "101", "99")
    assert exc_info.value.status_code == 404


async def test_get_submission_anonymize(client):
    client.request.return_value = {
        "id": 501,
        "user_id": 10,
        "user": {"name": "Alice Smith"},
        "workflow_state": "graded",
        "score": 95,
        "grade": "95",
        "submitted_at": "2026-02-01T12:00:00Z",
        "rubric_assessment": {"_8027": {"points": 25}},
    }
    result = await get_submission(client, "1", "101", "10", anonymize=True)
    assert result["user_name"] == ""
    assert result["user_id"] == 10


# -- submit_grade --


async def test_submit_grade(client):
    client.request.return_value = {
        "id": 501,
        "user_id": 10,
        "score": 85,
        "grade": "85",
    }

    result = await submit_grade(client, "1", "101", "10", "85")
    assert result["score"] == 85

    call_args = client.request.call_args
    assert call_args.kwargs["form_data"][0] == ("submission[posted_grade]", "85")


async def test_submit_grade_with_comment(client):
    client.request.return_value = {
        "id": 501,
        "user_id": 10,
        "score": 85,
        "grade": "85",
    }

    await submit_grade(client, "1", "101", "10", "85", comment="Nice work")

    form_data = client.request.call_args.kwargs["form_data"]
    keys = [k for k, _ in form_data]
    assert "comment[text_comment]" in keys


async def test_submit_grade_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("PUT", "https://canvas.test/api/v1/x"),
        response=httpx.Response(422, text="invalid"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await submit_grade(client, "1", "101", "10", "85")
    assert exc_info.value.status_code == 422


# -- submit_rubric_grade --


async def test_submit_rubric_grade(client):
    client.request.return_value = {
        "id": 501,
        "user_id": 10,
        "score": 45,
        "grade": "45",
    }

    assessment = {
        "_8027": {"points": 25, "comments": "Good thesis"},
        "_8028": {"points": 20},
    }

    result = await submit_rubric_grade(client, "1", "101", "10", assessment)
    assert result["score"] == 45

    form_data = client.request.call_args.kwargs["form_data"]
    keys = [k for k, _ in form_data]
    assert "rubric_assessment[_8027][points]" in keys
    assert "rubric_assessment[_8027][comments]" in keys


async def test_submit_rubric_grade_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("PUT", "https://canvas.test/api/v1/x"),
        response=httpx.Response(500, text="server error"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await submit_rubric_grade(
            client,
            "1",
            "101",
            "10",
            {"_8027": {"points": 10}},
        )
    assert exc_info.value.status_code == 500
