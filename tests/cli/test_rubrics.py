"""Tests for dauber.cli.rubrics."""

import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.app import app
from dauber.services import CanvasError

runner = CliRunner()

MOCK_RUBRICS = [
    {
        "id": 5,
        "title": "Essay Rubric",
        "points_possible": 100,
        "criteria_count": 2,
    },
]

MOCK_RUBRIC_DETAIL = {
    "id": 5,
    "title": "Essay Rubric",
    "points_possible": 100,
    "criteria": [
        {
            "id": "_8027",
            "description": "Thesis",
            "points": 25,
            "ratings": [
                {"id": "r1", "description": "Excellent", "points": 25},
            ],
        },
    ],
}

MOCK_CREATED = {
    "id": 10,
    "title": "New Rubric",
    "points_possible": 25,
    "criteria_count": 1,
}

RUBRIC_SPEC = {
    "title": "New Rubric",
    "criteria": [
        {
            "description": "Thesis",
            "points": 25,
            "ratings": [
                {"description": "Excellent", "points": 25},
                {"description": "Poor", "points": 0},
            ],
        }
    ],
}


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="1")
    mock_ctx.close = AsyncMock()
    return patch(
        "dauber.cli.rubrics.get_context",
        return_value=mock_ctx,
    )


# -- rubrics list --


@patch("dauber.cli.rubrics.list_rubrics", new_callable=AsyncMock)
def test_rubrics_list(mock_list):
    mock_list.return_value = MOCK_RUBRICS
    with _patch_context():
        result = runner.invoke(app, ["rubrics", "list", "--course", "IS505"])
    assert result.exit_code == 0
    assert "Essay Rubric" in result.output


@patch("dauber.cli.rubrics.list_rubrics", new_callable=AsyncMock)
def test_rubrics_list_json(mock_list):
    mock_list.return_value = MOCK_RUBRICS
    with _patch_context():
        result = runner.invoke(
            app,
            ["--format", "json", "rubrics", "list", "--course", "IS505"],
        )
    assert result.exit_code == 0
    assert '"Essay Rubric"' in result.output


@patch("dauber.cli.rubrics.list_rubrics", new_callable=AsyncMock)
def test_rubrics_list_error(mock_list):
    mock_list.side_effect = CanvasError("forbidden", status_code=403)
    with _patch_context():
        result = runner.invoke(app, ["rubrics", "list", "--course", "IS505"])
    assert result.exit_code == 1
    assert "forbidden" in result.output


# -- rubrics show --


@patch("dauber.cli.rubrics.get_rubric", new_callable=AsyncMock)
def test_rubrics_show(mock_get):
    mock_get.return_value = MOCK_RUBRIC_DETAIL
    with _patch_context():
        result = runner.invoke(app, ["rubrics", "show", "--course", "IS505", "5"])
    assert result.exit_code == 0
    assert "Thesis" in result.output


@patch("dauber.cli.rubrics.get_rubric", new_callable=AsyncMock)
def test_rubrics_show_json(mock_get):
    mock_get.return_value = MOCK_RUBRIC_DETAIL
    with _patch_context():
        result = runner.invoke(
            app,
            ["--format", "json", "rubrics", "show", "--course", "IS505", "5"],
        )
    assert result.exit_code == 0
    assert '"Essay Rubric"' in result.output


@patch("dauber.cli.rubrics.get_rubric", new_callable=AsyncMock)
def test_rubrics_show_error(mock_get):
    mock_get.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(app, ["rubrics", "show", "--course", "IS505", "99"])
    assert result.exit_code == 1


# -- rubrics create --


@patch("dauber.cli.rubrics.create_rubric", new_callable=AsyncMock)
def test_rubrics_create(mock_create, tmp_path):
    mock_create.return_value = MOCK_CREATED
    spec_file = tmp_path / "rubric.json"
    spec_file.write_text(json.dumps(RUBRIC_SPEC))
    with _patch_context():
        result = runner.invoke(
            app,
            ["rubrics", "create", "--course", "IS505", "--file", str(spec_file)],
        )
    assert result.exit_code == 0
    assert "New Rubric" in result.output


