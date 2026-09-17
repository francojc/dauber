"""Tests for dauber.cli.quizzes."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from dauber.cli.quizzes import derive_report_filename
from dauber.services import CanvasError

from dauber.cli.app import app

runner = CliRunner()

QUIZ = {
    "id": 98732,
    "assignment_id": 614873,
    "title": "Capítulo 2: Autoevaluación",
    "quiz_type": "graded_survey",
    "published": True,
    "due_at": "2026-09-10T04:59:00Z",
}

REPORT_PENDING = {
    "id": 71956,
    "report_type": "student_analysis",
    "includes_all_versions": False,
    "url": "https://canvas.test/api/v1/courses/74806/quizzes/98732/reports/71956",
    "progress_url": "https://canvas.test/api/v1/progress/1423744",
    "quiz_id": 98732,
}

FILE = {
    "display_name": "Capítulo 2: Autoevaluación Survey Student Analysis Report.csv",
    "url": "https://canvas.test/files/6821649/download",
}

REPORT_DONE = {**REPORT_PENDING, "file": FILE}

CSV_BYTES = b"name,id,sis_id\r\nDoe,1,2\r\n"


def _patch_context():
    mock_ctx = AsyncMock()
    mock_ctx.client = AsyncMock()
    mock_ctx.cache = AsyncMock()
    mock_ctx.cache.resolve = AsyncMock(return_value="74806")
    mock_ctx.close = AsyncMock()
    return patch("dauber.cli.quizzes.get_context", return_value=mock_ctx)


def _quiet():
    """Silence stderr progress output in CLI test output."""
    return patch("dauber.cli.quizzes._console_err")


# -- filename derivation --


def test_derive_filename_survey():
    assert (
        derive_report_filename(
            "Capítulo 2: Autoevaluación", "student_analysis", survey=True
        )
        == "Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv"
    )


def test_derive_filename_trims_trailing_whitespace():
    assert (
        derive_report_filename(
            "Capítulo 8: Autoevaluación ", "student_analysis", survey=True
        )
        == "Capítulo 8_ Autoevaluación Survey Student Analysis Report.csv"
    )


def test_derive_filename_non_survey():
    assert (
        derive_report_filename("Unit 1 Quiz", "student_analysis")
        == "Unit 1 Quiz Student Analysis Report.csv"
    )


def test_derive_filename_item_analysis():
    assert (
        derive_report_filename("Unit 1 Quiz", "item_analysis")
        == "Unit 1 Quiz Item Analysis Report.csv"
    )


def test_derive_filename_fallback_display_name():
    assert (
        derive_report_filename(None, "student_analysis", fallback=FILE["display_name"])
        == "Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv"
    )


def test_derive_filename_no_title_no_fallback():
    assert (
        derive_report_filename("", "student_analysis")
        == "quiz_student_analysis_report.csv"
    )


# -- quizzes list / show / resolve-assignment --


@patch("dauber.cli.quizzes.list_quizzes", new_callable=AsyncMock)
def test_quizzes_list(mock_list):
    mock_list.return_value = [QUIZ]

    with _patch_context():
        result = runner.invoke(app, ["quizzes", "list", "--course", "74806"])

    assert result.exit_code == 0, result.output
    assert "98732" in result.stdout
    assert "614873" in result.stdout


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
def test_quizzes_show(mock_get):
    mock_get.return_value = QUIZ

    with _patch_context():
        result = runner.invoke(app, ["quizzes", "show", "98732", "-c", "74806"])

    assert result.exit_code == 0, result.output
    mock_get.assert_awaited_once()
    assert mock_get.await_args.args[2] == "98732"


@patch("dauber.cli.quizzes.resolve_assignment_to_quiz", new_callable=AsyncMock)
def test_quizzes_resolve_assignment(mock_resolve):
    mock_resolve.return_value = QUIZ

    with _patch_context():
        result = runner.invoke(
            app, ["quizzes", "resolve-assignment", "614873", "-c", "74806"]
        )

    assert result.exit_code == 0, result.output
    assert "98732" in result.stdout


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
def test_quizzes_show_canvas_error_exits_one(mock_get):
    mock_get.side_effect = CanvasError("Quiz 1 not found.")

    with _patch_context():
        result = runner.invoke(app, ["quizzes", "show", "1", "-c", "74806"])

    assert result.exit_code == 1
    assert "Quiz 1 not found." in result.output


# -- reports list / create / show --


@patch("dauber.cli.quizzes.list_reports", new_callable=AsyncMock)
def test_reports_list(mock_list):
    mock_list.return_value = [REPORT_DONE]

    with _patch_context():
        result = runner.invoke(
            app, ["quizzes", "reports", "list", "98732", "-c", "74806"]
        )

    assert result.exit_code == 0, result.output
    assert "71956" in result.stdout


@patch("dauber.cli.quizzes.create_report", new_callable=AsyncMock)
def test_reports_create(mock_create):
    mock_create.return_value = REPORT_PENDING

    with _patch_context():
        result = runner.invoke(
            app,
            ["quizzes", "reports", "create", "98732", "-c", "74806", "--all-versions"],
        )

    assert result.exit_code == 0, result.output
    assert mock_create.await_args.kwargs["includes_all_versions"] is True


def test_reports_create_invalid_type():
    with _patch_context():
        result = runner.invoke(
            app, ["quizzes", "reports", "create", "98732", "-c", "74806", "--type", "x"]
        )

    assert result.exit_code == 2
    assert "unsupported report type" in result.output


# -- reports download --


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_reuses_existing_report(mock_reuse, mock_quiz, tmp_path):
    mock_quiz.return_value = QUIZ
    mock_reuse.return_value = (REPORT_DONE, CSV_BYTES)

    with _patch_context(), _quiet():
        result = runner.invoke(
            app,
            [
                "quizzes",
                "reports",
                "download",
                "98732",
                "-c",
                "74806",
                "-o",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0, result.output
    out = tmp_path / "Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv"
    assert out.read_bytes() == CSV_BYTES


@patch("dauber.cli.quizzes.resolve_assignment_to_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes.download_report", new_callable=AsyncMock)
@patch("dauber.cli.quizzes.wait_for_report", new_callable=AsyncMock)
@patch("dauber.cli.quizzes.create_report", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_creates_and_waits(
    mock_reuse, mock_create, mock_wait, mock_download, mock_resolve, tmp_path
):
    mock_resolve.return_value = QUIZ
    mock_reuse.return_value = (None, None)
    mock_create.return_value = REPORT_PENDING
    mock_wait.return_value = REPORT_DONE
    mock_download.return_value = CSV_BYTES

    with _patch_context(), _quiet():
        result = runner.invoke(
            app,
            [
                "quizzes",
                "reports",
                "download",
                "--assignment",
                "614873",
                "-c",
                "74806",
                "-o",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0, result.output
    mock_create.assert_awaited_once()
    mock_wait.assert_awaited_once()
    assert (
        tmp_path / "Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv"
    ).exists()


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes.create_report", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_no_wait_prints_request(mock_reuse, mock_create, mock_quiz):
    mock_quiz.return_value = QUIZ
    mock_reuse.return_value = (None, None)
    mock_create.return_value = REPORT_PENDING

    with _patch_context(), _quiet():
        result = runner.invoke(
            app,
            ["quizzes", "reports", "download", "98732", "-c", "74806", "--no-wait"],
        )

    assert result.exit_code == 0, result.output
    assert "requested" in result.stdout
    assert "71956" in result.stdout


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_exact_csv_path(mock_reuse, mock_quiz, tmp_path):
    mock_quiz.return_value = QUIZ
    mock_reuse.return_value = (REPORT_DONE, CSV_BYTES)
    target = tmp_path / "custom-name.csv"

    with _patch_context(), _quiet():
        result = runner.invoke(
            app,
            [
                "quizzes",
                "reports",
                "download",
                "98732",
                "-c",
                "74806",
                "-o",
                str(target),
            ],
        )

    assert result.exit_code == 0, result.output
    assert target.read_bytes() == CSV_BYTES


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_refuses_overwrite(mock_reuse, mock_quiz, tmp_path):
    mock_quiz.return_value = QUIZ
    mock_reuse.return_value = (REPORT_DONE, CSV_BYTES)
    target = tmp_path / "Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv"
    target.write_bytes(b"old")

    with _patch_context(), _quiet():
        result = runner.invoke(
            app,
            [
                "quizzes",
                "reports",
                "download",
                "98732",
                "-c",
                "74806",
                "-o",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 2
    assert "refusing to overwrite" in result.output
    assert target.read_bytes() == b"old"


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_force_overwrites(mock_reuse, mock_quiz, tmp_path):
    mock_quiz.return_value = QUIZ
    mock_reuse.return_value = (REPORT_DONE, CSV_BYTES)
    target = tmp_path / "Capítulo 2_ Autoevaluación Survey Student Analysis Report.csv"
    target.write_bytes(b"old")

    with _patch_context(), _quiet():
        result = runner.invoke(
            app,
            [
                "quizzes",
                "reports",
                "download",
                "98732",
                "-c",
                "74806",
                "-o",
                str(tmp_path),
                "--force",
            ],
        )

    assert result.exit_code == 0, result.output
    assert target.read_bytes() == CSV_BYTES


@patch("dauber.cli.quizzes.get_quiz", new_callable=AsyncMock)
@patch("dauber.cli.quizzes._reuse_report", new_callable=AsyncMock)
def test_download_json_output_has_no_progress_noise(mock_reuse, mock_quiz, tmp_path):
    mock_quiz.return_value = QUIZ
    mock_reuse.return_value = (REPORT_DONE, CSV_BYTES)

    with _patch_context():
        result = runner.invoke(
            app,
            [
                "-f",
                "json",
                "quizzes",
                "reports",
                "download",
                "98732",
                "-c",
                "74806",
                "-o",
                str(tmp_path),
            ],
        )

    assert result.exit_code == 0, result.output
    assert result.stdout.strip().startswith("{")
    assert "report 71956" not in result.stdout


def test_download_rejects_quiz_and_assignment():
    with _patch_context():
        result = runner.invoke(
            app,
            [
                "quizzes",
                "reports",
                "download",
                "98732",
                "--assignment",
                "614873",
                "-c",
                "74806",
            ],
        )

    assert result.exit_code == 2
    assert "not both" in result.output


def test_download_requires_quiz_or_assignment():
    with _patch_context():
        result = runner.invoke(app, ["quizzes", "reports", "download", "-c", "74806"])

    assert result.exit_code == 2
    assert "provide a quiz ID" in result.output
