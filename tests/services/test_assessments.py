"""Tests for dauber.services.assessments."""

import io
import json
from unittest.mock import AsyncMock

import docx
import httpx
import pytest
from pypdf import PdfWriter

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.assessments import (
    build_assessment_structure,
    fetch_assignment_with_rubric,
    fetch_submissions_with_content,
    get_assessment_stats,
    load_assessment,
    save_assessment,
    submit_assessments,
    update_assessment_record,
)


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


SAMPLE_ASSIGNMENT_RESPONSE = {
    "id": 101,
    "name": "Essay 1",
    "description": "<p>Write an essay about linguistics.</p>",
    "due_at": "2026-03-01T23:59:00Z",
    "points_possible": 20,
    "rubric": [
        {
            "id": "_c1",
            "description": "Content",
            "points": 10,
            "ratings": [
                {"id": "r1", "description": "Excellent", "points": 10},
                {"id": "r2", "description": "Good", "points": 7},
                {"id": "r3", "description": "Fair", "points": 4},
            ],
        },
        {
            "id": "_c2",
            "description": "Grammar",
            "points": 10,
            "ratings": [
                {"id": "r4", "description": "Excellent", "points": 10},
                {"id": "r5", "description": "Needs work", "points": 5},
            ],
        },
    ],
    "rubric_settings": {"points_possible": 20},
}

SAMPLE_SUBMISSIONS = [
    {
        "id": 501,
        "user_id": 10,
        "user": {"name": "Alice", "email": "alice@test.edu"},
        "workflow_state": "submitted",
        "body": "<p>My essay content here.</p>",
        "submitted_at": "2026-02-28T12:00:00Z",
        "late": False,
        "submission_comments": [],
    },
    {
        "id": 502,
        "user_id": 20,
        "user": {"name": "Bob", "email": "bob@test.edu"},
        "workflow_state": "graded",
        "body": "Already graded submission.",
        "submitted_at": "2026-02-27T10:00:00Z",
        "late": True,
        "submission_comments": [],
    },
    {
        "id": 503,
        "user_id": 30,
        "user": None,
        "workflow_state": "unsubmitted",
        "body": None,
        "submitted_at": None,
        "late": False,
        "submission_comments": [],
    },
]


# -- fetch_assignment_with_rubric --


async def test_fetch_assignment_with_rubric(client):
    client.request.return_value = SAMPLE_ASSIGNMENT_RESPONSE
    result = await fetch_assignment_with_rubric(client, "1", "101")

    assert result["assignment_name"] == "Essay 1"
    assert result["description"] == "Write an essay about linguistics."
    assert result["rubric"]["criteria_count"] == 2
    assert result["rubric"]["total_points"] == 20
    assert "_c1" in result["rubric"]["criteria"]
    assert len(result["rubric"]["criteria"]["_c1"]["ratings"]) == 3


async def test_fetch_assignment_no_rubric(client):
    client.request.return_value = {
        "id": 101,
        "name": "No Rubric",
        "rubric": None,
    }
    with pytest.raises(CanvasError, match="no rubric"):
        await fetch_assignment_with_rubric(client, "1", "101")


async def test_fetch_assignment_http_error(client):
    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/x"),
        response=httpx.Response(404, text="not found"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await fetch_assignment_with_rubric(client, "1", "999")
    assert exc_info.value.status_code == 404


# -- fetch_submissions_with_content --


async def test_fetch_submissions_excludes_graded(client):
    client.get_paginated.return_value = SAMPLE_SUBMISSIONS
    result = await fetch_submissions_with_content(
        client, "1", "101", exclude_graded=True
    )
    assert len(result) == 1
    assert result[0]["user_id"] == 10
    assert result[0]["user_name"] == "Alice"
    assert result[0]["word_count"] > 0


async def test_fetch_submissions_includes_graded(client):
    client.get_paginated.return_value = SAMPLE_SUBMISSIONS
    result = await fetch_submissions_with_content(
        client, "1", "101", exclude_graded=False
    )
    assert len(result) == 2
    user_ids = [s["user_id"] for s in result]
    assert 10 in user_ids
    assert 20 in user_ids


async def test_fetch_submissions_skips_unsubmitted(client):
    client.get_paginated.return_value = SAMPLE_SUBMISSIONS
    result = await fetch_submissions_with_content(
        client, "1", "101", exclude_graded=False
    )
    user_ids = [s["user_id"] for s in result]
    assert 30 not in user_ids


async def test_fetch_submissions_empty(client):
    client.get_paginated.return_value = []
    result = await fetch_submissions_with_content(client, "1", "101")
    assert result == []


async def test_fetch_submissions_http_error(client):
    client.get_paginated.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("GET", "https://canvas.test/api/v1/x"),
        response=httpx.Response(403, text="forbidden"),
    )
    with pytest.raises(CanvasError) as exc_info:
        await fetch_submissions_with_content(client, "1", "101")
    assert exc_info.value.status_code == 403


