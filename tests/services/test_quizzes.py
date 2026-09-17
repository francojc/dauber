"""Tests for dauber.services.quizzes."""

from unittest.mock import AsyncMock

import httpx
import pytest

from dauber.core.client import CanvasClient
from dauber.services import CanvasError
from dauber.services.quizzes import (
    create_report,
    download_report,
    get_quiz,
    is_survey_quiz,
    list_quizzes,
    list_reports,
    report_file,
    resolve_assignment_to_quiz,
    wait_for_report,
)

MOCK_QUIZ = {
    "id": 98732,
    "assignment_id": 614873,
    "title": "Capítulo 2: Autoevaluación",
    "quiz_type": "graded_survey",
    "published": True,
    "due_at": "2026-09-10T04:59:00Z",
    "html_url": "https://canvas.test/courses/74806/quizzes/98732",
}

MOCK_REPORT_PENDING = {
    "id": 71956,
    "report_type": "student_analysis",
    "includes_all_versions": False,
    "url": "https://canvas.test/api/v1/courses/74806/quizzes/98732/reports/71956",
    "progress_url": "https://canvas.test/api/v1/progress/1423744",
    "quiz_id": 98732,
}

MOCK_FILE = {
    "id": 6821649,
    "display_name": "Capítulo 2: Autoevaluación Survey Student Analysis Report.csv",
    "filename": "quiz_student_analysis_report.csv",
    "url": "https://canvas.test/files/6821649/download",
    "size": 2779,
}


def _completed_report() -> dict:
    return {**MOCK_REPORT_PENDING, "file": MOCK_FILE}


