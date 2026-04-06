"""Tests for dauber.cli.discussions."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_DISCUSSIONS = [
    {
        "id": 1,
        "title": "Introductions",
        "published": True,
        "posted_at": "2026-01-15T10:00:00Z",
        "is_announcement": False,
    },
]

MOCK_DISCUSSION_DETAIL = {
    "id": 1,
    "title": "Introductions",
    "message": "Please introduce yourself.",
    "published": True,
    "posted_at": "2026-01-15T10:00:00Z",
    "is_announcement": False,
    "pinned": False,
    "discussion_type": "threaded",
}

MOCK_CREATED = {
    "id": 5,
    "title": "New Topic",
    "published": False,
    "is_announcement": False,
}

MOCK_UPDATED = {
    "id": 1,
    "title": "Updated",
    "published": True,
    "is_announcement": False,
}


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()
    return patch(
        "dauber.cli.discussions.get_context",
        return_value=mock_ctx,
    )


# -- discussions list --


@patch("dauber.cli.discussions.list_discussions", new_callable=AsyncMock)
def test_discussions_list(mock_list):
    mock_list.return_value = MOCK_DISCUSSIONS
    with _patch_context():
        result = runner.invoke(app, ["discussions", "list", "--course", "IS505"])
    assert result.exit_code == 0
    assert "Introductions" in result.output


@patch("dauber.cli.discussions.list_discussions", new_callable=AsyncMock)
def test_discussions_list_json(mock_list):
    mock_list.return_value = MOCK_DISCUSSIONS
    with _patch_context():
        result = runner.invoke(
            app,
            ["--format", "json", "discussions", "list", "--course", "IS505"],
        )
    assert result.exit_code == 0
    assert '"Introductions"' in result.output


@patch("dauber.cli.discussions.list_discussions", new_callable=AsyncMock)
def test_discussions_list_announcements(mock_list):
    mock_list.return_value = MOCK_DISCUSSIONS
    with _patch_context():
        result = runner.invoke(
            app,
            ["discussions", "list", "--course", "IS505", "--announcements"],
        )
    assert result.exit_code == 0
    mock_list.assert_called_once()


@patch("dauber.cli.discussions.list_discussions", new_callable=AsyncMock)
def test_discussions_list_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(app, ["discussions", "list", "--course", "IS505"])
    assert result.exit_code == 1
    assert "forbidden" in result.output


# -- discussions show --


@patch("dauber.cli.discussions.get_discussion", new_callable=AsyncMock)
def test_discussions_show(mock_get):
    mock_get.return_value = MOCK_DISCUSSION_DETAIL
    with _patch_context():
        result = runner.invoke(app, ["discussions", "show", "--course", "IS505", "1"])
    assert result.exit_code == 0
    assert "Introdu" in result.output


@patch("dauber.cli.discussions.get_discussion", new_callable=AsyncMock)
def test_discussions_show_error(mock_get):
    mock_get.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["discussions", "show", "--course", "IS505", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


# -- discussions create --


@patch("dauber.cli.discussions.create_discussion", new_callable=AsyncMock)
def test_discussions_create(mock_create):
    mock_create.return_value = MOCK_CREATED
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "discussions",
                "create",
                "--course",
                "IS505",
                "New Topic",
                "--message",
                "Hello",
            ],
        )
    assert result.exit_code == 0
    assert "New Topic" in result.output


@patch("dauber.cli.discussions.create_discussion", new_callable=AsyncMock)
def test_discussions_create_announcement(mock_create):
    mock_create.return_value = {**MOCK_CREATED, "is_announcement": True}
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "discussions",
                "create",
                "--course",
                "IS505",
                "Alert",
                "--announcement",
                "--publish",
            ],
        )
    assert result.exit_code == 0


@patch("dauber.cli.discussions.create_discussion", new_callable=AsyncMock)
def test_discussions_create_error(mock_create):
    mock_create.side_effect = CanvasError("invalid", status_code=422)
    with _patch_context():
        result = runner.invoke(
            app, ["discussions", "create", "--course", "IS505", "Bad"]
        )
    assert result.exit_code == 1
    assert "invalid" in result.output


# -- discussions update --


@patch("dauber.cli.discussions.update_discussion", new_callable=AsyncMock)
def test_discussions_update(mock_update):
    mock_update.return_value = MOCK_UPDATED
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "discussions",
                "update",
                "--course",
                "IS505",
                "1",
                "--title",
                "Updated",
            ],
        )
    assert result.exit_code == 0
    assert "Updated" in result.output