async def test_fetch_submissions_anonymize(client):
    client.get_paginated.return_value = SAMPLE_SUBMISSIONS
    result = await fetch_submissions_with_content(
        client, "1", "101", exclude_graded=False, anonymize=True
    )
    for sub in result:
        assert sub["user_name"] == ""
        assert sub["user_email"] == ""
    assert result[0]["user_id"] == 10


# -- build_assessment_structure --


def _sample_assignment_data():
    return {
        "assignment_id": 101,
        "assignment_name": "Essay 1",
        "description": "Write an essay.",
        "due_at": "2026-03-01T23:59:00Z",
        "points_possible": 20,
        "rubric": {
            "total_points": 20,
            "criteria_count": 2,
            "criteria": {
                "_c1": {
                    "description": "Content",
                    "max_points": 10,
                    "ratings": [],
                },
                "_c2": {
                    "description": "Grammar",
                    "max_points": 10,
                    "ratings": [],
                },
            },
        },
    }


def _sample_submissions():
    return [
        {
            "user_id": 10,
            "user_name": "Alice",
            "user_email": "alice@test.edu",
            "submission_id": 501,
            "submitted_at": "2026-02-28T12:00:00Z",
            "late": False,
            "word_count": 50,
            "submission_text": "My essay text.",
        },
    ]


def test_build_assessment_structure():
    data = build_assessment_structure(
        course_id="1",
        course_name="Linguistics 101",
        assignment_data=_sample_assignment_data(),
        submissions=_sample_submissions(),
        level="undergraduate",
        feedback_language="en",
    )

    assert data["metadata"]["course_id"] == "1"
    assert data["metadata"]["assignment_name"] == "Essay 1"
    assert data["metadata"]["workflow_version"] == "1.0"
    assert data["rubric"]["criteria_count"] == 2
    assert len(data["assessments"]) == 1

    a = data["assessments"][0]
    assert a["user_id"] == 10
    assert a["reviewed"] is False
    assert a["approved"] is False
    assert "_c1" in a["rubric_assessment"]
    assert a["rubric_assessment"]["_c1"]["points"] is None


def test_build_assessment_propagates_anonymized_fields():
    subs = [
        {
            "user_id": 10,
            "user_name": "",
            "user_email": "",
            "submission_id": 501,
            "submitted_at": "2026-02-28T12:00:00Z",
            "late": False,
            "word_count": 50,
            "submission_text": "My essay text.",
        },
    ]
    data = build_assessment_structure(
        course_id="1",
        course_name="Test",
        assignment_data=_sample_assignment_data(),
        submissions=subs,
    )
    a = data["assessments"][0]
    assert a["user_name"] == ""
    assert a["user_email"] == ""
    assert a["user_id"] == 10


def test_build_assessment_empty_submissions():
    data = build_assessment_structure(
        course_id="1",
        course_name="Test",
        assignment_data=_sample_assignment_data(),
        submissions=[],
    )
    assert data["metadata"]["total_submissions"] == 0
    assert data["assessments"] == []


# -- load_assessment / save_assessment --


def test_save_and_load(tmp_path):
    data = build_assessment_structure(
        course_id="1",
        course_name="Test",
        assignment_data=_sample_assignment_data(),
        submissions=_sample_submissions(),
    )
    path = tmp_path / "assessments" / "test.json"
    saved = save_assessment(data, path)
    assert saved.exists()

    loaded = load_assessment(saved)
    assert loaded["metadata"]["course_id"] == "1"
    assert len(loaded["assessments"]) == 1