def _http_error(status: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://canvas.test/api/v1/quizzes")
    response = httpx.Response(status, request=request, text="nope")
    return httpx.HTTPStatusError("boom", request=request, response=response)


@pytest.fixture()
def client():
    return AsyncMock(spec=CanvasClient)


# -- list_quizzes --


async def test_list_quizzes_projects_fields(client):
    client.get_paginated.return_value = [MOCK_QUIZ]

    result = await list_quizzes(client, "74806")

    client.get_paginated.assert_awaited_once_with("/courses/74806/quizzes", params=None)
    assert result == [
        {
            "id": 98732,
            "assignment_id": 614873,
            "title": "Capítulo 2: Autoevaluación",
            "quiz_type": "graded_survey",
            "published": True,
            "due_at": "2026-09-10T04:59:00Z",
        }
    ]


async def test_list_quizzes_search_filter(client):
    client.get_paginated.return_value = [
        MOCK_QUIZ,
        {**MOCK_QUIZ, "id": 99873, "title": "Capítulo 8: Autoevaluación "},
    ]

    result = await list_quizzes(client, "74806", search="capítulo 8")

    assert [q["id"] for q in result] == [99873]
    assert client.get_paginated.await_args.kwargs["params"] == {
        "search_term": "capítulo 8"
    }


async def test_list_quizzes_http_error(client):
    client.get_paginated.side_effect = _http_error(403)

    with pytest.raises(CanvasError) as exc:
        await list_quizzes(client, "74806")

    assert "instructor-level access" in exc.value.message


# -- get_quiz --


async def test_get_quiz(client):
    client.request.return_value = MOCK_QUIZ

    result = await get_quiz(client, "74806", "98732")

    assert result["id"] == 98732
    assert "html_url" not in result


async def test_get_quiz_not_found_hints_new_quizzes(client):
    client.request.side_effect = _http_error(404)

    with pytest.raises(CanvasError) as exc:
        await get_quiz(client, "74806", "999999")

    assert "New Quizzes" in exc.value.message


# -- resolve_assignment_to_quiz --


async def test_resolve_assignment_to_quiz(client):
    client.get_paginated.return_value = [MOCK_QUIZ]

    result = await resolve_assignment_to_quiz(client, "74806", "614873")

    assert result["id"] == 98732


async def test_resolve_assignment_to_quiz_no_match(client):
    client.get_paginated.return_value = [MOCK_QUIZ]

    with pytest.raises(CanvasError) as exc:
        await resolve_assignment_to_quiz(client, "74806", "614874")

    assert "No Classic Quiz" in exc.value.message


# -- list_reports --


async def test_list_reports_bare_array(client):
    client.request.return_value = [MOCK_REPORT_PENDING]

    result = await list_reports(client, "74806", "98732")

    assert result == [MOCK_REPORT_PENDING]


async def test_list_reports_wrapped_payload(client):
    client.request.return_value = {"quiz_reports": [MOCK_REPORT_PENDING]}

    result = await list_reports(client, "74806", "98732")

    assert result == [MOCK_REPORT_PENDING]


# -- create_report --


async def test_create_report_form_encoding(client):
    client.request.return_value = MOCK_REPORT_PENDING

    result = await create_report(
        client, "74806", "98732", report_type="student_analysis"
    )

    kwargs = client.request.await_args.kwargs
    assert kwargs["form_data"] == [
        ("quiz_report[report_type]", "student_analysis"),
        ("quiz_report[includes_all_versions]", "false"),
    ]
    assert result["id"] == 71956


async def test_create_report_all_versions(client):
    client.request.return_value = MOCK_REPORT_PENDING

    await create_report(client, "74806", "98732", includes_all_versions=True)

    assert client.request.await_args.kwargs["form_data"] == [
        ("quiz_report[report_type]", "student_analysis"),
        ("quiz_report[includes_all_versions]", "true"),
    ]


async def test_create_report_unsupported_type(client):
    with pytest.raises(CanvasError) as exc:
        await create_report(client, "74806", "98732", report_type="bogus")

    assert "Unsupported report type" in exc.value.message
    client.request.assert_not_awaited()


# -- wait_for_report --


async def test_wait_for_report_completes_immediately(client):
    client.request.return_value = _completed_report()

    report = await wait_for_report(
        client, "74806", "98732", "71956", progress_url="https://x/api/v1/progress/1"
    )

    assert report_file(report) == MOCK_FILE


async def test_wait_for_report_polls_until_file(client):
    client.request.side_effect = [
        MOCK_REPORT_PENDING,
        {"workflow_state": "running", "message": None},
        _completed_report(),
    ]
    states: list[str] = []

    report = await wait_for_report(
        client,
        "74806",
        "98732",
        "71956",
        progress_url="https://canvas.test/api/v1/progress/1423744",
        initial_interval=0,
        on_progress=lambda state, _: states.append(state),
    )

    assert report_file(report) == MOCK_FILE
    assert states == ["running", "completed"]


async def test_wait_for_report_failure(client):
    client.request.side_effect = [
        MOCK_REPORT_PENDING,
        {"workflow_state": "failed", "message": "quiz has no submissions"},
    ]

    with pytest.raises(CanvasError) as exc:
        await wait_for_report(
            client,
            "74806",
            "98732",
            "71956",
            progress_url="https://canvas.test/api/v1/progress/1423744",
            initial_interval=0,
        )

    assert "quiz has no submissions" in exc.value.message


async def test_wait_for_report_timeout(client):
    client.request.return_value = MOCK_REPORT_PENDING

    with pytest.raises(CanvasError) as exc:
        await wait_for_report(client, "74806", "98732", "71956", timeout=0)

    assert "Timed out" in exc.value.message


# -- download_report --


async def test_download_report_preserves_bytes(client):
    payload = b"name,id,sis_id\r\nDoe,1,2\r\n"
    client.download.return_value = payload

    data = await download_report(client, _completed_report())

    assert data == payload
    client.download.assert_awaited_once_with(MOCK_FILE["url"])


async def test_download_report_without_attachment(client):
    with pytest.raises(CanvasError) as exc:
        await download_report(client, MOCK_REPORT_PENDING)

    assert "no attachment" in exc.value.message


async def test_download_report_http_error(client):
    client.download.side_effect = _http_error(404)

    with pytest.raises(CanvasError) as exc:
        await download_report(client, _completed_report())

    assert "Could not download report" in exc.value.message


# -- helpers --


def test_report_file_missing():
    assert report_file(MOCK_REPORT_PENDING) is None
    assert report_file({"file": "nope"}) is None


def test_is_survey_quiz():
    assert is_survey_quiz(MOCK_QUIZ) is True
    assert is_survey_quiz({"quiz_type": "assignment"}) is False
    assert is_survey_quiz(None) is False
