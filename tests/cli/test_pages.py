"""Tests for dauber.cli.pages."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_PAGES = [
    {
        "url": "syllabus",
        "title": "Syllabus",
        "published": True,
        "updated_at": "2026-01-15T10:00:00Z",
    },
]

MOCK_PAGE_DETAIL = {
    "url": "syllabus",
    "title": "Syllabus",
    "body": "Welcome to the course.",
    "published": True,
    "front_page": True,
    "updated_at": "2026-01-15T10:00:00Z",
    "editing_roles": "teachers",
}

MOCK_CREATED = {
    "url": "new-page",
    "title": "New Page",
    "published": False,
}

MOCK_UPDATED = {
    "url": "syllabus",
    "title": "Updated",
    "published": True,
}


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()
    return patch(
        "dauber.cli.pages.get_context",
        return_value=mock_ctx,
    )


# -- pages list --


@patch("dauber.cli.pages.list_pages", new_callable=AsyncMock)
def test_pages_list(mock_list):
    mock_list.return_value = MOCK_PAGES
    with _patch_context():
        result = runner.invoke(app, ["pages", "list", "--course", "IS505"])
    assert result.exit_code == 0
    assert "Syllabus" in result.output


@patch("dauber.cli.pages.list_pages", new_callable=AsyncMock)
def test_pages_list_json(mock_list):
    mock_list.return_value = MOCK_PAGES
    with _patch_context():
        result = runner.invoke(
            app, ["--format", "json", "pages", "list", "--course", "IS505"]
        )
    assert result.exit_code == 0
    assert '"Syllabus"' in result.output


@patch("dauber.cli.pages.list_pages", new_callable=AsyncMock)
def test_pages_list_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(app, ["pages", "list", "--course", "IS505"])
    assert result.exit_code == 1
    assert "forbidden" in result.output


# -- pages show --


@patch("dauber.cli.pages.get_page", new_callable=AsyncMock)
def test_pages_show(mock_get):
    mock_get.return_value = MOCK_PAGE_DETAIL
    with _patch_context():
        result = runner.invoke(app, ["pages", "show", "--course", "IS505", "syllabus"])
    assert result.exit_code == 0
    assert "Syllabus" in result.output


@patch("dauber.cli.pages.get_page", new_callable=AsyncMock)
def test_pages_show_error(mock_get):
    mock_get.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["pages", "show", "--course", "IS505", "missing"])
    assert result.exit_code == 1
    assert "not found" in result.output


# -- pages create --


@patch("dauber.cli.pages.create_page", new_callable=AsyncMock)
def test_pages_create(mock_create):
    mock_create.return_value = MOCK_CREATED
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "pages",
                "create",
                "--course",
                "IS505",
                "New Page",
                "--body",
                "Hello",
            ],
        )
    assert result.exit_code == 0
    assert "New Page" in result.output


@patch("dauber.cli.pages.create_page", new_callable=AsyncMock)
def test_pages_create_error(mock_create):
    mock_create.side_effect = CanvasError("invalid", status_code=422)
    with _patch_context():
        result = runner.invoke(app, ["pages", "create", "--course", "IS505", "Bad"])
    assert result.exit_code == 1
    assert "invalid" in result.output


# -- pages update --


@patch("dauber.cli.pages.update_page", new_callable=AsyncMock)
def test_pages_update(mock_update):
    mock_update.return_value = MOCK_UPDATED
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "pages",
                "update",
                "--course",
                "IS505",
                "syllabus",
                "--title",
                "Updated",
            ],
        )
    assert result.exit_code == 0
    assert "Updated" in result.output


# -- pages delete --


@patch("dauber.cli.pages.delete_page", new_callable=AsyncMock)
def test_pages_delete(mock_delete):
    mock_delete.return_value = {"url": "syllabus", "deleted": True}
    with _patch_context():
        result = runner.invoke(
            app, ["pages", "delete", "--course", "IS505", "syllabus"]
        )
    assert result.exit_code == 0
    assert "Deleted" in result.output


@patch("dauber.cli.pages.delete_page", new_callable=AsyncMock)
def test_pages_delete_error(mock_delete):
    mock_delete.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["pages", "delete", "--course", "IS505", "missing"])
    assert result.exit_code == 1
    assert "not found" in result.output