def test_load_missing_file():
    with pytest.raises(CanvasError, match="not found"):
        load_assessment("/nonexistent/path.json")


def test_load_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    with pytest.raises(CanvasError, match="Invalid JSON"):
        load_assessment(bad)


def test_load_missing_keys(tmp_path):
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps({"metadata": {}}), encoding="utf-8")
    with pytest.raises(CanvasError, match="missing required key"):
        load_assessment(incomplete)


# -- update_assessment_record --


def _sample_assessment_data():
    return build_assessment_structure(
        course_id="1",
        course_name="Test",
        assignment_data=_sample_assignment_data(),
        submissions=_sample_submissions(),
    )


def test_update_assessment_record():
    data = _sample_assessment_data()
    entry = update_assessment_record(
        data,
        10,
        rubric_assessment={
            "_c1": {"points": 8, "rating_id": "r1", "justification": "Good"},
        },
        overall_comment="Well done.",
        reviewed=True,
    )
    assert entry["rubric_assessment"]["_c1"]["points"] == 8
    assert entry["overall_comment"] == "Well done."
    assert entry["reviewed"] is True
    assert entry["approved"] is False


def test_update_assessment_record_not_found():
    data = _sample_assessment_data()
    with pytest.raises(CanvasError, match="not found"):
        update_assessment_record(data, 999, reviewed=True)


def test_update_assessment_approve():
    data = _sample_assessment_data()
    entry = update_assessment_record(data, 10, approved=True)
    assert entry["approved"] is True


# -- get_assessment_stats --


def test_get_assessment_stats_no_reviewed():
    data = _sample_assessment_data()
    stats = get_assessment_stats(data)
    assert stats["total_submissions"] == 1
    assert stats["reviewed"] == 0
    assert stats["score_avg"] is None


def test_get_assessment_stats_with_reviewed():
    data = _sample_assessment_data()
    update_assessment_record(
        data,
        10,
        rubric_assessment={
            "_c1": {"points": 8},
            "_c2": {"points": 7},
        },
        reviewed=True,
    )
    stats = get_assessment_stats(data)
    assert stats["reviewed"] == 1
    assert stats["score_avg"] == 15.0
    assert stats["score_min"] == 15.0
    assert stats["score_max"] == 15.0


# -- submit_assessments --


async def test_submit_assessments_approved_only(client):
    data = _sample_assessment_data()
    update_assessment_record(
        data,
        10,
        rubric_assessment={
            "_c1": {"points": 8, "justification": "Good"},
            "_c2": {"points": 7},
        },
        overall_comment="Nice work.",
        reviewed=True,
        approved=True,
    )

    client.request.return_value = {
        "id": 501,
        "user_id": 10,
        "score": 15,
        "grade": "15",
    }

    result = await submit_assessments(client, "1", "101", data)
    assert result["total_submitted"] == 1
    assert result["total_skipped"] == 0


async def test_submit_assessments_skips_unapproved(client):
    data = _sample_assessment_data()
    update_assessment_record(
        data,
        10,
        rubric_assessment={"_c1": {"points": 5}},
        reviewed=True,
    )

    result = await submit_assessments(client, "1", "101", data)
    assert result["total_submitted"] == 0
    assert result["total_skipped"] == 1
    assert result["skipped"][0]["reason"] == "not approved"


async def test_submit_assessments_handles_errors(client):
    data = _sample_assessment_data()
    update_assessment_record(
        data,
        10,
        rubric_assessment={"_c1": {"points": 8}, "_c2": {"points": 7}},
        reviewed=True,
        approved=True,
    )

    client.request.side_effect = httpx.HTTPStatusError(
        "error",
        request=httpx.Request("PUT", "https://canvas.test/api/v1/x"),
        response=httpx.Response(500, text="server error"),
    )

    result = await submit_assessments(client, "1", "101", data)
    assert result["total_submitted"] == 0
    assert result["total_failed"] == 1


