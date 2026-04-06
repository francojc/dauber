"""Tests for dauber.cli.grading."""

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_SUBMISSIONS = [
    {
        "id": 501,
        "user_id": 10,
        "user_name": "Alice Smith",
        "workflow_state": "submitted",
        "score": "",
        "grade": "",
        "submitted_at": "2026-02-01T12:00:00Z",
    },
]

MOCK_SUBMISSION_DETAIL = {
    "id": 501,
    "user_id": 10,
    "user_name": "Alice Smith",
    "workflow_state": "graded",
    "score": 95,
    "grade": "95",
    "submitted_at": "2026-02-01T12:00:00Z",
    "rubric_assessment": {"_8027": {"points": 25}},
}

MOCK_GRADE_RESULT = {
    "id": 501,
    "user_id": 10,
    "score": 85,
    "grade": "85",
}


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()
    return patch(
        "dauber.cli.grading.get_context",
        return_value=mock_ctx,
    )


# -- grading submissions --


@patch("dauber.cli.grading.list_submissions", new_callable=AsyncMock)
def test_grading_submissions(mock_list):
    mock_list.return_value = MOCK_SUBMISSIONS
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submissions", "--course", "IS505", "101"],
        )
    assert result.exit_code == 0
    assert "Alice Smith" in result.output


@patch("dauber.cli.grading.list_submissions", new_callable=AsyncMock)
def test_grading_submissions_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submissions", "--course", "IS505", "101"],
        )
    assert result.exit_code == 1
    assert "forbidden" in result.output


@patch("dauber.cli.grading.list_submissions", new_callable=AsyncMock)
def test_grading_submissions_anonymize(mock_list):
    mock_list.return_value = [
        {
            "id": 501,
            "user_id": 10,
            "user_name": "",
            "workflow_state": "submitted",
            "score": "",
            "grade": "",
            "submitted_at": "2026-02-01T12:00:00Z",
        },
    ]
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submissions", "--course", "IS505", "101", "--anonymize"],
        )
    assert result.exit_code == 0
    mock_list.assert_called_once()
    assert mock_list.call_args.kwargs["anonymize"] is True
    assert "Alice Smith" not in result.output


# -- grading show --


@patch("dauber.cli.grading.get_submission", new_callable=AsyncMock)
def test_grading_show(mock_get):
    mock_get.return_value = MOCK_SUBMISSION_DETAIL
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "show", "--course", "IS505", "101", "10"],
        )
    assert result.exit_code == 0
    assert "501" in result.output
    assert "Alice" in result.output


@patch("dauber.cli.grading.get_submission", new_callable=AsyncMock)
def test_grading_show_anonymize(mock_get):
    mock_get.return_value = {
        "id": 501,
        "user_id": 10,
        "user_name": "",
        "workflow_state": "graded",
        "score": 95,
        "grade": "95",
        "submitted_at": "2026-02-01T12:00:00Z",
        "rubric_assessment": {"_8027": {"points": 25}},
    }
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "show", "--course", "IS505", "101", "10", "--anonymize"],
        )
    assert result.exit_code == 0
    mock_get.assert_called_once()
    assert mock_get.call_args.kwargs["anonymize"] is True
    assert "Alice Smith" not in result.output


@patch("dauber.cli.grading.get_submission", new_callable=AsyncMock)
def test_grading_show_error(mock_get):
    mock_get.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "show", "--course", "IS505", "101", "99"],
        )
    assert result.exit_code == 1
    assert "not found" in result.output


# -- grading submit --


@patch("dauber.cli.grading.submit_grade", new_callable=AsyncMock)
def test_grading_submit(mock_submit):
    mock_submit.return_value = MOCK_GRADE_RESULT
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submit", "--course", "IS505", "101", "10", "85"],
        )
    assert result.exit_code == 0
    assert "85" in result.output


@patch("dauber.cli.grading.submit_grade", new_callable=AsyncMock)
def test_grading_submit_with_comment(mock_submit):
    mock_submit.return_value = MOCK_GRADE_RESULT
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "grading",
                "submit",
                "--course",
                "IS505",
                "101",
                "10",
                "85",
                "--comment",
                "Nice work",
            ],
        )
    assert result.exit_code == 0
    mock_submit.assert_called_once()
    assert mock_submit.call_args.kwargs.get("comment") == "Nice work" or (
        len(mock_submit.call_args.args) > 5
        and mock_submit.call_args.args[5] is not None
    )


@patch("dauber.cli.grading.submit_grade", new_callable=AsyncMock)
def test_grading_submit_error(mock_submit):
    mock_submit.side_effect = CanvasError("invalid", status_code=422)
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submit", "--course", "IS505", "101", "10", "85"],
        )
    assert result.exit_code == 1
    assert "invalid" in result.output


# -- grading submit-rubric --


@patch("dauber.cli.grading.submit_rubric_grade", new_callable=AsyncMock)
def test_grading_submit_rubric(mock_submit, tmp_path):
    mock_submit.return_value = MOCK_GRADE_RESULT
    assessment = {"_8027": {"points": 25, "comments": "Good"}}
    f = tmp_path / "rubric.json"
    f.write_text(json.dumps(assessment), encoding="utf-8")
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submit-rubric", "--course", "IS505", "101", "10", str(f)],
        )
    assert result.exit_code == 0
    assert "85" in result.output


def test_grading_submit_rubric_invalid_json(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text("not-json", encoding="utf-8")
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submit-rubric", "--course", "IS505", "101", "10", str(f)],
        )
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


def test_grading_submit_rubric_file_not_found():
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "grading",
                "submit-rubric",
                "--course",
                "IS505",
                "101",
                "10",
                "/nonexistent/rubric.json",
            ],
        )
    assert result.exit_code == 1
    assert "File not found" in result.output


@patch("dauber.cli.grading.submit_rubric_grade", new_callable=AsyncMock)
def test_grading_submit_rubric_error(mock_submit, tmp_path):
    mock_submit.side_effect = CanvasError("server error", status_code=500)
    assessment = {"_8027": {"points": 10}}
    f = tmp_path / "rubric.json"
    f.write_text(json.dumps(assessment), encoding="utf-8")
    with _patch_context():
        result = runner.invoke(
            app,
            ["grading", "submit-rubric", "--course", "IS505", "101", "10", str(f)],
        )
    assert result.exit_code == 1
    assert "server error" in result.output
