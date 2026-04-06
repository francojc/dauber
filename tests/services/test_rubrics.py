"""Tests for dauber.services.rubrics."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.rubrics import (
    attach_rubric,
    build_rubric_assessment_form_data,
    create_rubric,
    get_rubric,
    list_rubrics,
    parse_rubric_csv,
)


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


# -- list_rubrics --


async def test_list_rubrics(client):
    client.get_paginated.return_value = [
        {
            "id": 1,
            "title": "Essay Rubric",
            "points_possible": 100,
            "data": [{"id": "_8027"}, {"id": "_8028"}],
        },
    ]

    result = await list_rubrics(client, "1")
    assert len(result) == 1
    assert result[0]["title"] == "Essay Rubric"
    assert result[0]["criteria_count"] == 2


async def test_list_rubrics_empty(client):
    client.get_paginated.return_value = []
    result = await list_rubrics(client, "1")
    assert result == []


async def test_list_rubrics_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses/1/rubrics"),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await list_rubrics(client, "1")
    assert exc_info.value.status_code == 403


# -- get_rubric --


async def test_get_rubric(client):
    client.request.return_value = {
        "id": 1,
        "title": "Essay Rubric",
        "points_possible": 100,
        "data": [
            {
                "id": "_8027",
                "description": "Thesis",
                "points": 25,
                "ratings": [
                    {"id": "r1", "description": "Excellent", "points": 25},
                    {"id": "r2", "description": "Poor", "points": 0},
                ],
            },
        ],
    }

    result = await get_rubric(client, "1", "1")
    assert result["title"] == "Essay Rubric"
    assert len(result["criteria"]) == 1
    assert result["criteria"][0]["id"] == "_8027"
    assert len(result["criteria"][0]["ratings"]) == 2


async def test_get_rubric_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/courses/1/rubrics/99"),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await get_rubric(client, "1", "99")
    assert exc_info.value.status_code == 404


# -- build_rubric_assessment_form_data --


def test_build_form_data_basic():
    assessment = {
        "_8027": {"points": 25, "comments": "Good thesis"},
        "_8028": {"points": 20},
    }
    pairs = build_rubric_assessment_form_data(assessment)

    keys = [k for k, _ in pairs]
    assert "rubric_assessment[_8027][points]" in keys
    assert "rubric_assessment[_8027][comments]" in keys
    assert "rubric_assessment[_8028][points]" in keys
    # No comments key for _8028
    assert "rubric_assessment[_8028][comments]" not in keys


def test_build_form_data_with_comment():
    assessment = {"_8027": {"points": 10}}
    pairs = build_rubric_assessment_form_data(assessment, comment="Overall good")

    keys = [k for k, _ in pairs]
    assert "comment[text_comment]" in keys
    values = dict(pairs)
    assert values["comment[text_comment]"] == "Overall good"


def test_build_form_data_with_rating_id():
    assessment = {"_8027": {"points": 25, "rating_id": "r1"}}
    pairs = build_rubric_assessment_form_data(assessment)

    keys = [k for k, _ in pairs]
    assert "rubric_assessment[_8027][rating_id]" in keys


# -- create_rubric --


VALID_CRITERIA = [
    {
        "description": "Thesis",
        "points": 25,
        "ratings": [
            {"description": "Excellent", "points": 25},
            {"description": "Poor", "points": 0},
        ],
    }
]


async def test_create_rubric(client):
    client.request.return_value = {
        "rubric": {
            "id": 10,
            "title": "New Rubric",
            "points_possible": 25,
            "data": [{"id": "_abc"}],
        }
    }

    result = await create_rubric(client, "1", "New Rubric", VALID_CRITERIA)
    assert result["title"] == "New Rubric"
    assert result["criteria_count"] == 1

    call_args = client.request.call_args
    assert call_args[0][0] == "post"
    form_data = call_args[1]["form_data"]
    keys_values = dict(form_data)
    assert keys_values.get("rubric[title]") == "New Rubric"
    assert keys_values.get("rubric[criteria][0][description]") == "Thesis"


async def test_create_rubric_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("POST", "https://canvas.test/api/v1/courses/1/rubrics"),
        response=httpx.Response(422, text="unprocessable"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await create_rubric(client, "1", "New Rubric", VALID_CRITERIA)
    assert exc_info.value.status_code == 422


async def test_create_rubric_empty_criteria(client):
    with pytest.raises(ValueError):
        await create_rubric(client, "1", "New Rubric", [])
    client.request.assert_not_called()


# -- parse_rubric_csv --

CSV_HEADER = (
    "Rubric Name,Criteria Name,Criteria Description,Criteria Enable Range,"
    "Rating Name,Rating Description,Rating Points,"
    "Rating Name,Rating Description,Rating Points"
)
CSV_ROW = "Essay Rubric,Thesis,Strong central argument,false,Excellent,Full marks,25,Poor,Needs work,0"


def test_parse_rubric_csv(tmp_path):
    f = tmp_path / "rubric.csv"
    f.write_text(f"{CSV_HEADER}\n{CSV_ROW}\n")
    title, criteria = parse_rubric_csv(str(f))
    assert title == "Essay Rubric"
    assert len(criteria) == 1
    assert criteria[0]["description"] == "Thesis"
    assert criteria[0]["points"] == 25
    assert any(r["description"] == "Excellent" for r in criteria[0]["ratings"])


def test_parse_rubric_csv_multiple_criteria(tmp_path):
    row2 = "Essay Rubric,Evidence,Use of sources,false,Strong,Good evidence,10,Weak,Little evidence,0"
    f = tmp_path / "rubric.csv"
    f.write_text(f"{CSV_HEADER}\n{CSV_ROW}\n{row2}\n")
    title, criteria = parse_rubric_csv(str(f))
    assert title == "Essay Rubric"
    assert len(criteria) == 2


def test_parse_rubric_csv_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_rubric_csv("/no/such/file.csv")


def test_parse_rubric_csv_invalid_points(tmp_path):
    bad_row = "Essay Rubric,Thesis,Description,false,Excellent,Full marks,BADVAL"
    f = tmp_path / "rubric.csv"
    f.write_text(f"{CSV_HEADER}\n{bad_row}\n")
    with pytest.raises(ValueError, match="Non-numeric points"):
        parse_rubric_csv(str(f))


def test_parse_rubric_csv_multiple_rubric_names(tmp_path):
    row2 = "Other Rubric,Evidence,Sources,false,Strong,Good,10,Weak,Poor,0"
    f = tmp_path / "rubric.csv"
    f.write_text(f"{CSV_HEADER}\n{CSV_ROW}\n{row2}\n")
    with pytest.raises(ValueError, match="Multiple rubric names"):
        parse_rubric_csv(str(f))


# -- attach_rubric --


async def test_attach_rubric(client):
    client.request.return_value = {
        "rubric": {"id": 5},
        "rubric_association": {
            "association_id": "101",
            "association_type": "Assignment",
            "use_for_grading": False,
            "purpose": "grading",
        },
    }

    result = await attach_rubric(client, "1", "5", "101")
    assert result["rubric_id"] == "5"
    assert result["assignment_id"] == "101"
    assert result["purpose"] == "grading"

    call_args = client.request.call_args
    assert call_args[0][0] == "put"
    assert "/rubrics/5" in call_args[0][1]
    body = call_args[1]["data"]
    assert body["rubric_association"]["association_id"] == "101"
    assert body["rubric_association"]["association_type"] == "Assignment"


async def test_attach_rubric_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("PUT", "https://canvas.test/api/v1/courses/1/rubrics/5"),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await attach_rubric(client, "1", "5", "101")
    assert exc_info.value.status_code == 404
