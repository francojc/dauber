"""Tests for dauber.cli.assessments."""

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_ASSIGNMENT_DATA = {
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

MOCK_SUBMISSIONS = [
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

MOCK_SUBMIT_RESULT = {
    "submitted": [{"user_id": "10", "score": 15}],
    "skipped": [],
    "failed": [],
    "total_submitted": 1,
    "total_skipped": 0,
    "total_failed": 0,
}


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()
    return patch(
        "dauber.cli.assessments.get_context",
        return_value=mock_ctx,
    )


# -- assess setup --


@patch(
    "dauber.cli.assessments.fetch_submissions_with_content",
    new_callable=AsyncMock,
)
@patch(
    "dauber.cli.assessments.fetch_assignment_with_rubric",
    new_callable=AsyncMock,
)
def test_assess_setup(mock_fetch_assign, mock_fetch_subs, tmp_path):
    mock_fetch_assign.return_value = MOCK_ASSIGNMENT_DATA
    mock_fetch_subs.return_value = MOCK_SUBMISSIONS
    out_path = str(tmp_path / "test_assessment.json")

    with _patch_context():
        result = runner.invoke(
            app,
            [
                "assess",
                "setup",
                "--course",
                "IS505",
                "101",
                "--output",
                out_path,
            ],
        )
    assert result.exit_code == 0
    assert "Essay 1" in result.output

    data = json.loads((tmp_path / "test_assessment.json").read_text())
    assert data["metadata"]["assignment_name"] == "Essay 1"
    assert len(data["assessments"]) == 1


@patch(
    "dauber.cli.assessments.fetch_assignment_with_rubric",
    new_callable=AsyncMock,
)
def test_assess_setup_error(mock_fetch):
    mock_fetch.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(
            app,
            ["assess", "setup", "--course", "IS505", "999"],
        )
    assert result.exit_code == 1
    assert "not found" in result.output


@patch(
    "dauber.cli.assessments.fetch_submissions_with_content",
    new_callable=AsyncMock,
)
@patch(
    "dauber.cli.assessments.fetch_assignment_with_rubric",
    new_callable=AsyncMock,
)
def test_assess_setup_with_options(mock_fetch_assign, mock_fetch_subs, tmp_path):
    mock_fetch_assign.return_value = MOCK_ASSIGNMENT_DATA
    mock_fetch_subs.return_value = MOCK_SUBMISSIONS
    out_path = str(tmp_path / "test.json")

    with _patch_context():
        result = runner.invoke(
            app,
            [
                "assess",
                "setup",
                "--course",
                "IS505",
                "101",
                "--output",
                out_path,
                "--level",
                "graduate",
                "--feedback-language",
                "es",
                "--language-learning",
                "--formality",
                "formal",
            ],
        )
    assert result.exit_code == 0

    data = json.loads((tmp_path / "test.json").read_text())
    assert data["metadata"]["level"] == "graduate"
    assert data["metadata"]["feedback_language"] == "es"
    assert data["metadata"]["language_learning"] is True
    assert data["metadata"]["formality"] == "formal"


@patch(
    "dauber.cli.assessments.fetch_submissions_with_content",
    new_callable=AsyncMock,
)
@patch(
    "dauber.cli.assessments.fetch_assignment_with_rubric",
    new_callable=AsyncMock,
)
def test_assess_setup_anonymize(mock_fetch_assign, mock_fetch_subs, tmp_path):
    mock_fetch_assign.return_value = MOCK_ASSIGNMENT_DATA
    mock_fetch_subs.return_value = MOCK_SUBMISSIONS
    out_path = str(tmp_path / "test_anon.json")

    with _patch_context():
        result = runner.invoke(
            app,
            [
                "assess",
                "setup",
                "--course",
                "IS505",
                "101",
                "--output",
                out_path,
                "--anonymize",
            ],
        )
    assert result.exit_code == 0
    mock_fetch_subs.assert_called_once()
    assert mock_fetch_subs.call_args.kwargs["anonymize"] is True


# -- assess load --


def test_assess_load(tmp_path):
    data = {
        "metadata": {
            "assignment_name": "Essay 1",
            "points_possible": 20,
        },
        "rubric": {"criteria": {}},
        "assessments": [
            {
                "user_id": 10,
                "reviewed": True,
                "approved": False,
                "rubric_assessment": {
                    "_c1": {"points": 8},
                },
            },
        ],
    }
    path = tmp_path / "assess.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(app, ["--format", "plain", "assess", "load", str(path)])
    assert result.exit_code == 0
    assert "Essay 1" in result.output
    assert "total_submissions: 1" in result.output


def test_assess_load_missing_file():
    result = runner.invoke(app, ["assess", "load", "/nonexistent/path.json"])
    assert result.exit_code == 1
    assert "not found" in result.output


# -- assess update --


def _write_assessment(tmp_path):
    data = {
        "metadata": {"assignment_name": "Essay 1", "points_possible": 20},
        "rubric": {"criteria": {"_c1": {"max_points": 10}}},
        "assessments": [
            {
                "user_id": 10,
                "user_name": "Alice",
                "rubric_assessment": {
                    "_c1": {
                        "points": None,
                        "rating_id": None,
                        "justification": "",
                    },
                },
                "overall_comment": "",
                "reviewed": False,
                "approved": False,
            },
        ],
    }
    path = tmp_path / "assess.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def test_assess_update(tmp_path):
    path = _write_assessment(tmp_path)
    rubric = json.dumps({"_c1": {"points": 8, "justification": "Good work"}})
    result = runner.invoke(
        app,
        [
            "assess",
            "update",
            path,
            "10",
            "--rubric-json",
            rubric,
            "--reviewed",
            "--comment",
            "Well done.",
        ],
    )
    assert result.exit_code == 0

    updated = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
    entry = updated["assessments"][0]
    assert entry["rubric_assessment"]["_c1"]["points"] == 8
    assert entry["reviewed"] is True
    assert entry["overall_comment"] == "Well done."


def test_assess_update_user_not_found(tmp_path):
    path = _write_assessment(tmp_path)
    result = runner.invoke(
        app,
        ["assess", "update", path, "999", "--reviewed"],
    )
    assert result.exit_code == 1
    assert "not found" in result.output


def test_assess_update_invalid_json(tmp_path):
    path = _write_assessment(tmp_path)
    result = runner.invoke(
        app,
        [
            "assess",
            "update",
            path,
            "10",
            "--rubric-json",
            "not-json",
        ],
    )
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


# -- assess submit --


def test_assess_submit_dry_run(tmp_path):
    path = _write_assessment(tmp_path)
    # First approve the assessment
    data = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
    data["assessments"][0]["approved"] = True
    data["assessments"][0]["reviewed"] = True
    data["assessments"][0]["rubric_assessment"]["_c1"]["points"] = 8
    (tmp_path / "assess.json").write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(
        app,
        ["assess", "submit", path, "--course", "IS505", "101"],
    )
    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "Approved: 1" in result.output


def test_assess_submit_no_approved(tmp_path):
    path = _write_assessment(tmp_path)
    result = runner.invoke(
        app,
        ["assess", "submit", path, "--course", "IS505", "101", "--confirm"],
    )
    assert result.exit_code == 1
    assert "No approved" in result.output


@patch(
    "dauber.cli.assessments.submit_assessments",
    new_callable=AsyncMock,
)
def test_assess_submit_confirmed(mock_submit, tmp_path):
    mock_submit.return_value = MOCK_SUBMIT_RESULT
    path = _write_assessment(tmp_path)

    # Approve the assessment
    data = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
    data["assessments"][0]["approved"] = True
    data["assessments"][0]["reviewed"] = True
    data["assessments"][0]["rubric_assessment"]["_c1"]["points"] = 8
    (tmp_path / "assess.json").write_text(json.dumps(data), encoding="utf-8")

    with _patch_context():
        result = runner.invoke(
            app,
            [
                "assess",
                "submit",
                path,
                "--course",
                "IS505",
                "101",
                "--confirm",
            ],
        )
    assert result.exit_code == 0
    assert "1" in result.output  # total_submitted


@patch(
    "dauber.cli.assessments.submit_assessments",
    new_callable=AsyncMock,
)
def test_assess_submit_canvas_error(mock_submit, tmp_path):
    mock_submit.side_effect = CanvasError("server error", status_code=500)
    path = _write_assessment(tmp_path)

    data = json.loads((tmp_path / "assess.json").read_text(encoding="utf-8"))
    data["assessments"][0]["approved"] = True
    data["assessments"][0]["reviewed"] = True
    data["assessments"][0]["rubric_assessment"]["_c1"]["points"] = 8
    (tmp_path / "assess.json").write_text(json.dumps(data), encoding="utf-8")

    with _patch_context():
        result = runner.invoke(
            app,
            [
                "assess",
                "submit",
                path,
                "--course",
                "IS505",
                "101",
                "--confirm",
            ],
        )
    assert result.exit_code == 1
    assert "server error" in result.output