# -- online_upload / attachment extraction --


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for p in paragraphs:
        document.add_paragraph(p)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def _make_pdf_bytes(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _upload_submission(
    user_id: int,
    sub_id: int,
    attachments: list[dict],
    workflow_state: str = "submitted",
) -> dict:
    return {
        "id": sub_id,
        "user_id": user_id,
        "user": {"name": f"User{user_id}", "email": f"u{user_id}@test.edu"},
        "workflow_state": workflow_state,
        "submission_type": "online_upload",
        "body": None,
        "url": None,
        "submitted_at": "2026-03-01T12:00:00Z",
        "late": False,
        "submission_comments": [],
        "attachments": attachments,
    }


async def test_online_upload_docx(client):
    docx_bytes = _make_docx_bytes(["Hello world", "Second paragraph"])
    client.download = AsyncMock(return_value=docx_bytes)
    client.get_paginated.return_value = [
        _upload_submission(
            10,
            601,
            [
                {
                    "filename": "essay.docx",
                    "content-type": (
                        "application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document"
                    ),
                    "url": "https://canvas.test/files/1/download",
                }
            ],
        )
    ]
    result = await fetch_submissions_with_content(client, "1", "101")
    assert len(result) == 1
    text = result[0]["submission_text"]
    assert "Hello world" in text
    assert "Second paragraph" in text
    assert result[0]["word_count"] > 0


async def test_online_upload_pdf(client):
    pdf_bytes = _make_pdf_bytes("PDF page content")
    client.download = AsyncMock(return_value=pdf_bytes)
    client.get_paginated.return_value = [
        _upload_submission(
            10,
            602,
            [
                {
                    "filename": "report.pdf",
                    "content-type": "application/pdf",
                    "url": "https://canvas.test/files/2/download",
                }
            ],
        )
    ]
    result = await fetch_submissions_with_content(client, "1", "101")
    assert len(result) == 1
    # blank PDF produces no text but should not raise
    assert isinstance(result[0]["submission_text"], str)


async def test_online_upload_unsupported_type(client):
    client.download = AsyncMock(return_value=b"binary content")
    client.get_paginated.return_value = [
        _upload_submission(
            10,
            603,
            [
                {
                    "filename": "data.xlsx",
                    "content-type": "application/vnd.ms-excel",
                    "url": "https://canvas.test/files/3/download",
                }
            ],
        )
    ]
    result = await fetch_submissions_with_content(client, "1", "101")
    assert "text extraction not supported" in result[0]["submission_text"]
    assert "data.xlsx" in result[0]["submission_text"]


async def test_online_upload_download_failure(client):
    client.download = AsyncMock(side_effect=Exception("connection reset"))
    client.get_paginated.return_value = [
        _upload_submission(
            10,
            604,
            [
                {
                    "filename": "essay.docx",
                    "content-type": (
                        "application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document"
                    ),
                    "url": "https://canvas.test/files/4/download",
                }
            ],
        )
    ]
    result = await fetch_submissions_with_content(client, "1", "101")
    assert "download failed" in result[0]["submission_text"]
    assert "essay.docx" in result[0]["submission_text"]


async def test_online_url_submission(client):
    client.get_paginated.return_value = [
        {
            "id": 605,
            "user_id": 10,
            "user": {"name": "Alice", "email": "alice@test.edu"},
            "workflow_state": "submitted",
            "submission_type": "online_url",
            "body": None,
            "url": "https://example.com/project",
            "submitted_at": "2026-03-01T12:00:00Z",
            "late": False,
            "submission_comments": [],
        }
    ]
    result = await fetch_submissions_with_content(client, "1", "101")
    assert (
        result[0]["submission_text"] == "[url submission: https://example.com/project]"
    )


async def test_unknown_submission_type(client):
    client.get_paginated.return_value = [
        {
            "id": 606,
            "user_id": 10,
            "user": {"name": "Alice", "email": "alice@test.edu"},
            "workflow_state": "submitted",
            "submission_type": "media_recording",
            "body": None,
            "url": None,
            "submitted_at": "2026-03-01T12:00:00Z",
            "late": False,
            "submission_comments": [],
        }
    ]
    result = await fetch_submissions_with_content(client, "1", "101")
    assert "media_recording" in result[0]["submission_text"]