def test_rubrics_create_file_not_found():
    result = runner.invoke(
        app,
        ["rubrics", "create", "--course", "IS505", "--file", "/no/such/file.json"],
    )
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_rubrics_create_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{bad")
    result = runner.invoke(
        app,
        ["rubrics", "create", "--course", "IS505", "--file", str(bad_file)],
    )
    assert result.exit_code == 1
    assert "Invalid JSON" in result.output


@patch("dauber.cli.rubrics.create_rubric", new_callable=AsyncMock)
def test_rubrics_create_canvas_error(mock_create, tmp_path):
    mock_create.side_effect = CanvasError("unprocessable", status_code=422)
    spec_file = tmp_path / "rubric.json"
    spec_file.write_text(json.dumps(RUBRIC_SPEC))
    with _patch_context():
        result = runner.invoke(
            app,
            ["rubrics", "create", "--course", "IS505", "--file", str(spec_file)],
        )
    assert result.exit_code == 1
    assert "unprocessable" in result.output


# -- rubrics import --

CSV_HEADER = (
    "Rubric Name,Criteria Name,Criteria Description,Criteria Enable Range,"
    "Rating Name,Rating Description,Rating Points,"
    "Rating Name,Rating Description,Rating Points"
)
CSV_ROW = (
    "Essay Rubric,Thesis,Strong argument,false,"
    "Excellent,Full marks,25,Poor,Needs work,0"
)


@patch("dauber.cli.rubrics.create_rubric", new_callable=AsyncMock)
def test_rubrics_import(mock_create, tmp_path):
    mock_create.return_value = MOCK_CREATED
    csv_file = tmp_path / "rubric.csv"
    csv_file.write_text(f"{CSV_HEADER}\n{CSV_ROW}\n")
    with _patch_context():
        result = runner.invoke(
            app,
            ["rubrics", "import", "--course", "IS505", "--csv", str(csv_file)],
        )
    assert result.exit_code == 0
    assert "New Rubric" in result.output


def test_rubrics_import_file_not_found():
    result = runner.invoke(
        app,
        ["rubrics", "import", "--course", "IS505", "--csv", "/no/such/file.csv"],
    )
    assert result.exit_code == 1
    assert "File not found" in result.output


def test_rubrics_import_invalid_csv(tmp_path):
    bad_row = "Essay Rubric,Thesis,Description,false,Excellent,Full marks,BADVAL"
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text(f"{CSV_HEADER}\n{bad_row}\n")
    result = runner.invoke(
        app,
        ["rubrics", "import", "--course", "IS505", "--csv", str(csv_file)],
    )
    assert result.exit_code == 1
    assert "Non-numeric points" in result.output


# -- rubrics attach --

MOCK_ATTACH = {
    "rubric_id": "5",
    "assignment_id": "101",
    "use_for_grading": False,
    "purpose": "grading",
}


@patch("dauber.cli.rubrics.attach_rubric", new_callable=AsyncMock)
def test_rubrics_attach(mock_attach):
    mock_attach.return_value = MOCK_ATTACH
    with _patch_context():
        result = runner.invoke(
            app,
            ["rubrics", "attach", "--course", "IS505", "5", "101"],
        )
    assert result.exit_code == 0
    assert "5" in result.output


@patch("dauber.cli.rubrics.attach_rubric", new_callable=AsyncMock)
def test_rubrics_attach_error(mock_attach):
    mock_attach.side_effect = CanvasError("not found", status_code=404)
    with _patch_context():
        result = runner.invoke(
            app,
            ["rubrics", "attach", "--course", "IS505", "5", "101"],
        )
    assert result.exit_code == 1
    assert "not found" in result.output
