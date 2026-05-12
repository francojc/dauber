"""Tests for dauber.cli.modules."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_MODULES = [
    {
        "id": 1,
        "name": "Week 1",
        "position": 1,
        "published": True,
        "items_count": 3,
    },
]

MOCK_MODULE_DETAIL = {
    "id": 1,
    "name": "Week 1",
    "position": 1,
    "published": True,
    "unlock_at": None,
    "require_sequential_progress": False,
    "items_count": 2,
    "items": [
        {"id": 10, "title": "Intro", "type": "Page", "position": 1, "indent": 0},
    ],
}

MOCK_CREATED = {
    "id": 3,
    "name": "Week 3",
    "position": 3,
    "published": False,
}

MOCK_UPDATED = {
    "id": 1,
    "name": "Updated",
    "position": 1,
    "published": True,
}


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()
    return patch(
        "dauber.cli.modules.get_context",
        return_value=mock_ctx,
    )


# -- modules list --


@patch("dauber.cli.modules.list_modules", new_callable=AsyncMock)
def test_modules_list(mock_list):
    mock_list.return_value = MOCK_MODULES
    with _patch_context():
        result = runner.invoke(app, ["modules", "list", "--course", "IS505"])
    assert result.exit_code == 0
    assert "Week 1" in result.output


@patch("dauber.cli.modules.list_modules", new_callable=AsyncMock)
def test_modules_list_json(mock_list):
    mock_list.return_value = MOCK_MODULES
    with _patch_context():
        result = runner.invoke(
            app, ["--format", "json", "modules", "list", "--course", "IS505"]
        )
    assert result.exit_code == 0
    assert '"Week 1"' in result.output


@patch("dauber.cli.modules.list_modules", new_callable=AsyncMock)
def test_modules_list_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(app, ["modules", "list", "--course", "IS505"])
    assert result.exit_code == 1
    assert "forbidden" in result.output


# -- modules show --


@patch("dauber.cli.modules.get_module", new_callable=AsyncMock)
def test_modules_show(mock_get):
    mock_get.return_value = MOCK_MODULE_DETAIL
    with _patch_context():
        result = runner.invoke(app, ["modules", "show", "--course", "IS505", "1"])
    assert result.exit_code == 0
    assert "Week 1" in result.output


@patch("dauber.cli.modules.get_module", new_callable=AsyncMock)
def test_modules_show_error(mock_get):
    mock_get.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["modules", "show", "--course", "IS505", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


# -- modules create --


@patch("dauber.cli.modules.create_module", new_callable=AsyncMock)
def test_modules_create(mock_create):
    mock_create.return_value = MOCK_CREATED
    with _patch_context():
        result = runner.invoke(
            app,
            ["modules", "create", "--course", "IS505", "Week 3", "--position", "3"],
        )
    assert result.exit_code == 0
    assert "Week 3" in result.output


@patch("dauber.cli.modules.create_module", new_callable=AsyncMock)
def test_modules_create_error(mock_create):
    mock_create.side_effect = CanvasError("invalid", status_code=422)
    with _patch_context():
        result = runner.invoke(app, ["modules", "create", "--course", "IS505", "Bad"])
    assert result.exit_code == 1
    assert "invalid" in result.output


# -- modules update --


@patch("dauber.cli.modules.update_module", new_callable=AsyncMock)
def test_modules_update(mock_update):
    mock_update.return_value = MOCK_UPDATED
    with _patch_context():
        result = runner.invoke(
            app,
            ["modules", "update", "--course", "IS505", "1", "--name", "Updated"],
        )
    assert result.exit_code == 0
    assert "Updated" in result.output


# -- modules delete --


@patch("dauber.cli.modules.delete_module", new_callable=AsyncMock)
def test_modules_delete(mock_delete):
    mock_delete.return_value = {"id": "1", "deleted": True}
    with _patch_context():
        result = runner.invoke(app, ["modules", "delete", "--course", "IS505", "1"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


@patch("dauber.cli.modules.delete_module", new_callable=AsyncMock)
def test_modules_delete_error(mock_delete):
    mock_delete.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["modules", "delete", "--course", "IS505", "999"])
    assert result.exit_code == 1
    assert "not found" in result.output


# -- module items --

MOCK_ITEMS = [
    {
        "id": 10,
        "title": "Intro",
        "type": "Page",
        "page_url": "intro",
        "position": 1,
        "indent": 0,
        "published": True,
    },
]

MOCK_ITEM = {
    "id": 10,
    "title": "Intro",
    "type": "Page",
    "page_url": "intro",
    "position": 1,
    "indent": 0,
    "published": True,
}


@patch("dauber.cli.modules.list_module_items", new_callable=AsyncMock)
def test_module_items_list(mock_list):
    mock_list.return_value = MOCK_ITEMS
    with _patch_context():
        result = runner.invoke(
            app, ["modules", "items", "list", "--course", "IS505", "1"]
        )
    assert result.exit_code == 0
    assert "Intro" in result.output


@patch("dauber.cli.modules.get_module_item", new_callable=AsyncMock)
def test_module_items_show(mock_get):
    mock_get.return_value = MOCK_ITEM
    with _patch_context():
        result = runner.invoke(
            app, ["modules", "items", "show", "--course", "IS505", "1", "10"]
        )
    assert result.exit_code == 0
    assert "Intro" in result.output


@patch("dauber.cli.modules.create_module_item", new_callable=AsyncMock)
def test_module_items_create_page(mock_create):
    mock_create.return_value = MOCK_ITEM
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "modules",
                "items",
                "create",
                "--course",
                "IS505",
                "1",
                "Intro",
                "--type",
                "Page",
                "--page-url",
                "intro",
            ],
        )
    assert result.exit_code == 0
    assert "Intro" in result.output
    mock_create.assert_awaited_once()


@patch("dauber.cli.modules.create_module_item", new_callable=AsyncMock)
def test_module_items_create_assignment(mock_create):
    mock_create.return_value = {
        "id": 11,
        "title": "Essay",
        "type": "Assignment",
        "content_id": 42,
    }
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "modules",
                "items",
                "create",
                "--course",
                "IS505",
                "1",
                "Essay",
                "--type",
                "Assignment",
                "--content-id",
                "42",
            ],
        )
    assert result.exit_code == 0
    assert "Essay" in result.output


def test_module_items_create_page_requires_page_url():
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "modules",
                "items",
                "create",
                "--course",
                "IS505",
                "1",
                "Intro",
                "--type",
                "Page",
            ],
        )
    assert result.exit_code != 0
    assert "--page-url is required" in result.output


@patch("dauber.cli.modules.update_module_item", new_callable=AsyncMock)
def test_module_items_update(mock_update):
    mock_update.return_value = {**MOCK_ITEM, "title": "Updated"}
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "modules",
                "items",
                "update",
                "--course",
                "IS505",
                "1",
                "10",
                "--title",
                "Updated",
            ],
        )
    assert result.exit_code == 0
    assert "Updated" in result.output


@patch("dauber.cli.modules.delete_module_item", new_callable=AsyncMock)
def test_module_items_delete(mock_delete):
    mock_delete.return_value = {"id": "10", "deleted": True}
    with _patch_context():
        result = runner.invoke(
            app, ["modules", "items", "delete", "--course", "IS505", "1", "10"]
        )
    assert result.exit_code == 0
    assert "Deleted module item 10" in result.output


@patch("dauber.cli.modules.list_module_items", new_callable=AsyncMock)
def test_module_items_list_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(
            app, ["modules", "items", "list", "--course", "IS505", "1"]
        )
    assert result.exit_code == 1
    assert "forbidden" in result.output
