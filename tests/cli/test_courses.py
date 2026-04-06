"""Tests for dauber.cli.courses."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_COURSES = [
    {
        "id": 1,
        "course_code": "IS505",
        "name": "Intro to Data Science",
        "term": "Spring 2026",
        "total_students": 25,
    },
]

MOCK_COURSE_DETAIL = {
    "id": 1,
    "course_code": "IS505",
    "name": "Intro to Data Science",
    "start_at": "2026-01-15T00:00:00Z",
    "end_at": "2026-05-15T00:00:00Z",
    "time_zone": "America/New_York",
    "default_view": "feed",
    "is_public": False,
}

MOCK_ENROLLMENTS = [
    {
        "id": 10,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "role": "StudentEnrollment",
    },
]


def _patch_context():
    """Patch EaselContext so CLI commands don't need real config."""
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()

    return patch(
        "dauber.cli.courses.get_context",
        return_value=mock_ctx,
    )


# -- courses list --


@patch("dauber.cli.courses.list_courses", new_callable=AsyncMock)
def test_courses_list(mock_list):
    mock_list.return_value = MOCK_COURSES
    with _patch_context():
        result = runner.invoke(app, ["courses", "list"])
    assert result.exit_code == 0
    assert "IS505" in result.output


@patch("dauber.cli.courses.list_courses", new_callable=AsyncMock)
def test_courses_list_json(mock_list):
    mock_list.return_value = MOCK_COURSES
    with _patch_context():
        result = runner.invoke(app, ["--format", "json", "courses", "list"])
    assert result.exit_code == 0
    assert '"IS505"' in result.output


@patch("dauber.cli.courses.list_courses", new_callable=AsyncMock)
def test_courses_list_csv(mock_list):
    mock_list.return_value = MOCK_COURSES
    with _patch_context():
        result = runner.invoke(app, ["--format", "csv", "courses", "list"])
    assert result.exit_code == 0
    lines = result.output.strip().splitlines()
    assert lines[0] == "id,course_code,name,term,total_students"
    assert "IS505" in lines[1]


@patch("dauber.cli.courses.list_courses", new_callable=AsyncMock)
def test_courses_list_concluded(mock_list):
    mock_list.return_value = []
    with _patch_context():
        result = runner.invoke(app, ["courses", "list", "--concluded"])
    assert result.exit_code == 0
    mock_list.assert_called_once()
    assert (
        mock_list.call_args.kwargs.get("include_concluded")
        or mock_list.call_args.args[1] is True
    )


@patch("dauber.cli.courses.list_courses", new_callable=AsyncMock)
def test_courses_list_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(app, ["courses", "list"])
    assert result.exit_code == 1
    assert "forbidden" in result.output


# -- courses show --


@patch("dauber.cli.courses.get_course", new_callable=AsyncMock)
def test_courses_show(mock_get):
    mock_get.return_value = MOCK_COURSE_DETAIL
    with _patch_context():
        result = runner.invoke(app, ["courses", "show", "--course", "IS505"])
    assert result.exit_code == 0
    assert "IS505" in result.output


@patch("dauber.cli.courses.get_course", new_callable=AsyncMock)
def test_courses_show_error(mock_get):
    mock_get.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["courses", "show", "--course", "99999"])
    assert result.exit_code == 1
    assert "not found" in result.output


# -- courses enrollments --


@patch("dauber.cli.courses.get_enrollments", new_callable=AsyncMock)
def test_courses_enrollments(mock_enroll):
    mock_enroll.return_value = MOCK_ENROLLMENTS
    with _patch_context():
        result = runner.invoke(app, ["courses", "enrollments", "--course", "IS505"])
    assert result.exit_code == 0
    assert "Alice Smith" in result.output


@patch("dauber.cli.courses.get_enrollments", new_callable=AsyncMock)
def test_courses_enrollments_error(mock_enroll):
    mock_enroll.side_effect = CanvasError("server error", status_code=500)
    with _patch_context():
        result = runner.invoke(app, ["courses", "enrollments", "--course", "1"])
    assert result.exit_code == 1
    assert "server error" in result.output
